---
kind: task
id: t0137
name: implement-vault-marker-relocation-per
type: implementation
status: in-progress
assignee: developer
owner: user
parent: "[[t0131-move-artifacts-yaml-to-project]]"
depends_on:
  - "[[t0132-spec-for-vault-marker-at]]"
created: 2026-05-10
started: 2026-05-10
---

# Implement Vault Marker Relocation (PR1)

## Requirements

Execute **PR1 of the build sequence** from
[[artifacts/specs/s0026-vault-marker-at-root]] §13.1 —
the atomic code + fixtures + self-vault migration.

This task is intentionally **single-PR** because the changes
are interlocked: `find_vault_root` cannot ship without the
fixture update (every test fails); the fixture update cannot
ship without `find_vault_root` (every test fails); this repo's
`artifacts/artifacts.yaml` cannot move until `find_vault_root`
recognises the new location. All three land together.

### Scope (in)

1. **`find_vault_root` resolution change** — drop the inner
   `"artifacts"` from the probe path per s0026 §6.2.
2. **Read-side path constructions** — all 7 call sites in
   `src/` enumerated in s0026 §7 (table). Concretely:
   - `src/artifacts_os/core/vault.py` (probe + docstring)
   - `src/artifacts_os/cli/__init__.py` (lines 56, 72)
   - `src/artifacts_os/cli/commands/init.py` (lines 419, 539)
   - `src/artifacts_os/hooks/loader.py` (line 85)
   - `src/artifacts_os/ai/install.py` (line 301)
   - `src/artifacts_os/cli/commands/views.py` (line 21 —
     embedded error string)
3. **Test fixtures** — three `make_vault` factories per
   s0026 §14.1:
   - `tests/core/conftest.py`
   - `tests/cli/conftest.py`
   - `tests/ai/conftest.py`
4. **Inline fixture sites** — ~40 occurrences across the
   `tests/` files listed in s0026 §14.2. Bulk pattern:
   `(<expr> / "artifacts" / "artifacts.yaml")` →
   `(<expr> / "artifacts.yaml")`.
5. **New `find_vault_root` tests** — five cases per s0026
   §14.3 added to `tests/core/test_vault.py`, including
   the legacy-only case that pins D3 (hard cutover).
6. **Migrate this repo's vault** —
   `git mv artifacts/artifacts.yaml ./artifacts.yaml`
   in the same commit as the code changes.
7. **New `docs/migration.md`** — content per s0026
   §11.1–11.2.
8. **CHANGELOG entry** — one-liner under the next minor
   version pointing to `docs/migration.md`.
9. **Updated "not in a vault" error message** — link to
   `docs/migration.md` per s0026 §9.3.

### Scope (out)

- **Documentation sweep** — every doc/README reference
  rewrite is the sibling task [[t0138-docs-sweep-for-vault-marker]].
  This task does **not** edit `CLAUDE.md`, `README.md`,
  `docs/settings.md`, `docs/init-flow.md`,
  `docs/adding-a-kind.md`, `docs/creating-an-artifact.md`,
  or any per-module README. Only `docs/migration.md` (new)
  is created here.
- **Spec amendments** — any tweaks to `s0021-artifacts-init-flow`
  worked transcripts belong to t0138.
- **Migration helper command** — explicitly out of scope
  (s0026 §3, §10.4).

### Implementation order within the PR

Recommended commit-by-commit shape (a single PR with a clean
history):

1. Update `find_vault_root` + the 7 read-side call sites.
2. Update the 3 `make_vault` factories.
3. Bulk-update the ~40 inline fixture sites
   (`grep -rn 'artifacts.*artifacts\.yaml' tests/` to verify
   no stragglers).
4. Add the 5 new `test_vault.py` cases.
5. `git mv artifacts/artifacts.yaml ./artifacts.yaml`.
6. Add `docs/migration.md` and the CHANGELOG entry.
7. Update the error message in `cli/__init__.py` to point
   at `docs/migration.md`.

`pytest` must pass after step 5 (and at the end of the PR).
Steps 1–4 cannot pass tests until step 5 lands; commit them
together in a single atomic commit if a stricter "every
commit is green" rule is enforced.

## Verification

- [ ] `find_vault_root` probe path matches s0026 §6.2
      verbatim.
- [ ] All 7 read-side call sites in s0026 §7 updated.
- [ ] All 3 `make_vault` factories updated; `pytest` passes.
- [ ] All 5 new `test_vault.py` cases from s0026 §14.3
      present and passing — including the legacy-only case
      that returns `None` (D3 hard-cutover pin).
- [ ] No occurrence of the literal `artifacts/artifacts.yaml`
      remains in `src/` or `tests/` (confirmed by
      `grep -rn 'artifacts.*artifacts\.yaml' src/ tests/`).
- [ ] This repo's `artifacts/artifacts.yaml` is now at
      `./artifacts.yaml`; `artifacts list --kind task` works
      from project root and from `artifacts/specs/`.
- [ ] `docs/migration.md` exists with §11.1–11.2 content.
- [ ] `CHANGELOG.md` has a one-line entry under the next
      version that links to `docs/migration.md`.
- [ ] "Not in a vault" CLI error message now references
      `docs/migration.md`.
- [ ] `pytest` exits 0 with no skips for changed modules.
