---
agent: manual
created: 2026-06-14
id: s0035
kind: spec
name: render-detail-single-artifact-view
status: draft
---

# `render_detail` — Single-Artifact Detail View for `artifacts show`

Spec for a new renderer in `artifacts_os.views` that displays one
artifact as a vertical key/value card (a `rich.Panel`), replacing the
one-row table currently used by `artifacts show`.

Extends [[s0007-artifacts-os-views-module]] (the views module and its
`KindDef.meta` convention). Sibling to the `table` / `tree` renderers
specified in [[s0022-tree-layout]].

## 1. Background and Cross-References

The views module ships exactly one tabular primitive, `render_table`,
plus the `tree` layout. There is no single-artifact renderer. The
`show` command therefore renders one artifact by calling
`render_table([artifact], columns)` — a one-row table where each field
becomes a column.

- s0007 — views module: `FieldSpec`, `parse_field_specs`, `format_field`,
  `default_columns`, `render_table`, the `KindDef.meta["columns"]` and
  `meta["status_colors"]` conventions.
- s0022 — tree layout: the layout-abstraction precedent (renderers live
  in `views/`, return rich renderables, never print).

## 2. Goals and Non-Goals

### 2.1 Goals

- Add `render_detail(item, columns, *, status_colors, title, omit_empty)`
  to `artifacts_os.views`, returning a `rich.Panel` with fields stacked
  vertically as aligned `Label: value` rows.
- Add a `detail_columns(kind_def, item)` helper that resolves the column
  set for the detail view, defaulting to **all** of the item's
  frontmatter keys (not the list-optimised subset).
- Wire `render_detail` into `show`'s default render path and `--meta`.
- Reuse the existing `status_colors` and `format_field` machinery so the
  detail card is consistent with table output.

### 2.2 Non-Goals

- Changing the `show` editor-default behaviour (humans → `\$EDITOR`).
  `render_detail` makes a good inline view *possible*; whether to flip
  the default is deferred to § 11 Open Questions.
- Markdown/rich rendering of the artifact body. Body printing stays as
  the current raw `markup=False` dump.
- Any new layout in the `LAYOUTS` registry. `render_detail` is a
  single-item renderer, orthogonal to the multi-item layout dimension.
- TUI integration (tracked separately under s0006).

## 3. Motivation — the current gap

Three problems with the status quo (all in `cli/commands/show.py`):

1. Default render uses `default_columns(kind_def)` = `meta["columns"]`,
   which is tuned for the *list* view (few compact columns). So `show`
   displays only that subset — you cannot see all of an artifact's
   fields in the default mode.
2. `--meta` shows all frontmatter keys, but as a one-row table: every
   key becomes a column, producing horizontal sprawl that wraps badly
   for artifacts with many keys or long values.
3. Empty fields render as blank columns (noise); there is no semantic
   grouping or alignment.

The result: AOS has no clean human-facing rendered view of a single
artifact — the default mode is incomplete, `--meta` is an ugly wide
table, and the only readable path is opening the file in an editor.

## 4. Public API

Added to `artifacts_os.views` (implemented in `views/_views.py`,
exported from `views/__init__.py`):

\`\`\`python
def render_detail(
    item: ItemMeta,
    columns: list[FieldSpec],
    *,
    status_colors: Mapping[str, str] | None = None,
    title: str | None = None,
    omit_empty: bool = True,
) -> rich.panel.Panel:
    \"\"\"Render one artifact as a vertical key/value card.\"\"\"
\`\`\`

And a column resolver, parallel to `default_columns`:

\`\`\`python
def detail_columns(kind_def: KindDef | None, item: ItemMeta) -> list[FieldSpec]:
    \"\"\"Resolve the detail-view column set for an item.

    Precedence:
      1. kind_def.meta[\"detail_columns\"]  (list of field-spec strings)
      2. all of item's frontmatter keys, in document order
    \"\"\"
\`\`\`

This introduces one new `KindDef.meta` convention key, `detail_columns`,
documented alongside `columns` / `status_colors` in s0007. It is
optional; absent it, the detail view shows every field.

## 5. Rendering semantics

`render_detail` builds, for each `FieldSpec` in `columns`:

- A row `f\"{label}: {value}\"` where `value = format_field(item.cell(key, \"\"), fmt)`.
- Labels right-padded to `max(len(label))` so the colons align vertically.
- When `col.key == \"status\"` and the value is in `status_colors`, the
  value is wrapped in `rich.text.Text(value, style=...)` (same rule as
  `render_table`).
- When `omit_empty` is True, rows whose formatted value is empty (`\"\"`)
  are skipped entirely.

The rows are composed into a single left-aligned `rich.text.Text` and
wrapped in a `rich.panel.Panel(text, title=title, expand=False)`. When
`title` is None, callers in this spec pass the artifact's `id` (or
`name` when there is no id).

This is the data-driven generalisation of openstation's bespoke
`rich_run_detail` (see § 10).

## 6. CLI wiring — `show` and `--meta`

In `cli/commands/show.py`:

- **Default render path** (currently `render_table([artifact], default_columns(...))`):
  replace with
  \`\`\`python
  columns = views.detail_columns(kind_def, artifact)
  title = artifact.frontmatter.get(\"id\") or artifact.name
  console.print(views.render_detail(artifact, columns, status_colors=status_colors, title=title))
  \`\`\`
  Body printing below it is unchanged.
- **`--meta` path**: same call, with `detail_columns` naturally yielding
  all frontmatter keys (no body printed). The existing all-keys one-row
  table is removed.

`-j` (JSON) and `-e` (editor) paths are untouched.

## 7. Column selection — detail vs list columns

The central design point: the detail view must default to **all fields**,
not reuse `meta[\"columns\"]` (which is list-scoped). Hence the separate
`detail_columns` resolver and the optional `meta[\"detail_columns\"]`
override for kinds that want a curated/ordered detail card. Falling back
to frontmatter document order keeps the common case zero-config.

## 8. Reuse of existing machinery

No new formatting or coloring logic is introduced. `render_detail`
reuses `format_field` (date/datetime parsing, `None` → `\"\"`) and the
`status_colors` mapping exactly as `render_table` does, guaranteeing the
detail card and table agree on every cell's rendered value.

## 9. Edge cases

- **No `kind_def`** (unknown kind): `detail_columns(None, item)` returns
  all frontmatter keys; `status_colors` is None → status uncolored.
- **Empty artifact** (no frontmatter beyond required keys): panel renders
  the minimal key set; `omit_empty` prevents blank rows.
- **Very long values**: the Panel wraps text to terminal width (rich
  default); no manual truncation (unlike list columns) since a detail
  view should show full values.
- **Missing key in `meta[\"detail_columns\"]`**: `item.cell(key, \"\")`
  yields `\"\"`, which `omit_empty` then skips.

## 10. Downstream: openstation `rich_run_detail`

openstation's `views/tables.py::rich_run_detail` is a hardcoded version
of this primitive for run records. After this lands, it can be
reimplemented as a thin wrapper:

- OS pre-formats its domain fields (e.g. `turns_used/turns_limit` → `\"3/10\"`,
  `cost` → `\"\$0.1234\"`) into a plain mapping.
- OS calls `render_detail(mapping, columns, status_colors=..., title=f\"Run {id}\")`.

The OS-specific value formatting stays in OS; only the card-rendering
mechanism is shared. This is a downstream benefit, not a requirement of
this spec.

## 11. Open Questions

- **Editor default**: with a readable inline card available, should
  `show` flip its interactive default from `\$EDITOR` to inline render
  (making editor opt-in via `-e`)? Out of scope here; revisit once
  `render_detail` ships and can be dogfooded.
- **`detail_columns` ordering**: frontmatter document order vs a fixed
  canonical order (e.g. id, kind, name, status first). Proposed:
  document order for v1; revisit if it reads poorly.
- **Panel styling**: border style/title format — match the table's plain
  aesthetic (`box=None`-equivalent) or use a bordered panel. Proposed:
  bordered, dim, to visually distinguish a single record from a table.

## 12. Verification

- [ ] `render_detail(item, columns, ...)` exists in `artifacts_os.views`
      and returns a `rich.panel.Panel`.
- [ ] `detail_columns(kind_def, item)` returns `meta[\"detail_columns\"]`
      parsed when present, else all frontmatter keys in document order.
- [ ] Rows render as aligned `Label: value`; colons align across rows.
- [ ] `status` cell is colored via `status_colors` identically to
      `render_table`.
- [ ] `omit_empty=True` skips rows whose formatted value is empty;
      `omit_empty=False` keeps them.
- [ ] `format_field` is reused (a `created:date` field renders the same
      string in `render_detail` and `render_table`).
- [ ] `artifacts show <ref>` default path renders a detail card showing
      all fields (not just `meta[\"columns\"]`).
- [ ] `artifacts show <ref> --meta` renders all frontmatter keys as a
      card (no body, no one-row table).
- [ ] `-j` and `-e` paths of `show` are behaviourally unchanged.
- [ ] Unknown-kind artifact renders without error (no `kind_def`,
      uncolored status).