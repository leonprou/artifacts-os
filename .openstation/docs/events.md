---
kind: spec
name: events
---

# Events

Structured event log that captures all significant Open Station
actions as JSONL. Always on, zero configuration. Independent of
hooks.

## Overview

Every `openstation create`, `openstation status`, and
`openstation run` operation emits a structured event to a daily
JSONL file. Events are framework telemetry — they record what
happened, never block operations, and require no setup.

For the full design spec (module design, integration code
samples, trade-off analysis) see
`openstation/specs/event-log-system.md`.

## Schema

Every event is a single JSON object on one line with two
universal fields:

| Field | Type | Description |
|-------|------|-------------|
| `ts` | string | ISO 8601 timestamp with timezone |
| `event` | string | Event type identifier |

All other fields are event-specific.

## Event Types

### `task_created`

Emitted after a task file is created.

```json
{
  "ts": "2026-04-04T14:32:01+03:00",
  "event": "task_created",
  "task": "0042-add-login-page",
  "status": "backlog",
  "assignee": "developer",
  "parent": "0040-auth-feature"
}
```

### `status_transition`

Emitted after a task's status changes.

```json
{
  "ts": "2026-04-04T14:35:12+03:00",
  "event": "status_transition",
  "task": "0042-add-login-page",
  "old_status": "ready",
  "new_status": "in-progress",
  "forced": false
}
```

### `run_started`

Emitted when an agent run launches.

```json
{
  "ts": "2026-04-04T14:36:00+03:00",
  "event": "run_started",
  "task": "0042-add-login-page",
  "agent": "developer",
  "run_id": "r-20260404-143600-abc1",
  "mode": "execute",
  "context_only": false,
  "detached": true
}
```

**Mode values:** `execute` (standard), `verify` (verification
run), `interactive` (by-agent mode).

### `run_complete`

Emitted when an agent run finishes.

```json
{
  "ts": "2026-04-04T14:42:30+03:00",
  "event": "run_complete",
  "task": "0042-add-login-page",
  "agent": "developer",
  "run_id": "r-20260404-143600-abc1",
  "run_status": "complete",
  "cost": "1.25",
  "turns": 12
}
```

### `hook_fired`

Emitted after a hook executes successfully.

```json
{
  "ts": "2026-04-04T14:35:13+03:00",
  "event": "hook_fired",
  "hook_type": "StatusTransition",
  "phase": "post",
  "matcher": "*→done",
  "command": "notify-send 'Task $OS_TASK_NAME completed'",
  "task": "0042-add-login-page",
  "duration_ms": 45
}
```

### `hook_failed`

Emitted when a hook exits non-zero or times out.

```json
{
  "ts": "2026-04-04T14:35:13+03:00",
  "event": "hook_failed",
  "hook_type": "StatusTransition",
  "phase": "pre",
  "matcher": "in-progress→review",
  "command": "bin/lint-task $OS_TASK_FILE",
  "task": "0042-add-login-page",
  "error": "hook failed: bin/lint-task $OS_TASK_FILE (exit 1)",
  "duration_ms": 1200
}
```

## Storage

Events are stored as daily JSONL files:

```
.openstation/events/YYYY-MM-DD.jsonl
```

One JSON object per line. Files are created on first write
each day. Append-only — no rotation or compaction.

## Events vs Hooks

Events and hooks are **parallel, independent systems**. Neither
blocks, gates, or depends on the other.

| Aspect | Hooks | Events |
|--------|-------|--------|
| Purpose | User-defined side-effects | Framework telemetry |
| Configuration | `openstation.yaml` | Always on, no config |
| Can block operations | Yes (pre-hooks) | Never |
| Failure impact | Pre: aborts transition; Post: warning | Warning only |
| Scope | `StatusTransition`, `RunComplete` | All significant actions |
| Output | Shell stdout/stderr | `.openstation/events/*.jsonl` |

A failed `emit()` never prevents an operation from completing.
Events record what happened; hooks control what happens.

See `docs/hooks.md` for the full hooks reference.

## Integration Points

Events are emitted from these functions:

| Event | Function | Module | Timing |
|-------|----------|--------|--------|
| `task_created` | `cmd_create()` | `tasks.py` | After file write, parent update, and post-create hooks |
| `status_transition` | `cmd_status()` | `tasks.py` | After frontmatter update and parent auto-promotion, before post-hooks |
| `run_started` | `run_single_task()`, `_exec_or_run()` | `run.py` | After state.db record, before subprocess launch |
| `run_complete` | `run_single_task()`, `cmd_run_complete()` | `run.py` | After run record completion |
| `hook_fired` | `run_matched()`, `fire_run_complete_hooks()` | `hooks.py` | After each successful hook execution |
| `hook_failed` | `run_matched()`, `fire_run_complete_hooks()` | `hooks.py` | After each failed hook execution |

### Timing in `cmd_status()`

```
validate status value
validate transition legality
─── pre-hooks fire ───              ← hook_fired / hook_failed
update_frontmatter()
auto_promote_parent()
─── events.emit(status_transition) ───
─── post-hooks fire ───             ← hook_fired / hook_failed
```

## Architecture

### Module Layout

| File | Purpose |
|------|---------|
| `src/openstation/events.py` | Single module: `emit()` function, daily file management |

### Integration Points

The `emit()` function is called from three modules:

- **`tasks.py`** — `cmd_create()` and `cmd_status()`
- **`run.py`** — `run_single_task()`, `_exec_or_run()`, `_run_verify()`, `cmd_run_complete()`
- **`hooks.py`** — `run_matched()` and `fire_run_complete_hooks()`

### Data Flow

```
Operation (create/status/run/hook)
  │
  ▼
events.emit(root, event_type, **fields)
  │
  ├─ Build record: {ts, event, ...fields}
  ├─ Resolve path: .openstation/events/YYYY-MM-DD.jsonl
  ├─ mkdir -p events dir
  └─ Append JSON line
      │
      ├─ Success: silent
      └─ Failure: warning to stderr, operation continues
```

### Key Abstraction

`emit(root, event, **fields)` — single function, keyword
arguments for event-specific fields. No event classes, no
registry, no validation at emit time. The schema is documented
in this file and in the spec; the implementation trusts callers
to pass correct fields.
