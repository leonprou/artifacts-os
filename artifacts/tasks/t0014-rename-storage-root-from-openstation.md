---
kind: task
id: t0014
name: rename-storage-root-from-openstation
type: feature
status: verified
assignee: developer
owner: user
created: 2026-04-23
summary: >
  Replace all hardcoded openstation/ storage root references with
  artifacts/ across source, tests, and docs.
started: 2026-04-23
---

# Rename Storage Root: openstation/ → artifacts/ in Source, Tests, and Docs

## Background

`init` already creates the correct layout: `.openstation/` is the vault
marker, `artifacts/` is the storage root, and `openstation → artifacts` is
a compat symlink. The code and docs have not caught up — they still
reference `openstation/` (no dot) as the storage root.

Flagged in `t0001` Downstream section.

## What to change and what to leave alone

**Change** — `openstation/` when used as the **storage root** (tasks, specs,
agents, research, types, logs). These should become `artifacts/`.

**Leave alone** — `.openstation/` (with dot) used as the **vault marker**,
and `openstation` as the **CLI tool name** (commands like
`openstation list`, `openstation status`, wikilinks that reference the
`openstation` CLI binary, skill/command names like `/openstation.done`).

---

## Requirements

### 1. Source — 3 locations

| File | Line | Before | After |
|------|------|--------|-------|
| `src/.../core/discover.py` | 29 | `/ "openstation" / kd.dir` | `/ "artifacts" / kd.dir` |
| `src/.../core/store.py` | 32 | `/ "openstation" / kd.dir` | `/ "artifacts" / kd.dir` |
| `src/.../core/registry.py` | 45 | `/ "openstation" / "types"` | `/ "artifacts" / "types"` |

`vault.py` — no change (looks for `.openstation/` marker, correct as-is).  
`init.py` — no change (creates `artifacts/` and the compat symlink, correct as-is).

### 2. Tests

**`tests/core/conftest.py`**
- Line 43: `(root / "openstation").mkdir()` → `(root / "artifacts").mkdir()`
- Line 46: `(root / "openstation" / kd.dir).mkdir(...)` → `(root / "artifacts" / kd.dir).mkdir(...)`

**`tests/core/test_registry.py`**
- `_write_schema`: `root / "openstation" / "types"` → `root / "artifacts" / "types"`

**`tests/core/test_store.py`**
- Line 15 (assertion): `root / "openstation" / "tasks"` → `root / "artifacts" / "tasks"`
- Line 49 (setup): `(root / "openstation" / "tasks").mkdir(...)` → `(root / "artifacts" / "tasks").mkdir(...)`

**`tests/cli/conftest.py`**
- Line 38: `root / "openstation" / "types"` → `root / "artifacts" / "types"`
- Line 44: `root / "openstation" / kind_dir` → `root / "artifacts" / kind_dir`
- Line 58: `root / "openstation" / kind_dir / filename` → `root / "artifacts" / kind_dir / filename`

**`tests/cli/test_create.py`**
- Lines 13, 27, 35, 45: `vault / "openstation" / ...` → `vault / "artifacts" / ...`

**`tests/cli/test_status.py`**
- Lines 19, 29: `vault / "openstation" / "tasks" / ...` → `vault / "artifacts" / "tasks" / ...`

**`tests/cli/test_validate_cmd.py`**
- Line 104: `vault / "openstation" / "tasks" / ...` → `vault / "artifacts" / "tasks" / ...`

### 3. Docs

**`docs/2026-04-20-artifacts-os-design.md`**
- Layout diagram: replace `openstation/` storage entries with `artifacts/`
- Prose: `openstation/types/` → `artifacts/types/` (3 occurrences)
- `x-dir` table note: "Subdirectory under `openstation/`" → "Subdirectory under `artifacts/`"
- Example filename: `openstation/types/changelog.json` → `artifacts/types/changelog.json`
- Registry docstring: `root/openstation/types/*.json` → `root/artifacts/types/*.json`

**`.openstation/docs/storage-query-layer.md`**
- All `openstation/` storage path references → `artifacts/`
  (tasks, agents, research, specs, logs directories and example paths)
- Agent symlink example: `openstation/agents/researcher.md` → `artifacts/agents/researcher.md`

**`.openstation/skills/openstation-execute/SKILL.md`**
- "Store new artifacts in the appropriate `openstation/<category>/`" → `artifacts/<category>/`
- Wikilink examples: `[[openstation/research/...]]`, `[[openstation/agents/...]]` → `[[artifacts/...]]`
- Artifact routing table: `openstation/research/`, `openstation/agents/`, etc. → `artifacts/...`
- "stored under `openstation/`" → "stored under `artifacts/`"
- Fallback scan path: `openstation/tasks/*.md` → `artifacts/tasks/*.md`
- Direct file read example: `openstation/tasks/<task-name>.md` → `artifacts/tasks/<task-name>.md`
- Log path example: `openstation/logs/<task-name>.jsonl` → `artifacts/logs/<task-name>.jsonl`

**`.openstation/commands/openstation.list.md`**
- Line 63: fallback scan `openstation/tasks/*.md` → `artifacts/tasks/*.md`

**`artifacts/specs/s0002-artifacts-os-architecture.md`**
- `dir` field comment: "subdirectory under openstation/" → "subdirectory under artifacts/"
- Registry docstring: `root/openstation/types/*.json` → `root/artifacts/types/*.json`
- `_load_vault_kinds` step: `root/openstation/types/` → `root/artifacts/types/`
- `list_artifacts`: `registry.root/openstation/{kd.dir}/` → `registry.root/artifacts/{kd.dir}/`
- `make_vault` fixture doc: `openstation/{kind.dir}/` → `artifacts/{kind.dir}/`

**`artifacts/specs/s0004-artifacts-os-log-module.md`**
- Line 92: `openstation/logs/` → `artifacts/logs/`

---

## Progress

### 2026-04-23 23:16:13 — Incomplete run (r0018)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$1.74, turns=51

## Findings

All `openstation/` storage root references replaced with `artifacts/` across source, tests, and docs. All 144 tests pass.

**Source changes (3 files):** `discover.py`, `store.py`, `registry.py` — `_kind_dir` and `_load_vault_kinds` now use `"artifacts"` instead of `"openstation"`.

**Test changes (7 files):** `tests/core/conftest.py`, `test_registry.py`, `test_store.py`, `tests/cli/conftest.py`, `test_create.py`, `test_status.py`, `test_validate_cmd.py` — fixtures and assertions updated to `artifacts/`.

**Docs changes (6 files):** `docs/2026-04-20-artifacts-os-design.md`, `.openstation/docs/storage-query-layer.md`, `.openstation/skills/openstation-execute/SKILL.md`, `.openstation/commands/openstation.list.md`, `artifacts/specs/s0002-artifacts-os-architecture.md`, `artifacts/specs/s0004-artifacts-os-log-module.md`.

`vault.py` and `init.py` left unchanged as specified.

## Verification

- [x] `src/.../core/discover.py` has no `/ "openstation"` (storage usage)
- [x] `src/.../core/store.py` has no `/ "openstation"` (storage usage)
- [x] `src/.../core/registry.py` has no `/ "openstation"` (storage usage)
- [x] `vault.py` and `init.py` are unchanged
- [x] All tests pass: `pytest`
- [x] Test fixtures create `artifacts/` dirs, not `openstation/` dirs
- [x] Test assertions reference `artifacts/` paths
- [x] `docs/2026-04-20-artifacts-os-design.md` layout and prose updated
- [x] `.openstation/docs/storage-query-layer.md` paths updated
- [x] `.openstation/skills/openstation-execute/SKILL.md` routing table and examples updated
- [x] `.openstation/commands/openstation.list.md` fallback path updated
- [x] `artifacts/specs/s0002-artifacts-os-architecture.md` updated
- [x] `artifacts/specs/s0004-artifacts-os-log-module.md` updated
- [x] No remaining `/ "openstation"` or `` `openstation/` `` (storage meaning) in any changed file

## Verification Report

*Verified: 2026-04-25*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `discover.py` has no `/ "openstation"` | PASS | Grep on `src/` returns no matches |
| 2 | `store.py` has no `/ "openstation"` | PASS | Same grep, no matches |
| 3 | `registry.py` has no `/ "openstation"` | PASS | Same grep, no matches |
| 4 | `vault.py` and `init.py` unchanged | PASS | `vault.py` only contains `.openstation` (vault marker); `init.py` creates `artifacts/` and compat symlink as before |
| 5 | All tests pass | PASS | `pytest` — 144 passed in 0.51s |
| 6 | Test fixtures use `artifacts/` dirs | PASS | `tests/core/conftest.py:43,46` and `tests/cli/conftest.py:38,44` confirmed |
| 7 | Test assertions reference `artifacts/` paths | PASS | No storage `openstation/` paths remain in any test file |
| 8 | `docs/2026-04-20-artifacts-os-design.md` updated | PASS | Only `.openstation/` vault marker refs remain |
| 9 | `.openstation/docs/storage-query-layer.md` updated | PASS | Only `.openstation/` framework plumbing refs remain |
| 10 | `openstation-execute/SKILL.md` updated | PASS | Only `.openstation/docs/` (vault marker) ref remains — correct |
| 11 | `openstation.list.md` updated | PASS | No `openstation/` matches |
| 12 | `s0002-artifacts-os-architecture.md` updated | PASS | Only `.openstation/` vault marker ref; `artifacts/{kind.dir}/` confirmed |
| 13 | `s0004-artifacts-os-log-module.md` updated | PASS | No `openstation/` matches |
| 14 | No remaining storage-meaning `openstation/` refs | PASS | All remaining matches are `.openstation/` (vault marker) or CLI tool name |

### Summary

14 passed, 0 failed. All criteria met.
