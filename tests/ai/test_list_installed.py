"""Tests for list_installed."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.ai import install, list_installed


def test_list_installed_empty(vault: Path) -> None:
    assets = list_installed(vault, tool="claude")
    assert assets == []


def test_list_installed_links(vault: Path) -> None:
    install(vault, mode="link")
    assets = list_installed(vault, tool="claude")
    assert len(assets) >= 3
    for a in assets:
        assert a.mode == "link"
        assert a.source.exists()
    # Commands are name-prefixed; skill is SKILL.md in a namespaced dir
    command_assets = [a for a in assets if a.path.name != "SKILL.md"]
    for a in command_assets:
        assert a.path.name.startswith("artifacts.")


def test_list_installed_copies(vault: Path) -> None:
    install(vault, mode="copy")
    assets = list_installed(vault, tool="claude")
    assert len(assets) >= 3
    for a in assets:
        assert a.mode == "copy"


def test_list_installed_after_uninstall(vault: Path) -> None:
    from artifacts_os.ai import uninstall
    install(vault, mode="link")
    uninstall(vault, tool="claude")
    assets = list_installed(vault, tool="claude")
    assert assets == []
