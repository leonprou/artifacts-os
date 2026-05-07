---
kind: task
id: t0114
name: feat-tree-layout-for-art
type: feature
status: done
assignee: 
owner: user
created: 2026-05-06
subtasks:
  - "[[t0115-apply-x-layouts-to-task]]"
  - "[[t0116-implement-tree-renderer-in-views]]"
  - "[[t0117-wire-layout-flag-in-cli]]"
  - "[[t0118-document-tree-layout]]"
  - "[[t0119-verify-tree-layout-on-artifacts]]"
  - "[[t0120-spec-revision-move-tree-layout]]"
  - "[[t0121-revert-x-layouts-from-kind]]"
  - "[[t0122-make-render-tree-parent-field]]"
  - "[[t0123-extend-views-models-for-layout]]"
  - "[[t0124-rewire-cli-resolve-layout-for]]"
  - "[[t0125-document-tree-layout-revised]]"
  - "[[t0126-verify-tree-layout-revised]]"
completed: 2026-05-07
---

# Feat: Tree Layout For Art Ls

## User story

As an artifacts-os user listing a hierarchical kind
(`art ls --kind task`), I want to see parent/child relationships
rendered as a tree so the structure already encoded in my data is
visible without me passing flags or memorising field names.

## Origin

- Scoping: [[n0002-layouts-tree-view-scoping]] — work breakdown,
  risks, dependency shape.
- Spec (approved): [[s0022-tree-layout]] — layout abstraction,
  kind-side / renderer / CLI / settings contracts.
- Spec task (done): [[t0113-spec-tree-layout-for-art]].

This is the umbrella task for items #2–#6 of n0002's work
breakdown. Each sub-task is a single agent, single contract slice
of the spec.

## Requirements

The user-facing outcome — and the only thing the user sees — is:

- `art ls --kind task` shows hierarchy by default on this vault.
  `t0042` appears under `t0036`; `t0043`–`t0046` appear under
  `t0041`. Spec §6.5 has the exact target shape.
- `-q` and `-j` output is unchanged.
- `--fields` continues to work for non-hierarchical kinds.
- A user can opt out of the tree on a hierarchical kind via
  `--layout table`.
- Behaviour is driven by `x-layouts` on the kind, not hardcoded.

Sub-tasks carry the implementation contracts. This task tracks
their completion and anchors the verification pass.

## Subtasks

The implementation chain, sequenced per n0002 § "Work breakdown"
and spec § "Downstream":

1. Kind schema + migration — `task.json` gets `x-layouts`
   (developer; reads spec §3).
2. Tree renderer in `views/` — algorithm + `LAYOUTS` registry
   (developer; reads spec §5, §6, §9).
3. CLI wiring — `--layout` flag + resolution chain
   (developer; reads spec §8, §13.4).
4. Documentation — settings doc, CLI README, views README,
   `artifacts-os` skill (author).
5. Verification on artifacts-os vault (owner: user).

Sub-tasks #1 and #2 run in parallel after spec lands; #3 depends
on both; #4 depends on #3; #5 depends on #4.

## Verification

- [ ] Sub-tasks #1–#5 are all `done`.
- [ ] On the artifacts-os vault, `art ls --kind task` renders the
      hierarchy described in spec §6.5.
- [ ] `art ls --kind task -q` output is byte-identical to the
      pre-change output (regression check).
- [ ] `art ls --kind task -j` output is byte-identical
      (regression check).
- [ ] `art ls --kind task --layout table` produces the previous
      flat output (opt-out works).
