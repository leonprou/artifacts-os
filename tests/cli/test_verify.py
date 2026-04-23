"""Tests for cli verify command."""

import json
import pytest

from artifacts_os.cli import main


_BODY_ALL_CHECKED = """# Verification

- [x] First item done
- [x] Second item done
"""

_BODY_PARTIAL = """# Verification

- [x] First item done
- [ ] Second item pending
"""


def test_verify_all_checked_returns_0(vault, write_artifact):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "done"},
                   body=_BODY_ALL_CHECKED)

    main(["verify", "t0001-fix-bug"])  # no SystemExit = code 0


def test_verify_partial_returns_1(vault, write_artifact):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
                   body=_BODY_PARTIAL)

    with pytest.raises(SystemExit) as exc:
        main(["verify", "t0001-fix-bug"])
    assert exc.value.code == 1


def test_verify_json_output(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
                   body=_BODY_PARTIAL)

    with pytest.raises(SystemExit):
        main(["verify", "t0001-fix-bug", "-j"])

    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["name"] == "t0001-fix-bug"
    assert data["total"] == 2
    assert data["done"] == 1
    assert data["complete"] is False


def test_verify_json_all_checked(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "done"},
                   body=_BODY_ALL_CHECKED)

    main(["verify", "t0001-fix-bug", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["complete"] is True
    assert data["done"] == 2


def test_verify_not_found_exits_3(vault, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["verify", "nonexistent"])
    assert exc.value.code == 3


def test_verify_all_flag(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug"},
                   body=_BODY_ALL_CHECKED)

    main(["verify", "--all", "--kind", "task", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert any(r["name"] == "t0001-fix-bug" for r in data)
