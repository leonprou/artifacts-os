"""Tests for release-changelog skill migration.

Covers spec §6 property groups:
- §6.1  Layer isolation
- §6.6  Migration / orphan pruning

The release-changelog skill was relocated out of artifacts-os (it is
openstation-specific). These tests verify layer isolation is preserved
and that the orphan-pruning mechanism handles stale artifacts-release
symlinks left by earlier package versions.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from artifacts_os.ai import install, list_installed, uninstall


# ---------------------------------------------------------------------------
# §6.1 — Layer isolation
# ---------------------------------------------------------------------------

def _dir_hash(directory: Path) -> str:
    """Stable content hash of a directory tree (filenames + contents)."""
    h = hashlib.sha256()
    if not directory.exists():
        h.update(b"<absent>")
        return h.hexdigest()
    for p in sorted(directory.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(directory)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def test_install_does_not_write_to_tasks_dir(vault: Path) -> None:
    """§6.1 — install() must not modify artifacts/tasks/."""
    tasks_dir = vault / "artifacts" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    # Seed one task file
    (tasks_dir / "t0001-example.md").write_text("---\nid: t0001\n---\n# Example\n")
    before = _dir_hash(tasks_dir)

    install(vault, mode="link")

    assert _dir_hash(tasks_dir) == before, "install() must not write to artifacts/tasks/"


def test_install_does_not_write_to_log_dir(vault: Path) -> None:
    """§6.1 — install() must not modify artifacts/log/."""
    log_dir = vault / "artifacts" / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "operations.jsonl").write_text('{"op":"init"}\n')
    before = _dir_hash(log_dir)

    install(vault, mode="link")

    assert _dir_hash(log_dir) == before, "install() must not write to artifacts/log/"


def test_uninstall_does_not_write_to_tasks_dir(vault: Path) -> None:
    """§6.1 — uninstall() must not modify artifacts/tasks/."""
    tasks_dir = vault / "artifacts" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "t0001-example.md").write_text("---\nid: t0001\n---\n# Example\n")
    install(vault, mode="link")
    before = _dir_hash(tasks_dir)

    uninstall(vault, tool="claude")

    assert _dir_hash(tasks_dir) == before, "uninstall() must not write to artifacts/tasks/"


# ---------------------------------------------------------------------------
# release-changelog relocated — not installed from artifacts-os
# ---------------------------------------------------------------------------

def test_release_changelog_not_installed_from_package(vault: Path) -> None:
    """release-changelog was relocated out of artifacts-os; install() must not add it."""
    install(vault, mode="link")
    assets = list_installed(vault, tool="claude")
    ns_names = {a.path.parent.name for a in assets if a.path.name == "SKILL.md"}
    assert "release-changelog" not in ns_names, (
        "release-changelog should not be installed by artifacts-os (skill relocated)"
    )


def test_list_installed_does_not_report_artifacts_release(vault: Path) -> None:
    """list_installed() must not report artifacts-release (removed from package)."""
    install(vault, mode="link")
    assets = list_installed(vault, tool="claude")
    ns_names = {a.path.parent.name for a in assets if a.path.name == "SKILL.md"}
    assert "artifacts-release" not in ns_names, (
        "artifacts-release should not appear in listed skills after migration"
    )


# ---------------------------------------------------------------------------
# §6.6 — Migration: orphan artifacts-release pruning
# ---------------------------------------------------------------------------

def test_orphan_artifacts_release_pruned_on_install(vault: Path) -> None:
    """§6.6 — A stale artifacts-release symlink is removed when install() is run."""
    # Simulate a vault that was installed before the migration: create a broken
    # symlink at .claude/skills/artifacts-release/SKILL.md pointing to a
    # (now-deleted) package source.
    orphan_dir = vault / ".claude" / "skills" / "artifacts-release"
    orphan_dir.mkdir(parents=True)
    orphan_symlink = orphan_dir / "SKILL.md"
    # Point to a non-existent path (simulates the deleted artifacts-release source)
    os.symlink("/nonexistent/package/artifacts-release/SKILL.md", orphan_symlink)
    assert orphan_symlink.is_symlink()
    assert not orphan_symlink.exists()  # broken

    install(vault, mode="link")

    assert not orphan_symlink.is_symlink(), (
        "Orphaned artifacts-release SKILL.md symlink should be pruned on install"
    )


def test_orphan_artifacts_release_dir_pruned_when_empty(vault: Path) -> None:
    """§6.6 — The now-empty artifacts-release/ directory is removed after pruning."""
    orphan_dir = vault / ".claude" / "skills" / "artifacts-release"
    orphan_dir.mkdir(parents=True)
    orphan_symlink = orphan_dir / "SKILL.md"
    os.symlink("/nonexistent/source/SKILL.md", orphan_symlink)

    install(vault, mode="link")

    assert not orphan_dir.exists(), (
        "Empty artifacts-release/ directory should be pruned after symlink removal"
    )


def test_orphan_pruning_dry_run_does_not_remove(vault: Path) -> None:
    """§6.6 — Orphan pruning with dry_run=True plans but does not write."""
    orphan_dir = vault / ".claude" / "skills" / "artifacts-release"
    orphan_dir.mkdir(parents=True)
    orphan_symlink = orphan_dir / "SKILL.md"
    os.symlink("/nonexistent/source/SKILL.md", orphan_symlink)

    report = install(vault, mode="link", dry_run=True)

    # Symlink must still be present
    assert orphan_symlink.is_symlink(), "dry_run must not remove the orphan symlink"

    orphan_actions = [
        a for a in report.actions
        if a.action == "remove" and "orphan" in a.reason
    ]
    assert len(orphan_actions) == 1


