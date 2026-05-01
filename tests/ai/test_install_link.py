"""Tests for symlink-mode install."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from artifacts_os.ai import install, list_installed


def test_install_link_creates_symlinks(vault: Path) -> None:
    report = install(vault, mode="link")
    commands_dir = vault / ".claude" / "commands"

    assert commands_dir.is_dir()
    # At least the three shipped commands
    installed = [a for a in report.actions if a.action in ("install-link",)]
    assert len(installed) >= 3
    for action in installed:
        assert action.target.is_symlink(), f"{action.target} is not a symlink"
        assert action.target.resolve().exists(), f"{action.target} symlink is broken"


def test_install_link_idempotent(vault: Path) -> None:
    install(vault, mode="link")
    report2 = install(vault, mode="link")
    skipped = [a for a in report2.actions if a.action == "skip"]
    installed = [a for a in report2.actions if "install" in a.action or "replace" in a.action]
    assert len(skipped) >= 3
    assert len(installed) == 0


def test_install_link_namespace_respected(vault: Path) -> None:
    """Foreign files in commands/ are never touched."""
    commands_dir = vault / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    foreign = commands_dir / "foo.md"
    foreign.write_text("# my custom command\n")

    install(vault, mode="link")

    # Foreign file still exists and is unchanged
    assert foreign.is_file()
    assert foreign.read_text() == "# my custom command\n"


def test_install_link_creates_claude_dir(vault: Path) -> None:
    """If .claude/ doesn't exist, install creates it."""
    assert not (vault / ".claude").exists()
    install(vault, mode="link")
    assert (vault / ".claude" / "commands").is_dir()
