"""Tests for cli create command."""

import pytest

from artifacts_os.cli import main


def test_create_task(vault, capsys):
    main(["create", "Fix the bug"])
    out = capsys.readouterr().out.strip()
    assert out.startswith("t0001-")
    # Artifact file should exist
    assert (vault / "artifacts" / "tasks" / f"{out}.md").exists()


def test_create_increments(vault, capsys):
    main(["create", "First task"])
    main(["create", "Second task"])
    out = capsys.readouterr().out.strip()
    assert "t0002-" in out


def test_create_with_kind(vault, capsys):
    main(["create", "my-researcher", "--kind", "agent"])
    out = capsys.readouterr().out.strip()
    assert out == "my-researcher"
    assert (vault / "artifacts" / "agents" / "my-researcher.md").exists()


def test_create_with_fields(vault, capsys):
    main(["create", "Fix bug", "--fields", "status=ready", "priority=high"])
    out = capsys.readouterr().out.strip()
    # Verify fields were written
    from artifacts_os.core import frontmatter as _fm
    path = vault / "artifacts" / "tasks" / f"{out}.md"
    meta, _ = _fm.parse(path.read_text())
    assert meta["status"] == "ready"
    assert meta["priority"] == "high"


def test_create_with_body(vault, capsys):
    main(["create", "Task with body", "--body", "Some body content."])
    out = capsys.readouterr().out.strip()
    from artifacts_os.core import frontmatter as _fm
    path = vault / "artifacts" / "tasks" / f"{out}.md"
    _, body = _fm.parse(path.read_text())
    assert "Some body content." in body


def test_create_unknown_kind_exits(vault, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["create", "Thing", "--kind", "unknownkind"])
    assert exc.value.code == 1


def test_create_empty_title_exits_2(vault, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["create", "!!!"])
    assert exc.value.code == 2
    assert "error:" in capsys.readouterr().err
