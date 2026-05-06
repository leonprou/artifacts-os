"""Tests for views.layouts.tree — compute_tree, render_tree, LAYOUTS registry.

Covers §5, §6, §9 of spec s0022-tree-layout.
Uses real ArtifactMeta instances constructed directly — no vault needed.
"""

import sys
from pathlib import Path

import pytest
from rich.table import Table

from artifacts_os.core.models import ArtifactMeta, KindDef
from artifacts_os.views import (
    LAYOUTS,
    Layout,
    TreeNote,
    compute_tree,
    parse_field_specs,
    render_table,
    render_tree,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_task(
    stem: str,
    *,
    id: str = "",
    parent: str | None = None,
    status: str | None = None,
) -> ArtifactMeta:
    """Build a minimal task ArtifactMeta."""
    fm: dict = {"id": id or stem, "kind": "task", "status": status}
    if parent is not None:
        fm["parent"] = f"[[{parent}]]"
    return ArtifactMeta(
        id=id or stem,
        kind="task",
        name=stem,
        title=stem,
        status=status,
        tags=[],
        created="2026-01-01",
        path=Path(f"tasks/{stem}.md"),
        frontmatter=fm,
    )


def stems(nodes: list[tuple[ArtifactMeta, int, TreeNote]]) -> list[str]:
    """Extract stem list from compute_tree output."""
    return [item.path.stem for item, _, _ in nodes]


def depths(nodes: list[tuple[ArtifactMeta, int, TreeNote]]) -> list[int]:
    """Extract depth list from compute_tree output."""
    return [depth for _, depth, _ in nodes]


def notes(nodes: list[tuple[ArtifactMeta, int, TreeNote]]) -> list[TreeNote]:
    """Extract note list from compute_tree output."""
    return [note for _, _, note in nodes]


def _task_kind() -> KindDef:
    return KindDef(
        name="task",
        dir="tasks",
        prefix="t",
        numbered=True,
        meta={
            "columns": ["id", "name", "status"],
            "layouts": {"default": "tree", "tree": {"parent_field": "parent"}},
        },
    )


def _first_col_cells(table: Table) -> list[str]:
    """Return the raw string cells in the first column."""
    return [str(c) for c in table.columns[0]._cells]


# ---------------------------------------------------------------------------
# compute_tree — Case A: simple tree (no parents)
# ---------------------------------------------------------------------------


class TestComputeTreeCaseA:
    def test_empty_input(self):
        result = compute_tree([], parent_field="parent")
        assert result == []

    def test_single_root(self):
        items = [make_task("t0001", id="t0001")]
        result = compute_tree(items, parent_field="parent")
        assert stems(result) == ["t0001"]
        assert depths(result) == [0]
        assert notes(result) == [TreeNote.NORMAL]

    def test_two_roots_sorted_by_id(self):
        items = [make_task("t0002", id="t0002"), make_task("t0001", id="t0001")]
        result = compute_tree(items, parent_field="parent")
        assert stems(result) == ["t0001", "t0002"]

    def test_root_with_one_child(self):
        parent = make_task("t0036", id="t0036")
        child = make_task("t0042", id="t0042", parent="t0036")
        result = compute_tree([child, parent], parent_field="parent")
        assert stems(result) == ["t0036", "t0042"]
        assert depths(result) == [0, 1]
        assert notes(result) == [TreeNote.NORMAL, TreeNote.NORMAL]


# ---------------------------------------------------------------------------
# compute_tree — multi-level tree (§6.5 verification fixture)
# ---------------------------------------------------------------------------


class TestComputeTreeMultiLevel:
    def _spec_items(self) -> list[ArtifactMeta]:
        """Fixture mirroring spec §6.5 verification target."""
        return [
            make_task("t0036", id="t0036"),
            make_task("t0041", id="t0041"),
            make_task("t0042", id="t0042", parent="t0036"),
            make_task("t0043", id="t0043", parent="t0041"),
            make_task("t0044", id="t0044", parent="t0041"),
            make_task("t0045", id="t0045", parent="t0041"),
            make_task("t0046", id="t0046", parent="t0041"),
        ]

    def test_spec_6_5_order(self):
        result = compute_tree(self._spec_items(), parent_field="parent")
        assert stems(result) == [
            "t0036", "t0042",
            "t0041", "t0043", "t0044", "t0045", "t0046",
        ]

    def test_spec_6_5_depths(self):
        result = compute_tree(self._spec_items(), parent_field="parent")
        assert depths(result) == [0, 1, 0, 1, 1, 1, 1]

    def test_spec_6_5_all_normal(self):
        result = compute_tree(self._spec_items(), parent_field="parent")
        assert all(n == TreeNote.NORMAL for n in notes(result))

    def test_three_levels(self):
        grandparent = make_task("t0001", id="t0001")
        parent = make_task("t0002", id="t0002", parent="t0001")
        child = make_task("t0003", id="t0003", parent="t0002")
        result = compute_tree([grandparent, parent, child], parent_field="parent")
        assert stems(result) == ["t0001", "t0002", "t0003"]
        assert depths(result) == [0, 1, 2]


# ---------------------------------------------------------------------------
# compute_tree — sibling order
# ---------------------------------------------------------------------------


class TestComputeTreeSiblingOrder:
    def test_default_order_by_id(self):
        root = make_task("t0001", id="t0001")
        c1 = make_task("t0005", id="t0005", parent="t0001")
        c2 = make_task("t0003", id="t0003", parent="t0001")
        c3 = make_task("t0004", id="t0004", parent="t0001")
        result = compute_tree([root, c1, c2, c3], parent_field="parent")
        assert stems(result) == ["t0001", "t0003", "t0004", "t0005"]

    def test_custom_sort_key(self):
        root = make_task("t0001", id="t0001")
        c1 = make_task("t0002", id="t0002", parent="t0001", status="ready")
        c2 = make_task("t0003", id="t0003", parent="t0001", status="done")
        c3 = make_task("t0004", id="t0004", parent="t0001", status="backlog")
        result = compute_tree(
            [root, c1, c2, c3],
            parent_field="parent",
            sort_key=lambda m: m.frontmatter.get("status", ""),
        )
        # sorted by status: backlog < done < ready
        child_stems = [item.path.stem for item, d, _ in result if d == 1]
        assert child_stems == ["t0004", "t0003", "t0002"]

    def test_sort_key_also_applies_to_roots(self):
        r1 = make_task("t0001", id="t0001", status="z")
        r2 = make_task("t0002", id="t0002", status="a")
        result = compute_tree(
            [r1, r2],
            parent_field="parent",
            sort_key=lambda m: m.frontmatter.get("status", ""),
        )
        assert stems(result) == ["t0002", "t0001"]

    def test_name_fallback_for_non_numbered(self):
        r = make_task("agent-base", id="")
        c = make_task("agent-zoo", id="", parent="agent-base")
        c2 = make_task("agent-alpha", id="", parent="agent-base")
        result = compute_tree([r, c, c2], parent_field="parent")
        assert stems(result) == ["agent-base", "agent-alpha", "agent-zoo"]


# ---------------------------------------------------------------------------
# compute_tree — Case B: orphan out-of-slice
# ---------------------------------------------------------------------------


class TestComputeTreeCaseBOrphanOutOfSlice:
    def test_child_with_missing_parent_in_slice(self):
        child = make_task("t0042", id="t0042", parent="t0036")
        # t0036 is not in the items list — orphan
        result = compute_tree([child], parent_field="parent")
        assert stems(result) == ["t0042"]
        assert depths(result) == [0]
        assert notes(result) == [TreeNote.ORPHAN_OUT_OF_SLICE]

    def test_orphan_appears_after_normal_roots(self):
        normal_root = make_task("t0041", id="t0041")
        child_of_normal = make_task("t0043", id="t0043", parent="t0041")
        orphan = make_task("t0042", id="t0042", parent="t0036")
        result = compute_tree([normal_root, child_of_normal, orphan], parent_field="parent")
        assert stems(result) == ["t0041", "t0043", "t0042"]
        assert notes(result) == [TreeNote.NORMAL, TreeNote.NORMAL, TreeNote.ORPHAN_OUT_OF_SLICE]

    def test_orphans_own_children_are_still_nested(self):
        """An orphan that IS in the slice can still have children."""
        orphan = make_task("t0042", id="t0042", parent="t0036")  # t0036 not in slice
        child_of_orphan = make_task("t0043", id="t0043", parent="t0042")
        result = compute_tree([child_of_orphan, orphan], parent_field="parent")
        assert stems(result) == ["t0042", "t0043"]
        assert depths(result) == [0, 1]
        assert notes(result) == [TreeNote.ORPHAN_OUT_OF_SLICE, TreeNote.NORMAL]


# ---------------------------------------------------------------------------
# compute_tree — Case D: cycle detection
# ---------------------------------------------------------------------------


class TestComputeTreeCaseDCycle:
    def test_two_node_cycle(self, capsys):
        t60 = make_task("t0060", id="t0060", parent="t0061")
        t61 = make_task("t0061", id="t0061", parent="t0060")
        result = compute_tree([t60, t61], parent_field="parent")
        note_vals = notes(result)
        assert TreeNote.CYCLE_BREAK in note_vals

    def test_cycle_break_row_depth(self, capsys):
        t60 = make_task("t0060", id="t0060")
        t61 = make_task("t0061", id="t0061", parent="t0060")
        t60_back = make_task("t0060", id="t0060", parent="t0061")
        # Manually: t0060 has child t0061, t0061's parent points back
        root = make_task("t0060", id="t0060")
        child = make_task("t0061", id="t0061", parent="t0060")
        root.frontmatter["parent"] = "[[t0061]]"  # create cycle: t0060 ↔ t0061

        # Rebuild root with cycle parent
        cyc_root = make_task("t0060", id="t0060", parent="t0061")
        result = compute_tree([cyc_root, child], parent_field="parent")
        # One should be CYCLE_BREAK
        assert any(n == TreeNote.CYCLE_BREAK for _, _, n in result)

    def test_cycle_warning_emitted_to_stderr(self, capsys):
        t60 = make_task("t0060", id="t0060")
        t61 = make_task("t0061", id="t0061", parent="t0060")
        # Make t0060 also point to t0061 to form cycle
        t60_with_parent = ArtifactMeta(
            id="t0060",
            kind="task",
            name="t0060",
            title="t0060",
            status=None,
            tags=[],
            created="2026-01-01",
            path=Path("tasks/t0060.md"),
            frontmatter={"id": "t0060", "kind": "task", "parent": "[[t0061]]"},
        )
        compute_tree([t60_with_parent, t61], parent_field="parent")
        captured = capsys.readouterr()
        assert "warning" in captured.err.lower()
        assert "cycle" in captured.err.lower()

    def test_cycle_warning_emitted_at_most_once(self, capsys):
        """Same cycle edge should only warn once per traversal."""
        t60_with_parent = ArtifactMeta(
            id="t0060",
            kind="task",
            name="t0060",
            title="t0060",
            status=None,
            tags=[],
            created="2026-01-01",
            path=Path("tasks/t0060.md"),
            frontmatter={"id": "t0060", "kind": "task", "parent": "[[t0061]]"},
        )
        t61 = make_task("t0061", id="t0061", parent="t0060")
        compute_tree([t60_with_parent, t61], parent_field="parent")
        captured = capsys.readouterr()
        warning_lines = [l for l in captured.err.splitlines() if "warning" in l.lower()]
        assert len(warning_lines) == 1


# ---------------------------------------------------------------------------
# render_tree — prefix on first column
# ---------------------------------------------------------------------------


class TestRenderTreePrefix:
    def _cols(self):
        return parse_field_specs("id,name")

    def _kind(self):
        return _task_kind()

    def test_root_has_no_prefix(self):
        items = [make_task("t0001", id="t0001")]
        table = render_tree(items, self._cols(), kind_def=self._kind(), parent_field="parent")
        assert isinstance(table, Table)
        cells = _first_col_cells(table)
        assert cells[0] == "t0001"

    def test_child_has_glyph_prefix(self):
        parent = make_task("t0036", id="t0036")
        child = make_task("t0042", id="t0042", parent="t0036")
        table = render_tree([parent, child], self._cols(), kind_def=self._kind(), parent_field="parent")
        cells = _first_col_cells(table)
        child_cell = cells[1]
        assert "└─" in child_cell or "├─" in child_cell
        assert "t0042" in child_cell

    def test_last_child_uses_corner_glyph(self):
        parent = make_task("t0036", id="t0036")
        child = make_task("t0042", id="t0042", parent="t0036")
        table = render_tree([parent, child], self._cols(), kind_def=self._kind(), parent_field="parent")
        cells = _first_col_cells(table)
        assert "└─" in cells[1]

    def test_non_last_child_uses_tee_glyph(self):
        parent = make_task("t0041", id="t0041")
        c1 = make_task("t0043", id="t0043", parent="t0041")
        c2 = make_task("t0044", id="t0044", parent="t0041")
        table = render_tree([parent, c1, c2], self._cols(), kind_def=self._kind(), parent_field="parent")
        cells = _first_col_cells(table)
        assert "├─" in cells[1]  # t0043 is not last
        assert "└─" in cells[2]  # t0044 is last

    def test_prefix_attaches_to_first_column_only(self):
        parent = make_task("t0036", id="t0036")
        child = make_task("t0042", id="t0042", parent="t0036")
        table = render_tree([parent, child], self._cols(), kind_def=self._kind(), parent_field="parent")
        # second column should not have tree glyphs
        name_cells = [str(c) for c in table.columns[1]._cells]
        for cell in name_cells:
            assert "└─" not in cell
            assert "├─" not in cell

    def test_spec_6_5_fixture_renders(self):
        items = [
            make_task("t0036", id="t0036"),
            make_task("t0041", id="t0041"),
            make_task("t0042", id="t0042", parent="t0036"),
            make_task("t0043", id="t0043", parent="t0041"),
            make_task("t0044", id="t0044", parent="t0041"),
            make_task("t0045", id="t0045", parent="t0041"),
            make_task("t0046", id="t0046", parent="t0041"),
        ]
        table = render_tree(items, self._cols(), kind_def=self._kind(), parent_field="parent")
        assert isinstance(table, Table)
        assert table.row_count == 7
        cells = _first_col_cells(table)
        # roots at expected positions
        assert cells[0] == "t0036"   # root, no prefix
        assert cells[2] == "t0041"   # root, no prefix
        # children have glyphs
        assert "└─" in cells[1]      # t0042 is only child of t0036
        assert "├─" in cells[3]      # t0043 not last under t0041
        assert "└─" in cells[6]      # t0046 is last under t0041


# ---------------------------------------------------------------------------
# render_tree — case B/C annotations (filtered-slice and missing parent)
# ---------------------------------------------------------------------------


class TestRenderTreeOrphanAnnotations:
    def _cols(self):
        return parse_field_specs("id,name")

    def _kind(self):
        return _task_kind()

    def test_case_b_with_known_stem(self):
        """Parent in vault but not in items slice → ↑[parent: ref]."""
        child = make_task("t0042", id="t0042", parent="t0036")
        table = render_tree(
            [child],
            self._cols(),
            kind_def=self._kind(),
            parent_field="parent",
            is_known_stem=lambda s: s == "t0036",  # t0036 is in vault
        )
        cells = _first_col_cells(table)
        assert "↑[parent: t0036]" in cells[0]

    def test_case_c_with_known_stem_false(self):
        """Parent not in vault at all → ?[parent: ref]."""
        child = make_task("t0050", id="t0050", parent="t9999")
        table = render_tree(
            [child],
            self._cols(),
            kind_def=self._kind(),
            parent_field="parent",
            is_known_stem=lambda s: False,  # t9999 not in vault
        )
        cells = _first_col_cells(table)
        assert "?[parent: t9999]" in cells[0]

    def test_degraded_without_is_known_stem(self):
        """Without is_known_stem, both B and C render as ?[parent: ref]."""
        child = make_task("t0042", id="t0042", parent="t0036")
        table = render_tree([child], self._cols(), kind_def=self._kind(), parent_field="parent")
        cells = _first_col_cells(table)
        assert "?[parent: t0036]" in cells[0]

    def test_filtered_slice_example(self):
        """§7 worked example: t0036 hidden by filter, t0042 promoted to root."""
        # Only ready tasks are passed (t0036 filtered out, t0042 is ready)
        t0041 = make_task("t0041", id="t0041")
        t0042 = make_task("t0042", id="t0042", parent="t0036", status="ready")
        t0043 = make_task("t0043", id="t0043", parent="t0041")
        t0044 = make_task("t0044", id="t0044", parent="t0041")
        t0045 = make_task("t0045", id="t0045", parent="t0041")
        t0046 = make_task("t0046", id="t0046", parent="t0041")
        items = [t0041, t0042, t0043, t0044, t0045, t0046]
        table = render_tree(
            items,
            self._cols(),
            kind_def=self._kind(),
            parent_field="parent",
            is_known_stem=lambda s: s == "t0036",
        )
        cells = _first_col_cells(table)
        # t0042 has parent t0036 (in vault, filtered out) → ↑ annotation
        orphan_cells = [c for c in cells if "t0042" in c]
        assert len(orphan_cells) == 1
        assert "↑[parent: t0036]" in orphan_cells[0]


# ---------------------------------------------------------------------------
# render_tree — cycle annotation
# ---------------------------------------------------------------------------


class TestRenderTreeCycleAnnotation:
    def _kind(self):
        return _task_kind()

    def test_cycle_break_annotation_in_first_col(self, capsys):
        t60 = ArtifactMeta(
            id="t0060",
            kind="task",
            name="t0060",
            title="t0060",
            status=None,
            tags=[],
            created="2026-01-01",
            path=Path("tasks/t0060.md"),
            frontmatter={"id": "t0060", "kind": "task", "parent": "[[t0061]]"},
        )
        t61 = make_task("t0061", id="t0061", parent="t0060")
        cols = parse_field_specs("id,name")
        table = render_tree([t60, t61], cols, kind_def=self._kind(), parent_field="parent")
        cells = _first_col_cells(table)
        all_text = " ".join(cells)
        assert "↻ cycle" in all_text

    def test_cycle_emits_one_stderr_warning(self, capsys):
        t60 = ArtifactMeta(
            id="t0060",
            kind="task",
            name="t0060",
            title="t0060",
            status=None,
            tags=[],
            created="2026-01-01",
            path=Path("tasks/t0060.md"),
            frontmatter={"id": "t0060", "kind": "task", "parent": "[[t0061]]"},
        )
        t61 = make_task("t0061", id="t0061", parent="t0060")
        cols = parse_field_specs("id,name")
        render_tree([t60, t61], cols, kind_def=self._kind(), parent_field="parent")
        captured = capsys.readouterr()
        lines = [l for l in captured.err.splitlines() if "warning" in l.lower()]
        assert len(lines) == 1


# ---------------------------------------------------------------------------
# render_tree — parent_field resolution
# ---------------------------------------------------------------------------


class TestRenderTreeParentFieldResolution:
    def test_explicit_parent_field_overrides_kind_def(self):
        # Use a custom field name "owner_ref" instead of "parent"
        items = [
            ArtifactMeta(
                id="r",
                kind="task",
                name="r",
                title="r",
                status=None,
                tags=[],
                created="2026-01-01",
                path=Path("tasks/r.md"),
                frontmatter={"id": "r", "kind": "task"},
            ),
            ArtifactMeta(
                id="c",
                kind="task",
                name="c",
                title="c",
                status=None,
                tags=[],
                created="2026-01-01",
                path=Path("tasks/c.md"),
                frontmatter={"id": "c", "kind": "task", "owner_ref": "[[r]]"},
            ),
        ]
        table = render_tree(items, parse_field_specs("id"), parent_field="owner_ref")
        cells = _first_col_cells(table)
        assert "└─" in cells[1] or "├─" in cells[1]

    def test_raises_when_no_parent_field(self):
        """render_tree(parent_field=...) is now required; omitting it is a TypeError."""
        items = [make_task("t0001", id="t0001")]
        with pytest.raises(TypeError):
            render_tree(items, parse_field_specs("id"))


# ---------------------------------------------------------------------------
# LAYOUTS registry
# ---------------------------------------------------------------------------


class TestLayoutsRegistry:
    def test_layouts_has_table_and_tree(self):
        assert "table" in LAYOUTS
        assert "tree" in LAYOUTS

    def test_table_entry_is_render_table(self):
        assert LAYOUTS["table"] is render_table

    def test_tree_entry_is_render_tree(self):
        assert LAYOUTS["tree"] is render_tree

    def test_layouts_is_dict(self):
        assert isinstance(LAYOUTS, dict)

    def test_layout_type_alias_importable(self):
        # Layout is a callable type alias — just check it exists.
        assert Layout is not None


# ---------------------------------------------------------------------------
# ViewsConfig / ViewConfig — layout field
# ---------------------------------------------------------------------------


class TestViewsConfigLayout:
    def _make_base_settings(self, raw: dict):
        from artifacts_os.core.models import ProjectConfig, Settings

        return Settings(
            layout_version=1,
            project=ProjectConfig(name="test"),
            raw=raw,
        )

    def test_view_config_layout_field_default_none(self):
        from artifacts_os.views import ViewConfig

        vc = ViewConfig(columns="id,name")
        assert vc.layout is None

    def test_parse_view_with_valid_layout(self):
        base = self._make_base_settings(
            {"views": {"active": {"columns": "id,name", "layout": "tree"}}}
        )
        from artifacts_os.views import ViewsSettings

        settings = ViewsSettings.from_base(base)
        assert settings.views is not None
        assert settings.views.views["active"].layout == "tree"

    def test_parse_view_with_invalid_layout_raises(self):
        base = self._make_base_settings(
            {"views": {"bad": {"columns": "id,name", "layout": "board"}}}
        )
        from artifacts_os.views import ViewsSettings

        with pytest.raises(ValueError, match="not a registered layout"):
            ViewsSettings.from_base(base)

    def test_default_layouts_parsed(self):
        base = self._make_base_settings({"default_layouts": {"task": "table"}})
        from artifacts_os.views import ViewsSettings

        settings = ViewsSettings.from_base(base)
        assert settings.views is not None
        assert settings.views.default_layouts == {"task": "table"}

    def test_default_layouts_unknown_value_raises(self):
        base = self._make_base_settings({"default_layouts": {"task": "nope"}})
        from artifacts_os.views import ViewsSettings

        with pytest.raises(ValueError, match="not a registered layout"):
            ViewsSettings.from_base(base)

    def test_default_layouts_absent_gives_empty_dict(self):
        base = self._make_base_settings(
            {"views": {"active": {"columns": "id,name"}}}
        )
        from artifacts_os.views import ViewsSettings

        settings = ViewsSettings.from_base(base)
        assert settings.views is not None
        assert settings.views.default_layouts == {}
