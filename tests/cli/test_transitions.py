"""Tests for cli transitions command (t0189)."""

import json

import pytest

from artifacts_os.cli import main


def test_transitions_all_properties(vault, write_artifact, capsys):
    """Happy path: prints a table of all state-machined properties."""
    write_artifact(vault, "tasks", "t0001-my-task.md",
                   {"kind": "task", "id": "t0001", "name": "my-task", "status": "backlog"})

    main(["transitions", "t0001"])
    out = capsys.readouterr().out
    # status is state-machined in the vault conftest schema
    assert "status" in out
    assert "backlog" in out


def test_transitions_single_property(vault, write_artifact, capsys):
    """Single-property mode prints just that row."""
    write_artifact(vault, "tasks", "t0001-my-task.md",
                   {"kind": "task", "id": "t0001", "name": "my-task", "status": "ready"})

    main(["transitions", "t0001", "status"])
    out = capsys.readouterr().out
    assert "status" in out
    assert "ready" in out


def test_transitions_single_property_json(vault, write_artifact, capsys):
    """Single-property + --json returns the TransitionView JSON."""
    write_artifact(vault, "tasks", "t0001-my-task.md",
                   {"kind": "task", "id": "t0001", "name": "my-task", "status": "ready"})

    main(["transitions", "t0001", "status", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["property"] == "status"
    assert data["current"] == "ready"
    assert "allowed_next" in data
    assert "wildcard_targets" in data
    assert "locked" in data


def test_transitions_all_properties_json(vault, write_artifact, capsys):
    """All-properties + --json returns a dict keyed by property name."""
    write_artifact(vault, "tasks", "t0001-my-task.md",
                   {"kind": "task", "id": "t0001", "name": "my-task", "status": "backlog"})

    main(["transitions", "t0001", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert "status" in data
    assert data["status"]["property"] == "status"


def test_transitions_no_state_machine_exits_2(vault, write_artifact, capsys):
    """Property with no state machine exits 2 with 'no state machine declared' message."""
    write_artifact(vault, "tasks", "t0001-my-task.md",
                   {"kind": "task", "id": "t0001", "name": "my-task", "status": "ready",
                    "assignee": "alice"})

    with pytest.raises(SystemExit) as exc:
        main(["transitions", "t0001", "assignee"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "no state machine declared" in err
    assert "assignee" in err


def test_transitions_unknown_property_exits_2(vault, write_artifact, capsys):
    """A property that isn't even in the schema exits 2."""
    write_artifact(vault, "tasks", "t0001-my-task.md",
                   {"kind": "task", "id": "t0001", "name": "my-task", "status": "ready"})

    with pytest.raises(SystemExit) as exc:
        main(["transitions", "t0001", "completely_unknown_field"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "no state machine declared" in err


def test_transitions_unknown_ref_exits_3(vault, capsys):
    """Unknown ref → exits 3 with error message."""
    with pytest.raises(SystemExit) as exc:
        main(["transitions", "t9999"])
    assert exc.value.code == 3
    assert "error:" in capsys.readouterr().err
