---
assignee: integrator
created: 2026-05-18
depends_on:
- '[[t0173-implement-artbook-promotion-engine-and]]'
id: t0175
kind: task
name: migrate-artbook-yaml-to-promote
owner: user
parent: '[[t0169-add-post-pull-artifact-promotion]]'
status: done
type: implementation
---

# Migrate Artbook.Yaml To Promote Shape And Rewrite Init D2 Fallback

## Goal

Land the **user-visible** half of the post-pull artifact promotion mechanism: migrate the artifacts-os distro's own `artbook.yaml` to the canonical-landing + promote shape, and rewrite the no-distro init D2 fallback to flow through the canonical + promote pipeline. This is **S5** from § 6 of [[s0031-artbook-post-pull-artifact-promotion]] and the sub-task where operators actually see the feature working end-to-end.

After this task lands, `artifacts init` against the artifacts-os distro produces `artifacts/agents/` populated *and* `.claude/agents/` symlinked to it — the bug captured in [[t0169-add-post-pull-artifact-promotion]] § Why is fixed.

## Scope

Per § 4.3, § 5.1, and § 6 S5 of [[s0031]]:

### `artbook.yaml` (repo root) migration

Rewrite per the worked example in § 4.3 of [[s0031]] — same `version: 1`, tightened semantics:

- **`agents`** — drop `dest: .claude/agents/`; defaults to `artifacts/agents/`. Add `promote: .claude/agents/`.
- **`commands`** — `dest: artifacts/commands/` (explicit, mirrors the D37 default for clarity since `src` basename differs from canonical). Add `promote: .claude/commands/`.
- **`skills`** — `dest: artifacts/skills/` (explicit, same reason). Add `promote: .claude/skills/`. Keep `recurse: true`.
- **`kinds`** — drop `dest: artifacts/kinds/` (default suffices). **No** `promote:` — kinds are canonical-only.
- Update the leading comment block in `artbook.yaml` to point at [[s0031]] as the spec governing the new shape.

### `src/artifacts_os/cli/commands/init.py` — D2 fallback rewrite (D40)

Replace the direct-to-`.claude/skills/` write in `_install_bundled_skill` with a canonical-write + synthetic-book `promote_book` call:

1. Copy the bundled skill resource to `artifacts/skills/artifacts-os/SKILL.md` (canonical, via the same atomic-write path used elsewhere).
2. Construct a synthetic in-memory `Book` (not persisted to any manifest):
   ```python
   Book(
       name="artifacts-os-skill",
       src="(bundled)",
       dest="artifacts/skills/",
       promote=Promote(target=".claude/skills/", mode="symlink"),
       recurse=True,
       files=None,
   )
   ```
3. Call `promote_book` against the synthetic book to emit the symlink at `.claude/skills/artifacts-os/SKILL.md → ../../artifacts/skills/artifacts-os/SKILL.md`.
4. The state file at `artifacts/.artbook/state.json` records the promotion under `promotions["artifacts-os-skill"]`. A subsequent `artifacts init --distro <url> --force` that pulls a distro-shipped `skills` book replaces this entry cleanly (the synthetic name does not collide).
5. Plumb `--no-promote` through `init` so an operator can opt out of the bundled-skill promotion at install time.

### Tests

- **`tests/cli/test_init.py`**
  - D2 fallback (`artifacts init -y` with no distro) writes **both** `artifacts/skills/artifacts-os/SKILL.md` and `.claude/skills/artifacts-os/SKILL.md`.
  - The promotion at `.claude/skills/artifacts-os/SKILL.md` is a symlink resolving to the canonical file.
  - `artifacts/.artbook/state.json` exists and records the synthetic book under `promotions["artifacts-os-skill"]`.
  - `artifacts init -y --no-promote` writes only the canonical file; no `.claude/skills/` directory; no state file entry.
  - A second `artifacts init -y` against the same vault is idempotent (no spurious writes; state file byte-stable).
- **`tests/artbook/test_pull_integration.py`** — add end-to-end fixture-driven tests that use a local clone of this repo's own `artbook.yaml` as the distro:
  - `artifacts init --distro file://<repo> -y` populates `artifacts/agents/`, `artifacts/commands/`, `artifacts/skills/`, `artifacts/kinds/`, *and* `.claude/agents/`, `.claude/commands/`, `.claude/skills/` (all symlinked to canonical).
  - `.claude/kinds/` does **not** exist (kinds book has no `promote:`).
  - `artifacts list --kind agent` returns the 10 default agents on the freshly-initialised vault.
  - A second `book pull agents` is byte-for-byte idempotent.

### Spec-side bookkeeping

- **`artifacts/specs/s0030-books-driven-init-flow.md`** — add a Revision note that D2 (no-distro fallback) is amended by [[s0031]] D40 to flow through canonical + promote.

## Out of scope

- Engine / CLI surface — delivered by [[t0173]].
- Documentation — delivered by the S4 sub-task.
- Multi-tool distros (Cursor, Codex). Deferred per L4.
- Auto-promotion of user-authored content created via `artifacts create`. Deferred per D35.

## Dependencies

- **Blocked by [[t0173]]**. This task cannot land until the engine (`promote_book`, state file, extended `PullReport`) and the CLI surface (`--no-promote`, settings) are in place. The synthetic-book D40 path reuses `promote_book` directly; the migration relies on the parser accepting `promote:` and rejecting `dest: .claude/…`.

## Verification (end-to-end on a clean vault)

- [ ] `artifacts init -y` (no distro) writes both `artifacts/skills/artifacts-os/SKILL.md` (canonical, regular file) and `.claude/skills/artifacts-os/SKILL.md` (symlink resolving to the canonical).
- [ ] `artifacts/.artbook/state.json` records the synthetic book under `promotions["artifacts-os-skill"]`.
- [ ] `artifacts init -y --no-promote` (no distro) writes only the canonical bundled skill; no `.claude/skills/` directory; no state file.
- [ ] `artifacts init --distro file://<this-repo> -y` produces:
  - `artifacts/agents/` (10 files) + `.claude/agents/` (10 symlinks → canonical).
  - `artifacts/commands/` + `.claude/commands/` (symlinked).
  - `artifacts/skills/` + `.claude/skills/` (symlinked, recurse).
  - `artifacts/kinds/` only (no `.claude/kinds/`).
- [ ] `artifacts list --kind agent` returns the 10 default agents on the freshly-initialised vault.
- [ ] A second `book pull agents` against the same vault is byte-for-byte idempotent (no canonical changes, no state-file content changes).
- [ ] s0030 has the new Revision note at the top per § 5.5 of s0031.
- [ ] `artbook.yaml` (repo root) is migrated per § 4.3 of [[s0031]] and leading comment points at the new spec.
- [ ] `pytest tests/cli/test_init.py tests/artbook/test_pull_integration.py` passes.

## References

- Parent spec: [[s0031-artbook-post-pull-artifact-promotion]] § 4.1 (transcript A), § 4.3 (migration example), § 5.1 (init.py change), § 6 S5, § 3 (D40).
- Parent feature: [[t0169-add-post-pull-artifact-promotion]] — § Why captures the bug this task fixes.
- Sibling implementation: [[t0173]] — engine + CLI surface; **must land first**.
- Sibling docs: S4 sub-task — documentation; ships in parallel.
- Init-flow ancestor: [[s0030-books-driven-init-flow]] — original D2 design, amended by s0031 D40.
- Files: `artbook.yaml` (repo root), `src/artifacts_os/cli/commands/init.py`, `tests/cli/test_init.py`, `tests/artbook/test_pull_integration.py`, `artifacts/specs/s0030-books-driven-init-flow.md`.