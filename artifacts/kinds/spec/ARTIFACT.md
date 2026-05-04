---
name: spec
description: Locks a technical contract — goals, non-goals, decisions, and the surfaces they imply — before implementation begins. Use when a design has alternatives worth recording, crosses a module boundary, or will land across multiple tasks.
---

# Spec

## What is a spec?

A **spec** is a design document that locks a technical contract
before implementation begins. It records goals, non-goals, the
decisions the design is committing to, and the surfaces those
decisions imply, in a form a reviewer can approve and a follow-up
implementation task can build against without re-deriving the
design. Its load-bearing property is **decision-locking**: every
choice that shapes the contract earns a row in a decisions table
plus a subsection of justification, so post-approval drift is
visible.

Reach for a spec when at least one signal holds:

| Signal | Why a spec |
|---|---|
| Two or more reasonable designs and the choice is non-obvious | The locked-decisions table records which alternative won and why. |
| The change crosses a module boundary in the dependency DAG | The Surfaces section pins the contract each module sees. |
| Implementation will land across multiple tasks | The approved spec is the shared north star for the sub-tasks. |
| A public surface (CLI, TUI, agent, API) needs parity or backwards-compat guarantees | "Why X + Y, not just X" justifications belong in a spec, not a PR. |
| Validation, error-routing, or compat rules are load-bearing | These rules drift easily; a spec freezes them. |

If none holds, prefer a `task` (mechanical change, no decision
points) or a `note` (`type: decision` already locks the rationale,
no new surface to design).

## How to draft a spec

A spec has no fixed skeleton. Several sections are required because
they *are* the spec's accountability surface; everything else is
shaped to fit the design. `s0014` and `s0017` are worked examples.

### Step 1 — Lock decisions, do not paraphrase

Every load-bearing choice earns a row in a `## Locked Decisions
Summary` table (`D1`, `D2`, …) plus a dedicated subsection later in
the spec where trade-offs, rejected alternatives, and rationale
live. The table is for skimmers; the subsections are for reviewers
reconstructing the rationale.

When upstream research informed the design, reproduce its
recommendation list as an engagement table — one row per
recommendation with an explicit `LOCK` / `LOCK-WITH-EDIT` /
`REJECT` verdict. No silent drops; a reviewer reading only that
table can tell which research input shaped which decision.
`s0017` § 10 is the worked example.

### Step 2 — Pin goals AND non-goals; descope before sprawl

Goals are mandatory; **non-goals are also mandatory.** Non-goals
tell the reviewer what the spec is *not* taking responsibility for,
and give the implementation task an authoritative answer when
scope creep arrives mid-work. Cross-link deferred items to a
`## Next Steps` section that sketches them well enough to file
follow-up specs.

If the spec is growing past what a single reviewer can hold in
their head, **descope before review, not after.** Push deferred
sections into `## Next Steps` and record the cut as a numbered
entry in `## Scope History`. A spec that needs cutting in half
during review almost always splits poorly. `s0017` § 13 is the
worked example.

### Step 3 — Anchor required sections; respect the lifecycle

The spec's required structure (`## Surfaces` is conditional on
touching a public API; the rest are always required):

- **`## Background and Cross-References`** — every upstream input
  as a one-line bullet (prompting task, parent/sibling specs,
  research, notes, code paths).
- **`## Goals` + `## Non-Goals`** — see Step 2.
- **`## Locked Decisions Summary` + per-decision subsections** —
  see Step 1.
- **`## Surfaces`** *(when the spec touches a public surface)* —
  pin signatures, input/output shapes, and backwards-compat impact
  per surface.
- **`## Test Plan`** — grouped by the property each test verifies
  (layer-isolation, contract validation, parity, compat); the
  implementation task pulls this section verbatim into its work
  plan.
- **`## Cross-References`** — every artifact and code path the
  spec consumes or affects. Bare wikilinks (`[[s0017-...]]`)
  auto-resolve in the vault. Never copy text from a referenced
  artifact — link and consume.

Optional anchors when the spec calls for them: `## Layered
Disclosure Model` (genuinely layered surfaces only — do not force
non-layered designs into a layer table), `## Scope History`
(descope or restructure during review), `## Next Steps` (deferred
work), `## Implementation Notes` (pre-populate the follow-up
task's scope).

Set `status: draft` on creation; advance to `review` after a
self-check, `approved` after reviewer sign-off, `deprecated` if
superseded. Implementation tasks must wait for `approved`. If
implementation reveals a flaw, amend the spec under a new
`## Scope History` entry — never let code drift from the approved
contract.
