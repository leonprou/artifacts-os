"""Tests for dry-run mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.ai import install


def test_dry_run_writes_nothing(vault: Path) -> None:
    report = install(vault, mode="link", dry_run=True)
    # Nothing was actually created
    commands_dir = vault / ".claude" / "commands"
    assert not commands_dir.exists() or not any(commands_dir.iterdir())

    # But actions were planned
    planned = [a for a in report.actions if a.action != "skip"]
    assert len(planned) >= 3


def test_dry_run_reports_planned_actions(vault: Path) -> None:
    install(vault, mode="link")  # actually install
    # Dry-run again: should show skip actions
    report = install(vault, mode="link", dry_run=True)
    assert report.skipped >= 3
    assert report.installed == 0


def test_dry_run_no_side_effects(vault: Path) -> None:
    install(vault, mode="copy")  # real install
    # Dry-run link: should plan refuses (copy→link without force), no changes
    report = install(vault, mode="link", dry_run=True)
    refused = [a for a in report.actions if a.action == "refuse"]
    assert len(refused) >= 1
    # Files still copies
    commands_dir = vault / ".claude" / "commands"
    for f in commands_dir.glob("artifacts.*.md"):
        assert not f.is_symlink()
