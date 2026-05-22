---
assignee: author
created: 2026-05-18
depends_on:
- '[[t0176-teach-the-artifacts-os-skill]]'
id: t0177
kind: task
name: teach-openstation-create-to-use
owner: user
status: ready
type: documentation
---

## Why

`/openstation.create` hardcodes the task body template as
`## Requirements + ## Verification`. The task kind's
`ARTIFACT.md` (`artifacts/kinds/task/ARTIFACT.md`) is a
fully-authored brief enumerating 15 body sections with explicit
"when to add" rules — most ignored by the command today. The
result is the pattern observed on t0176: PMs hand-enrich the
body after creation (adding `## Why`, `## Context`, `## Source
of truth`, `## Constraints`, `## Out of scope`, `## Files to
touch`) instead of getting those sections by default when the
task type warrants them. Closing this gap brings the slash
command into alignment with the kind's authored contract.

## Context

Sibling of `[[t0176-teach-the-artifacts-os-skill]]`, which
applies the same pattern to `/artifacts.create`. The two share
a common shape: an agent-facing prompt reads `ARTIFACT.md` and
uses it as the drafting brief. They're handled as separate
tasks because they touch different surfaces with different
draft/approve loops, but the design pattern is identical. The
author should reference t0176's output as the reference style
when wording this slash command's flow.

## Source of truth

- **`artifacts/kinds/task/ARTIFACT.md`** — the brief the slash
  command should consume. Defines the 15-section schema and
  conditional rules (e.g., `## User story` only for
  `type: feature`; `## Test plan` for `type: implementation`/
  `refactor`; `## Source of truth` when a binding spec is
  named).
- **`[[t0176-teach-the-artifacts-os-skill]]`** — sister task.
  Author should match its read-then-create flow shape and
  voice when editing `/openstation.create`.
- **`docs/decomposition.md`** — sizing heuristics the command
  already references; carry over without change.

## Files to touch

| Path | Surface | Edit |
|---|---|---|
| `.openstation/commands/openstation.create.md` | Canonical slash command | Replace hardcoded body template with a flow that consults `artifacts kinds task` and selects sections by inferred `type`. |
| `.claude/commands/openstation.create.md` | Active project copy | Mirror the canonical command. |
| `src/artifacts_os/ai/claude/commands/openstation.create.md` (if present) | Shipped copy | Mirror. |

## Constraints

- **Section selection by type.** Honor the conditional rules
  in `task/ARTIFACT.md`'s section table: `## User story` only
  for `type: feature`; `## Test plan` for
  `type: implementation`/`refactor`; `## Subtasks` for feature
  umbrellas; `## Source of truth` when a binding spec/research
  is named; `## Constraints` and `## Out of scope` when scope
  creep or load-bearing rules are present.
- **Required-at-draft set unchanged.** `## Requirements` and
  `## Verification` remain required at draft time per
  `ARTIFACT.md`. Other sections are added only when type and
  maturity call for them.
- **Read-then-create flow mirrors t0176's exactly.** The
  command runs `artifacts kinds task` to load the brief, drafts
  the body per the brief, then writes via
  `openstation create --body "…"`. No re-derivation of section
  rules in the slash command prose.
- **No CLI change.** `openstation create` (Python CLI) is not
  modified; this task is purely a slash-command edit.

## Out of scope

- Updating `/artifacts.create` (handled by
  `[[t0176-teach-the-artifacts-os-skill]]`).
- Per-kind slash commands (`/openstation.create.spec`,
  `…note`, etc.) — separate concern.
- Any Python CLI change.
- Other `/openstation.create` improvement candidates captured
  in `[[n0016-deferred-create-command-improvements]]` —
  triaged for future review, not this task.

## Requirements

1. The slash command's Round 1 draft step consults
   `artifacts kinds task` and uses its body as the drafting
   brief, rather than hardcoding the body template.
2. Section selection in Round 1 is conditional on the inferred
   `type`, per the section table in `task/ARTIFACT.md`.
3. Round 1's preview shows the complete body that will be
   written, not just a section outline.
4. The shipped slash command copy under
   `src/artifacts_os/ai/claude/commands/openstation.create.md`
   (if present) is updated in sync with the canonical and
   active-project copies.
5. No changes to `src/artifacts_os/cli/commands/create.py` or
   any other Python module.
6. `pytest` passes.

## Verification

- [ ] `/openstation.create` instructs the agent to run
  `artifacts kinds task` during Round 1 and use the returned
  body as the drafting brief.
- [ ] Section selection in Round 1 is driven by
  `task/ARTIFACT.md`'s conditional rules, gated on inferred
  `type`.
- [ ] Round 1 message presents the full body (selected sections
  with their content) before approval, not just a section list.
- [ ] `.openstation/commands/openstation.create.md` and
  `.claude/commands/openstation.create.md` carry the same flow.
- [ ] Shipped copy at
  `src/artifacts_os/ai/claude/commands/openstation.create.md`
  (if present) matches the canonical command.
- [ ] No changes to `src/artifacts_os/cli/commands/create.py`.
- [ ] `pytest` passes.
- [ ] Reviewed and approved by user.