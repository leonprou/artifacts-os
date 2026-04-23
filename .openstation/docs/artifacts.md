---
kind: doc
name: artifacts
---

# Artifacts

This document covers how Open Station stores, discovers, and renders
vault artifacts — non-task items such as agents, notes, research, specs,
and alerts — including the rendering pipeline for `openstation list`
and the status-colouring system.

---

## Artifact Kinds and Storage Paths

Open Station recognises six item kinds, all registered in the
**`REGISTRY`** dict in `src/openstation/registry.py`. This is the
single source of truth for kind names, directories, default columns,
valid statuses, discovery callables, and renderer hints.

| Kind       | Singular flag | Directory                  | Renderer   |
|------------|---------------|----------------------------|------------|
| `agent`    | `agent`       | `openstation/agents/`      | artifact   |
| `note`     | `note`        | `openstation/notes/`       | artifact   |
| `research` | `research`    | `openstation/research/`    | artifact   |
| `spec`     | `spec`        | `openstation/specs/`       | artifact   |
| `alert`    | `alert`       | `openstation/alerts/`      | alert      |
| `task`     | `task`        | `openstation/tasks/`       | task       |

**`REGISTRY`** (in `src/openstation/registry.py`) — a
`dict[str, ArtifactKind]` keyed by singular kind name. Each
`ArtifactKind` dataclass carries:

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | Canonical CLI `--kind` value |
| `dir` | `str` | Subdirectory relative to `openstation/` |
| `default_columns` | `list[str]` | Default table columns |
| `statuses` | `list[str] \| None` | Valid statuses; `None` = no status concept |
| `discover` | `Callable \| None` | Custom discover fn; `None` = stdlib scan |
| `filterable_by` | `list[str]` | Filter kwargs accepted by `discover` |
| `renderer` | `str` | `"task"`, `"artifact"`, or `"alert"` |

**`KIND_DIR_MAP`** (in `src/openstation/artifacts.py`) — derived from
`REGISTRY` at import time: `{k: v.dir for k, v in REGISTRY.items() if k != "task"}`.
Includes `"alert": "alerts"` so `resolve_artifact_for_kind` works
for alerts. `"task"` is excluded because tasks use their own path.

**`ARTIFACT_KINDS`** — tuple of directories for non-task, non-alert
kinds: `("agents", "notes", "research", "specs")`. Used by
`discover_artifacts` when no kind filter is given.

### Discovery Functions

**`discover_artifacts(root, kind=None)`** — scans the artifact
subdirectories and returns a list of dicts. Each dict contains all
frontmatter fields plus:

- `name` — filename stem
- `kind` — singular form (e.g. `"agent"`, `"research"`)
- `summary` — `description` frontmatter field, or the first
  non-heading body line (truncated to 80 characters)
- `path` — absolute `Path` to the file

Pass `kind=None` to scan all `ARTIFACT_KINDS` directories.
Pass a singular kind (e.g. `kind="research"`) to restrict discovery
to that directory.

**`resolve_artifact(root, query)`** — resolves a name across all
`ARTIFACT_KINDS` directories. Tries exact stem match first, then
substring match. Returns `(path, error_msg, exit_code)`.

**`resolve_artifact_for_kind(root, query, kind)`** — same resolution
logic restricted to a single kind's directory. Looks up `dir` from the
live `REGISTRY` first (enabling runtime-added kinds), then falls back
to `KIND_DIR_MAP`.

**`resolve_any(root, query, kind=None)`** (in `src/openstation/registry.py`)
— unified resolver used by `openstation show`. Resolution order when
`kind=None`: task → artifacts → alerts. Returns
`(path, error_msg, exit_code)`.

**`discover_alerts(root, *, status=None, type=None)`** (in
`alerts.py`) — scans `openstation/alerts/`. Returns a list of dicts
containing all frontmatter fields plus `_path` and `_text`. Optional
`status` and `type` keyword arguments narrow the results. Also
wired into `REGISTRY["alert"].discover` for unified list paths.

---

## Artifact Naming

Every artifact kind except agents uses the `NNNN-kebab-slug`
pattern. This is the canonical reference for naming;
`storage-query-layer.md` § 1a links here.

| Kind       | Pattern           | ID source                       |
|------------|-------------------|---------------------------------|
| Task       | `NNNN-kebab-slug` | Per-kind, scan `openstation/tasks/` |
| Alert      | `NNNN-kebab-slug` | Per-kind, scan `openstation/alerts/` |
| Research   | `NNNN-kebab-slug` | Per-kind, scan `openstation/research/` |
| Spec       | `NNNN-kebab-slug` | Per-kind, scan `openstation/specs/` |
| Note       | `NNNN-kebab-slug` | Per-kind, scan `openstation/notes/` |
| Agent      | `kebab-slug`      | No prefix — stable CLI identity |

### Auto-assigned NNNN (All kinds except Agents)

All artifact kinds except agents receive IDs via
`openstation create --kind <kind>`, which scans the kind's
directory for the highest existing `NNNN-` prefix and assigns
`max + 1`. IDs are:

- 4-digit zero-padded integers (`0001`, `0042`, `0100`)
- Auto-incrementing per kind (each directory is its own
  counter space — research 0001 and spec 0001 are independent)
- Assigned atomically (`O_CREAT | O_EXCL`) — never pick manually

```
openstation/tasks/0042-add-login-page.md
openstation/alerts/0001-daily-standup.md
openstation/research/0003-login-page-ux-research.md
openstation/specs/0007-storage-query-layer.md
openstation/notes/0002-release-plan.md
```

Provenance (which task produced an artifact) is tracked via the
`task` frontmatter field, not the filename.

### No-prefix (Agents)

Agent filenames are descriptive `kebab-slug` names with no numeric
prefix. The filename is used as the agent identifier in
`openstation run <name>` and must remain stable over time:

```
openstation/agents/researcher.md
openstation/agents/project-manager.md
```

### Existing artifacts are not renamed

This convention applies to **new** artifacts only. Existing files
are not renamed to conform — moving files breaks wikilinks,
history, and symlinks.

---

## Rendering Pipeline

`openstation list` is handled by `cmd_list()` in
`src/openstation/tasks.py`. The call chain is:

```
cmd_list()
  │
  ├─ load settings from openstation.yaml
  ├─ resolve view: default_views → --view → view config (filters, columns, sort)
  ├─ resolve columns: --fields > view columns > default
  │
  ├─ kind == "alert"   → discover_alerts()   → rich_artifact_table()
  ├─ kind != "task"    → discover_artifacts() → rich_artifact_table()
  └─ kind == "task"    → discover_tasks()    → rich_task_table()
```

> **Shortcut equivalence:** `openstation alerts list` and
> `openstation list --kind alert` reach the same `cmd_list()` path via
> shortcut delegation — the `alerts` subcommand synthesises `kind="alert"`
> and forwards to `cmd_list`. All filtering, sorting, and column
> resolution behave identically through either entry point.

### Step 1 — View Resolution

Settings are loaded from `openstation.yaml` via `load_settings()`.

If `--view` is not given, `cmd_list` checks `default_views` in
settings. The active type is `--type` if provided, otherwise
`--kind`. If the active type has an entry in `default_views`, the
bound view name is used exactly as if `--view` had been passed.

```yaml
# openstation.yaml
default_views:
  task:     my-tasks     # applied when listing tasks
  research: by-date      # applied when listing research
  bug:      active-bugs  # applied when --type bug
```

If `default_views.<type>` names a view that does not exist in
`views`, `cmd_list` exits with an error.

### Step 2 — View Configuration

When a view name is resolved, its config block is read from
`settings["views"][view_name]`:

```yaml
views:
  my-tasks:
    columns: "id,name,status,assignee,created:date as Created"
    filters:
      status: ready
      assignee: researcher
    sort: "-created"   # leading "-" = descending
```

Filters are applied **only if the corresponding CLI flag was not
given**. A `--status` flag always wins over the view's `status`
filter; `--assignee` wins over the view's `assignee` filter.

`columns` and `sort` from the view are stored for the next step.

### Step 3 — Column Resolution

```
--fields  (highest priority)
  └─ parse_field_specs(fields_str)  → columns list

view.columns  (if --view or default_views matched)
  └─ parse_field_specs(view_cols_str) → columns list

default  (no --fields and no view columns)
  └─ columns = None  → built-in table layout
```

`parse_field_specs()` converts a comma-separated field spec string
into a list of `{"key", "format", "label"}` dicts:

```
"id,name,status,created:date as Created"
→ [
    {"key": "id",      "format": None,     "label": "ID"},
    {"key": "name",    "format": None,     "label": "Name"},
    {"key": "status",  "format": None,     "label": "Status"},
    {"key": "created", "format": "date",   "label": "Created"},
  ]
```

Syntax: `field[:format] [as Alias]`. Known formats: `date`
(truncates to `YYYY-MM-DD`), `datetime` (truncates to
`YYYY-MM-DD HH:MM`). Unknown formats pass through unchanged.

See `docs/views.md` for full `--fields` / `--view` syntax.

### Step 4 — Kind-Specific Filtering and Sorting

After column resolution each kind follows its own path:

**Alerts** — `discover_alerts()` is called with `status` (default
`"active"`) and `type` filters. The view `sort` key is applied if
present.

**Non-task artifacts** (agent, note, research, spec) —
`discover_artifacts(root, kind=kind)` is called. A `--type` filter
is applied post-discovery. Results are sorted alphabetically by name
by default; the view `sort` key overrides this.

**`--kind all`** — all artifact kinds are merged into a single list,
including tasks (tasks are artifacts; they gained separate rendering
and richer functionality over time, but remain the same concept).
`include_kind=True` is passed to `rich_artifact_table` so a Kind
column is prepended.

**Tasks** — `discover_tasks()` is called. Status defaults to
`"active"` (ready, in-progress, review, verified) unless overridden.
After filtering and sorting, `group_tasks_for_display()` builds a
hierarchy of `(task_dict, depth)` tuples for tree rendering.

### Step 5 — Table Rendering

**`rich_artifact_table(items, include_kind=False, columns=None)`**
(in `src/openstation/ui.py`) — renders a Rich table for non-task
artifacts and alerts.

- Without `columns`: two-column layout — Name and Summary (plus
  optional Kind column when `include_kind=True`).
- With `columns`: one column per spec. `status` values pass through
  `styled_status()`. The `summary` field is truncated to 72
  characters. Date/datetime formats are applied by
  `format_field_value()`.

**`rich_task_table(rows, all_tasks=None, running_tasks=None, columns=None)`**
(in `src/openstation/ui.py`) — renders a Rich table for tasks.

- Without `columns` (default layout): Indicator · ID · Name ·
  Status · Assignee · Owner. The indicator column shows `▶` for
  running tasks and `◼` for blocked tasks.
- With `columns`: indicator column is omitted; custom columns are
  rendered. Tree indentation is applied to the `name` field at
  depth > 0. `status` values pass through `styled_status()`.

---

## Status Colouring

`_STATUS_STYLES` and `styled_status()` are defined in
`src/openstation/ui.py`.

```python
_STATUS_STYLES = {
    # Task statuses
    "backlog":     "dim",
    "ready":       "bold white",
    "in-progress": "bold cyan",
    "review":      "yellow",
    "verified":    "green",
    "done":        "green",
    "failed":      "bold red",
    "rejected":    "red",
    # Run / session statuses
    "running":     "bold green",
    "complete":    "green",
    "stale":       "yellow",
    "lost":        "dim red",
    # Alert statuses
    "active":      "bold cyan",
    "paused":      "dim",
}

def styled_status(status: str) -> Text:
    """Return a Rich Text object styled for the given status string."""
    style = _STATUS_STYLES.get(status, "")
    return Text(status, style=style)
```

**Where `styled_status()` is applied:**

| Call site | Condition |
|-----------|-----------|
| `rich_task_table` — default layout | always, on the Status cell |
| `_rich_task_table_custom` — custom columns | when `key == "status"` |
| `rich_artifact_table` — custom columns | when `col["key"] == "status"` |
| `rich_runs_table` | when `key == "status"` |
| `rich_logs_table` | on the status column |
| `rich_run_detail` | when label is `"Status"` |

**Where it is NOT applied:** the default `rich_artifact_table` layout
(Name + Summary columns) does not include a status column, so
`styled_status()` is not called there.

---

## Adding a New Artifact Kind — Checklist

Follow these steps to introduce a new kind (example: `"template"`
stored in `openstation/templates/`).

1. **Add the kind to `REGISTRY`** — in `src/openstation/registry.py`,
   add a new `ArtifactKind` entry:
   ```python
   "template": ArtifactKind(
       name="template",
       dir="templates",
       default_columns=["name", "type", "summary"],
       filterable_by=["type"],
   ),
   ```
   This one change automatically updates `KIND_DIR_MAP`,
   `ARTIFACT_KINDS`, `VALID_NON_TASK_KINDS`, and the `--kind` choices
   for both `list` and `show` CLI subcommands — no other files need
   touching for basic support.

2. **Ensure the directory is created** (if needed) — if the kind's
   directory should be created on `openstation init`, add it to the
   init logic in `src/openstation/init.py`.

3. **Add a `default_views` entry** (optional) — in
   `openstation.yaml`, add a binding so that
   `openstation list --kind template` uses a sensible default view:
   ```yaml
   default_views:
     template: template-list
   views:
     template-list:
       columns: "name,type,summary"
       sort: "name"
   ```

4. **Add status styles** (if the kind has its own statuses) — in
   `src/openstation/ui.py`, add entries to `_STATUS_STYLES`:
   ```python
   "draft":     "dim",
   "published": "green",
   ```
   No changes to `styled_status()` itself are needed — it does a
   plain dict lookup.

5. **Add a per-kind shim** (optional convenience subcommand) — in
   `src/openstation/cli.py`, register the new kind with
   `_cmd_kind_shim(args, root, kind)` so users can type
   `openstation templates` instead of `openstation list --kind template`.

   **Shims must delegate, not implement.** `_cmd_kind_shim` synthesises
   an `argparse.Namespace` and calls one of three shared functions based
   on the subcommand:

   | User command | Delegates to |
   |---|---|
   | `openstation templates` / `openstation templates list` | `tasks.cmd_list(synthetic, root)` |
   | `openstation templates show NAME` | `tasks.cmd_show(synthetic, root)` |
   | `openstation templates create DESCRIPTION` | `tasks._shortcut_create(synthetic, root, kind)` |

   Do **not** add independent logic inside the shim — all business logic
   lives in `cmd_list`, `cmd_show`, and `_shortcut_create`.

6. **Write or update docs** — add a section to this file and update
   `CLAUDE.md`'s Vault Structure table if the new directory is
   user-facing.

---

## Artifact Specs

Each artifact kind has a dedicated spec document that defines its
frontmatter schema, naming convention, body structure, and examples.
Use these as the authoritative reference when creating or validating
artifacts.

| Kind | Spec | Description |
|------|------|-------------|
| `task` | `docs/task.spec.md` | Unit of work — status lifecycle, requirements, findings, verification |
| `agent` | `docs/agent.spec.md` | Role definition — capabilities, constraints, allowed tools, skills |
| `spec` | `docs/spec.spec.md` | Feature specification — architecture, components, design decisions |
| `alert` | `docs/alerts.md` | Event-driven trigger — connector types, schedule, inbox, heartbeat |
| `note` | `docs/note.spec.md` | Planning note — roadmaps, release plans, free-form durable documents |
| `research` | `docs/research.spec.md` | Research output — findings, confidence levels, sources, recommendations |
