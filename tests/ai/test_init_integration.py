"""Tests for artifacts init — AI integration notes (updated for s0030).

Per s0030 (books-driven init flow): the D2 no-distro fallback installs the
bundled artifacts-os skill into .claude/skills/artifacts-os/. This is the
only opinionated content the package itself writes to the consumer's vault.

No kinds or agent specs are installed by init without a distro. These tests
verify the updated init behaviour.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.cli import main


@pytest.fixture(autouse=True)
def _clear_distro_env(monkeypatch):
    """Clear ARTIFACTS_DISTRO_URL for all tests in this module."""
    monkeypatch.delenv("ARTIFACTS_DISTRO_URL", raising=False)


def test_init_creates_vault_with_skill(tmp_path: Path, monkeypatch) -> None:
    """D2: init -y writes artifacts.yaml and the bundled skill."""
    monkeypatch.chdir(tmp_path)
    main(["init", "-y"])

    assert (tmp_path / "artifacts.yaml").is_file()
    # D2 fallback installs the bundled skill
    assert (tmp_path / ".claude" / "skills" / "artifacts-os" / "SKILL.md").is_file()
    # No kinds or agents (those come from distro books)
    assert not (tmp_path / "artifacts" / "kinds").exists()
    assert not (tmp_path / "artifacts" / "agents").exists()


def test_init_no_ai_flag_removed(tmp_path: Path, monkeypatch) -> None:
    """`--no-ai` is no longer a valid flag; argparse exits 2."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(["init", "--no-ai"])
    assert exc.value.code == 2


def test_init_with_yes_flag_is_non_interactive(tmp_path: Path, monkeypatch) -> None:
    """init -y works in non-TTY contexts and writes the D2 payload."""
    monkeypatch.chdir(tmp_path)
    main(["init", "-y"])

    assert (tmp_path / "artifacts.yaml").is_file()
    assert (tmp_path / ".claude" / "skills" / "artifacts-os" / "SKILL.md").is_file()
