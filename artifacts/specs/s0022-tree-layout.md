---
kind: spec
id: s0022
name: tree-layout
status: approved
created: 2026-05-06
task: "[[t0113-spec-tree-layout-for-art]]"
agent: architect
---

# Tree Layout for `art ls`

Sub-spec of [[s0007-artifacts-os-views-module]]. Defines the
**layout abstraction** for `artifacts_os.views`, the **tree
layout** as its first concrete second member alongside the
existing table, and the kind-side / CLI-side / settings-side
contracts that surround them.

Origin: scoping note [[n0002-layouts-tree-view-scoping]]. Task
brief: [[t0113-spec-tree-layout-for-art]].

**Scope: design only.** Implementation is filed as the four
follow-up tasks listed in n0002 (#2 kind schema, #3 renderer,
#4 CLI wiring, #5 docs). Tasks #2 and #3 are designed to start
in parallel after this spec lands; the contracts in §3 (kind
schema), §5 (renderer signature), and §8 (CLI flag) are the
parallel-start interlocks.

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
  already used for `columns` and `status_colors`; the kind-side
  declaration in §3 is an additive `x-layouts` block on the same
  JSON schema.
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

## 3. Kind-Level Declaration

### 3.1 Schema shape

A kind opts into hierarchical rendering by adding an
`x-layouts` block to its `kind.json`:

```json
{
  "x-dir": "tasks",
  "x-prefix": "t",
  "x-numbered": true,
  "x-columns": ["id", "name", "status", "assignee"],
  "x-layouts": {
    "default": "tree",
    "tree": {
      "parent_field": "parent"
    }
  },
  "properties": { ... }
}
```

Three keys are introduced under `x-layouts`. Each is independent;
omitting any one is well-defined.

| Key | Type | Required | Purpose |
|-----|------|----------|---------|
| `default` | string — `"table"` \| `"tree"` | no — falls back to `"table"` | Layout selected when no view, settings, or flag overrides |
| `tree` | object | no — but **required to enable `default: "tree"`** | Tree-layout configuration. Absence means "no tree configuration declared"; setting `default: "tree"` without it is a load-time error per §3.3. |
| `tree.parent_field` | string — frontmatter key name | yes (when `tree` block present) | Field on the artifact's frontmatter whose value points up to its parent (wikilink string) |

### 3.2 Forward-compat for traversal direction and second source

`tree.parent_field` is a **single string** in v1, not a list.
Forward-compat is preserved by the **block name being
`tree`**, not `parent_tree` or `from_parent`: future schema
keys land *inside* the same block.

#### Direction: up-pointer vs. down-pointer

Two shapes a future kind may need:

```jsonc
// v1 — declared
"tree": { "parent_field": "parent" }
// renderer walks DOWN via an inverse map built from parent_field

// Future — kind with no upward pointer (e.g. playlist→tracks)
"tree": { "children_field": "tracks" }
// renderer walks DOWN via the literal list at parent[children_field]
```

**Precedence rule (locked here so v2 doesn't re-litigate it):**
when both `parent_field` and `children_field` are declared on
the same kind, **`parent_field` is the traversal source**.
`children_field` is denormalized metadata the layout does not
read. There is no divergence policy because there is no
divergence to resolve — only one field drives the walk.

`children_field` is **not implemented in v1**; the rule is
documented now so the eventual implementer has nothing to
decide.

#### Second source (parent + depends_on)

A future multi-source design adds new keys inside the same
block (e.g. `tree.sources: [{field: "parent"}, {field:
"depends_on"}]`). The single-string `parent_field` becomes
a deprecated alias for the one-source case; v1 callers
stay readable.

#### Default layout name

The `default: "tree"` value is also forward-compat: a future
board layout declares `default: "board"` and the same
resolution chain (§8.2) selects it without code changes in
`cli/`.

### 3.3 Validation at registry load

`registry._load_vault_kinds` (today: `registry.py:130–151`)
gains three checks when `x-layouts` is present:

1. `x-layouts.default`, if present, must be one of the
   currently-registered layout names (`table`, `tree`). Unknown
   value → `ValidationError(f"unknown layout {name!r}")`.
2. If `x-layouts.default == "tree"`, `x-layouts.tree` must be
   present. Otherwise → `ValidationError("kind {k!r} declares
   default layout 'tree' but has no x-layouts.tree block")`.
3. If `x-layouts.tree` is present, `parent_field` must be a
   string and must match a property name in the same schema's
   `properties` map. (Catches typos and prevents pointing at a
   field that does not exist.) Failure → `ValidationError`.

`KindDef.meta` carries the parsed result under `meta["layouts"]`:

```python
{
  "default": "tree",
  "tree": {"parent_field": "parent"},
}
```

Consumers (`views/`, `cli/`) read `meta["layouts"]` only;
they do not re-parse `x-layouts`. This matches the existing
discipline used for `meta["columns"]` and `meta["status_colors"]`
(s0007 § "KindDef.meta keys consumed by views").

### 3.4 Concrete declarations for the v1 vault

Only `task` declares tree in v1. The other four kinds (`agent`,
`note`, `research`, `spec`) **do not** add `x-layouts`; they
fall back to table — no behaviour change.

```json
// artifacts/kinds/task.json
"x-layouts": { "default": "tree", "tree": { "parent_field": "parent" } }

// artifacts/kinds/spec.json   — not added in v1
// artifacts/kinds/research.json — not added in v1
// artifacts/kinds/note.json   — not added in v1
// artifacts/kinds/agent.json  — not added in v1
```

This is the complete migration footprint of task #2 (kind
schema). One file changes; four are inspected and confirmed
unaffected.

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

### 4.3 Selecting the layout — kind default

A kind selects its default layout via
`meta["layouts"]["default"]`. When the key is absent, the
default is `"table"`. The resolution chain that lets a user
override this is in §8.2.

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
    parent_field: str | None = None,
    sort_key: Callable[[ArtifactMeta], object] | None = None,
) -> Table:
    """Render *items* as a tree-prefixed table.

    *parent_field* defaults to kind_def.meta["layouts"]["tree"]
    ["parent_field"] when None. Raises ValidationError when both
    are None — tree layout requires a parent field.
    """
```

The CLI passes `parent_field` explicitly only when overriding;
in the common path it leaves the parameter `None` and lets the
function read from `kind_def.meta`.

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

### 8.2 Resolution chain — explicit > view > kind default > implicit

Five rungs, top wins:

1. **Explicit `--layout NAME`** — user intent, last-mile.
2. **View config** — `view_cfg.layout` (a new optional field on
   `ViewConfig`; see §10.1). Set when the user is using a saved
   view that pins a layout.
3. **`default_layouts[kind]` settings map** — kind-scoped user
   preference under `default_layouts:` in `artifacts.yaml` (see
   §10.2). Lets an end-user say "always tree for tasks on this
   vault" without editing the kind file.
4. **Kind default** — `kind_def.meta["layouts"]["default"]`,
   sourced from `x-layouts.default` in the schema.
5. **Implicit** — `"table"`. Every kind without any of the
   above ends up as table. This is the v1 default for every
   kind except `task`.

The chain is implemented in a new helper:

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
        m = settings.views.default_layouts        # see §10.2
        if kind_def is not None and kind_def.name in m:
            return m[kind_def.name]
    if kind_def is not None:
        return kind_def.meta.get("layouts", {}).get("default", "table")
    return "table"
```

Validation: the resolved name must be in `views.LAYOUTS`. If
not, raise `ValidationError`; exit 2.

### 8.3 Opt-out — flat output on a hierarchical kind

The user opts out by:

```bash
art ls --kind task --layout table
```

Or, for a per-vault preference:

```yaml
# artifacts.yaml
default_layouts:
  task: table
```

Both leave `art ls --kind task` rendering flat regardless of
the kind's `x-layouts.default: tree`. The first is a one-shot;
the second is durable.

A view can also pin layout:

```yaml
views:
  active:
    columns: id,name,assignee,status
    filters: { status: in-progress }
    layout: table
```

`art ls --view active --kind task` then renders flat.

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

The CLI integration tests (per §13) cover these rows:

| Kind layout default | settings `default_layouts` | view `layout` | flag `--layout` | Effective |
|---------------------|----------------------------|---------------|-----------------|-----------|
| (absent) | (absent) | (absent) | (absent) | `table` |
| `tree` | (absent) | (absent) | (absent) | `tree` |
| `tree` | `{task: table}` | (absent) | (absent) | `table` |
| `tree` | `{task: table}` | `tree` | (absent) | `tree` |
| `tree` | `{task: table}` | `tree` | `table` | `table` |
| `tree` | (absent) | (absent) | `tree` | `tree` |
| (absent on kind) | (absent) | (absent) | `tree` | `tree` (works on any kind that *can* resolve a parent_field; ValidationError if not) |
| (absent) | (absent) | (absent) | `nope` | exit 2, `unknown layout 'nope'` |

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

### 10.1 `ViewConfig` — add optional `layout` field

```python
@dataclass
class ViewConfig:
    columns: str
    filters: dict[str, Any] = field(default_factory=dict)
    sort: str | None = None
    layout: str | None = None      # NEW — None means "fall through"
```

YAML:

```yaml
views:
  active-tree:
    columns: id,name,assignee,status
    filters: { status: in-progress }
    layout: tree

  active-flat:
    columns: id,name,assignee,status
    filters: { status: in-progress }
    layout: table
```

Validation: if `layout` is set, it must be one of
`views.LAYOUTS`. Otherwise → `ValidationError` at settings
parse time (in `_parse_view`, `views/models.py:71–82`). Emitted
as exit 2 by the CLI.

`layout` is **optional** — every existing view file keeps
working unchanged. None means "fall through to the
default_layouts / kind / implicit chain" per §8.2.

### 10.2 `ViewsConfig` — add `default_layouts: dict[str, str]`

Symmetric to the existing `default_views: dict[str, str]`
(s0007 § "Settings YAML Schema"). Maps kind name → layout
name. Lets the user pin a layout per-kind without writing a
view.

```python
@dataclass
class ViewsConfig:
    views: dict[str, ViewConfig]
    default_views: dict[str, str]
    default_layouts: dict[str, str]      # NEW — empty dict if absent
```

YAML:

```yaml
default_views:
  session: sessions

default_layouts:
  task: table          # opt out of tree on this vault
  spec: table          # explicit (matches implicit anyway)
```

Validation at parse time: each value must be in
`views.LAYOUTS`. Each key need not be a registered kind (so
a vault can declare a preference for a kind it does not yet
have without an error). Unknown layout name → `ValidationError`,
exit 2.

### 10.3 Vocabulary-collision risk — addressed

The n0002 risk: `ViewConfig` already speaks the language of
"how the user wants to look at data". Adding `layout` could
collide with `views` itself.

**Resolution**: `views` is the **module name** and the
**configuration namespace**. `layout` is a **field within a
view**. The two are at different levels — a view has a
columns string, a filters dict, a sort key, and now a layout
name. No collision: the view declares "use the tree layout
for this saved query"; the layout is internal vocabulary
of the renderer.

The existing top-level `views:` and `default_views:`
keys keep their meaning (saved queries; per-kind default
view binding). `default_layouts:` is the new sibling key,
parallel to `default_views:` but for the layout dimension.
The two are independent: a vault may set `default_views.task =
active` and `default_layouts.task = table` simultaneously —
the active view runs, in flat-table form.

### 10.4 `ViewsSettings.from_base` updates

`from_base` (in `views/models.py:42–68`) gains parsing of:

- `base.raw["default_layouts"]` (optional dict)

```python
raw_dl = base.raw.get("default_layouts") or {}
if not isinstance(raw_dl, dict):
    raise ValueError("default_layouts must be a mapping")
for k, v in raw_dl.items():
    if v not in views.LAYOUTS:
        raise ValueError(f"default_layouts[{k!r}] = {v!r} is not a registered layout")
```

`_parse_view` is extended to read `layout`:

```python
def _parse_view(d: dict) -> ViewConfig:
    if "columns" not in d:
        raise ValueError("view entry missing required 'columns' field")
    layout = d.get("layout")
    if layout is not None and layout not in views.LAYOUTS:
        raise ValueError(f"view 'layout' = {layout!r} is not a registered layout")
    return ViewConfig(
        columns=d["columns"],
        filters=dict(d.get("filters") or {}),
        sort=d.get("sort"),
        layout=layout,
    )
```

The layout-validation in both helpers reads from
`views.layouts.LAYOUTS` — i.e. the same registry the CLI uses.
A circular import is avoided by importing inside the function
body (Python permits this).

## 11. `x-columns` Migration — Compatibility Path

### 11.1 Decision — preserve `x-columns` unchanged

`x-columns` keeps its meaning, its key name, its position in
`kind.json`, and its parsed home in `meta["columns"]`. **No
migration is required for any existing kind file**, in v1 or
beyond.

### 11.2 Rationale — column model is layout-independent

The note (n0002 Risk #1) flags the migration blast radius if
the kind-file shape changes. The cleanest path is to not
change it: `x-columns` lists the column projection the
**user reads**, and that projection is independent of the
layout that draws it. The same `["id", "name", "status",
"assignee"]` works for the table layout and for the tree
layout — only the renderer changes; the columns do not.

The `x-layouts` block (§3) is **additive**:

- Existing kind files: `x-columns` works as today; no
  `x-layouts`; layout falls through to `table` (implicit
  default). No behaviour change.
- New / opted-in kind files: `x-columns` keeps its job;
  `x-layouts` declares the layout default and tree
  configuration. Two orthogonal blocks, one per concern.

### 11.3 Why not consolidate into `x-layouts.table.columns`

An alternative considered: move the `x-columns` list under
`x-layouts.table.columns`, justifying "each layout owns its
own column list". This is rejected:

- Every existing kind file (5 in this vault, plus the 5
  template kinds, plus any third-party vault using
  artifacts-os) would need editing for zero user-visible
  benefit.
- Tree shares the same column list as table; making the
  user duplicate it under both layouts is friction.
- The "each layout owns its columns" framing is a v3
  problem at best — when there is a third layout that
  genuinely wants different columns.

A future layout that needs different columns can declare
`x-layouts.<name>.columns` *additively*, with documented
fall-through to `x-columns` when absent. v1 does not need
that escape hatch.

### 11.4 Rollback story

If `x-layouts` ever needs to be redesigned, kind files that
declared it can have it stripped without affecting their
table behaviour — `x-columns` carries on. The migration
"out" of v1 is as cheap as the migration "in".

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

## 13. Implementation Outline (for follow-up tasks)

The four follow-up tasks from n0002 § "Work breakdown" map to
this spec:

### Task #2 — Kind schema + migration (developer)

1. Add `x-layouts` block to `artifacts/kinds/task.json` per §3.4.
2. Update `registry._load_vault_kinds` to:
   - Validate `x-layouts` per §3.3.
   - Populate `meta["layouts"]` per §3.3.
3. No changes to `agent.json`, `note.json`, `research.json`,
   `spec.json` (verify that `art ls --kind <each>` produces
   identical output before/after).
4. Tests: vault with `x-layouts` present and absent; invalid
   `default`; missing `tree.parent_field`; `parent_field`
   typo (not in `properties`).

### Task #3 — Tree renderer in `views/` (developer)

1. New module `src/artifacts_os/views/layouts/`:
   - `tree.py` — `compute_tree`, `render_tree`, `TreeNote`.
   - `table.py` — re-export of `render_table` for symmetry.
   - `__init__.py` — `LAYOUTS` registry.
2. Promote `core.discover._unwrap_wikilink` to public
   `core.discover.unwrap_wikilink` (no behaviour change; just
   a rename + back-compat alias kept private for one cycle).
3. Add `Registry.exists_stem(stem) -> bool` for the §6.4
   B-vs-C distinction.
4. Re-export from `views/__init__.py`: `Layout`, `LAYOUTS`,
   `render_tree`, `compute_tree`, `TreeNote`.
5. Tests:
   - Pure `compute_tree`: §6.4 cases A, B, C, D; sibling
     order; sort-key threading.
   - `render_tree` table output: prefix on first column,
     annotations on cases B/C/D.
   - Cycle detection emits one stderr warning; row gets `↻`.

### Task #4 — CLI wiring (developer; depends on #3)

1. Add `--layout` flag to `cli/commands/list.py` parser (§8.1).
2. Add `--layout` to `_RESERVED_FILTER_FLAG_NAMES`.
3. Add `resolve_layout` helper (§8.2).
4. Modify `run()` to call `views.LAYOUTS[name](items, columns,
   kind_def=..., parent_field=...)` for tree and pass
   `sort_key` (when active) instead of `_apply_sort` on flat
   list.
5. Validate `--layout NAME` against `LAYOUTS`.
6. Tests: §8.5 resolution-chain matrix; `-q`/`-j` unchanged
   under `--layout tree`; the verification target (§6.5) on
   the artifacts-os vault itself.

### Task #5 — Documentation (author / technical-writer)

1. `docs/settings.md` — add `default_layouts` section parallel
   to existing `default_views`.
2. `src/artifacts_os/views/README.md` — describe `LAYOUTS`,
   `render_tree`, `compute_tree`, the `Layout` type alias.
3. `src/artifacts_os/cli/README.md` — `--layout` flag under
   `list`; resolution chain; `-q`/`-j` carve-out.
4. `docs/adding-a-kind.md` — `x-layouts` block, when to
   declare tree, the `parent_field` contract.
5. `CLAUDE.md` "Coding Style" / "Naming Conventions" — no
   changes required (no new naming convention).

Tasks #2 and #3 share no files except the regression tests on
the artifacts-os vault itself. They can run in parallel; their
join point is task #4 (CLI wiring), which depends on both.

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
| Where is the hierarchy declared? | `x-layouts.tree.parent_field` on the kind schema. Single string in v1; block name reserved for forward-compat to multi-source. | §3.1, §3.2 |
| What does a root look like? Parent outside slice? Missing parent? | Four `TreeNote` cases: NORMAL (root), ORPHAN_OUT_OF_SLICE (parent in registry but filtered out), ORPHAN_MISSING (parent not in registry), CYCLE_BREAK. Each rendered with a distinct annotation; all kept visible. | §6.4 |
| What sibling order does the user see? | Default: by `id` (or `name` for non-numbered kinds). With `--sort`/`view.sort`: by that key, applied at every level; tree shape preserved. | §6.2 |
| Cycles and orphans — fail loudly, break visibly, or silently flatten? | **Visible-break.** Render the back-edge row with `↻ cycle`, stop descending from that edge, emit one stderr warning per cycle. | §6.3 |
| Where does traversal live — `views/` or `core/`? | `views/`. Module DAG argument: `-q`/`-j` consume flat lists; `--fields` is a `views/` concept; traversal is a presentation concern. | §5.1 |
| Filtered slices — child kept, parent hidden? | Promote child to root with a Case B annotation (`↑[parent: <ref>]`). | §7 |

## 16. Decision Log

| Marker | Items |
|--------|-------|
| **Decided** | (1) Layout is a `Callable[(items, columns, kind_def), Renderable]` registered in `views.LAYOUTS`. (2) Tree returns `rich.Table`, not `rich.Tree`. (3) `x-layouts.tree.parent_field` is a single string in v1; forward-compat to multi-source by extending the same block. (4) Tree traversal lives in `views/`; `core.list_artifacts` stays flat. (5) Default sibling order is by `id` (or `name` for non-numbered kinds); `--sort` applies at every level with tree shape preserved. (6) Cycles → visible-break + `↻` annotation + single stderr warning. (7) Filtered-out parent → child is promoted to root with `↑[parent: <ref>]` Case B annotation. (8) `--layout` flag, no short form; resolution chain explicit > view > settings.default_layouts > kind.x-layouts.default > implicit "table". (9) `-q`/`-j` carve out: layout selection skipped; sort still applies on flat data. (10) `--fields` semantics under tree: same parser, prefix attaches to the **first** column. (11) `ViewConfig.layout: str \| None` and `ViewsConfig.default_layouts: dict[str, str]` are added; both optional. (12) `x-columns` preserved unchanged; `x-layouts` is additive. (13) Bidirectional traversal precedence: when a future kind declares both `parent_field` and `children_field`, `parent_field` is the traversal source; `children_field` is denormalized metadata the layout does not read. No divergence policy. |
| **Recommended** | (a) Implement task #3 against task #2's kind schema using the artifacts-os vault as integration fixture. (b) Add a `Registry.exists_stem` helper at the same time as `render_tree` so cases B and C diagnose precisely. (c) Promote `core.discover._unwrap_wikilink` to public `unwrap_wikilink` to give `views/` a clean import path. (d) Use `pytest.warns(...)` for the cycle-warning test rather than capturing stderr directly. |
| **Deferred** | A second concrete layout (board, timeline, card). Multi-source tree (`parent + depends_on`). Down-pointer kinds (`tree.children_field`). Hierarchical `art show`. TUI integration. `x-layouts.<layout>.columns` (per-layout column lists). Per-kind `prefix_column` override (currently fixed to first column). Loud-fail mode for cycles (the present rendering surfaces the bug; loud-fail is opt-in for a future release if user research shows operators want it). |
