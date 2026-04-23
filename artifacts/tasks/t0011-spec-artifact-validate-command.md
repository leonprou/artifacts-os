---
kind: task
id: t0011
name: spec-artifact-validate-command
type: spec
status: done
assignee: architect
owner: user
created: 2026-04-23
started: 2026-04-23
artifacts:
  - "[[openstation/specs/s0008-artifact-validate-command]]"
completed: 2026-04-23
---

# Spec Artifact Validate Command

## Context

`artifacts verify` (existing) checks task *completeness* via markdown body checklists — it is correctly named. A separate `artifacts validate` command is needed for structural correctness: validating frontmatter fields against a `KindDef.schema`, catching missing required fields, bad status values, and malformed slugs/IDs — without touching the body.

This is the schema-linting concern identified in t0006 downstream.

## Requirements

1. **New `validate` subcommand** in `src/artifacts_os/cli/commands/validate.py`, registered alongside existing commands.

2. **Scope** — operates on frontmatter only; never reads or modifies body.

3. **Validation rules** applied to each artifact:
   - Required frontmatter keys present (`id`, `kind`, `title`, `created`)
   - `status` is in `KindDef.statuses` (if the kind defines statuses)
   - `id` matches expected format for the kind (`prefix + NNNN` for numbered kinds, or slug for non-numbered)
   - All fields in `KindDef.schema` pass their declared constraints (type, enum, pattern)

4. **Interface:**
   ```
   artifacts validate [<ref>] [--kind KIND] [--all] [--fix] [--dry-run] [-j]
   ```
   - No args + no `--all` → validates the current vault (all artifacts)
   - `<ref>` → single artifact
   - `--all` → all artifacts (explicit, same as no args)
   - `--kind KIND` → filter by kind
   - `--fix` → auto-correct fixable issues (unknown status → `backlog`, malformed slug → corrected slug); writes via `core.update`
   - `--dry-run` → show what `--fix` would change without writing
   - `-j` → JSON output

5. **Exit codes** — consistent with existing CLI:
   - `0` → all valid
   - `2` (`ValidationError`) → one or more artifacts failed validation
   - `3` → ref not found

6. **Output** — rich table by default: artifact name, issue count, list of issue messages per artifact. JSON: array of `{name, kind, issues: [{field, message}]}`.

7. **Core logic** lives in `core.validate` (new function in `core/__init__.py` and a new `core/validate.py`) — CLI is a thin dispatch layer; no validation logic in the command itself.

8. **No lifecycle logic** in the command — `--fix` calls `core.update`, not direct file writes.

## Progress

### 2026-04-23 — architect
> time: 22:06

Produced spec s0008 covering data models, validation rules, CLI interface, fix behaviour, and test strategy. Transitioning to review.

### 2026-04-23 — architect
> time: 22:30

Amended s0008 to add an `error`/`warning` severity axis per review feedback. Added rule 6 (unknown fields → warning, skipped when `additionalProperties: false`), updated exit-code logic so warnings don't fail (exit 0), updated JSON/table outputs to include `severity`, expanded test matrix.

## Findings

Produced **[[openstation/specs/s0008-artifact-validate-command]]** — a complete design spec for the `artifacts validate` command.

Key design decisions:

- **`validate_one` is a pure function** (no I/O): takes an `ArtifactMeta` and `Registry`, returns `ValidationResult`. Keeps core logic fully unit-testable without fixtures.
- **Two new dataclasses** in `core/validate.py`: `ValidationIssue` (field, message, fixable) and `ValidationResult` (name, kind, issues list). `fixable` flag drives `--fix` dispatch in the CLI without leaking decision logic into the command.
- **Six validation rules** applied in order, all accumulated per artifact: required keys, kind resolution, status legality, ID format, JSON Schema constraints, unknown-field detection. Schema violations delegate to `jsonschema` (already a dependency via `store.py`).
- **Severity axis (`error` vs `warning`)**: errors fail validation (exit 2); warnings (currently only unknown-field detection) appear in output but exit 0. Composes cleanly with a future `--strict` flag.
- **Rule 6 skips itself** when `KindDef.schema.additionalProperties == false` — rule 5 already reports those keys as schema errors, so we avoid double-reporting.
- **Only `status` is auto-fixable** (set to `KindDef.statuses[0]`). ID reformatting and schema violations require human intervention.
- **`--fix` and `--dry-run` are mutually exclusive** at argparse level.
- **CLI dispatch** follows the existing pattern: thin `run()` function, exit codes via return value, errors handled by the top-level `_run` handler in `cli/__init__.py`.
- **File map** identifies six files to create or edit; see spec § File Map.

## Downstream

- A developer task should be created to implement `core/validate.py`, `cli/commands/validate.py`, and the associated tests per the spec.
- `docs/` (CLI reference) will need a `validate` entry added after implementation.

## Verification Report

*Verified: 2026-04-23*

> Note: task has no `## Verification` checklist; criteria derived from `## Requirements`.

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `cli/commands/validate.py` specified with `register()` + `run()` and registered in `cli/__init__.py` | PASS | File Map lists both as Create/Edit; `_validate_cmd.register(subparsers)` shown in Registration section |
| 2 | Spec operates on frontmatter only; body never touched | PASS | Scope Boundary table: body content explicitly out of scope; motivation repeats "without ever reading or touching the body" |
| 3 | All four validation rules covered: required keys, status legality, ID format, schema constraints | PASS | Rules 1–5 cover all four; rule 6 adds warning-severity unknown-field detection as bonus |
| 4 | Interface matches spec: `<ref>`, `--kind`, `--all`, `--fix`, `--dry-run`, `-j` | PASS | Full argparse block shown; all flags documented; note: req listed "malformed slug → corrected slug" as fixable but spec makes a deliberate documented decision to skip ID auto-fix (file rename risk), justified in Decisions table |
| 5 | Exit codes: 0 (valid), 2 (errors), 3 (ref not found) | PASS | Exit Codes table in CLI section; code 3 via `NotFoundError` caught by top-level handler |
| 6 | Output: rich table by default; JSON `{name, kind, issues: [{field, message}]}` | PASS | Both output formats specified with concrete examples; JSON is a superset of required fields (adds `fixable`, `severity`) |
| 7 | Core logic in `core/validate.py`; exported from `core/__init__.py`; CLI is thin dispatch | PASS | `validate_one`/`validate_many` in `core/validate.py` (pure functions); export block shown; CLI `run()` delegates entirely to core |
| 8 | `--fix` calls `core.update`, not direct file writes; no lifecycle logic in command | PASS | Fix Behaviour: "`validate_one` never writes. The CLI calls `core.update`"; dispatch code confirms `_apply_fixes` calls `core.update(registry, name, fields={...})` |

### Summary

8 passed, 0 failed. Spec fully satisfies all requirements; one requirement deviation (ID auto-fix) is explicitly documented with justification in the Decisions section.

### Artifact Check

- `[[openstation/specs/s0008-artifact-validate-command.md]]` — file exists and is complete ✅
