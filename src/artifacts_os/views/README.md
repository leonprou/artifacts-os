# artifacts_os.views

Pure formatting layer for artifact data. Provides column layout, field
formatting, and `rich` table construction. Does not emit output — returns
renderables or strings to callers (`cli`, `tui`).

**Spec:** `s0007-artifacts-os-views-module`

**Dependencies:** `artifacts_os.core` (`ArtifactMeta`, `KindDef`), `rich>=13`

---

## Public API

```python
from artifacts_os.views import (
    FieldSpec,
    parse_field_specs,
    format_field,
    default_columns,
    render_table,
)
```

### `FieldSpec`

```python
@dataclass
class FieldSpec:
    key: str        # frontmatter key to read from ArtifactMeta.frontmatter
    fmt: str | None # format hint: "date", "datetime", or None
    label: str      # column header text
```

Describes one display column. Created by `parse_field_specs`; consumed by
`render_table` and `default_columns`.

---

### `parse_field_specs(spec_str: str) -> list[FieldSpec]`

Parses a comma-separated field spec string into a list of `FieldSpec` objects.

**Token syntax:** `field[:format] [as Label]`

| Input | Result |
|-------|--------|
| `"id"` | `FieldSpec(key="id", fmt=None, label="id")` |
| `"created:date"` | `FieldSpec(key="created", fmt="date", label="created")` |
| `"created:date as Date"` | `FieldSpec(key="created", fmt="date", label="Date")` |
| `"id, status, created:date as Date"` | three `FieldSpec` objects |

Whitespace around commas and tokens is stripped. Empty tokens are ignored.

---

### `format_field(value: Any, fmt: str | None) -> str`

Formats a raw frontmatter value for display.

| `fmt` | Behaviour |
|-------|-----------|
| `"date"` | Parse ISO datetime string → `"YYYY-MM-DD"` |
| `"datetime"` | Parse ISO datetime string → `"YYYY-MM-DD HH:MM"` |
| `None` | `str(value)`; `None` → `""` |

If parsing fails for `"date"` or `"datetime"`, the raw string is returned
unchanged. `None` values always return `""` regardless of `fmt`.

---

### `default_columns(kind_def: KindDef) -> list[FieldSpec]`

Returns the default column list for a kind.

Reads `kind_def.meta["columns"]` (list of field spec strings) and passes
them through `parse_field_specs`. Falls back to `["name", "summary"]` when
the key is absent.

```python
kd = KindDef(name="task", ..., meta={"columns": ["id", "status", "created:date as Date"]})
cols = default_columns(kd)
# → [FieldSpec("id", None, "id"), FieldSpec("status", None, "status"), FieldSpec("created", "date", "Date")]
```

---

### `render_table(items: list[ArtifactMeta], columns: list[FieldSpec], *, kind_def: KindDef | None = None) -> rich.Table`

Builds and returns a `rich.Table` from *items* and *columns*.

- One column per `FieldSpec`, using `label` as the header.
- One row per `ArtifactMeta`; each cell formatted via `format_field`.
- Missing frontmatter keys render as `""`.
- If `kind_def` is provided, `meta["status_colors"]` is applied: the
  `status` cell is wrapped in a `rich.text.Text` with the mapped style.
  Status values not in the mapping render as plain strings.

---

## `KindDef.meta` Convention

`KindDef.meta` is caller-defined — the `artifacts-os` library never
populates it. The `views` module reads two conventional keys:

| Key | Type | Purpose | Fallback |
|-----|------|---------|---------|
| `"columns"` | `list[str]` (field spec strings) | Default column list | `["name", "summary"]` |
| `"status_colors"` | `dict[str, str]` (status → rich style) | Cell coloring for `status` column | No coloring |

Example (caller's `registry.py`):

```python
KindDef(
    name="task",
    dir="tasks",
    prefix="t",
    numbered=True,
    meta={
        "columns": ["id", "status", "name", "assignee"],
        "status_colors": {
            "done":        "green",
            "ready":       "cyan",
            "in-progress": "yellow",
            "failed":      "red",
        },
    },
)
```

---

## Usage Example

End-to-end: list artifacts, build columns, render, print.

```python
from rich.console import Console
from artifacts_os.core import Registry, list_artifacts
from artifacts_os.views import default_columns, render_table

console = Console()
registry = Registry.load("registry.yaml")
kind_def = registry.get("task")

items = list_artifacts(vault_path, kind_def)
columns = default_columns(kind_def)           # reads meta["columns"]
table = render_table(items, columns, kind_def=kind_def)  # applies status_colors
console.print(table)
```

To override columns at the call site:

```python
from artifacts_os.views import parse_field_specs, render_table

columns = parse_field_specs("id, status, created:date as Created")
table = render_table(items, columns, kind_def=kind_def)
console.print(table)
```

---

## Not Yet Implemented

| Name | Notes |
|------|-------|
| `ViewConfig` | Named view dataclass (columns, filters, sort) — deferred pending settings YAML schema |
| `load_views` | Loads named views from a settings file — blocked on `ViewConfig` |

These are intentionally omitted from `__all__` until the settings YAML
schema is defined.
