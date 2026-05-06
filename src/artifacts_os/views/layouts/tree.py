"""Tree layout: compute_tree, render_tree, TreeNote.

Spec: s0022-tree-layout §5, §6, §9
"""

import enum
import sys
from collections.abc import Callable
from typing import Any

from rich.table import Table
from rich.text import Text

from artifacts_os.core.discover import unwrap_wikilink
from artifacts_os.core.errors import ValidationError
from artifacts_os.core.models import ArtifactMeta, KindDef

from artifacts_os.views._views import FieldSpec, format_field


class TreeNote(enum.Enum):
    """Per-row annotation produced by compute_tree and consumed by render_tree."""

    NORMAL = "normal"
    ORPHAN_OUT_OF_SLICE = "orphan_out_of_slice"
    ORPHAN_MISSING = "orphan_missing"
    CYCLE_BREAK = "cycle_break"


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
    parent_field: str | None = None,
    sort_key: Callable[[ArtifactMeta], Any] | None = None,
    is_known_stem: Callable[[str], bool] | None = None,
) -> Table:
    """Render *items* as a tree-prefixed Rich Table.

    *parent_field* defaults to kind_def.meta["layouts"]["tree"]["parent_field"]
    when None. Raises ValidationError when both are None — tree layout requires
    a parent field.

    *is_known_stem* is used to distinguish Case B (parent filtered out,
    ↑[parent: ref]) from Case C (parent missing from vault, ?[parent: ref]).
    When None, both cases render as ?[parent: ref].
    """
    # Resolve parent_field.
    resolved_parent_field = parent_field
    if resolved_parent_field is None and kind_def is not None:
        layouts_meta = kind_def.meta.get("layouts", {})
        tree_meta = layouts_meta.get("tree", {})
        resolved_parent_field = tree_meta.get("parent_field")
    if resolved_parent_field is None:
        raise ValidationError(
            "render_tree requires a parent_field; pass parent_field= or"
            " set kind_def.meta['layouts']['tree']['parent_field']"
        )

    nodes = compute_tree(items, parent_field=resolved_parent_field, sort_key=sort_key)

    table = Table()
    for col in columns:
        table.add_column(col.label)

    status_colors: dict[str, str] = {}
    if kind_def is not None:
        status_colors = kind_def.meta.get("status_colors", {})

    for idx, (item, depth, note) in enumerate(nodes):
        row: list[Any] = []
        for col_idx, col in enumerate(columns):
            raw = item.frontmatter.get(col.key, "")
            cell_str = format_field(raw, col.fmt)

            if col_idx == 0:
                # Prepend tree prefix glyph to first column.
                prefix = _glyph(nodes, idx)
                cell_str = prefix + cell_str

                # Append annotation for non-normal nodes (§9.3).
                if note == TreeNote.CYCLE_BREAK:
                    cell_str += "  ↻ cycle"
                elif note in (TreeNote.ORPHAN_OUT_OF_SLICE, TreeNote.ORPHAN_MISSING):
                    raw_parent = item.frontmatter.get(resolved_parent_field, "")
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

            if col.key == "status" and cell_str in status_colors:
                row.append(Text(cell_str, style=status_colors[cell_str]))
            else:
                row.append(cell_str)

        table.add_row(*row)

    return table
