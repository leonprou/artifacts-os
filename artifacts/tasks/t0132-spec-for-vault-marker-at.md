---
kind: task
id: t0132
name: spec-for-vault-marker-at
type: spec
status: done
assignee: architect
owner: user
parent: "[[t0131-move-artifacts-yaml-to-project]]"
artifacts:
  - "[[artifacts/specs/s0026-vault-marker-at-root]]"
created: 2026-05-09
started: 2026-05-10
completed: 2026-05-10
---

# Spec For Vault Marker At Project Root

# Spec: relocate vault marker to project root

## Requirements

The architect should produce a spec under `artifacts/specs/`
that defines the contract for moving the vault marker from
`artifacts/artifacts.yaml` to `./artifacts.yaml` (project root).
Parent task: [[t0131-move-artifacts-yaml-to-project]].

The spec must cover:

1. **New layout, stated precisely** — the canonical paths after
   the change (marker at `<project-root>/artifacts.yaml`, data
   under `<project-root>/artifacts/`), and the relationship
   between them. Define what counts as the "vault root" in the
   new world: the directory containing the marker, or the
   `artifacts/` directory? Pick one and justify.

2. **Resolution algorithm change** — exact replacement for
   `find_vault_root` in `src/artifacts_os/core/vault.py`.
   Specify the walk-up condition, what to return, and edge cases
   (e.g. CWD inside `artifacts/`, CWD at project root, CWD
   anywhere above). Include before/after pseudocode.

3. **Settings loading impact** — how `core.load_settings` and
   any module `from_base` extensions resolve the YAML path after
   the move. List every call-site in `src/` that constructs the
   marker path and the change required at each.

4. **`artifacts init` flow** — what files/directories the
   command creates after the change. Update the init contract
   from `s0021-artifacts-init-flow` (or supersede the relevant
   section). Cover both empty-directory and existing-project
   cases.

5. **Backward compatibility decision** — pick one explicitly:
   (a) hard cutover — old location is no longer recognised;
   `find_vault_root` ignores `artifacts/artifacts.yaml`;
   (b) dual-recognition — both locations work, with a deprecation
   warning when the old one is found;
   (c) migration-only — old location triggers a clear error
   pointing the user at the migration command.
   Justify the pick. Pre-1.0 the project has license to break.

6. **Migration story** — concrete plan for moving an existing
   vault. At minimum: a documented manual procedure (a few
   `mv`/edit steps). Optionally: an `artifacts migrate` (or
   equivalent) helper that detects the old layout and performs
   the move. Architect decides which to include in v1; if a
   helper is added, spec the CLI surface, dry-run behaviour, and
   exit codes.

7. **Documentation update plan** — enumerate the docs and
   READMEs that reference `artifacts/artifacts.yaml` today
   (`CLAUDE.md`, `README.md`, `docs/settings.md`,
   `docs/init-flow.md`, `docs/adding-a-kind.md`, per-module
   READMEs, etc.). The implementation task uses this list as
   its checklist.

8. **Tests / fixtures impact** — how `make_vault` and any other
   test helpers create the marker, and which test files need to
   be touched. Spec does not need to enumerate every test, but
   should call out the fixtures.

9. **Worked example** — show a fresh `artifacts init` run and
   the resulting tree, plus a `find_vault_root` walk from a
   nested CWD, before vs. after.

10. **Out of scope, made explicit** — anything the spec
    deliberately defers (e.g. multi-vault projects, marker
    rename, schema changes inside `artifacts.yaml`).

11. **Build sequence** — ordered, independently-shippable steps
    the implementing task(s) should follow (e.g. resolution
    change → init change → migrate this repo's vault → docs
    sweep). Each step should be small enough to land in one PR.

## Progress

### 2026-05-10 — architect

- Loaded parent task (t0131) and predecessor pair (t0133/t0134
  rejected) for context.
- Audited current marker call sites:
  `rg "artifacts/artifacts\.yaml"` on `src/` (7 sites + 5
  docstring-only), `tests/` (~40 sites + 3 fixtures),
  `docs/` + READMEs + skills (~20 sites).
- Wrote **[[artifacts/specs/s0026-vault-marker-at-root]]**
  covering all 11 requirements; locked decisions D1–D8 in
  §4 with trade-offs in §10.
- Created sibling implementation tasks
  [[t0137-implement-vault-marker-relocation-per]] (PR1 —
  developer) and
  [[t0138-docs-sweep-for-vault-marker]] (PR2 —
  technical-writer); wired both into t0131's `subtasks`.
- Transitioning t0132 → review.

## Findings

Produced **[[artifacts/specs/s0026-vault-marker-at-root]]**
covering all 11 requirements.

**Key decisions:**

- **D1 — Marker at `<vault-root>/artifacts.yaml`**, with
  `artifacts/` continuing to host artifact data. The doubled
  `artifacts/artifacts.yaml` token disappears from call sites
  and docs.
- **D2 — "Vault root" stays the project root** (the directory
  containing the marker). Promoting `artifacts/` to "the vault"
  was rejected because it would force every
  `root / "artifacts" / kd.dir` consumer to change — net
  conceptual gain ≈ 0 against significant code churn.
- **D3 — Hard cutover**, not dual-recognition. Pre-1.0; no
  PyPI users; migration is a one-line `mv`. Dual recognition
  would land a deprecation branch we'd then need to sweep.
- **D4 — Documented `mv`, no helper command.** Mechanical
  one-time-per-vault op; a CLI subcommand is more code than
  the operation warrants.
- **D5 — Two atomic PRs.** PR1 changes code + this repo's
  vault + tests in lock-step (further splitting requires a
  known-broken intermediate state). PR2 sweeps documentation.
- **D6 — Type-strict probe** (`is_file()`) sidesteps the
  `artifacts.yaml` file vs `artifacts/` directory name
  collision by construction.

**Trade-offs explicitly captured** (spec §10):
- `<root>/` vs `artifacts/` as vault root → `<root>/`.
- Flat vault vs nested `artifacts/` → keep nested.
- Hard cutover vs dual-recognition → hard cutover.
- Migration helper vs documented `mv` → documented.

**Surfaces enumerated:**
- 7 src/ call sites changing path string (§7).
- 3 `make_vault` factories + ~40 inline test sites (§14).
- ~20 doc/README references (§12) split into the §13 PR2
  sweep.

**Implementing task to be created:** `developer` task that
executes PR1 from the build sequence (§13.1). Recommend
splitting PR2 (docs sweep) into its own follow-up task — it
is pure prose with no test/CI risk and benefits from being
reviewed independently.

## Downstream

- **Implementation task (PR1).** Single developer task
  executing §13.1 build sequence — code changes, fixture
  updates, this repo's `git mv`, new `docs/migration.md`,
  CHANGELOG entry. Single atomic PR.
- **Docs-sweep task (PR2).** Technical-writer or developer
  task executing §12 + §13.2 — every doc/README reference
  rewritten in one prose-only PR.
- **Migration-helper task (deferred).** Only if user
  feedback after release shows the documented `mv` path is
  causing friction (§10.4). Not auto-created.

## Verification

- [ ] Spec file exists at `artifacts/specs/sNNNN-vault-marker-at-root.md`
      (or similar slug) with proper frontmatter
      (`kind: spec`, `name`, `id`, `task: "[[t0131-...]]"`).
- [ ] New layout is stated precisely and the "vault root"
      definition is unambiguous.
- [ ] `find_vault_root` replacement is specified with
      before/after pseudocode and edge-case handling.
- [ ] Every call-site in `src/` that references the old marker
      path is enumerated.
- [ ] `artifacts init` post-change behaviour is fully specified
      and reconciled with `s0021`.
- [ ] Backward compatibility decision is picked explicitly and
      justified.
- [ ] Migration plan is concrete (manual steps at minimum;
      helper command spec'd if included).
- [ ] Doc/README update checklist is exhaustive.
- [ ] Test fixture impact (e.g. `make_vault`) is called out.
- [ ] Worked example shows before/after tree and resolution
      walk.
- [ ] Out-of-scope section is included.
- [ ] Build sequence is ordered and each step is
      independently-shippable.
