"""Tests for artifacts init + AI install integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.cli import main


def test_init_installs_ai_commands(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    main(["init"])

    commands_dir = tmp_path / ".claude" / "commands"
    md_files = list(commands_dir.glob("artifacts.*.md"))
    assert len(md_files) >= 3, f"Expected AI commands in {commands_dir}, found: {md_files}"
    # Default mode is link
    for f in md_files:
        assert f.is_symlink(), f"{f} should be a symlink"


def test_init_no_ai_skips_install(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    main(["init", "--no-ai"])

    commands_dir = tmp_path / ".claude" / "commands"
    if commands_dir.exists():
        md_files = list(commands_dir.glob("artifacts.*.md"))
        assert len(md_files) == 0
    # No .claude/commands created at all is also fine


def test_init_ai_commands_resolve(tmp_path: Path, monkeypatch) -> None:
    """Installed symlinks resolve to actual package files."""
    monkeypatch.chdir(tmp_path)
    main(["init"])

    commands_dir = tmp_path / ".claude" / "commands"
    for f in commands_dir.glob("artifacts.*.md"):
        assert f.resolve().exists(), f"Broken symlink: {f}"
        content = f.read_text()
        assert len(content) > 10, f"Command file seems empty: {f}"
