---
kind: spec
name: alerts
---

# Alerts

Alerts are a first-class vault artifact that enable agents to be triggered by
external events. An alert file serves as three things in one: a trigger spec,
an optional pointer to a task, and an agent activity log.

**Storage:** `openstation/alerts/NNNN-slug.md` — same kebab-case naming as tasks. Alert IDs use their own per-artifact counter (`alert_id`), independent from the task ID counter.

## File Location

Alert files live permanently in `openstation/alerts/`:

```
openstation/alerts/NNNN-kebab-slug.md
```

Alert IDs use their own per-artifact counter, independent from task IDs. Never pick IDs manually — use `openstation create --kind alert`.

## Frontmatter Schema

```yaml
---
kind: alert                    # Required. Always "alert".
type: reminder                 # Required. Connector type.
name: NNNN-slug                # Required. Matches filename (without .md).
status: active                 # Required. See Status Values below.
assignee: project-manager      # Optional. Agent to run; null = notification-only.
task: "[[NNNN-task-slug]]"     # Optional. Linked task wikilink; absent = alert is the work item.
schedule: "0 9 * * 1"         # Conditional. Cron expression (reminder type only).
event: deployment              # Conditional. Event name (internal/github/slack/telegram).
filter: "service=api"          # Optional. Key=value filter applied to event payload.
action:                        # Optional. Shell command for notification-only alerts.
  command: "notify-send '$MSG'"
aliases: []                    # Optional. Obsidian aliases for this file.
tags: []                       # Optional. Topic tags for discovery/filtering.
last_triggered: null           # Optional. ISO 8601 timestamp of last trigger.
---
```

### Field Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `kind` | string | yes | — | Always `alert` |
| `type` | enum | yes | — | Connector type: `reminder`, `internal`, `github`, `slack`, `telegram` |
| `name` | string | yes | — | `NNNN-slug`, matches filename (without `.md`) |
| `status` | enum | yes | — | Current state: `active`, `paused`, `done` |
| `assignee` | string | no | `null` | Agent to run when triggered; `null` = notification-only |
| `task` | string | no | `null` | Wikilink to a task to run (`"[[NNNN-slug]]"`); absent means the alert is the work item |
| `schedule` | string | no | — | Cron expression (`"0 9 * * 1"`). Required for `type: reminder`. |
| `event` | string | no | — | Event name to match. Required for `internal`, `github`, `slack`, `telegram` types. |
| `filter` | string | no | — | Key=value filter applied to event payload (e.g., `service=api`) |
| `action.command` | string | no | — | Shell command executed when `assignee` is null (notification-only) |
| `aliases` | list | no | `[]` | Obsidian aliases for vault linking |
| `tags` | list | no | `[]` | Topic tags for discovery and filtering |
| `last_triggered` | datetime | no | `null` | ISO 8601 timestamp of most recent trigger (set by heartbeat) |

### Status Values

| Value | Meaning |
|-------|---------|
| `active` | Alert is enabled and processed by heartbeat |
| `paused` | Alert is disabled (skipped by heartbeat) |
| `done` | Alert is retired — no longer processed |

## Connector Types

| `type` | Trigger mechanism | Key fields |
|---|---|---|
| `reminder` | Cron schedule checked by heartbeat | `schedule` (cron expression) |
| `internal` | Open Station event log (cursor-based) | `event`, `filter` |
| `github` | External relay → inbox | `event` (comment/deployment/pr), `filter` |
| `slack` | External relay → inbox | `event`, `filter` |
| `telegram` | External relay → inbox | `event`, `filter` |

External types (`github`, `slack`, `telegram`) share the inbox mechanism —
the relay drops a JSON file; heartbeat processes it.

## Examples

**Scheduled reminder (alert is the work item):**
```markdown
---
kind: alert
type: reminder
name: 0001-weekly-backlog-grooming
schedule: "0 9 * * 1"
assignee: project-manager
task: null
status: active
last_triggered: null
---

Review backlog, promote ready tasks, archive stale items.

## Update — 2026-04-07
- Promoted 3 tasks to ready
- Archived 2 stale items
```

**External event with linked task:**
```markdown
---
kind: alert
type: github
name: 0002-on-deploy-run-tests
event: deployment
filter: service=api
assignee: developer
task: "0042-run-integration-tests"
status: active
last_triggered: 2026-04-09T14:00:00
---

Triggered by API service deployments. Runs integration test task.

## Update — 2026-04-09
Deployment detected. Task 0042 run completed, moved to review.
```

**Internal event, notification-only (no agent):**
```markdown
---
kind: alert
type: internal
name: 0003-notify-on-run-fail
event: run_complete
filter: run_status=failed
action:
  command: "notify-send 'FAILED: $OS_TASK_NAME'"
assignee: null
status: active
---

Alert on any failed agent run.
```

## Body Structure

The markdown body follows the frontmatter. It starts with an optional
one-line description and may contain update log entries appended by
the heartbeat on each trigger.

### Opening Description (optional)

A plain-text sentence or two describing what the alert does and why.
This appears as the `summary` in `openstation alerts list`.

```markdown
Review backlog, promote ready tasks, archive stale items.
```

### `## Update — <timestamp>` (append-only)

Each time the alert fires, the heartbeat appends an update entry
in chronological order. These are the only body modifications
after the alert is created — never edit or remove existing entries.

```markdown
## Update — 2026-04-07
- Promoted 3 tasks to ready
- Archived 2 stale items
```

### Canonical Body Order

1. Opening description (optional)
2. `## Update — <ts>` entries, oldest first (appended by heartbeat)

---

## Progressive Disclosure

Alert files start minimal and accumulate update log entries over
time. Only add fields and body sections when they become relevant.

### Stages

| Stage | Frontmatter | Body |
|-------|-------------|------|
| **New** | `kind`, `type`, `name`, `status: active`, `assignee` or `action`, required connector fields | One-line description |
| **Connected** | + `task` (if driving a task), + `filter` (if filtering events) | — |
| **Active** | `last_triggered` updated by heartbeat | + `## Update` entries per trigger |
| **Retired** | `status: done` | Final `## Update` entry noting retirement |

### Rules

1. **Start with the minimum** — only include the fields your connector type needs.
2. **Let heartbeat write updates** — never pre-author update sections; they are machine-written.
3. **Retire, don't delete** — set `status: done` when an alert is no longer needed; the history in update entries remains useful.

---

## Inbox Format

External connectors drop JSON files into `.openstation/inbox/`:

```json
{
  "alert": "0002-on-deploy-run-tests",
  "event": "github_deployment",
  "payload": { "service": "api", "sha": "abc123" },
  "ts": "2026-04-10T14:00:00+03:00"
}
```

Processed files are archived to `.openstation/inbox/processed/`.

## Heartbeat

`openstation heartbeat` — cron-driven, processes all pending triggers each tick.

**State:** a single cursor file (`.openstation/heartbeat.cursor`) tracks the
last processed position in the event log for `internal` alert matching. No
other state is needed.

**Processing order per tick:**
1. `reminder` alerts — compare `schedule` cron expression vs current time
2. `internal` alerts — scan event log from cursor (`.openstation/heartbeat.cursor`), match `event` + `filter`
3. Inbox files — process each `.json` file in `.openstation/inbox/`

**Execution per matched alert:**

| Condition | Action |
|---|---|
| `assignee` set, `task` set | `openstation run --task <id>` |
| `assignee` set, `task` null | `openstation run --alert <name>` |
| `assignee` null | Run `action.command` directly |

After every trigger: append `## Update — <ts>` to alert file, update `last_triggered`.

**Cron setup:**
```bash
* * * * * cd /path/to/project && openstation heartbeat
```

## CLI Reference

```bash
openstation alerts list                   # active alerts (default)
openstation alerts list --type reminder   # filter by connector type
openstation alerts list --status paused
openstation alerts show <name>
openstation alerts create "weekly grooming" --connector-type reminder --schedule "0 9 * * 1"
openstation alerts create "deploy hook" --connector-type github --event deploy.completed
openstation alerts pause <name>           # status → paused
openstation alerts resume <name>          # status → active
openstation alerts done <name>            # status → done

# Equivalent via openstation create --kind alert
openstation create "weekly grooming" --kind alert --connector-type reminder --schedule "0 9 * * 1"
openstation create "deploy hook" --kind alert --connector-type github --event deploy.completed

openstation heartbeat                     # process all pending triggers
openstation run --alert <name>            # run agent in alert context
```

## Creating Alerts

Use `openstation alerts create` or `openstation create --kind alert` to create
a new alert. Both paths are equivalent and auto-assign the next `NNNN` ID.

### Flags

| Flag | Description |
|------|-------------|
| `--connector-type <type>` | Connector type: `reminder`, `internal`, `github`, `slack`, `telegram`. Required. |
| `--schedule <cron>` | Cron expression. Required when `--connector-type reminder`. |
| `--event <name>` | Event name. Required for `internal`, `github`, `slack`, `telegram`. |
| `--assignee <agent>` | Agent to run when triggered. Omit for notification-only alerts. |
| `--status <status>` | Initial status (default: `active`). |

> **Deprecation notice:** `--type` (the old flag name) is a hidden alias for
> `--connector-type` and will be removed in a future release. Use
> `--connector-type` in all new commands and scripts.

### Examples

```bash
# Scheduled reminder
openstation alerts create "weekly grooming" --connector-type reminder --schedule "0 9 * * 1" --assignee project-manager

# GitHub event
openstation alerts create "on deploy run tests" --connector-type github --event deployment --assignee developer

# Internal event, notification-only
openstation alerts create "notify on run fail" --connector-type internal --event run_complete
```

---

## Connector Config in `openstation.yaml`

Connector credentials live in `openstation.yaml` under `connectors:`.
See [settings.md](settings.md) for the full schema.

```yaml
connectors:
  github:
    webhook_secret: $GITHUB_WEBHOOK_SECRET
  telegram:
    bot_token: $TELEGRAM_BOT_TOKEN
  slack:
    signing_secret: $SLACK_SIGNING_SECRET
```

## Integration with Existing Systems

| System | Integration |
|---|---|
| Event log (JSONL) | `internal` alerts subscribe to existing event types; heartbeat reads log cursor-based |
| Hooks | Independent — hooks fire inline; alerts are async and heartbeat-driven |
| `openstation run` | Unchanged — alerts trigger it; no new launch mechanism |
| Sessions / runs | Alert-triggered runs appear in `state.db` identically to manual runs |
