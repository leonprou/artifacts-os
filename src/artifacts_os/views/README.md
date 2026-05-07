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
    Layout,              # callable type alias for layout functions
    LAYOUTS,             # registry: layout name → layout function
    render_tree,         # tree layout entry point
    compute_tree,        # pure ordering helper used by render_tree
    TreeNote,            # row annotation enum (NORMAL / ORPHAN_* / CYCLE_BREAK)
    ViewConfig,
    ViewsConfig,
    ViewsSettings,
)
```

### `FieldSpec`

One display column: `key` (frontmatter key), `fmt` (`"date"`, `"datetime"`, or `None`),
`label` (column header). Created by `parse_field_specs`; consumed by `render_table` and
`default_columns`.

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

## Layouts

A **layout** is a function that takes a list of `ArtifactMeta`
plus a column list and returns a `rich` renderable. Layouts are
the seam at which `views/` decides how rows are *arranged* —
flat or hierarchical — without changing the column model
(`FieldSpec`, `format_field`, `default_columns`,
`status_colors`) the rest of the module owns.

The shipped registry has two members:

| Name   | Function       | What it draws                                    |
|--------|----------------|--------------------------------------------------|
| `table` | `render_table` | Flat `rich.Table`, one row per item, input order |
| `tree`  | `render_tree`  | `rich.Table` with rows pre-ordered parent-before-children and a `└─` prefix on the first column; the caller (CLI) supplies `parent_field` — the renderer is mechanism-agnostic |

`render_tree` returns a `rich.Table` (not `rich.Tree`) so the
existing column model and status coloring carry over unchanged
— the tree shape is encoded as a prefix on the first column.

### Registry — `LAYOUTS`

```python
from artifacts_os.views import LAYOUTS, render_tree, render_table

LAYOUTS["table"] is render_table   # True
LAYOUTS["tree"] is render_tree     # True
```

The CLI looks up the chosen layout name in `LAYOUTS` and calls
it. An unknown name raises `ValidationError`.

### Registering a third layout

A future layout (e.g. `board`) slots in additively:

```python
from artifacts_os.views.layouts import LAYOUTS

def render_board(items, columns, *, kind_def=None, **kw):
    ...   # return a rich renderable
    return board

LAYOUTS["board"] = render_board
```

Once registered, the new name becomes a valid value of
`default_layouts[<kind>]`, `view.layout`, and `--layout`. No
changes are required in the CLI resolution chain or in
`render_table` / `render_tree`.

The renderer ordering algorithm (parent-before-children
traversal, sibling order, cycle handling, four orphan/cycle
cases) is the responsibility of each layout. For `tree` see
[`s0022-tree-layout`](../../../artifacts/specs/s0022-tree-layout.md)
§ 6 for the full algorithm and § 8 for how the CLI selects a
layout.

### Prune modes — `PRUNE_MODES`

`render_tree` accepts a `prune` keyword argument that controls
how the tree renders around a filtered slice:

| Mode | Behaviour |
|------|-----------|
| `strict` *(default)* | render only the matched set; orphans promote to root with `↑[parent: …]` |
| `ancestors` | walk every match's parent chain via `full_items`; ancestors render as `TreeNote.CONTEXT_ANCESTOR` rows (dim, marked `· (context)`) |
| `subtree` | expand every match's full descendant set via `full_items`; descendants render as normal rows |

When `prune != "strict"`, the caller must pass `full_items`
(an unfiltered `list[ArtifactMeta]`) so the engine can walk
ancestors and descendants. The set of registered modes is
exposed as `PRUNE_MODES`:

```python
from artifacts_os.views import PRUNE_MODES, render_tree

table = render_tree(
    matched_items, columns,
    parent_field="parent",
    prune="ancestors",
    full_items=all_tasks,           # for ancestor / descendant walk
    is_known_stem=registry.exists_stem,
)

assert PRUNE_MODES == frozenset({"strict", "ancestors", "subtree"})
```

The full design lives in
[`s0024-tree-prune-modes`](../../../artifacts/specs/s0024-tree-prune-modes-strict-ancestors.md).

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

`views` owns the `views`, `default_views`, and `default_layouts`
top-level keys of `artifacts.yaml` end-to-end. `core.load_settings`
parses the global section (`layout_version`, `project`) and
stores the rest of the YAML document on `Settings.raw`; `views`
reads its sections out of that dict and produces a typed
`ViewsSettings` via `ViewsSettings.from_base`.

### `ViewConfig`

A single named view: `columns` (field-spec string, same syntax as `parse_field_specs`),
`filters` (frontmatter-key → expected value, default `{}`),
`sort` (field key, default `None`), `layout` (layout name,
default `None` — falls through to the `default_layouts` /
implicit chain), `parent_field` (frontmatter key, required when
`layout: "tree"`, forbidden otherwise). The caller parses
`columns` into `FieldSpec` objects when needed.

`filters` accepts both scalar and list values: a scalar means
equality, a list means OR-within-key (per
[`s0023-multi-value-filters`](../../../artifacts/specs/s0023-multi-value-filters.md)).
Example:

```yaml
active-tree:
  columns: id,name,status
  filters: { kind: task, status: [ready, in-progress, review] }
  layout: tree
  parent_field: parent
```

Empty lists (`status: []`) are rejected with `ValueError` at
`from_base` time — empty OR clauses are always config bugs.

### `LayoutConfig`

A single `default_layouts` entry: `layout` (layout name in
`LAYOUTS`, required) and `parent_field` (frontmatter key,
required when `layout: "tree"`, forbidden otherwise). YAML
accepts a string-form shorthand (`task: table`) for layouts
that need no extra config; tree entries must use the object form
(`task: { layout: tree, parent_field: parent }`).

### `ViewsConfig`

Holds the parsed top-level keys: `views` (`dict[str, ViewConfig]`),
`default_views` (`dict[str, str]` mapping kind name → view name),
and `default_layouts` (`dict[str, LayoutConfig]` mapping kind
name → typed layout config). `default_layouts` is parallel to
`default_views` and steers the layout dimension of the resolution
chain — see
[`docs/settings.md`](../../../docs/settings.md#layout-selection).

### `ViewsSettings`

Subclass of `core.Settings`. Adds `views: ViewsConfig | None` —
`None` when none of `views`, `default_views`, or `default_layouts`
is present in the settings file.

#### `ViewsSettings.from_base(base: Settings) -> ViewsSettings`

Constructs a `ViewsSettings` by reading the `views`,
`default_views`, and `default_layouts` sections out of
`base.raw`. Chain it with `core.load_settings`:

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
