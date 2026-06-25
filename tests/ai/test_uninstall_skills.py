"""Tests for skill uninstall."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.ai import install, uninstall


def test_uninstall_removes_skill_file(vault: Path) -> None:
    install(vault, mode="link")
    skill_path = vault / ".claude" / "skills" / "artifacts-os" / "SKILL.md"
    assert skill_path.exists()

    uninstall(vault, tool="claude")

    assert not skill_path.exists(), "SKILL.md should be removed after uninstall"
    assert not skill_path.is_symlink(), "SKILL.md symlink should be gone"


def test_uninstall_prunes_empty_namespace_dir(vault: Path) -> None:
    install(vault, mode="link")
    ns_dir = vault / ".claude" / "skills" / "artifacts-os"
    assert ns_dir.is_dir()

    uninstall(vault, tool="claude")

    assert not ns_dir.exists(), "Empty artifacts-os/ dir should be pruned"


def test_uninstall_keeps_namespace_dir_when_foreign_files_present(vault: Path) -> None:
    install(vault, mode="link")
    ns_dir = vault / ".claude" / "skills" / "artifacts-os"
    # Add a foreign file alongside SKILL.md
    foreign = ns_dir / "MY_CUSTOM.md"
    foreign.write_text("# my custom skill note\n")

    uninstall(vault, tool="claude")

    # SKILL.md removed, but dir retained due to foreign file
    assert not (ns_dir / "SKILL.md").exists()
    assert ns_dir.is_dir(), "artifacts-os/ dir should be kept (has foreign files)"
    assert foreign.is_file(), "Foreign file should be untouched"


def test_uninstall_skill_dry_run(vault: Path) -> None:
    install(vault, mode="link")
    skill_path = vault / ".claude" / "skills" / "artifacts-os" / "SKILL.md"
    assert skill_path.exists()

    report = uninstall(vault, tool="claude", dry_run=True)

    skill_removes = [
        a for a in report.actions
        if a.action == "remove" and a.target.name == "SKILL.md"
    ]
    assert len(skill_removes) == 1
    # File still present
    assert skill_path.exists(), "dry_run should not remove the file"


def test_uninstall_no_skills_dir(vault: Path) -> None:
    """Uninstalling on a vault with no skills dir returns no skill actions."""
    report = uninstall(vault, tool="claude")
    skill_removes = [
        a for a in report.actions if a.target.name == "SKILL.md"
    ]
    assert len(skill_removes) == 0
