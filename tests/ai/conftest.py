"""Shared fixtures for ai tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Create a minimal initialised vault at tmp_path/vault."""
    root = tmp_path / "vault"
    (root / "artifacts" / "kinds").mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    (root / "artifacts" / "tasks").mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def vault_with_claude(vault: Path) -> Path:
    """Vault that has a .claude/commands/ directory already."""
    (vault / ".claude" / "commands").mkdir(parents=True)
    return vault
