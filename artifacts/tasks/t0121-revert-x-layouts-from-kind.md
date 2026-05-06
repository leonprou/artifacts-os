---
kind: task
id: t0121
name: revert-x-layouts-from-kind
type: implementation
status: done
assignee: developer
owner: developer
parent: "[[t0114-feat-tree-layout-for-art]]"
created: 2026-05-06
started: 2026-05-06
completed: 2026-05-07
---

# Revert-X-Layouts-From-Kind-Schema

## User story

Kind files should not carry layout configuration. Remove the
`x-layouts` block from `task.json` and the registry-side parsing
that populated `meta["layouts"]` — kinds describe data shape,
not presentation.

## Context

- Parent: [[t0114-feat-tree-layout-for-art]].
- Spec contract: [[s0022-tree-layout]] §13.1 (file-level diff
  with paths and exact change set).
- Sibling sub-tasks (parallel-startable): t0122
  (`make-render-tree-parent-field-required`), t0123
  (`extend-views-models-for-layout-config`).
- Joins at: t0124 (`rewire-cli-resolve-layout-for-settings-only`).

## Requirements

Apply spec §13.1 exactly. No additional schema changes.

1. Remove the `x-layouts` block from `artifacts/kinds/task.json`.
   `x-columns`, `x-status-colors`, and `properties` stay
   byte-unchanged.
2. Remove `_KNOWN_LAYOUTS`, `_validate_and_parse_layouts`, and
   the call site in `_load_vault_kinds` from
   `src/artifacts_os/core/registry.py`.
3. Remove the 8 tests added by t0115 from
   `tests/core/test_registry.py`. The 12 pre-existing tests
   stay green.
4. Add `KindDef.schema_properties` accessor per spec §3.6 — a
   `set[str]` of property names from the kind JSON. No
   validation at registry load (property-existence check
   moves to CLI-resolve in t0124).
5. Add one new test: `kd.schema_properties` returns the
   expected set for `task.json`.

## Findings

All five requirements completed:

1. Removed `x-layouts` block from `artifacts/kinds/task.json`. `x-columns`, `x-status-colors`, and `properties` are byte-unchanged.
2. Removed `_KNOWN_LAYOUTS`, `_validate_and_parse_layouts`, and the call site in `_load_vault_kinds` from `src/artifacts_os/core/registry.py`.
3. Removed all 8 x-layouts tests (and the `_schema_with_parent` helper) from `tests/core/test_registry.py`. The 12 pre-existing tests remain green.
4. Added `KindDef.schema_properties` property to `src/artifacts_os/core/models.py` — returns `set[str]` of property names from `schema["properties"]`.
5. Added `test_schema_properties_task_kind` — loads the real `task.json` and asserts the full property set plus spot-checks five known fields.

`tests/core/test_registry.py` now has exactly 13 tests, all passing. Full suite introduces no new failures: 9 apparent failures in `test_list_layout.py` / `test_tree_renderer.py` are pre-existing from sibling task (t0123) working-tree changes, confirmed by reverting only t0121 changes and observing the same failures.

## Progress

### 2026-05-06 — developer
> time: 23:12

Removed x-layouts from task.json, _KNOWN_LAYOUTS and _validate_and_parse_layouts from registry.py, 8 x-layouts tests from test_registry.py. Added KindDef.schema_properties property. 13 tests pass in test_registry.py. No new failures in full suite (pre-existing failures from sibling task changes are not caused by this task).

## Verification

- [x] `task.json` no longer contains `x-layouts`; remaining
      content byte-unchanged.
- [x] `registry.py` no longer references `_KNOWN_LAYOUTS` or
      `_validate_and_parse_layouts`.
- [x] `tests/core/test_registry.py` has 12 + 1 = 13 tests; all
      pass.
- [x] `KindDef.schema_properties` exposes the kind's property
      set.
- [x] No other kind file modified.
- [x] Full test suite: no new failures introduced.

## Verification Report

*Verified: 2026-05-06*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | task.json no longer contains x-layouts; remaining content byte-unchanged | PASS | json.load confirms no x-layouts key; x-columns, x-status-colors, properties all present |
| 2 | registry.py no longer references _KNOWN_LAYOUTS or _validate_and_parse_layouts | PASS | grep finds zero references to either symbol |
| 3 | tests/core/test_registry.py has 13 tests; all pass | PASS | grep -c counts 13; pytest reports 13 passed |
| 4 | KindDef.schema_properties exposes the kind property set | PASS | models.py line 27 defines @property schema_properties returning set[str] |
| 5 | No other kind file modified | PASS | git diff --name-only shows only artifacts/kinds/task.json |
| 6 | Full test suite: no new failures introduced | PASS | 13 failures in full suite are all pre-existing (4 release-changelog-skill + 9 from sibling t0122/t0123 working-tree changes), confirmed by reverting t0121 changes and observing same count |

### Summary

6 passed, 0 failed. All verification criteria satisfied.


## Note

After this task lands and before t0124 ships, `art ls --kind
task` will temporarily fall back to `table` (the new
configuration site in `artifacts.yaml` only takes effect after
t0124 wires it). This is expected per spec §13.5 — the vault
config block ships with t0124's diff to keep the gap minimal.
