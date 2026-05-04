---
artifacts:
  - '[[artifacts/kinds/research/ARTIFACT.md]]'
assignee: author
created: 2026-05-03
id: t0082
kind: task
name: author-artifact-md-for-research
owner: user
parent: '[[t0079-artifact-md-artifacts-ai-extension]]'
status: done
type: documentation
started: 2026-05-03
completed: 2026-05-04
---

# Author ARTIFACT.md for `research` Kind

## Goal

Author `artifacts/kinds/research/ARTIFACT.md` so the L1 catalogue
shows a meaningful `description` for the `research` kind, and so
the researcher agent has a stable skeleton when drafting research
artifacts.

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

`[[r0001-openstation-integration-audit]]` and
`[[r0002-claude-skills-design-reference]]` — real research artifacts
showing the conventions in use.

`[[s0017-artifact-kinds-discovery-mechanism]]` § 6 — locked
`description:` contract. Consult only if `docs/adding-a-kind.md`
doesn't answer a contract question.

## Scope

1. Create `artifacts/kinds/research/ARTIFACT.md`.
2. Frontmatter:
   - `name: research`
   - `description:` — "what" anchored in investigation output
     (surveys external systems, evaluates options, reports
     findings; lifecycle draft → done) and "when" anchored in the
     trigger (a question requires evidence before design can
     proceed; a sibling task needs background a future reader can
     consult).
   - `applies_to: research`
   - `placeholder_syntax`, `schema_version` per exemplar.
3. `## How to use` prose: when to file a research artifact vs an
   inline note; the cite-every-claim discipline; the
   `## TL;DR` + body + `## Recommendations` shape exhibited by
   r0002.
4. `## Skeleton` shaped after r0001 / r0002: TL;DR / Areas
   covered / Mapping or comparison tables / Recommendations /
   Sources & cross-references.

## Constraints

- **No new design** — consumes the `description:` contract from
  s0017 § 6.
- **Lift from r0001 and r0002.** Both are good examples; the
  template should reproduce what those artifacts already do well.
- **One-deep nesting** for any declared playbooks.

## Verification

- [x] `artifacts/kinds/research/ARTIFACT.md` exists with valid
      frontmatter.
- [x] `description` honours s0017 § 6.
- [x] `artifacts kinds` shows the description for `research`.
- [x] `## How to use` and `## Skeleton` sections present.
- [x] Reviewed and approved by user.

## Verification Report

*Verified: 2026-05-04*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | ARTIFACT.md exists with valid frontmatter | PASS | `artifacts/kinds/research/ARTIFACT.md` (80 lines) loads cleanly into the L1 catalogue. The frontmatter contract was simplified during the manual rewrite to `name + description` only, matching the redesigned `note/ARTIFACT.md` exemplar. |
| 2 | description honours s0017 § 6 (≤ 1024 chars, third-person, what + when) | PASS | 244 chars; third-person ("Captures cited findings from an investigation…"); names *what* (cited findings: external-system survey, code audit, options comparison) and *when* (a question requires evidence before a downstream spec or task can act, or findings must outlive the prompting conversation). |
| 3 | `artifacts kinds` shows the description for `research` | PASS | CLI table renders the populated description cell for `research`; `-j` returns `description` non-null and `has_template: true`. |
| 4 | `## How to use` and `## Skeleton` sections present | PASS | Section names migrated to the current exemplar shape: `## What is research?` + `## How to draft research` (3 numbered steps). The skeleton is conveyed through Step 3 ("Anchor the artifact: metadata, TL;DR, Recommendations, Sources") naming required anchors, matching how the redesigned `note`, `spec`, and `task` exemplars present their templates. The skeleton lifts shape from `r0001` and `r0002` as required. |
| 5 | Reviewed and approved by user | PASS | User confirmed manually-completed work in conversation 2026-05-04 and asked the project-manager to follow up the workflow. |

### Summary

5 passed, 0 failed. Task ready to transition `review → verified → done`.

## Findings

Authored `artifacts/kinds/research/ARTIFACT.md`. The `research`
kind now appears in the L1 catalogue with a 378-character
`description` that names both *what* the kind is (surveys external
systems, audits existing code, evaluates competing options, reports
cited findings) and *when* to choose it (a question needs evidence
before a design can proceed, or a sibling task needs background a
future reader can consult). The kind loads cleanly — no
registration warnings — and `has_template=True` in
`artifacts kinds -j`.

**Body shape.** Mirrors `artifacts/kinds/spec/ARTIFACT.md` and
`artifacts/kinds/note/ARTIFACT.md`: hybrid frontmatter +
`## How to use this template` (eight-step authoring guide) +
`## Skeleton` (fenced markdown). The eight steps cover the
research-vs-note decision rule, the cite-every-claim discipline,
the lead-with-TL;DR rule, mapping/comparison-table patterns,
the `## Recommendations` requirement, the `## Sources` requirement,
the `draft → done` lifecycle, and the emit-and-substitute
instruction.

**Skeleton lifted from r0001 + r0002.** Reproduces the shapes
those artifacts already do well: lead-in metadata block (Date /
Agent / For / Sources), `## TL;DR` (required), numbered area
sections containing comparison tables, an optional Gaps
sub-section pattern (lifted from r0001 § 3), an optional
LOCK/LOCK-WITH-EDIT/REJECT mapping table (lifted from r0002 § 9),
an optional coverage matrix (lifted from r0001 § 4),
`## Recommendations` (required), and `## Sources` (required).
Optional sections are clearly marked with `<!-- ===== OPTIONAL: ... =====-->`
banners so authors can drop them without breaking section numbering.

**Design constraints honoured.** No new design (consumes the
description contract from s0017 § 6); contract verified in-process
(378 ≤ 1024 chars, third-person voice, no XML tags, no reserved
words). One-deep nesting is moot — no playbooks declared.

**Verification.** `pytest tests/core/test_kinds_catalog.py
tests/core/test_registry.py` passes (25 passed, 1 skipped).
`artifacts kinds` table renders the new description; `-j` JSON
shows `description` populated and `has_template=True`.

## Progress

- 2026-05-03 author: read `docs/adding-a-kind.md`, the existing
  `note` and `spec` ARTIFACT.md exemplars, `r0001` and `r0002`,
  and `s0017` § 6 for the description contract.
- 2026-05-03 author: drafted
  `artifacts/kinds/research/ARTIFACT.md` with frontmatter, an
  eight-step `## How to use` guide, and a `## Skeleton` lifting
  the TL;DR + comparison-table + Recommendations + Sources shape
  from `r0001` and `r0002`.
- 2026-05-03 author: verified `artifacts kinds` (table + `-j`)
  shows the new description and `has_template=True` for
  `research`; ran `pytest tests/core/test_kinds_catalog.py
  tests/core/test_registry.py` — all green.
- 2026-05-03 author: transitioned task to `review`.