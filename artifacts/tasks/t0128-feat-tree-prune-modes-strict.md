---
kind: task
id: t0128
name: feat-tree-prune-modes-strict
type: feature
status: done
assignee: 
owner: user
created: 2026-05-07
subtasks:
  - "[[t0129-implement-tree-prune-modes-engine]]"
started: 2026-05-07
completed: 2026-05-07
---

# Feat: Tree Prune Modes (Strict|Ancestors|Subtree)

# Feat: Tree Prune Modes

## User story

As a vault user running `art ls --kind task` against a status
filter (e.g. the `active` view), I want to choose how the tree
prunes around the matched set:

- **strict** — only matches render; orphan-promote with §6.4 Case B
  annotation (today's behavior).
- **ancestors** — match descendants; auto-include parents up to
  root as visually-distinct context rows so I can see which
  feature each active task belongs to.
- **subtree** — once a node matches, render its full descendant
  subtree regardless of filter, so I can review feature progress
  including done/backlog children.

## Context

- Today the tree layout always runs in `strict` mode (s0022 §6.4
  Case B / §7 — child promoted with `↑[parent: <ref>]`). That is
  the right default for "what's actually active right now" but a
  poor default for "what does my work hierarchy look like?"
- Open Station's CLI already implements something close to
  `subtree` (any matching ancestor's full subtree renders).
  Users have asked for this behaviour in `art` too.
- The `active` view in this vault now matches
  `[ready, in-progress, review, verified]` — the prune mode
  question is what made the difference between `art v active`
  and `os ls` outputs visible.

## Spec

[[s0024-tree-prune-modes]] (forthcoming — see sub-task assigned
to architect).

## Sub-tasks

1. **Spec** — architect drafts s0024 (this spec covers the
   contract, resolution chain, model changes, algorithm, and
   test matrix). Status: in progress on creation of this task.
2. **Implementation** — developer extends `compute_tree`,
   `render_tree`, `ViewConfig`, `LayoutConfig`, and the CLI to
   support the three modes. Set the `active` view to
   `prune: ancestors` and dogfood it.
3. **Documentation** — author updates `docs/views/`,
   `cli/README.md`, `views/README.md` with the new flag, view
   field, and kind-default field.
4. **Verify** — confirm that `art v active` shows the t0114
   subtree's matched leaves (t0124) under the active parent,
   plus an `art v active --prune subtree` invocation that shows
   the full t0114 descendant set.

## Verification

- [ ] Spec s0024 exists, approved, links back to this task.
- [ ] All three modes implemented; `--prune` flag, `view.prune`,
      and `default_layouts.<kind>.prune` all resolve per spec §4.
- [ ] Match-preservation: `set(rendered_ids) ⊇ set(matched_ids)`
      for every mode in the test matrix.
- [ ] Filter-honesty: in `ancestors` mode, every non-match row
      is rendered with `Style(dim=True)` and `· (context)` marker.
- [ ] `-q` and `-j` outputs unchanged regardless of `--prune`.
- [ ] `--children` and `--parent` neutralize prune.
- [ ] `artifacts.yaml` `active` view sets `prune: ancestors` and
      `art v active` renders t0114 + t0124 only (not its full
      subtree).
- [ ] All existing tree tests still pass; new tests cover the
      §9 matrix.
- [ ] Docs reflect the new surface.
