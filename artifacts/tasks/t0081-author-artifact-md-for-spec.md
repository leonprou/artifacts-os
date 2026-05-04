---
artifacts:
  - '[[artifacts/kinds/spec/ARTIFACT.md]]'
assignee: author
created: 2026-05-03
id: t0081
kind: task
name: author-artifact-md-for-spec
owner: user
parent: '[[t0079-artifact-md-artifacts-ai-extension]]'
status: done
type: documentation
started: 2026-05-03
completed: 2026-05-04
---

# Author ARTIFACT.md for `spec` Kind

## Goal

Author `artifacts/kinds/spec/ARTIFACT.md` so the L1 catalogue
shows a meaningful `description` for the `spec` kind, and so the
architect agent (and any human author) has a stable skeleton when
drafting new specs.

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

`[[artifacts/kinds/note/ARTIFACT.md]]` — v1 exemplar shape.

`[[s0017-artifact-kinds-discovery-mechanism]]` § 6 — the
locked `description:` field contract. Consult only if
`docs/adding-a-kind.md` doesn't answer a contract question.

## Scope

1. Create `artifacts/kinds/spec/ARTIFACT.md`.
2. Frontmatter:
   - `name: spec`
   - `description:` — anchor "what" in design-doc semantics
     (locks contract before implementation; lifecycle draft →
     review → approved → deprecated) and "when" in the concrete
     trigger (technical contract is non-obvious; an architect
     needs to lock decisions before code is written).
   - `applies_to: spec`
   - `placeholder_syntax`, `schema_version` per exemplar.
3. `## How to use` prose: when to file a spec vs when to skip
   straight to implementation; how to engage research artifacts;
   the `LOCK` / `LOCK-WITH-EDIT` / `REJECT` engagement pattern
   (used in s0017 § 10); when to descope (s0017 § 13 is a worked
   example).
4. `## Skeleton` shaped after recent well-formed specs (s0014,
   s0017): Background / Goals & Non-goals / Locked decisions
   table / Layered model (if applicable) / Surfaces / Test plan /
   r0002-style engagement table where research drove the design /
   Next steps / Cross-references.

## Constraints

- **No new design** — consumes the `description:` contract from
  s0017 § 6.
- **Lift from real specs.** Survey s0002 (architecture), s0014
  (unified filter API), s0017 (kinds discovery) — they show the
  conventions to encode.
- **One-deep nesting** for any declared playbooks.

## Verification

- [x] `artifacts/kinds/spec/ARTIFACT.md` exists with valid
      frontmatter.
- [x] `description` honours s0017 § 6.
- [x] `artifacts kinds` shows the description for `spec`.
- [x] `## How to use` and `## Skeleton` sections present.
- [x] Reviewed and approved by user.

## Verification Report

*Verified: 2026-05-04*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | ARTIFACT.md exists with valid frontmatter | PASS | `artifacts/kinds/spec/ARTIFACT.md` (107 lines) loads cleanly into the L1 catalogue. The frontmatter contract was simplified during the manual rewrite to `name + description` only, matching the redesigned `note/ARTIFACT.md` exemplar. |
| 2 | description honours s0017 § 6 (≤ 1024 chars, third-person, what + when) | PASS | 232 chars; third-person ("Locks a technical contract…"); names *what* (goals, non-goals, decisions, surfaces) and *when* (alternatives worth recording, crosses module boundary, lands across multiple tasks). |
| 3 | `artifacts kinds` shows the description for `spec` | PASS | CLI table renders the populated description cell for `spec`; `-j` returns `description` non-null and `has_template: true`. |
| 4 | `## How to use` and `## Skeleton` sections present | PASS | Section names migrated to the current exemplar shape: `## What is a spec?` + `## How to draft a spec` (3 numbered steps). The intent — a how-to-author guide plus a body template — is met. The skeleton is woven through Step 3 ("Anchor required sections") with required vs optional anchors enumerated, rather than a separate fenced block; this matches how the redesigned `note` and `task` exemplars present their templates. |
| 5 | Reviewed and approved by user | PASS | User confirmed manually-completed work in conversation 2026-05-04 and asked the project-manager to follow up the workflow. |

### Summary

5 passed, 0 failed. Task ready to transition `review → verified → done`.

## Progress

### 2026-05-03 — author
> time: 09:52

Authored `artifacts/kinds/spec/ARTIFACT.md` per scope.
Frontmatter (description 384 chars, name/applies_to=spec,
placeholder_syntax/schema_version per note exemplar) loaded
cleanly into L1 catalogue (`artifacts kinds` shows the
description; `-j` returns `has_template=true`). `## How to use`
covers when-to-file (incl. skip criteria), LOCK / LOCK-WITH-EDIT
/ REJECT engagement pattern (s0017 § 10), descope discipline
(s0017 § 13), status lifecycle. `## Skeleton` lifts shape from
s0014 / s0017: Background, Goals + Non-goals, Locked Decisions
table, optional Layered Model, Surfaces, Test Plan, optional
research engagement table, optional Next Steps and Scope
History, Cross-References. Tests green: 25 passed / 1 skipped
in `tests/core/test_registry.py` + `test_kinds_catalog.py`.
Transitioning to review.

## Findings

Authored `artifacts/kinds/spec/ARTIFACT.md` matching the v1 exemplar
shape (`note/ARTIFACT.md`) and lifting conventions from `s0002`,
`s0014`, and `s0017`.

**Frontmatter** — `name: spec`, `applies_to: spec`,
`placeholder_syntax: "{{NAME}}"`, `schema_version: 1`.
`description` (384 chars, well under the 1024 cap) anchors *what*
in design-doc semantics ("design documents that lock a technical
contract … API shapes, validation rules, layered models,
cross-module boundaries") and *when* in the concrete trigger
("when an architect needs to freeze goals, non-goals, and
load-bearing decisions before code is written"), with the
lifecycle (`draft → review → approved → deprecated`) tail per
s0017 § 6.1. No XML tags, no reserved words, third-person voice.

**`## How to use` prose** — eight numbered steps:
1. Decide whether a spec is the right artifact (signals table +
   skip-the-spec criteria — bias is to *not* file a spec when a
   note suffices).
2. Engage research with `LOCK` / `LOCK-WITH-EDIT` / `REJECT`,
   pointing at s0017 § 10 as the worked example.
3. Pin goals **and** non-goals — non-goals do double duty:
   reviewer signal + scope-creep guard for the implementation
   task.
4. Lock decisions in a table, justify them in prose; flag
   load-bearing decisions per s0014 § 5's "if any one reason is
   contested, revisit before implementation" pattern.
5. Descope rather than ship sprawling specs (s0017 § 13's three
   revision entries cited as the worked example). Descope before
   review, not after.
6. Set the right `status` on creation — explicit lifecycle table.
7. Cross-reference, do not duplicate (links every flavour of
   upstream input the survey of s0002/s0014/s0017 surfaces).
8. Emit the skeleton — drop optional sections that do not apply,
   renumber to keep TOC contiguous.

**`## Skeleton`** — eleven numbered top-level sections marked
required vs optional:

1. Background and Cross-References (bullet-per-input shape from
   s0014 § 1 / s0017 § 1).
2. Goals and Non-Goals — both subsections required.
3. Locked Decisions Summary table.
4. Layered Disclosure Model (optional; only when the spec
   introduces a layered surface — s0017 § 4).
5. Surfaces (per-surface aspect tables from s0017 § 5; backwards-
   compatibility table from s0017 § 8.3).
6. Test Plan grouped by property (s0017 § 9).
7. Research engagement table (optional; one row per recommendation
   with `LOCK` / `LOCK-WITH-EDIT` / `REJECT` + rationale).
8. Implementation Notes (optional; pre-populates the follow-up
   task's scope).
9. Next Steps — Deferred Work (only when scope was reduced).
10. Scope History (optional; one bullet per major revision).
11. Cross-References — required.

**Verification evidence**:
- `artifacts kinds` table now shows the `spec` description (no
  longer `(no description)`).
- `artifacts kinds -j` for `spec` returns
  `has_template: true`, populated `description`.
- `pytest tests/core/test_registry.py tests/core/test_kinds_catalog.py`
  → 25 passed, 1 skipped (no regressions).
- `artifacts validate` reports the only error on r0001 (missing
  `created`), pre-existing and unrelated.

**Design choices worth flagging**:
- The skeleton encodes the s0017 r0002 engagement pattern with a
  parametrised research ref (`{{RESEARCH_REF}}`) rather than
  hard-coding `r0002`, so future specs that engage different
  research artifacts can use the same scaffold.
- Step 1 ("Decide whether a spec is the right artifact") leads
  with skip-criteria so the agent layer pushes back when a note
  would suffice — this matters because specs carry the cost of an
  approved lifecycle and over-filing dilutes the surface.
- Per the task's "one-deep nesting" constraint, the skeleton does
  not declare any playbooks — the `playbooks:` frontmatter field
  is reserved for L2 (s0017 § 7.2) and not surfaced in v1.