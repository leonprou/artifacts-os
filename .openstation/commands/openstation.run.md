---
name: openstation.run
description: Run a task in detached mode. $ARGUMENTS = task ID or name [options]. Use when user says "run task", "execute task", "launch task", or wants to start an agent on a task.
---

# Run Task

Launch an agent to execute a task in detached (background) mode.

## Input

`$ARGUMENTS` — a task ID or name, followed by optional flags.

Supported flags (space-separated after the task reference):

| Token | Meaning |
|-------|---------|
| `--budget N` | Max USD per invocation (default: 5) |
| `--turns N` | Max agent turns (default: 50) |
| `--worktree` | Run in an isolated git worktree |
| `--dry-run` | Print the command without executing |
| `--interactive` or `-i` | Run interactively instead of detached |
| `--verify` | Launch verification (task must be in `review`) |

Examples:
- `0042`
- `0042 --budget 3 --turns 30`
- `0042 --worktree`
- `0042 --interactive`
- `0042 --verify`

## Procedure

### 1. Parse input

Extract the task reference (first token) and any flags from
`$ARGUMENTS`. If `$ARGUMENTS` is empty, ask the user which
task to run.

### 2. Resolve the task

```bash
openstation show <task-ref> --json
```

Verify the task exists. Extract `name`, `status`, and `assignee`
from the output.

### 3. Validate

- **Status check**: The task must be `ready` or `in-progress`
  (unless `--verify` is passed, which requires `review`).
  If the status is wrong, report the current status and stop.
- **Assignee check**: The task must have an `assignee`. If
  empty, ask the user to assign an agent first
  (`/openstation.update <task> assignee:<agent>`).

### 4. Build and execute the command

Construct the `openstation run` command:

```bash
# Default: detached mode
openstation run --task <name> -d

# With options
openstation run --task <name> -d --budget <N> --turns <N>

# Interactive mode (when --interactive or -i is passed)
openstation run --task <name> -i

# Verify mode
openstation run --task <name> --verify -i

# Worktree
openstation run --task <name> -d --worktree

# Dry run (append --dry-run)
openstation run --task <name> -d --dry-run
```

If `--dry-run` was passed, show the command and stop.

Otherwise, execute the command and report the result to the
user. For detached runs, note that the agent is running in the
background and suggest `/openstation.check <task>` to monitor
progress.

### 5. Confirm

Report:
- Task name and assigned agent
- Mode (detached / interactive / verify)
- Session name (for detached runs, from tmux output)
- How to check progress: `/openstation.check <task-id>`
