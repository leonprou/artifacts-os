"""Tests for dry-run mode with skills."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.ai import install


def test_dry_run_skill_writes_nothing(vault: Path) -> None:
    report = install(vault, mode="link", dry_run=True)
    skill_path = vault / ".claude" / "skills" / "artifacts-os" / "SKILL.md"

    assert not skill_path.exists(), "dry_run should not create SKILL.md"
    assert not skill_path.is_symlink(), "dry_run should not create symlink"

    planned = [
        a for a in report.actions
        if a.action == "install-link" and a.target.name == "SKILL.md"
    ]
    assert len(planned) == 2, "dry_run should plan install for both skills"


def test_dry_run_skill_shows_skip_when_already_installed(vault: Path) -> None:
    install(vault, mode="link")  # real install
    report2 = install(vault, mode="link", dry_run=True)

    skill_skips = [
        a for a in report2.actions
        if a.action == "skip" and a.target.name == "SKILL.md"
    ]
    assert len(skill_skips) == 2
    assert report2.installed == 0
