---
assignee: developer
completed: 2026-05-03
created: 2026-05-02
id: t0076
kind: task
name: implement-l1-kinds-catalogue-s0017
owner: user
parent: '[[t0079-artifact-md-artifacts-ai-extension]]'
priority: normal
started: 2026-05-03
status: done
type: implementation
---

# Implement L1 Kinds Catalogue (s0017)

## Goal

Implement the L1 catalogue surface locked by
`[[s0017-artifact-kinds-discovery-mechanism]]`. After this task, every
registered artifact kind exposes a one-line `description` and a
`has_template` boolean through both the Python API
(`KindCatalog.list_kinds()`) and the CLI (`artifacts kinds`).

The scope is exactly what s0017 § 5–§ 9 locks. Anything sketched in
s0017 § 11 "Next Steps" is **not** part of this task.

## Source of truth

`[[s0017-artifact-kinds-discovery-mechanism]]` § 12 lists the six
implementation steps. This task body is a brief; the spec is binding.

## Implementation steps (mirrors s0017 § 12)

1. **New module** `src/artifacts_os/core/kinds_catalog.py` exposing
   `KindCatalog` and `KindCatalogEntry` per s0017 § 5.1 / § 8.1.
2. **Registry extension** — `Registry._load_vault_kinds`
   (`src/artifacts_os/core/registry.py`) reads `ARTIFACT.md`
   frontmatter alongside `kind.json` and emits the validation
   warnings/errors per s0017 § 6.3 and § 7.
3. **CLI changes** — `artifacts kinds` (`src/artifacts_os/cli/commands/kinds.py`)
   gains the `description` column in table output; `-j` JSON gains
   `description` and `has_template` keys. `-q` mode unchanged
   (s0017 § 8.3).
4. **Loader compatibility** — handle both
   `artifacts/kinds/<name>.json` (legacy flat) and
   `artifacts/kinds/<name>/kind.json` (folder form). Folder wins on
   collision; warning logged (s0017 § 7.1).
5. **Tests** — implement the test plan in s0017 § 9. Layer-isolation
   tests (§ 9.1) are the load-bearing surface and must not be
   skipped or relaxed.
6. **Retire `/artifacts.kinds` slash command** per s0017 § 11.6 (D10):
   - Delete `src/artifacts_os/ai/claude/commands/artifacts.kinds.md`.
   - Update `src/artifacts_os/ai/claude/commands/artifacts.create.md`
     so its \"run \`/artifacts.kinds\` first\" instruction reads \"run
     \`artifacts kinds\` first\".
   - Grep the repo for other `/artifacts.kinds` references; replace
     with `artifacts kinds` or remove if obsolete.

## Out of scope

- Anything sketched in s0017 § 11 "Next Steps" — those items live
  outside this task by design.
- Updates to `/artifacts.create` beyond the one-line CLI substitution
  in step 6 (replace `/artifacts.kinds` reference with
  `artifacts kinds`).
- Authoring-guide changes — filed as a separate documentation
  sub-task (`[[t0078-update-docs-adding-a-kind]]`).
- Per-kind `ARTIFACT.md` authoring for `task`, `spec`, `research`,
  `agent` — adjacent authoring work tracked under the epic
  (`[[t0079-artifact-md-artifacts-ai-extension]]`), not this code
  task.

## Constraints

- **Layer-isolation invariant** — L1 must not read `ARTIFACT.md`
  body content or any `playbooks/*.md` file. Tests in s0017 § 9.1
  pin this; do not relax them.
- **Backwards compatibility** — see s0017 § 8.3. No removed flags,
  output keys, or exit codes. New columns and JSON keys are
  additive.
- **Module DAG** — `KindCatalog` lives in `core` (uses `Registry`,
  no peer imports). Honour the locked DAG: `core → views → cli, tui`.
- **Atomic writes** — preserve existing `O_CREAT|O_EXCL` / `os.replace`
  invariants in `core.store` (no changes expected, but flag any
  drift).
- **Doc updates with API changes** — when `kind.json` / `ARTIFACT.md`
  loading or the CLI surface changes, update the corresponding doc
  in the same commit (per project CLAUDE.md).

## Test plan

Implement every test listed in s0017 § 9 (sub-sections 9.1 through
9.6). The token-budget test (§ 9.6) is marked optional in the spec
and may be skipped if it proves flaky against the in-repo vault.

## Deliverable

A single PR (or task-scoped commit series) that lands all six
implementation steps, with green tests.

## Progress

### 2026-05-03 00:17:26 — Incomplete run (r0094)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$1.90, turns=51

## Verification

- [x] `src/artifacts_os/core/kinds_catalog.py` exists and exposes
      `KindCatalog` + `KindCatalogEntry` per s0017 § 5.1 / § 8.1.
- [x] `Registry._load_vault_kinds` reads `ARTIFACT.md` frontmatter
      and emits the documented warnings/errors.
- [x] `artifacts kinds` table output includes a `description` column.
- [x] `artifacts kinds -j` output includes `description` and
      `has_template` keys for every kind.
- [x] `artifacts kinds -q` byte-for-byte unchanged from baseline.
- [x] Loader accepts both legacy flat `kind.json` and folder-form
      `<name>/kind.json`, folder wins on collision.
- [x] All tests in s0017 § 9.1–9.5 pass; § 9.6 either passes or is
      explicitly skipped with rationale.
- [x] `/artifacts.kinds` slash command file deleted; references in
      `artifacts.create.md` and elsewhere updated.
- [x] No regression in existing `artifacts kinds` or
      `artifacts kinds -j` consumers.
- [x] Doc updates land in the same commit as API changes (per
      project CLAUDE.md).
- [x] PR linked back to `[[s0017-artifact-kinds-discovery-mechanism]]`
      and this task.

## Verification Report

*Verified: 2026-05-03*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `kinds_catalog.py` exists, exposes `KindCatalog` + `KindCatalogEntry` per s0017 § 5.1 / § 8.1 | PASS | `src/artifacts_os/core/kinds_catalog.py` defines frozen `KindCatalogEntry(name, description, has_template)` and `KindCatalog(registry, root)` with `list_kinds() -> list[KindCatalogEntry]`; matches § 5.1 / § 8.1 verbatim. |
| 2 | `Registry._load_vault_kinds` reads `ARTIFACT.md` frontmatter and emits warnings/errors | PASS | `core/registry.py` adds `_read_artifact_md_frontmatter` (frontmatter-only) and `_validate_description` (length/XML/reserved-word checks); `_load_vault_kinds` warns on missing/empty `description`, missing ARTIFACT.md, and folder-vs-flat collision. |
| 3 | `artifacts kinds` table includes `description` column | PASS | `cli/commands/kinds.py` adds `description` column with `_DESCRIPTION_MAX_DISPLAY=60` truncation; `test_cli_table_includes_description_column` passes. |
| 4 | `artifacts kinds -j` includes `description` and `has_template` keys | PASS | JSON branch emits both new keys for every kind; `test_cli_json_keys_additive` and `test_cli_json_no_description_is_none` pass. |
| 5 | `artifacts kinds -q` byte-for-byte unchanged | PASS | `-q` branch still prints `kd.name` per line in sorted order (diffed against parent commit); `test_cli_quiet_mode_unchanged` and `test_kinds_quiet_default_four` pass. |
| 6 | Loader accepts both flat `kind.json` and folder-form `<name>/kind.json`, folder wins | PASS | `_load_vault_kinds` collects flat then folder paths (folder overwrites with warning); `test_legacy_flat_kind_json_still_loads` and `test_folder_form_wins_on_collision` pass. |
| 7 | All tests in s0017 § 9.1–9.5 pass; § 9.6 skipped with rationale | PASS | `pytest tests/core/test_kinds_catalog.py tests/cli/test_kinds.py`: 24 passed, 1 skipped (§ 9.6 with explicit rationale about chars/4 BPE estimate). |
| 8 | `/artifacts.kinds` slash command file deleted; references updated | PASS | `src/artifacts_os/ai/claude/commands/artifacts.kinds.md` no longer exists; `artifacts.create.md` line 33 reads "run `artifacts kinds` first"; remaining references are in spec/historical task files describing the retirement. |
| 9 | No regression in existing `artifacts kinds` / `-j` consumers | PASS | Pre-existing tests (`test_kinds_json_output`, `test_kinds_custom_vault_kind_appears`, `test_kinds_vault_overrides_caller_kind`, `test_kinds_mutually_exclusive_flags`) all pass; only additive changes to JSON keys per s0017 § 8.3. |
| 10 | Doc updates in same commit as API changes | PASS | Commit `4e52d6f` updates `docs/plans/2026-04-29-artifacts-claude-commands-design.md` and the `ai/claude/commands/*.md` files alongside source/test changes; authoring-guide updates (`docs/adding-a-kind.md`) explicitly deferred to `[[t0078-update-docs-adding-a-kind]]` per task scope. |
| 11 | PR / commit linked back to spec and task | PASS | Single commit `4e52d6f feat(t0076): implement L1 kinds catalogue per s0017` references spec § 5–§ 9, § 12 in body and task ID in subject; matches the "task-scoped commit series" deliverable shape. |

### Summary

11 passed, 0 failed. All verification criteria met; task ready to be marked verified.