"""Tests for ``artifacts list --parent <ref>`` flag.

``--parent`` on ``list`` returns the parent of <ref> as a 0-or-1 array,
intended for the workflow ``list --parent <ref> | jq … | xargs show``.
"""

import json
import pytest

from artifacts_os.cli import main


def test_list_parent_returns_parent_record(vault, write_artifact, capsys):
    """list --parent <ref> -j returns a one-element array with the parent."""
    write_artifact(vault, "tasks", "t0041-epic.md",
                   {"kind": "task", "id": "t0041", "name": "epic", "status": "ready"})
    write_artifact(vault, "tasks", "t0046-child.md",
                   {"kind": "task", "id": "t0046", "name": "child", "status": "ready",
                    "parent": "[[t0041-epic]]"})

    main(["list", "--parent", "t0046-child", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "t0041"


def test_list_parent_root_returns_empty(vault, write_artifact, capsys):
    """list --parent on a rootless artifact returns an empty array (exit 0)."""
    write_artifact(vault, "tasks", "t0041-root.md",
                   {"kind": "task", "id": "t0041", "name": "root", "status": "ready"})

    main(["list", "--parent", "t0041-root", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data == []


def test_list_parent_cross_kind(vault, write_artifact, capsys):
    """list --parent resolves cross-kind parent (task → spec)."""
    write_artifact(vault, "specs", "s0012-parent-spec.md",
                   {"kind": "spec", "id": "s0012", "name": "parent-spec",
                    "status": "draft"})
    write_artifact(vault, "tasks", "t0048-impl.md",
                   {"kind": "task", "id": "t0048", "name": "impl", "status": "ready",
                    "parent": "[[s0012-parent-spec]]"})

    main(["list", "--parent", "t0048-impl", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 1
    assert data[0]["id"] == "s0012"
    assert data[0]["kind"] == "spec"


def test_list_parent_quiet(vault, write_artifact, capsys):
    """list --parent <ref> -q prints the parent stem."""
    write_artifact(vault, "tasks", "t0041-epic.md",
                   {"kind": "task", "id": "t0041", "name": "epic", "status": "ready"})
    write_artifact(vault, "tasks", "t0046-child.md",
                   {"kind": "task", "id": "t0046", "name": "child", "status": "ready",
                    "parent": "[[t0041-epic]]"})

    main(["list", "--parent", "t0046-child", "-q"])
    out = capsys.readouterr().out
    lines = [l for l in out.strip().splitlines() if l]
    assert lines == ["t0041-epic"]


def test_list_parent_meta_json(vault, write_artifact, capsys):
    """list --parent --meta -j returns parent's full frontmatter."""
    write_artifact(vault, "tasks", "t0041-epic.md",
                   {"kind": "task", "id": "t0041", "name": "epic", "status": "ready",
                    "assignee": "alice"})
    write_artifact(vault, "tasks", "t0046-child.md",
                   {"kind": "task", "id": "t0046", "name": "child", "status": "ready",
                    "parent": "[[t0041-epic]]"})

    main(["list", "--parent", "t0046-child", "--meta", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 1
    assert data[0]["assignee"] == "alice"


def test_list_parent_unknown_ref_exits_3(vault, capsys):
    """list --parent <unknown> exits 3 (resolution fails)."""
    with pytest.raises(SystemExit) as exc:
        main(["list", "--parent", "t9999-nonexistent"])
    assert exc.value.code == 3


def test_list_parent_broken_wikilink_exits_3(vault, write_artifact, capsys):
    """list --parent on artifact with broken parent link exits 3."""
    write_artifact(vault, "tasks", "t0046-child.md",
                   {"kind": "task", "id": "t0046", "name": "child", "status": "ready",
                    "parent": "[[t0099-deleted]]"})

    with pytest.raises(SystemExit) as exc:
        main(["list", "--parent", "t0046-child"])
    assert exc.value.code == 3
    err = capsys.readouterr().err
    assert "t0099-deleted" in err
