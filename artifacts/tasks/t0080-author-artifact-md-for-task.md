---
artifacts:
  - '[[artifacts/kinds/task/ARTIFACT.md]]'
assignee: author
created: 2026-05-03
id: t0080
kind: task
name: author-artifact-md-for-task
owner: user
parent: '[[t0079-artifact-md-artifacts-ai-extension]]'
status: done
type: documentation
started: 2026-05-03
completed: 2026-05-04
---

# Author ARTIFACT.md for `task` Kind

## Goal

Author `artifacts/kinds/task/ARTIFACT.md` so the L1 catalogue
(shipped by `[[t0076-implement-l1-kinds-catalogue-s0017]]`) shows
a meaningful `description` for the `task` kind, and so agents
drafting new tasks have a stable body skeleton to follow.

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

`[[artifacts/kinds/note/ARTIFACT.md]]` — the v1 exemplar on
disk. Its shape (frontmatter → `## How to use` → `## Skeleton`
with optional `## Variants/<name>` blocks) is the pattern to
follow.

`[[s0017-artifact-kinds-discovery-mechanism]]` § 6 — the
locked `description:` field contract. Consult only if
`docs/adding-a-kind.md` doesn't answer a contract question.

## Scope

1. Create `artifacts/kinds/task/ARTIFACT.md`.
2. Frontmatter:
   - `name: task`
   - `description:` per s0017 § 6 — required, ≤ 1024 chars,
     third-person, encodes both *what* the kind is and *when* to
     choose it. Anchor "what" in the lifecycle (backlog → ready →
     in-progress → review → verified → done) and "when" in the
     concrete trigger (planned work item with verifiable
     acceptance criteria, owner, assignee).
   - `applies_to: task`
   - `placeholder_syntax`, `schema_version` per the note
     exemplar.
3. `## How to use` prose: how to pick `type` (feature,
   implementation, spec, documentation, research, refactor); when
   to set `parent`, `assignee`, `owner`, `priority`; the
   verification-checklist convention (`- [ ]` items the verifier
   ticks).
4. `## Skeleton` body shaped after the conventions in recent
   well-formed tasks (t0050–t0078): Goal / Source of truth /
   Implementation steps or Scope / Out of scope / Constraints /
   Test plan or Deliverable / Verification.
5. Optional variants if a few task-types have meaningfully
   different body shapes (e.g. `bug` tasks want a Root-cause
   section; `spec` tasks want a Findings/Verification Report
   section). Keep variants minimal — only declare what's
   load-bearing.

## Constraints

- **No new design.** The `description:` field contract is locked
  in s0017 § 6. This task consumes it.
- **Lift conventions from real artifacts.** Survey at least five
  recent `done` tasks before drafting the skeleton; the template
  should reproduce what a good task body already looks like.
- **No CLI / loader changes.** This is pure authoring under
  `artifacts/kinds/task/`.
- **One-deep nesting.** If you declare `playbooks:`, each playbook
  file lives one level deep at `artifacts/kinds/task/playbooks/<name>.md`.

## Findings

Created `artifacts/kinds/task/ARTIFACT.md` following the shape of
the v1 exemplar `artifacts/kinds/note/ARTIFACT.md`: frontmatter →
`## How to use this template` (numbered Steps) → `## Skeleton` (a
fenced-markdown body template with `{{TOKEN}}` placeholders and
HTML-comment guidance).

**Frontmatter.** `name: task`, `applies_to: task`,
`placeholder_syntax: "{{NAME}}"`, `schema_version: 1`. Description
is 494 chars (well under the 1024 cap), third-person, and encodes
both halves required by s0017 § 6:

- *what* — "Body template for task artifacts — planned units of
  work shaped for execution by a single agent or person."
- *when* — names the lifecycle (`backlog → ready → in-progress →
  review → verified → done`, with `cancelled`/`rejected` for
  descoped work) and the closed `type` enum (`feature`,
  `implementation`, `spec`, `documentation`, `research`,
  `refactor`), so an agent picking a kind can immediately tell
  whether `task` is the right match.

`artifacts kinds` now shows the populated description row;
`artifacts kinds -j` returns `description` non-null and
`has_template: true` for `task`. The existing 24-test catalogue
suite (`tests/core/test_kinds_catalog.py`,
`tests/cli/test_kinds.py`) continues to pass with no warnings
attributable to this kind.

**`## How to use` (7 steps).**

1. Pick the `type` — closed-enum table mapping each value to the
   *output* it produces (not the activity), with a short
   tie-breaker rule for `feature` vs `implementation` and explicit
   guidance that bug fixes file as `implementation`/`refactor` (no
   `bug` type exists in the schema).
2. Pick lifecycle fields — table covering `status`, `assignee`,
   `owner`, `priority`, `parent`, `depends_on`, `artifacts`,
   `created`, with a clear note that the harness owns most status
   transitions.
3. Write requirements that are testable — numbered-list vs
   prose-with-H3 patterns, plus a hint that requiring rationale
   means the task is mis-typed.
4. Lock the verification checklist — convention that `- [ ]` items
   are true-or-false at completion, plus an anti-pattern table
   contrasting subjective rubrics with verifiable properties, and
   the explicit "Reviewed and approved by `<owner>`" final gate.
5. Cite, do not duplicate — when a spec/plan/research artifact
   binds the task, link to it under `## Source of truth` and keep
   the task body to pointers. `t0076` cited as the worked example.
6. Decompose only when needed — restates the four
   `docs/decomposition.md` triggers (6+ requirements, 2+ agent
   roles, 4+ files, 2+ unrelated domains).
7. Emit the skeleton — instructions on which sections to drop for
   each `type` and which sections (`## Findings`, `## Progress`,
   `## Verification Report`) are written during execution rather
   than at draft time.

**`## Skeleton`.** Single fenced markdown block reproducing the
shape observed across t0050, t0058, t0064, t0066, t0070, t0072,
t0074, t0075, t0076, t0078:

- `# Title`, optional one-paragraph summary
- `## User story` — required for `feature`
- `## Why` — strategic context for umbrellas
- `## Source of truth` — required for tasks backed by a spec or
  plan; cites the binding artifact
- `## Context` — background links and current state
- `## Goal` — single-outcome statement (used in lieu of/alongside
  User story)
- `## Requirements` — REQUIRED; numbered or H3-grouped
- `## Out of scope` — required for impl tasks backed by a spec
- `## Constraints` — load-bearing rules (DAG, atomic writes,
  backwards-compat)
- `## Test plan` — for `implementation`/`refactor`
- `## Subtasks` — required for `feature` umbrellas (manifest
  table mirroring the `subtasks:` frontmatter list)
- `## Progress` — append-only execution log
- `## Findings` — REQUIRED at completion; type-specific content
  table copied from `task.spec.md`
- `## Downstream` — follow-up work surfaced during execution
- `## Verification` — REQUIRED checklist, with the explicit
  "Reviewed and approved by `<owner>`" gate
- `## Verification Report` — machine-written by
  `/openstation.verify`; included so canonical section order is
  documented

**Variants — none declared.** s0017 reserves `variant_field` /
`variants` for L2 (deferred). Surveying the recent done-task
corpus, the six `type` values share enough common spine (Goal +
Requirements + Verification + Findings) that a single skeleton
with optional sections covers them faithfully — no `type` needs a
genuinely different shape. Bug fixes file under
`implementation`/`refactor` and use the existing `## Context` /
`## Root cause` slots; the constraint to "keep variants minimal —
only declare what's load-bearing" is honoured by declaring none.

**No CLI / loader changes** — pure authoring under
`artifacts/kinds/task/`. No `playbooks:` declared, so the
one-deep-nesting constraint does not apply.

## Progress

### 2026-05-03 10:18:38 — Incomplete run (r0100)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$3.53, turns=51

### 2026-05-03 10:34 — author

Resumed after the r0100 incomplete run. `artifacts/kinds/task/ARTIFACT.md`
was already on disk in its final shape with Findings recorded; this
session re-verified the artifact end-to-end and found nothing to amend.

- Frontmatter present and well-formed: `name: task`, `applies_to: task`,
  `placeholder_syntax: "{{NAME}}"`, `schema_version: 1`, plus a
  `description` of **494 chars** (third-person, encodes both *what*
  the kind is and *when* to choose it via the lifecycle and `type`
  enum) — under the s0017 § 6 cap of 1024.
- `artifacts kinds` renders a populated `description` cell for `task`
  (no `(no description)`).
- `artifacts kinds -j` returns `description` non-null and
  `has_template: true` for `task`.
- The 24-test catalogue suite (`tests/core/test_kinds_catalog.py`,
  `tests/cli/test_kinds.py`) passes (24 passed, 1 skipped).
- `## How to use this template` (7 steps) and `## Skeleton` (fenced
  markdown block with `{{TOKEN}}` placeholders + HTML-comment
  guidance) match the v1 exemplar `artifacts/kinds/note/ARTIFACT.md`
  shape; no variants declared.

Transitioning to `review` for owner approval.

## Verification

- [x] `artifacts/kinds/task/ARTIFACT.md` exists with valid
      frontmatter (`name`, `description`, `applies_to`,
      `placeholder_syntax`, `schema_version`).
- [x] `description` honours s0017 § 6: ≤ 1024 chars, third-person,
      what + when.
- [x] `artifacts kinds` shows the new description for `task` (no
      `(no description)` row).
- [x] `artifacts kinds -j` returns `description` non-null and
      `has_template=true` for `task`.
- [x] `## How to use` and `## Skeleton` sections present and
      faithful to the note exemplar's shape.
- [x] Reviewed and approved by user.

## Verification Report

*Verified: 2026-05-04*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | ARTIFACT.md exists with valid frontmatter | PASS | `artifacts/kinds/task/ARTIFACT.md` (212 lines) loads cleanly into the L1 catalogue. Frontmatter contract was simplified during the manual rewrite to `name + description` only — `applies_to` / `placeholder_syntax` / `schema_version` are no longer required (the current `note/ARTIFACT.md` exemplar reflects the same simplification). |
| 2 | description ≤ 1024 chars, third-person, what + when | PASS | 211 chars; third-person ("Captures a planned unit of work…"); names *what* (planned unit of work with verifiable acceptance criteria, owner, assignee) and *when* (single deliverable an agent or person can complete and a verifier can accept). |
| 3 | `artifacts kinds` shows the new description for `task` | PASS | CLI table renders `task` with the populated description cell — no `(no description)`. |
| 4 | `artifacts kinds -j` returns `description` non-null and `has_template=true` for `task` | PASS | JSON output has `description` populated and `has_template: true` for `task`. |
| 5 | `## How to use` and `## Skeleton` sections present and faithful to the note exemplar's shape | PASS | The note exemplar itself was redesigned during this work to use `## What is a {kind}?` + `## How to draft a {kind}` (3 numbered steps). `task/ARTIFACT.md` mirrors that current shape — the literal section names in the criterion are stale, but the intent ("faithful to the note exemplar") is met. |
| 6 | Reviewed and approved by user | PASS | User confirmed manually-completed work in conversation 2026-05-04 and asked the project-manager to follow up the workflow. |

### Summary

6 passed, 0 failed. Task ready to transition `review → verified → done`.