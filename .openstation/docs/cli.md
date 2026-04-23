---
kind: spec
name: cli-reference
---

# CLI Reference

## Quick Reference

| Command   | Description                                  |
|-----------|----------------------------------------------|
| `list`    | List vault items (default: active tasks; `--kind` to widen) |
| `show`    | Display a single vault item (task-first fallback; `--kind` to restrict) |
| `create`  | Create a new vault artifact (task by default; `--kind` for other types) |
| `status`  | Change a task's lifecycle status             |
| `run`     | Launch an agent on tasks                     |
| `tasks`   | List or show tasks (shim for `list --kind task`; symmetric with `research`/`spec`) |
| `bugs`    | List or show bug tasks (shim for `list --kind task --type bug`) |
| `research` | List or show research artifacts (shim for `list --kind research`) |
| `spec`    | List or show spec artifacts (shim for `list --kind spec`) |
| `artifacts` | *(deprecated)* Browse non-task artifacts — use `list --kind` or per-kind subcommands |
| `agents`  | Manage and inspect agent specs               |
| `hooks`   | Inspect and trigger lifecycle hooks           |
| `logs`    | View task run logs                            |
| `sessions` | List and inspect run records                 |
| `verify`  | Validate artifact frontmatter (id, name, required fields, status) |
| `doctor`  | Validate installation and optionally fix issues |
| `init`    | Initialize Open Station in current directory |
| `self-update` | Update Open Station to latest version    |

## Global Flags

| Flag        | Description              |
|-------------|--------------------------|
| `--version` | Print version and exit   |
| `--help`    | Show help for any command |

---

## `list`

List vault items. Defaults to tasks; use `--kind` to query other artifact types.

### Synopsis

```
openstation list [FILTER] [--kind KIND] [--status STATUS] [--assignee NAME]
                 [--type TYPE] [--fields FIELD_SPECS] [--view NAME]
                 [-q | -j | -e]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `FILTER` | Optional. Task ID/slug or assignee name (auto-detected). Only applies when `--kind task` (default). Numeric values resolve as task IDs and show the subtask tree; non-numeric values filter by assignee. |

### Flags

| Flag               | Default  | Description |
|--------------------|----------|-------------|
| `--kind KIND`      | `task`   | Vault kind to list: `task`, `agent`, `research`, `spec`, `note`, `alert`, or `all`. `all` lists every kind with a `Kind` column. |
| `--status STATUS`  | `active` | Filter by status: `backlog`, `ready`, `in-progress`, `review`, `done`, `failed`, `active`, or `all`. Only applies when `--kind task`. `active` = ready + in-progress + review. When a task ID is given as FILTER, defaults to `all`. |
| `--assignee NAME`  | —        | Filter by assignee (exact match). Only applies when `--kind task`. |
| `--type TYPE`      | —        | Filter by `type` frontmatter field. Applies to tasks and any kind whose files carry a `type` field. Common task types: `feature`, `research`, `spec`, `implementation`, `documentation`, `bug`. |
| `--fields SPECS`   | —        | Comma-separated list of field specs controlling which columns to display and how to format them. Syntax: `field[:format] [as Alias]`. See [Field Specs](#field-specs) below. Ignored when `-j` or `-q` is active. |
| `--view NAME`      | —        | Load a named view from `openstation.yaml`. Applies the view's `columns`, `filters`, and `sort` as defaults. Explicit CLI flags override view settings. See [Views](#views) and `docs/settings.md`. |
| `-q`, `--quiet`    | —        | One name per line, no header (pipe-friendly). With `--kind all`, emits `kind/name` pairs. |
| `-j`, `--json`     | —        | JSON array of objects. Each object has `name`, `kind`, and `summary` keys. |
| `-e`, `--editor`   | —        | Open matching files in `$EDITOR` (default: vim). |

Output flags (`-q`, `-j`, `-e`) are mutually exclusive.

Flags `--status` and `--assignee` have no effect when `--kind` is not `task` and emit a
warning to stderr if supplied. `--type` does **not** trigger this warning — it filters by
the `type` frontmatter field on any kind.

### Field Specs

`--fields` accepts a comma-separated list of **field specs**, each with the form:

```
field[:format] [as Alias]
```

| Part | Required | Description |
|------|----------|-------------|
| `field` | yes | Frontmatter key to display (e.g. `id`, `status`, `created`) |
| `:format` | no | Format hint: `date` or `datetime`. Unknown hints pass the value through raw. |
| `as Alias` | no | Column header override (case-preserved). |

**Supported format hints:**

| Hint | Output |
|------|--------|
| `date` | `YYYY-MM-DD` (date portion only) |
| `datetime` | `YYYY-MM-DD HH:MM` (date and time, no seconds) |

Format hints only affect display — filtering and sort are unaffected.

`--fields` is ignored when `-j` (`--json`) or `-q` (`--quiet`) is active; those modes
always include all fields.

### Views

`--view <name>` loads a named view from `openstation.yaml` and applies its settings as
defaults for this invocation. Views can define:

- `columns` — column list in field spec syntax (same as `--fields`)
- `filters` — key/value equality filters (`status`, `assignee`, `type`)
- `sort` — field to sort by

If the named view does not exist in `openstation.yaml`, the CLI exits with exit code 2.

**Precedence (highest → lowest):**

```
explicit CLI flag  >  --fields  >  view columns  >  default columns
```

`--fields` always overrides view `columns`. Explicit `--status` or `--assignee` override
the corresponding view filter; other view filters remain active. `--view` `filters` and
`sort` still apply even when `--fields` is also present.

#### Artifact-Type View Binding

`default_views` in `openstation.yaml` maps each **artifact type** to a named view,
applied automatically when no explicit `--view` is given:

```yaml
default_views:
  feature: my-feature-view   # when --type feature is active
  session: my-session-view   # always for openstation sessions
  spec: my-spec-view         # when --type spec is active
```

The artifact type is determined by `--type TYPE` on `openstation list`. For
`openstation sessions`, the type is always `session`.

**Binding precedence (highest → lowest):**

```
explicit --view  >  default_views binding  >  no view
```

An explicit `--view` always wins. If absent, the binding for the active artifact
type is applied (if one exists). For non-table modes (`--json`, `--quiet`,
`--editor`), the bound view's `columns` are ignored — only `filters` and `sort`
apply.

If a bound view name does not exist in `views:`, the CLI exits with exit code 2:

```
error: default_views.feature refers to unknown view 'my-feature-view'
```

See `docs/settings.md` for the full schema and examples.

### Examples

```bash
openstation list                          # active tasks (ready + in-progress + review)
openstation list --status all             # all tasks regardless of status
openstation list --status ready --assignee researcher
openstation list -q --status ready        # one task name per line
openstation list --json                   # JSON array of task objects
openstation list --editor                 # open active tasks in editor
openstation list 0042                     # show task 0042 and its subtask tree

openstation list --kind all               # every vault item across all kinds
openstation list --kind research          # research artifacts only
openstation list --kind spec              # spec artifacts only
openstation list --kind agent             # agent specs only
openstation list --kind all --json        # JSON array with 'kind' field on each item
openstation list --kind all -q            # kind/name pairs, one per line
openstation list --type bug               # all bug tasks
openstation list --type feature --assignee developer
openstation list --kind spec --type api   # specs with type: api

# Custom columns
openstation list --fields id,name,status
openstation list --fields id,name,created:date
openstation list --fields "id,name,created:date as Created,status"

# Named views from openstation.yaml
openstation list --view mine
openstation list --view review-queue
openstation list --view mine --status all   # view filters overridden for status
```

---

## `show`

Display a single vault item. Resolves tasks first by default; use `--kind` to restrict to a
specific artifact type.

### Synopsis

```
openstation show NAME [--kind KIND] [-j | -e]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `NAME`   | Required. Item name, ID, slug, or full name. Short numeric IDs are zero-padded automatically (e.g. `42` → `0042`). |

### Flags

| Flag            | Description |
|-----------------|-------------|
| `--kind KIND`   | Restrict resolution to a specific kind: `task`, `agent`, `research`, `spec`, `note`, or `alert`. When omitted, uses task-first fallback. `--kind all` is not valid for `show`. |
| `-j`, `--json`  | Emit parsed frontmatter and body as a JSON object |
| `-e`, `--editor`   | Open the file in `$EDITOR` (default: vim) |

### Resolution Order

**Without `--kind` (task-first fallback):**

1. **Task resolution** — scan `openstation/tasks/` using:
   - Exact match (full name, e.g. `0042-cli-improvements`)
   - ID prefix (zero-padded, e.g. `0042` or `42`)
   - Slug match (e.g. `cli-improvements`)
2. **Artifact fallback** — if no task found, scan `openstation/{agents,research,specs,notes,alerts}/`
   using stem and partial matching.
3. Error (exit code 3) if still not found.

**With `--kind KIND`:**

Resolution restricted to that kind's directory. The same matching strategies
(exact stem, partial match) apply within the directory. Ambiguous matches produce
an error listing all candidates (exit code 4).

### Examples

```bash
openstation show 0042                     # show task by numeric ID
openstation show 42                       # short ID (auto-padded)
openstation show 0042-cli-improvements    # show task by full name
openstation show cli-improvements         # show task by slug (or artifact if no task match)
openstation show 0042 --json              # frontmatter + body as JSON
openstation show 0042 --editor            # open in editor

openstation show unified-vault-query-kind --kind spec      # show a spec artifact
openstation show researcher --kind agent                   # show an agent spec
openstation show stellar-defi-landscape --kind research    # show a research artifact
```

---

## `create`

Create a new vault artifact. Defaults to a task; use `--kind` to create research
notes, specs, planning notes, agent specs, or alerts.

### Synopsis

```
openstation create DESCRIPTION [--assignee NAME] [--owner NAME]
                   [--status STATUS] [--type TYPE] [--parent TASK]
                   [--depends-on TASK [TASK ...]]
                   [--body BODY | --body-file PATH]
                   [--kind {task,research,spec,note,agent,alert}]
                   [--task TASK_ID] [--description TEXT] [--model MODEL]
                   [--connector-type CONNECTOR_TYPE] [--schedule CRON]
                   [--event EVENT]
```

### Arguments

| Argument      | Description |
|---------------|-------------|
| `DESCRIPTION` | Required. Free-text artifact description. Used to generate the slug (kebab-case, max 5 words) and H1 title. |

### Flags

| Flag              | Default   | Kind scope | Description |
|-------------------|-----------|------------|-------------|
| `--kind KIND`     | `task`    | all        | Artifact kind: `task`, `research`, `spec`, `note`, `agent`, or `alert`. |
| `--assignee NAME` | —         | task       | Agent name to assign |
| `--owner NAME`    | `user`    | task       | Who verifies: agent name or `user` |
| `--status STATUS` | see below | task       | Initial status: `backlog` or `ready` only |
| `--type TYPE`     | `feature` | task       | Task type: `feature`, `research`, `spec`, `implementation`, `documentation` |
| `--parent TASK`   | —         | task       | Parent task ID/slug. Wikilink added to child's `parent` field and parent's `subtasks` list automatically. |
| `--depends-on TASK [TASK ...]` | — | task | Task(s) this task depends on. Populates the `depends_on` frontmatter list with wikilinks. Each target is resolved via standard task resolution. |
| `--body BODY`     | —         | all        | Markdown body content (replaces skeleton). Use `--body -` to read from stdin. |
| `--body-file PATH`| —         | all        | Read markdown body from a file. Mutually exclusive with `--body`. |
| `--task TASK_ID`  | —         | spec, alert | Producing task ID (NNNN). Required for `--kind spec`; optional task ref for `--kind alert`. |
| `--description TEXT` | —      | agent      | Agent description (one-line summary for the agent spec). |
| `--model MODEL`   | `claude-sonnet-4-5` | agent | Agent model. |
| `--connector-type TYPE` | —   | alert      | Alert connector type: `reminder`, `internal`, `github`, `slack`, or `telegram`. Required for `--kind alert`. |
| `--schedule CRON` | —         | alert      | Cron expression. Only valid with `--kind alert --connector-type reminder`. |
| `--event EVENT`   | —         | alert      | Event name. Only valid with `--kind alert` and non-reminder connector types. |

**Status default logic:** If `--parent` is set and no `--status` given, inherits the parent's status when the parent is `backlog` or `ready`; otherwise defaults to `backlog`. Without `--parent`, defaults to `backlog`.

**Parent auto-promotion:** When creating a sub-task, the parent is auto-promoted through valid transitions if the child's status outranks it.

### Validation

Validation is two-stage:

1. **Argparse** — enforces that `description` is provided (the only universally required positional argument). All flags are syntactically optional at the argparse level.

2. **`cmd_create` semantic validation** — enforces kind-specific rules after parsing:
   - `--connector-type` is required for `--kind alert`
   - `--task` is required for `--kind spec`
   - Flags incompatible with the active `--kind` are rejected with a clear message:
     ```
     error: --schedule is only valid with --kind alert --connector-type reminder
     error: --connector-type is only valid with --kind alert
     ```

This means argparse errors (`missing argument`, `unrecognized argument`) indicate
a syntax problem, while `error:` messages from `cmd_create` indicate a semantic
mismatch between the flag and the selected kind.

### Examples

```bash
openstation create "add login page"
openstation create "fix auth bug" --assignee developer --status ready
openstation create "child task" --parent 0042
openstation create "implement auth" --parent 0042 --depends-on 0051-research-auth
openstation create "integration tests" --depends-on 0051 0052
openstation create "desc" --body "## Requirements\n\nDo X.\n\n## Verification\n\n- [ ] X done"
openstation create "desc" --body-file spec-body.md
echo "## Requirements..." | openstation create "desc" --body -

# Research, spec, and note artifacts
openstation create "login page ux research" --kind research --task 0042
openstation create "auth service design" --kind spec --task 0042
openstation create "release plan q3" --kind note --task 0042

# Agent specs
openstation create "project-manager" --kind agent
openstation create "data-analyst" --kind agent --description "Analyzes datasets and produces reports" --model claude-opus-4-5

# Alerts
openstation create "daily standup reminder" --kind alert --connector-type reminder --schedule "0 9 * * 1-5"
openstation create "pr merged notification" --kind alert --connector-type github --event pull_request.closed
openstation create "deploy alert" --kind alert --connector-type slack --event deployment --task 0099
```

Prints the created artifact name (e.g. `0113-add-login-page`) to stdout.

---

## `status`

Change a task's lifecycle status.

### Synopsis

```
openstation status TASK [NEW_STATUS]
```

### Arguments

| Argument     | Description |
|--------------|-------------|
| `TASK`       | Required. Task ID, slug, or full name. |
| `NEW_STATUS` | Optional. Target status: `backlog`, `ready`, `in-progress`, `review`, `done`, `failed`. When omitted, shows an interactive picker of valid transitions. |

### Flags

| Flag | Description |
|------|-------------|
| `-f`, `--force` | Bypass transition validation, allowing any status → any status. Prints a warning for invalid transitions. Hooks and parent auto-promotion still run. When combined with the interactive picker (no `NEW_STATUS`), shows all statuses. |

### Valid Transitions

```
backlog → ready → in-progress → review → verified → done
                   ready → backlog
                   in-progress → ready      (suspend)
                   in-progress → backlog    (suspend)
                                  review → in-progress (rework)
                                  in-progress → failed → ready
```

Invalid transitions produce an error showing allowed targets from the current status.

If the task has a parent, auto-promotion is applied after a successful transition.

### Hooks

If lifecycle hooks are configured in `openstation.yaml`, matching
hooks run before the status is written. A failed hook aborts the
transition (exit code 10). See `docs/hooks.md` for configuration.

### Examples

```bash
openstation status 0042                   # interactive picker
openstation status 0042 ready             # backlog → ready
openstation status 42 in-progress         # short ID works
openstation status cli-improvements review
openstation status 0042 backlog --force   # bypass validation
openstation status 0042 --force           # picker shows all statuses
```

---

## `run`

Launch an agent to execute tasks.

### Synopsis

```
openstation run AGENT [flags]             # by-agent mode
openstation run --task TASK [flags]       # by-task mode
openstation run --task TASK --verify [flags]  # verify mode
```

A positional argument starting with a digit is treated as a task ID (equivalent to `--task`).

### Modes

**By-agent (always interactive):** Launches the named agent in an interactive Claude session. Uses `os.execvp` to replace the process. The `-i` flag is accepted but redundant. Detached-only flags (`--budget`, `--turns`, `--max-tasks`, `--quiet`, `--json`) are rejected or warned.

**By-task:** Resolves the task, finds ready subtasks (if any), and executes them sequentially with `stream-json` output. If no subtasks exist, executes the task directly. The agent is read from the task's `assignee` field. Supports both detached (default) and interactive (`-i`) modes.

**Interactive (`-i` / `--interactive`):** Launches an interactive Claude session with task context pre-loaded. Uses `os.execvp` to replace the process. No log capture — Claude's built-in session persistence (`--resume`) provides replay. In by-task mode, this must be explicitly requested. In by-agent mode, this is always the behavior.

**Detached (`-d` / `--detached`, by-task only):** The agent runs in the background via the configured detached backend (default: tmux). Supports budget, turns, and log capture. Only available in by-task mode. An optional session name can be passed: `-d mysession`.

**Verify (`--verify`):** Launches task verification. Requires `--task` and task must be in `review` status. Pre-loads `/openstation.verify <task-id>` as the prompt. Works with `-i` and `--worktree`.

Agent resolution order (highest to lowest priority):

1. `--agent` CLI argument
2. Task `owner` field (skipped if `user` or empty)
3. `settings.verify.agent` project-level default (see `docs/settings.md`)
4. Hardcoded fallback: `project-manager`

### Flags

| Flag                | Default | Description |
|---------------------|---------|-------------|
| `--task TASK`       | —       | Task ID or slug (explicit by-task mode) |
| `-i`, `--interactive` | —     | Interactive mode (replace process, no log capture) |
| `-d`, `--detached [SESSION]` | — | Detached background execution via configured backend (optional session name) |
| `--tmux-mode MODE`  | —       | Override tmux mode for this run: `session`, `window`, or `pane` |
| `--budget USD`      | `5`     | Max USD per invocation (detached only) |
| `--turns N`         | `50`    | Max turns per invocation (detached only) |
| `--max-tasks N`     | `1`     | Max subtasks to execute (detached only) |
| `-w`, `--worktree [NAME]` | — | Run in a Claude worktree (optional name, default: auto-derived from task or agent) |
| `--force`           | —       | Skip task status checks (allow non-ready tasks) |
| `--dry-run`         | —       | Print the command without executing |
| `-q`, `--quiet`     | —       | Suppress progress output (detached only) |
| `-j`, `--json`      | —       | Structured JSON dry-run output (detached only) |
| `--context-only`    | —       | Load task context without injecting "Execute task" prompt (implies `-i`) |
| `--verify`          | —       | Launch verification (agent from task `owner`, requires `--task` in `review`) |

### Incompatibilities

| Combination | Behavior |
|-------------|----------|
| by-agent + `--json` | Error: "JSON output not supported in interactive mode" |
| by-agent + `--quiet` | Error: "Quiet mode not supported in interactive mode" |
| by-agent + `--budget` | Warning to stderr, flag ignored |
| by-agent + `--turns` | Warning to stderr, flag ignored |
| by-agent + `--max-tasks` | Warning to stderr, flag ignored |
| `-i` + `-d` | Error: "cannot combine --interactive and --detached" |
| `-i` + `--json` | Error: "JSON output not supported in interactive mode" |
| `-i` + `--quiet` | Error: "Quiet mode not supported in interactive mode" |
| `-i` + `--budget` | Warning to stderr, flag ignored |
| `-i` + `--turns` | Warning to stderr, flag ignored |
| `-i` + `--max-tasks` | Warning to stderr, flag ignored |
| `-i` + `--dry-run` | Allowed — prints the command that would be `execvp`'d |
| `-i` + task with subtasks | Error with hint to target a specific subtask |
| `-d` + `--json` | Error (unless `--dry-run`) |
| `-d` + by-agent mode | Error: "detached requires --task" |
| `--tmux-mode` + non-tmux backend | Warning to stderr, flag ignored |
| `--context-only` without `--task` | Error: "--context-only requires --task" |
| `--context-only` + `-d` | Error: "--context-only is incompatible with --detached" |
| `--verify` without `--task` | Error: "--verify requires --task" |
| `--verify` + task not in `review` | Error with current status |

### Deprecated Flags

The following flags are deprecated and will be removed in a future
release. They still work but emit a deprecation warning to stderr.

| Deprecated | Replacement | Migration |
|------------|-------------|-----------|
| `-a`, `--attached` | `-i`, `--interactive` | `openstation run agent -a` → `openstation run agent -i` |
| `-t`, `--tmux [SESSION]` | `-d`, `--detached [SESSION]` | `openstation run --task 42 -t` → `openstation run --task 42 -d` |

Migration examples:

```bash
# Old                                     → New
openstation run agent -a                   → openstation run agent -i
openstation run --task 42 -a               → openstation run --task 42 -i
openstation run --task 42 --tmux           → openstation run --task 42 -d
openstation run --task 42 -t myname        → openstation run --task 42 -d myname
```

### Examples

```bash
openstation run researcher                  # interactive agent session (always interactive)
openstation run researcher -i               # same (-i is redundant for by-agent)
openstation run --task 0042 -i              # interactive task session
openstation run --task 0042                 # autonomous (foreground)
openstation run --task 0042 -d              # detached (background)
openstation run --task 0042 -d mysession    # detached with custom session name
openstation run --task 0042 --worktree -i   # in a worktree (auto-named)
openstation run --task 0042 --worktree my-feature -i  # explicit worktree name
openstation run --task 0042 -i --dry-run    # preview interactive command
openstation run researcher --dry-run        # show command without executing
openstation run --task 42 --dry-run --json  # structured JSON dry-run output
openstation run --task 42 --verify -i       # interactive verification
openstation run --task 42 --verify          # autonomous verification
openstation run --task 0042 -d --tmux-mode window  # detached in tmux window mode
```

### Logs

By-task detached execution writes stream-json output to `openstation/logs/<task-name>.jsonl`. Session IDs are extracted and displayed for resumption via `claude --resume <session-id>`. Interactive mode does not capture logs.

---

## `research`

List or show research artifacts from `openstation/research/`.
This is a shim that delegates to `list --kind research` or `show --kind research`.

### Synopsis

```
openstation research [list] [-q | -j | -e]
openstation research show NAME [-j | -e]
openstation research NAME
```

Bare `openstation research` (no sub-action) defaults to `list`. `research NAME` is shorthand
for `research show NAME`.

### Sub-Actions

#### `research list` (default)

List all research artifacts with name and one-line summary.

| Flag | Short | Description |
|------|-------|-------------|
| `--json` | `-j` | JSON array of research artifact objects |
| `--quiet` | `-q` | One artifact name per line (pipe-friendly) |
| `--editor` | `-e` | Open matching files in `$EDITOR` |

#### `research show NAME`

Display a single research artifact. Resolves by stem and partial match within
`openstation/research/`. Exit code 3 if not found, exit code 4 if ambiguous.

| Flag | Description |
|------|-------------|
| `--json` | Frontmatter fields + `body` key as JSON object |
| `--editor` | Open the file in `$EDITOR` (default: vim) |

### Examples

```bash
openstation research                                 # list all research artifacts
openstation research list                            # same as bare 'research'
openstation research list --json                     # JSON array
openstation research list -q                         # one name per line
openstation research show stellar-defi-landscape     # print full research artifact
openstation research stellar-defi-landscape          # shorthand show
openstation research show stellar-defi-landscape --json   # as JSON
openstation research show stellar-defi-landscape --editor # open in editor
```

---

## `spec`

List or show spec artifacts from `openstation/specs/`.
This is a shim that delegates to `list --kind spec` or `show --kind spec`.

### Synopsis

```
openstation spec [list] [-q | -j | -e]
openstation spec show NAME [-j | -e]
openstation spec NAME
```

Bare `openstation spec` (no sub-action) defaults to `list`. `spec NAME` is shorthand
for `spec show NAME`.

### Sub-Actions

#### `spec list` (default)

List all spec artifacts with name and one-line summary.

| Flag | Short | Description |
|------|-------|-------------|
| `--json` | `-j` | JSON array of spec artifact objects |
| `--quiet` | `-q` | One artifact name per line (pipe-friendly) |
| `--editor` | `-e` | Open matching files in `$EDITOR` |

#### `spec show NAME`

Display a single spec artifact. Resolves by stem and partial match within
`openstation/specs/`. Exit code 3 if not found, exit code 4 if ambiguous.

| Flag | Description |
|------|-------------|
| `--json` | Frontmatter fields + `body` key as JSON object |
| `--editor` | Open the file in `$EDITOR` (default: vim) |

### Examples

```bash
openstation spec                                     # list all spec artifacts
openstation spec list                                # same as bare 'spec'
openstation spec list --json                         # JSON array
openstation spec list -q                             # one name per line
openstation spec show unified-vault-query-kind       # print full spec
openstation spec unified-vault-query-kind            # shorthand show
openstation spec show unified-vault-query-kind --json     # as JSON
openstation spec show unified-vault-query-kind --editor   # open in editor
```

---

## `tasks`

List or show tasks from `openstation/tasks/`.
This is a shim that delegates to `list --kind task` or `show --kind task`, providing an
explicit per-kind subcommand symmetric with `research` and `spec`.

### Synopsis

```
openstation tasks [list] [--status STATUS] [--assignee NAME] [--type TYPE] [-q | -j | -e]
openstation tasks show NAME [-j | -e]
openstation tasks NAME
```

Bare `openstation tasks` (no sub-action) defaults to `list`. `tasks NAME` is shorthand
for `tasks show NAME`.

### Sub-Actions

#### `tasks list` (default)

List tasks with name and one-line summary. All standard list filters apply.

| Flag | Short | Description |
|------|-------|-------------|
| `--status STATUS` | — | Filter by status: `backlog`, `ready`, `in-progress`, `review`, `done`, `failed`, `active`, or `all`. Default: `active`. |
| `--assignee NAME` | — | Filter by assignee (exact match) |
| `--type TYPE` | — | Filter by `type` frontmatter field (e.g. `feature`, `bug`, `spec`) |
| `--json` | `-j` | JSON array of task objects |
| `--quiet` | `-q` | One task name per line (pipe-friendly) |
| `--editor` | `-e` | Open matching files in `$EDITOR` |

#### `tasks show NAME`

Display a single task. Resolves by ID, full name, or slug within `openstation/tasks/`.
Exit code 3 if not found, exit code 4 if ambiguous.

| Flag | Description |
|------|-------------|
| `--json` | Frontmatter fields + `body` key as JSON object |
| `--editor` | Open the file in `$EDITOR` (default: vim) |

### Examples

```bash
openstation tasks                                    # list active tasks
openstation tasks list                               # same as bare 'tasks'
openstation tasks list --status all                  # all tasks regardless of status
openstation tasks list --type bug                    # bug tasks only
openstation tasks list --type feature --assignee developer
openstation tasks list --json                        # JSON array
openstation tasks list -q                            # one name per line
openstation tasks show 0042                          # show task by numeric ID
openstation tasks show 0042-cli-improvements         # show task by full name
openstation tasks 0042                               # shorthand show
openstation tasks show 0042 --json                   # as JSON
openstation tasks show 0042 --editor                 # open in editor
```

---

## `bugs`

List or show bug tasks from `openstation/tasks/`.
This is a type-scoped alias that delegates to `list --kind task --type bug` or
`show --kind task`. The `type: bug` filter is implicit and cannot be overridden.

### Synopsis

```
openstation bugs [list] [--status STATUS] [--assignee NAME] [-q | -j | -e]
openstation bugs show NAME [-j | -e]
openstation bugs NAME
openstation bugs ID
```

Bare `openstation bugs` (no sub-action) defaults to `list`. `bugs NAME` and `bugs ID`
are shorthand for `bugs show NAME/ID`.

### Sub-Actions

#### `bugs list` (default)

List tasks where `type: bug`, with name and one-line summary.

| Flag | Short | Description |
|------|-------|-------------|
| `--status STATUS` | — | Filter by status. Default: `active`. |
| `--assignee NAME` | — | Filter by assignee (exact match) |
| `--json` | `-j` | JSON array of bug task objects |
| `--quiet` | `-q` | One task name per line (pipe-friendly) |
| `--editor` | `-e` | Open matching files in `$EDITOR` |

`--type` is not accepted (the bug type is implicit). Supplying `--type` returns exit code 1.

#### `bugs show NAME`

Display a single task by name or ID within `openstation/tasks/`. Does not re-validate
that the task has `type: bug` — resolution follows the same strategies as `show --kind task`.
Exit code 3 if not found, exit code 4 if ambiguous.

| Flag | Description |
|------|-------------|
| `--json` | Frontmatter fields + `body` key as JSON object |
| `--editor` | Open the file in `$EDITOR` (default: vim) |

### Examples

```bash
openstation bugs                                     # list active bug tasks
openstation bugs list                                # same as bare 'bugs'
openstation bugs list --status all                   # all bug tasks regardless of status
openstation bugs list --assignee developer           # bugs assigned to developer
openstation bugs list --json                         # JSON array
openstation bugs list -q                             # one name per line
openstation bugs show 0099                           # show task 0099
openstation bugs 0099                                # shorthand show
openstation bugs 99                                  # short numeric ID (auto-padded)
openstation bugs show 0099 --json                    # as JSON
openstation bugs show 0099 --editor                  # open in editor
```

---

## `artifacts` *(deprecated)*

> **Deprecated.** `openstation artifacts` will be removed in a future release.
> Use `openstation list --kind <kind>` or the per-kind subcommands instead.
> A deprecation warning is printed to stderr on every invocation.
>
> **Migration:**
> | Old command | Replacement |
> |-------------|-------------|
> | `openstation artifacts` | `openstation list --kind all` |
> | `openstation artifacts list` | `openstation list --kind all` |
> | `openstation artifacts list --kind research` | `openstation research` |
> | `openstation artifacts list --kind specs` | `openstation spec` |
> | `openstation artifacts list --kind agents` | `openstation agents` |
> | `openstation artifacts show NAME` | `openstation show NAME` |
> | `openstation art list -q` | `openstation list --kind all -q` |

Browse non-task artifacts from `openstation/` subdirectories.

### Synopsis

```
openstation artifacts [list] [--kind KIND] [-q | -j]
openstation artifacts show <name> [-j | -e]
```

Bare `openstation artifacts` (no sub-action) defaults to `list`.

Alias: `art` (e.g. `openstation art list`).

### Sub-Actions

#### `artifacts list` (default)

List artifacts with name, kind, and one-line summary. Without `--kind`, lists all non-task artifacts (agents, research, specs).

| Flag | Short | Description |
|------|-------|-------------|
| `--kind KIND` | — | Filter by subdirectory: `agents`, `research`, `specs` |
| `--json` | `-j` | JSON array of artifact objects |
| `--quiet` | `-q` | One artifact name per line (pipe-friendly) |

`--json` and `--quiet` are mutually exclusive. Using `--kind tasks` is rejected with a hint to use `openstation list`.

#### `artifacts show <name>`

Display a single artifact by name, resolved across `openstation/research/`, `openstation/specs/`, and `openstation/agents/`. Resolution matches filename stems. Ambiguous matches produce an error listing candidates.

| Flag | Description |
|------|-------------|
| `--json` | Frontmatter fields + `body` key as JSON object |
| `--editor` | Open artifact file in `$EDITOR` (default: vim) |

Exit code 3 if artifact not found. Exit code 4 if ambiguous.

### Examples

```bash
openstation artifacts                         # list all non-task artifacts
openstation artifacts list                    # same as bare 'artifacts'
openstation artifacts list --kind research    # only research artifacts
openstation artifacts list --json             # JSON array
openstation artifacts list -q                 # one name per line
openstation artifacts show cli-feature-spec   # print full artifact
openstation artifacts show cli-feature-spec --json  # as JSON
openstation artifacts show cli-feature-spec --editor   # open in editor
openstation art list -q                       # alias works too
```

---

## `agents`

Manage and inspect agent specs from `openstation/agents/`.

### Synopsis

```
openstation agents [list] [--json | --quiet]
openstation agents show <name> [--json | --editor]
```

Bare `openstation agents` (no sub-action) defaults to `list`.

### Sub-Actions

#### `agents list` (default)

List all agents with name and description.

| Flag | Short | Description |
|------|-------|-------------|
| `--json` | `-j` | JSON array of agent objects |
| `--quiet` | `-q` | One agent name per line (pipe-friendly) |

`--json` and `--quiet` are mutually exclusive.

#### `agents show <name>`

Display the full agent spec (frontmatter + body).

| Flag | Description |
|------|-------------|
| `--json` | Frontmatter fields + `body` key as JSON object |
| `--editor` | Open spec file in `$EDITOR` (default: vim) |

Exit code 3 if agent not found (hints available agents).

### Examples

```bash
openstation agents                          # list all agents (default)
openstation agents list                     # same as bare 'agents'
openstation agents list --json              # JSON array of agent objects
openstation agents list --quiet             # one name per line
openstation agents show researcher          # print full agent spec
openstation agents show researcher --json   # frontmatter + body as JSON
openstation agents show researcher --editor    # open in editor
```

---

## `verify`

Validate artifact frontmatter against structural rules.  Reports errors and
exits non-zero when any are found.

### Synopsis

```
openstation verify [<name>] [--kind <kind>] [--all] [--json]
```

Exactly one scope must be provided: a positional `<name>`, `--kind`, or
`--all`.  Omitting all three exits with code 2 and prints usage.

### Scope Rules

| Scope | What is checked |
|-------|-----------------|
| `<name>` | Single artifact resolved by name or ID (searches across all kinds) |
| `--kind <kind>` | All `.md` files in that kind's directory |
| `--all` | All `.md` files across every registered kind |

### Checks

All 11 structural checks run on each artifact:

| # | Check |
|---|-------|
| 1 | `kind` field is present |
| 2 | `kind` value is a known registry kind |
| 3 | `kind` matches the file's parent directory |
| 4 | `id` field is present |
| 5 | `id` prefix matches the expected prefix for the kind |
| 6 | `id` numeric part is exactly 4 digits (zero-padded) |
| 7 | `id` is consistent with the filename stem |
| 8 | `name` does not embed an ID prefix (e.g. `t0042-slug`) |
| 9 | All required fields for the kind are present |
| 10 | `status` value is valid for the kind (when the kind has a status list) |
| 11 | No duplicate `id` within the same kind |

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--all` | — | Verify all artifacts across all kinds |
| `--kind <kind>` | — | Verify all artifacts of one kind (e.g. `task`, `spec`) |
| `--json` | `-j` | Emit a JSON array: `[{"id", "kind", "file", "errors"}]` |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All artifacts valid |
| 1 | One or more errors found |
| 2 | Usage error (no scope specified, or unknown kind) |

### Examples

```bash
openstation verify --all                    # verify every artifact
openstation verify --kind task              # tasks only
openstation verify t0042                    # single artifact by ID
openstation verify my-spec                  # single artifact by name
openstation verify --all --json             # JSON output of all results
openstation verify --kind spec --json       # JSON output for specs
```

---

## `hooks`

Inspect and trigger lifecycle hooks configured in `openstation.yaml`.

### Synopsis

```
openstation hooks [list]
openstation hooks show <index|matcher>
openstation hooks run <task> <old-status> <new-status> [--phase PHASE] [--dry-run]
```

Bare `openstation hooks` (no sub-action) defaults to `list`.

### Sub-Actions

#### `hooks list` (default)

Display all configured `StatusTransition` hooks in a table showing
index, matcher, phase, timeout, and command.

If no hooks are configured, prints an informational message.

#### `hooks show <index|matcher>`

Display a single hook entry with full details (index, matcher,
command, phase, timeout).

The query can be a 0-based numeric index or a matcher pattern
(e.g. `*→done` or `*->done`). If the matcher matches multiple
entries, an ambiguity error is reported.

Exit code 3 if hook not found. Exit code 4 if ambiguous.

#### `hooks run <task> <old-status> <new-status>`

Manually trigger matching hooks for a simulated transition against
a real task. Sets `OS_*` environment variables as documented in
`docs/hooks.md`.

| Flag | Default | Description |
|------|---------|-------------|
| `--phase PHASE` | `all` | Which phase hooks to fire: `pre`, `post`, or `all` |
| `--dry-run` | — | Show matched hooks without executing them |

Pre-hook failures return exit code 10 (`EXIT_HOOK_FAILED`).
Post-hook failures are reported but return exit code 0.
Invalid status values return exit code 1.

### Examples

```bash
openstation hooks                                          # list all hooks
openstation hooks list                                     # same as bare 'hooks'
openstation hooks show 0                                   # show hook at index 0
openstation hooks show "*→done"                            # show hook by matcher
openstation hooks run 0042 in-progress review              # trigger matching hooks
openstation hooks run 0042 in-progress review --dry-run    # preview without executing
openstation hooks run 0042 ready in-progress --phase pre   # only pre-hooks
```

---

## `logs`

View task run logs from `openstation/logs/`.

### Synopsis

```
openstation logs [TASK] [--tail N] [-f] [-r] [-j]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `TASK`   | Optional. Task ID or slug. When omitted, lists all log files. |

### Flags

| Flag            | Description |
|-----------------|-------------|
| `--tail N`      | Show last N lines (only with a task argument) |
| `-f`, `--format` | Render JSONL through os-format (default for terminal) |
| `-r`, `--raw`   | Show raw JSONL (skip formatting even in terminal) |
| `-j`, `--json`  | Emit JSON output (list mode only) |

### Examples

```bash
openstation logs                          # list all log files
openstation logs --json                   # JSON output
openstation logs 0042                     # show log for task 0042
openstation logs 42 --tail 50            # last 50 lines of task 42's log
```

---

## `sessions`

List and inspect run records from `state.db`. Run records are created for every
detached agent execution and track the full lifecycle from start to finish.

### Synopsis

```
openstation sessions [--status STATUS] [--task TASK] [-q | -j]
```

### Flags

| Flag               | Default | Description |
|--------------------|---------|-------------|
| `--status STATUS`  | —       | Filter by run status: `running`, `complete`, `failed`, or `lost`. When omitted, all statuses are shown. |
| `--task TASK`      | —       | Filter by task name or ID (e.g. `0042` or `0042-add-login`). Prefix matching applies. |
| `-q`, `--quiet`    | —       | One run ID per line, no header (pipe-friendly). |
| `-j`, `--json`     | —       | JSON array of run record objects. Each object includes `id`, `task`, `agent`, `status`, `started`, `finished`, `cost`, and `turns_used`. |

Output flags (`-q`, `-j`) are mutually exclusive.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0    | Success (records listed, even if result set is empty) |
| 1    | Invalid arguments or usage error |
| 2    | Not in an Open Station project |

### Examples

```bash
openstation sessions                          # list all run records
openstation sessions --status running         # show currently active runs
openstation sessions --task 0042              # all runs for task 0042
openstation sessions --status complete --json # completed runs as JSON
openstation sessions -q                       # one run ID per line
```

---

## `doctor`

Validate the Open Station installation and optionally fix issues.
Works identically in the main repo and in worktrees.

### Synopsis

```
openstation doctor [--fix [--force]] [--json] [--quiet]
```

### Checks

Run all checks in order, reporting pass/warn/fail for each:

| # | Check | Pass condition |
|---|-------|---------------|
| 1 | Project root | `.openstation/` exists at git toplevel |
| 2 | Artifact dirs | `openstation/{tasks,agents,research,specs}` exist |
| 3 | Framework dirs | `.openstation/{docs,agents,skills,commands}` exist |
| 4 | Settings file | `.openstation/openstation.yaml` exists and parses |
| 5 | Docs | Required docs present: `lifecycle.md`, `task.spec.md`, `cli.md`, `storage-query-layer.md` |
| 6 | Skills | `openstation-execute` skill dir + `SKILL.md` exists |
| 7 | Claude symlinks | `.claude/{commands,agents,skills}` → `.openstation/…` (valid symlinks) |
| 8 | Agent discovery | `.openstation/agents/*.md` symlinks resolve to `openstation/agents/*.md` |
| 9 | Worktree settings | `.claude/settings.json` has `worktree.symlinkDirectories` containing `.openstation`, `.claude`, `openstation` |
| 10 | Worktree symlinks | If in a linked worktree: `.openstation/`, `.claude/`, `openstation/` are symlinks to main repo |

### Flags

| Flag            | Description |
|-----------------|-------------|
| `--fix`         | Attempt to repair failed checks (missing dirs, broken symlinks, worktree settings) |
| `--force`       | With `--fix`, replace worktree directories even if they contain local-only content |
| `-j`, `--json`  | Emit results as JSON array |
| `-q`, `--quiet` | Exit code only (0 = all pass, 1 = any fail) |

`--json` and `--quiet` are mutually exclusive.

### `--fix` Behavior

When `--fix` is passed, attempts to repair failed checks:

- Missing dirs → `mkdir -p`
- Broken symlinks → recreate (reuses init symlink logic)
- Missing worktree settings → calls `_ensure_symlink_directories()`
- Missing docs/skills → re-copy from install cache
- Worktree directories with local-only content → skipped with hint to use `--force`
- With `--force`, worktree directories are replaced unconditionally
- Unfixable issues report what manual action is needed

### Examples

```bash
openstation doctor                        # check all
openstation doctor --fix                  # check and fix issues
openstation doctor --fix --force          # fix, replacing dirs with local content
openstation doctor --json                 # machine-readable JSON
openstation doctor --quiet                # exit code only
```

---

## `init`

Initialize Open Station in the current directory.

### Synopsis

```
openstation init [--agents NAMES | --no-agents] [--template {minimal,standard,full}]
                 [--user] [--dry-run] [--force]
```

### What It Does

1. Creates the `.openstation/` directory structure and `.claude/`
2. Copies commands, skills, and docs from the install cache (`$OPENSTATION_DIR` or `~/.local/share/openstation`)
3. Installs agent templates (adapted for the project name)
4. Creates `.claude/` symlinks → `.openstation/` for agent, command, and skill discovery

### Flags

| Flag              | Description |
|-------------------|-------------|
| `--agents NAMES`  | Comma-separated agent names to install (default: all available templates) |
| `--no-agents`     | Skip installing agent specs |
| `--template {minimal,standard,full}` | Settings template to install (default: prompt or minimal) |
| `--user`          | Install `.claude/` files to `~/.claude/` (user-level) instead of project |
| `--dry-run`       | Show what would be done without writing |
| `--force`         | Overwrite existing user-owned files |

`--agents` and `--no-agents` are mutually exclusive. `--template`
selects which `openstation.yaml` settings template to install.

### Default Agents

When no filter is specified: `architect`, `author`, `developer`, `project-manager`, `researcher`.

### Examples

```bash
openstation init                          # full init with all agents
openstation init --template standard      # use standard settings template
openstation init --agents researcher,author
openstation init --no-agents
openstation init --user                   # install to ~/.claude/ instead
openstation init --dry-run                # preview without writing
```

### Guards

- Refuses to run inside the Open Station source repo itself.
- Requires the install cache to exist (prompts to run the installer if missing).

---

## `self-update`

Update the Open Station install cache and re-link the CLI binary.

### Synopsis

```
openstation self-update [--version TAG]
```

### Flags

| Flag              | Default  | Description |
|-------------------|----------|-------------|
| `--version TAG`   | latest   | Target version tag (e.g. `v0.10.0`). When omitted, updates to the latest tag from the remote. Bare version numbers are auto-prefixed with `v`. |

### What It Does

1. Fetches tags from the remote in the install cache (`~/.local/share/openstation/` or `$OPENSTATION_DIR`)
2. Checks out the target version (latest tag or `--version`)
3. Force-checkouts to handle dirty install caches (the cache is not user-editable)
4. Re-creates the CLI binary symlink (`~/.local/bin/openstation` → `dist/openstation`)
5. Prints the old and new version
6. If run inside a project with `.openstation/`, suggests running `openstation init` to update the project

### Prerequisites

- The install cache must exist (run the installer first)
- The install cache must be a git clone (curl-only installs are not supported)
- `git` must be available on `$PATH`

### Examples

```bash
openstation self-update                    # update to latest tag
openstation self-update --version v0.10.0  # pin to a specific version
openstation self-update --version 0.10.0   # bare version (auto-prefixed with v)
```

---

## Exit Codes

| Code | Constant              | Meaning |
|------|-----------------------|---------|
| 0    | `EXIT_OK`             | Success |
| 1    | `EXIT_USAGE`          | Invalid arguments or usage error |
| 2    | `EXIT_NO_PROJECT`     | Not in an Open Station project (no `.openstation/` found) |
| 3    | `EXIT_NOT_FOUND`      | Task or agent not found |
| 4    | `EXIT_AMBIGUOUS`      | Ambiguous task query (multiple matches) |
| 5    | `EXIT_TASK_NOT_READY` | Task status is not `ready` (use `--force` to override) |
| 6    | `EXIT_INVALID_TRANSITION` | Invalid lifecycle status transition |
| 7    | `EXIT_NO_CLAUDE`      | `claude` CLI not found on `$PATH` |
| 8    | `EXIT_AGENT_ERROR`    | Agent execution failed (non-zero exit from claude) |
| 9    | `EXIT_SOURCE_GUARD`   | Refused to init inside the source repo |
| 10   | `EXIT_HOOK_FAILED`    | A lifecycle hook failed or timed out (see `docs/hooks.md`) |

## Project Discovery

All commands except `init` require an Open Station project root. The CLI walks up from `$CWD` looking for:

1. A directory containing both `agents/` and `install.sh` (source repo — prefix: `""`)
2. A `.openstation/` subdirectory (installed project — prefix: `".openstation"`)

If the walk-up finds nothing and `$CWD` is inside a git worktree, the main worktree root is checked as a fallback.
