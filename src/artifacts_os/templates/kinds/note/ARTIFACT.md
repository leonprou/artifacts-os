---
name: note
description: Captures thinking at a point in time — planning, decisions, brainstorms, meetings, or scratch work. Use when context (decisions, trade-offs, references) must outlive the conversation that produced it.
---

# Note

## What is a note?

A **note** is a free-form artifact that captures thinking at a point
in time — planning, a decision already made, brainstorm convergence,
meeting minutes, or scratch work. Notes preserve the load-bearing
content (decisions, trade-offs, references, exact phrasing) so future
tasks can act on the thinking without re-running the conversation
that produced it.

Every note carries a `type`. Use one of the conventional values below
when it fits; coin a new one only if none applies.

| `type` | Captures |
|---|---|
| `planning` | PM scoping, work breakdown, risks, requirements drafted before a spec or task. |
| `decision` | Decisions already made — labelled `D1`, `D2`, etc. — so a future task can act without re-deciding. |
| `brainstorm` | Convergence from a live exploration session: themes, designs, open questions. |
| `meeting` | Notes from a synchronous discussion. |
| `scratch` | Throwaway working notes; minimal structure. |

## How to draft a note

Notes are deliberately open-ended — there is **no fixed skeleton**.
Shape the body around what the note captures: prose, lists, tables,
sub-headings, diagrams, code blocks — whatever serves a future reader
best.

### Step 1 — Pick a value for frontmatter `type`

Use the table above. If you cannot decide between `planning` and
`decision`, ask the user before drafting.

### Step 2 — Lift convergence, do not summarise

If a brainstorm or chat thread preceded this note, copy the load-bearing
content **verbatim**: decisions already locked, code references, exact
phrasing of trade-offs. The note's job is transcription, not
compression. Future tasks read notes to act without re-running the
brainstorm — paraphrasing erases the fidelity that makes that work.

### Step 3 — Anchor the note: Origin (top) and References (bottom)

Two sections are required regardless of `type`:

- **`## Origin`** — when, why, and the prompting context. State the
  session or chat thread, the prompting question or event, and (if
  known) the parent task. Anchors the note in time and source so the
  trail back to where the thinking came from is never lost.
- **`## References`** — at minimum, link the parent task or session
  that prompted the note. Add sibling notes, code paths, and any
  external material the note relies on. Bare wiki refs
  (`[[t0042-foo]]`) auto-resolve in the vault. Notes without
  references are hard to act on later.

Everything between Origin and References is up to you. Use whatever
structure the content demands; do not invent structure for its own
sake, and do not omit structure when it helps a future reader.

## Skeleton

```markdown
# {{TITLE}}

{{ONE_PARAGRAPH_SUMMARY}}

## Origin

## References
```
