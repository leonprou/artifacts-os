"""Tree layout: compute_tree, render_tree, TreeNote, PRUNE_MODES.

Spec: s0022-tree-layout §5, §6, §9 (base) +
      s0024-tree-prune-modes §3, §6 (prune modes)
"""

import enum
import sys
from collections.abc import Callable
from typing import Any

from rich.style import Style
from rich.table import Table
from rich.text import Text

from artifacts_os.core.discover import unwrap_wikilink
from artifacts_os.core.models import ArtifactMeta, KindDef

from artifacts_os.views._views import FieldSpec, format_field


class TreeNote(enum.Enum):
    """Per-row annotation produced by compute_tree and consumed by render_tree."""

    NORMAL = "normal"
    ORPHAN_OUT_OF_SLICE = "orphan_out_of_slice"
    ORPHAN_MISSING = "orphan_missing"
    CYCLE_BREAK = "cycle_break"
    # s0024 §6.2 — ancestor pulled in by prune=ancestors; render dim with
    # `· (context)` annotation so the user can tell it didn't match the filter.
    CONTEXT_ANCESTOR = "context_ancestor"


#: Registered prune modes (s0024 §3.1). Adding a fourth mode means
#: registering it here, teaching ``_apply_prune`` how to expand, and
#: documenting the visual contract in s0024.
PRUNE_MODES: frozenset[str] = frozenset({"strict", "ancestors", "subtree"})


def _default_sort_key(item: ArtifactMeta) -> str:
    """Default sibling order: id ascending; fall back to name for non-numbered kinds."""
    return item.id if item.id else item.name


def compute_tree(
    items: list[ArtifactMeta],
    *,
    parent_field: str,
    sort_key: Callable[[ArtifactMeta], Any] | None = None,
) -> list[tuple[ArtifactMeta, int, "TreeNote"]]:
    """Order *items* parent-before-children; return (item, depth, note).

    *sort_key* sets sibling order at every level. If None, falls back to id
    (or name for non-numbered kinds).
    *note* is one of TreeNote.NORMAL, TreeNote.ORPHAN_OUT_OF_SLICE,
    TreeNote.CYCLE_BREAK — see §6. ORPHAN_MISSING is assigned by render_tree
    when is_known_stem confirms the parent does not exist in the vault.
    """
    if not items:
        return []

    effective_sort_key = sort_key if sort_key is not None else _default_sort_key

    # Build stem → item map for parent resolution.
    by_stem: dict[str, ArtifactMeta] = {item.path.stem: item for item in items}

    # Separate items into children (parent in by_stem) and top-level (root or orphan).
    # children_map: parent_stem → list of direct children
    children_map: dict[str, list[ArtifactMeta]] = {item.path.stem: [] for item in items}
    # top_level: (item, note)
    top_level: list[tuple[ArtifactMeta, TreeNote]] = []

    for item in items:
        raw = item.frontmatter.get(parent_field)
        if not raw:
            top_level.append((item, TreeNote.NORMAL))
        else:
            bare = unwrap_wikilink(str(raw))
            parent_item = by_stem.get(bare)
            if parent_item is None:
                # Parent not in input slice — orphan (B or C; distinguished in render_tree).
                top_level.append((item, TreeNote.ORPHAN_OUT_OF_SLICE))
            else:
                children_map[parent_item.path.stem].append(item)

    # Sort sibling groups.
    top_level.sort(key=lambda x: effective_sort_key(x[0]))
    for stem in children_map:
        children_map[stem].sort(key=effective_sort_key)

    result: list[tuple[ArtifactMeta, int, TreeNote]] = []
    warned_stems: set[str] = set()
    visited: set[str] = set()

    def visit(
        node: ArtifactMeta,
        depth: int,
        self_note: TreeNote,
        ancestors: frozenset[str],
    ) -> None:
        visited.add(node.path.stem)
        result.append((node, depth, self_note))
        stem = node.path.stem
        new_ancestors = ancestors | {stem}
        for child in children_map.get(stem, []):
            child_stem = child.path.stem
            if child_stem in new_ancestors:
                # Cycle detected — emit visible break row and warn once.
                visited.add(child_stem)
                result.append((child, depth + 1, TreeNote.CYCLE_BREAK))
                cycle_key = min(child_stem, stem)
                if cycle_key not in warned_stems:
                    warned_stems.add(cycle_key)
                    kind_name = node.frontmatter.get("kind", "unknown")
                    print(
                        f"warning: cycle detected on parent chain of"
                        f" {child_stem} (kind: {kind_name})",
                        file=sys.stderr,
                    )
            else:
                visit(child, depth + 1, TreeNote.NORMAL, new_ancestors)

    for item, note in top_level:
        visit(item, 0, note, frozenset())

    # Second pass: handle items that weren't reached because they form a
    # pure cycle with no natural root (all members have parents in by_stem).
    unvisited = sorted(
        [item for item in items if item.path.stem not in visited],
        key=effective_sort_key,
    )
    while unvisited:
        # Force the first unvisited item as a root — the DFS will detect cycles.
        forced_root = unvisited[0]
        visit(forced_root, 0, TreeNote.NORMAL, frozenset())
        unvisited = [item for item in unvisited if item.path.stem not in visited]

    return result


# ---------------------------------------------------------------------------
# Prune expansion (s0024 §6.3 / §6.4)
# ---------------------------------------------------------------------------


def _expand_ancestors(
    items: list[ArtifactMeta],
    *,
    parent_field: str,
    full_items: list[ArtifactMeta],
) -> tuple[list[ArtifactMeta], set[str]]:
    """Return (items + walked ancestors, set of ancestor stems).

    For each item whose ``parent_field`` resolves to a stem outside the
    matched set, walk upward via *full_items* until a root, a matched
    ancestor, a missing parent, or a cycle is reached. Each newly
    discovered ancestor is added to the working list.

    The returned ancestor stem set is used by render_tree to mark those
    rows as TreeNote.CONTEXT_ANCESTOR.

    Cycle detection emits one stderr warning per cycle, identical wording
    to s0022 §6.3.
    """
    matched_stems: set[str] = {item.path.stem for item in items}
    full_by_stem: dict[str, ArtifactMeta] = {
        m.path.stem: m for m in full_items
    }
    ancestors: dict[str, ArtifactMeta] = {}
    warned_cycles: set[frozenset[str]] = set()

    for item in items:
        # Walk up from this item's direct parent.
        cur_ref = item.frontmatter.get(parent_field)
        # Track stems visited by *this* walk for cycle detection.
        walk_visited: set[str] = {item.path.stem}
        while cur_ref:
            bare = unwrap_wikilink(str(cur_ref))
            if not bare:
                break
            if bare in walk_visited:
                # Cycle on the upward walk — warn once, halt walk.
                cycle_key = frozenset(walk_visited | {bare})
                if cycle_key not in warned_cycles:
                    warned_cycles.add(cycle_key)
                    print(
                        "warning: cycle detected on parent chain of"
                        f" {bare} (kind: {item.frontmatter.get('kind', 'unknown')})",
                        file=sys.stderr,
                    )
                break
            walk_visited.add(bare)

            if bare in matched_stems:
                # Reached a matched ancestor — child will attach beneath it.
                break
            if bare in ancestors:
                # Already discovered via another walk — stop (no rework).
                break
            meta = full_by_stem.get(bare)
            if meta is None:
                # Parent missing from the full registry — child stays an
                # orphan (Case C).
                break
            ancestors[bare] = meta
            cur_ref = meta.frontmatter.get(parent_field)

    expanded: list[ArtifactMeta] = list(items) + list(ancestors.values())
    return expanded, set(ancestors.keys())


def _expand_subtree(
    items: list[ArtifactMeta],
    *,
    parent_field: str,
    full_items: list[ArtifactMeta],
) -> list[ArtifactMeta]:
    """Return items + all descendants of every matched item.

    For each x in *items*, BFS through children (computed from *full_items*)
    and collect every descendant. Cycle-guarded by a global visited set.
    """
    matched_stems: set[str] = {item.path.stem for item in items}
    full_by_stem: dict[str, ArtifactMeta] = {
        m.path.stem: m for m in full_items
    }

    # Build a children_map over the full registry: parent_stem → list of meta.
    children_map: dict[str, list[ArtifactMeta]] = {}
    for m in full_items:
        raw = m.frontmatter.get(parent_field)
        if not raw:
            continue
        bare = unwrap_wikilink(str(raw))
        if not bare:
            continue
        children_map.setdefault(bare, []).append(m)

    descendants: dict[str, ArtifactMeta] = {}
    visited: set[str] = set(matched_stems)
    queue: list[str] = list(matched_stems)
    while queue:
        cur_stem = queue.pop(0)
        for child in children_map.get(cur_stem, []):
            child_stem = child.path.stem
            if child_stem in visited:
                continue
            visited.add(child_stem)
            descendants[child_stem] = child
            queue.append(child_stem)

    # full_by_stem unused below but kept for symmetry / future use.
    del full_by_stem
    return list(items) + list(descendants.values())


def _apply_prune(
    items: list[ArtifactMeta],
    *,
    prune: str,
    parent_field: str,
    full_items: list[ArtifactMeta] | None,
) -> tuple[list[ArtifactMeta], set[str]]:
    """Apply the requested prune mode and return (expanded_items, context_stems).

    * ``strict`` — return items unchanged; no context stems.
    * ``ancestors`` — walk upward via *full_items*, returning the matched
      set plus discovered ancestors; ancestor stems flagged as context.
    * ``subtree`` — expand every match's full descendant set via
      *full_items*; no context stems (subtree opts out of filter honesty).

    Raises ValueError on unknown mode or missing *full_items* for non-strict.
    """
    if prune == "strict":
        return list(items), set()
    if prune not in PRUNE_MODES:
        raise ValueError(
            f"unknown prune mode {prune!r}; known: {sorted(PRUNE_MODES)}"
        )
    if full_items is None:
        raise ValueError(
            f"prune={prune!r} requires full_items "
            "(an unfiltered list to walk for ancestors / descendants)"
        )
    if prune == "ancestors":
        return _expand_ancestors(
            items, parent_field=parent_field, full_items=full_items
        )
    # subtree
    return (
        _expand_subtree(items, parent_field=parent_field, full_items=full_items),
        set(),
    )


def _glyph(nodes: list[tuple[ArtifactMeta, int, TreeNote]], idx: int) -> str:
    """Return the tree-drawing prefix for the node at *idx*.

    Uses "└─" for the last sibling at a given depth, "├─" for others.
    Prefix = "  " * depth + glyph + " ".
    """
    _, depth, _ = nodes[idx]
    if depth == 0:
        return ""
    # Look ahead to determine whether another node at the same depth follows
    # before the parent's depth (or end of list).
    is_last = True
    for j in range(idx + 1, len(nodes)):
        _, other_depth, _ = nodes[j]
        if other_depth < depth:
            break  # returned to a shallower level — this is the last sibling
        if other_depth == depth:
            is_last = False
            break  # another sibling found at the same depth
    glyph = "└─" if is_last else "├─"
    return "  " * depth + glyph + " "


def render_tree(
    items: list[ArtifactMeta],
    columns: list[FieldSpec],
    *,
    kind_def: KindDef | None = None,
    parent_field: str,
    sort_key: Callable[[ArtifactMeta], Any] | None = None,
    is_known_stem: Callable[[str], bool] | None = None,
    prune: str = "strict",
    full_items: list[ArtifactMeta] | None = None,
) -> Table:
    """Render *items* as a tree-prefixed Rich Table.

    *parent_field* is required — the caller is responsible for resolving
    which frontmatter key points up the hierarchy.

    *kind_def* carries ``status_colors`` for cell styling; it is not used
    to resolve *parent_field*.

    *is_known_stem* is used to distinguish Case B (parent filtered out,
    ↑[parent: ref]) from Case C (parent missing from vault, ?[parent: ref]).
    When None, both cases render as ?[parent: ref].

    *prune* selects the prune mode (s0024 §3.1):

    - ``strict`` (default) — render only the matched set; preserves the
      existing s0022 §6.4 / §7 behaviour.
    - ``ancestors`` — auto-include the parent chain of every matched
      node up to root; rendered as dim ``· (context)`` rows.
    - ``subtree`` — once a node matches, render its full descendant
      subtree regardless of filter (no marking).

    *full_items* — required when ``prune != 'strict'``. The unfiltered
    list of artifacts (typically of the same kind) used to walk ancestors
    and descendants.
    """
    # Apply prune expansion before tree assembly.
    expanded_items, context_stems = _apply_prune(
        items,
        prune=prune,
        parent_field=parent_field,
        full_items=full_items,
    )

    nodes = compute_tree(
        expanded_items, parent_field=parent_field, sort_key=sort_key
    )

    table = Table()
    for col in columns:
        table.add_column(col.label)

    status_colors: dict[str, str] = {}
    if kind_def is not None:
        status_colors = kind_def.meta.get("status_colors", {})

    dim_style = Style(dim=True)

    for idx, (item, depth, note) in enumerate(nodes):
        is_context = item.path.stem in context_stems
        # Promote the note when this row is a context ancestor — render_tree
        # determines this from the prune-pass result rather than threading
        # the note through compute_tree, which stays focused on assembly.
        effective_note = (
            TreeNote.CONTEXT_ANCESTOR if is_context else note
        )

        row: list[Any] = []
        for col_idx, col in enumerate(columns):
            raw = item.frontmatter.get(col.key, "")
            cell_str = format_field(raw, col.fmt)

            if col_idx == 0:
                # Prepend tree prefix glyph to first column.
                prefix = _glyph(nodes, idx)
                cell_str = prefix + cell_str

                # Append annotation for non-normal nodes.
                if effective_note == TreeNote.CYCLE_BREAK:
                    cell_str += "  ↻ cycle"
                elif effective_note == TreeNote.CONTEXT_ANCESTOR:
                    # s0024 §3.3 filter-honesty marker.
                    cell_str += "  · (context)"
                elif effective_note in (
                    TreeNote.ORPHAN_OUT_OF_SLICE,
                    TreeNote.ORPHAN_MISSING,
                ):
                    raw_parent = item.frontmatter.get(parent_field, "")
                    bare_ref = unwrap_wikilink(str(raw_parent)) if raw_parent else ""
                    if is_known_stem is not None and not is_known_stem(bare_ref):
                        # Case C — parent not in vault at all.
                        cell_str += f"  ?[parent: {bare_ref}]"
                    elif is_known_stem is not None:
                        # Case B — parent in vault but filtered out.
                        cell_str += f"  ↑[parent: {bare_ref}]"
                    else:
                        # Degraded: is_known_stem not provided; collapse B and C.
                        cell_str += f"  ?[parent: {bare_ref}]"

            if effective_note == TreeNote.CONTEXT_ANCESTOR:
                # Dim every cell in a context row so the eye skips past it.
                row.append(Text(cell_str, style=dim_style))
            elif col.key == "status" and cell_str in status_colors:
                row.append(Text(cell_str, style=status_colors[cell_str]))
            else:
                row.append(cell_str)

        table.add_row(*row)

    return table
