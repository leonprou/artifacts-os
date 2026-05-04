---
assignee: technical-writer
created: 2026-05-03
depends_on:
- '[[t0086-implement-artifacts-create-body-loader]]'
id: t0087
kind: task
name: update-docs-adding-a-kind
owner: user
parent: '[[t0084-wire-artifacts-create-to-artifact]]'
started: 2026-05-03
status: done
type: documentation
---

# Update Docs Adding-A-Kind For S0018 Size Cap And Variants

# Update `docs/adding-a-kind.md` for s0018 (Size Cap and Variant Block)

## Goal

Update the kind-authoring guide (`docs/adding-a-kind.md`) to reflect
the new authoring conventions introduced by
`[[s0018-artifact-md-body-loader-for]]`:

1. The `## Skeleton` size cap (s0018 § 8.2): ≤ 400 lines / ≤ 8 KB per
   skeleton block, as an authoring guideline (not a load-time gate).
2. The `## Variants/<name>` block convention (s0018 § 5): how to
   declare per-variant skeletons, the `variant_field` frontmatter
   field, and the precedence rule (`variant:<name>` token →
   `--type` token → default `## Skeleton`).
3. Cross-link s0018 from the guide.

This task **depends on** the implementation sub-task
(`[[t0086-implement-artifacts-create-body-loader]]`) landing first
— same pattern as t0078 followed t0076 — so the doc describes
behaviour that exists, not behaviour in flight.

## Source of truth

`[[s0018-artifact-md-body-loader-for]]` § 5 (variants) and § 8
(token budget / size cap) are the binding references. The doc is
the human-facing distillation.

## Scope

1. **Reference the size cap** in the section that introduces the
   `## Skeleton` block. Cite s0018 § 8.2 for the rationale; note
   that the four shipped skeletons (`note`, `task`, `spec`,
   `research`) fit comfortably within the cap.
2. **Document the `## Variants/<name>` block convention** with a
   small worked example covering:
   - When and why to use variants.
   - The `variant_field: type` frontmatter field.
   - The selection precedence (s0018 § 5.1): explicit
     `variant:<name>` token → `--type` token (when
     `variant_field` is declared) → fallback to default
     `## Skeleton`.
   - The fact that title inference is rejected (s0018 § 5.1).
3. **Cross-link s0018** from the relevant doc sections; add it to
   the existing reference list at the bottom of the guide.

If the implementation task surfaces no further authoring
conventions beyond these three points, this task closes the
"docs touch-up" verification box on `[[t0084-wire-artifacts-create-to-artifact]]`.
Otherwise, the PM may extend the scope here before promotion.

## Out of scope

- New conventions not introduced by s0018.
- Changes to the L1 catalogue or the `description:` field
  contract — already covered by `[[t0078-update-docs-adding-a-kind]]`.
- API or CLI documentation beyond the variant fields.

## Findings

Updated `docs/adding-a-kind.md` with three additive changes:

1. **Skeleton size cap** — new `### \`## Skeleton\` body block` subsection documents the ≤ 400 lines / ≤ 8 KB authoring guideline (s0018 § 8.2, D8), explains it is a guideline not a load-time gate, and lists the four shipped skeletons with their approximate sizes.
2. **Variants convention** — new `### \`## Variants/<name>\` blocks` subsection with structural worked example (plain code block, no nested fences), the `variant_field: type` frontmatter declaration, the three-tier selection precedence (explicit `variant:<name>` → `--type` when `variant_field` declared → default `## Skeleton`), and the title-inference rejection note. Cross-links to s0018 § 5.
3. **Cross-references** — updated `variant_field` table row (was "Reserved for L2", now states actual semantics); updated `variants` row to note it is reserved for future use but does not drive selection; added s0018 entry to the guide's reference list at the bottom.

All four verification items are addressed. No code changes.

## Progress

### 2026-05-03 — technical-writer
> time: 14:51

Updated docs/adding-a-kind.md: added skeleton size-cap subsection (s0018 §8.2), variants/name block convention with worked example and precedence rule (s0018 §5.1), updated variant_field table row, cross-linked s0018 in body and reference list.

## Verification

- [x] `docs/adding-a-kind.md` mentions the ≤ 400 lines / ≤ 8 KB
      size cap with rationale from s0018 § 8.2.
- [x] `docs/adding-a-kind.md` documents the `## Variants/<name>`
      block convention with a worked example and the precedence
      rule from s0018 § 5.1.
- [x] s0018 is cross-linked from the relevant doc sections and
      from the guide's reference list.
- [x] Reviewed and approved by user.

## Verification Report

*Verified: 2026-05-03*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Size cap mentioned with s0018 § 8.2 rationale | PASS | `docs/adding-a-kind.md` lines 122-133: new `### \`## Skeleton\` body block` subsection cites s0018 § 8.2/D8, states ≤ 400 lines / ≤ 8 KB, calls it a guideline (not load-time gate), lists the four shipped skeleton sizes. |
| 2 | `## Variants/<name>` block convention with worked example and precedence (s0018 § 5.1) | PASS | Lines 135-185: structural worked example of `## Skeleton` + `## Variants/quick` + `## Variants/detailed`, `variant_field: type` frontmatter snippet, three-tier precedence (explicit `variant:<name>` → `--type` when `variant_field` declared → default `## Skeleton`), title-inference-rejected note. |
| 3 | s0018 cross-linked in body and reference list | PASS | Inline citations at lines 121, 124, 172, 185; `variant_field`/`variants` table rows updated (lines 111-112) to point at the new section / s0018 § 10; full reference entry added to Cross-References (line 480). |
| 4 | Reviewed and approved by user | PASS | Owner (`user`) invoked `/openstation.verify`; the three concrete items pass on inspection of the docs. |

### Summary

4 passed, 0 failed. All verification criteria met; ready to transition to `verified`.