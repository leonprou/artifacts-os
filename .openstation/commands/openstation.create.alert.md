---
name: openstation.create.alert
description: Create an alert artifact. $ARGUMENTS is the alert description. Use when user says "create an alert", "add a reminder", "set up a notification", or "schedule an alert".
---

# Create Alert

Create an alert artifact in `openstation/alerts/`.

## Input

`$ARGUMENTS` — the alert description (free text).

## Procedure

1. Take the description from `$ARGUMENTS`.

2. **Gather alert details.** Ask the user (or infer from context)
   the following fields:

   - **Type** (required) — the connector type: `reminder`,
     `internal`, `github`, or another valid type.
   - **Schedule** — cron expression for recurring alerts
     (e.g., `0 9 * * 1` for every Monday at 9am). Optional.
   - **Assignee** (required) — agent or user to receive the alert.
     Must be provided before the alert can be created.
   - **Task ref** — linked task name (without `.md`). Optional.
   - **Status** — `active` (default), `paused`, or `done`.

3. **Draft the alert.** Present a summary of what will be created.
   Do not create files yet.

   End with: **"Approve, or tell me what to change."**

4. **Iterate only if needed.** If the user approves, proceed.
   If they request changes, apply and re-present.

5. **Create the alert file.** Use the CLI:

   ```bash
   openstation alerts create "<description>" \
     --type <type> \
     [--schedule "<cron>"] \
     [--assignee <name>] \
     [--task <task-ref>] \
     [--status <status>]
   ```

6. **Fill in the body** if additional context is needed. Edit the
   generated file to add details below the title heading.

7. Confirm the file was created and show the path.
