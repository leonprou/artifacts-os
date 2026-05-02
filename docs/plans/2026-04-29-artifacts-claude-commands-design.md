# `/artifacts.*` Claude Slash Commands — Design

**Date:** 2026-04-29
**Status:** Approved
**Owner:** user

## Goal

Provide a slash-command surface for the `artifacts` CLI that
**complements** the existing `artifacts-os` skill. Commands earn
their keep through workflow scaffolding, deterministic argument
shapes, and discoverability via `/` autocomplete — they do not
duplicate the skill's CLI-reference content.

## Background

The repository already ships:

- A working `artifacts` CLI with subcommands `list`, `show`,
  `create`, `status`, `verify`, `validate`, `init`, `kinds`.
- A `.claude/skills/artifacts-os/SKILL.md` skill that documents
  every CLI flag, output mode, JSON-parsing idiom, and edge case.
  It is the natural-language entry point for "show ready tasks"
  or "create a new spec".
- A 21-command `openstation.*` slash-command set wrapping an older
  sibling CLI. It mixes thin wrappers and workflow commands.

The new commands target the `artifacts` CLI specifically. They
coexist with `openstation.*` (different CLI, different vault
layout); deprecation is a separate decision.

## Architecture

```
┌──────────────────────────────────────────────────┐
│  artifacts-os skill                              │
│  Single source of truth for CLI mechanics:       │
│    flags · output modes · JSON · edge cases      │
└────────────┬─────────────────────────────────────┘
             │ referenced by
             ▼
┌──────────────────────────────────────────────────┐
│  /artifacts.* slash commands                     │
│                                                  │
│  Thin wrappers     → arg-shape mapping +         │
│                      minimum invocation +        │
│                      pointer to skill (~15 ln)   │
│                                                  │
│  Workflow commands → multi-step procedures;      │
│                      explicitly invoke skill     │
│                      before running CLI calls    │
└──────────────────────────────────────────────────┘
```

The skill is the canonical reference. Slash commands are the
workflow + UX surface. This avoids the failure mode where the
CLI is documented in three places and they drift.

## Command Set

### Workflow commands (4)

Real value beyond the skill — multi-step drafting and approval.

| Command | Purpose |
|---|---|
| `/artifacts.create` | Generic multi-round draft/approval, then `artifacts create`. Auto-infers kind. |
| `/artifacts.create.task` | Task-specific draft template — requirements + verification checklist. |
| `/artifacts.create.spec` | Spec-specific draft template — summary, scope, producing task. |
| `/artifacts.create.agent` | Agent-specific draft template — role, capabilities, constraints. |

Each follows the pattern from `openstation.create`:

1. Round 1 — present a draft with all inferred fields. Do not
   create files yet.
2. End with: **"Approve, or tell me what to change."**
3. Round 2+ — iterate only if the user requests changes.
4. On approval, run `artifacts create "<title>" --kind <kind>
   --body "<approved body>" --fields key=value ...`.
5. Confirm by showing the created file path.

### Thin-wrapper commands (6)

Deterministic shortcuts. Each defers to the skill for full reference.

| Command | Adds |
|---|---|
| `/artifacts.list` | Argument-shape mapping (`status:ready` → `--status ready`) + default-to-active filter |
| `/artifacts.show` | Passthrough |
| `artifacts kinds` (CLI) | Passthrough — `/artifacts.kinds` slash command retired per s0017 D10 |
| `/artifacts.status` | Passthrough; surface allowed-status list on error |
| `/artifacts.verify` | Passthrough |
| `/artifacts.validate` | Passthrough |

**Body shape (~15 lines):**

```markdown
---
name: artifacts.<cmd>
description: <one-liner>. $ARGUMENTS = <shape>. Use when ...
---

# <Title>

## Input

`$ARGUMENTS` — <shape and mapping rules>.

## Procedure

Run:
```bash
artifacts <cmd> [...flags]
```

For full flag reference, output formats, and edge cases — invoke
the `artifacts-os` skill.
```

## File Layout

```
.claude/commands/
  artifacts.list.md
  artifacts.show.md
  artifacts.kinds.md
  artifacts.create.md
  artifacts.create.task.md
  artifacts.create.spec.md
  artifacts.create.agent.md
  artifacts.status.md
  artifacts.verify.md
  artifacts.validate.md
```

Total: **10 files**.

## Out of Scope

- **Lifecycle aliases** (`/artifacts.done`, `/artifacts.ready`,
  `/artifacts.reject`) — `artifacts status <ref> <new-status>`
  already covers all transitions; CLI itself rejects invalid
  values. The lifecycle-gate logic from `openstation.done` ("must
  be `verified` first") is workflow-specific and not part of the
  generic CLI semantics.
- **`/artifacts.progress`** — `artifacts` CLI does not currently
  expose a progress-log primitive. Defer until it does.
- **`/artifacts.update`** for non-status fields — the CLI does
  not yet support generic field updates (see `artifacts-os` skill
  § "Updating non-status fields"). Defer.
- **`/artifacts.init`** — one-time bootstrap; slash-command surface
  adds no value over running the CLI directly.

## Coexistence with `openstation.*`

Both sets remain installed. They wrap different CLIs and target
different vault layouts. No deprecation plan is part of this design.

## Testing

Each command must be smoke-testable against the local vault:

- `/artifacts.list` → table of active artifacts
- `/artifacts.list status:ready` → only ready
- `/artifacts.list kind:task status:ready` → filtered
- `/artifacts.show t0001` → renders task
- `artifacts kinds` → table of kinds (slash command retired per s0017 D10)
- `/artifacts.status t0001 in-progress` → status update
- `/artifacts.verify t0001` → checklist count
- `/artifacts.validate t0001` → schema check
- `/artifacts.create "test workflow"` → draft, approve, create
- `/artifacts.create.task "test task"` → task-specific draft
- `/artifacts.create.spec "test spec"` → spec-specific draft
- `/artifacts.create.agent "test-agent"` → agent-specific draft

## Open Questions

None. Design is complete and approved.
