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
defined here. The `ViewConfig` full contract and settings YAML schema
are deferred to a follow-up spec.

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
    FieldSpec,          # dataclass: key, format, label
    parse_field_specs,  # (spec_str: str) -> list[FieldSpec]
    format_field,       # (value: Any, fmt: str | None) -> str
    render_table,       # (items, columns, *, kind_def) -> rich.Table
    ViewConfig,         # dataclass: columns, filters, sort
    load_views,         # (path: Path) -> dict[str, ViewConfig]
    default_columns,    # (kind_def: KindDef) -> list[FieldSpec]
)
```

## Key Concepts

### FieldSpec

Describes one column: which frontmatter key to display, an optional
format hint (`date`, `datetime`), and a display label.

Spec string syntax: `field[:format] [as Label]`

Examples: `id`, `created:date`, `created:date as Date`

### ViewConfig

A named view loaded from a settings file. Contains:
- `columns` — list of field spec strings
- `filters` — key/value equality filters (e.g. `status: ready`)
- `sort` — field name to sort by

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

- **In:** column layout, field formatting, named view loading, rich table construction
- **Out:** argument parsing, I/O, user interaction, filter application
  (callers filter via `list_artifacts`; `views` only formats results)

## Deferred

| Item | Notes |
|------|-------|
| `ViewConfig` full contract | Settings YAML schema not yet defined |
| Named view loading format | Tied to settings YAML schema |
| Filter application in views | Evaluate whether `views` applies filters or delegates to core |
