---
kind: task
id: t0013
name: implement-artifacts-validate-command
type: implementation
status: done
assignee: developer
owner: user
created: 2026-04-23
started: 2026-04-23
completed: 2026-04-25
---

# Implement Artifacts Validate Command

## Requirements

Implement the `artifacts validate` command per `artifacts/specs/s0008-artifact-validate-command.md`. Six files to create or edit:

**Create `src/artifacts_os/core/validate.py`**
- `ValidationIssue` and `ValidationResult` dataclasses as specified
- `validate_one(meta, registry) -> ValidationResult` — pure function, no I/O
- `validate_many(metas, registry) -> list[ValidationResult]`
- All six validation rules applied in order, issues accumulated (not short-circuited)

**Edit `src/artifacts_os/core/__init__.py`**
- Export `validate_one`, `validate_many`, `ValidationIssue`, `ValidationResult`

**Create `src/artifacts_os/cli/commands/validate.py`**
- `register(subparsers)` — argparse wiring as specified
- `run(args, registry) -> int` — thin dispatch, delegates to core
- `_apply_fixes` calls `core.update`; `--dry-run` prints only
- `_print_table` and `_print_json` output formatters

**Edit `src/artifacts_os/cli/__init__.py`**
- Import and register `validate` command

**Create `tests/core/test_validate.py`**
- All 14 unit test cases from the spec's test matrix

**Create `tests/cli/test_validate_cmd.py`**
- All 9 integration test cases from the spec's test matrix

## Verification

- [x] `core/validate.py` exists with `validate_one`, `validate_many`, and both dataclasses
- [x] `validate_one` is a pure function (no file I/O)
- [x] All six rules implemented; issues accumulated, not short-circuited
- [x] `severity="error"` issues trigger exit 2; warnings alone exit 0
- [x] `--fix` corrects bad `status` via `core.update`; no other fields auto-fixed
- [x] `--dry-run` produces no writes
- [x] `--fix` and `--dry-run` are mutually exclusive at parse time
- [x] Rich table output matches spec format (severity marker, `[fixable]` tag)
- [x] JSON output matches spec schema (name, kind, issues with field/message/fixable/severity)
- [x] `pytest tests/core/test_validate.py` passes (all 14 cases)
- [x] `pytest tests/cli/test_validate_cmd.py` passes (all 9 cases)
- [x] `validate_one`, `validate_many` exported from `core/__init__.py`
- [x] Command registered in `cli/__init__.py` alongside existing commands

## Verification Report

*Verified: 2026-04-25*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `core/validate.py` exists with `validate_one`, `validate_many`, and both dataclasses | PASS | File present; all four symbols defined |
| 2 | `validate_one` is a pure function (no file I/O) | PASS | Docstring states "Pure function; no I/O"; no file ops in body |
| 3 | All six rules implemented; issues accumulated, not short-circuited | PASS | All six rules present in validate.py; `test_multiple_violations_accumulated` passes |
| 4 | `severity="error"` issues trigger exit 2; warnings alone exit 0 | PASS | `run()` returns `2 if has_errors else 0`; `test_vault_with_only_warnings_returns_0` passes |
| 5 | `--fix` corrects bad `status` via `core.update`; no other fields auto-fixed | PASS | `_apply_fixes` calls `update()` for status only; `test_fix_does_not_touch_warnings` passes |
| 6 | `--dry-run` produces no writes | PASS | `update()` never called under `dry_run`; `test_dry_run_does_not_write` passes |
| 7 | `--fix` and `--dry-run` are mutually exclusive at parse time | PASS | Both added to `add_mutually_exclusive_group()` in `register()` |
| 8 | Rich table output matches spec format (severity marker, `[fixable]` tag) | PASS | `_print_table` uses `E`/`W` markers and `[fixable]` tag |
| 9 | JSON output matches spec schema (name, kind, issues with field/message/fixable/severity) | PASS | `_print_json` emits all required keys per entry |
| 10 | `pytest tests/core/test_validate.py` passes (all 14 cases) | PASS | 15/15 tests pass (15 implemented, all green) |
| 11 | `pytest tests/cli/test_validate_cmd.py` passes (all 9 cases) | PASS | 9/9 tests pass |
| 12 | `validate_one`, `validate_many` exported from `core/__init__.py` | PASS | Both in `__all__` alongside `ValidationIssue`, `ValidationResult` |
| 13 | Command registered in `cli/__init__.py` alongside existing commands | PASS | `_validate_cmd` imported and `register()` called in `_build_parser()` |

### Summary

13 passed, 0 failed. All verification criteria met.

## Findings

All six files implemented from scratch. 24 tests pass (15 unit + 9 CLI); full suite 143/143.

**What was built:**
- `src/artifacts_os/core/validate.py` — pure validation logic with `ValidationIssue`, `ValidationResult` dataclasses and all six rules. Uses `jsonschema.Draft7Validator.iter_errors()` to collect all schema violations in one pass. Rule 5 skips the `status` field when `KindDef.statuses` is non-empty to avoid double-reporting the rule-3 status error.
- `src/artifacts_os/cli/commands/validate.py` — thin CLI dispatch. `_apply_fixes` calls `core.update` then mutates `result.issues` in-place, so the exit-code check after `--fix` reflects the corrected state without re-reading files.
- `src/artifacts_os/core/__init__.py` — added exports for `validate_one`, `validate_many`, `ValidationIssue`, `ValidationResult`.
- `src/artifacts_os/cli/__init__.py` — imported and registered `validate` command.

**Key design decision:** `--fix` only corrects `status` (sets to `statuses[0]`); unknown-field warnings are never auto-corrected, matching the spec's fix table exactly.
