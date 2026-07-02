"""Tests for artifacts_os.views public API.

Uses real ArtifactMeta instances constructed directly — no vault needed.
"""

from pathlib import Path

import pytest
from rich.table import Table
from rich.text import Text

from dataclasses import dataclass

from artifacts_os.core.models import ArtifactMeta, ItemMeta, KindDef
from artifacts_os.views import (
    FieldSpec,
    default_columns,
    format_field,
    parse_field_specs,
    render_table,
)


def make_meta(name: str, frontmatter: dict | None = None) -> ArtifactMeta:
    """Build a minimal ArtifactMeta with the given frontmatter."""
    fm = frontmatter or {}
    return ArtifactMeta(
        id=fm.get("id", "t0001"),
        kind=fm.get("kind", "task"),
        name=name,
        title=fm.get("title", name),
        status=fm.get("status", None),
        tags=fm.get("tags", []),
        created=fm.get("created", "2026-01-01"),
        path=Path(f"tasks/{name}.md"),
        frontmatter=fm,
    )


# ---------------------------------------------------------------------------
# parse_field_specs
# ---------------------------------------------------------------------------


class TestParseFieldSpecs:
    def test_plain_key(self):
        assert parse_field_specs("id") == [FieldSpec(key="id", fmt=None, label="id")]

    def test_key_with_format(self):
        assert parse_field_specs("created:date") == [
            FieldSpec(key="created", fmt="date", label="created")
        ]

    def test_key_with_format_and_label(self):
        assert parse_field_specs("created:date as Date") == [
            FieldSpec(key="created", fmt="date", label="Date")
        ]

    def test_multiple_fields(self):
        result = parse_field_specs("id,status,created:date as Date")
        assert result == [
            FieldSpec(key="id", fmt=None, label="id"),
            FieldSpec(key="status", fmt=None, label="status"),
            FieldSpec(key="created", fmt="date", label="Date"),
        ]

    def test_whitespace_tolerance(self):
        result = parse_field_specs(" id , status ")
        assert result == [
            FieldSpec(key="id", fmt=None, label="id"),
            FieldSpec(key="status", fmt=None, label="status"),
        ]

    def test_empty_string_returns_empty(self):
        assert parse_field_specs("") == []


# ---------------------------------------------------------------------------
# format_field
# ---------------------------------------------------------------------------


class TestFormatField:
    def test_date_format_date_only(self):
        assert format_field("2026-04-22", "date") == "2026-04-22"

    def test_date_format_with_time(self):
        assert format_field("2026-04-22T14:30:00", "date") == "2026-04-22"

    def test_datetime_format(self):
        assert format_field("2026-04-22T14:30:00", "datetime") == "2026-04-22 14:30"

    def test_none_fmt_string(self):
        assert format_field("hello", None) == "hello"

    def test_none_fmt_integer(self):
        assert format_field(42, None) == "42"

    def test_none_value_returns_empty(self):
        assert format_field(None, None) == ""

    def test_none_value_with_date_fmt(self):
        assert format_field(None, "date") == ""

    def test_none_value_with_datetime_fmt(self):
        assert format_field(None, "datetime") == ""

    def test_list_value_joined(self):
        assert format_field(["arch"], None) == "arch"

    def test_list_value_multiple_joined(self):
        assert format_field(["pdm", "prd"], None) == "pdm, prd"

    def test_empty_list_returns_empty(self):
        assert format_field([], None) == ""

    def test_list_value_with_date_fmt(self):
        assert format_field(["2026-04-22T14:30:00"], "date") == "2026-04-22"


# ---------------------------------------------------------------------------
# default_columns
# ---------------------------------------------------------------------------


class TestDefaultColumns:
    def test_with_meta_columns(self):
        kd = KindDef(
            name="task",
            dir="tasks",
            prefix="t",
            numbered=True,
            meta={"columns": ["id", "status"]},
        )
        assert default_columns(kd) == [
            FieldSpec(key="id", fmt=None, label="id"),
            FieldSpec(key="status", fmt=None, label="status"),
        ]

    def test_fallback_when_absent(self):
        kd = KindDef(name="task", dir="tasks", prefix="t", numbered=True)
        assert default_columns(kd) == [
            FieldSpec(key="name", fmt=None, label="name"),
            FieldSpec(key="summary", fmt=None, label="summary"),
        ]

    def test_with_format_specs_in_meta(self):
        kd = KindDef(
            name="task",
            dir="tasks",
            prefix="t",
            numbered=True,
            meta={"columns": ["id", "created:date as Date"]},
        )
        assert default_columns(kd) == [
            FieldSpec(key="id", fmt=None, label="id"),
            FieldSpec(key="created", fmt="date", label="Date"),
        ]


# ---------------------------------------------------------------------------
# render_table
# ---------------------------------------------------------------------------


class TestRenderTable:
    _status_colors = {"done": "green", "ready": "cyan"}

    def test_returns_rich_table(self):
        cols = parse_field_specs("id,name")
        items = [make_meta("fix-bug", {"id": "t0001", "name": "fix-bug"})]
        assert isinstance(render_table(items, cols), Table)

    def test_column_headers(self):
        cols = parse_field_specs("id,name")
        items = [make_meta("fix-bug", {"id": "t0001", "name": "fix-bug"})]
        table = render_table(items, cols)
        headers = [col.header for col in table.columns]
        assert headers == ["id", "name"]

    def test_custom_label_in_header(self):
        cols = parse_field_specs("created:date as Created")
        items = [make_meta("task", {"created": "2026-01-01"})]
        table = render_table(items, cols)
        assert table.columns[0].header == "Created"

    def test_row_count(self):
        cols = parse_field_specs("id")
        items = [
            make_meta("a", {"id": "t0001"}),
            make_meta("b", {"id": "t0002"}),
        ]
        table = render_table(items, cols)
        assert table.row_count == 2

    def test_cell_values(self):
        cols = parse_field_specs("id,name")
        items = [make_meta("fix-bug", {"id": "t0001", "name": "fix-bug"})]
        table = render_table(items, cols)
        assert table.columns[0]._cells[0] == "t0001"
        assert table.columns[1]._cells[0] == "fix-bug"

    def test_status_color_applied(self):
        cols = parse_field_specs("id,status")
        items = [make_meta("done-task", {"id": "t0001", "status": "done"})]
        table = render_table(items, cols, status_colors=self._status_colors)
        cell = table.columns[1]._cells[0]
        assert isinstance(cell, Text)
        assert str(cell) == "done"
        assert cell.style == "green"

    def test_status_color_not_applied_without_status_colors(self):
        cols = parse_field_specs("id,status")
        items = [make_meta("done-task", {"id": "t0001", "status": "done"})]
        table = render_table(items, cols)
        cell = table.columns[1]._cells[0]
        assert isinstance(cell, str)
        assert cell == "done"

    def test_unmatched_status_not_colored(self):
        cols = parse_field_specs("status")
        items = [make_meta("task", {"status": "in-progress"})]
        table = render_table(items, cols, status_colors=self._status_colors)
        cell = table.columns[0]._cells[0]
        # "in-progress" not in status_colors → plain string
        assert isinstance(cell, str)
        assert cell == "in-progress"

    def test_missing_field_renders_empty(self):
        cols = parse_field_specs("summary")
        items = [make_meta("task", {})]
        table = render_table(items, cols)
        assert table.columns[0]._cells[0] == ""

    def test_empty_items(self):
        cols = parse_field_specs("id,name")
        table = render_table([], cols)
        assert table.row_count == 0


# ---------------------------------------------------------------------------
# render_table with generic ItemMeta subclass (non-ArtifactMeta)
# ---------------------------------------------------------------------------


class TestRenderTableGenericItemMeta:
    """Verify render_table works with any ItemMeta subclass, not just ArtifactMeta."""

    def _make_row(self, **fields) -> ItemMeta:
        @dataclass
        class BookRow(ItemMeta):
            title: str = ""
            status: str = ""
            author: str = ""

            def cell(self, key: str, default="") -> object:
                return getattr(self, key, default)

        return BookRow(**fields)

    def test_renders_custom_item_meta(self):
        cols = parse_field_specs("title,author")
        items = [self._make_row(title="My Book", author="Alice")]
        table = render_table(items, cols)
        assert isinstance(table, Table)
        assert table.row_count == 1
        assert table.columns[0]._cells[0] == "My Book"
        assert table.columns[1]._cells[0] == "Alice"

    def test_status_colors_applied_to_generic_item(self):
        cols = parse_field_specs("title,status")
        items = [self._make_row(title="My Book", status="published")]
        table = render_table(
            items, cols, status_colors={"published": "bold green"}
        )
        cell = table.columns[1]._cells[0]
        assert isinstance(cell, Text)
        assert str(cell) == "published"
        assert cell.style == "bold green"
