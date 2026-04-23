---
kind: doc
name: sessions
---

# Sessions

Run tracking and session management in Open Station. This doc
covers the backend-agnostic run model, the `sessions` command,
the `cc-sessions` browser, and stale-run detection. For
tmux-specific details (window creation, modes, pane lifecycle),
see `docs/tmux-backend.md`.

## Run Record Model

Every detached agent execution creates a **run record** in
`state.db`. The `runs` table is the single source of truth for
execution history.

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | TEXT PK | Auto-incrementing run ID (`r0001`, `r0002`, ...) |
| `task` | TEXT | Task name (`0042-slug`) |
| `agent` | TEXT | Agent name assigned to the run |
| `session_id` | TEXT | Claude Code session ID (extracted from log on completion) |
| `status` | TEXT | Run status: `running`, `complete`, `failed`, `lost` |
| `started` | TEXT | ISO 8601 timestamp when the run began |
| `finished` | TEXT | ISO 8601 timestamp when the run ended (null while running) |
| `turns_used` | INTEGER | Turns consumed during the run |
| `turns_limit` | INTEGER | Max turns allowed for the run |
| `cost` | REAL | USD cost of the run |
| `exit_reason` | TEXT | Reason for failure or abnormal exit (null on success) |
| `log_path` | TEXT | Path to the stream-json log file |
| `tmux_ref` | TEXT | Backend session/window/pane name |
| `mode` | TEXT | `execute` or `verify` |

### Key Operations

| Function | Location | Purpose |
|----------|----------|---------|
| `insert_run()` | `state.py` | Create a new run record with `status: running` |
| `complete_run()` | `state.py` | Mark a run finished with final stats |
| `list_runs()` | `state.py` | Query runs with optional status/task filters (newest first) |
| `resolve_run_ref()` | `state.py` | Flexible reference resolution (see below) |
| `gc_stale_runs()` | `state.py` | Mark orphaned `running` entries as `lost` |

## Run Lifecycle

```
insert_run()
  └─► running
        ├─ (normal exit)      → complete   via run-complete
        ├─ (abnormal exit)    → failed     via run-complete
        └─ (no live backend)  → lost       via --gc
```

### Normal Completion

The agent exits cleanly. `run-complete` parses the log, sets
`status: complete`, records `turns_used`, `cost`, and
`session_id` in state.db.

### Abnormal Exit (Failed)

The agent exits due to max turns, budget exhaustion, or crash.
`run-complete` detects the abnormal exit from the log or return
code, sets `status: failed` with an `exit_reason`, and appends
a `## Progress` entry to the task file documenting the failure.

Abnormal exit detection checks for:
- Missing session ID or result text (crash)
- "max turns" pattern in result text
- "budget" pattern in result text

### Lost Runs (GC)

If the agent process or backend crashes before `run-complete`
executes, state.db retains a `running` entry with no matching
backend session. These orphaned runs are marked `lost` by
`openstation sessions --gc` with
`exit_reason: "gc: no live tmux window"`.

## `run-complete`

An internal command chained to the end of every detached
pipeline. It fires automatically when the agent process exits,
regardless of exit code (chained with `;`, not `&&`).

### Synopsis

```
openstation run-complete RUN_ID --log LOG_FILE [--remain-on-exit]
```

### Flow

1. **Parse log** — Extract `session_id`, `cost`, `turns_used`,
   exit subtype, and abnormal-exit flag from the stream-json log.
2. **Update state.db** — Set `status` to `complete` or `failed`,
   populate `finished`, `turns_used`, `cost`, `exit_reason`,
   `session_id`.
3. **Append progress** — If abnormal, append a `## Progress`
   entry to the task file with stop reason and stats.
4. **Fire hooks** — Trigger `RunComplete` hooks (post-phase only).
   Environment variables: `OPENSTATION_RUN_STATUS`,
   `OPENSTATION_RUN_ID`, `OPENSTATION_TASK`,
   `OPENSTATION_RUN_SUBTYPE`, `OPENSTATION_LOG`,
   `OPENSTATION_COST`, `OS_VAULT_ROOT`.
5. **Backend cleanup** — If abnormal or `--remain-on-exit`: keep
   the backend pane alive for inspection. Otherwise, the pane
   closes when the shell exits.

## `openstation sessions`

Run history and live session management.

### Synopsis

```
openstation sessions [REF] [--active] [--attach REF] [--kill REF]
                     [--gc] [--json] [--limit N]
```

### REF — Run Reference

`REF` is an optional positional argument that identifies a run or
task. When provided, the command shows detail for that specific
run or lists all runs for that task. When omitted, it lists the
last N runs across all tasks.

`REF` accepts any of these forms:

| Form | Example | Meaning |
|------|---------|---------|
| Run ID | `r0205` | A specific run by its ID |
| Task:index | `0346:2` | The 2nd run for task 0346 (1-based) |
| Task name | `0346-unify-vault-query-with-kind` | Latest run for that task |
| Numeric prefix | `346` | Zero-padded to `0346`, then prefix-matched |

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `REF` (positional) | — | Run reference — see above |
| `--active` | — | Show only currently running sessions (excludes stale) |
| `--attach REF` | — | Attach to a live backend session |
| `--kill REF` | — | Kill a live backend session |
| `--gc` | — | Mark stale `running` entries as `lost` |
| `--json` | — | JSON output |
| `--limit N` | `20` | Max results |

### Reference Resolution

References resolve in this order (first match wins):

| Pattern | Example | Resolves to |
|---------|---------|-------------|
| Run ID | `r0001` | Exact match in state.db |
| Task:index | `0042:2` | 2nd run for task 0042 (1-based) |
| Task name | `0042-add-login` | Latest run for that task |
| Numeric prefix | `42` | Zero-padded to `0042`, then prefix-matched |
| Prefix match | `0042` | Matches `0042-anything` |

### Data Sources

1. **state.db** (primary) — The `runs` table provides the
   canonical run history.
2. **Live backend** (augmentation) — The backend is queried for
   active sessions to cross-check against state.db entries and
   detect stale runs.

### Default Listing

Shows the last N runs (default 20). For each `running` entry,
cross-checks the backend to verify the session is still alive.
Entries with no matching backend session display as `stale`.

### Fallback

If state.db is unavailable, `sessions` falls back to
backend-only listing — scanning for active sessions and
displaying them directly.

## Stale / Ghost Run Detection

A **stale run** is a state.db entry with `status: running` but
no matching live backend session. This happens when:

- The agent process crashes before `run-complete` fires
- The backend server dies (e.g., tmux server killed)
- The machine shuts down unexpectedly

### Detection

During `openstation sessions` listing, each `running` entry is
cross-checked against live backend sessions. Mismatches are
displayed as `stale` (in-memory flag only — state.db is not
modified).

### Garbage Collection

```bash
openstation sessions --gc
```

Formally marks all stale entries as `lost` in state.db with
`exit_reason: "gc: no live tmux window"` and a `finished`
timestamp. The `gc_stale_runs()` function compares the set of
live backend refs against all `running` entries.

## CC Sessions

The `cc-sessions` command browses Claude Code session files,
providing a view into interactive sessions that are not tracked
in state.db (which only covers detached runs).

### Synopsis

```
openstation cc-sessions [QUERY] [--branch BRANCH] [--agent AGENT]
                        [--limit N] [--json] [--count]
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `QUERY` (positional) | — | Substring search in first message, session ID, or branch |
| `--branch BRANCH` | current branch | Filter by git branch (exact or prefix match) |
| `--agent AGENT` | — | Filter by agent name (exact match) |
| `--limit N` | `20` | Max results |
| `--json` | — | JSON output |
| `--count` | — | Count all messages per session (slower) |

### Discovery

CC sessions are discovered from Claude Code's local session
files:

1. **Project directory resolution** — The project's absolute path
   is converted to Claude Code's directory naming convention
   (e.g., `/Users/leo/workspace/open-station` becomes
   `-Users-leo-workspace-open-station`). Both the main project
   and worktree variants are matched under
   `~/.claude/projects/`.

2. **Session file parsing** — JSONL session files are read
   (first 50 lines) to extract: `session_id`, `agent`, `branch`,
   `cwd`, `first_message`, `message_count`, `timestamp`.

### Default Behavior

With no filters, defaults to showing sessions for the current
git branch (`git rev-parse --abbrev-ref HEAD`).

### Output

- **Table**: DATE | SESSION (first 12 chars, `*` = current) |
  MSGS | AGENT | FIRST MESSAGE (truncated)
- **JSON**: Array with `session_id`, `date`, `agent`, `branch`,
  `message_count`, `first_message`, `current` (bool)

## Backend Abstraction

Sessions are **backend-agnostic**. The run model (state.db, run
lifecycle, `sessions` command) does not depend on any specific
backend implementation.

### Backend Interface

All backends implement the same launch signature:

```python
def launch(
    cmd: list[str],
    session_name: str,
    log_file: Path | None,
    cwd: Path,
    *,
    config: dict | None = None,
    on_exit: str | None = None,
) -> tuple[int, bool]
```

### Backend Registry

Backends are registered in `backends/__init__.py`. The active
backend is configured via `run.detached_backend` in
`openstation.yaml` (default: `tmux`).

Currently the only backend is **tmux** — see
`docs/tmux-backend.md` for tmux-specific details (window
creation, naming, modes, index allocation, `send-keys` pipeline,
pane lifecycle, `remain-on-exit`, edge cases).

## Architecture

### Module Layout

| File | Role |
|------|------|
| `src/openstation/state.py` | Run tracking in `state.db` — insert, update, query, GC |
| `src/openstation/run.py` | Orchestration — agent commands, run records, `sessions` listing, `run-complete` |
| `src/openstation/sessions.py` | CC sessions — discovery, parsing, filtering |
| `src/openstation/backends/__init__.py` | Backend registry (`get_backend()`) |
| `src/openstation/backends/tmux.py` | Tmux backend implementation |

### Integration Points

- **CLI entry** — `openstation run --task <id> -d` creates a run
  record and dispatches to the configured backend.
- **Backend dispatch** — `run.py` calls `get_backend(name)` to
  load the backend's `launch()` function.
- **Run-complete chain** — `build_run_complete_cmd()` appends the
  cleanup command to every detached pipeline.
- **RunComplete hooks** — `run-complete` fires `RunComplete`
  hooks after updating state.db (post-phase only, failures are
  non-blocking warnings).
- **Sessions discovery** — `cmd_sessions()` queries both state.db
  and the live backend to produce cross-checked listings.
- **CC sessions** — `cmd_cc_sessions()` reads Claude Code session
  files independently of state.db.

### Data Flow (Detached Run)

```
CLI args
  → run_single_task()
    → state.insert_run(status="running")
    → backend.launch(cmd, session, log, cwd, on_exit=run-complete)
      [agent runs in background]
      → run-complete fires
        → state.complete_run(status=complete|failed)
        → hooks.fire_run_complete_hooks()
```
