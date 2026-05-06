---
kind: task
id: t0117
name: wire-layout-flag-in-cli
type: implementation
status: done
assignee: developer
owner: developer
parent: "[[t0114-feat-tree-layout-for-art]]"
depends_on:
  - "[[t0115-apply-x-layouts-to-task]]"
  - "[[t0116-implement-tree-renderer-in-views]]"
created: 2026-05-06
started: 2026-05-06
completed: 2026-05-06
---

# Wire --Layout Flag In Cli

## User story

As an `art ls` user on a kind that declares a tree layout, I
want the tree to be the default; as a user who wants flat
output anyway, I want to pass `--layout table`.

## Context

- Parent: [[t0114-feat-tree-layout-for-art]].
- Depends on the kind-schema task and the tree-renderer task —
  both must be `done` before this can start.
- Spec contracts:
  - §8 — `--layout` flag, resolution chain, `-q`/`-j`
    carve-out.
  - §13.4 — flag registration against
    `_RESERVED_FILTER_FLAG_NAMES`.

## Requirements

1. Add the `--layout` long-form flag to `art ls` per spec §8.
   No short form. Document the help text from §8.
2. Implement the resolution chain per §8: explicit > view >
   `settings.default_layouts` > `kind.x-layouts.default` >
   implicit `"table"`. Wrap this as a single helper
   (`resolve_layout`) so it's testable in isolation.
3. Reserve `--layout` against `_RESERVED_FILTER_FLAG_NAMES` per
   §13.4 so a future filter flag with the same name is caught
   at registry load.
4. Thread `sort_key` into `compute_tree` so the active `--sort`
   selection drives sibling order (§6.2 / §8 interaction).
5. `-q` and `-j` carve out per §8: layout selection skipped,
   sort still applies on flat data.
6. Tests cover: default-tree path, explicit `--layout table`
   opt-out, resolution-chain precedence, `-q`/`-j` carve-out,
   `--sort` interaction, reserved-flag collision detection.

## Progress

### 2026-05-06 22:17:43 — Incomplete run (r0133)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$2.28, turns=51

## Verification

- [x] `--layout` flag registered with help text from §8.
- [x] `resolve_layout` returns the spec §8 precedence on every
      branch; unit test covers each branch.
- [x] `_RESERVED_FILTER_FLAG_NAMES` includes `layout` and a
      collision test exercises the path.
- [x] `art ls --kind task -q` and `-j` byte-identical to
      pre-change output (regression test).
- [x] `art ls --kind task --layout table` produces the
      pre-change flat output.
- [x] `art ls --kind task --sort id` sibling order matches
      §6.2 with sort applied.
- [x] CLI tests pass; existing list-command tests pass
      unchanged.

## Verification Report

*Verified: 2026-05-06*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `--layout` flag registered with help text from §8 | PASS | `list.py` lines 230–237: `--layout NAME` added, no short form, help text matches §8.6; `TestLayoutHelp` passes |
| 2 | `resolve_layout` covers all §8 branches; unit tests each branch | PASS | `resolve_layout` at line 337 implements 5-rung chain; `TestResolveLayout` (9 tests) covers every rung and matrix — all pass |
| 3 | `_RESERVED_FILTER_FLAG_NAMES` includes `layout`; collision test | PASS | Line 28: `"layout"` in frozenset; `TestReservedFlagName::test_layout_in_reserved_names` and `test_collision_skipped_silently` pass |
| 4 | `-q`/`-j` regression: byte-identical to pre-change output | PASS | `TestQuietJsonCarveOut` (5 tests): layout skipped for -q/-j, sort still applies — all pass |
| 5 | `--layout table` produces flat output | PASS | `TestLayoutTableOptOut` (3 tests): explicit table override confirmed — all pass |
| 6 | `--sort id` sibling order matches §6.2 | PASS | `TestSortInteractionWithTree` (2 tests): sort_key threaded into render_tree — all pass |
| 7 | CLI tests pass; existing list-command tests pass | PASS | 398 CLI tests pass (all of `tests/cli/`) |

### Summary

7 passed, 0 failed. All verification criteria confirmed by direct code inspection and test execution.

## Findings

All six requirements implemented in `src/artifacts_os/cli/commands/list.py`.

**What was built:**

1. **`--layout NAME` flag** — added to `art ls` parser after `--fields`/`--meta`,
   no short form, help text per §8.6. Choices validated against `views.LAYOUTS`
   at runtime.

2. **`resolve_layout` helper** — five-rung chain
   (explicit > view.layout > default_layouts > kind.meta > implicit "table").
   Exported from the module for unit-testing in isolation.

3. **`"layout"` reserved** — added to `_RESERVED_FILTER_FLAG_NAMES` per §13.4.

4. **`_build_sort_key` helper** — converts a sort string (`"id"`, `"-created"`)
   into a key callable for `compute_tree`. Handles ascending and descending with
   a `_Rev` wrapper class (avoids cmp_to_key overhead). Falls through to
   `compute_tree`'s id-based default when `sort_str` is falsy.

5. **`run()` restructured** — early flat `_apply_sort` removed; sort is now
   applied per output mode: -q/-j always get sorted flat data; tree layout
   threads `sort_key_fn` into `render_tree`; table layout applies `_apply_sort`
   before `render_table`. `is_known_stem=registry.exists_stem` passed to
   `render_tree` for precise B-vs-C annotation.

6. **Tests** — `tests/cli/test_list_layout.py` with 34 tests covering:
   - `resolve_layout` unit tests for all 5 rungs + full matrix
   - `_build_sort_key` unit tests (ascending, descending, missing values)
   - Reserved-flag collision test
   - Default-tree path integration tests
   - Explicit `--layout table` opt-out
   - Settings `default_layouts` override (rung 3)
   - View `layout` override (rung 2)
   - Explicit flag override (rung 1)
   - `-q`/`-j` carve-out (layout skipped, sort still applies)
   - `--sort` interaction threading into tree sibling order

**Gotcha**: `_write_artifacts_yaml` in tests must include `project:\n  name: test\n`
because `load_settings` raises `KeyError` on missing `project` section, which
`_load_views_settings` catches and returns `None` — silently bypassing settings.

**Tests run**: 625 passed, 1 skipped (pre-existing `test_release_changelog_skill`
failure unrelated to this task).
