"""Tests for ``artifacts show`` rejected flag shapes.

``--parent`` was removed from ``show`` in favour of ``list --parent``;
``--view``, ``--status``, ``--children`` remain rejected on ``show``.
"""

import pytest

from artifacts_os.cli import main


def test_show_parent_rejected(vault, write_artifact, capsys):
    """show <ref> --parent exits 2 with 'not valid on show'."""
    write_artifact(vault, "tasks", "t0046-fix.md",
                   {"kind": "task", "id": "t0046", "name": "fix", "status": "ready"})
    with pytest.raises(SystemExit) as exc:
        main(["show", "t0046-fix", "--parent"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "not valid on 'show'" in err


def test_show_view_rejected(vault, write_artifact, capsys):
    """show <ref> --view exits 2 with 'not valid on show' error."""
    write_artifact(vault, "tasks", "t0046-fix.md",
                   {"kind": "task", "id": "t0046", "name": "fix", "status": "ready"})
    with pytest.raises(SystemExit) as exc:
        main(["show", "t0046-fix", "--view", "active"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "not valid on 'show'" in err


def test_show_status_rejected(vault, write_artifact, capsys):
    """show <ref> --status exits 2."""
    write_artifact(vault, "tasks", "t0046-fix.md",
                   {"kind": "task", "id": "t0046", "name": "fix", "status": "ready"})
    with pytest.raises(SystemExit) as exc:
        main(["show", "t0046-fix", "--status", "ready"])
    assert exc.value.code == 2


def test_show_children_rejected(vault, write_artifact, capsys):
    """show <ref> --children exits 2 with 'not valid on show' error."""
    write_artifact(vault, "tasks", "t0046-fix.md",
                   {"kind": "task", "id": "t0046", "name": "fix", "status": "ready"})
    with pytest.raises(SystemExit) as exc:
        main(["show", "t0046-fix", "--children", "t0041"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "not valid on 'show'" in err
