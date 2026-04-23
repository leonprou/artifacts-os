---
name: openstation-supervisor
description: Supervise active openstation tasks — list in-progress and review tasks, check session health for each, and present actionable recommendations. Use when asked to check on tasks, supervise work, or get a status overview.
user-invocable: false
---

# Open Station Supervisor

Monitor and supervise active tasks across the vault. Diagnose
health, identify blockers, and recommend next actions.

## Procedure

### 1. Gather active tasks

```bash
openstation list --status in-progress
openstation list --status review
```

Collect all task IDs from both lists.

### 2. Check each task

For each task, determine if it has an active agent session:

```bash
openstation sessions <task-id>
```

Parse the output:
- **Running** (tmux window alive) — report as active, skip
  deep check unless asked.
- **Complete / no session** — run `/openstation.check <task-id>`
  to analyze the log and diagnose.

To verify if a tmux window is actually alive:

```bash
tmux list-windows -t os -F "#{window_name}" 2>/dev/null | grep <task-id>
```

### 3. Present summary

Output a single table with all tasks and their status:

```
| ID   | Task                  | Status      | Agent     | Diagnosis          |
|------|-----------------------|-------------|-----------|--------------------|
| 0268 | project name/alias    | in-progress | developer | Needs re-run       |
| 0278 | parent task review    | review      | developer | Rework: --force    |
```

For each task include:
- **Healthy** — on track, no action needed
- **Running** — agent session active in tmux
- **Needs re-run** — hit turn limit or failed, needs restart
- **Needs verification** — in review, no verify session running
- **Rework** — verification failed, back in progress
- **Blocked** — waiting on dependency or user input
- **Stale** — no activity, no sessions, needs triage

### 4. Recommend actions

After the table, list concrete next steps ordered by priority:
1. Tasks blocking other work
2. Tasks in review needing verification
3. Failed/stale tasks needing re-run
4. New ready tasks to start

## Constraints

- **Diagnose only.** Do not run tasks, make edits, or change
  status. Present findings and let the user decide.
- Use `/openstation.check` for per-task deep analysis — do not
  duplicate its log-reading logic here.
- Keep the summary concise — one line per task in the table.
