---
kind: task
id: t0115
name: apply-x-layouts-to-task
type: implementation
status: done
assignee: developer
owner: developer
parent: "[[t0114-feat-tree-layout-for-art]]"
created: 2026-05-06
started: 2026-05-06
completed: 2026-05-06
---

# Apply X-Layouts To Task.Json

## User story

As a downstream consumer of `task.json`, I expect the kind
itself to declare that it forms a tree and which field carries
the upward pointer — so the renderer doesn't hardcode `parent`
and so future kinds can opt in without code changes.

## Context

- Parent: [[t0114-feat-tree-layout-for-art]].
- Spec contract: [[s0022-tree-layout]] §3 (`x-layouts` block),
  §3.1 (schema), §3.3 (registry validation), §3.4 (`meta`
  population), §11 (`x-columns` left untouched).
- Parallel-start with [[Tree renderer in views]] (sibling
  sub-task). Their join is the CLI wiring task.

## Requirements

Apply only what spec §3 specifies. Do not invent additional
schema. Do not modify any kind file other than `task.json` in
this task.

1. Add the `x-layouts` block to `artifacts/kinds/task.json` per
   spec §3.1, declaring `default: "tree"` and
   `tree.parent_field: "parent"`.
2. Validate the block at registry load (spec §3.3). Surface a
   loud error for unknown fields, missing `default`, or a
   `parent_field` that does not exist in the kind's frontmatter
   schema.
3. Populate `KindDef.meta["layouts"]` per spec §3.4 so the
   `views/` layer can consume it without re-parsing JSON.
4. `x-columns` stays exactly as it is. No migration this task
   (spec §11).
5. Tests cover: valid block parses, invalid block rejects, kinds
   without `x-layouts` keep working unchanged.

## Verification

- [x] `task.json` contains the `x-layouts` block per spec §3.1.
- [x] Registry rejects malformed `x-layouts` with the error
      shape spec §3.3 specifies.
- [x] `KindDef.meta["layouts"]` is populated and matches §3.4.
- [x] No other `kinds/*.json` file modified.
- [x] `x-columns` on `task.json` byte-unchanged.
- [x] New tests pass; existing kind tests pass unchanged.

## Verification Report

*Verified: 2026-05-06*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `task.json` contains `x-layouts` per §3.1 | PASS | Block present: `{"default":"tree","tree":{"parent_field":"parent"}}` |
| 2 | Registry rejects malformed `x-layouts` per §3.3 | PASS | `_validate_and_parse_layouts` raises `ValidationError` for unknown default, missing tree block, bad `parent_field` |
| 3 | `KindDef.meta["layouts"]` populated per §3.4 | PASS | Live vault load returns `{'default': 'tree', 'tree': {'parent_field': 'parent'}}` |
| 4 | No other `kinds/*.json` modified | PASS | `git diff` shows only `artifacts/kinds/task.json` changed in kinds/ |
| 5 | `x-columns` byte-unchanged | PASS | Still `["id", "name", "status", "assignee"]` |
| 6 | New tests pass; existing tests pass unchanged | PASS | 20/20 registry tests pass; 8 new, 12 pre-existing |

### Summary

6 passed, 0 failed. All verification criteria satisfied.

## Progress

### 2026-05-06 — developer
> time: 19:05

Implemented x-layouts block in task.json, validation in registry.py, meta population, and 8 new tests. All 20 registry tests pass.

## Findings

Three files changed; one kind file modified.

- **`artifacts/kinds/task.json`** — added `x-layouts` block between
  `x-columns` and `x-status-colors`. `x-columns` is byte-unchanged.
  Declares `default: "tree"` and `tree.parent_field: "parent"` per §3.1.

- **`src/artifacts_os/core/registry.py`** — added `_KNOWN_LAYOUTS`
  constant (`{"table", "tree"}`) and `_validate_and_parse_layouts()`
  helper. The helper runs the three §3.3 checks (unknown default, missing
  `tree` block when `default == "tree"`, `parent_field` not a property)
  and returns the parsed dict. `_load_vault_kinds` calls it when
  `x-layouts` is present and stores the result in `meta["layouts"]`.
  Kinds without `x-layouts` are unaffected.

- **`tests/core/test_registry.py`** — 8 new tests covering: valid parse,
  absent block (no side-effect), unknown default, missing tree block,
  `parent_field` missing from schema, `parent_field` wrong type, `table`
  default without tree block (valid), and non-object `x-layouts` value.
  All 20 registry tests pass; full suite adds no new failures beyond the
  4 pre-existing `test_release_changelog_skill` failures.
