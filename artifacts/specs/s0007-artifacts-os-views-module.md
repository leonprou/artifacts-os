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

Spec for `artifacts_os.views`. The `KindDef.meta` key convention is
defined here. `ViewConfig` is a pure data shape defined in `core.models`
and consumed by `views` for column resolution; parsing and settings-file
I/O are handled by `artifacts_os.config` (see s0009).

Source reference: `~/workspace/open-station/.openstation/openstation.yaml`

## Purpose

Produce renderable representations of artifact data for consumption by
`cli` and `tui`. `views` owns the column layout model, field formatting,
and named view configuration. It does not emit output — callers receive
renderables or strings and print/display them.

## Dependencies

- `artifacts_os` (core) — `ArtifactMeta`, `KindDef`
- `rich>=13` — table rendering

## Public API

```python
from artifacts_os.views import (
    FieldSpec,           # dataclass: key, format, label
    parse_field_specs,   # (spec_str: str) -> list[FieldSpec]
    format_field,        # (value: Any, fmt: str | None) -> str
    render_table,        # (items, columns, *, kind_def) -> rich.Table
    default_columns,     # (kind_def: KindDef) -> list[FieldSpec]
)
```

`ViewConfig` is defined in `core.models` and consumed by `views` for
column resolution. Import it from `artifacts_os.core.models`, not from
`artifacts_os.views`.

## Key Concepts

### FieldSpec

Describes one column: which frontmatter key to display, an optional
format hint (`date`, `datetime`), and a display label.

Spec string syntax: `field[:format] [as Label]`

Examples: `id`, `created:date`, `created:date as Date`

### ViewConfig

`ViewConfig` is defined in `artifacts_os.core.models` (alongside
`KindDef` and `ArtifactMeta`). `views` consumes it — specifically its
`.columns` field — for column resolution in `default_columns` and
`render_table`. `views` does not own, parse, or construct `ViewConfig`;
that responsibility belongs to `artifacts_os.config` via its private
`_parse_view` helper (see s0009 for the parsing path).

`ViewConfig` fields (defined in `core`):

- `columns` — comma-separated field spec string (e.g. `"id,name,status"`)
- `filters` — key/value equality filters (e.g. `{"status": "ready"}`)
- `sort` — optional field name; prefix `-` for descending (e.g. `"-started"`)

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

- **In:** column layout, field formatting, rich table construction
- **Out:** settings-file I/O (delegated to `artifacts_os.config`),
  view-config parsing (delegated to `artifacts_os.config`),
  argument parsing, user interaction, filter application
  (callers filter via `list_artifacts`; `views` only formats results)

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

`artifacts_os.config._parse_view` is called for each entry in the
`views` dict. `views` itself never reads, writes, or parses config files.
