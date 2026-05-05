"""Tests for copy-mode skill install."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.ai import install


def test_install_skill_copy_creates_regular_file(vault: Path) -> None:
    install(vault, mode="copy")
    skill_path = vault / ".claude" / "skills" / "artifacts-os" / "SKILL.md"

    assert skill_path.is_file(), f"{skill_path} should exist as a regular file"
    assert not skill_path.is_symlink(), f"{skill_path} should not be a symlink"


def test_install_skill_copy_content_matches_package(vault: Path) -> None:
    import importlib.resources as ir

    install(vault, mode="copy")
    skill_path = vault / ".claude" / "skills" / "artifacts-os" / "SKILL.md"

    pkg_skill = ir.files("artifacts_os.ai.claude.skills.artifacts-os") / "SKILL.md"
    assert skill_path.read_bytes() == Path(str(pkg_skill)).read_bytes()


def test_install_skill_copy_idempotent(vault: Path) -> None:
    install(vault, mode="copy")
    report2 = install(vault, mode="copy")

    skill_skips = [
        a for a in report2.actions
        if a.action == "skip" and a.target.name == "SKILL.md"
    ]
    assert len(skill_skips) == 2
