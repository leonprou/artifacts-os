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
    ViewConfig,
    ViewsConfig,
    ViewsSettings,
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
from pathlib import Path
from rich.console import Console
from artifacts_os.core import Registry, KindDef, find_vault_root, list_artifacts
from artifacts_os.views import default_columns, render_table

root = find_vault_root()
kind_def = KindDef(
    name="task", dir="tasks", prefix="t", numbered=True,
    statuses=["backlog", "ready", "in-progress", "done"],
    meta={
        "columns": ["id", "status", "name"],
        "status_colors": {"done": "green", "in-progress": "yellow"},
    },
)
registry = Registry(kinds=[kind_def], root=root)

console = Console()
items = list_artifacts(registry, kind="task")
columns = default_columns(kind_def)                          # reads meta["columns"]
table = render_table(items, columns, kind_def=kind_def)      # applies status_colors
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

## Settings Extension

`views` owns the `views` and `default_views` top-level keys of
`artifacts.yaml` end-to-end. `core.load_settings` parses the global
section (`layout_version`, `project`) and stores the rest of the
YAML document on `Settings.raw`; `views` reads its sections out of
that dict and produces a typed `ViewsSettings` via
`ViewsSettings.from_base`.

### `ViewConfig`

```python
@dataclass
class ViewConfig:
    columns: str                              # e.g. "id, status, created:date as Date"
    filters: dict[str, Any]                   # frontmatter-key → expected value (default: {})
    sort: str | None = None                   # field key to sort by
```

A single named view's configuration. `columns` is a comma-separated
field-spec string in the same syntax accepted by
`parse_field_specs` above; the caller is responsible for parsing it
when it needs `FieldSpec` objects.

### `ViewsConfig`

```python
@dataclass
class ViewsConfig:
    views: dict[str, ViewConfig]              # view name → config
    default_views: dict[str, str]             # kind name → view name
```

The parsed `views` and `default_views` sections of the settings
file, bundled together. `default_views` maps a kind to the name of
the view from `views` that should be used by default.

### `ViewsSettings`

```python
@dataclass(kw_only=True)
class ViewsSettings(Settings):
    views: ViewsConfig | None = None
```

Subclass of `core.Settings`. The `views` field is `None` when
neither `views` nor `default_views` is present in the settings
file; otherwise it holds a populated `ViewsConfig`.

#### `ViewsSettings.from_base(base: Settings) -> ViewsSettings`

Constructs a `ViewsSettings` by reading the `views` and
`default_views` sections out of `base.raw`. Chain it with
`core.load_settings`:

```python
from pathlib import Path
from artifacts_os.core import load_settings
from artifacts_os.views import ViewsSettings

base = load_settings(Path("artifacts/artifacts.yaml"))
settings = ViewsSettings.from_base(base)

if settings.views is not None:
    active = settings.views.views["active"]   # ViewConfig
    active.columns                            # "id, status, created:date as Date"

    default_view = settings.views.default_views.get("task", "active")
```

If a view entry is missing the required `columns` key,
`from_base` raises `ValueError`. Validation of any other view
fields is the caller's responsibility.

A consumer that needs more than one module's settings at once can
either compose subclasses —
`RunSettings.from_base(ViewsSettings.from_base(base))` — or define
a single subclass that adds all the fields it cares about. The
library does not prescribe one or the other.
