---
assignee: author
created: 2026-05-03
id: t0083
kind: task
name: author-artifact-md-for-agent
owner: user
parent: '[[t0079-artifact-md-artifacts-ai-extension]]'
status: ready
type: documentation
---

# Author ARTIFACT.md for `agent` Kind

## Goal

Author `artifacts/kinds/agent/ARTIFACT.md` so the L1 catalogue
shows a meaningful `description` for the `agent` kind, and so
authoring a new agent definition follows a consistent shape.

## Context

This task is a sub-task of
`[[t0079-artifact-md-artifacts-ai-extension]]`. The parent task
carries the full reading list, design constraints, and progress
table for the epic — read it for context if you need more than
the Source of truth below.

## Source of truth

[`docs/adding-a-kind.md`](../../docs/adding-a-kind.md) — **the
canonical authoring guide.** Covers the `description:` contract
(required, ≤ 1024 chars, third-person, what + when), validation
outcomes, anti-patterns, the L1 catalogue surface, and the
evaluation-first authoring loop. Read this first.

`[[artifacts/kinds/note/ARTIFACT.md]]` — exemplar shape.

`artifacts/agents/architect.md`, `author.md`, `developer.md`,
`product-manager.md`, `project-manager.md`, `researcher.md`,
`technical-writer.md` — existing agent definitions to lift
conventions from.

`[[s0017-artifact-kinds-discovery-mechanism]]` § 6 — locked
`description:` contract. Consult only if `docs/adding-a-kind.md`
doesn't answer a contract question.

## Scope

1. Create `artifacts/kinds/agent/ARTIFACT.md`.
2. Frontmatter:
   - `name: agent`
   - `description:` — "what" anchored in agent role definitions
     (capabilities + constraints that scope an AI agent's
     behaviour) and "when" anchored in the trigger (a new role is
     needed to delegate work; an existing role's scope shifts).
   - `applies_to: agent`
   - Note that `agent` is a non-numbered kind (see existing
     agent files: filename = slug, `id == name`); reflect any
     necessary frontmatter conventions accordingly.
   - `placeholder_syntax`, `schema_version` per exemplar.
3. `## How to use` prose: how to write Capabilities + Constraints
   sections (precedent: project-manager.md, product-manager.md);
   when to scope an agent narrowly vs broadly; how to delegate
   between agents.
4. `## Skeleton` shaped after the existing seven agent
   definitions: Role intro / Capabilities (bulleted) /
   Constraints (bulleted) / Optional sections (e.g. workflow
   guidance, decision rules).

## Constraints

- **No new design** — consumes the `description:` contract from
  s0017 § 6.
- **Lift from existing agents.** Survey all seven existing
  `artifacts/agents/*.md` files; the skeleton should reproduce
  their best conventions (project-manager.md and
  product-manager.md are particularly well-structured).
- **Non-numbered kind** — agent files are named by slug, not
  prefixed ID. Document this in `## How to use` so authors don't
  expect a `gNNNN-` prefix.
- **One-deep nesting** for any declared playbooks.

## Verification

- [ ] `artifacts/kinds/agent/ARTIFACT.md` exists with valid
      frontmatter.
- [ ] `description` honours s0017 § 6.
- [ ] `artifacts kinds` shows the description for `agent`.
- [ ] `## How to use` and `## Skeleton` sections present.
- [ ] Non-numbered-kind convention documented.
- [ ] Reviewed and approved by user.