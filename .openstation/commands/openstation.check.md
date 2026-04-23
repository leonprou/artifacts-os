---
name: openstation.check
description: Check on a running or completed agent session. $ARGUMENTS = task ID or run ID. Analyzes logs for health, progress, issues, and blockers.
---

# Check Agent Session

Analyze an agent's execution logs and provide actionable insights
about health, progress, issues, and blockers.

## Input

`$ARGUMENTS` — a task ID (e.g., `0253`) or run ID (e.g., `r0056`).

## Constraints

- **Diagnose only, never execute.** This command reads logs and
  reports findings. Do not run tests, make edits, fix code, update
  task status, or perform any agent work.
- **Read-only tools only.** Only use `openstation sessions`,
  `openstation show`, `openstation logs`, and the Read tool.
- **No session data = stop.** If `openstation sessions` returns
  no runs, report "No session data available" and stop. Do not
  attempt to compensate by running the task's work yourself.

## Procedure

### 1. Gather context

Run these commands to collect session and task info:

```bash
openstation sessions <ref>
openstation show <task>
```

If `$ARGUMENTS` is a run ID, extract the task from the sessions
output. If it's a task ID, use it directly.

### 2. Read the log

Use `openstation logs` to read the formatted session log:

```bash
# Show last 200 lines, formatted for readability
openstation logs <task-id> --tail 200

# If you need raw JSONL (e.g., to inspect exact fields)
openstation logs <task-id> --tail 200 --raw
```

Focus on these event types:
- `type: assistant` — agent messages and tool calls
- `type: user` — tool results (especially errors)
- `type: result` — final outcome
- `type: rate_limit_event` — rate limiting

### 3. Analyze and report

Present a structured diagnosis:

**Status**: running | complete | failed

**Progress**: What has the agent accomplished so far?
List the key actions taken (files read, edits made, tests run).

**Current activity** (if running): What is the agent doing
right now? What was the last tool call?

**Health**:
- Turn count vs limit (e.g., 15/50 — healthy, 48/50 — near limit)
- Cost so far
- Rate limiting events (if any)
- Tool error rate (how many tool calls failed vs succeeded)

**Issues**:
- Tool errors or permission denials
- Repeated failed attempts (agent stuck in a loop)
- Tests failing
- Files not found or wrong paths

**Blockers**:
- Is the agent blocked on a permission prompt?
- Is it waiting for user input (`AskUserQuestion`)?
- Is it stuck retrying the same action?
- Has it hit the turn or budget limit?

**Recommendations** (optional):
Non-blocking suggestions for improving the agent's execution
environment or workflow — not the task content itself. Reference
specific items from Issues and suggest how to help the agent
succeed (e.g., adjust permissions, increase turn limit, change
agent assignment). Omit when there are no issues worth
addressing.

**Action needed** (only if the agent is blocked or incomplete):
- If blocked — provide specific instructions to unblock (e.g.,
  approve a permission prompt, fix a failing test, kill a stuck
  session)
- If incomplete/failed — provide the rerun command to restart
  the task (e.g., `openstation run --task 0336 -d`)
- Omit this section entirely when no action is needed (agent is
  healthy and on track, or task completed successfully).

## Example output

```
## Diagnosis: Task 0336

**Status**: Complete (both runs finished)

**Progress**: Two runs executed:

1. **r0182** (developer, 39 turns) — investigated and fixed three root causes:
   - `_send_pipeline()` now checks `send-keys` return code
   - `cmd_run_complete()` wraps hooks/events in `try/finally` so `_kill_pane()` always runs
   - `_kill_pane()` accepts `tmux_ref` fallback when `$TMUX_PANE` is unavailable
   - Added 8 new tests across `test_run_complete.py` and `test_tmux_modes.py`

2. **r0183** (project-manager, 18 turns) — verified all 4 criteria, wrote verification report, transitioned task to `verified`

**Health**:
| Metric | r0182 (developer) | r0183 (verifier) |
|---|---|---|
| Turns | 39/50 | 18/50 |
| Cost | $2.57 | $0.73 |
| Duration | ~8 min | ~1 min |
| Rate limits | None | None |
| Permission denials | 1 (writing analysis to /tmp, non-blocking) | 0 |
| Tool errors | None significant | None |

**Issues**:
- 1 pre-existing test failure (`test_window_found` — incorrect mock data, unrelated to this task). Documented in Downstream section.
- The developer had 1 permission denial trying to write a large analysis file to `/tmp` — it pivoted and continued without issue.

**Blockers**: None

**Recommendations**:
- The developer hit a permission denial writing to `/tmp` — consider adding `/tmp` to allowed paths in Claude Code settings to avoid future interruptions in autonomous runs.

**Action needed**: None — task completed successfully. Run `/openstation.done 0336` to finalize.
```
