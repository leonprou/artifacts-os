---
assignee: developer
created: 2026-04-26
id: t0020
kind: task
name: rename-artifacts-types-to-artifacts
owner: project-manager
started: 2026-04-26
status: done
type: implementation
---

# Rename `artifacts/types/` → `artifacts/kinds/` and Standardize on "Kind"

## Background

The codebase already calls the artifact-classification concept a
**kind** everywhere it matters:

- `KindDef` is the model class
- The frontmatter field is `kind:`
- The CLI flag is `--kind`
- The registry methods are `get(kind)`, `all()`, `for_dir()`, and
  internally use `_kinds` / `_load_vault_kinds`
- `artifacts list -k` filters by kind

The only place the word "type" leaks in for this concept is the
**directory name** `artifacts/types/`, inherited from openstation
where it was named to match the JSON-Schema `type` keyword. This
forces every doc to say "kinds are loaded from `types/`" — a
real footgun for new contributors.

This task fixes the inconsistency in one pass: rename the directory
to `artifacts/kinds/` and update every source/test/docs reference
that named the path. It does **not** rename anything else (the
JSON-Schema `type` keyword inside the kind files is unrelated and
must stay).

## What to change and what to leave alone

**Change** — every reference to `artifacts/types/` (or `"types"` as
the literal directory name in code) that points at the kind-schemas
directory.

**Leave alone:**
- The JSON-Schema `"type": ...` keyword inside the kind schema files
  (`artifacts/kinds/*.json`) — that is JSON Schema syntax, not our
  concept.
- The `--type` flag on `openstation create` (and the `type:` task
  frontmatter field — `feature|research|spec|implementation|documentation`).
  That is OpenStation's task-type taxonomy, a separate concept.
- Python `type()`, type annotations, mypy, etc.
- Historical references in already-completed task files
  (`artifacts/tasks/t0010-*.md`, `artifacts/tasks/t0014-*.md`) and
  any `artifacts/logs/*.jsonl` — these are immutable history.

---

## Requirements

### 1. Move the directory

```
git mv artifacts/types artifacts/kinds
```

The four schema files (`agent.json`, `research.json`, `spec.json`,
`task.json`) move with it. No content changes inside the JSON.

### 2. Source — 3 files

| File | Change |
|------|--------|
| `src/artifacts_os/core/registry.py` | Line 45: `root / "artifacts" / "types"` → `root / "artifacts" / "kinds"`. Update local var name `types_dir` → `kinds_dir`. Update any docstring/comments referring to `types/`. |
| `src/artifacts_os/cli/commands/init.py` | Lines 113, 122, 136: rename `types_dir` → `kinds_dir`, change directory literal `"types"` → `"kinds"`, and update the printed line `artifacts/types/  (N kinds)` → `artifacts/kinds/  (N kinds)`. The comment on line 111 ("with kind subdirs, types, and vault marker") should read "with kind subdirs, kind schemas, and vault marker". |
| `src/artifacts_os/core/README.md` | Line 61: `openstation/types/*.json` → `artifacts/kinds/*.json` (also fixes the stale `openstation/` path). |

### 3. Tests — 3 files

| File | Change |
|------|--------|
| `tests/cli/test_init.py` | Lines 16, 30: `tmp_path / "artifacts" / "types"` → `tmp_path / "artifacts" / "kinds"`. Rename local `types_dir` → `kinds_dir`. |
| `tests/cli/conftest.py` | Line 37: `root / "artifacts" / "types"` → `root / "artifacts" / "kinds"`. Rename local `types_dir` → `kinds_dir`. |
| `tests/core/test_registry.py` | Line 11: `root / "artifacts" / "types"` → `root / "artifacts" / "kinds"`. Rename local `types` → `kinds_dir`. Update any docstring/help text. |

### 4. Docs

| File | Change |
|------|--------|
| `docs/2026-04-20-artifacts-os-design.md` | Update every `artifacts/types/` → `artifacts/kinds/` (lines 74, 126, 146, 148, 254). In the layout diagram (around line 94), `types/  # user-defined kind schemas` → `kinds/  # user-defined kind schemas`. The phrase "vault types/ scan" → "vault kinds/ scan" (lines 62, 120, 451 of s0002). Example filename `artifacts/types/changelog.json` → `artifacts/kinds/changelog.json`. |
| `artifacts/specs/s0002-artifacts-os-architecture.md` | Lines 213, 232, 451: `artifacts/types/*.json` and `vault types/ scan` → `artifacts/kinds/*.json` and `vault kinds/ scan`. |

### 5. Validate the new contract

Add an explicit assertion in `tests/core/test_registry.py` (or extend
an existing test) that scanning `artifacts/types/` is **not** a
fallback — only `artifacts/kinds/` is recognized. This locks in the
rename and prevents accidental dual-path support.

### 6. CLAUDE.md

Project root `CLAUDE.md` does not currently reference the directory.
No change needed unless the audit finds a new reference; if so, fix
it in the same task.

---

## Out of Scope

- Adding an `artifacts kinds` subcommand to the CLI. That was discussed
  alongside this rename but is a separate piece of work. File a
  follow-up task in `## Downstream` if desired.
- Renaming the `--type` flag on `openstation create` or the `type:`
  task frontmatter field.
- Touching any `.openstation/` framework files (commands, skills,
  docs) — they speak about openstation tasks, not artifacts-os
  kinds.

---

## Verification

- [x] `artifacts/kinds/` exists and contains the four JSON schemas; `artifacts/types/` no longer exists
- [x] `git log --follow artifacts/kinds/task.json` shows continuity from the old path (i.e. `git mv` was used, not delete + add)
- [x] `grep -rn "artifacts/types" src/ tests/ docs/ artifacts/specs/` returns no matches
- [x] `grep -rn '"types"' src/ tests/` returns no matches that refer to the kind-schemas directory
- [x] `src/artifacts_os/core/registry.py` loads kinds from `artifacts/kinds/`
- [x] `src/artifacts_os/cli/commands/init.py` creates `artifacts/kinds/` on init and prints the new path in the success output
- [x] `src/artifacts_os/core/README.md` references `artifacts/kinds/*.json` (no stale `openstation/types/`)
- [x] `docs/2026-04-20-artifacts-os-design.md` and `artifacts/specs/s0002-artifacts-os-architecture.md` use `kinds/` consistently
- [x] `pytest` — all tests pass
- [x] `artifacts init` in a fresh tmp dir produces `artifacts/kinds/` (not `artifacts/types/`)
- [x] `artifacts list -k task -q` still works (smoke test against this repo after rename)
- [x] JSON-Schema `"type":` keywords inside `artifacts/kinds/*.json` are untouched
- [x] The `--type` flag on `openstation create` and the `type:` task frontmatter field are untouched

## Verification Report

*Verified: 2026-04-26*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts/kinds/` exists with 4 schemas; `artifacts/types/` gone | PASS | `ls artifacts/kinds/` → agent.json research.json spec.json task.json; `ls artifacts/types/` → no such directory |
| 2 | `git log --follow` shows history continuity (git mv used) | PASS | 3-commit history visible: initial commit → validate fixes → rename commit |
| 3 | No `artifacts/types` references in src/tests/docs/specs | PASS | Only match is in `test_types_dir_is_not_scanned` docstring (intentional contract test, proves old path is rejected) |
| 4 | No `"types"` matches referring to kind-schemas dir | PASS | Match at test_registry.py:98 creates `artifacts/types/` only to assert it's NOT scanned — not a functional reference |
| 5 | `registry.py` loads from `artifacts/kinds/` | PASS | Line 45: `kinds_dir = root / "artifacts" / "kinds"` |
| 6 | `init.py` creates `artifacts/kinds/` and prints new path | PASS | Prints `artifacts/kinds/  (4 kinds)`; uses `kinds_dir` var throughout |
| 7 | `core/README.md` references `artifacts/kinds/*.json` | PASS | Line 61: `kinds loaded from \`artifacts/kinds/*.json\`` |
| 8 | Both docs use `kinds/` consistently | PASS | design doc (5 occurrences) and s0002 (3 occurrences) all use `kinds/` |
| 9 | `pytest` — all tests pass | PASS | 145 passed in 0.54s |
| 10 | `artifacts init` produces `artifacts/kinds/` not `artifacts/types/` | PASS | Fresh tmp dir init: `artifacts/kinds/  (4 kinds)`; `ls artifacts/types/` → not found |
| 11 | `artifacts list -k task -q` works | PASS | Returns task list successfully |
| 12 | JSON-Schema `"type":` keywords inside kind files untouched | PASS | All 4 files contain `"type": "object"` unchanged |
| 13 | `--type` flag and `type:` frontmatter field untouched | PASS | `openstation create --help` shows `--type TYPE` intact |

### Summary

13 passed, 0 failed. All verification criteria met — rename is complete and consistent.

## Findings

All requirements implemented in a single atomic commit (`6200757`).

- `git mv artifacts/types artifacts/kinds` — four JSON schemas moved with git history preserved (rename tracked by git).
- **Source** — `registry.py` now scans `artifacts/kinds/`; `init.py` creates `artifacts/kinds/`, prints `artifacts/kinds/  (4 kinds)`, and uses `kinds_dir` variable throughout; `core/README.md` corrected from stale `openstation/types/` to `artifacts/kinds/`.
- **Tests** — `tests/cli/conftest.py`, `tests/cli/test_init.py`, `tests/core/test_registry.py` all updated; `_write_schema` helper uses `kinds_dir`; existing `test_vault_types_scan` renamed to `test_vault_kinds_scan`.
- **Contract test** — `test_types_dir_is_not_scanned` added: places a schema only in `artifacts/types/` and asserts the registry does NOT load it, locking in the single-path contract.
- **Docs** — `docs/2026-04-20-artifacts-os-design.md` (5 occurrences) and `artifacts/specs/s0002-artifacts-os-architecture.md` (3 occurrences) updated. JSON-Schema `"type":` keywords inside kind files left untouched.
- 145 tests pass; `artifacts init` and `artifacts list -k task -q` both work correctly after the rename.