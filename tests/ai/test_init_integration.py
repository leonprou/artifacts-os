"""Tests for artifacts init — AI integration was removed in s0021.

Per s0021 §3 (Non-Goals): `.claude/` symlink tree installation is out of
scope for `artifacts init`. AI commands are no longer installed by init;
`--no-ai` was also removed (it has no meaning when AI install is absent).

These tests verify the updated init behaviour rather than the removed
AI-install behaviour.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.cli import main


def test_init_creates_vault_without_ai_dir(tmp_path: Path, monkeypatch) -> None:
    """Init succeeds and does NOT create .claude/ — AI install removed per s0021."""
    monkeypatch.chdir(tmp_path)
    main(["init", "-y"])

    assert (tmp_path / "artifacts.yaml").is_file()
    # .claude/ is NOT created — AI install is out of scope
    assert not (tmp_path / ".claude").exists()


def test_init_no_ai_flag_removed(tmp_path: Path, monkeypatch) -> None:
    """`--no-ai` is no longer a valid flag; argparse exits 2."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["init", "--no-ai"])
    assert exc.value.code == 2


def test_init_with_yes_flag_is_non_interactive(tmp_path: Path, monkeypatch) -> None:
    """init -y works in non-TTY contexts without AI install."""
    monkeypatch.chdir(tmp_path)
    main(["init", "-y"])

    assert (tmp_path / "artifacts.yaml").is_file()
    assert (tmp_path / "artifacts" / "kinds").is_dir()


def test_init_with_openstation_compat_no_ai(tmp_path: Path, monkeypatch) -> None:
    """--openstation-compat creates symlink; AI commands still not installed."""
    monkeypatch.chdir(tmp_path)
    main([
        "init",
        "--template", "minimal",
        "--kinds", "none",
        "--agents", "none",
        "--openstation-compat",
    ])

    symlink = tmp_path / "openstation"
    assert symlink.is_symlink()
    assert not (tmp_path / ".claude").exists()
