---
created: 2026-05-18
id: n0016
kind: note
name: deferred-create-command-improvements
---

Items #2–#10 from the `/openstation.create` analysis on 2026-05-18.
Issue #1 (slash command doesn't use the task kind's `ARTIFACT.md`) is
filed as its own task; the items below are deferred for future
triage. Each row is a candidate task; review in priority order when
bandwidth allows.

## Deferred candidates

| # | Item | Priority | One-line spec |
|---|---|---|---|
| 4 | Agent-assignment rubric | **H** | Add `type → likely agent` mapping and one-line justification in Round 1 draft. PM hit this when picking `technical-writer` over `author` for t0176 — cost a round-trip. |
| 7 | Full-body preview | **H** | Body is immutable through the CLI; Round 1 should preview the complete body as it will be written, not just a section outline. Prevents the post-create enrichment pattern observed on t0176. |
| 2 | Conditional section logic | M | Falls out of issue #1; may be partially obsolete once the sibling task lands. Re-evaluate then. |
| 3 | Decomposition + spec sub-task prompt | M | Surface PM constraint ("spawn architect spec sub-task for non-obvious design") inline during Round 1 rather than buried in `docs/decomposition.md`. |
| 5 | Verification derivation from constraints + out-of-scope | M | Today: requirements-only. Better: derive from `Requirements ∪ Constraints` and add negative checks from `## Out of scope`. The t0176 verification line about variant precedence came from a constraint, not a requirement. |
| 8 | Reference to prior similar tasks | M | Surface 1–2 closely-related completed tasks in Round 1 ("similar to t0142 / t0078") so the user can anchor drafting with one line. |
| 6 | Title vs description disambiguation | L | `$ARGUMENTS` becomes the title positional; should distil to ≤ 8-word title and echo the full description as context. t0176's title ran 13 words. |
| 9 | Schema validation preview | L | Run `openstation create --dry-run` between approval and write. Rarely fails today but cheap insurance. |
| 10 | Consolidate with `/artifacts.create` | L now / **H** long-term | `/openstation.create` becomes a thin alias for `/artifacts.create --kind task`. Revisit once t0176 + the sibling task land, when the parallel-surfaces tax is concrete. |

## Origin

PM analysis triggered by the post-create enrichment experience on
t0176 (2026-05-18). The conversation that produced this list:
PM↔user audit of `/openstation.create` against the t0176 flow.

## Triage guidance

- Items marked **H** are the lowest-effort / highest-impact pickups
  once issue #1 lands.
- Items marked M cluster under "make Round 1 smarter" and could be
  bundled into one umbrella task if picked up together.
- Item #10 is a structural consolidation; revisit after the sibling
  patterns stabilise.