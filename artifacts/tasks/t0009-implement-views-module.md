---
kind: task
id: t0009
name: implement-views-module
type: implementation
status: done
assignee: developer
owner: user
created: 2026-04-22
started: 2026-04-22
completed: 2026-04-22
---

# Implement Views Module

## Requirements

Implement `src/artifacts_os/views/` per `artifacts/specs/s0007-artifacts-os-views-module.md`.

### Scope

Implement the full public API **except** `ViewConfig` and `load_views` — those are
blocked on the settings YAML schema (still deferred in the spec).

### Public API to implement

```python
from artifacts_os.views import (
    FieldSpec,          # dataclass: key, format, label
    parse_field_specs,  # (spec_str: str) -> list[FieldSpec]
    format_field,       # (value: Any, fmt: str | None) -> str
    render_table,       # (items, columns, *, kind_def) -> rich.Table
    default_columns,    # (kind_def: KindDef) -> list[FieldSpec]
)
```

### `FieldSpec`

Dataclass with fields: `key: str`, `fmt: str | None`, `label: str`.

### `parse_field_specs(spec_str)`

Parse a comma-separated field spec string into `list[FieldSpec]`.
Syntax per token: `field[:format] [as Label]`
Examples: `id`, `created:date`, `created:date as Date`

### `format_field(value, fmt)`

Format a raw frontmatter value for display:
- `fmt="date"` — parse ISO datetime string, return `YYYY-MM-DD`
- `fmt="datetime"` — return `YYYY-MM-DD HH:MM`
- `fmt=None` — `str(value)` with `None` → `""`

### `default_columns(kind_def)`

Read `kind_def.meta.get("columns", ["name", "summary"])` and return
`parse_field_specs(",".join(columns))`.

### `render_table(items, columns, *, kind_def=None)`

Build and return a `rich.Table`:
- One column per `FieldSpec` using `label` as header
- One row per `ArtifactMeta` in `items`; each cell via `format_field(value, fmt)`
  where `value = item.frontmatter.get(field_spec.key, "")`
- If `kind_def` given, apply `kind_def.meta.get("status_colors", {})`:
  color the `status` cell using the mapped rich color string

### `__init__.py`

Export all five names above. Do **not** export `ViewConfig` or `load_views`
until those are implemented.

### Dependencies

- `rich>=13` (already in `pyproject.toml` under `[views]` extra)
- `artifacts_os.core` models: `ArtifactMeta`, `KindDef`

### Tests

Add `tests/views/test_views.py`. No mocking — use real `ArtifactMeta` instances
constructed directly (no vault needed). Cover:

- `parse_field_specs`: plain key, key+fmt, key+fmt+label, multiple fields
- `format_field`: date fmt, datetime fmt, None fmt, None value
- `default_columns`: with `meta["columns"]` set, fallback when absent
- `render_table`: correct column headers, correct cell values, status color applied

## Findings

Implemented `src/artifacts_os/views/` with the full scoped public API:

- **`FieldSpec`** — dataclass (`key`, `fmt`, `label`)
- **`parse_field_specs`** — comma-separated token parser; handles `key`, `key:fmt`, `key:fmt as Label`
- **`format_field`** — `date`/`datetime`/passthrough formatting; `None` → `""`
- **`default_columns`** — reads `KindDef.meta["columns"]`, falls back to `["name", "summary"]`
- **`render_table`** — returns `rich.Table`; applies `status_colors` from `KindDef.meta` when provided

Implementation lives in `src/artifacts_os/views/_views.py`; `__init__.py` re-exports all five names. `ViewConfig` and `load_views` are intentionally absent. 27 tests in `tests/views/test_views.py` all pass.

## Progress

### 2026-04-22 — developer
> time: 23:01

Implemented _views.py with all 5 public API items (FieldSpec, parse_field_specs, format_field, default_columns, render_table); updated __init__.py exports; wrote 27 passing tests in tests/views/test_views.py

## Verification

- [ ] All five API functions/classes implemented and exported from `views/__init__.py`
- [ ] `ViewConfig` and `load_views` are **not** exported (still deferred)
- [ ] `parse_field_specs` handles all three token syntaxes
- [ ] `render_table` applies status colors when `kind_def` supplied
- [ ] `pytest tests/views/` passes
- [ ] No imports from `cli` or `tui` (dependency direction enforced)
