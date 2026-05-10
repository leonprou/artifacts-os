"""Tests for graph traversal primitives: parent() and children().

Spec: s0013-programmatic-cli-access §6, §11.5
"""

import json
from pathlib import Path

import pytest

from artifacts_os.core import Registry, parent, children
from artifacts_os.core.errors import AmbiguousError, NotFoundError
from artifacts_os.core.discover import _unwrap_wikilink


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_KINDS = {
    "task": {
        "x-dir": "tasks",
        "x-prefix": "t",
        "x-numbered": True,
        "properties": {"status": {"enum": ["backlog", "ready", "in-progress", "done"]}},
    },
    "spec": {
        "x-dir": "specs",
        "x-prefix": "s",
        "x-numbered": True,
        "properties": {"status": {"enum": ["draft", "accepted"]}},
    },
}


@pytest.fixture
def vault(tmp_path, monkeypatch):
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts.yaml").write_text("layout_version: 1\n")
    for name, schema in _KINDS.items():
        (kinds_dir / f"{name}.json").write_text(json.dumps(schema))
        kind_dir = schema["x-dir"]
        (root / "artifacts" / kind_dir).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(root)
    return root


def _write(root: Path, kind_dir: str, filename: str, fm: dict, body: str = "") -> Path:
    from artifacts_os.core import frontmatter as _fm
    path = root / "artifacts" / kind_dir / filename
    path.write_text(_fm.dump(fm, body))
    return path


def make_registry(root: Path) -> Registry:
    """Build a Registry that auto-loads kinds from the vault's kinds/ directory."""
    return Registry([], root=root)


# ---------------------------------------------------------------------------
# _unwrap_wikilink helper
# ---------------------------------------------------------------------------

def test_unwrap_wikilink_with_brackets():
    assert _unwrap_wikilink("[[t0036-foo]]") == "t0036-foo"


def test_unwrap_wikilink_without_brackets():
    assert _unwrap_wikilink("t0036-foo") == "t0036-foo"


def test_unwrap_wikilink_bare_id():
    assert _unwrap_wikilink("[[t0036]]") == "t0036"


# ---------------------------------------------------------------------------
# parent()
# ---------------------------------------------------------------------------

def test_parent_with_wikilink(vault):
    """parent() resolves a [[wikilink]] parent field."""
    _write(vault, "tasks", "t0036-alpha.md",
           {"kind": "task", "id": "t0036", "name": "alpha", "status": "ready"})
    _write(vault, "tasks", "t0037-child.md",
           {"kind": "task", "id": "t0037", "name": "child", "status": "ready",
            "parent": "[[t0036-alpha]]"})

    reg = make_registry(vault)
    result = parent(reg, "t0037-child")
    assert result is not None
    assert result.id == "t0036"


def test_parent_returns_none_when_no_parent_field(vault):
    """parent() returns None when artifact has no parent field."""
    _write(vault, "tasks", "t0036-root.md",
           {"kind": "task", "id": "t0036", "name": "root", "status": "ready"})

    reg = make_registry(vault)
    assert parent(reg, "t0036-root") is None


def test_parent_raises_not_found_on_broken_wikilink(vault):
    """parent() raises NotFoundError when wikilink target is missing."""
    _write(vault, "tasks", "t0037-child.md",
           {"kind": "task", "id": "t0037", "name": "child", "status": "ready",
            "parent": "[[t0099-deleted]]"})

    reg = make_registry(vault)
    with pytest.raises(NotFoundError, match="t0099-deleted"):
        parent(reg, "t0037-child")


def test_parent_cross_kind(vault):
    """parent() resolves across kinds (task → spec)."""
    _write(vault, "specs", "s0012-some-spec.md",
           {"kind": "spec", "id": "s0012", "name": "some-spec", "status": "draft"})
    _write(vault, "tasks", "t0048-impl.md",
           {"kind": "task", "id": "t0048", "name": "impl", "status": "ready",
            "parent": "[[s0012-some-spec]]"})

    reg = make_registry(vault)
    result = parent(reg, "t0048-impl")
    assert result is not None
    assert result.id == "s0012"
    assert result.kind == "spec"


def test_parent_bare_ref_no_brackets(vault):
    """parent() resolves even when stored value has no [[…]] brackets."""
    _write(vault, "tasks", "t0036-alpha.md",
           {"kind": "task", "id": "t0036", "name": "alpha", "status": "ready"})
    _write(vault, "tasks", "t0037-child.md",
           {"kind": "task", "id": "t0037", "name": "child", "status": "ready",
            "parent": "t0036-alpha"})

    reg = make_registry(vault)
    result = parent(reg, "t0037-child")
    assert result is not None
    assert result.id == "t0036"


# ---------------------------------------------------------------------------
# children()
# ---------------------------------------------------------------------------

def test_children_returns_list(vault):
    """children() returns all children of an artifact."""
    _write(vault, "tasks", "t0041-parent.md",
           {"kind": "task", "id": "t0041", "name": "parent", "status": "ready"})
    _write(vault, "tasks", "t0042-child1.md",
           {"kind": "task", "id": "t0042", "name": "child1", "status": "ready",
            "parent": "[[t0041-parent]]"})
    _write(vault, "tasks", "t0043-child2.md",
           {"kind": "task", "id": "t0043", "name": "child2", "status": "in-progress",
            "parent": "[[t0041-parent]]"})
    _write(vault, "tasks", "t0044-unrelated.md",
           {"kind": "task", "id": "t0044", "name": "unrelated", "status": "ready"})

    reg = make_registry(vault)
    result = children(reg, "t0041-parent")
    ids = {m.id for m in result}
    assert ids == {"t0042", "t0043"}


def test_children_leaf_returns_empty(vault):
    """children() returns [] for an artifact with no children."""
    _write(vault, "tasks", "t0042-leaf.md",
           {"kind": "task", "id": "t0042", "name": "leaf", "status": "ready"})

    reg = make_registry(vault)
    assert children(reg, "t0042-leaf") == []


def test_children_with_kind_filter(vault):
    """children() with kind= narrows to that kind."""
    _write(vault, "tasks", "t0041-parent.md",
           {"kind": "task", "id": "t0041", "name": "parent", "status": "ready"})
    _write(vault, "tasks", "t0042-task-child.md",
           {"kind": "task", "id": "t0042", "name": "task-child", "status": "ready",
            "parent": "[[t0041-parent]]"})
    _write(vault, "specs", "s0020-spec-child.md",
           {"kind": "spec", "id": "s0020", "name": "spec-child", "status": "draft",
            "parent": "[[t0041-parent]]"})

    reg = make_registry(vault)
    result = children(reg, "t0041-parent", kind="task")
    assert len(result) == 1
    assert result[0].id == "t0042"


def test_children_with_status_filter(vault):
    """children() with status= narrows to that status."""
    _write(vault, "tasks", "t0041-parent.md",
           {"kind": "task", "id": "t0041", "name": "parent", "status": "ready"})
    _write(vault, "tasks", "t0042-ready-child.md",
           {"kind": "task", "id": "t0042", "name": "ready-child", "status": "ready",
            "parent": "[[t0041-parent]]"})
    _write(vault, "tasks", "t0043-done-child.md",
           {"kind": "task", "id": "t0043", "name": "done-child", "status": "done",
            "parent": "[[t0041-parent]]"})

    reg = make_registry(vault)
    result = children(reg, "t0041-parent", status="ready")
    assert len(result) == 1
    assert result[0].id == "t0042"


def test_children_different_ref_forms(vault):
    """children() matches regardless of ref form (t41, t0041, t0041-name, [[…]])."""
    _write(vault, "tasks", "t0041-parent.md",
           {"kind": "task", "id": "t0041", "name": "parent", "status": "ready"})
    # Different ref forms all pointing at t0041:
    _write(vault, "tasks", "t0042-form1.md",
           {"kind": "task", "id": "t0042", "name": "form1", "status": "ready",
            "parent": "[[t0041]]"})
    _write(vault, "tasks", "t0043-form2.md",
           {"kind": "task", "id": "t0043", "name": "form2", "status": "ready",
            "parent": "[[t0041-parent]]"})
    _write(vault, "tasks", "t0044-form3.md",
           {"kind": "task", "id": "t0044", "name": "form3", "status": "ready",
            "parent": "t0041-parent"})

    reg = make_registry(vault)
    result = children(reg, "t0041-parent")
    ids = {m.id for m in result}
    # All three should match.
    assert "t0042" in ids
    assert "t0043" in ids
    assert "t0044" in ids


def test_children_cross_kind_parent(vault):
    """children() of a spec returns mixed-kind children."""
    _write(vault, "specs", "s0012-parent-spec.md",
           {"kind": "spec", "id": "s0012", "name": "parent-spec", "status": "draft"})
    _write(vault, "tasks", "t0048-child.md",
           {"kind": "task", "id": "t0048", "name": "child", "status": "ready",
            "parent": "[[s0012-parent-spec]]"})

    reg = make_registry(vault)
    result = children(reg, "s0012-parent-spec")
    assert len(result) == 1
    assert result[0].id == "t0048"
