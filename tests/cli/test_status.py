"""Tests for cli status command."""

import pytest

from artifacts_os.cli import main
from artifacts_os.core import frontmatter as _fm


def test_status_update(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"})

    main(["status", "t0001-fix-bug", "done"])
    out = capsys.readouterr().out
    assert "t0001-fix-bug" in out
    assert "done" in out

    # Verify file was updated
    path = vault / "artifacts" / "tasks" / "t0001-fix-bug.md"
    meta, _ = _fm.parse(path.read_text())
    assert meta["status"] == "done"


def test_status_by_partial_ref(vault, write_artifact):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"})

    main(["status", "t0001", "done"])
    path = vault / "artifacts" / "tasks" / "t0001-fix-bug.md"
    meta, _ = _fm.parse(path.read_text())
    assert meta["status"] == "done"


def test_status_invalid_exits_2(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"})

    with pytest.raises(SystemExit) as exc:
        main(["status", "t0001-fix-bug", "invalid-status"])
    assert exc.value.code == 2
    assert "error:" in capsys.readouterr().err


def test_status_not_found_exits_3(vault, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["status", "nonexistent", "done"])
    assert exc.value.code == 3
    assert "error:" in capsys.readouterr().err
