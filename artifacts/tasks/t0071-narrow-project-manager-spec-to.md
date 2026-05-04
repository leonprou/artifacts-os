---
assignee: author
created: 2026-05-02
id: t0071
kind: task
name: narrow-project-manager-spec-to
owner: user
status: cancelled
type: documentation
---

# Narrow `project-manager` Spec to Delivery Coordination

## User Story

**As a** user driving artifacts-os direction,
**I want** the `project-manager` agent spec to focus exclusively
on delivery coordination,
**so that** product framing (strategy, roadmap, user stories,
feature intent) cleanly belongs to the new `product-manager`
agent and there is no overlap between the two.

## Why

`product-manager` shipped in [[t0070-define-product-manager-agent]]
and now owns product strategy, roadmap, market/user discovery,
and feature task authoring. The current `project-manager` spec
still claims requirements-capture as one of its responsibilities
("Capture user-level requirements — user stories, intent, and
acceptance criteria…"), which now duplicates `product-manager`'s
mandate. We want `project-manager`'s scope to be unambiguous:
backlog flow, agent assignment, status transitions, verification,
and project documentation — i.e. delivery coordination.

## Directions

> Intent, not contract. Match existing agent-spec conventions in
> `artifacts/agents/`.

- Edit `artifacts/agents/project-manager.md` to remove
  product-framing language from **Capabilities** and
  **Constraints** — specifically the bullet about capturing
  user-level requirements / user stories / acceptance criteria,
  and any wording that overlaps `product-manager`.
- Lean fully into delivery coordination: backlog triage,
  promotion when ready, agent assignment, status monitoring,
  verification when designated, project documentation upkeep,
  documentation-gap detection.
- Add a brief boundary note pointing to `product-manager` for
  product/strategy/roadmap/feature framing and to `architect`
  for technical contract — mirror the boundary section already
  present in `product-manager.md`.
- Preserve the spec's existing tone, frontmatter, and any
  unrelated guidance. Use minimal-diff edits, not a rewrite.

## Open Questions for the Author

- Should `project-manager` keep the "spawn an architect spec
  sub-task" guidance? Recommended yes — it remains a delivery-
  coordination move (routing technical work to the right agent),
  not a product-framing move.
- Does any other agent spec reference `project-manager`'s
  requirements-capture role in a way that needs follow-up
  edits? Recommended: scan `artifacts/agents/` and update if
  found.

## Sub-tasks

None.

## Verification

- [ ] `project-manager.md` no longer claims requirements-capture
      / user-story / acceptance-criteria responsibilities.
- [ ] Capabilities and Constraints sections read as a coherent
      delivery-coordination charter with no product-framing
      overlap with `product-manager`.
- [ ] A short boundary note distinguishes `project-manager` from
      `product-manager` and `architect`.
- [ ] `artifacts validate project-manager --kind agent` passes.
- [ ] No other agent spec references the removed responsibilities
      in a way that contradicts the new boundary.