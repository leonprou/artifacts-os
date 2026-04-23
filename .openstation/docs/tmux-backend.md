---
kind: doc
name: tmux-backend
---

# Tmux Backend

The tmux backend launches agent sessions in detached tmux
windows (or sessions/panes) so they run independently of the
user's terminal. This document covers tmux-specific details:
window creation, the detached pipeline, window lifecycle, and
known edge cases. For the backend-agnostic run model, run
lifecycle, `openstation sessions` command, and stale-run
detection, see `docs/sessions.md`.

## Window Creation

### Naming Convention

Window/session names follow the pattern `{alias}-{task-name}`,
where *alias* comes from `project.alias` in `openstation.yaml`
(default: `os`). Examples:

| Task | Name |
|------|------|
| `0042-add-login` | `os-0042-add-login` |
| `0042-add-login` (verify) | `os-verify-0042-add-login` |

Verify sessions add a `verify-` segment so run and verify
sessions for the same task don't collide. A custom session
name can be passed via the `--detached` flag (e.g.,
`-d my-session`), which overrides the convention entirely.

### Target Session

In the default **window** mode, all agent windows are created
inside a shared tmux session named `os` (the
`DEFAULT_TARGET_SESSION`). If the `os` session doesn't exist,
it is created automatically. This keeps all agent runs grouped
in one session for easy navigation.

### Modes

The tmux backend supports three modes, configured via
`run.tmux.mode` in `openstation.yaml` or `--tmux-mode` on the
CLI:

| Mode | Behavior |
|------|----------|
| `window` (default) | New window in the `os` target session |
| `session` | New standalone tmux session per run |
| `pane` | New pane (horizontal split) in the current window of the target session |

### Index Allocation

- **Window mode**: tmux assigns the next available window index
  automatically via `tmux new-window -d`. The window is named
  with the derived session name (`-n os-0042-slug`).
- **Session mode**: `tmux new-session -d -s os-0042-slug`
  creates a named session. Collisions are detected by
  `has_session()` and rejected with a hint.
- **Pane mode**: `tmux split-window -h` creates a horizontal
  split. The pane title is set to the session name via
  `select-pane -T` for discovery by `list_tmux_sessions()`.

All modes create the tmux entity with a wide terminal
(`-x 200 -y 50`) and set the working directory to the project
root (`-c {cwd}`).

## Detached Pipeline

When a task runs in detached mode (`openstation run --task 0042 -d`),
the full command chain is:

```
claude <agent-args> | tee <log-file> | os-format; openstation run-complete <run-id> --log <log-file>
```

### Step by Step

1. **Build agent command** — `run_single_task()` builds the
   `claude` command with agent name, budget, turns, prompt,
   tools, and `--output-format stream-json`.

2. **Create run record** — A run record is inserted into
   `state.db` with `status: running`, a unique `run_id`
   (`r0001`, `r0002`, ...), and the `tmux_ref` set to the
   window name.

3. **Build pipeline** — `_build_pipeline()` constructs the
   shell string: `claude ... | tee <log>.jsonl | os-format`.
   The `tee` captures the raw stream-json to the log file while
   `os-format` renders human-readable output in the pane.

4. **Chain run-complete** — `build_run_complete_cmd()` appends
   `; openstation run-complete <run-id> --log <log-file>` to
   the pipeline. This ensures cleanup runs regardless of the
   agent's exit code (`;` not `&&`).

5. **Send to tmux** — For short commands (interactive mode),
   the pipeline is sent directly via `tmux send-keys`. For
   non-interactive pipelines (which can exceed the ~1500-char
   `send-keys` limit), the pipeline is written to a self-deleting
   temp script (`/tmp/openstation-run-*.sh`) and executed with
   `exec bash /tmp/openstation-run-*.sh`.

6. **Return immediately** — The CLI prints the session name and
   log path, then exits. The agent runs in the background.

### Argument Flow

```
openstation run --task 0042 -d
  └─► run_single_task(tmux=True)
        ├─ build_command() → claude CLI args
        ├─ get_backend("tmux") → backends.tmux.launch
        ├─ derive_session_name("0042-slug") → "os-0042-slug"
        ├─ build_run_complete_cmd(run_id, log) → on_exit string
        └─ launch(cmd, session, log, cwd, on_exit=...)
             ├─ _build_pipeline(cmd, log, on_exit) → shell string
             └─ _send_pipeline(target, pipeline, log) → tmux send-keys
```

### Interactive + Detached

When both `-i` and `-d` are specified, the backend creates the
tmux window the same way but then immediately attaches to it,
giving the user an interactive session inside tmux.

## Window Lifecycle

### Success — Pane Closes

On normal completion (agent exits cleanly, no max-turns or
budget exhaustion), `run-complete` sets `status: complete` in
state.db and the pipeline exits. Since tmux's `remain-on-exit`
defaults to `off`, the pane closes automatically when the shell
process exits. The window disappears from `openstation sessions`.

### Failure / Max-Turns — Pane Stays Open

When the agent exits abnormally (max turns exhausted, budget
exceeded, crash), `cmd_run_complete()`:

1. Parses the log file for completion data (session ID, cost,
   turns used, exit subtype).
2. Detects abnormal exit via missing result text or
   max-turns/budget patterns in the result.
3. Sets `status: failed` in state.db with the `exit_reason`.
4. Appends a `## Progress` entry to the task file documenting
   the failure.
5. Calls `_set_pane_remain_on_exit()`, which sets
   `remain-on-exit on` on the current tmux pane via
   `$TMUX_PANE`.

The pane stays open so the user can inspect the last output,
scroll through the log, and diagnose the issue. The user must
manually close it (`openstation sessions --kill <ref>` or
`tmux kill-pane`).

### `--remain-on-exit` Flag

The `--remain-on-exit` flag forces the pane to stay open even
on success. This is useful for debugging or when you want to
inspect the final output of a successful run.

## Tmux Session Discovery

The tmux backend provides `list_tmux_sessions()` which scans
three sources for live sessions matching the `os-` prefix:

1. **Standalone sessions** — `tmux list-sessions` (session mode)
2. **Windows in target** — `tmux list-windows -t os` (window mode)
3. **Panes in target** — `tmux list-panes -s -t os` with pane
   titles (pane mode)

Returns a list with keys: `name`, `task`, `status`, `activity`,
`kind` (session/window/pane), `pane_id`. This is used by
`openstation sessions` for cross-checking and stale detection
(see `docs/sessions.md`).

## Known Edge Cases

### Window Name Conflicts

If a tmux window named `os-0042-slug` already exists when a
new run is launched for the same task, the backend detects the
collision and exits with an error:

```
error: tmux window already exists: os:os-0042-slug
  hint: select with  tmux select-window -t os:os-0042-slug
```

This happens when a previous run's pane is still open (e.g.,
from a failure with `remain-on-exit on`). Kill the old window
first with `openstation sessions --kill 0042`.

### Ghost Runs from Crashed Processes

If the agent process or tmux server crashes before
`run-complete` executes, state.db retains a `running` entry
with no matching tmux window. The `run-complete` chain
(`; openstation run-complete ...`) mitigates this for normal
exits, but cannot handle hard crashes (SIGKILL, tmux server
death, machine shutdown). See `docs/sessions.md` § "Stale /
Ghost Run Detection" for detection and GC.

### Stale `remain-on-exit` Panes

Failed runs leave panes open via `remain-on-exit on`. These
panes:

- Continue to appear in `openstation sessions` as `dead`
- Consume a tmux window slot, potentially causing name conflicts
  on retry
- Must be manually closed with `--kill` or `tmux kill-pane`

After inspecting a failed run, always clean up:

```bash
openstation sessions --kill 0042
```

### `send-keys` Truncation

Tmux `send-keys` silently truncates commands longer than ~1500
characters. The backend works around this by writing long
pipelines to a self-deleting temp script
(`/tmp/openstation-run-*.sh`) and executing it with
`exec bash <script>`. Interactive (short) commands are sent
directly.

## Architecture

### Module Layout

| File | Role |
|------|------|
| `src/openstation/backends/tmux.py` | Window/session/pane creation, pipeline building, tmux command execution |
| `src/openstation/run.py` | Orchestration — builds agent commands, dispatches to backend, `list_tmux_sessions()` |

For run tracking (`state.py`), session listing, and GC, see
`docs/sessions.md` § "Architecture".

### Integration Points

- **CLI entry** — `openstation run --task <id> -d` triggers
  detached launch via `run_single_task(tmux=True)`.
- **Backend dispatch** — `run.py` calls `get_backend("tmux")`
  to load `backends.tmux.launch()`. The backend name is
  configurable via `run.detached_backend` in settings.
- **Run-complete chain** — `build_run_complete_cmd()` appends
  cleanup to every detached pipeline (see `docs/sessions.md`
  § "`run-complete`").
- **Tmux discovery** — `list_tmux_sessions()` is used by
  `cmd_sessions()` and `gc_stale_runs()` to find live tmux
  entities.
- **Settings** — `project.alias` in `openstation.yaml`
  controls the naming prefix; `run.tmux.mode` and
  `run.tmux.target_session` configure tmux behavior.

### Data Flow (Detached Run)

```
CLI args
  → run_single_task()
    → state.insert_run(status="running")
    → backends.tmux.launch(cmd, session, log, cwd, on_exit=...)
      → tmux new-window / new-session / split-window
      → send-keys: "claude ... | tee log | os-format; run-complete ..."
        [agent runs in background]
        → run-complete fires
          → state.complete_run(status=complete|failed)
          → hooks.fire_run_complete_hooks()
          → _set_pane_remain_on_exit() (on failure)
```
