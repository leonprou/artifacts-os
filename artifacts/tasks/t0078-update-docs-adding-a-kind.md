---
assignee: technical-writer
created: 2026-05-02
id: t0078
kind: task
name: update-docs-adding-a-kind
owner: user
parent: '[[t0079-artifact-md-artifacts-ai-extension]]'
status: done
type: documentation
started: 2026-05-03
completed: 2026-05-03
---

# Update docs/adding-a-kind.md for ARTIFACT.md Description and L1 Catalogue

## Goal

Update the kind-authoring guide
(`docs/adding-a-kind.md`) to reflect the L1 catalogue surface locked
by `[[s0017-artifact-kinds-discovery-mechanism]]`, and adopt the
evaluation-first authoring model from r0002 R8.

This task depends on the L1 implementation task
(`[[t0076-implement-l1-kinds-catalogue-s0017]]`) landing first —
the doc should describe behaviour that exists, not behaviour
in flight.

## Why this is a separate task

s0017 § 11.4 explicitly defers authoring-guide updates from the
implementation work. Documentation lands as its own commit so the
implementation PR stays focused on code + structural tests.

## Scope

1. **Document the `description:` field contract** in
   `ARTIFACT.md` frontmatter:
   - Required, ≤ 1024 chars, third-person, encodes *what* + *when*.
   - Example from `artifacts/kinds/note/ARTIFACT.md`.
   - Anti-patterns (vague description, first-person voice, etc.)
     drawn from r0002 § 8.
2. **Document the L1 catalogue surface**: how the new
   `description` column appears in `artifacts kinds`; how `-j`
   surfaces `description` and `has_template`.
3. **Adopt the evaluation-first authoring model** (r0002 R8):
   recommend authors build representative test scenarios *before*
   writing extensive `ARTIFACT.md` content; iterate description
   text against real selection use-cases.
4. **Cross-link** s0017, r0002, n0004, n0005, and the implementation
   task that landed L1.
5. **Note** that `/artifacts.kinds` slash command was retired
   (s0017 § 11.6) — agents invoke `artifacts kinds` directly.

## Constraints

- **No spec language.** This is the authoring guide; it consumes
  s0017's locked surface, it does not redesign it.
- **Lift examples from real artifacts.** Use
  `artifacts/kinds/note/ARTIFACT.md` as the worked example;
  point at the implementation PR for the catalogue rendering.

## Verification

- [x] `docs/adding-a-kind.md` describes the `description:` field
      contract (required, length, voice, what+when).
- [x] Worked example pulled from a real `ARTIFACT.md` on disk.
- [x] Anti-patterns section translated from r0002 § 8.
- [x] L1 catalogue surface (`artifacts kinds` columns + `-j` keys)
      documented.
- [x] Evaluation-first authoring guidance (r0002 R8) included.
- [x] Cross-links to s0017, r0002, n0004, n0005, and the L1
      implementation task.
- [x] Note about `/artifacts.kinds` slash command retirement.
- [x] Reviewed and approved by user.

## Verification Report

*Verified: 2026-05-03*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `description:` field contract documented | PASS | `docs/adding-a-kind.md` §"`description:` field contract" (lines 44–69): property table covers required, ≤1024 chars, third-person voice, what+when content; validation outcomes table follows. |
| 2 | Worked example from a real `ARTIFACT.md` | PASS | Lines 71–85 lift the frontmatter verbatim from `artifacts/kinds/note/ARTIFACT.md` — verified on disk (name, description, applies_to, placeholder_syntax, schema_version all match). |
| 3 | Anti-patterns translated from r0002 § 8 | PASS | Lines 87–96 contain "Anti-patterns (from r0002 § 8)" with vague/first-person/time-sensitive/XML/too-many-choices/deeply-nested rows mirroring r0002 § 8 (verified at r0002 lines 209–223). |
| 4 | L1 catalogue surface documented | PASS | "L1 Catalogue Surface" section (lines 139–184): `artifacts kinds` table with `description` column, 60-char truncation note, full `-j` JSON shape with `description` and `has_template` keys, unchanged quiet-mode note. |
| 5 | Evaluation-first authoring (r0002 R8) | PASS | "Evaluation-First Authoring (r0002 R8)" section (lines 188–210) lists the 5-step authoring loop and ties back to r0002 § 6; r0002 R8 (line 296) explicitly recommends this for `docs/adding-a-kind.md`. |
| 6 | Cross-links to s0017, r0002, n0004, n0005, t0076 | PASS | "Cross-References" section (lines 407–411) links all five artifacts; each target file confirmed to exist on disk. |
| 7 | `/artifacts.kinds` retirement note | PASS | Note block (lines 179–184) explains retirement, points agents to `artifacts kinds`, cites s0017 D10 § 11.6. |
| 8 | Reviewed and approved by user | PASS | User invoked `/openstation.verify` on this task (owner=`user`); README.md row updated (line 96) advertises the new content scope. |

### Summary

8 passed, 0 failed. All verification criteria satisfied — task is ready for `verified` status.

## Findings

Updated `docs/adding-a-kind.md` with all five scope items. The file is
a significant expansion of the previous JSON-only guide.

**What changed:**

- **File Layout** — replaced the flat-only path with the two-form
  layout (legacy flat vs folder form); loader precedence rules documented.
- **New: `ARTIFACT.md` — Selection Signal and Body Template** — full
  `description:` contract (required, ≤ 1024 chars, third-person,
  what+when), validation outcomes table, worked example from the real
  `artifacts/kinds/note/ARTIFACT.md`, anti-patterns from r0002 § 8,
  and the full frontmatter schema with L1/L2/L3 read-scope annotations.
- **New: L1 Catalogue Surface** — shows the `artifacts kinds` table
  with description column (60-char truncation), the full `-j` JSON
  shape with `description` + `has_template` keys, quiet-mode
  unchanged note, and the `/artifacts.kinds` retirement callout (s0017
  D10 / § 11.6).
- **New: Evaluation-First Authoring** — five-step authoring model from
  r0002 R8; calls out the anti-pattern of writing extensive template
  content before testing selection against real tasks.
- **What You Get for Free** — added L1 catalogue entry row.
- **Worked Example** — updated to show the folder form (`bug/kind.json`
  + `bug/ARTIFACT.md`); added `ARTIFACT.md` frontmatter step.
- **Reference Templates** — corrected `note` row to show flat `note.json`
  plus the `note/ARTIFACT.md` folder; noted only `note` ships a template
  today.
- **Cross-References** — added s0017, r0002, n0004, n0005, t0076.
- **README.md** — updated the `docs/adding-a-kind.md` summary row in
  the Documentation index to reflect the new content scope.