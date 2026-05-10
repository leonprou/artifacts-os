"""Tests for ``artifacts list --children`` flag.

Spec: s0013-programmatic-cli-access §3, §4.1, §5.3, §7, §11.5
"""

import json
from pathlib import Path

import pytest

from artifacts_os.cli import main


def _write_yaml(root: Path, extra: str) -> None:
    base = root / "artifacts.yaml"
    content = "layout_version: 1\nproject:\n  name: test\n" + extra
    base.write_text(content)


# ---------------------------------------------------------------------------
# Basic children enumeration
# ---------------------------------------------------------------------------

def test_list_children_table(vault, write_artifact, capsys):
    """list --children <ref> renders a flat table of direct children."""
    write_artifact(vault, "tasks", "t0041-epic.md",
                   {"kind": "task", "id": "t0041", "name": "epic", "status": "ready"})
    write_artifact(vault, "tasks", "t0042-child.md",
                   {"kind": "task", "id": "t0042", "name": "child", "status": "ready",
                    "parent": "[[t0041-epic]]"})
    write_artifact(vault, "tasks", "t0099-other.md",
                   {"kind": "task", "id": "t0099", "name": "other", "status": "ready"})

    main(["list", "--children", "t0041-epic"])
    out = capsys.readouterr().out
    # The child's name appears; the unrelated task does not.
    assert "child" in out
    assert "other" not in out


def test_list_children_json(vault, write_artifact, capsys):
    """list --children -j returns a JSON array."""
    write_artifact(vault, "tasks", "t0041-epic.md",
                   {"kind": "task", "id": "t0041", "name": "epic", "status": "ready"})
    write_artifact(vault, "tasks", "t0042-child.md",
                   {"kind": "task", "id": "t0042", "name": "child", "status": "ready",
                    "parent": "[[t0041-epic]]"})

    main(["list", "--children", "t0041-epic", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "t0042"


def test_list_children_meta_json(vault, write_artifact, capsys):
    """list --children --meta -j returns full frontmatter dicts."""
    write_artifact(vault, "tasks", "t0041-epic.md",
                   {"kind": "task", "id": "t0041", "name": "epic", "status": "ready"})
    write_artifact(vault, "tasks", "t0042-child.md",
                   {"kind": "task", "id": "t0042", "name": "child", "status": "ready",
                    "assignee": "alice", "parent": "[[t0041-epic]]"})

    main(["list", "--children", "t0041-epic", "--meta", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert data[0]["id"] == "t0042"
    assert data[0]["assignee"] == "alice"


def test_list_children_quiet(vault, write_artifact, capsys):
    """list --children -q prints child stems only."""
    write_artifact(vault, "tasks", "t0041-epic.md",
                   {"kind": "task", "id": "t0041", "name": "epic", "status": "ready"})
    write_artifact(vault, "tasks", "t0042-child.md",
                   {"kind": "task", "id": "t0042", "name": "child", "status": "ready",
                    "parent": "[[t0041-epic]]"})

    main(["list", "--children", "t0041-epic", "-q"])
    out = capsys.readouterr().out
    lines = [l for l in out.strip().splitlines() if l]
    assert lines == ["t0042-child"]


def test_list_children_status_filter(vault, write_artifact, capsys):
    """list --children --status ready intersects children with status filter."""
    write_artifact(vault, "tasks", "t0041-epic.md",
                   {"kind": "task", "id": "t0041", "name": "epic", "status": "ready"})
    write_artifact(vault, "tasks", "t0042-ready.md",
                   {"kind": "task", "id": "t0042", "name": "ready", "status": "ready",
                    "parent": "[[t0041-epic]]"})
    write_artifact(vault, "tasks", "t0043-done.md",
                   {"kind": "task", "id": "t0043", "name": "done", "status": "done",
                    "parent": "[[t0041-epic]]"})

    main(["list", "--children", "t0041-epic", "--status", "ready", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 1
    assert data[0]["id"] == "t0042"


def test_list_children_view_composes(vault, write_artifact, capsys):
    """list --children --view composes view filters with parent predicate."""
    write_artifact(vault, "tasks", "t0041-epic.md",
                   {"kind": "task", "id": "t0041", "name": "epic", "status": "ready"})
    write_artifact(vault, "tasks", "t0042-ready.md",
                   {"kind": "task", "id": "t0042", "name": "ready-child", "status": "ready",
                    "parent": "[[t0041-epic]]"})
    write_artifact(vault, "tasks", "t0043-done.md",
                   {"kind": "task", "id": "t0043", "name": "done-child", "status": "done",
                    "parent": "[[t0041-epic]]"})

    _write_yaml(vault, """
views:
  active:
    columns: id,name,status
    filters:
      status: ready
""")

    main(["list", "--children", "t0041-epic", "--view", "active", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert all(item["status"] == "ready" for item in data)
    ids = {item["id"] for item in data}
    assert "t0042" in ids
    assert "t0043" not in ids


def test_list_children_leaf_empty_exit_0(vault, write_artifact, capsys):
    """list --children <leaf> returns empty result with exit 0."""
    write_artifact(vault, "tasks", "t0042-leaf.md",
                   {"kind": "task", "id": "t0042", "name": "leaf", "status": "ready"})

    # Should not raise SystemExit.
    main(["list", "--children", "t0042-leaf"])
    out, err = capsys.readouterr()
    # No error, no output (empty table suppressed for empty result).
    assert "error:" not in err


def test_list_children_leaf_empty_json(vault, write_artifact, capsys):
    """list --children <leaf> -j returns []."""
    write_artifact(vault, "tasks", "t0042-leaf.md",
                   {"kind": "task", "id": "t0042", "name": "leaf", "status": "ready"})

    main(["list", "--children", "t0042-leaf", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data == []


def test_list_children_unknown_ref_exits_3(vault, capsys):
    """list --children <unknown> exits 3."""
    with pytest.raises(SystemExit) as exc:
        main(["list", "--children", "t9999-nonexistent"])
    assert exc.value.code == 3
    assert "error:" in capsys.readouterr().err


def test_list_children_cross_kind(vault, write_artifact, capsys):
    """list --children <spec> returns mixed-kind children."""
    write_artifact(vault, "specs", "s0012-parent.md",
                   {"kind": "spec", "id": "s0012", "name": "parent", "status": "draft"})
    write_artifact(vault, "tasks", "t0048-child.md",
                   {"kind": "task", "id": "t0048", "name": "child", "status": "ready",
                    "parent": "[[s0012-parent]]"})

    main(["list", "--children", "s0012-parent", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 1
    assert data[0]["id"] == "t0048"


def test_list_parent_now_supported(vault, write_artifact, capsys):
    """list --parent <ref> is valid (replaces show --parent)."""
    write_artifact(vault, "tasks", "t0041-epic.md",
                   {"kind": "task", "id": "t0041", "name": "epic", "status": "ready"})
    write_artifact(vault, "tasks", "t0042-child.md",
                   {"kind": "task", "id": "t0042", "name": "child", "status": "ready",
                    "parent": "[[t0041-epic]]"})
    # Should not raise: list --parent t0042 returns t0041 as a 1-element array.
    main(["list", "--parent", "t0042-child", "-j"])
    out = capsys.readouterr().out
    import json as _json
    assert _json.loads(out)[0]["id"] == "t0041"


def test_list_jq_length(vault, write_artifact, capsys):
    """list --children -j | jq length: count is correct."""
    write_artifact(vault, "tasks", "t0041-epic.md",
                   {"kind": "task", "id": "t0041", "name": "epic", "status": "ready"})
    write_artifact(vault, "tasks", "t0042-c1.md",
                   {"kind": "task", "id": "t0042", "name": "c1", "status": "ready",
                    "parent": "[[t0041-epic]]"})
    write_artifact(vault, "tasks", "t0043-c2.md",
                   {"kind": "task", "id": "t0043", "name": "c2", "status": "ready",
                    "parent": "[[t0041-epic]]"})

    main(["list", "--children", "t0041-epic", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 2
