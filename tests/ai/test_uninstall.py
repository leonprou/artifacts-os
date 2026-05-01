"""Tests for uninstall."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.ai import install, uninstall


def test_uninstall_removes_namespaced_files(vault: Path) -> None:
    install(vault, mode="link")
    commands_dir = vault / ".claude" / "commands"
    assert len(list(commands_dir.glob("artifacts.*.md"))) >= 3

    report = uninstall(vault, tool="claude")
    assert report.removed >= 3
    assert len(list(commands_dir.glob("artifacts.*.md"))) == 0


def test_uninstall_leaves_foreign_files(vault: Path) -> None:
    commands_dir = vault / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    foreign = commands_dir / "openstation.list.md"
    foreign.write_text("# openstation command\n")

    install(vault, mode="link")
    uninstall(vault, tool="claude")

    assert foreign.is_file()
    assert foreign.read_text() == "# openstation command\n"


def test_uninstall_no_commands_dir(vault: Path) -> None:
    """Uninstalling on a vault with no commands dir returns empty report."""
    report = uninstall(vault, tool="claude")
    assert report.removed == 0


def test_uninstall_dry_run(vault: Path) -> None:
    install(vault, mode="link")
    commands_dir = vault / ".claude" / "commands"
    before = set(commands_dir.glob("artifacts.*.md"))

    report = uninstall(vault, tool="claude", dry_run=True)
    assert report.removed >= 3  # planned
    # Nothing actually removed
    after = set(commands_dir.glob("artifacts.*.md"))
    assert before == after
