---
kind: task
id: t0122
name: make-render-tree-parent-field
type: implementation
status: done
assignee: developer
owner: developer
parent: "[[t0114-feat-tree-layout-for-art]]"
created: 2026-05-06
started: 2026-05-06
completed: 2026-05-06
---

# Make-Render-Tree-Parent-Field-Required

## User story

The renderer should be mechanism-agnostic — it accepts a
`parent_field` argument from its caller, not by reading the
kind file. Make `parent_field` a required argument on
`render_tree`.

## Context

- Parent: [[t0114-feat-tree-layout-for-art]].
- Spec contract: [[s0022-tree-layout]] §13.2 (file-level diff).
- Sibling sub-tasks (parallel): t0121, t0123.
- Joins at: t0124.

## Requirements

Apply spec §13.2 exactly. The renderer algorithm in §6 stays
unchanged.

1. In `src/artifacts_os/views/layouts/tree.py`, change
   `render_tree(parent_field: str | None = None)` to
   `render_tree(parent_field: str)` — required, no default.
2. Remove the `if resolved_parent_field is None and kind_def
   is not None: ...` fallback block (the kind_def-side lookup
   that read `meta["layouts"]["tree"]["parent_field"]`).
3. Keep the `kind_def` parameter — it carries `status_colors`
   for the underlying table render.
4. `compute_tree`, `TreeNote`, `LAYOUTS` registry,
   `Registry.exists_stem`, `unwrap_wikilink`, and the §6
   algorithm are **unchanged**.
5. Update existing tests: any `render_tree(...)` call that
   omitted `parent_field` either pivots to passing it
   explicitly, or becomes a test of the new "missing
   parent_field" surface (`TypeError` from missing kwarg).

## Verification

- [ ] `render_tree.parent_field` is a required parameter.
- [ ] Kind_def fallback block is gone.
- [ ] `compute_tree`, `TreeNote`, `LAYOUTS`,
      `Registry.exists_stem`, `unwrap_wikilink` unchanged.
- [ ] Renderer tests pass; calls that exercised the fallback
      either pass `parent_field` explicitly or are repurposed.
- [ ] No `cli/` or `core/` reach-in beyond existing imports.

## Findings

Made `parent_field` a required keyword argument on `render_tree`,
removing the kind_def-side fallback that read
`meta["layouts"]["tree"]["parent_field"]`. The renderer is now
mechanism-agnostic: it accepts `parent_field` from the caller only.

**Changes:**
- `src/artifacts_os/views/layouts/tree.py`: signature changed from
  `parent_field: str | None = None` to `parent_field: str`; removed
  the three-line kind_def fallback block and the `ValidationError`
  raise; removed the now-unused `ValidationError` import; replaced
  `resolved_parent_field` with `parent_field` in the orphan annotation
  branch.
- `tests/views/test_tree_renderer.py`: added `parent_field="parent"`
  to all 11 `render_tree(...)` calls that previously relied on the
  kind_def fallback; changed `test_raises_when_no_parent_field` to
  expect `TypeError` (missing required kwarg) instead of
  `ValidationError`.

42/42 renderer tests pass. 2 pre-existing failures in
`TestViewsConfigLayout` are unrelated (owned by t0123).

## Downstream

- The CLI caller in `src/artifacts_os/cli/commands/list.py` (line 564)
  still calls `render_tree` without `parent_field`. It will fail at
  runtime when tree layout is selected until t0124 wires the resolved
  `parent_field` through. This is expected per spec §13.8 sequence.
