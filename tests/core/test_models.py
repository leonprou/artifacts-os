"""Tests for core.models — ItemMeta base class and ArtifactMeta subclass."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from artifacts_os.core.models import ArtifactMeta, ItemMeta


# ---------------------------------------------------------------------------
# ItemMeta base class
# ---------------------------------------------------------------------------


class TestItemMeta:
    def test_cell_reads_attribute(self):
        @dataclass
        class RowItem(ItemMeta):
            status: str = "ready"
            name: str = "my-item"

        item = RowItem()
        assert item.cell("status") == "ready"
        assert item.cell("name") == "my-item"

    def test_cell_returns_default_for_missing_attribute(self):
        item = ItemMeta()
        assert item.cell("nonexistent") == ""
        assert item.cell("nonexistent", "fallback") == "fallback"

    def test_cell_default_is_empty_string(self):
        item = ItemMeta()
        assert item.cell("anything") == ""

    def test_artifactmeta_is_subclass(self):
        assert issubclass(ArtifactMeta, ItemMeta)


# ---------------------------------------------------------------------------
# ArtifactMeta.cell — reads from frontmatter
# ---------------------------------------------------------------------------


def _make_artifact_meta(frontmatter: dict) -> ArtifactMeta:
    return ArtifactMeta(
        id="t0001",
        kind="task",
        name="test",
        title="Test",
        status=frontmatter.get("status"),
        tags=[],
        created="2026-01-01",
        path=Path("tasks/test.md"),
        frontmatter=frontmatter,
    )


class TestArtifactMetaCell:
    def test_reads_frontmatter_key(self):
        meta = _make_artifact_meta({"status": "done", "assignee": "alice"})
        assert meta.cell("status") == "done"
        assert meta.cell("assignee") == "alice"

    def test_missing_key_returns_default(self):
        meta = _make_artifact_meta({})
        assert meta.cell("status") == ""
        assert meta.cell("status", "unknown") == "unknown"

    def test_does_not_fall_through_to_attribute(self):
        # frontmatter missing key — should return default, not the attribute value
        meta = _make_artifact_meta({})
        # meta.kind = "task" as attribute, but frontmatter is empty
        assert meta.cell("kind") == ""

    def test_frontmatter_overrides_attribute(self):
        # frontmatter has "kind" = "spec" even though attribute kind = "task"
        meta = _make_artifact_meta({"kind": "spec"})
        assert meta.cell("kind") == "spec"
