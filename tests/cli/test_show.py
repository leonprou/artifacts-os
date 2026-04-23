"""Tests for cli show command."""

import json
import pytest

from artifacts_os.cli import main


def test_show_json(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
                   body="# Fix the bug\n\nSome body text.")

    main(["show", "t0001-fix-bug", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["name"] == "t0001-fix-bug"
    assert data["status"] == "ready"
    assert "body" in data


def test_show_by_partial_ref(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"})

    main(["show", "t0001", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["name"] == "t0001-fix-bug"


def test_show_with_kind(vault, write_artifact, capsys):
    write_artifact(vault, "agents", "researcher.md",
                   {"kind": "agent", "id": "researcher", "name": "researcher"})

    main(["show", "researcher", "--kind", "agent", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["name"] == "researcher"


def test_show_not_found_exits_3(vault, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["show", "nonexistent"])
    assert exc.value.code == 3
    assert "error:" in capsys.readouterr().err


def test_show_default_output(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
                   body="# Fix the bug\n\nBody text.")

    main(["show", "t0001-fix-bug"])
    out = capsys.readouterr().out
    assert "t0001-fix-bug" in out
