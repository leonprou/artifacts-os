"""End-to-end pull tests with promotion (test_pull_integration.py).

Tests: pull with promote, --no-promote, promotion: disabled, re-pull idempotency,
and stale promotion cleanup after upstream removes an item.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from artifacts_os.artbook.manifest import Book, Promote
from artifacts_os.artbook.pull import pull_book
from artifacts_os.artbook.state import read_state


def _make_distro(root: Path, agent_names: list[str]) -> Path:
    """Create a minimal distro repo with promote: .claude/agents/."""
    root.mkdir(parents=True, exist_ok=True)
    for cmd in [
        ["git", "init", "--initial-branch", "main"],
        ["git", "config", "user.email", "t@t.com"],
        ["git", "config", "user.name", "T"],
    ]:
        subprocess.run(cmd, cwd=root, check=True, capture_output=True)
    agents_dir = root / "agents"
    agents_dir.mkdir()
    for name in agent_names:
        (agents_dir / f"{name}.md").write_text(f"# {name}")
    (root / "artbook.yaml").write_text(yaml.dump({
        "version": 1,
        "distro": {"name": "test-distro"},
        "books": [{"name": "agents", "src": "agents/", "promote": ".claude/agents/"}],
    }))
    for cmd in [["git", "add", "."], ["git", "commit", "-m", "init"]]:
        subprocess.run(cmd, cwd=root, check=True, capture_output=True)
    return root


def _make_vault(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    return root


class TestPullWithPromote:
    def test_pull_promotes_to_target(self, tmp_path: Path) -> None:
        """Basic pull: canonical + promotion both written."""
        clone = tmp_path / "clone"
        vault = _make_vault(tmp_path / "vault")
        _make_distro(clone, ["architect", "developer"])

        from artifacts_os.artbook.manifest import load_manifest
        manifest = load_manifest(clone)
        book = manifest.books[0]
        report = pull_book(book, clone, vault)

        # Canonical write (D37 default dest: artifacts/agents/)
        canon_dir = vault / "artifacts" / "agents"
        assert (canon_dir / "architect.md").is_file()
        assert (canon_dir / "developer.md").is_file()

        # Promotion write
        assert report.promotion is not None
        promo_dir = vault / ".claude" / "agents"
        assert promo_dir.is_dir()

        assert report.promotion_skipped_reason is None

    def test_pull_no_promote_flag(self, tmp_path: Path) -> None:
        """--no-promote: canonical writes happen, state file untouched."""
        clone = tmp_path / "clone"
        vault = _make_vault(tmp_path / "vault")
        _make_distro(clone, ["architect"])

        from artifacts_os.artbook.manifest import load_manifest
        manifest = load_manifest(clone)
        book = manifest.books[0]
        report = pull_book(book, clone, vault, no_promote=True)

        # Canonical written
        assert (vault / "artifacts" / "agents" / "architect.md").is_file()
        # Promotion skipped
        assert report.promotion is None
        assert report.promotion_skipped_reason == "flag"
        # State file not touched
        state = read_state(vault)
        assert state["promotions"] == {}

    def test_pull_promotion_disabled_setting(self, tmp_path: Path) -> None:
        """artbook.promotion: disabled — skipped with reason='setting'."""
        clone = tmp_path / "clone"
        vault = _make_vault(tmp_path / "vault")
        _make_distro(clone, ["architect"])

        from artifacts_os.artbook.manifest import load_manifest
        manifest = load_manifest(clone)
        book = manifest.books[0]
        report = pull_book(book, clone, vault, promote_disabled=True)

        assert report.promotion is None
        assert report.promotion_skipped_reason == "setting"

    def test_repull_idempotency(self, tmp_path: Path) -> None:
        """Re-pull: same files, state file unchanged on second pull."""
        clone = tmp_path / "clone"
        vault = _make_vault(tmp_path / "vault")
        _make_distro(clone, ["architect"])

        from artifacts_os.artbook.manifest import load_manifest
        manifest = load_manifest(clone)
        book = manifest.books[0]

        pull_book(book, clone, vault)
        state1 = read_state(vault)

        pull_book(book, clone, vault)
        state2 = read_state(vault)

        # State should be equivalent (same content)
        assert state1["promotions"].keys() == state2["promotions"].keys()
        # The promoted file should still be there
        promo_target = vault / ".claude" / "agents" / "architect.md"
        assert promo_target.exists()

    def test_stale_cleanup_after_canonical_file_removed(self, tmp_path: Path) -> None:
        """Stale promotion target is cleaned up when canonical file is removed.

        This tests the promote_book stale-cleanup logic directly:
        if the canonical file is no longer present, the previously-promoted
        symlink at the target should be removed on re-pull.

        Note: pull_book does not currently remove stale canonical files (that
        is the responsibility of the caller or a future re-pull engine).  This
        test simulates that by manually removing the canonical file and calling
        pull_book again.
        """
        clone = tmp_path / "clone"
        vault = _make_vault(tmp_path / "vault")
        _make_distro(clone, ["architect", "developer"])

        from artifacts_os.artbook.manifest import load_manifest
        from artifacts_os.artbook.placement import promote_book

        manifest = load_manifest(clone)
        book = manifest.books[0]

        # First pull: both files promoted
        pull_book(book, clone, vault)
        promo_dir = vault / ".claude" / "agents"
        assert (promo_dir / "architect.md").exists()
        assert (promo_dir / "developer.md").exists()

        # Simulate upstream removing developer.md by removing both the clone source
        # AND the canonical destination file (as a future re-pull engine would do)
        (clone / "agents" / "developer.md").unlink()
        (vault / "artifacts" / "agents" / "developer.md").unlink()

        # Re-run promotion step: should detect developer.md as stale and clean it
        from artifacts_os.artbook.state import read_state
        state = read_state(vault)
        report = promote_book(book, vault, state=state)

        # Stale promotion target should be cleaned up
        assert not (promo_dir / "developer.md").exists()
        assert (promo_dir / "architect.md").exists()  # still there

        assert len(report.cleaned) >= 1
