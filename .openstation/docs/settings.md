---
kind: spec
name: settings
---

# Settings

Project-level configuration for Open Station. Settings control
runtime behavior such as lifecycle hooks.

## File Location

| Context | Path |
|---------|------|
| Installed project | `.openstation/openstation.yaml` |
| Source repo | `openstation.yaml` (vault root) |

If the file is missing, Open Station runs with defaults (no
hooks, no overrides).

## Format

YAML document with top-level keys:

```yaml
hooks: ...
defaults: ...
```

## Keys

| Key | Type | Description | Details |
|-----|------|-------------|---------|
| `project` | object | Project identity (name, alias) | See below |
| `hooks` | object | Lifecycle hooks that run on status transitions | [hooks.md](hooks.md) |
| `autonomous` | object | Autonomous execution settings | See below |
| `defaults` | object | Default flag values for CLI commands | See below |
| `views` | object | Named list views (columns, filters, sort) | See below |
| `default_views` | object | Maps artifact types to named views for automatic binding | See below |
| `run` | object | Settings for `openstation run` (detached backend, tmux modes) | See below |
| `verify` | object | Verification settings | See below |
| `connectors` | object | Connector credentials for external alert types | See below |
| `layout_version` | integer | Layout schema version (currently `1`) | Set by `openstation init` |

Keys not listed above are ignored.

## `project`

Project identity used for display and naming.

### Schema

```yaml
project:
  name: openstation
  alias: os
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `project.name` | string | — | Full project name (informational) |
| `project.alias` | string | `"os"` | Short alias used as tmux window name prefix (e.g. `os-0042-my-task`) |

The `alias` is used by `derive_session_name()` in the tmux
backend to prefix window/session names. If not set, defaults
to `os`.

## `autonomous`

Controls autonomous (non-interactive) agent execution.

### Schema

```yaml
autonomous:
  enabled: true
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `autonomous.enabled` | boolean | `false` | When `true`, agents can run autonomously in detached mode |

## `layout_version`

Schema version for the vault layout. Set by `openstation init`
and used for future migrations. Currently always `1`.

```yaml
layout_version: 1
```

## `defaults`

Maps command names to default flag values. When a flag is not
explicitly passed on the command line, the corresponding default
is applied.

### Schema

```yaml
defaults:
  <command>:
    <flag>: <value>
```

**Command keys** use the subcommand name directly for top-level
commands (`show`, `list`, `status`, `run`, `create`) and dot
notation for nested commands (`agents.show`, `agents.list`,
`artifacts.show`, `artifacts.list`).

**Flag names** match the argparse attribute (long form, dashes
replaced with underscores): `editor`, `json`, `quiet`, `status`,
`assignee`, `dry_run`, etc.

**Values** are the default to apply — `true`/`false` for boolean
flags, strings for value flags.

### Scoping: Human-Only

Defaults apply **only in human CLI context**. When the
`CLAUDECODE` environment variable is set (indicating an agent
session), all defaults are skipped. This prevents defaults like
`editor: true` from interfering with agent automation.

### Override Precedence

Explicit CLI flags always override defaults:

```
explicit CLI flag  >  settings default  >  argparse default
```

If a user passes `--json` and the default says `editor: true`,
`--json` wins — the default for `editor` is not applied. This
also respects mutually exclusive flag groups.

### Examples

Open tasks in the editor by default:

```yaml
defaults:
  show:
    editor: true
```

Default list to ready tasks only:

```yaml
defaults:
  list:
    status: ready
```

Multiple commands:

```yaml
defaults:
  show:
    editor: true
  agents.show:
    editor: true
  list:
    status: ready
```

## `views`

Named view presets for `openstation list --view <name>`. Each view
defines a reusable combination of columns, filters, and sort order.

### Schema

```yaml
views:
  <name>:
    columns: <field-spec-list>
    filters:
      <field>: <value>
    sort: <field>
```

| Key | Type | Description |
|-----|------|-------------|
| `columns` | string | Comma-separated field spec list. Same syntax as `--fields`: `field[:format] [as Alias]`. Controls which columns appear and how values are formatted. |
| `filters` | object | Key/value equality filters applied to the task list. Recognised keys: `status`, `assignee`, `type`. Unknown keys are silently ignored. The special value `me` for `assignee` resolves to the current user at query time. |
| `sort` | string | Field name to sort by (ascending). |

All keys are optional. A view with no keys is valid but has no effect.

### Format Hints in `columns`

The `columns` value uses the same field spec syntax as `--fields`:

| Hint | Output |
|------|--------|
| `date` | `YYYY-MM-DD` (date only) |
| `datetime` | `YYYY-MM-DD HH:MM` |

Unknown hints pass values through raw.

### Precedence

When `--view <name>` is used, explicit CLI flags take priority:

```
explicit CLI flag  >  --fields flag  >  view columns  >  default columns
```

`--fields` overrides view `columns` entirely. Explicit `--status` or
`--assignee` override the matching view filter; other view filters
remain active.

`--json` and `--quiet` ignore `columns` but still apply view `filters`
and `sort`.

### Example

```yaml
views:
  mine:
    columns: id,name,status,created:date as Since
    filters:
      assignee: me
      status: active
    sort: created

  review-queue:
    columns: id,name,assignee,status
    filters:
      status: review
    sort: created

  backlog:
    columns: id,name,type,created:date
    filters:
      status: backlog
```

Usage:

```bash
openstation list --view mine
openstation list --view review-queue
openstation list --view mine --status all    # overrides view's status filter
```

---

## `default_views`

Maps artifact types to named views, applied automatically when `openstation list`
is run without an explicit `--view` flag.

### Schema

```yaml
default_views:
  <artifact-type>: <view-name>
```

Each key is an artifact type string (e.g. `task`, `feature`, `bug`, `spec`,
`session`). Each value must be the name of a view defined in the top-level
`views:` block. All keys are optional.

### Valid Artifact Types

Any string value that appears as the `type:` field on vault items is valid.
Common values:

| Type | Source |
|------|--------|
| `task` | Default for tasks without an explicit type |
| `feature`, `bug`, `spec`, `research` | Custom task/artifact types |
| `session` | Always set for `openstation sessions` output |

### Precedence

```
explicit --view  >  default_views binding  >  no view
```

An explicit `--view` always wins. If absent, the binding for the active artifact
type is applied (if one exists). If no binding exists, no view is applied.

For `--json`, `--quiet`, and `--editor` modes, the bound view's `columns` are
ignored — only `filters` and `sort` apply.

If a bound view name does not exist in `views:`, the CLI exits with exit code 2:

```
error: default_views.feature refers to unknown view 'active-features'
```

### Example

```yaml
views:
  active-features:
    columns: id,name,assignee,status
    filters:
      type: feature
      status: active
    sort: created

  session-log:
    columns: id,name,started:datetime,status
    sort: started

default_views:
  feature: active-features   # openstation list --type feature → active-features view
  session: session-log       # openstation sessions            → session-log view
```

See [plans/output-type-view-binding.md](plans/output-type-view-binding.md) for the
full design and implementation notes.

---

## `run`

Settings for `openstation run`.

### Schema

```yaml
run:
  detached_backend: tmux
  tmux:
    mode: session
    target_session: os
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `detached_backend` | string | `"tmux"` | Backend for `-d`/`--detached`. Validated against registered backends at dispatch time. |
| `tmux.mode` | enum | `"session"` | Tmux launch mode: `session` (new detached session per run), `window` (new window in target session), or `pane` (split pane in target session) |
| `tmux.target_session` | string | `"os"` | Target tmux session name for `window` and `pane` modes. Ignored in `session` mode. |

The `--tmux-mode` CLI flag overrides `tmux.mode` for a single
invocation without changing `openstation.yaml`.

## `verify`

Settings for `openstation run --verify`.

### Schema

```yaml
verify:
  agent: <agent-name>
```

| Key | Type | Description |
|-----|------|-------------|
| `agent` | string | Default agent for `--verify` mode. Used when the task `owner` is `user` or empty and no `--agent` flag is given. |

### Agent Resolution Order

When `--verify` resolves the verification agent, it uses this
precedence (highest to lowest):

1. `--agent` CLI argument
2. Task `owner` field (skipped if `user` or empty)
3. `settings.verify.agent` (project-level default)
4. Hardcoded fallback: `project-manager`

### Example

```yaml
verify:
  agent: reviewer
```

With this setting, `openstation run --task 42 --verify` uses
the `reviewer` agent when the task's `owner` is `user`.

## Example

Settings file with project identity, a hook, defaults, views, run
config, and verify agent:

```yaml
project:
  name: openstation
  alias: os

hooks:
  StatusTransition:
    - matcher: "*→done"
      command: bin/hooks/auto-commit
      phase: post
      timeout: 120

defaults:
  show:
    editor: true

views:
  mine:
    columns: id,name,status,created:date as Since
    filters:
      assignee: me
      status: active
    sort: created

  review-queue:
    columns: id,name,assignee,status
    filters:
      status: review

  session-log:
    columns: id,name,started:datetime,status
    sort: started

default_views:
  feature: mine              # openstation list --type feature → mine view
  session: session-log       # openstation sessions            → session-log view

run:
  detached_backend: tmux
  tmux:
    mode: window
    target_session: os

verify:
  agent: project-manager

connectors:
  github:
    webhook_secret: $GITHUB_WEBHOOK_SECRET
  slack:
    signing_secret: $SLACK_SIGNING_SECRET
  telegram:
    bot_token: $TELEGRAM_BOT_TOKEN
```

See [hooks.md](hooks.md) for the full hook schema, matchers,
environment variables, and execution model.

## `connectors`

Credentials for external alert connector types. Heartbeat looks up the
matching connector config when processing `github`, `slack`, or `telegram`
alerts. Environment variable references (`$VAR`) are expanded at runtime.

### Schema

```yaml
connectors:
  github:
    webhook_secret: $GITHUB_WEBHOOK_SECRET
  slack:
    signing_secret: $SLACK_SIGNING_SECRET
  telegram:
    bot_token: $TELEGRAM_BOT_TOKEN
```

| Connector | Key | Description |
|-----------|-----|-------------|
| `github` | `webhook_secret` | Secret used to validate incoming GitHub webhook payloads |
| `slack` | `signing_secret` | Secret used to validate Slack event payloads |
| `telegram` | `bot_token` | Bot API token for receiving Telegram messages |

Only connectors in active use need to be configured. Missing connectors
are ignored unless an alert of that type is active.

See [alerts.md](alerts.md) for the full alert system reference.

## Architecture

### Module layout

| File | Role |
|------|------|
| `src/openstation/hooks.py` | Settings loading (`load_settings`), hook loading and execution |
| `src/openstation/cli.py` | Default application (`_apply_cli_defaults`), argv scanning (`_explicit_flags`) |

### Integration points

- `hooks.load_settings(root)` reads and parses
  `openstation.yaml` from the vault root, returning the full dict.
  Used by both the hook system and the defaults system.
- `cli._apply_cli_defaults(args, settings)` is called in
  `main()` after argparse and `find_root()`, before command
  routing. Guarded by `CLAUDECODE` env var check.
- `cli._explicit_flags()` scans `sys.argv` to determine which
  flags were explicitly passed, preventing defaults from
  overriding user intent in mutually exclusive groups.

### Data flow

1. `main()` calls `parser.parse_args()` → `args` namespace
2. `find_root()` locates the vault → `root`
3. If `CLAUDECODE` is not set:
   a. `load_settings(root)` reads `openstation.yaml`
   b. `_command_key(args)` derives the lookup key (e.g. `"show"`)
   c. `_explicit_flags()` scans `sys.argv` for user-provided flags
   d. `_apply_cli_defaults()` merges unset flags from settings
4. Command handler runs with merged args
