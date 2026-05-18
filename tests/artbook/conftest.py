"""Shared fixtures for artbook tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml


def _run(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def make_distro_repo(
    root: Path,
    *,
    artbook_yaml: dict | None = None,
    agent_files: dict[str, str] | None = None,
    branch: str = "main",
) -> Path:
    """Create a minimal git repo at *root* suitable for use as a distro.

    ``artbook_yaml`` is the parsed dict to write as artbook.yaml.
    ``agent_files`` maps relative paths (under root) to file content.
    """
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "--initial-branch", branch], root)
    _run(["git", "config", "user.email", "test@test.com"], root)
    _run(["git", "config", "user.name", "Test"], root)

    if agent_files:
        for rel_path, content in agent_files.items():
            dest = root / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)

    if artbook_yaml is not None:
        (root / "artbook.yaml").write_text(yaml.dump(artbook_yaml))

    # Commit everything
    _run(["git", "add", "."], root)
    _run(["git", "commit", "--allow-empty", "-m", "init"], root)

    return root


@pytest.fixture
def distro_repo(tmp_path: Path) -> Path:
    """A minimal distro repo with one 'agents' book (directory mode, D20, v2 schema)."""
    root = tmp_path / "distro"
    return make_distro_repo(
        root,
        artbook_yaml={
            "version": 1,
            "distro": {"name": "test-distro", "description": "Unit test distro."},
            "books": [
                {
                    "name": "agents",
                    "src": "agents/",
                    "dest": "artifacts/agents/",
                    "promote": ".claude/agents/",
                    "description": "Test agents.",
                }
            ],
        },
        agent_files={
            "agents/architect.md": "# Architect\nAgent body.",
            "agents/developer.md": "# Developer\nAgent body.",
            "agents/README.md": "# README",  # should be excluded by D20
        },
    )


@pytest.fixture
def distro_repo_allowlist(tmp_path: Path) -> Path:
    """A distro repo with an explicit files allowlist (D18, v2 schema)."""
    root = tmp_path / "distro-allowlist"
    return make_distro_repo(
        root,
        artbook_yaml={
            "version": 1,
            "distro": {"name": "test-distro"},
            "books": [
                {
                    "name": "agents",
                    "src": "agents/",
                    "dest": "artifacts/agents/",
                    "promote": ".claude/agents/",
                    "files": ["architect.md"],
                }
            ],
        },
        agent_files={
            "agents/architect.md": "# Architect",
            "agents/developer.md": "# Developer",  # not in allowlist
        },
    )


@pytest.fixture
def clone_root(tmp_path: Path, distro_repo: Path) -> Path:
    """A shallow clone of the distro_repo fixture, ready for pull_book."""
    dest = tmp_path / "clone"
    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            "main",
            "--single-branch",
            str(distro_repo),
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    return dest


@pytest.fixture
def vault_root(tmp_path: Path) -> Path:
    """A minimal vault root directory."""
    root = tmp_path / "vault"
    root.mkdir()
    (root / "artifacts.yaml").write_text(
        "layout_version: 1\nproject:\n  name: test-project\n"
    )
    return root
