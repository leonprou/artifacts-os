---
kind: spec
name: artifacts-os-views-module
status: draft
created: 2026-04-20
task: "[[0001-migrate-docs-specs-to-openstation]]"
agent: manual
id: s0007
---

# artifacts-os: views Module

Spec for `artifacts_os.views`. `views` owns its own settings: it
defines `ViewConfig`, `ViewsConfig`, and `ViewsSettings` (a subclass
of `core.Settings`), and parses its own section out of the raw YAML
loaded by `core.load_settings`. The `KindDef.meta` key convention is
also defined here.

See [[s0010-core-settings-module-spec]] for the base `Settings`
class and the extension pattern used by `views`.

Source reference: `~/workspace/open-station/.openstation/openstation.yaml`

## Purpose

Produce renderable representations of artifact data for consumption by
`cli` and `tui`. `views` owns the column layout model, field formatting,
and named view configuration. It does not emit output — callers receive
renderables or strings and print/display them.

## Dependencies

- `artifacts_os` (core) — `ArtifactMeta`, `KindDef`, `Settings`
- `rich>=13` — table rendering

## Public API

```python
from artifacts_os.views import (
    FieldSpec,           # dataclass: key, format, label
    parse_field_specs,   # (spec_str: str) -> list[FieldSpec]
    format_field,        # (value: Any, fmt: str | None) -> str
    render_table,        # (items, columns, *, kind_def) -> rich.Table
    default_columns,     # (kind_def: KindDef) -> list[FieldSpec]
    ViewConfig,          # dataclass: columns, filters, sort
    ViewsConfig,         # dataclass: views, default_views
    ViewsSettings,       # core.Settings subclass with .views: ViewsConfig
)
```

`ViewConfig`, `ViewsConfig`, and `ViewsSettings` live in
`artifacts_os.views.models`. `ViewsSettings.from_base(base: Settings)`
takes the result of `core.load_settings` and parses the `views` /
`default_views` sections out of `base.raw`. See
[[s0010-core-settings-module-spec]] for the base `Settings` and the
extension pattern.

## Key Concepts

### FieldSpec

Describes one column: which frontmatter key to display, an optional
format hint (`date`, `datetime`), and a display label.

Spec string syntax: `field[:format] [as Label]`

Examples: `id`, `created:date`, `created:date as Date`

### ViewConfig

`ViewConfig` is defined in `artifacts_os.views.models` and owned by
the `views` module. It is consumed via its `.columns` field for
column resolution in `default_columns` and `render_table`, and
constructed by `ViewsSettings.from_base` when parsing the
`views` section of the settings file.

```python
@dataclass
class ViewConfig:
    columns: str                    # comma-separated field spec string
    filters: dict[str, Any]         # key/value equality filters; default {}
    sort: str | None = None         # optional; "-" prefix = descending
```

Fields:

- `columns` — comma-separated field spec string (e.g. `"id,name,status"`)
- `filters` — key/value equality filters (e.g. `{"status": "ready"}`)
- `sort` — optional field name; prefix `-` for descending (e.g. `"-started"`)

### ViewsConfig

`ViewsConfig` groups the parsed `views` and `default_views` maps:

```python
@dataclass
class ViewsConfig:
    views: dict[str, ViewConfig]    # name → ViewConfig
    default_views: dict[str, str]   # kind → view name
```

### ViewsSettings

`ViewsSettings` extends `core.Settings` (see s0010) and adds a typed
`views: ViewsConfig | None` field. It is constructed via
`ViewsSettings.from_base(base: Settings)`, which reads
`base.raw["views"]` and `base.raw["default_views"]` and parses each
view entry through a private `_parse_view` helper local to `views`.

```python
@dataclass(kw_only=True)
class ViewsSettings(Settings):
    views: ViewsConfig | None = None

    @classmethod
    def from_base(cls, base: Settings) -> "ViewsSettings": ...
```

Typical caller flow:

```python
from artifacts_os.core import load_settings
from artifacts_os.views import ViewsSettings

base = load_settings(path)
settings = ViewsSettings.from_base(base)
columns = settings.views.views["active"].columns
```

`views` is the **only** module that reads or writes the `views` /
`default_views` sections of the settings file. `core` does not parse
them; consumers do not parse them.

### `KindDef.meta` keys consumed by `views`

`KindDef.meta` is **caller-defined** — the `artifacts-os` library never
reads it. `views` reads two conventional keys that callers (e.g.
OpenStation) are expected to populate:

| Key | Type | Purpose | Fallback |
|-----|------|---------|---------|
| `"columns"` | `list[str]` — field spec strings | Default column list for this kind | `["name", "summary"]` |
| `"status_colors"` | `dict[str, str]` — status → rich color | Row/cell coloring in `render_table` | No coloring applied |

Example (caller's `registry.py`):

```python
KindDef(
    name="task", ...,
    meta={
        "columns": ["id", "status", "name", "assignee"],
        "status_colors": {"done": "green", "failed": "red", "ready": "cyan"},
    },
)
```

`default_columns(kind_def)` reads `meta["columns"]` and returns the
corresponding `list[FieldSpec]`. Falls back to `["name", "summary"]`
if the key is absent. `views` treats unknown keys in `meta` as no-ops.

### `render_table`

Accepts `list[ArtifactMeta]` and `list[FieldSpec]`, returns a
`rich.Table`. Optionally accepts `kind_def` to apply status colors.

## Scope Boundary

- **In:** column layout, field formatting, rich table construction,
  ownership of `ViewConfig` / `ViewsConfig` / `ViewsSettings`,
  parsing the `views` and `default_views` sections of the settings
  file via `ViewsSettings.from_base`
- **Out:** raw YAML I/O and `layout_version` validation (handled by
  `core.load_settings`), argument parsing, user interaction,
  filter application (callers filter via `list_artifacts`; `views`
  only formats results)

## Settings YAML Schema (views section)

The `views` key in the settings file maps view names to view dicts.
Each view dict has the following structure (from the reference
`openstation.yaml`):

```yaml
views:
  <name>:
    columns: "field1,field2:fmt,field3"  # required; comma-separated spec string
    filters:                              # optional; key/value equality map
      <field>: <value>
    sort: field_name                      # optional; prefix "-" for descending
```

Examples from the reference:

```yaml
views:
  active:
    columns: id,name,assignee,status
    filters:
      status: in-progress

  session-log:
    columns: id,name,started:datetime,status
    sort: started

  sessions:
    columns: id,task,agent,status,started,cost
    sort: -started
```

`default_views` maps kind names to a view name:

```yaml
default_views:
  session: sessions
  spec: spec
  research: research
  note: note
  alert: alerts
```

`ViewsSettings.from_base` calls a private `_parse_view` helper local
to `views` for each entry in the `views` dict. `core.load_settings`
performs the raw YAML read; `views` performs the section-level
parsing on top of `Settings.raw`.
