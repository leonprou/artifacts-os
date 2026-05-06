---
kind: spec
id: s0022
name: tree-layout
status: approved
created: 2026-05-06
revised: 2026-05-06
task: "[[t0113-spec-tree-layout-for-art]]"
agent: architect
---

# Tree Layout for `art ls`

Sub-spec of [[s0007-artifacts-os-views-module]]. Defines the
**layout abstraction** for `artifacts_os.views`, the **tree
layout** as its first concrete second member alongside the
existing table, and the settings-side / CLI-side / kind-side
contracts that surround them.

Origin: scoping note [[n0002-layouts-tree-view-scoping]]. Task
brief: [[t0113-spec-tree-layout-for-art]]. Revision driver:
[[t0120-spec-revision-move-tree-layout]] — see §0.

**Scope: design only.** Implementation is filed as the four
follow-up tasks listed in n0002 (#2 kind schema, #3 renderer,
#4 CLI wiring, #5 docs). After this revision the renderer,
sort, filter, and `--fields` contracts are unchanged; the
configuration surface moves entirely into `artifacts.yaml`.
The migration of the as-shipped work is filed in §13.

## 0. Revision Notice — 2026-05-06

**This is a revision in place, not a supersede.** Cross-refs
from t0114-family tasks remain valid. Sections rewritten in
this revision: §3, §4.3, §5.5, §8.2, §8.3, §8.5, §10, §11,
§13, §15 row 1, §16. Sections unchanged: §1, §2, §4 (other
than 4.3), §5 (other than 5.5), §6, §7, §9, §12, §14.

### 0.1 What pivoted

Pre-revision, layout configuration lived in two places: an
`x-layouts` block on the kind JSON (declaring `default` and
`tree.parent_field`), with `artifacts.yaml` providing only an
override layer. The user's framing post-shipping
([[n0002-layouts-tree-view-scoping]] § "Update — 2026-05-06"):

> "Layout shouldn't live in the kind file. It should be defined
> in `artifacts.yaml` views — as a default view for task."

**Post-revision, layout configuration lives only in
`artifacts.yaml`.** Kind JSON describes data shape; presentation
is the user's concern. The `x-layouts` block is deleted entirely
(no narrower form is preserved); `parent_field` moves alongside
the layout name in the settings file.

### 0.2 What did not pivot

- The **renderer** (§4–§7, §9) is mechanism-agnostic. It accepts
  `parent_field` as a parameter; the parameter source changed
  but the renderer did not.
- The **user-facing outcome** (§2, §6.5): `art ls --kind task`
  on this vault still shows `t0042` under `t0036` and
  `t0043`–`t0046` under `t0041`. The configuration that
  produces that shape moves; the shape is contract.
- `-q` / `-j` / `--fields` carve-outs (§8.4, §9) — unchanged.
- `x-columns` (§11) — still on the kind, still untouched. The
  argument for keeping `x-columns` kind-side strengthens:
  columns are a projection of the data the kind defines,
  reusable across every layout.

### 0.3 Breaking-change posture

This is a breaking change against the as-shipped v1 (one day
old, not in the wild). See §11.4 for the explicit
backward-compatibility statement and the migration any
downstream user would need.

## 1. Background and Cross-References

- **Origin** — [[n0002-layouts-tree-view-scoping]]. The note's
  six **Open questions for the spec** are answered §3, §4, §5,
  §6, §7, §9 — a one-to-one mapping recorded in §15.
- **Views model** — [[s0007-artifacts-os-views-module]] § "Public
  API" and § "Key Concepts". `FieldSpec`, `parse_field_specs`,
  `format_field`, `default_columns`, `render_table`, `ViewConfig`,
  `ViewsConfig`, `ViewsSettings` are the existing surface this
  spec extends without breaking.
- **Filter pipeline** — [[s0014-core-unified-filter-api]]. The
  filter resolution this spec interacts with (§7) is the
  pipeline locked there. Layouts run **after** filtering; they
  do not see filter state directly, only the post-filter
  `list[ArtifactMeta]`.
- **Kind discovery** — [[s0017-artifact-kinds-discovery-mechanism]].
  Kind metadata travels via the same `KindDef.meta` channel
  already used for `columns` and `status_colors`. **Post-revision
  (§0):** layout config does **not** travel via this channel;
  it lives in `artifacts.yaml`. `KindDef` does gain a small
  read-only addition (`schema_properties`, §3.6) for the
  parent-field validation guard.
- **CLI list contract** — [[s0012-cli-list-named-views]] §§ 4–5
  (resolution chain), [[s0015-cli-schema-derived-filter-flags]]
  (existing `list` flags). The new `--layout` flag plugs into the
  same parser without colliding with reserved flag names.
- **Prior art (read, don't copy)** —
  `~/workspace/os/open-station/src/openstation/tasks.py:263–293`
  (`group_tasks_for_display`) and
  `~/workspace/os/open-station/src/openstation/ui.py:65–166`
  (`rich_task_table`, `_rich_task_table_custom`). The two-step
  algorithm — flatten-with-depth then render-with-prefix — is
  the pattern this spec lifts; the data shapes and module
  placement are this spec's call.

## 2. Goals and Non-Goals

### 2.1 Goals

1. **Hierarchy visible by default.** `art ls --kind task` on the
   artifacts-os vault renders `t0042` indented under `t0036`,
   and `t0043`–`t0046` indented under `t0041`, with no flag and
   no settings change.
2. **One abstraction, two members.** `views/` exposes a
   `Layout` concept that admits exactly two concrete members in
   v1 (`table`, `tree`) and stays open for a future third without
   redesign. No third layout is built.
3. **Generic over kinds.** The renderer is **not** hardcoded to
   `parent`. Any kind that declares an upward-pointer field via
   `x-layouts.tree.parent_field` becomes hierarchical; kinds that
   do not stay flat.
4. **No regression on `-q`, `-j`, `--fields`.** Quiet and JSON
   output are unchanged. `--fields` keeps its existing semantics
   for non-hierarchical kinds and gains a documented (small)
   meaning under tree layout.
5. **Settings-layer compatibility.** `ViewConfig` /
   `ViewsConfig` saved queries continue to work; layout is a
   new optional dimension that does not collide with existing
   keys.
6. **Migration cost = 0 for existing kind files.** `x-columns`
   stays. Layouts are an additive `x-layouts` block.

### 2.2 Non-Goals (held the line per n0002 Risk #3)

- A second concrete layout beyond tree (board, timeline, card,
  matrix). The abstraction earns its keep with one new user; we
  refuse to design four to "validate the shape".
- TUI integration. `tui/` is a stub today.
- Hierarchical `art show` (rendering an artifact with its
  subtree underneath). Separate concern; out of scope here.
- Layouts driven by `depends_on` or any non-tree relationship.
  Tree-of-parents only in v1.
- Multi-source traversal (parent + depends_on combined). v1
  supports parent-style only; the schema in §3 is forward-compat
  for a second source but does not implement one.

## 3. Configuration Surface — `artifacts.yaml`

### 3.1 Where layout config lives — single home

**Layout configuration lives in `artifacts.yaml`, only.** The
kind JSON describes the data shape (frontmatter properties,
`x-dir`, `x-prefix`, `x-numbered`, `x-columns`,
`x-status-colors`); it does **not** declare layouts.

A vault that wants tree-by-default for `task` writes one block:

```yaml
# artifacts.yaml
default_layouts:
  task:
    layout: tree
    parent_field: parent
```

That is the complete declaration. No kind file changes; no
registry changes; no `meta["layouts"]` channel.

### 3.2 The `default_layouts` map

`default_layouts` is a top-level key in `artifacts.yaml`,
parallel to the existing `default_views`. Each entry maps a
kind name to a **layout configuration object**.

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `layout` | string — `"table"` \| `"tree"` | yes | Layout name; must be in `views.LAYOUTS` |
| `parent_field` | string — frontmatter key name | required when `layout: tree`, forbidden otherwise | Field on the artifact's frontmatter whose value points up to its parent (wikilink string) |

A **string-form shorthand** is accepted for layouts that take
no configuration:

```yaml
default_layouts:
  task: table        # equivalent to: task: { layout: table }
  spec: table
```

The shorthand is rejected for layouts that require config
(today, `tree`):

```yaml
default_layouts:
  task: tree         # ValidationError — tree requires parent_field
```

This keeps simple cases simple and forces explicitness exactly
where it is needed.

### 3.3 Parent-field placement decision

`parent_field` lives in the layout config object — not on the
kind JSON, not in a separate `x-hierarchy` slot. The decision
log (§16) records the alternatives considered; the operative
argument:

- The user's pivot rejected layout config on the kind. A
  `parent_field` slot under any other kind-side key
  (`x-hierarchy.parent_field`, `x-tree.parent_field`,
  whatever name) recreates the coupling the user removed.
- `parent_field` is read by exactly one consumer: the tree
  layout. Other layouts neither produce nor consume it. That
  is the literal definition of layout configuration — config
  scoped to a layout's needs.
- Splitting it across kind JSON (data property: "this kind
  has a parent") and `artifacts.yaml` (presentation: "the
  tree layout walks the parent field") is two homes for one
  datum. Single home wins.

Trade-off accepted: a vault that switches between two tree-
configurable kinds repeats the parent-field name in two
`default_layouts` entries. The cost is one identifier per
kind. The clarity gain (one home, no kind-side residue)
is worth it.

### 3.4 Forward-compat — same arguments, different surface

The forward-compat properties from the pre-revision §3.2 carry
over with a renamed surface. The block is now a **YAML
mapping** under `default_layouts[<kind>]` (or under a saved
view — see §10) instead of a JSON object on the kind. The
extension shapes are identical.

#### Direction: up-pointer vs. down-pointer

```yaml
# v1 — declared
default_layouts:
  task: { layout: tree, parent_field: parent }

# Future — kind with no upward pointer (e.g. playlist→tracks)
default_layouts:
  playlist: { layout: tree, children_field: tracks }
```

Precedence rule (unchanged): when both `parent_field` and
`children_field` are declared on the same entry,
`parent_field` is the traversal source. Not implemented in
v1.

#### Second source (parent + depends_on)

A future multi-source design adds keys to the same object:

```yaml
default_layouts:
  task:
    layout: tree
    sources:
      - field: parent
      - field: depends_on
```

The single-string `parent_field` becomes a deprecated alias
for the one-source case.

#### Default layout name

A future board layout declares `layout: board` and the same
resolution chain (§8.2) selects it without code changes in
`cli/`.

### 3.5 Validation at settings load

`ViewsSettings.from_base` validates each `default_layouts`
entry at parse time. Three checks:

1. **Layout known.** `entry.layout` must be in `views.LAYOUTS`.
   Unknown → `ValueError("default_layouts[<kind>].layout =
   <name> is not a registered layout")`. Surfaced as exit 2 by
   the CLI.
2. **Required config present.** If `entry.layout == "tree"`,
   `entry.parent_field` must be a non-empty string. Otherwise →
   `ValueError("default_layouts[<kind>] declares layout 'tree'
   but has no parent_field")`.
3. **Spurious config rejected.** If `entry.layout == "table"`,
   `entry.parent_field` must be absent. Otherwise →
   `ValueError("default_layouts[<kind>].parent_field is set but
   layout is 'table'")`. (Cheap typo guard; mirrors the
   §3.3-old check that `x-layouts.tree` was forbidden when
   `default == "table"`.)

The kind-name key (`task`, `spec`, etc.) is **not validated**
against the registered kinds list at parse time. Reason: a
vault may declare a preference for a kind it does not yet
have without an error. Same discipline as `default_views`.

A typo on the kind name (e.g. `taks` instead of `task`) is
detected only when the user runs `art ls --kind taks` and
nothing matches — not at settings load. This is an accepted
ergonomic cost; the alternative is making `default_layouts`
fail-loud on every fresh vault before kinds are added.

### 3.6 Validation at use (parent_field × kind schema)

The kind-schema check (old §3.3 rule 3 — `parent_field` must
match a property in the kind's `properties` map) **moves** to
`render_tree`'s call site, not registry load. When the CLI
resolves `parent_field` for a tree render, the renderer reads
`item.frontmatter.get(parent_field)` per row. A
`parent_field` that does not exist on any artifact yields
empty values → every artifact appears as a root → flat
output. That is silent and not what the user wants.

Add a single guard in `cli/commands/list.py` immediately
after `resolve_parent_field` (see §8.2): if `kind_def is not
None` and `parent_field not in kind_def.schema_properties`,
raise `ValidationError("kind '<k>' has no property
'<parent_field>'; declared by default_layouts or view
config")`, exit 2.

The check requires `KindDef` to expose a property-name
accessor. The minimal addition is a `properties` attribute
already present in the parsed schema; if it is not currently
exposed on `KindDef`, adding it is a small migration step
recorded in §13.

This validation **is not in the renderer** — the renderer
stays kind-agnostic. The CLI is the only caller that has
both a kind schema and a layout choice in hand.

### 3.7 Concrete declaration for the artifacts-os vault

The vault's own `artifacts.yaml` gains:

```yaml
default_layouts:
  task:
    layout: tree
    parent_field: parent
```

That single block reproduces the pre-revision shipped
behaviour. No other kind needs an entry; the four other
kinds (`agent`, `note`, `research`, `spec`) fall through to
`table`.

## 4. Layout Abstraction

### 4.1 What a layout is

A **layout** is a function from `(items, columns, kind_def)` to
a Rich renderable, plus an optional layout-specific configuration
object read from `kind_def.meta["layouts"][<name>]`.

```python
# Conceptual shape — the public surface in §5 makes it concrete.
Layout = Callable[
    [list[ArtifactMeta], list[FieldSpec], KindDef | None],
    RenderableType,        # rich.console.RenderableType
]
```

Two members in v1:

| Layout | Configuration | Renderable |
|--------|---------------|------------|
| `table` | none | `rich.Table` |
| `tree`  | `{parent_field: str}` | `rich.Table` (rows pre-ordered, prefix applied to the first column — see §5) |

`tree` returns a `rich.Table`, not a `rich.Tree`. Rationale:
the existing column model (`FieldSpec`, status coloring,
`format_field`) is column-rich and would be lost in a switch
to `rich.Tree`'s "label-per-node" structure. The tree shape is
encoded as a prefix string in the row's first cell, identical
to the open-station prior art. A user who wanted pure
`rich.Tree`-style nesting would lose every other column — net
regression.

### 4.2 Coexistence — what `table` owns vs. what `tree` owns

| Concern | `table` owns | `tree` owns |
|---------|--------------|-------------|
| Column model (`FieldSpec`, format) | yes | inherits — same `parse_field_specs`, `format_field` |
| `KindDef.meta["columns"]` default | yes | inherits — `default_columns(kind_def)` |
| Status coloring (`status_colors`) | yes | inherits — applied per row |
| Row order | input order (then `_apply_sort`) | computed traversal (§6) |
| Prefix on a column | none | `└─` glyphs on the **first** column (§9) |
| Layout-specific config | none | `meta["layouts"]["tree"]` |

The boundary between layouts is **row ordering and the
optional prefix on one column**. Everything else is shared.
This is what makes the abstraction cheap: 90% of `render_table`
is reused; the new code is `compute_tree` (a pure ordering
pass) and a thin wrapper that injects the prefix.

### 4.3 Selecting the layout — settings default

A vault selects a per-kind default layout via
`default_layouts[kind]` in `artifacts.yaml` (§3.2). When the
key is absent, the default is `"table"`. The resolution chain
that lets a user override per-invocation is in §8.2.

(Pre-revision, this slot was on the kind JSON. See §0 and
§16 for the pivot.)

### 4.4 Extensibility argument — without designing a second new layout

The abstraction supports a hypothetical third layout (e.g.
`board`) by:

1. Registering a new entry in the layout registry exposed by
   `views.layouts.LAYOUTS` (§5.4).
2. Adding `"board"` to the recognized values of
   `meta["layouts"]["default"]` and `--layout`.
3. Optionally adding a `"board"` configuration block under
   `x-layouts` with whatever fields it needs.

No change is required in `cli/commands/list.py` resolution
chain code, in `views/render_table`, in `ViewConfig`, or in
`-q`/`-j`. The seam is the **layout registry** (§5.4); a
second new layout slots in there or it does not slot in at all.

We do not design `board` here. The argument above is sufficient
to demonstrate that a second new layout is one (well-named)
function and one (well-named) registry entry, **not** a
schema redesign.

## 5. Module Placement and Renderer Signatures

### 5.1 Decision — traversal lives in `views/`

Tree traversal is a **`views/` concern.** Core stays the flat
discovery + filter layer locked in [[s0014-core-unified-filter-api]].

**Module DAG argument.** The DAG today is `core → views → cli`
(per [[s0007-artifacts-os-views-module]] § "Scope Boundary" and
[[s0002-artifacts-os-architecture]]). Putting traversal in
`views/` keeps each module's contract intact:

- `core.list_artifacts` returns a flat `list[ArtifactMeta]` that
  honours filters. This is the **same shape `-q` and `-j` need.**
  If traversal lived in `core`, the discovery API would either
  return a tree-shaped object (forcing `-q`/`-j` to flatten
  again) or grow a parallel flat path (two APIs). Both are
  worse than the current state.
- `views` already owns presentation: row order is presentation,
  prefix glyphs are presentation, depth is a layout property. A
  pure renderer concern.
- `cli` selects a layout and passes flat data; it does not
  traverse.

**`-q` / `-j` argument.** Both modes consume the flat
`list[ArtifactMeta]` directly (`cli/commands/list.py:417–423`).
They **must remain layout-agnostic** — see §8.4 for the
normative carve-out. Keeping traversal in `views/` makes this
free: `-q`/`-j` simply do not call into `views/` at all.

**`--fields` argument.** `--fields` selects columns from
`FieldSpec`. Columns are a `views/` concept. A `views/` layout
that knows about columns can decide which column carries the
tree prefix (§9) without `core` ever being aware of "columns".

The cost of placing traversal in `views/` is small: the
renderer needs a parent-resolution helper that consults
wikilink-style strings. That helper is pure and does not
require a `Registry` — it operates on the in-memory list of
`ArtifactMeta` already passed in. See §6 for the algorithm.

### 5.2 Public surface added to `views/`

Three new symbols. All live in a new module
`src/artifacts_os/views/layouts/` with submodules `tree.py`,
`table.py`, and `__init__.py`. The public API extends s0007's
`Public API` block:

```python
from artifacts_os.views import (
    # ... existing exports unchanged ...
    Layout,              # type alias (Callable signature)
    LAYOUTS,             # dict[str, Layout] — registry
    render_tree,         # tree layout entry point
    compute_tree,        # pure helper: flatten-with-depth
)
```

`render_table` keeps its signature; it is registered as the
`"table"` entry in `LAYOUTS`. No existing caller of
`views.render_table` breaks.

### 5.3 `compute_tree` — pure helper

```python
def compute_tree(
    items: list[ArtifactMeta],
    *,
    parent_field: str,
    sort_key: Callable[[ArtifactMeta], object] | None = None,
) -> list[tuple[ArtifactMeta, int, TreeNote]]:
    """Order *items* parent-before-children; return (item, depth, note).

    *sort_key* sets sibling order. If None, falls back to id.
    *note* is one of TreeNote.NORMAL, TreeNote.ORPHAN_OUT_OF_SLICE,
    TreeNote.ORPHAN_MISSING, TreeNote.CYCLE_BREAK — see §6.
    """
```

The function is pure (no I/O, no Registry). It builds a
parent-name → child-list map using the wikilink resolution
rule defined in §6.1, runs an iterative depth-first traversal,
and returns the ordered list. Cycles are broken visibly per
§6.3.

`TreeNote` is an `Enum` exported as
`artifacts_os.views.TreeNote` and consumed by `render_tree`
to choose the row-level annotation in §6.4.

### 5.4 Layout registry

```python
# src/artifacts_os/views/layouts/__init__.py
LAYOUTS: dict[str, Layout] = {
    "table": render_table,
    "tree":  render_tree,
}
```

The CLI looks up the chosen layout name in `LAYOUTS` and
calls it. Unknown name → `ValidationError("unknown layout {n!r};
known: {sorted(LAYOUTS)}")`, exit 2.

### 5.5 `render_tree` signature

```python
def render_tree(
    items: list[ArtifactMeta],
    columns: list[FieldSpec],
    *,
    kind_def: KindDef | None = None,
    parent_field: str,                       # required, no default
    sort_key: Callable[[ArtifactMeta], object] | None = None,
    is_known_stem: Callable[[str], bool] | None = None,
) -> Table:
    """Render *items* as a tree-prefixed table.

    *parent_field* is required; the caller (CLI) resolves it
    from artifacts.yaml via the §8.2 chain and passes the result.
    The renderer does not consult kind_def for parent_field.
    """
```

Post-revision, `parent_field` is **required**; there is no
fallback to `kind_def.meta` because `meta["layouts"]` no
longer exists. The renderer is mechanism-agnostic — it
receives the resolved parent-field name from the CLI and
operates on the in-memory item list.

`kind_def` is still passed (kept for status_colors,
default_columns, and other `views/` consumers); it just
contributes nothing to layout resolution.

The `sort_key` parameter is the binding seam to
`--sort` / `view.sort` — see §6.2.

## 6. Traversal, Sibling Order, and Edge Cases

### 6.1 Parent reference resolution

A row's parent is the artifact whose **stem** equals the
unwrapped wikilink in the row's `parent_field`. The unwrap is
the existing `core.discover._unwrap_wikilink` helper (already
imported in `cli/commands/list.py:358`), promoted to a
**public** export of `core.discover` so `views/` may call it
without poking module-private symbols.

```python
# Pseudocode
def _resolve_parent(item, parent_field, by_stem):
    raw = item.frontmatter.get(parent_field)
    if not raw:
        return None, TreeNote.NORMAL          # this item is a root
    bare = unwrap_wikilink(str(raw))
    parent = by_stem.get(bare)
    if parent is None:
        return None, TreeNote.ORPHAN_OUT_OF_SLICE  # see §6.4
    return parent, TreeNote.NORMAL
```

The `by_stem` map is built once from the input list:
`{item.path.stem: item for item in items}`. Items not present
in the input list are unresolvable — they may be in another
kind, filtered out, or genuinely missing. §6.4 distinguishes
these cases.

### 6.2 Sibling order

**Default sibling order is by `id`.** Both top-level roots and
descendants sort by `id` ascending — the same order
open-station's `group_tasks_for_display` produces (sort by
`id` at every level). Justified: deterministic, predictable,
matches both intuitive "tree by creation order" and existing
flat-list behaviour for kinds with numeric IDs.

For non-numbered kinds (no `id` prefix), sibling order
falls back to `name` ascending (also deterministic).

**Interaction with `--sort` / `view.sort`.** When the user
passes `--sort <field>` (or a view declares `sort: <field>`),
the sort function is applied **at every level** of the tree,
parents and siblings independently. Tree shape is preserved —
parents always come before their children — but each cohort
of siblings sorts by the requested key. Roots sort by the
requested key as well.

```text
# Default order:               # --sort -created:
t0036 (parent)                 t0041 (newer parent)
  └─ t0042                       └─ t0046
t0041 (parent)                   └─ t0045
  └─ t0043                       └─ t0044
  └─ t0044                       └─ t0043
  └─ t0045                     t0036 (older parent)
  └─ t0046                       └─ t0042
```

Implementation: `_apply_sort` (today: `cli/commands/list.py:527–540`)
returns a sort function/key; that key is passed into
`compute_tree(sort_key=...)` rather than applied to a flat
list. The CLI no longer applies `_apply_sort` directly to the
output of `list_artifacts` when the active layout is `tree` —
the sort flows into `compute_tree`. For `table` layout, sort
behaves exactly as today.

`-q` and `-j` apply sort the same way they do today (flat
list, no tree). See §8.4.

### 6.3 Cycles — visible break

A vault is user-edited markdown; cycles are possible. The
renderer **detects cycles and breaks them visibly** (decision:
visible-break, not loud-fail and not silent-flatten).

Algorithm (depth-first, ancestor-set tracking):

```python
def _visit(node, ancestors, by_stem, parent_field):
    yield (node, len(ancestors), TreeNote.NORMAL)
    seen = ancestors | {node.path.stem}
    for child in _children(node, by_stem, parent_field):
        if child.path.stem in seen:
            yield (child, len(ancestors) + 1, TreeNote.CYCLE_BREAK)
            continue                       # break cycle here
        yield from _visit(child, seen, by_stem, parent_field)
```

When `TreeNote.CYCLE_BREAK` fires, `render_tree` emits the
row with a trailing annotation `↻ cycle` in the first column
and **does not descend further into that subtree from that
edge**. A single stderr warning is emitted per cycle:

```
warning: cycle detected on parent chain of <stem> (kind: <k>)
```

The warning goes to stderr so `-q`/`-j` consumers do not see
it interleaved with their data. The warning is emitted **at
most once per traversal**, deduped by the lowest-id member of
the cycle.

**Why visible-break (vs. loud-fail / silent-flatten):**

| Strategy | Cost | Fix-fit |
|----------|------|---------|
| Loud-fail (raise) | User cannot list at all until they fix the data; blocks every other unrelated work in the vault. | Punishes the user for one bad row. |
| Silent-flatten (drop the back-edge, no marker) | Bug invisible; user never learns the data is broken. | Hides the problem. |
| **Visible-break (chosen)** | One row gets a `↻` annotation; remaining rows render normally. | Surface the bug + keep the tool usable. |

Loud-fail was the architect-side preference per n0002, but
the cost-of-blockage is too high for a presentation-layer
issue. Visible-break preserves "user can fix without
re-running" while making the corruption obvious.

### 6.4 Roots, orphans, and missing parents — the four cases

`compute_tree` produces one of four `TreeNote` values per row.
`render_tree` translates each to a row-level annotation. All
four cases keep the row visible.

| Case | TreeNote | Condition | Rendered as |
|------|----------|-----------|-------------|
| **A. Root** | `NORMAL` (depth 0) | Item has no `parent_field` value, or value is empty | Top-level row, no prefix |
| **B. Orphan — parent outside slice** | `ORPHAN_OUT_OF_SLICE` | `parent_field` resolves but parent is not in the input list (filtered out, in another kind) | Top-level row, prefix `↑` annotation: `t0042  ↑[parent: t0036]` |
| **C. Orphan — missing parent** | `ORPHAN_MISSING` | `parent_field` is set but does not resolve to any artifact in the input list, **and** also not present in the registry as a stem | Top-level row, prefix `?` annotation: `t0042  ?[parent: t0036]` |
| **D. Cycle break** | `CYCLE_BREAK` | Re-encountered an ancestor (§6.3) | Indented row, prefix `↻ cycle` annotation |

Cases B and C are operationally distinguished by a registry
lookup. The renderer is given access to a callable that returns
True if a stem is registered anywhere in the vault (not just
the input slice):

```python
def render_tree(
    items, columns, *,
    kind_def=None, parent_field=None, sort_key=None,
    is_known_stem: Callable[[str], bool] | None = None,
) -> Table:
    ...
```

The CLI binds `is_known_stem` from `Registry.exists_stem(stem)`
(a thin wrapper to add) when constructing the call. When the
caller does not pass `is_known_stem` (programmatic use without a
registry), B and C **collapse to a single annotation**:
`?[parent: <ref>]`. This is acceptable degraded behaviour —
the rendering remains correct, only the diagnostic becomes
less precise.

#### Worked examples

Vault with `parent` field on tasks:

```text
t0036 (no parent)                — Case A
  ├─ t0042 (parent: [[t0036]])    — Case A child of A
t0041 (no parent)                — Case A
  ├─ t0043 (parent: [[t0041]])
  ├─ t0044 (parent: [[t0041]])
  ├─ t0045 (parent: [[t0041]])
  └─ t0046 (parent: [[t0041]])
```

Same vault with `--status ready` filter that hides `t0036`:

```text
t0042  ↑[parent: t0036]          — Case B (parent filtered out)
t0041
  ├─ t0043
  ├─ t0044
  ├─ t0045
  └─ t0046
```

Same vault with `t0050` declaring `parent: [[t9999]]` (no
such file):

```text
t0036
  └─ t0042
t0041
  ├─ t0043
  ├─ t0044
  ├─ t0045
  └─ t0046
t0050  ?[parent: t9999]          — Case C (no such artifact)
```

Vault with cycle: `t0060.parent = [[t0061]]` and
`t0061.parent = [[t0060]]`:

```text
t0060
  └─ t0061
       └─ t0060  ↻ cycle         — Case D, traversal stops
```

stderr: `warning: cycle detected on parent chain of t0060 (kind: task)`.

### 6.5 The verification-target rendering

Per the task brief, `art ls --kind task` on the artifacts-os
vault must produce a tree with:

- `t0042` indented under `t0036`
- `t0043`–`t0046` indented under `t0041`

This is a Case A + Case A example with default settings. No
filters, no `--sort`, no flag, no view. Both rows of every
sibling pair render in `id` order.

## 7. Filtered Slices — `--status` Hides a Parent

When a filter (`--status ready`, `--filter assignee=alice`,
positional refs, etc.) hides a parent but keeps a child, the
renderer **promotes the child to root with a Case B
annotation** (§6.4).

**Decision rationale:**

| Strategy | Why rejected / chosen |
|----------|------------------------|
| Render a placeholder for the hidden parent | Leaks data outside the filter — user asked "show me ready tasks", we silently surface a non-ready one. Cuts against the principle that the filter is the user's truth. |
| Fall back to flat | Users notice the layout flickering between tree and flat as filters change. Inconsistent. Loses hierarchy on every non-trivial filter. |
| **Promote to root with Case B annotation (chosen)** | Honours the filter (no hidden-parent leakage); preserves the layout (still tree-shaped); makes the gap visible (`↑[parent: t0036]`); is consistent with §6.4 Case B for "parent is in another kind". |

The annotation depends on whether the hidden parent is
**in the registry** (Case B → `↑`) or **not in the registry**
(Case C → `?`). A filtered-out parent is always Case B because
it does exist in the registry.

**Worked example.** Same vault as §6.4, `art ls --kind task
--status ready` where `t0036` has `status: done` (so the
filter hides it):

```text
t0042  ↑[parent: t0036]
t0041
  ├─ t0043
  ├─ t0044
  ├─ t0045
  └─ t0046
```

`t0042` is preserved (status: ready) with a visible breadcrumb
to its hidden parent. The user can issue
`art ls --kind task t0036` to see the parent without
backing out their filter.

## 8. CLI Surface

### 8.1 New flag — `--layout`

```text
artifacts list [--kind KIND] [--status STATUS] [--filter K=V]...
               [--view NAME] [--fields FIELDS] [--layout NAME] [-q | -j]
```

| Property | Value |
|----------|-------|
| Long form | `--layout` |
| Short form | none (intentionally — see §8.7) |
| Choices | `table`, `tree` (in v1; the parser reads from `LAYOUTS.keys()` so future layouts auto-register) |
| Default | `None` (sentinel — falls through resolution chain in §8.2) |
| Help | `presentation layout for the result; auto-detects from kind when omitted` |

Adding `--layout` to the reserved-flag set in `_RESERVED_FILTER_FLAG_NAMES`
(`cli/commands/list.py:24–27`) prevents a future kind property
named `layout` from colliding.

### 8.2 Resolution chain — explicit > view > settings default > implicit

**Four rungs**, top wins. The pre-revision fifth rung (`kind_def
.meta["layouts"]["default"]`) is removed:

1. **Explicit `--layout NAME`** — user intent, last-mile.
2. **View config** — `view_cfg.layout` (an optional field on
   `ViewConfig`; see §10.1). Set when the user is using a saved
   view that pins a layout.
3. **`default_layouts[kind]` settings map** — kind-scoped user
   preference under `default_layouts:` in `artifacts.yaml` (see
   §10.2 / §3.2).
4. **Implicit** — `"table"`. Every kind without any of the
   above ends up as table. The v1 default for every kind except
   `task` (which the vault declares via §3.7).

Layout-name resolution is implemented in a single helper:

```python
def resolve_layout(
    args: Any,
    view_cfg: ViewConfig | None,
    settings: ViewsSettings | None,
    kind_def: KindDef | None,
) -> str:
    if getattr(args, "layout", None):
        return args.layout
    if view_cfg is not None and getattr(view_cfg, "layout", None):
        return view_cfg.layout
    if settings is not None and settings.views is not None:
        m = settings.views.default_layouts                       # see §10.2
        if kind_def is not None and kind_def.name in m:
            return m[kind_def.name].layout                        # entry is a LayoutConfig
    return "table"
```

`kind_def` is still passed in (the helper signature is
preserved for compatibility with existing call sites and
because validation in §3.6 needs it) — it just no longer
contributes a layer to the chain.

Validation: the resolved name must be in `views.LAYOUTS`. If
not, raise `ValidationError`; exit 2.

#### Parent-field resolution — sibling chain

When the resolved layout is `tree`, `parent_field` is resolved
through a parallel chain consulting the same slots, so a user
who passes `--layout tree` ad-hoc can still draw a tree:

1. **View config** — `view_cfg.parent_field`.
2. **`default_layouts[kind].parent_field`** — even if that
   entry's `layout` differs from the resolved layout. Reason:
   the user may have set `default_layouts.task: { layout: table,
   parent_field: parent }` to declare "this kind is a tree but
   I want flat by default", then run `art ls --kind task
   --layout tree` to see the tree this once. The
   `parent_field` is reusable because it is a property of the
   data, not of the chosen render.
3. **None** — if neither slot supplies one,
   `ValidationError("layout 'tree' requires parent_field;
   declare it in artifacts.yaml under default_layouts[<kind>]
   or a view config")`, exit 2.

There is no `--parent-field` CLI flag in v1. A user who needs
ad-hoc tree on a kind without configured `parent_field` is one
edit to `artifacts.yaml` away. (A future `--parent-field` flag
slots in trivially as rung 0 if user research justifies it;
not designed here.)

```python
def resolve_parent_field(
    view_cfg: ViewConfig | None,
    settings: ViewsSettings | None,
    kind_def: KindDef | None,
) -> str | None:
    if view_cfg is not None and getattr(view_cfg, "parent_field", None):
        return view_cfg.parent_field
    if settings is not None and settings.views is not None:
        m = settings.views.default_layouts
        if kind_def is not None and kind_def.name in m:
            pf = m[kind_def.name].parent_field
            if pf:
                return pf
    return None
```

Then in `run()`: `if layout == "tree": pf = resolve_parent_field(...);
if pf is None: raise ValidationError(...)`.

#### Property-existence check

After resolving `parent_field`, the CLI verifies it matches
a property in `kind_def.schema_properties` (§3.6). This catches
typos in `artifacts.yaml` at use time.

### 8.3 Opt-out — flat output on a hierarchical kind

The user opts out by:

```bash
art ls --kind task --layout table
```

Or, for a per-vault preference:

```yaml
# artifacts.yaml
default_layouts:
  task: table         # string-form shorthand; equivalent to { layout: table }
```

The first is a one-shot; the second is durable.

A view can pin layout:

```yaml
views:
  active:
    columns: id,name,assignee,status
    filters: { status: in-progress }
    layout: table
```

`art ls --view active --kind task` then renders flat.

To opt **into** tree on a vault that previously declared
`default_layouts.task: table`, the user passes `--layout tree`
once — or edits `artifacts.yaml` to use the object form with
`parent_field`.

### 8.4 `-q` and `-j` carve-outs — unchanged

`-q` and `-j` short-circuit before any layout selection, exactly
as today. `-q` walks `items` and prints `item.path.stem` per
line; `-j` dumps `[item.frontmatter for item in items]` as JSON.
Neither calls into `views/` at all.

**Sort still applies** (so `-q` and `-j` see filtered + sorted
flat data), but tree depth and prefixes do not — those are
presentation only. This is the literal current behaviour;
no code changes in the `-q`/`-j` branches of `run()`.

The `--layout` flag is silently ignored when combined with
`-q` or `-j` (no warning, no error). Justification: scripted
callers may pass `--layout tree -j` while iterating fixtures;
making the combination an error costs them and gains the user
nothing. The flag was a no-op anyway.

### 8.5 Resolution-chain test matrix

The kind-default rung is removed; the matrix shrinks
correspondingly. The CLI integration tests (per §13) cover
these rows:

| settings `default_layouts[task]` | view `layout` | flag `--layout` | Effective layout | Effective parent_field |
|----------------------------------|---------------|-----------------|------------------|------------------------|
| (absent) | (absent) | (absent) | `table` | n/a |
| `{layout: tree, parent_field: parent}` | (absent) | (absent) | `tree` | `parent` |
| `{layout: tree, parent_field: parent}` | (absent) | `table` | `table` | n/a |
| `{layout: tree, parent_field: parent}` | `table` (view) | (absent) | `table` | n/a |
| `{layout: tree, parent_field: parent}` | `table` (view) | `tree` | `tree` | `parent` (rung 2 in §8.2 sibling chain) |
| `table` (string-form) | (absent) | (absent) | `table` | n/a |
| `table` (string-form) | `{layout: tree, parent_field: parent}` (view) | (absent) | `tree` | `parent` |
| (absent) | (absent) | `tree` | exit 2 — "layout 'tree' requires parent_field" |
| (absent) | (absent) | `nope` | exit 2 — "unknown layout 'nope'" |
| `{layout: tree}` (no parent_field) | n/a | n/a | exit 2 at settings parse — "default_layouts[task] declares layout 'tree' but has no parent_field" |
| `{layout: table, parent_field: parent}` | n/a | n/a | exit 2 at settings parse — "parent_field is set but layout is 'table'" |

### 8.6 Help text

`art ls --help` lists `--layout` immediately after `--fields`.
Help string: `presentation layout for the result; auto-detects
from kind when omitted (e.g. tasks render as a tree by default)`.

### 8.7 Why no short form

`-l` is the natural short form but it is an extremely
common alias for `list` itself, and `art ls -l` would read as
"list, list" — confusing. We refuse to burn it on this flag.
The flag is opt-out-flavoured; users who set the kind default
they want do not type it. Keeping it long-form-only signals
"infrequent use".

## 9. `--fields` Interaction Under Tree Layout

### 9.1 Same parser, same semantics

`--fields` parses identically under both layouts (shared
`parse_field_specs`). The resolved column list is the same.

### 9.2 Tree prefix attaches to the first column

When the active layout is `tree`, the tree-drawing prefix
(spaces + `└─`) is prepended to the **first column** of the
resolved field list — whatever column that is. The prefix is
applied *after* `format_field` runs, so it does not interfere
with date formatting or status coloring.

```bash
# default columns: id,name,status,assignee
# prefix attaches to "id":
t0036
  └─ t0042

# explicit fields: --fields name,status
# prefix attaches to "name":
spec-tree-layout-for-art
  └─ work-on-edge-cases
```

The first-column choice is intentional — it is the column the
user reads first, and id-or-name conventions match. We do not
add a `tree_column` config in v1; if a kind needs the prefix
on a non-first column, that is a v2 concern and a single new
`x-layouts.tree.prefix_column: <name>` field would handle it
without breaking the v1 contract.

### 9.3 Annotations

Case B/C/D annotations (§6.4) are *suffixes* on the same first
column, after the prefix and after the formatted value:

```
<prefix><formatted-value>  <annotation>
```

This keeps the annotation visually attached to the row identifier.

### 9.4 Non-hierarchical kinds — no behaviour change

A kind without `x-layouts` or with `x-layouts.default = "table"`
sees no change: `--fields` selects columns, `render_table`
draws the table. The t0036-family `--fields` workflow is
preserved exactly.

The implementation guard: the CLI calls
`render_table(items, columns, kind_def=...)` for `table` and
`render_tree(items, columns, kind_def=..., parent_field=...)`
for `tree`. The `--fields` resolution code path
(`_resolve_columns` at `cli/commands/list.py:543–556`) is
unchanged.

## 10. Settings Layer — `ViewConfig`, `ViewsConfig`, `default_layouts`

### 10.1 `ViewConfig` — add `layout` and `parent_field`

```python
@dataclass
class ViewConfig:
    columns: str
    filters: dict[str, Any] = field(default_factory=dict)
    sort: str | None = None
    layout: str | None = None             # None means "fall through"
    parent_field: str | None = None       # required when layout: tree
```

YAML:

```yaml
views:
  active-tree:
    columns: id,name,assignee,status
    filters: { status: in-progress }
    layout: tree
    parent_field: parent           # required because layout: tree

  active-flat:
    columns: id,name,assignee,status
    filters: { status: in-progress }
    layout: table
```

Validation at `_parse_view`:

| Condition | Outcome |
|-----------|---------|
| `layout` set but not in `views.LAYOUTS` | `ValueError("view 'layout' = <name> is not a registered layout")` |
| `layout: tree` and `parent_field` absent or empty | `ValueError("view declares layout 'tree' but has no parent_field")` |
| `layout: table` (or any non-tree) and `parent_field` set | `ValueError("view 'parent_field' is set but layout is not 'tree'")` |

`layout` is **optional** — every existing view file keeps
working unchanged. None means "fall through to the
`default_layouts` / implicit chain" per §8.2.

### 10.2 `ViewsConfig` — `default_layouts: dict[str, LayoutConfig]`

Symmetric to the existing `default_views: dict[str, str]`
(s0007 § "Settings YAML Schema"). Maps kind name to a
**`LayoutConfig`** dataclass, not a bare string. The string-
form shorthand from §3.2 is parsed into a `LayoutConfig` at
load time.

```python
@dataclass(frozen=True)
class LayoutConfig:
    layout: str                              # in views.LAYOUTS
    parent_field: str | None = None          # required when layout: tree

@dataclass
class ViewsConfig:
    views: dict[str, ViewConfig]
    default_views: dict[str, str]
    default_layouts: dict[str, LayoutConfig]   # CHANGED — was dict[str, str]
```

YAML (full vocabulary):

```yaml
default_views:
  session: sessions

default_layouts:
  task:
    layout: tree
    parent_field: parent
  spec: table             # string-form shorthand → LayoutConfig(layout="table")
  research: table
```

Parse-time validation per §3.5:

```python
def _parse_default_layouts(raw: object) -> dict[str, LayoutConfig]:
    if not isinstance(raw, dict):
        raise ValueError("default_layouts must be a mapping")
    out: dict[str, LayoutConfig] = {}
    for kind_name, entry in raw.items():
        if isinstance(entry, str):
            entry = {"layout": entry}
        if not isinstance(entry, dict):
            raise ValueError(
                f"default_layouts[{kind_name!r}] must be a string or mapping"
            )
        layout = entry.get("layout")
        if not isinstance(layout, str) or layout not in LAYOUTS:
            raise ValueError(
                f"default_layouts[{kind_name!r}].layout = {layout!r}"
                f" is not a registered layout; known: {sorted(LAYOUTS)}"
            )
        parent_field = entry.get("parent_field")
        if layout == "tree" and not parent_field:
            raise ValueError(
                f"default_layouts[{kind_name!r}] declares layout 'tree'"
                " but has no parent_field"
            )
        if layout != "tree" and parent_field is not None:
            raise ValueError(
                f"default_layouts[{kind_name!r}].parent_field is set but"
                f" layout is {layout!r}"
            )
        out[kind_name] = LayoutConfig(layout=layout, parent_field=parent_field)
    return out
```

The kind-name key is intentionally unvalidated against the
registry (see §3.5).

### 10.3 Vocabulary-collision risk — addressed

The pre-revision argument carries over verbatim. `views` is
the module name and configuration namespace; `layout` is a
field within a view; `default_layouts` is a sibling top-level
key parallel to `default_views`. No collision.

`parent_field` is a field on `ViewConfig` and `LayoutConfig`;
it does not appear at top level and does not collide with any
existing settings key.

### 10.4 `ViewsSettings.from_base` updates

`from_base` (in `views/models.py:42–68`) parses
`base.raw["default_layouts"]` via `_parse_default_layouts`
above. `_parse_view` is extended to read `layout` and
`parent_field` together:

```python
def _parse_view(d: dict) -> ViewConfig:
    if "columns" not in d:
        raise ValueError("view entry missing required 'columns' field")
    layout = d.get("layout")
    parent_field = d.get("parent_field")
    if layout is not None and layout not in LAYOUTS:
        raise ValueError(f"view 'layout' = {layout!r} is not a registered layout")
    if layout == "tree" and not parent_field:
        raise ValueError("view declares layout 'tree' but has no parent_field")
    if layout != "tree" and parent_field is not None:
        raise ValueError(
            f"view 'parent_field' is set but layout is {layout!r} (not 'tree')"
        )
    return ViewConfig(
        columns=d["columns"],
        filters=dict(d.get("filters") or {}),
        sort=d.get("sort"),
        layout=layout,
        parent_field=parent_field,
    )
```

The layout-validation in both helpers reads from
`views.layouts.LAYOUTS`. The circular-import workaround
already in place (`from artifacts_os.views.layouts import
LAYOUTS` inside the function body) is preserved.

## 11. Kind-File Compatibility Path

### 11.1 Decision — `x-columns` preserved; `x-layouts` deleted

Two orthogonal kind-file decisions, one for each block that
the original spec touched:

| Block | Disposition | Where it lives now |
|-------|-------------|--------------------|
| `x-columns` | **preserved unchanged** | kind JSON; parsed into `meta["columns"]` |
| `x-layouts` | **deleted entirely** | configuration moves to `artifacts.yaml` (§3) |

No new kind-side block (e.g. `x-hierarchy`, `x-tree`) replaces
`x-layouts`. The `parent_field` datum that lived under
`x-layouts.tree.parent_field` is **not** retained on the kind;
it moves to the layout config in `artifacts.yaml`. See §3.3
for the rationale.

### 11.2 Rationale — column model is layout-independent (unchanged)

`x-columns` lists the column projection the user reads; that
projection is independent of the layout that draws it. The
same `["id", "name", "status", "assignee"]` works for the
table layout and for the tree layout — only the renderer
changes.

The argument for keeping `x-columns` kind-side is unchanged
from the original spec; the user pivot was specifically about
*layout* configuration, and columns are a property of the data
projection, not of the chosen render. (Compare: `parent_field`
is consumed only by tree, so it is layout-coupled and moves
with the layout.)

### 11.3 Why not a narrower `x-hierarchy` block

An alternative considered: keep a slim `x-hierarchy.parent_field`
on the kind, distinct from any layout name, on the rationale
that "this kind has a parent pointer" is a structural property
of the data. Rejected:

- The user pivot was explicit: layout config does not live on
  the kind. `x-hierarchy` is layout config under a different
  name; the only layout that consumes `parent_field` is the
  tree layout.
- Splitting `parent_field` (kind-side) from `layout: tree`
  (settings-side) creates two homes for one tightly coupled
  pair. Settings users have to look in two files; vault
  authors have to remember to update both when adding a new
  hierarchical kind.
- A second hierarchical kind (today, none; tomorrow, perhaps
  `playlist` with a `tracks` field) is one `default_layouts`
  entry away — same friction as `x-hierarchy` but in one file.

### 11.4 Backward-compatibility statement

This revision is **breaking against the as-shipped v1**. Three
edges break:

1. `x-layouts` on `kind.json` is no longer parsed. A vault
   that wrote one to a custom kind silently loses the
   configuration — nothing reads it.
2. `KindDef.meta["layouts"]` is removed. Any caller that
   reads it breaks. (In v1, the only consumer was
   `cli/commands/list.py`'s `resolve_layout`, which is being
   rewritten in this revision; no other consumers existed.)
3. `render_tree(parent_field=None)` no longer falls back to
   `kind_def.meta` — `parent_field` becomes a required keyword
   argument. Callers that relied on the fallback get a
   `TypeError` (good fail-loud; the migration is one keyword).

**Downstream-user posture.** No artifacts-os user has
`x-layouts` on a custom kind in production (the original
shipped on 2026-05-06 and is being revised the same day).
The migration any downstream user would need:

```diff
  // artifacts/kinds/<my-kind>.json
- "x-layouts": {
-   "default": "tree",
-   "tree": { "parent_field": "parent" }
- }

  # artifacts.yaml
+ default_layouts:
+   <my-kind>:
+     layout: tree
+     parent_field: parent
```

### 11.5 Rollback story

If `default_layouts` ever needs to be redesigned, removing
the block from `artifacts.yaml` reverts every kind to flat
table — same single-file scope as the migration "in". The
kind JSON is untouched throughout.

## 12. Out-of-Scope (verbatim from n0002 § "Out of scope")

This list is preserved literally for traceability. The architect
does not relax any of these in v1.

- **TUI integration.**
- **A second concrete layout beyond tree (board, timeline,
  card, etc.).**
- **Hierarchical `art show`** (rendering an artifact with its
  subtree underneath). Separate concern.
- **Layouts driven by `depends_on`.** Tree-of-parents only for
  now.

## 13. Migration Plan — As-Shipped Work

This revision lands after t0115, t0116, t0117 are `done` and
t0118 is `rejected`. The PM uses this section verbatim to
queue the next round of implementation tasks. Each block lists
**what to revert**, **what to add**, and **expected diff scope**.

### 13.1 Revert kind schema (touch t0115)

**Files affected:**

| Path | Change |
|------|--------|
| `artifacts/kinds/task.json` | Remove the `x-layouts` block. `x-columns`, `x-status-colors`, and properties stay byte-unchanged. |
| `src/artifacts_os/core/registry.py` | Remove `_KNOWN_LAYOUTS`, `_validate_and_parse_layouts`, the call site in `_load_vault_kinds` that populates `meta["layouts"]`. |
| `tests/core/test_registry.py` | Remove the 8 tests added by t0115 (valid parse, absent block, unknown default, missing tree block, parent_field absent, parent_field wrong type, table-default-without-tree, non-object x-layouts). The 12 pre-existing registry tests stay. |

**Add:** `KindDef.schema_properties` accessor (§3.6). The
parser already retains the kind JSON `properties` map; expose
it on `KindDef` as `set[str]` of property names. One small
field; no validation at registry load (the property-existence
check moves to `cli/commands/list.py`, §8.2).

**Test scope:** existing 12 registry tests still pass; one
new test confirms `kd.schema_properties` returns the expected
set for `task.json`.

**Cut as:** *one task*, type `implementation`, assignee
`developer`. Title: `revert-x-layouts-from-kind-schema`.

### 13.2 Renderer touch-up (touch t0116)

**Files affected:**

| Path | Change |
|------|--------|
| `src/artifacts_os/views/layouts/tree.py` | `render_tree`: change `parent_field: str \| None = None` to `parent_field: str` (required, no default). Remove the `if resolved_parent_field is None and kind_def is not None: ...` fallback block (today: roughly lines 174–183). The `kind_def` parameter stays — it carries `status_colors` for the underlying table render. |
| `tests/views/...` | Update any `render_tree(...)` test call sites that omitted `parent_field` (relied on the kind_def fallback). The 44 tests added by t0116 should be reviewed; the cases that exercised the fallback either pivot to passing `parent_field` explicitly or become tests of the new "missing parent_field" surface (now a TypeError from missing kwarg, not a ValidationError from the fallback). |

`compute_tree`, `TreeNote`, the `LAYOUTS` registry,
`Registry.exists_stem`, `unwrap_wikilink`, and the algorithm
in §6 are **unchanged**. The renderer remains
mechanism-agnostic.

**Cut as:** *one task*, type `implementation`, assignee
`developer`. Sequence: independent of 13.1, can run in
parallel. Title: `make-render-tree-parent-field-required`.

### 13.3 Settings model — `LayoutConfig` and `parent_field` on views (new)

**Files affected:**

| Path | Change |
|------|--------|
| `src/artifacts_os/views/models.py` | Add `LayoutConfig` dataclass per §10.2. Change `ViewsConfig.default_layouts` from `dict[str, str]` to `dict[str, LayoutConfig]`. Add `parent_field: str \| None = None` to `ViewConfig`. Replace inline `default_layouts` validation with `_parse_default_layouts` (§10.2). Extend `_parse_view` to read and validate `parent_field` per §10.4. |
| `tests/views/test_models.py` (or wherever models tests live) | Add tests for the parse-time validation matrix: string-form vs object-form `default_layouts`; tree without parent_field; non-tree with parent_field; unknown layout name; both `view.layout` and `view.parent_field` paired correctly and incorrectly. |

**Sequence:** independent of 13.1 and 13.2. 13.4 (CLI)
depends on this landing — it consumes `LayoutConfig.parent_field`.

**Cut as:** *one task*, type `implementation`, assignee
`developer`. Title: `extend-views-models-for-layout-config`.

### 13.4 CLI wiring rework (touch t0117)

**Files affected:**

| Path | Change |
|------|--------|
| `src/artifacts_os/cli/commands/list.py` | `resolve_layout`: drop the `kind_def.meta.get("layouts", ...)` rung (today: lines 360–361). Add `resolve_parent_field` helper per §8.2 sibling chain. In `run()`: after `resolve_layout` returns, if layout == "tree" call `resolve_parent_field`, ValidationError if None, then verify `parent_field in kind_def.schema_properties` (§3.6). Pass the resolved `parent_field` to `render_tree`. |
| `src/artifacts_os/cli/commands/list.py` (reserved set) | `_RESERVED_FILTER_FLAG_NAMES` keeps `"layout"`. No change required; included for completeness. |
| `tests/cli/test_list_layout.py` | Update `TestResolveLayout` to match the §8.5 matrix (drop kind-default rows, add `LayoutConfig` rows). Add `TestResolveParentField`. Update integration tests that asserted "tree by default on `task` because `x-layouts` declares it" to instead set `default_layouts.task = LayoutConfig(layout="tree", parent_field="parent")` in the test vault's `artifacts.yaml`. |

**Add tests for:** ValidationError on `--layout tree` without
parent_field; ValidationError when parent_field doesn't match
a property in the kind schema (`docs/settings.md` typo guard);
parent-field reuse across `default_layouts` and view config.

**Cut as:** *one task*, type `implementation`, assignee
`developer`, **depends_on** 13.1 (`KindDef.schema_properties`),
13.2 (`render_tree` signature), 13.3 (`LayoutConfig`). Title:
`rewire-cli-resolve-layout-for-settings-only`.

### 13.5 Vault-config migration

**Files affected:**

| Path | Change |
|------|--------|
| `artifacts/artifacts.yaml` | Add a `default_layouts:` block per §3.7: `task: { layout: tree, parent_field: parent }`. |

This is the single-line change that preserves the §6.5
verification target after the kind-side block is removed.

**Sequence:** must land **with or before** 13.4 (otherwise
`art ls --kind task` flips from tree to table on this vault
between 13.1 landing and 13.4 landing). Recommended:
**bundle into 13.4's diff** — adding the `artifacts.yaml`
block and wiring the CLI to read it ship together so the
behaviour is contiguous.

### 13.6 Documentation respec (re-cut t0118)

t0118 was rejected because it documented the pre-revision
design. Re-cut after 13.4 lands. Per-file scope:

| Path | Scope |
|------|-------|
| `docs/settings.md` | New "Layout selection" subsection. Document `default_layouts` (string-form and object-form, parent_field requirement for tree), `view.layout` + `view.parent_field`. Worked examples: vault wants flat tasks (`default_layouts.task: table`); vault wants tree tasks (`default_layouts.task: { layout: tree, parent_field: parent }`). Resolution-chain summary (4 rungs per §8.2) including the parent-field sibling chain. Link to `s0022-tree-layout` once. |
| `docs/adding-a-kind.md` | **Remove** the `x-layouts` section that t0118 added. Replace with a one-paragraph note: "Layout configuration lives in `artifacts.yaml`, not `kind.json`. See [docs/settings.md](settings.md#layout-selection)." Remove `x-layouts` from the kind.json reference table. |
| `src/artifacts_os/views/README.md` | Keep the `Layout`, `LAYOUTS`, `render_tree`, `compute_tree`, `TreeNote` API descriptions. **Remove** the `"layouts"` row from the `KindDef.meta` convention table (it no longer exists). Update settings extension subsection: `view.layout`, `view.parent_field`, `default_layouts: dict[str, LayoutConfig]`. Link to `s0022-tree-layout` once. |
| `src/artifacts_os/cli/README.md` | Keep `--layout` in the flag table. Rewrite the resolution-chain section (4 rungs, not 5). Add the parent-field sibling chain. Worked example: pivot the "default tree on tasks" source from `x-layouts` to `default_layouts.task` in `artifacts.yaml`. Remove every reference to kind-side layout config. |
| `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` | One-paragraph adjustment: "Tree layout for tasks is configured in `artifacts.yaml`'s `default_layouts`. Override per-invocation with `--layout table`. `-q` / `-j` are unaffected." |

Cross-link consistency: every doc that mentions the new
behaviour links to `s0022-tree-layout` exactly once. Spec
internals (algorithm, cycle policy) defer to §6 / §8 as
before.

**Cut as:** *one task*, type `documentation`, assignee
`author`. Title: `document-tree-layout-revised`. Depends on
13.4.

### 13.7 End-to-end verification (re-run t0119)

Verification target unchanged: `art ls --kind task` on this
vault renders `t0042` under `t0036` and `t0043`–`t0046`
under `t0041`. The configuration mechanism that produces
that shape is now §3.7 (`artifacts.yaml`), not the kind
file.

Add to the verification matrix:

- `art ls --kind task --layout table` → flat output (existing).
- Removing the `default_layouts.task` block from
  `artifacts.yaml` and re-running `art ls --kind task` →
  flat output (the new opt-out path; replaces "remove
  `x-layouts`" from the original test).
- Setting `default_layouts: { task: tree }` (object form,
  no `parent_field`) → exit 2 at settings load with the
  parent_field error per §3.5 rule 2.

**Cut as:** *one task*, type `feature` verification (parent:
t0114), assignee `user`. Title: `verify-tree-layout-revised`.

### 13.8 Sequencing summary

```
13.1 (revert kind schema)   ─┐
13.2 (renderer touch-up)    ─┼─→ 13.4 (CLI wiring + 13.5 vault config) ─→ 13.6 (docs) ─→ 13.7 (verify)
13.3 (settings models)      ─┘
```

13.1, 13.2, 13.3 run in parallel. 13.4 joins them and bundles
13.5. 13.6 follows 13.4. 13.7 closes out.

## 14. Test Plan Summary

Per-task tests are listed in §13. The cross-cutting
verification target (n0002 § "Work breakdown" #6) is the
artifacts-os vault itself running `art ls --kind task` and
showing:

- `t0042` indented under `t0036`
- `t0043`–`t0046` indented under `t0041`

This is the integration test in task #4's matrix. It
requires no fixture; the vault's own task tree is the input.

## 15. Open Questions — Resolved

Direct map from n0002 § "Open questions for the spec":

| n0002 question | Resolution | Spec section |
|----------------|-----------|--------------|
| Where is the hierarchy declared? | **Revised 2026-05-06**: in `artifacts.yaml` under `default_layouts[<kind>].parent_field` or on a view's `parent_field` field. Kind JSON does not declare layout (originally `x-layouts.tree.parent_field`; pivoted per §0). Single string in v1; the same forward-compat extensions land in the same map. | §3.1, §3.2, §3.4 |
| What does a root look like? Parent outside slice? Missing parent? | Four `TreeNote` cases: NORMAL (root), ORPHAN_OUT_OF_SLICE (parent in registry but filtered out), ORPHAN_MISSING (parent not in registry), CYCLE_BREAK. Each rendered with a distinct annotation; all kept visible. | §6.4 |
| What sibling order does the user see? | Default: by `id` (or `name` for non-numbered kinds). With `--sort`/`view.sort`: by that key, applied at every level; tree shape preserved. | §6.2 |
| Cycles and orphans — fail loudly, break visibly, or silently flatten? | **Visible-break.** Render the back-edge row with `↻ cycle`, stop descending from that edge, emit one stderr warning per cycle. | §6.3 |
| Where does traversal live — `views/` or `core/`? | `views/`. Module DAG argument: `-q`/`-j` consume flat lists; `--fields` is a `views/` concept; traversal is a presentation concern. | §5.1 |
| Filtered slices — child kept, parent hidden? | Promote child to root with a Case B annotation (`↑[parent: <ref>]`). | §7 |

## 16. Decision Log

| Marker | Items |
|--------|-------|
| **Decided (original 2026-05-06)** | (1) Layout is a `Callable[(items, columns, kind_def), Renderable]` registered in `views.LAYOUTS`. (2) Tree returns `rich.Table`, not `rich.Tree`. (3) ~~`x-layouts.tree.parent_field` is a single string in v1; forward-compat to multi-source by extending the same block.~~ — **superseded by R-1 below.** (4) Tree traversal lives in `views/`; `core.list_artifacts` stays flat. (5) Default sibling order is by `id` (or `name` for non-numbered kinds); `--sort` applies at every level with tree shape preserved. (6) Cycles → visible-break + `↻` annotation + single stderr warning. (7) Filtered-out parent → child is promoted to root with `↑[parent: <ref>]` Case B annotation. (8) `--layout` flag, no short form; ~~resolution chain explicit > view > settings.default_layouts > kind.x-layouts.default > implicit "table".~~ — **superseded by R-3 below.** (9) `-q`/`-j` carve out: layout selection skipped; sort still applies on flat data. (10) `--fields` semantics under tree: same parser, prefix attaches to the **first** column. (11) ~~`ViewConfig.layout: str \| None` and `ViewsConfig.default_layouts: dict[str, str]` are added; both optional.~~ — **revised by R-4 below.** (12) `x-columns` preserved unchanged; ~~`x-layouts` is additive.~~ — **`x-layouts` deleted entirely; see R-2 below.** (13) Bidirectional traversal precedence: when a future kind declares both `parent_field` and `children_field`, `parent_field` is the traversal source; `children_field` is denormalized metadata the layout does not read. No divergence policy. |
| **Decided (revision 2026-05-06)** | **(R-1)** Layout configuration lives in `artifacts.yaml` only; kind JSON describes data shape. **(R-2)** `x-layouts` is **deleted entirely** from the kind schema — no narrower replacement (`x-hierarchy`, etc.). The `parent_field` datum moves into the layout config object alongside the layout name. Rationale §11.3. **(R-3)** Resolution chain is **four rungs**: explicit `--layout` > `view.layout` > `default_layouts[<kind>].layout` > implicit `"table"`. The kind-default rung is removed. **(R-4)** `default_layouts` becomes `dict[str, LayoutConfig]` (object-form) with a string-form shorthand for layouts that take no config. `LayoutConfig` carries `layout: str` and `parent_field: str \| None`. **(R-5)** `ViewConfig` gains a `parent_field: str \| None` field. **(R-6)** `parent_field` resolution follows a parallel sibling chain (view > `default_layouts[<kind>]`); a `--layout tree` invocation without a resolvable parent_field is a ValidationError, not a silent fall-through. **(R-7)** Property-existence check (`parent_field` matches a kind property) moves from registry-load to CLI-resolve, keeping the renderer kind-agnostic and the registry presentation-agnostic. **(R-8)** `render_tree(parent_field=...)` becomes required (no kind_def fallback). **(R-9)** Breaking change against shipped v1; one-day window of as-shipped behaviour, no third-party adopters. Migration documented in §11.4. |
| **Recommended** | (a) Implement task #3 against task #2's kind schema using the artifacts-os vault as integration fixture. (b) Add a `Registry.exists_stem` helper at the same time as `render_tree` so cases B and C diagnose precisely. (c) Promote `core.discover._unwrap_wikilink` to public `unwrap_wikilink` to give `views/` a clean import path. (d) Use `pytest.warns(...)` for the cycle-warning test rather than capturing stderr directly. |
| **Deferred** | A second concrete layout (board, timeline, card). Multi-source tree (`parent + depends_on`). Down-pointer kinds (`tree.children_field`). Hierarchical `art show`. TUI integration. `x-layouts.<layout>.columns` (per-layout column lists). Per-kind `prefix_column` override (currently fixed to first column). Loud-fail mode for cycles (the present rendering surfaces the bug; loud-fail is opt-in for a future release if user research shows operators want it). |
