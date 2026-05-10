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


# ---------------------------------------------------------------------------
# --tail [N] (t0139): show the last N results after sorting/filtering.
# ---------------------------------------------------------------------------


def test_list_tail_n(vault, write_artifact, capsys):
    """`--tail N` returns the last N items after sort."""
    for i in range(5):
        write_artifact(vault, "tasks", f"t{i:04d}-task.md",
                       {"kind": "task", "id": f"t{i:04d}",
                        "name": f"t{i:04d}-task", "status": "ready"})

    main(["list", "--kind", "task", "--tail", "2", "-q"])
    lines = capsys.readouterr().out.strip().splitlines()
    # _apply_sort with no sort key preserves discovery order; --tail returns
    # the last 2 items in that order.
    assert len(lines) == 2


def test_list_tail_default_50(vault, write_artifact, capsys):
    """`--tail` (no value) caps at 50 by default."""
    for i in range(60):
        write_artifact(vault, "tasks", f"t{i:04d}-task.md",
                       {"kind": "task", "id": f"t{i:04d}",
                        "name": f"t{i:04d}-task", "status": "ready"})

    main(["list", "--kind", "task", "--tail", "-q"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 50


def test_list_tail_json(vault, write_artifact, capsys):
    """`--tail N` works in JSON mode too."""
    for i in range(4):
        write_artifact(vault, "tasks", f"t{i:04d}-task.md",
                       {"kind": "task", "id": f"t{i:04d}",
                        "name": f"t{i:04d}-task", "status": "ready"})

    main(["list", "--kind", "task", "--tail", "2", "-j"])
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert len(data) == 2


def test_list_tail_zero_returns_empty(vault, write_artifact, capsys):
    """`--tail 0` returns no rows."""
    write_artifact(vault, "tasks", "t0001-task.md",
                   {"kind": "task", "id": "t0001",
                    "name": "t0001-task", "status": "ready"})

    main(["list", "--kind", "task", "--tail", "0", "-q"])
    assert capsys.readouterr().out == ""
