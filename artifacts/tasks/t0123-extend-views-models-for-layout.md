---
kind: task
id: t0123
name: extend-views-models-for-layout
type: implementation
status: done
assignee: developer
owner: developer
parent: "[[t0114-feat-tree-layout-for-art]]"
created: 2026-05-06
started: 2026-05-06
completed: 2026-05-07
---

# Extend-Views-Models-For-Layout-Config

## User story

The settings layer needs to express layout configuration in
`artifacts.yaml`. Add `LayoutConfig` and update `ViewsConfig`
and `ViewConfig` so users can declare per-kind defaults and
per-view overrides.

## Context

- Parent: [[t0114-feat-tree-layout-for-art]].
- Spec contract: [[s0022-tree-layout]] §10.2 (`LayoutConfig`),
  §10.4 (view layer), §13.3 (file-level diff).
- Sibling sub-tasks (parallel): t0121, t0122.
- Consumed by: t0124 (CLI resolve_layout reads `LayoutConfig`).

## Requirements

Apply spec §10.2 / §10.4 / §13.3 exactly.

1. In `src/artifacts_os/views/models.py`:
   - Add `LayoutConfig` dataclass (shape per §10.2; carries
     `layout: str` and `parent_field: str | None`).
   - Change `ViewsConfig.default_layouts` from
     `dict[str, str]` to `dict[str, LayoutConfig]`.
   - Add `parent_field: str | None = None` to `ViewConfig`.
   - Replace inline `default_layouts` validation with
     `_parse_default_layouts` per §10.2 (string-form
     shorthand vs object-form, parent_field required when
     `layout: tree`).
   - Extend `_parse_view` to read and validate `parent_field`
     per §10.4.
2. Add tests for the parse-time validation matrix:
   - String-form `default_layouts` (e.g. `task: table`).
   - Object-form `default_layouts` (`{ layout: tree,
     parent_field: parent }`).
   - Tree without parent_field → ValidationError.
   - Non-tree with parent_field → ValidationError.
   - Unknown layout name → ValidationError.
   - `view.layout` + `view.parent_field` paired correctly.
   - `view.layout` + `view.parent_field` paired
     incorrectly → ValidationError.

## Findings

`src/artifacts_os/views/models.py` was already substantially implemented. Verified all requirements of spec §10.2/§10.4/§13.3 are in place:

- `LayoutConfig` frozen dataclass with `layout: str` and `parent_field: str | None = None`.
- `ViewsConfig.default_layouts: dict[str, LayoutConfig]` (updated from `dict[str, str]`).
- `ViewConfig.parent_field: str | None = None` added.
- `_parse_default_layouts` handles string-form shorthand, object-form, and enforces all validation rules (unknown layout, tree+parent_field pairing).
- `_parse_view` validates `layout`/`parent_field` pairing per §10.4.
- 15 tests in `tests/views/test_views_settings.py` all pass, including all 7 required validation-matrix cases.
- No imports from `cli/` or `core/` (only `artifacts_os.core.models.Settings`).

## Progress

### 2026-05-07 — developer
> time: 00:13

All 15 tests pass (7 new layout validation tests + 8 pre-existing); models.py fully implements LayoutConfig, ViewsConfig.default_layouts, ViewConfig.parent_field, _parse_default_layouts, _parse_view per spec §10.2/§10.4

## Verification

- [x] `LayoutConfig` dataclass exists per §10.2.
- [x] `ViewsConfig.default_layouts: dict[str, LayoutConfig]`.
- [x] `ViewConfig.parent_field: str | None = None`.
- [x] `_parse_default_layouts` enforces the validation matrix
      above.
- [x] `_parse_view` enforces `parent_field` validity per
      §10.4.
- [x] All seven test cases above pass.
- [x] No `cli/` or `core/` reach-ins.

## Verification Report

*Verified: 2026-05-07*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `LayoutConfig` dataclass exists per §10.2 | PASS | `models.py` line 15: `@dataclass(frozen=True) class LayoutConfig` with `layout: str` and `parent_field: str \| None = None` |
| 2 | `ViewsConfig.default_layouts: dict[str, LayoutConfig]` | PASS | `models.py` line 43: `default_layouts: dict[str, LayoutConfig] = field(default_factory=dict)` |
| 3 | `ViewConfig.parent_field: str \| None = None` | PASS | `models.py` line 34: `parent_field: str \| None = None` |
| 4 | `_parse_default_layouts` enforces the validation matrix | PASS | Lines 89–130: handles string-form, object-form, unknown layout, tree+no parent_field, non-tree+parent_field |
| 5 | `_parse_view` enforces `parent_field` validity per §10.4 | PASS | Lines 133–175: validates layout/parent_field pairing in all cases including parent_field without layout |
| 6 | All seven test cases pass | PASS | `pytest tests/views/test_views_settings.py` — 15 passed (includes all 7 layout validation matrix tests) |
| 7 | No `cli/` or `core/` reach-ins | PASS | Only import is `from artifacts_os.core.models import Settings` (expected inheritance base) |

### Summary

7 passed, 0 failed. All verification criteria confirmed against source code and test output.
