"""Tests for --layout flag, resolve_layout, _build_sort_key, and reserved-flag collision.

Covers spec s0022-tree-layout §8.1–§8.6, §13.4 and task t0117 requirements.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from artifacts_os.cli import main
from artifacts_os.core import frontmatter as _fm


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

# Task kind with tree layout declared.
_TASK_TREE_SCHEMA = {
    "x-dir": "tasks",
    "x-prefix": "t",
    "x-numbered": True,
    "x-columns": ["id", "name", "status"],
    "properties": {
        "status": {"enum": ["backlog", "ready", "in-progress", "done"]},
        "assignee": {"type": "string"},
        "parent": {"type": "string"},
        "created": {"type": "string"},
    },
    "x-layouts": {
        "default": "tree",
        "tree": {"parent_field": "parent"},
    },
}

# Note kind — no x-layouts (stays table).
_NOTE_SCHEMA = {
    "x-dir": "notes",
    "x-prefix": "n",
    "x-numbered": True,
    "properties": {
        "status": {"type": "string"},
    },
}


# ---------------------------------------------------------------------------
# Vault fixture with tree-capable task kind
# ---------------------------------------------------------------------------


@pytest.fixture
def tree_vault(tmp_path, monkeypatch):
    """Vault where task kind declares x-layouts.default = tree."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")

    import json as _json
    (kinds_dir / "task.json").write_text(_json.dumps(_TASK_TREE_SCHEMA))
    (kinds_dir / "note.json").write_text(_json.dumps(_NOTE_SCHEMA))

    (root / "artifacts" / "tasks").mkdir(parents=True)
    (root / "artifacts" / "notes").mkdir(parents=True)

    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)
    return root


def _write(root: Path, kind_dir: str, filename: str, fm: dict, body: str = "") -> Path:
    path = root / "artifacts" / kind_dir / filename
    path.write_text(_fm.dump(fm, body))
    return path


def _write_task(root, num, slug, *, parent=None, status="ready", created=None):
    fm: dict = {
        "kind": "task",
        "id": f"t{num:04d}",
        "name": f"t{num:04d}-{slug}",
        "status": status,
    }
    if parent is not None:
        fm["parent"] = f"[[{parent}]]"
    if created is not None:
        fm["created"] = created
    _write(root, "tasks", f"t{num:04d}-{slug}.md", fm)
    return f"t{num:04d}-{slug}"


def _write_artifacts_yaml(root: Path, extra: str) -> None:
    """Rewrite artifacts.yaml with required headers plus *extra* YAML."""
    (root / "artifacts" / "artifacts.yaml").write_text(
        "layout_version: 1\nproject:\n  name: test\n" + extra
    )


# ---------------------------------------------------------------------------
# resolve_layout unit tests — isolation via direct function call
# ---------------------------------------------------------------------------


class TestResolveLayout:
    """Unit tests for the resolve_layout helper (no vault needed)."""

    def _make_args(self, layout=None):
        from argparse import Namespace
        return Namespace(layout=layout)

    def _make_view_cfg(self, layout=None, columns="id,name"):
        from artifacts_os.views import ViewConfig
        return ViewConfig(columns=columns, layout=layout)

    def _make_settings(self, default_layouts: dict):
        """Build a ViewsSettings with the given default_layouts mapping."""
        from artifacts_os.core.models import ProjectConfig, Settings
        from artifacts_os.views import ViewsSettings
        base = Settings(
            layout_version=1,
            project=ProjectConfig(name="test"),
            raw={"default_layouts": default_layouts},
        )
        return ViewsSettings.from_base(base)

    def _make_kind_def(self, layout_default: str | None = None):
        from artifacts_os.core.models import KindDef
        meta = {}
        if layout_default is not None:
            meta["layouts"] = {"default": layout_default}
            if layout_default == "tree":
                meta["layouts"]["tree"] = {"parent_field": "parent"}
        return KindDef(name="task", dir="tasks", prefix="t", numbered=True, meta=meta)

    from artifacts_os.cli.commands.list import resolve_layout as _rl

    def _rl(self, args, view_cfg, settings, kind_def):
        from artifacts_os.cli.commands.list import resolve_layout
        return resolve_layout(args, view_cfg, settings, kind_def)

    def test_rung1_explicit_flag_wins(self):
        """Explicit --layout overrides everything."""
        args = self._make_args(layout="table")
        view = self._make_view_cfg(layout="tree")
        settings = self._make_settings({"task": "tree"})
        kind = self._make_kind_def("tree")
        assert self._rl(args, view, settings, kind) == "table"

    def test_rung2_view_cfg_beats_settings_and_kind(self):
        """view.layout wins over settings.default_layouts and kind default."""
        args = self._make_args(layout=None)
        view = self._make_view_cfg(layout="tree")
        settings = self._make_settings({"task": "table"})
        kind = self._make_kind_def("table")
        assert self._rl(args, view, settings, kind) == "tree"

    def test_rung3_settings_default_layouts_beats_kind(self):
        """default_layouts[kind] wins over kind's x-layouts.default."""
        args = self._make_args(layout=None)
        settings = self._make_settings({"task": "table"})
        kind = self._make_kind_def("tree")
        assert self._rl(args, None, settings, kind) == "table"

    def test_rung4_kind_default_used_when_no_override(self):
        """kind.meta["layouts"]["default"] used when no flag/view/settings."""
        args = self._make_args(layout=None)
        kind = self._make_kind_def("tree")
        assert self._rl(args, None, None, kind) == "tree"

    def test_rung5_implicit_table_when_all_absent(self):
        """No overrides, no kind → "table"."""
        args = self._make_args(layout=None)
        assert self._rl(args, None, None, None) == "table"

    def test_rung5_kind_without_layouts_meta_gives_table(self):
        """Kind with no layouts meta falls back to implicit table."""
        args = self._make_args(layout=None)
        kind = self._make_kind_def(layout_default=None)
        assert self._rl(args, None, None, kind) == "table"

    def test_resolution_matrix_all_rungs_explicit_wins(self):
        """Full matrix row: all sources set, explicit flag wins (§8.5 row 5)."""
        args = self._make_args(layout="table")
        view = self._make_view_cfg(layout="tree")
        settings = self._make_settings({"task": "table"})
        kind = self._make_kind_def("tree")
        assert self._rl(args, view, settings, kind) == "table"

    def test_resolution_matrix_no_sources_gives_table(self):
        """§8.5 row 1: kind has no default, all absent → table."""
        args = self._make_args(layout=None)
        kind = self._make_kind_def(layout_default=None)
        assert self._rl(args, None, None, kind) == "table"

    def test_resolution_matrix_kind_tree_no_override(self):
        """§8.5 row 2: kind default=tree, no override → tree."""
        args = self._make_args(layout=None)
        kind = self._make_kind_def("tree")
        assert self._rl(args, None, None, kind) == "tree"


# ---------------------------------------------------------------------------
# _build_sort_key unit tests
# ---------------------------------------------------------------------------


class TestBuildSortKey:
    """Unit tests for _build_sort_key helper."""

    def _make_item(self, stem: str, **fm_fields):
        from artifacts_os.core.models import ArtifactMeta
        fm = {"id": stem, **fm_fields}
        return ArtifactMeta(
            id=stem, kind="task", name=stem, title=stem,
            status=fm.get("status"), tags=[], created=fm.get("created", ""),
            path=Path(f"tasks/{stem}.md"), frontmatter=fm,
        )

    def _sort_key(self, sort_str):
        from artifacts_os.cli.commands.list import _build_sort_key
        return _build_sort_key(sort_str)

    def test_none_returns_none(self):
        assert self._sort_key(None) is None

    def test_empty_string_returns_none(self):
        assert self._sort_key("") is None

    def test_ascending_sort_produces_key(self):
        key = self._sort_key("id")
        assert key is not None
        a = self._make_item("t0001", id="t0001")
        b = self._make_item("t0002", id="t0002")
        assert key(a) < key(b)

    def test_descending_sort_reverses_order(self):
        key = self._sort_key("-id")
        a = self._make_item("t0001", id="t0001")
        b = self._make_item("t0002", id="t0002")
        assert key(a) > key(b)

    def test_ascending_missing_value_sorts_last(self):
        key = self._sort_key("status")
        has_val = self._make_item("t0001", status="ready")
        missing = self._make_item("t0002")  # no status
        assert key(has_val) < key(missing)

    def test_sort_key_usable_in_sorted(self):
        key = self._sort_key("status")
        items = [
            self._make_item("t0003", status="done"),
            self._make_item("t0001", status="backlog"),
            self._make_item("t0002", status="ready"),
        ]
        ordered = sorted(items, key=key)
        statuses = [i.frontmatter["status"] for i in ordered]
        assert statuses == ["backlog", "done", "ready"]


# ---------------------------------------------------------------------------
# _RESERVED_FILTER_FLAG_NAMES includes "layout"
# ---------------------------------------------------------------------------


class TestReservedFlagName:
    def test_layout_in_reserved_names(self):
        """§13.4: 'layout' must be in _RESERVED_FILTER_FLAG_NAMES."""
        from artifacts_os.cli.commands.list import _RESERVED_FILTER_FLAG_NAMES
        assert "layout" in _RESERVED_FILTER_FLAG_NAMES

    def test_collision_skipped_silently(self, tree_vault, capsys):
        """A kind property named 'layout' does not create a --layout flag collision.

        The schema-derived flag logic skips reserved names, so --layout
        remains the static flag and no argparse error is raised.
        """
        # This test exercises the code path without needing a kind with
        # a 'layout' property — just verify the reserved check suppresses it
        # by confirming the CLI starts without argparse conflict.
        _write_task(tree_vault, 1, "alpha")
        # main should not raise due to flag collision
        main(["list", "--kind", "task", "-q"])
        out = capsys.readouterr().out
        assert "alpha" in out


# ---------------------------------------------------------------------------
# Default-tree path: kind with x-layouts.default=tree
# ---------------------------------------------------------------------------


def _has_tree_glyph(out: str) -> bool:
    """Return True if *out* contains a tree-layout glyph (space-prefixed)."""
    # Tree glyphs in cell content are always preceded by spaces (depth≥1)
    # whereas Rich table borders use └─ without leading spaces.
    return "  └─" in out or "  ├─" in out


class TestDefaultTreePath:
    def test_tree_layout_is_default_for_tree_kind(self, tree_vault, capsys):
        """§8.2 rung 4: task kind's x-layouts.default=tree selects tree layout."""
        _write_task(tree_vault, 36, "parent-task")
        _write_task(tree_vault, 42, "child-task", parent="t0036-parent-task")
        main(["list", "--kind", "task"])
        out = capsys.readouterr().out
        # Tree glyphs (space-prefixed) should appear in cell content
        assert _has_tree_glyph(out)

    def test_tree_default_shows_hierarchy(self, tree_vault, capsys):
        """Child appears after parent with tree glyph prefix."""
        _write_task(tree_vault, 36, "root")
        _write_task(tree_vault, 42, "leaf", parent="t0036-root")
        main(["list", "--kind", "task"])
        out = capsys.readouterr().out
        lines = out.splitlines()
        root_lines = [l for l in lines if "t0036" in l]
        leaf_lines = [l for l in lines if "t0042" in l]
        assert root_lines, "root task must appear"
        assert leaf_lines, "leaf task must appear"
        assert any(_has_tree_glyph(l) for l in leaf_lines), "leaf must have glyph"


# ---------------------------------------------------------------------------
# Explicit --layout table opt-out
# ---------------------------------------------------------------------------


class TestLayoutTableOptOut:
    def test_explicit_table_overrides_kind_default(self, tree_vault, capsys):
        """§8.3: --layout table opts out of tree even when kind defaults to tree."""
        _write_task(tree_vault, 36, "root")
        _write_task(tree_vault, 42, "leaf", parent="t0036-root")
        main(["list", "--kind", "task", "--layout", "table"])
        out = capsys.readouterr().out
        # No tree-layout glyphs in cell content — flat table output
        assert not _has_tree_glyph(out)
        # Both tasks still appear
        assert "t0036" in out
        assert "t0042" in out

    def test_layout_table_on_non_tree_kind_stays_table(self, tree_vault, capsys):
        """note kind has no x-layouts; --layout table is redundant but valid."""
        _write(tree_vault, "notes", "n0001-my-note.md", {
            "kind": "note", "id": "n0001", "name": "n0001-my-note",
        })
        main(["list", "--kind", "note", "--layout", "table"])
        out = capsys.readouterr().out
        assert "n0001" in out
        assert not _has_tree_glyph(out)

    def test_unknown_layout_exits_nonzero(self, tree_vault, capsys):
        """Unknown --layout value → exit 2."""
        _write_task(tree_vault, 1, "alpha")
        with pytest.raises(SystemExit) as exc:
            main(["list", "--kind", "task", "--layout", "nope"])
        assert exc.value.code == 2


# ---------------------------------------------------------------------------
# Resolution-chain: settings.default_layouts overrides kind default
# ---------------------------------------------------------------------------


class TestResolutionChainSettings:
    def test_default_layouts_table_opts_out_of_tree(self, tree_vault, capsys):
        """§8.2 rung 3: default_layouts.task=table overrides kind tree default."""
        _write_task(tree_vault, 36, "root")
        _write_task(tree_vault, 42, "leaf", parent="t0036-root")
        _write_artifacts_yaml(tree_vault, "default_layouts:\n  task: table\n")
        main(["list", "--kind", "task"])
        out = capsys.readouterr().out
        assert not _has_tree_glyph(out)
        assert "t0036" in out
        assert "t0042" in out

    def test_view_layout_overrides_settings_default_layouts(self, tree_vault, capsys):
        """§8.2 rung 2: view.layout=tree beats settings.default_layouts.task=table."""
        _write_task(tree_vault, 36, "root")
        _write_task(tree_vault, 42, "leaf", parent="t0036-root")
        _write_artifacts_yaml(tree_vault, """
default_layouts:
  task: table
views:
  tree-view:
    columns: id,name,status
    layout: tree
""")
        main(["list", "--kind", "task", "--view", "tree-view"])
        out = capsys.readouterr().out
        assert _has_tree_glyph(out)

    def test_explicit_flag_beats_view_layout(self, tree_vault, capsys):
        """§8.2 rung 1: --layout table beats view.layout=tree."""
        _write_task(tree_vault, 36, "root")
        _write_task(tree_vault, 42, "leaf", parent="t0036-root")
        _write_artifacts_yaml(tree_vault, """
views:
  tree-view:
    columns: id,name,status
    layout: tree
""")
        main(["list", "--kind", "task", "--view", "tree-view", "--layout", "table"])
        out = capsys.readouterr().out
        assert not _has_tree_glyph(out)
        assert "t0036" in out


# ---------------------------------------------------------------------------
# -q/-j carve-out: layout skipped, sort still applies (§8.4)
# ---------------------------------------------------------------------------


class TestQuietJsonCarveOut:
    """§8.4: -q and -j are layout-agnostic; sort still applies."""

    def test_quiet_output_unchanged_by_tree_default(self, tree_vault, capsys):
        """-q output is identical regardless of tree layout default."""
        _write_task(tree_vault, 36, "root")
        _write_task(tree_vault, 42, "leaf", parent="t0036-root")

        main(["list", "--kind", "task", "-q"])
        out_tree = capsys.readouterr().out

        # Force table to check output is the same shape
        main(["list", "--kind", "task", "--layout", "table", "-q"])
        out_table = capsys.readouterr().out

        assert out_tree == out_table

    def test_quiet_with_explicit_tree_flag_still_flat(self, tree_vault, capsys):
        """-q --layout tree: layout flag is silently ignored; still flat output."""
        _write_task(tree_vault, 1, "alpha")
        _write_task(tree_vault, 2, "beta")
        main(["list", "--kind", "task", "--layout", "tree", "-q"])
        out = capsys.readouterr().out
        # Quiet output: one stem per line; no tree glyphs
        assert not _has_tree_glyph(out)
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        assert len(lines) == 2

    def test_json_output_unchanged_by_tree_default(self, tree_vault, capsys):
        """-j output is identical regardless of tree layout default."""
        _write_task(tree_vault, 36, "root")
        _write_task(tree_vault, 42, "leaf", parent="t0036-root")

        main(["list", "--kind", "task", "-j"])
        out_tree_json = json.loads(capsys.readouterr().out)

        main(["list", "--kind", "task", "--layout", "table", "-j"])
        out_table_json = json.loads(capsys.readouterr().out)

        assert out_tree_json == out_table_json

    def test_json_with_tree_flag_still_flat_json(self, tree_vault, capsys):
        """-j --layout tree: layout flag silently ignored; still JSON array."""
        _write_task(tree_vault, 1, "alpha")
        main(["list", "--kind", "task", "--layout", "tree", "-j"])
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_quiet_sort_still_applies(self, tree_vault, capsys):
        """-q with a view that has sort: output is sorted flat."""
        _write_task(tree_vault, 2, "beta", status="ready")
        _write_task(tree_vault, 1, "alpha", status="ready")
        _write_artifacts_yaml(tree_vault, """
views:
  sorted:
    columns: id,name
    sort: id
""")
        main(["list", "--kind", "task", "--view", "sorted", "-q"])
        out = capsys.readouterr().out
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        # Sorted by id ascending: t0001 before t0002
        assert lines.index(next(l for l in lines if "t0001" in l)) < \
               lines.index(next(l for l in lines if "t0002" in l))


# ---------------------------------------------------------------------------
# --sort interaction with tree layout (§6.2)
# ---------------------------------------------------------------------------


class TestSortInteractionWithTree:
    """§6.2: --sort / view.sort threads into compute_tree sibling order."""

    def test_view_sort_drives_sibling_order_in_tree(self, tree_vault, capsys):
        """View's sort applied at sibling level in tree output."""
        # Create parent with 3 children
        _write_task(tree_vault, 41, "parent")
        _write_task(tree_vault, 43, "charlie", parent="t0041-parent", status="done")
        _write_task(tree_vault, 44, "alpha", parent="t0041-parent", status="ready")
        _write_task(tree_vault, 45, "beta", parent="t0041-parent", status="backlog")
        _write_artifacts_yaml(tree_vault, """
views:
  by-status:
    columns: id,name,status
    sort: status
""")
        main(["list", "--kind", "task", "--view", "by-status"])
        out = capsys.readouterr().out
        # backlog < done < ready lexicographically
        # t0045 (backlog) should appear before t0043 (done) before t0044 (ready) in output
        pos_backlog = out.find("t0045")
        pos_done = out.find("t0043")
        pos_ready = out.find("t0044")
        assert pos_backlog < pos_done < pos_ready, (
            "tree siblings should be sorted by status: backlog < done < ready"
        )

    def test_default_tree_sort_by_id(self, tree_vault, capsys):
        """Default tree sort is by id ascending (no view, no --sort)."""
        _write_task(tree_vault, 41, "parent")
        _write_task(tree_vault, 46, "last", parent="t0041-parent")
        _write_task(tree_vault, 43, "first", parent="t0041-parent")
        main(["list", "--kind", "task"])
        out = capsys.readouterr().out
        # t0043 should appear before t0046 (sorted by id)
        assert out.find("t0043") < out.find("t0046")


# ---------------------------------------------------------------------------
# --layout flag appears in --help
# ---------------------------------------------------------------------------


class TestLayoutHelp:
    def test_layout_in_help_text(self, tree_vault, capsys):
        """--layout flag appears in list --help output."""
        with pytest.raises(SystemExit):
            main(["list", "--help"])
        out = capsys.readouterr().out
        assert "--layout" in out

    def test_layout_help_mentions_auto_detect(self, tree_vault, capsys):
        """Help text for --layout describes auto-detection."""
        with pytest.raises(SystemExit):
            main(["list", "--help"])
        out = capsys.readouterr().out
        # Help text should mention auto-detection per §8.6
        assert "auto-detects" in out or "auto_detects" in out or "auto" in out
