---
created: 2026-05-03
id: r0003
kind: research
name: artifacts-usage
---

# Artifacts usage

**Date:** {{YYYY-MM-DD}}
**Agent:** {{AGENT_NAME}}
**For:** [[{{PROMPTING_TASK_OR_SPEC}}]]
**Sources:** [{{SOURCE_NAME}}]({{URL}}), [{{SOURCE_NAME}}]({{URL}})

<!-- The lead-in metadata block grounds the artifact in time,
     authorship, and the question it answers. `For:` links the
     prompting task or spec — the surface that will consume the
     findings. `Sources:` previews the load-bearing external
     references; the full list lives in the final section. Drop
     the `Sources:` line if the investigation is purely internal
     (code audit, sibling-artifact synthesis). -->

---

## TL;DR

{{HEADLINE_FINDING_ONE_SENTENCE}}

{{QUANTIFIED_SHAPE_OF_THE_RESULT}}

{{FORWARD_POINTERS_TO_BODY_SECTIONS}}

<!-- REQUIRED. Two to four paragraphs. Open with the conclusion;
     state the size or shape of the finding (numbers, counts,
     percentages); end with a one-sentence map of what the body
     covers so a reader who only needs the headline can stop. -->

---

## 1. {{AREA_OR_DIMENSION}}

{{ONE_PARAGRAPH_INTRO}}

| {{DIMENSION}} | {{SYSTEM_A_OR_OPTION_A}} | {{SYSTEM_B_OR_OPTION_B}} |
|---|---|---|
| {{ROW_LABEL}} | {{VALUE_WITH_CITATION}} | {{VALUE_WITH_CITATION}} |

<!-- Side-by-side comparison table. Use when the investigation
     contrasts two systems or two options across many dimensions.
     Lift the shape from r0001 § 1 ("Architectural shape, side by
     side"). Each cell either states a fact with a source or
     names a gap explicitly ("none", "n/a"). -->

## 2. {{AREA_OR_DIMENSION}}

{{ONE_PARAGRAPH_INTRO}}

| Capability | {{SOURCE_SYSTEM}} today | {{TARGET_SYSTEM}} equivalent |
|---|---|---|
| {{CAPABILITY}} | {{CURRENT_IMPLEMENTATION}} | {{REPLACEMENT_OR_GAP}} |

<!-- Coverage / mapping table. Use when one system is being
     audited against another (e.g. "what already exists vs what
     is missing"). r0001 § 2 ("What is already covered by
     artifacts-os") is the worked example. End the section with
     a "bottom line" sentence that quantifies the result. -->

<!-- ===== OPTIONAL: gaps or sub-areas warrant their own subsections ===== -->

## 3. {{GAPS_OR_SUB_AREAS}}

### 3.1 {{SUB_AREA}}

{{NARRATIVE_WITH_CITATIONS}}

**Recommendation:** {{ONE_LINE_DIRECTIONAL_NOTE}}

<!-- Use when the investigation enumerates multiple gaps,
     sub-systems, or open questions, each warranting its own
     paragraph. Each subsection ends with a directional
     recommendation that the final ## Recommendations section
     will reference. r0001 § 3 ("Gaps in artifacts-os") is the
     worked example with eleven sub-sections. -->

<!-- ===== OPTIONAL: research consumed informs a follow-up spec ===== -->

## 4. Mapping Table

| Concept | {{SOURCE_FRAME}} | {{TARGET_FRAME}} | Verdict | Rationale |
|---|---|---|---|---|
| {{CONCEPT}} | {{SOURCE_REPRESENTATION}} | {{TARGET_REPRESENTATION}} | **adopt** | {{ONE_LINE_RATIONALE}} |
| {{CONCEPT}} | {{SOURCE_REPRESENTATION}} | {{TARGET_REPRESENTATION}} | **adapt** | {{WHAT_NARROWED_AND_WHY}} |
| {{CONCEPT}} | {{SOURCE_REPRESENTATION}} | {{TARGET_REPRESENTATION}} | **reject** | {{CONFLICTING_CONSTRAINT}} |

<!-- Use when the research lifts conventions from one system
     (e.g. Claude Skills) into another (e.g. artifacts-os) and
     each concept gets an explicit verdict. r0002 § 9 ("Mapping
     Table") is the worked example. The verdict column is the
     handoff to the downstream spec's engagement table. -->

<!-- ===== OPTIONAL: high-level summary across many dimensions ===== -->

## 5. Coverage matrix at a glance

| Concern | {{SYSTEM_A}} | {{SYSTEM_B}} | Decision |
|---|:-:|:-:|---|
| {{CONCERN}} | yes | partial | {{DIRECTIONAL_NOTE}} |

<!-- Use as a one-glance summary after a long body. r0001 § 4
     is the worked example: 30+ rows, two boolean columns, and
     a "Decision" column that previews the recommendation. -->

## 6. Recommendations

1. **{{IMPERATIVE_RECOMMENDATION}}** — {{WHY_BACKED_BY_SECTION_NUMBER}}
2. **{{IMPERATIVE_RECOMMENDATION}}** — {{WHY_BACKED_BY_SECTION_NUMBER}}
3. **{{IMPERATIVE_RECOMMENDATION}}** — {{WHY_BACKED_BY_SECTION_NUMBER}}

<!-- REQUIRED. Each recommendation is a numbered, imperative
     bullet. State what the downstream consumer should do and
     cite the section number that backs the move. If the
     prompting artifact is a spec, expect each recommendation to
     map onto a row in that spec's engagement table. r0002
     § "Recommendations for t0073" is the worked example. -->

## Sources

- [{{EXTERNAL_SOURCE_NAME}}]({{URL}})
- `{{REPO_RELATIVE_PATH}}` — {{ONE_LINE_ROLE}}
- [[{{SIBLING_ARTIFACT}}]] — {{ONE_LINE_ROLE}}
- [[{{PROMPTING_TASK_OR_SPEC}}]] — {{ONE_LINE_ROLE}}

<!-- REQUIRED. Every external URL, code path, and sibling
     artifact the body depends on. The prompting task or spec
     appears here as well as in the lead-in metadata block —
     duplicate intentionally so the artifact is auditable from
     either end. Bare wikilinks (`[[r0001-...]]`) auto-resolve
     in the vault. -->