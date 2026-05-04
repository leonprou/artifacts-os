---
name: task
description: Captures a planned unit of work with verifiable acceptance criteria, an owner, and (once scoped) an assignee. Use when the work has a single deliverable an agent or person can complete and a verifier can accept.
---

# Task

## What is a task?

A **task** is a planned unit of work with verifiable acceptance
criteria. It moves through a lifecycle (`backlog → ready →
in-progress → review → verified → done`, with `cancelled` /
`rejected` for descoped work) under a named `owner` and (once
scoped) an `assignee`. Its load-bearing property is
**verifiability**: every requirement is something a verifier can
mark true or false, and the `## Verification` checklist is the
explicit accept gate.

Every task carries a `type` naming the *output* it produces, not
the activity that produces it:

| `type` | Captures |
|---|---|
| `feature` | End-to-end product capability. Often an umbrella that decomposes into spec + implementation sub-tasks. |
| `implementation` | Coding work against an approved spec or a clearly bounded change. |
| `spec` | Architect produces a design document under `artifacts/specs/`. The body lists the questions the spec must answer. |
| `documentation` | Writes or updates docs, READMEs, skills, commands. No code. |
| `research` | Investigation or evidence-gathering. Output is a `research` artifact. |
| `refactor` | Restructures shipped code with no behaviour change. Verification bar is "behaviour preserved". |

Defects file as `implementation` (or `refactor` for
non-behavioural cleanup) with a `## Root cause` note under
Context — `bug` is not a separate `type`.

A task has no fixed skeleton. Two sections are required at draft
time — `## Requirements` and `## Verification` — and one more
(`## Findings`) at completion. Every other section is optional
and added only when the task's `type` and maturity call for it:

| Section | Required / when to add |
|---|---|
| `## Requirements` | **Required at draft.** Testable deliverables the verifier can check. |
| `## Verification` | **Required at draft.** GitHub-flavoured checkboxes; the explicit accept gate. |
| `## Findings` | **Required at completion.** Lead with conclusions: what was built, key decisions, gotchas; link to artifacts produced. |
| `## User story` | `type: feature` — the user-facing *what* + *why*. |
| `## Why` | Strategic context isn't obvious from title + Requirements. |
| `## Source of truth` | An approved spec, plan, or research artifact binds the task. |
| `## Context` | The verifier needs background (current behaviour, related code, prior tasks). |
| `## Goal` | One concrete outcome worth pinning when Requirements alone don't make it explicit. |
| `## Out of scope` | Scope creep is likely; mirror the spec's non-goals for `implementation` tasks. |
| `## Constraints` | Load-bearing rules apply that aren't obvious from the spec or codebase. |
| `## Test plan` | `type: implementation` or `refactor` — test groups the implementer must add or extend. |
| `## Subtasks` | `type: feature` umbrellas — manifest of child tasks; mirror in `subtasks:` frontmatter. |
| `## Progress` | Written during execution via `/openstation.progress`; one entry per session. |
| `## Downstream` | Follow-up work the executor noticed but did not address. |
| `## Verification Report` | Written by `/openstation.verify`; do not author manually. |

## How to draft a task

`t0076-implement-l1-kinds-catalogue-s0017` is the worked example
for an implementation task backed by a spec.

### Step 1 — Write requirements that are testable

Every line in `## Requirements` is something the verifier can
check. Numbered list when there are 3+ independent deliverables;
prose + H3 sub-sections when related requirements need framing.

If a requirement needs rationale, design alternatives, or a
contract that does not yet exist, the task is mis-typed —
externalise the reasoning to a `## User story` / `## Why` section
(`type: feature`) or a sibling `spec` artifact. The task body is
a brief, not a design.

### Step 2 — Lock the verification checklist as the accept gate

`## Verification` is GitHub-flavoured checkboxes (`- [ ]`); each
item must be **true or false at completion** — no "works well",
"is reasonable", or other subjective rubric. The final
`- [ ] Reviewed and approved by {{OWNER}}` (`user` for human
review; an agent name for automated approval) is the explicit
accept gate. The verifier ticks the boxes; do not pre-tick.

| Anti-pattern | Better |
|---|---|
| `- [ ] Implementation looks good` | `- [ ] All tests in s0017 § 9.1–9.5 pass` |
| `- [ ] Documentation updated` | `- [ ] docs/adding-a-kind.md describes the description contract` |
| Re-stating requirements verbatim | Cite a verifiable property of the requirement |
| Mixing test plan and verification | Test plan goes in `## Test plan`; verification is the accept gate |

### Step 3 — Cite, do not duplicate; decompose only when too large

When an approved spec, plan, or research artifact binds the task,
link it under `## Source of truth` and keep the body to pointers
plus the verification checklist — the spec is binding, the body
drifts as it evolves.

Decompose into `## Subtasks` only when **any** of these hold (per
`docs/decomposition.md`): 6+ independent requirements; work spans
2+ agent roles; 4+ files to create or modify; 2+ unrelated
domains. Otherwise keep the task whole — premature decomposition
fragments context.

Set `status: backlog` at creation; promote to `ready` only after
Requirements are concrete and an `assignee` is chosen. The
harness owns later transitions (`in-progress`, `review`,
`verified`, `done`) — do not pre-set them.
