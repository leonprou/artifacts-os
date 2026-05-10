"""Tests for cli list command."""

import json
import pytest

from artifacts_os.cli import main


def test_list_quiet_empty(vault):
    """Empty vault returns 0 with no output."""
    main(["list", "-q"])  # no SystemExit means code 0


def test_list_quiet_shows_names(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"})
    write_artifact(vault, "tasks", "t0002-add-feature.md",
                   {"kind": "task", "id": "t0002", "name": "t0002-add-feature", "status": "done"})

    main(["list", "-q"])
    out = capsys.readouterr().out
    lines = out.strip().splitlines()
    assert "t0001-fix-bug" in lines
    assert "t0002-add-feature" in lines


def test_list_json_output(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"})

    main(["list", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "t0001-fix-bug"


def test_list_kind_filter(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"})
    write_artifact(vault, "agents", "researcher.md",
                   {"kind": "agent", "id": "researcher", "name": "researcher"})

    main(["list", "--kind", "task", "-q"])
    out = capsys.readouterr().out
    assert "t0001-fix-bug" in out
    assert "researcher" not in out


def test_list_status_filter(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"})
    write_artifact(vault, "tasks", "t0002-done.md",
                   {"kind": "task", "id": "t0002", "name": "t0002-done", "status": "done"})

    main(["list", "--status", "ready", "-q"])
    out = capsys.readouterr().out
    assert "t0001-fix-bug" in out
    assert "t0002-done" not in out


def test_list_fields(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"})

    main(["list", "--fields", "name,status", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data[0]["status"] == "ready"


def test_list_not_in_project(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["list"])
    assert exc.value.code == 2
    assert "not in an artifacts-os vault" in capsys.readouterr().err
