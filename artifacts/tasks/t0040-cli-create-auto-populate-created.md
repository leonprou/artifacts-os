---
kind: task
id: t0040
name: cli-create-auto-populate-created
type: feature
status: done
assignee: developer
owner: user
created: 2026-04-30
started: 2026-04-30
completed: 2026-04-30
---

# Cli Create: Auto-Populate Created On New Artifacts

`artifacts create` does not set the `created` frontmatter field on
newly-created artifacts. As a result every artifact starts with an
empty `created`, and `artifacts validate` flags it as broken because
`core.validate._REQUIRED_KEYS` lists `created` as required.

## Requirements

1. In `cli/commands/create.py`, set `fields["created"]` to today's
   ISO date (`date.today().isoformat()`) when the user has not
   passed it explicitly via `--fields created=…`.
2. Resolution order: explicit `--fields created=YYYY-MM-DD` from
   the user → today's date.
3. The auto-populated value must appear in dry-run output as well
   as in the persisted file.
4. Apply uniformly to all kinds (numbered and non-numbered alike) —
   `created` is a base required field per `core.validate`, not a
   per-kind concern.

## Out of scope

- Auto-populating `started`, `updated`, `assignee`, `owner`, or any
  other lifecycle fields — separate tasks.
- Changing `_REQUIRED_KEYS` in `core.validate`.
- Backfilling `created` on existing artifacts that were created
  before this fix.

## Findings

`artifacts create` now sets `fields.setdefault("created", date.today())`
in `_build_fields()`. Passing the `date` object (not its `isoformat()`
string) keeps the YAML output unquoted (`created: 2026-04-30`) — PyYAML
otherwise wraps date-looking strings in quotes to disambiguate from
the YAML date scalar.

- `cli/commands/create.py`: imported `datetime.date`; one-line setdefault.
- `tests/cli/test_create.py`: 5 new tests — auto-population, explicit
  override preserved, dry-run inclusion, non-numbered kind (agent), and
  validate-passes integration check. Added `_created_str` helper to
  normalise the field whether YAML returns a `date` or `str`.
- Backfilled `artifacts/notes/n0001-test.md` so the existing test note
  validates cleanly.

All 55 cli tests pass; full suite pre-existing failure
(`test_pyproject_extras_match_spec` about `rich` extras) is unrelated.

## Progress

### 2026-04-30 — developer
> time: 17:10

Implemented `created` auto-population in `_build_fields()` using `date.today()` (date object → unquoted YAML). 5 new tests in `tests/cli/test_create.py` cover auto-pop, explicit override, dry-run, non-numbered kind, and validate-passes. Backfilled `n0001-test.md`. All 55 cli tests pass.

## Verification

- [x] `artifacts create "thing"` writes a file whose frontmatter
      contains `created: <today's ISO date>`.
- [x] `artifacts create "thing" --fields created=2024-01-15`
      preserves the explicit value (no overwrite).
- [x] `artifacts create "thing" --dry-run` shows the auto-populated
      `created` in the dry-run preview.
- [x] `artifacts validate <new-artifact>` produces 0 errors for an
      artifact created via the command after this fix.
- [x] New tests in `tests/cli/test_create.py` (or a new file) cover
      auto-population, explicit override, and dry-run inclusion.
- [x] Existing `tests/cli/test_create.py` and
      `tests/cli/test_create_kind_default.py` continue to pass.

## Verification Report

*Verified: 2026-04-30*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts create "thing"` writes `created: <today>` to frontmatter | PASS | `create.py:144` `fields.setdefault("created", date.today())`; `test_created_auto_populated` passes |
| 2 | `--fields created=YYYY-MM-DD` preserves explicit value | PASS | `setdefault` only sets when key absent; `test_created_explicit_value_preserved` passes |
| 3 | Dry-run preview shows auto-populated `created` | PASS | `_build_fields` runs before `_print_dry_run`; live `artifacts create "..." --dry-run` outputs `created: 2026-04-30` unquoted; `test_created_in_dry_run_output` passes |
| 4 | `artifacts validate` produces 0 errors for new artifacts | PASS | `test_created_makes_validate_pass` checks "1 valid, 0 with errors" in stdout — passes |
| 5 | New tests cover auto-pop, explicit override, dry-run | PASS | `tests/cli/test_create.py:288-326` adds 5 `test_created_*` tests covering all three plus non-numbered kind and validate-integration |
| 6 | Existing `test_create.py` and `test_create_kind_default.py` pass | PASS | 42/42 tests pass (32 pre-existing in `test_create.py` + 5 new + 5 in `test_create_kind_default.py`) |

### Summary

6 passed, 0 failed. All verification criteria met — task is ready to move to verified.
