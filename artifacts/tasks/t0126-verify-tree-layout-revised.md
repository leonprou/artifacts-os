---
kind: task
id: t0126
name: verify-tree-layout-revised
type: feature
status: rejected
assignee: 
owner: user
parent: "[[t0114-feat-tree-layout-for-art]]"
depends_on:
  - "[[t0125-document-tree-layout-revised]]"
created: 2026-05-06
---

# Verify-Tree-Layout-Revised

## User story

End-to-end verification on the artifacts-os vault that the
revised configuration mechanism produces the same user-facing
tree output as the original — proof the migration is
behaviour-preserving.

## Context

- Parent: [[t0114-feat-tree-layout-for-art]].
- Depends on: t0125 (docs landed).
- Spec contract: [[s0022-tree-layout]] §13.7 (verification
  matrix), §6.5 (target shape).
- Replaces / closes-out the original [[t0119-verify-tree-layout-on-artifacts]]
  at the parent's level.

## Requirements

Hands-on check on this vault. Owner runs the matrix.

1. Run `art ls --kind task` on the artifacts-os vault.
2. Confirm `t0042` is rendered under `t0036`.
3. Confirm `t0043`–`t0046` are rendered under `t0041` (modulo
   filter-promotion glyphs depending on active status filter).
4. Confirm `art ls --kind task --layout table` produces flat
   output.
5. **New test (replaces the original "remove `x-layouts`"
   path):** remove the `default_layouts.task` block from
   `artifacts/artifacts.yaml` and re-run `art ls --kind task`.
   Confirm flat output. Restore the block after.
6. **New test:** set `default_layouts: { task: tree }` in
   `artifacts.yaml` (object form, **no `parent_field`**).
   Run any `art ls --kind task` invocation. Confirm exit 2
   at settings load with the parent_field error per §3.5
   rule 2. Restore the block after.
7. Spot-check a cycle (manually create one in a scratch
   vault if none exists naturally) — confirm `↻ cycle`
   annotation and stderr warning per §6.3.
8. Spot-check a filtered slice that hides a parent — confirm
   `↑[parent: <ref>]` per §7.

## Verification

- [ ] Item 2 verified — paste/screenshot of rendered tree.
- [ ] Item 3 verified — same.
- [ ] Item 4 verified — flat output reproduced.
- [ ] Item 5 verified — opt-out by removing
      `default_layouts.task` works.
- [ ] Item 6 verified — settings load fails loudly when
      `parent_field` is missing on a tree config.
- [ ] Item 7 verified — cycle annotation behaves per spec.
- [ ] Item 8 verified — filtered-parent annotation behaves
      per spec.
- [ ] Parent task [[t0114-feat-tree-layout-for-art]] gets
      its verification checklist marked once this task is
      `done`. Original t0119 may be left in `backlog` and
      auto-superseded, or marked rejected with reason —
      PM to decide once this is verified.
