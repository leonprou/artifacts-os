---
kind: task
id: t0116
name: implement-tree-renderer-in-views
type: implementation
status: done
assignee: developer
owner: developer
parent: "[[t0114-feat-tree-layout-for-art]]"
created: 2026-05-06
started: 2026-05-06
completed: 2026-05-06
---

# Implement Tree Renderer In Views

## User story

As a `views/` consumer, I want a tree renderer that takes a
flat `list[ArtifactMeta]` plus the kind def and returns a
Rich `Table` with hierarchy glyphs on the first column — so
the existing column model, status colors, and format strings
all keep working.

## Context

- Parent: [[t0114-feat-tree-layout-for-art]].
- Spec contracts (read these, in order):
  - §4 — `Layout` type and `views.LAYOUTS` registry.
  - §5 — `compute_tree`, `render_tree`, `TreeNote` signatures.
  - §6 — algorithm: flatten-with-depth, sibling order, cycles
    (`↻ cycle`), filtered-slice (`↑[parent: <ref>]`).
  - §9 — glyph prefix on first column.
- Parallel-start with [[Apply x-layouts to task.json]]
  (sibling sub-task).
- This task does **not** touch CLI code. CLI wiring is the next
  task.

## Requirements

Implementation surface is fully specified in §5 and §6. Stay
within those contracts.

1. Implement `compute_tree(items, kind_def, sort_key)` and
   `render_tree(nodes, columns)` per spec §5 and §6.
2. Define the `TreeNote` annotation type per §5 — used for
   `↻ cycle` and `↑[parent: <ref>]` cases.
3. Register `tree` and the existing `table` in
   `views.LAYOUTS` per §4. Keep the registry open for a future
   third member without code changes.
4. Promote `_unwrap_wikilink` to public per spec §5; add
   `Registry.exists_stem` per §6.4 (used by
   missing-parent detection).
5. Tests cover: simple tree, multi-level, cycle handling,
   missing parent, sibling order with and without `--sort`,
   filtered-slice promotion. Use the spec §6.5 vault example as
   one of the fixtures.
6. Module-DAG respected: no `cli/` imports, no `core/` reach-in
   beyond the existing data types.

## Progress

### 2026-05-06 — developer
> time: 21:44

Implemented tree renderer: layouts/ module with TreeNote, compute_tree,
render_tree, LAYOUTS registry. Updated ViewConfig and ViewsConfig for
layout fields. 44 new tests; 661 total pass.

## Findings

New module `src/artifacts_os/views/layouts/` with three files:

- `tree.py` — `TreeNote` enum, `compute_tree` (pure DFS with cycle
  detection and ORPHAN_OUT_OF_SLICE for unresolved parents), `render_tree`
  (builds Rich Table with `├─`/`└─` glyphs on first column; Case B/C/D
  annotations; emits one stderr warning per cycle).
- `table.py` — re-export of `render_table` for layout symmetry.
- `__init__.py` — `Layout` type alias and `LAYOUTS = {"table": render_table, "tree": render_tree}`.

Re-exports added to `views/__init__.py`: `Layout`, `LAYOUTS`, `TreeNote`,
`compute_tree`, `render_tree`.

`ViewConfig` gains `layout: str | None = None`; `ViewsConfig` gains
`default_layouts: dict[str, str]`. Both validated against `LAYOUTS` at
parse time (import inside function body to avoid circular import).

Notable decisions:
- Pure-cycle edge case (all items in a cycle with no natural root): handled
  by a second pass that forces the lowest-id unvisited item as a root.
- `ORPHAN_MISSING` is used in render_tree logic when `is_known_stem`
  distinguishes Case B from C; `compute_tree` always emits
  `ORPHAN_OUT_OF_SLICE` for unresolvable parents (it has no registry access).
- `unwrap_wikilink` and `Registry.exists_stem` were already promoted in the
  parallel task (t0115); no changes needed here.

## Verification

- [x] `compute_tree` and `render_tree` implemented per §5/§6
      signatures.
- [x] `views.LAYOUTS` registry has `table` and `tree` members.
- [x] Cycle rendering matches §6.3 (visible-break with
      `↻ cycle` + one stderr warning).
- [x] Filtered-slice rendering matches §7 (`↑[parent: <ref>]`).
- [x] Module DAG preserved — no cli/core reach-ins.
- [x] Renderer tests pass; existing table renderer tests
      pass unchanged.

## Verification Report

*Verified: 2026-05-06*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `compute_tree` and `render_tree` implemented per §5/§6 signatures | PASS | `compute_tree(items, *, parent_field, sort_key)` and `render_tree(items, columns, *, kind_def, parent_field, sort_key, is_known_stem)` match spec exactly; TreeNote has all 4 values |
| 2 | `views.LAYOUTS` registry has `table` and `tree` members | PASS | `LAYOUTS = {"table": render_table, "tree": render_tree}` in `views/layouts/__init__.py`; confirmed via import |
| 3 | Cycle rendering matches §6.3 (visible-break with `↻ cycle` + one stderr warning) | PASS | Live test: cells contain `t0060  ↻ cycle`; stderr emits exactly one `warning: cycle detected on parent chain of t0060 (kind: task)` |
| 4 | Filtered-slice rendering matches §7 (`↑[parent: <ref>]`) | PASS | Live test: orphan with `is_known_stem=True` renders `t0042  ↑[parent: t0036]`; without `is_known_stem` renders `?[parent: ...]` |
| 5 | Module DAG preserved — no cli/core reach-ins | PASS | `grep` finds zero `artifacts_os.cli` imports in `views/layouts/`; only `core.discover`, `core.errors`, `core.models`, `views._views` imported |
| 6 | Renderer tests pass; existing table renderer tests pass unchanged | PASS | 78 views tests pass (44 new tree tests + 34 existing); 661 total suite passes |

### Summary

6 passed, 0 failed. All verification criteria met.
