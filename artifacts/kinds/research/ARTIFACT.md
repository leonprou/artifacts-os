---
name: research
description: Captures cited findings from an investigation — external-system survey, code audit, or options comparison. Use when a question requires evidence before a downstream spec or task can act, or when findings must outlive the prompting conversation.
---

# Research

## What is research?

A **research** artifact captures the cited findings of an
investigation — an external-system survey, an internal-code audit,
or a comparison of competing options — in a form a downstream spec,
task, or future reader can consume without re-running the work. Its
load-bearing property is **traceability**: every claim links to the
source that supports it.

Reach for a research artifact (rather than a note) when:

| Signal | Why research |
|---|---|
| ≥ 3 external sources synthesised | The cited body becomes the authoritative summary; consumers skip the re-read. |
| Two or more options compared, with a follow-up spec to land the choice | The mapping / comparison table is the load-bearing artefact. |
| Findings will outlive the prompting task | A note dies inside its task; research is indexed under `artifacts/research/`. |
| A reviewer will audit or challenge the conclusions | Cited claims are reviewable; paraphrased opinion is not. |

Otherwise, file a `note` (`type: planning`, `decision`, or
`brainstorm`) — notes are cheaper.

## How to draft research

Research has no fixed skeleton. Shape the body around the
investigation: side-by-side comparison tables, mapping tables with
verdicts, coverage matrices, sub-area sub-sections, or cited prose
— whichever surfaces the findings best. `r0001` and `r0002` are
worked examples.

### Step 1 — Cite every claim

Every non-trivial claim earns an inline link to its source (URL
for external docs, repo-relative path for code, `[[r0001-...]]`
for sibling artifacts) or a row in a sourced table, with the full
list mirrored in `## Sources` at the bottom. Paraphrased synthesis
without a source is indistinguishable from invented claims to a
future reader. When in doubt, cite.

### Step 2 — Lead with the TL;DR

Open with the conclusion, not the method. `## TL;DR` is the first
heading after the metadata block — two to four paragraphs naming
the headline finding, the quantified shape (numbers, percentages,
key counts), and a forward pointer to where the body goes deep so
a reader who only needs the conclusion can stop.

### Step 3 — Anchor the artifact: metadata, TL;DR, Recommendations, Sources

Four sections are required regardless of investigation shape:

- **Lead-in metadata block** — `Date`, `Agent`,
  `For: [[prompting-task]]`, key `Sources:`. Sits above the first
  horizontal rule; grounds the artifact in time, authorship, and
  the question it answers.
- **`## TL;DR`** — see Step 2.
- **`## Recommendations`** — numbered, imperative bullets stating
  what the downstream consumer should do and citing the section
  that backs each move. Without recommendations, every reader has
  to re-derive the next move.
- **`## Sources`** — every external URL, code path, and sibling
  artifact the body depends on. Bare wikilinks (`[[r0001-...]]`)
  auto-resolve in the vault. Uncited research cannot be audited.

Between TL;DR and Recommendations the structure is yours. Use
whichever shape the investigation demands; do not invent structure
for its own sake, and do not omit structure when it helps a future
reader.

Set `status: draft` on creation; move to `done` only once findings
are complete, cited, and recommendations are firm. There is no
intermediate review step — the downstream spec that consumes the
findings is the surface that earns review.
