# Settings

`artifacts-os` reads project configuration from `artifacts.yaml`
at the vault root. `core` parses the global section and stores the full YAML
document so that other modules can extract their own sections without
coupling to the library's release cycle.

---

## Public API

```python
from artifacts_os.core import (
    load_settings,           # parse artifacts.yaml → Settings
    Settings,                # base dataclass
    ProjectConfig,           # project identity (name, alias)
    UnsupportedSchemaVersion, # raised for missing / unknown layout_version
)
```

### `load_settings(path: Path) -> Settings`

Reads and parses the YAML file at *path*.

Raises `UnsupportedSchemaVersion` if `layout_version` is absent or not in
the supported set (currently `{1}`). Raises `KeyError` if the `project`
section is absent.

### `Settings`

Fields: `layout_version: int`, `project: ProjectConfig`, `raw: dict` (full parsed YAML; default `{}`).

### `ProjectConfig`

Fields: `name: str` (required), `alias: str | None` (default `None`).

---

## Worked Example

```python
from artifacts_os.core import find_vault_root, load_settings

root = find_vault_root()
if root is None:
    raise RuntimeError("No artifacts vault found")

settings = load_settings(root / "artifacts.yaml")

print(settings.project.name)       # "my-project"
print(settings.layout_version)     # 1
print(settings.raw.get("views"))   # raw views section, or None
```

---

## Extension Pattern

Modules that own their own settings section subclass `Settings` and add a
`from_base` classmethod that reads their section from `base.raw`:

```python
from dataclasses import dataclass
from artifacts_os.core import Settings, load_settings

@dataclass(kw_only=True)
class MySettings(Settings):
    my_value: str = "default"

    @classmethod
    def from_base(cls, base: Settings) -> "MySettings":
        section = base.raw.get("my_module") or {}
        return cls(
            layout_version=base.layout_version,
            project=base.project,
            raw=base.raw,
            my_value=section.get("value", "default"),
        )

# Usage
base = load_settings(root / "artifacts.yaml")
settings = MySettings.from_base(base)
```

`views` ships the canonical implementation of this pattern —
`ViewsSettings.from_base` reads the `views` and `default_views` top-level
keys out of `base.raw`. See
[../src/artifacts_os/views/README.md](../src/artifacts_os/views/README.md)
for the full `ViewsSettings` API.

To compose settings from multiple modules, chain the `from_base` calls:

```python
combined = RunSettings.from_base(ViewsSettings.from_base(base))
```

Or define a single subclass that reads all relevant sections at once.

---

## Views Section

The `views` and `default_views` top-level keys configure named views for
`artifacts list --view`. Views pre-bundle filters, columns, and sort order
so common queries become a single flag.

```yaml
layout_version: 1
project:
  name: my-project

views:
  active:
    columns: id,name,status,assignee   # columns shown in table mode
    filters:
      status: ready                    # pre-filter by status
      assignee: alice                  # post-discovery equality filter
    sort: name                         # ascending; prefix with "-" for descending

default_views:
  task: active   # auto-applies "active" view when --kind task is given
```

#### Multi-value filters

A filter value may be a list — every element is OR-ed within
the key, while keys remain AND-ed across the dict. This is the
SQL `IN`-style shape: `status: [ready, in-progress, review]`
means "status is any of these three". Spec:
[`s0023-multi-value-filters`](../artifacts/specs/s0023-multi-value-filters.md).

| Filter value | Meaning |
|--------------|---------|
| Scalar (`str`/`int`/`bool`) | Equality, as today. |
| `list` | OR-within-key — match if **any** element compares equal. |
| `tags` (special) | Already list-membership; a list value means "any of these tags is present". |
| Across keys | Always AND. |

```yaml
views:
  # Scalar — single status
  ready:
    columns: id,name,assignee
    filters: { kind: task, status: ready }

  # List — all active (in-flight) work
  active:
    columns: id,name,status,assignee
    filters: { kind: task, status: [ready, in-progress, review] }
    sort: id

  # AND-of-ORs — Alice's open work
  alice-open:
    columns: id,name,status
    filters: { kind: task, status: [ready, in-progress], assignee: alice }
```

**Empty lists** are rejected at view-load time —
`status: []` raises `ValueError` because an empty OR clause is
always a config bug (it matches nothing; if that's the intent,
delete the view).

**Usage:**

```bash
# Explicit view
artifacts list --view active

# Auto-bound view (fires when --kind task is passed)
artifacts list --kind task

# Explicit flag overrides view filter for that key only
artifacts list --view active --status done
```

`ViewsSettings.from_base` parses these sections from `base.raw`. See
[../src/artifacts_os/cli/README.md](../src/artifacts_os/cli/README.md)
for the full precedence model, error handling, and `-j`/`-q` contract.

Run `artifacts views` to list every defined view from the command line; see
[`cli/README.md`](../src/artifacts_os/cli/README.md) for the full reference.

### Layout selection

A view can be drawn as a flat table or as a parent-child tree.
Layout configuration lives **only** in `artifacts.yaml` — kind
JSON describes data shape, presentation is the vault's concern.
Two settings keys steer the choice; both are optional and both
default to "fall through to the implicit table".

**`default_layouts`** — top-level map keyed by kind name, parallel
to `default_views`. Each entry is either a **string-form**
shorthand (for layouts that need no extra config) or an
**object-form** mapping with explicit fields:

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `layout` | `"table"` \| `"tree"` | yes | Layout name; must be in the registry |
| `parent_field` | string | required when `layout: tree`, forbidden otherwise | Frontmatter key on each artifact whose value points up to its parent (wikilink) |

The string-form (`task: table`) is rejected for layouts that
require config — `task: tree` raises `ValueError` at parse time
because `tree` needs `parent_field`. Conversely, setting
`parent_field` under a `layout: table` entry is also a parse-time
error (cheap typo guard).

**`view.layout` and `view.parent_field`** — optional fields on a
single view definition. When `layout` is set, the view pins its
own layout regardless of `default_layouts`. When `layout: tree`,
`parent_field` is required on the same view.

```yaml
views:
  active-tree:
    columns: id,name,assignee,status
    filters: { status: in-progress }
    layout: tree
    parent_field: parent

  active-flat:
    columns: id,name,assignee,status
    filters: { status: in-progress }
    layout: table
```

**Worked example — vault wants flat tasks.** Use the string-form
shorthand:

```yaml
layout_version: 1
project:
  name: my-project

default_layouts:
  task: table          # this vault prefers flat for tasks
```

**Worked example — vault wants tree tasks.** Use the object-form
with `parent_field`:

```yaml
layout_version: 1
project:
  name: my-project

default_layouts:
  task:
    layout: tree
    parent_field: parent
```

`artifacts list --kind task` then renders as a parent-child tree
with `└─` prefix on the first column.

#### Resolution chain — 4 rungs

The active layout is resolved per call. First rung that resolves
wins:

| Rung | Source |
|------|--------|
| 1 (highest) | `--layout NAME` (per call) |
| 2 | `view.layout` (named view) |
| 3 | `default_layouts[<kind>]` (vault default) |
| 4 (implicit) | `"table"` |

When the resolved layout is `tree`, `parent_field` is resolved
through a **sibling chain** consulting the same slots in the
same order — there is no `--parent-field` flag:

| Rung | Source |
|------|--------|
| 1 (highest) | `view.parent_field` |
| 2 | `default_layouts[<kind>].parent_field` |
| 3 (implicit) | none — exits 2 with "layout 'tree' requires parent_field" |

A user who passes `--layout tree` on a kind without a configured
`parent_field` adds one entry to `artifacts.yaml`; the tool will
not infer a field name.

The full design and the rationale for the resolution order live
in [`s0022-tree-layout`](../artifacts/specs/s0022-tree-layout.md).

### Prune mode for tree layouts — `prune`

When the layout is `tree`, the **prune mode** controls how the
tree renders around a filtered slice. Three modes are defined:

| Mode | Rendered set | When to use |
|------|--------------|-------------|
| `strict` *(default)* | only matched rows; orphan parents promote to root with `↑[parent: …]` annotation | triage queues — "what's actually active right now?" |
| `ancestors` | matched rows + every match's parent chain up to root, rendered dim with `· (context)` | give context to narrow filters — "where does this active task live?" |
| `subtree` | matched rows + every match's full descendant set, regardless of filter | feature progress reviews — "show everything around this active feature" |

**Configuration surface.** Like `layout`, prune is set per
view or per kind:

```yaml
default_layouts:
  task:
    layout: tree
    parent_field: parent
    prune: ancestors      # vault-wide kind default

views:
  active:
    columns: id,name,status,assignee
    filters: { kind: task, status: [ready, in-progress, review, verified] }
    layout: tree
    parent_field: parent
    prune: ancestors      # per-view override
    sort: id
```

**Constraints.** `prune` is meaningful only on `layout: tree`
views. Setting it on a `layout: table` (or layout-less) view is
a parse-time `ValueError`. The recognised mode names are
`strict`, `ancestors`, `subtree` — anything else fails parse.

**Resolution chain.** Same shape as `layout` — first match wins:

1. `--prune NAME` CLI flag (per call)
2. `view.prune` (named view)
3. `default_layouts[<kind>].prune` (vault-wide kind default)
4. Implicit `strict`

`--children` and `--parent` neutralise `prune`: when the user
has already shaped an explicit slice, no automatic
ancestor / subtree expansion happens.

The full design lives in
[`s0024-tree-prune-modes`](../artifacts/specs/s0024-tree-prune-modes-strict-ancestors.md).

---

## Events Section

The `events:` key configures the always-on JSONL audit stream.
All fields are optional; omitting the section entirely uses defaults.

```yaml
events:
  enabled: true                    # default true; set false to disable stream
  dir: artifacts/logs/events       # override default directory
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `true` | Enable/disable the audit stream |
| `dir` | path | `artifacts/logs/events` | Directory where daily JSONL files are written |

`EventsSettings.from_base` parses this section:

```python
from artifacts_os.events.settings import EventsSettings
from artifacts_os.core import load_settings

base = load_settings(root / "artifacts.yaml")
events_cfg = EventsSettings.from_base(base)
print(events_cfg.enabled)  # True
print(events_cfg.dir)      # None (use default) or Path("artifacts/logs/events")
```

---

## Hooks Section

The `hooks:` key configures the opt-in reactive layer. Each entry defines
a named hook with a matcher and an action. Hooks are evaluated in
declaration order.

```yaml
hooks:
  - name: notify-on-review
    matcher:
      event: artifact.status_changed
      kind: task
      after: review
    action:
      type: notify
      title: "Review needed: $ART_NAME"
      body: "Task $ART_ID is ready for review"

  - name: lint-before-create
    phase: pre
    blocking: true
    matcher:
      event: artifact.created
      kind: task
    action:
      type: shell
      command: "bin/lint-task $ART_PATH"
      timeout: 30
```

### Hook Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | required | Unique hook name |
| `matcher` | dict | `{}` | Key/value pairs that must all match (AND) |
| `action` | dict | required | Action to execute |
| `phase` | `"pre"` \| `"post"` | `"post"` | When the hook fires relative to the CRUD write |
| `blocking` | bool | `false` | Pre-phase only — abort CRUD on failure when `true` |
| `timeout` | int (seconds) | `30` | Timeout for shell/notify actions |

### Matcher Keys

| Key | Matches against | Example |
|-----|----------------|---------|
| `event` | Event type string; `"*"` catches all | `artifact.created` |
| `kind` | `payload.kind` | `task` |
| `id` | `payload.id` | `t0042` |
| `name` | `payload.name` (slug) | `fix-the-bug` |
| `stem` | `payload.stem` | `t0042-fix-the-bug` |
| `changed` | List membership check | `[status]` |
| `result` | From `artifact.validated` | `fail` |
| `before` | Scalar before-value (`artifact.status_changed`) | `ready` |
| `after` | Scalar after-value (`artifact.status_changed`) | `review` |
| `fields.<key>` | Key in post-update frontmatter | `fields.assignee: developer` |
| `before.<key>` | Pre-update value (`artifact.updated`) | `before.status: ready` |
| `after.<key>` | Post-update value (`artifact.updated`) | `after.status: review` |

A list value on any key is OR-ed within the key (e.g. `kind: [task, spec]`
matches either). The `event: "*"` wildcard matches any event type.

### Action Types

#### `shell`

```yaml
action:
  type: shell
  command: "bin/my-script $ART_PATH"
  timeout: 30
```

Runs via `/bin/sh -c`. Receives `ART_*` environment variables (see below).

#### `notify`

```yaml
action:
  type: notify
  title: "Task ready: $ART_NAME"
  body: "Status changed to $ART_AFTER_STATUS"
  mechanism: auto   # "auto" | "bell" | "desktop"
```

Sends a desktop notification (macOS `osascript`, Linux `notify-send`,
Windows PowerShell). Falls back to a terminal bell when no daemon is
available.

#### `file-drop`

```yaml
action:
  type: file-drop
  path: "artifacts/.notifications/{event}-{ts}.json"
  payload: full   # "full" (default) or "summary"
```

Writes the event payload to a file. `path` supports `{event}`, `{ts}`,
`{kind}`, `{id}` substitutions.

### Environment Variables (`ART_*`)

Hooks receive event context via environment variables:

| Variable | Source |
|----------|--------|
| `ART_EVENT` | Event type string |
| `ART_KIND` | `payload.kind` |
| `ART_ID` | `payload.id` |
| `ART_NAME` | `payload.name` |
| `ART_STEM` | `payload.stem` |
| `ART_PATH` | Absolute path to artifact |
| `ART_VAULT_ROOT` | Vault root directory |
| `ART_BEFORE_STATUS` | Status before update (on status-change events) |
| `ART_AFTER_STATUS` | Status after update |
| `ART_CHANGED` | Comma-joined changed field names |
| `ART_PAYLOAD_JSON` | Full payload as JSON (escape hatch) |

`HooksSettings.from_base` parses the raw hooks list:

```python
from artifacts_os.hooks.settings import HooksSettings
from artifacts_os.core import load_settings

base = load_settings(root / "artifacts.yaml")
hooks_cfg = HooksSettings.from_base(base)
print(hooks_cfg.hooks)  # list of hook config dicts
```

---

## Artbook Section

The `artbook:` key configures the artbook distribution feature, which
lets consumers pull agent defaults (and future book types) from a remote
git repository with one command.

```yaml
artbook:
  distro_url: https://github.com/example/artbook-defaults
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `distro_url` | string | `null` | URL of the distro git repository. Required for `artifacts book` commands. |

When `distro_url` is absent or empty, `ArtbookSettings.distro_url` returns
`None`. The CLI raises `DistroNotConfiguredError` (exit 4) in that case.

`ArtbookSettings.from_base` parses this section:

```python
from artifacts_os.artbook import ArtbookSettings
from artifacts_os.core import load_settings

base = load_settings(root / "artifacts.yaml")
arts = ArtbookSettings.from_base(base)
print(arts.distro_url)  # "https://github.com/example/artbook-defaults" or None
```

Unlike `EventsSettings` (which extends `Settings`), `ArtbookSettings` is a
standalone frozen dataclass. It reads its section from `base.raw` without
inheriting `Settings`' fields, so it composes cleanly alongside other
settings extensions.

---

## Schema Versioning

`artifacts.yaml` must begin with `layout_version: 1`. Any other value (or
its absence) causes `load_settings` to raise `UnsupportedSchemaVersion`.

The supported set is `{1}`. Future versions will be added here when the
schema changes in a backward-incompatible way.

---

## Cross-References

- Architecture overview — [architecture.md](architecture.md)
- `views` settings extension — [../src/artifacts_os/views/README.md](../src/artifacts_os/views/README.md)
- Authoritative spec: `s0010-core-settings-module-spec`
