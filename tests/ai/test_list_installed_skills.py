"""Tests for list_installed covering skills."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.ai import install, list_installed, uninstall


def test_list_installed_includes_skill_link(vault: Path) -> None:
    install(vault, mode="link")
    assets = list_installed(vault, tool="claude")

    skill_assets = [a for a in assets if a.path.name == "SKILL.md"]
    assert len(skill_assets) == 1
    sa = skill_assets[0]
    assert sa.mode == "link"
    assert sa.source.exists()
    assert "artifacts_os" in str(sa.source)


def test_list_installed_includes_skill_copy(vault: Path) -> None:
    install(vault, mode="copy")
    assets = list_installed(vault, tool="claude")

    skill_assets = [a for a in assets if a.path.name == "SKILL.md"]
    assert len(skill_assets) == 1
    assert skill_assets[0].mode == "copy"


def test_list_installed_skill_alongside_commands(vault: Path) -> None:
    install(vault, mode="link")
    assets = list_installed(vault, tool="claude")

    command_assets = [a for a in assets if a.path.name != "SKILL.md"]
    skill_assets = [a for a in assets if a.path.name == "SKILL.md"]

    assert len(command_assets) >= 3, "Should report commands"
    assert len(skill_assets) == 1, "Should report the skill"


def test_list_installed_skill_removed_after_uninstall(vault: Path) -> None:
    install(vault, mode="link")
    uninstall(vault, tool="claude")
    assets = list_installed(vault, tool="claude")
    skill_assets = [a for a in assets if a.path.name == "SKILL.md"]
    assert len(skill_assets) == 0
