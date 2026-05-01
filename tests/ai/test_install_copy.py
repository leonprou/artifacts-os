"""Tests for copy-mode install."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.ai import install


def test_install_copy_creates_real_files(vault: Path) -> None:
    report = install(vault, mode="copy")
    for action in report.actions:
        if action.action == "install-copy":
            assert action.target.is_file()
            assert not action.target.is_symlink()


def test_install_copy_idempotent(vault: Path) -> None:
    install(vault, mode="copy")
    report2 = install(vault, mode="copy")
    skipped = [a for a in report2.actions if a.action == "skip"]
    assert len(skipped) >= 3


def test_install_copy_force_overwrites(vault: Path) -> None:
    install(vault, mode="copy")
    # Corrupt one file
    commands_dir = vault / ".claude" / "commands"
    target = next(commands_dir.glob("artifacts.*.md"))
    original_content = target.read_text()
    target.write_text("# modified by user\n")

    # Without --force: refuses
    report = install(vault, mode="copy")
    refused = [a for a in report.actions if a.action == "refuse"]
    assert len(refused) >= 1

    # The file is still the user-modified version
    assert target.read_text() == "# modified by user\n"

    # With --force: overwrites
    report2 = install(vault, mode="copy", force=True)
    copied = [a for a in report2.actions if a.action == "install-copy"]
    assert len(copied) >= 1
    assert target.read_text() == original_content


def test_install_link_after_copy_refuses_without_force(vault: Path) -> None:
    """copy → link upgrade requires --force."""
    install(vault, mode="copy")
    # Now try link mode without force
    report = install(vault, mode="link")
    refused = [a for a in report.actions if a.action == "refuse"]
    assert len(refused) >= 1


def test_install_link_after_copy_force_succeeds(vault: Path) -> None:
    install(vault, mode="copy")
    report = install(vault, mode="link", force=True)
    replaced = [a for a in report.actions if a.action == "replace-link"]
    assert len(replaced) >= 1
    commands_dir = vault / ".claude" / "commands"
    for f in commands_dir.glob("artifacts.*.md"):
        assert f.is_symlink(), f"{f} should be a symlink after force upgrade"
