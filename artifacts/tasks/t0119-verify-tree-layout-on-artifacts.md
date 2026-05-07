---
kind: task
id: t0119
name: verify-tree-layout-on-artifacts
type: feature
status: rejected
assignee: 
owner: user
parent: "[[t0114-feat-tree-layout-for-art]]"
depends_on:
  - "[[t0118-document-tree-layout]]"
created: 2026-05-06
---

# Verify Tree Layout On Artifacts-Os Vault

## User story

As the user who asked for tree layout, I want to run `art ls`
on this very vault and see the hierarchy I already encoded —
end-to-end proof the feature does what it set out to do.

## Context

- Parent: [[t0114-feat-tree-layout-for-art]].
- Depends on docs (#5) being `done` so the public surface is
  shipped.
- Verification target is in [[s0022-tree-layout]] §6.5.

## Requirements

This is a hands-on check on the artifacts-os vault. Owner
performs the run.

1. Run `art ls --kind task` on the artifacts-os vault.
2. Confirm `t0042` is rendered under `t0036`.
3. Confirm `t0043`, `t0044`, `t0045`, `t0046` are rendered
   under `t0041`.
4. Confirm `art ls --kind task -q` output is unchanged
   compared to pre-feature output.
5. Confirm `art ls --kind task --layout table` produces the
   pre-feature flat output.
6. Spot-check a cycle (manually create one in a scratch vault
   if none exists naturally) — confirm `↻ cycle` annotation
   and the stderr warning per spec §6.3.
7. Spot-check a filtered slice that hides a parent — confirm
   `↑[parent: <ref>]` annotation per spec §7.

## Verification

- [ ] Item 2 verified — screenshot or paste of the rendered
      tree in the task body.
- [ ] Item 3 verified — same.
- [ ] Item 4 verified — diff is empty.
- [ ] Item 5 verified — flat output reproduced.
- [ ] Item 6 verified — cycle annotation behaves per spec.
- [ ] Item 7 verified — filtered-parent annotation behaves
      per spec.
- [ ] Parent task [[t0114-feat-tree-layout-for-art]] gets its
      verification checklist marked once this task is `done`.
