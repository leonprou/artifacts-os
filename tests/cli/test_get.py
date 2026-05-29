"""Tests for cli get command (t0189)."""

import json

import pytest

from artifacts_os.cli import main
from artifacts_os.core import frontmatter as _fm


def test_get_single_property(vault, write_artifact, capsys):
    """Happy path: prints the property value."""
    write_artifact(vault, "tasks", "t0001-my-task.md",
                   {"kind": "task", "id": "t0001", "name": "my-task", "status": "ready"})

    main(["get", "t0001", "status"])
    out = capsys.readouterr().out.strip()
    assert out == "ready"


def test_get_single_property_json(vault, write_artifact, capsys):
    """--json returns {property, value} object."""
    write_artifact(vault, "tasks", "t0001-my-task.md",
                   {"kind": "task", "id": "t0001", "name": "my-task", "status": "done"})

    main(["get", "t0001", "status", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data == {"property": "status", "value": "done"}


def test_get_all_properties_no_arg(vault, write_artifact, capsys):
    """No property arg: prints all frontmatter fields as a table (no body)."""
    write_artifact(vault, "tasks", "t0001-my-task.md",
                   {"kind": "task", "id": "t0001", "name": "my-task", "status": "ready",
                    "assignee": "alice"})

    main(["get", "t0001"])
    out = capsys.readouterr().out
    # Should include the property names
    assert "status" in out
    assert "assignee" in out
    # Should NOT include body (no body in this artifact anyway, but ensure fm keys are there)
    assert "kind" in out


def test_get_all_properties_json(vault, write_artifact, capsys):
    """No property + --json returns full frontmatter JSON."""
    write_artifact(vault, "tasks", "t0001-my-task.md",
                   {"kind": "task", "id": "t0001", "name": "my-task", "status": "ready"})

    main(["get", "t0001", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "ready"
    assert data["kind"] == "task"


def test_get_unknown_property_exits_2(vault, write_artifact, capsys):
    """Unknown property → exits 2 with error message."""
    write_artifact(vault, "tasks", "t0001-my-task.md",
                   {"kind": "task", "id": "t0001", "name": "my-task", "status": "ready"})

    with pytest.raises(SystemExit) as exc:
        main(["get", "t0001", "nonexistent_prop"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "Unknown property" in err
    assert "nonexistent_prop" in err


def test_get_unknown_ref_exits_3(vault, capsys):
    """Unknown ref → exits 3 with error message."""
    with pytest.raises(SystemExit) as exc:
        main(["get", "t9999", "status"])
    assert exc.value.code == 3
    assert "error:" in capsys.readouterr().err
