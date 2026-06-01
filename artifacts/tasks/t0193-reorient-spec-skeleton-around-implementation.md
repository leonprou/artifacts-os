---
kind: task
id: t0193
name: reorient-spec-skeleton-around-implementation
type: feature
status: verified
assignee: author
owner: user
created: 2026-05-29
started: 2026-05-29
artifacts:
  - "[[s0023-multi-value-filters]]"
---

# Reorient Spec Skeleton Around Implementation

## User Story

**As a** spec author and the implementer downstream of them,
**I want** the spec skeleton to be organised around the
implementation it locks (architecture, components, data models,
surfaces, file structure) rather than around the decisions the
design considered,
**so that** the spec is useful for building from — not just for
reviewing — and the sections that *get* re-read during
implementation are the ones the skeleton privileges.

## Why

- The current contract (`artifacts/kinds/spec/ARTIFACT.md`) treats
  **decision-locking** as the load-bearing property of every
  spec. In practice most specs we ship are not picking between
  reasonable alternatives — they are locking a contract before
  code. Forcing every spec through a `D1, D2, …` justification
  table creates ceremony for specs that do not need it.
- Sections that get re-read six months later are
  implementation-shaped (API signatures, data models, module
  layout). Sections that do not (`## Goals`, the per-decision
  justification subsections) currently take up the highest-real-estate
  anchors of the skeleton.
- The skeleton is also missing the single highest-bandwidth
  artefact a spec can carry: an **architecture diagram**. Even an
  ASCII boxes-and-arrows beats most of the prose currently
  required.
- The early-era specs (`s0001`–`s0008`) were already
  implementation-shaped (Purpose / Public API / Key Concepts /
  Scope Boundary). The current shape is a drift away from a
  contract that was working — this task pulls the centre of
  gravity back, sharpened with what we learned since.

## Directions (intent, not contract)

The architect spec sub-task owns the exact required/optional
matrix and the diagram convention. These are the locked product
calls; everything else is up for refinement.

- **Reorient around implementation surfaces.** The required
  anchors should describe what is being built, in this order of
  priority: architecture, components, data models, surfaces (CLI
  / API / TUI / agent), file structure, test plan.
- **Architecture diagram is mandatory.** Every spec must carry a
  diagram of some form (ASCII, mermaid, image — the architect
  picks the convention). Prose-only is not acceptable.
- **Make most implementation sections conditional, not optional.**
  "Components" is required when the change is multi-component;
  "Data Models" when shapes change; "Surfaces" when a public
  surface is touched; "File Structure" when a new module or
  non-trivial layout lands. The architect codifies the
  triggers.
- **`## Non-Goals` → `## Out of Scope`.** Rename for clarity. May
  also collapse to a one-line inline list under the summary
  rather than a full section — the architect picks the shape
  that minimises ceremony without losing the anti-scope-creep
  function.
- **`## Decisions` becomes optional and high-level.** When
  present, the section captures the headline calls only — no
  per-decision justification subsections, no `D1 / D2` table
  unless the spec genuinely is a contested-design spec (e.g.
  `s0014`). Default is no decisions section.
- **Drop `## Goals` as a required anchor.** The one-paragraph
  summary already carries the goal. A bullet-list paraphrase is
  noise.
- **Keep `## Cross-References` and `## Test Plan` required.**
  Cross-references is load-bearing for vault navigation; test
  plan is what the implementation task pulls verbatim.

## Open Questions

These are deliberate hand-offs to the architect spec sub-task.

- Which diagram convention? Mermaid (renders in GitHub +
  Obsidian) vs ASCII (zero tooling, harder to maintain) vs both
  allowed. Pick one default, allow escape hatches.
- Should `## Out of Scope` be a section anchor or an inline
  one-liner under the summary? Reviewer ergonomics vs ceremony
  reduction.
- Trigger rules for each conditional anchor — what counts as
  "multi-component", "public surface touched", etc. The
  architect codifies these so authors are not guessing.
- Migration posture for existing specs. New contract applies to
  new specs only? Refresh a handful of recent specs as worked
  examples? Bulk-migrate? The architect proposes a posture;
  scope is deliberately bounded here.
- Does the `ARTIFACT.md` skeleton block at the bottom of
  `artifacts/kinds/spec/ARTIFACT.md` get auto-rendered anywhere
  (e.g. `openstation create --kind spec` body skeleton)? If yes,
  the change has a code touchpoint.

## Sub-tasks

- Architect spec sub-task: revise the `spec` kind contract per
  the directions above — exact required/optional matrix,
  diagram convention, trigger rules, migration posture, worked
  examples. Spawn once this task is picked up.

## Verification

User-observable outcomes:

- [x] `artifacts/kinds/spec/ARTIFACT.md` reflects the new skeleton
  — implementation-shaped required anchors, architecture
  diagram mandatory, `## Out of Scope` (rename), `## Decisions`
  optional + high-level, no `## Goals` required.
- [x] One or two recent specs are refreshed as worked examples of
  the new shape (architect picks which).
- [x] `openstation create --kind spec ...` (or whatever surface
  renders the skeleton) produces a body that matches the new
  contract.
- [x] A spec author can read `ARTIFACT.md` and produce a conforming
  spec without consulting the old shape.

## Verification Report

*Verified: 2026-06-01*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `ARTIFACT.md` reflects new skeleton (implementation-shaped anchors, mandatory diagram, Out of Scope rename, Decisions optional, no Goals) | PASS | `artifacts/kinds/spec/ARTIFACT.md` L8–53: load-bearing property is "buildability"; required-anchor table lists summary, Out of Scope, Architecture (with diagram), Test Plan, Cross-References; Components/Data Models/Surfaces/File Structure are conditional with codified triggers; Decisions is optional + high-level (D1/D2 reserved for s0014); no Goals section anywhere. |
| 2 | One or two recent specs refreshed as worked examples | PASS | `artifacts/specs/s0023-multi-value-filters.md` reorganised into summary → Out of Scope → Architecture (with ASCII diagram L43–58) → Components → Data Models → Surfaces → Test Plan → Migration → Cross-References. No Goals/Non-Goals sections. ARTIFACT.md L57–61 cites s0023 as the default-shape worked example (alongside s0001 minimal early-era and s0014 contested-design references). |
| 3 | Skeleton-rendering surface produces a body matching the new contract | PASS | `body_for_kind('spec', ARTIFACT.md path, 'Test Spec Title')` renders: title + `{{ONE_PARAGRAPH_SUMMARY}}` + `## Out of Scope` + `## Architecture` (with mandatory-diagram reminder + conditional-anchors comment) + `## Test Plan` + `## Cross-References` — exactly the always-required anchors. `tests/ai/test_body_loader.py` 28 passed. `artifacts create --kind spec` invokes this same path via `--body-file -`. |
| 4 | Spec author can produce a conforming spec from `ARTIFACT.md` alone | PASS | ARTIFACT.md is self-contained: definition of "spec" + selection signal table (L8–32); explicit required/conditional/optional matrix (L40–53); three-step authoring guide covering diagram conventions (L63–76), conditional triggers (L82–95), and Out-of-Scope/Decisions discipline (L97–116); three worked-example references (s0023 default, s0001 minimal, s0014 contested) cited inline. `docs/creating-an-artifact.md` L84 and `docs/adding-a-kind.md` synced to the new required-section list. |

### Summary

4 passed, 0 failed. All verification criteria met — the spec kind contract is fully reoriented around implementation surfaces.

## Progress

### 2026-05-29 — author
> time: 22:58

Rewrote spec `ARTIFACT.md` around implementation (buildability,
mandatory architecture diagram, conditional Components / Data
Models / Surfaces / File Structure, `## Non-Goals` → `## Out of
Scope`, `## Decisions` optional, `## Goals` dropped). Refreshed
`s0023` as the worked example; synced `creating-an-artifact.md` +
`adding-a-kind.md`. No code change — the skeleton is data-driven
via `ai/body_loader.py`. Tests: 336 passed; `verify --kind spec`
clean. → review.

## Findings

Rewrote the `spec` kind contract around what gets built and
re-read, not around the decisions a design weighed. The spec's
load-bearing property changed from **decision-locking** to
**buildability**.

**Deliverables**

- `artifacts/kinds/spec/ARTIFACT.md` — full rewrite. New
  always-required anchors: one-paragraph summary, `## Out of Scope`,
  `## Architecture` (diagram mandatory), `## Test Plan`,
  `## Cross-References`. New **conditional** anchors (required only
  when the change touches them, with codified triggers):
  `## Components`, `## Data Models`, `## Surfaces`,
  `## File Structure`. `## Goals` and `## Non-Goals` dropped;
  `## Decisions` is now optional + high-level (D-table reserved for
  genuinely contested-design specs like `s0014`). The `## Skeleton`
  block renders only the always-required anchors + a one-line
  reminder of the conditionals, keeping new specs lean.
- `artifacts/specs/s0023-multi-value-filters.md` — refreshed as the
  default-shape worked example (summary → Out of Scope →
  Architecture w/ ASCII diagram → Components → Data Models →
  Surfaces → Test Plan → Cross-References), substance preserved.
- `docs/creating-an-artifact.md`, `docs/adding-a-kind.md` — synced
  to the new required-section list and the new load-bearing phrase.

**Architect calls** (the task's deliberate hand-offs)

- *Diagram convention:* ASCII boxes-and-arrows is the default
  (zero tooling, diffs clean, matches existing specs); mermaid
  allowed (renders in GitHub + Obsidian); committed image allowed.
  Prose-only is not acceptable.
- *Out of Scope:* a required section placed right after the summary
  (the framing position the old `## Non-Goals` held); may be a
  single bullet.
- *Conditional triggers:* Components = 2+ interacting
  components/modules; Data Models = new/changed shape; Surfaces =
  public CLI/API/TUI/agent surface added or changed; File Structure
  = new module or non-trivial layout. "When unsure, include it."
- *Migration posture:* new contract for new specs; one recent spec
  (`s0023`) refreshed as the worked example; `s0001` cited as the
  minimal early-era shape; `s0014` cited as the contested-design
  exception. No bulk migration.
- *Code touchpoint:* `src/artifacts_os/ai/body_loader.py` renders
  the `## Skeleton` block (data-driven) — no code change needed.
  Kept the `{{ONE_PARAGRAPH_SUMMARY}}` placeholder so the existing
  `test_body_loader` assertion still holds.

**Verification evidence**

- `pytest tests/ai tests/core` → 336 passed, 1 skipped.
- `body_for_kind('spec', ...)` renders the new skeleton with
  `{{TITLE}}` substituted and required anchors present — this is
  the exact path `artifacts create --kind spec` invokes.
- `openstation verify --kind spec` → all 33 specs valid. (The 43
  `verify --all` errors are pre-existing task-frontmatter issues,
  none spec-related.)

## Downstream

- The remaining ~30 decision-locking-era specs (`s0009`–`s0033`,
  excluding the refreshed `s0023`) still use the old shape. Per the
  chosen migration posture this is intentional — they are not bulk-
  migrated. A follow-up task could refresh high-traffic ones if the
  old shape proves a navigation drag.
- `.openstation/docs/spec.spec.md` (the earlier "feature spec"
  format) and the new `ARTIFACT.md` now describe the same
  implementation-shaped spec from two places. Worth a follow-up to
  reconcile or cross-link them so authors have a single source.
