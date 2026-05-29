"""Tests for cli set command (t0189)."""

import pytest

from artifacts_os.cli import main
from artifacts_os.core import frontmatter as _fm


def test_set_state_machined_property(vault, write_artifact, capsys):
    """Happy path: write a state-machined property (status)."""
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "fix-bug", "status": "backlog"})

    main(["set", "t0001", "status", "ready"])
    out = capsys.readouterr().out
    assert "status" in out
    assert "ready" in out

    path = vault / "artifacts" / "tasks" / "t0001-fix-bug.md"
    meta, _ = _fm.parse(path.read_text())
    assert meta["status"] == "ready"


def test_set_free_form_property(vault, write_artifact, capsys):
    """Happy path: set a free-form (non-state-machined) property."""
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "fix-bug", "status": "backlog"})

    main(["set", "t0001", "assignee", "alice"])

    path = vault / "artifacts" / "tasks" / "t0001-fix-bug.md"
    meta, _ = _fm.parse(path.read_text())
    assert meta["assignee"] == "alice"


def test_set_illegal_transition_exits_2(vault, write_artifact, capsys):
    """Illegal transition → exits 2 with D212 message."""
    # The CLI vault's task kind uses a PERMISSIVE transition table in conftest.py
    # (all→all). We need a restrictive kind to test illegal transitions.
    # Use the permissive table but write a kind.json that locks status.
    import json
    from pathlib import Path

    # Overwrite the task kind.json with a restrictive table
    kind_json = vault / "artifacts" / "kinds" / "task" / "kind.json"
    restrictive_schema = {
        "x-dir": "tasks",
        "x-prefix": "t",
        "x-numbered": True,
        "properties": {
            "status": {
                "enum": ["open", "closed"],
                "initial": "open",
                "transitions": {
                    "open": ["closed"],
                    "closed": [],
                },
            }
        },
    }
    kind_json.write_text(json.dumps(restrictive_schema))

    write_artifact(vault, "tasks", "t0001-bug.md",
                   {"kind": "task", "id": "t0001", "name": "bug", "status": "closed"})

    with pytest.raises(SystemExit) as exc:
        main(["set", "t0001", "status", "open"])  # closed → open is illegal
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "Illegal transition" in err
    assert "status" in err


def test_set_unknown_ref_exits_3(vault, capsys):
    """Unknown ref → exits 3."""
    with pytest.raises(SystemExit) as exc:
        main(["set", "t9999", "status", "ready"])
    assert exc.value.code == 3
    assert "error:" in capsys.readouterr().err


def test_set_preserves_body(vault, write_artifact):
    """set does not modify the artifact body."""
    from artifacts_os.core import frontmatter as _fm2

    write_artifact(vault, "tasks", "t0001-task.md",
                   {"kind": "task", "id": "t0001", "name": "task", "status": "backlog"},
                   body="# My Task\n\nKeep this body.\n")

    main(["set", "t0001", "assignee", "bob"])

    path = vault / "artifacts" / "tasks" / "t0001-task.md"
    _, body = _fm2.parse(path.read_text())
    assert "Keep this body." in body
