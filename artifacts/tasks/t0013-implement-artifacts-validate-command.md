---
kind: task
id: t0013
name: implement-artifacts-validate-command
type: implementation
status: review
assignee: developer
owner: user
created: 2026-04-23
started: 2026-04-23
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

- [ ] `core/validate.py` exists with `validate_one`, `validate_many`, and both dataclasses
- [ ] `validate_one` is a pure function (no file I/O)
- [ ] All six rules implemented; issues accumulated, not short-circuited
- [ ] `severity="error"` issues trigger exit 2; warnings alone exit 0
- [ ] `--fix` corrects bad `status` via `core.update`; no other fields auto-fixed
- [ ] `--dry-run` produces no writes
- [ ] `--fix` and `--dry-run` are mutually exclusive at parse time
- [ ] Rich table output matches spec format (severity marker, `[fixable]` tag)
- [ ] JSON output matches spec schema (name, kind, issues with field/message/fixable/severity)
- [ ] `pytest tests/core/test_validate.py` passes (all 14 cases)
- [ ] `pytest tests/cli/test_validate_cmd.py` passes (all 9 cases)
- [ ] `validate_one`, `validate_many` exported from `core/__init__.py`
- [ ] Command registered in `cli/__init__.py` alongside existing commands

## Findings

All six files implemented from scratch. 24 tests pass (15 unit + 9 CLI); full suite 143/143.

**What was built:**
- `src/artifacts_os/core/validate.py` — pure validation logic with `ValidationIssue`, `ValidationResult` dataclasses and all six rules. Uses `jsonschema.Draft7Validator.iter_errors()` to collect all schema violations in one pass. Rule 5 skips the `status` field when `KindDef.statuses` is non-empty to avoid double-reporting the rule-3 status error.
- `src/artifacts_os/cli/commands/validate.py` — thin CLI dispatch. `_apply_fixes` calls `core.update` then mutates `result.issues` in-place, so the exit-code check after `--fix` reflects the corrected state without re-reading files.
- `src/artifacts_os/core/__init__.py` — added exports for `validate_one`, `validate_many`, `ValidationIssue`, `ValidationResult`.
- `src/artifacts_os/cli/__init__.py` — imported and registered `validate` command.

**Key design decision:** `--fix` only corrects `status` (sets to `statuses[0]`); unknown-field warnings are never auto-corrected, matching the spec's fix table exactly.
