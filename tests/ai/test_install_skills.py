"""Tests for symlink-mode skill install."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.ai import install


def test_install_skill_creates_symlink(vault: Path) -> None:
    report = install(vault, mode="link")
    skill_path = vault / ".claude" / "skills" / "artifacts-os" / "SKILL.md"

    assert skill_path.is_symlink(), f"{skill_path} is not a symlink"
    assert skill_path.resolve().exists(), f"{skill_path} symlink is broken"

    skill_actions = [
        a for a in report.actions
        if a.action == "install-link" and a.target.name == "SKILL.md"
    ]
    assert len(skill_actions) == 1


def test_install_skill_resolves_into_package(vault: Path) -> None:
    install(vault, mode="link")
    skill_path = vault / ".claude" / "skills" / "artifacts-os" / "SKILL.md"

    resolved = skill_path.resolve()
    # Must resolve into the artifacts_os package source tree
    assert "artifacts_os" in str(resolved), (
        f"Resolved path {resolved} does not point into the package"
    )
    assert resolved.name == "SKILL.md"


def test_install_skill_idempotent(vault: Path) -> None:
    install(vault, mode="link")
    report2 = install(vault, mode="link")

    skill_skips = [
        a for a in report2.actions
        if a.action == "skip" and a.target.name == "SKILL.md"
    ]
    assert len(skill_skips) == 1

    skill_installs = [
        a for a in report2.actions
        if a.action in ("install-link", "replace-link") and a.target.name == "SKILL.md"
    ]
    assert len(skill_installs) == 0


def test_install_skill_creates_skills_dir(vault: Path) -> None:
    """If .claude/skills/ doesn't exist, install creates it."""
    assert not (vault / ".claude" / "skills").exists()
    install(vault, mode="link")
    assert (vault / ".claude" / "skills" / "artifacts-os").is_dir()
