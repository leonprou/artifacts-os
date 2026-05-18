"""End-to-end pull tests with promotion (test_pull_integration.py).

Tests: pull with promote, --no-promote, promotion: disabled, re-pull idempotency,
stale promotion cleanup after upstream removes an item, and end-to-end fixture
tests using the actual repo artbook.yaml.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from artifacts_os.artbook.manifest import Book, Promote
from artifacts_os.artbook.pull import pull_book
from artifacts_os.artbook.state import read_state

# Root of the artifacts-os repository (two directories above tests/artbook/).
_REPO_ROOT = Path(__file__).resolve().parents[2]


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


# ---------------------------------------------------------------------------
# End-to-end tests using the actual repo artbook.yaml
# ---------------------------------------------------------------------------


class TestArtifactsOsDistroIntegration:
    """Pull from the repo's own artbook.yaml and verify canonical + promote structure.

    These tests call pull_book directly against the repo root (no git clone
    required).  They verify the migrated artbook.yaml shape: canonical files
    land under artifacts/…, promoted symlinks land under .claude/… (except
    kinds which has no promote:).
    """

    def test_all_books_canonical_and_promoted(self, tmp_path: Path) -> None:
        """Pull all books: verify canonical + promotion dirs populated."""
        from artifacts_os.artbook.manifest import load_manifest

        vault = _make_vault(tmp_path / "vault")
        manifest = load_manifest(_REPO_ROOT)

        for book in manifest.books:
            pull_book(book, _REPO_ROOT, vault)

        # agents: canonical + promote
        assert (vault / "artifacts" / "agents").is_dir()
        assert (vault / ".claude" / "agents").is_dir()

        # commands: canonical + promote
        assert (vault / "artifacts" / "commands").is_dir()
        assert (vault / ".claude" / "commands").is_dir()

        # skills: canonical + promote
        assert (vault / "artifacts" / "skills").is_dir()
        assert (vault / ".claude" / "skills").is_dir()

        # kinds: canonical only — no .claude/kinds/
        assert (vault / "artifacts" / "kinds").is_dir()
        assert not (vault / ".claude" / "kinds").exists()

    def test_agent_symlinks_resolve_to_canonical(self, tmp_path: Path) -> None:
        """Promoted agent entries are symlinks pointing into artifacts/agents/."""
        from artifacts_os.artbook.manifest import load_manifest

        vault = _make_vault(tmp_path / "vault")
        manifest = load_manifest(_REPO_ROOT)
        agents_book = next(b for b in manifest.books if b.name == "agents")
        pull_book(agents_book, _REPO_ROOT, vault)

        promo_dir = vault / ".claude" / "agents"
        canon_dir = vault / "artifacts" / "agents"
        symlinks = sorted(promo_dir.glob("*.md"))
        assert len(symlinks) >= 10, f"expected ≥10 agent files, got {len(symlinks)}"
        for sl in symlinks:
            assert sl.is_symlink(), f"{sl} should be a symlink"
            assert sl.resolve().is_relative_to(
                canon_dir.resolve()
            ), f"{sl} should resolve under {canon_dir}"

    def test_kinds_no_promote(self, tmp_path: Path) -> None:
        """`kinds` book has no promote: — .claude/kinds/ is never created."""
        from artifacts_os.artbook.manifest import load_manifest

        vault = _make_vault(tmp_path / "vault")
        manifest = load_manifest(_REPO_ROOT)
        kinds_book = next(b for b in manifest.books if b.name == "kinds")

        assert kinds_book.promote is None
        pull_book(kinds_book, _REPO_ROOT, vault)
        assert not (vault / ".claude" / "kinds").exists()

    def test_agents_count_matches_canonical(self, tmp_path: Path) -> None:
        """Promotion creates one symlink per canonical agent file."""
        from artifacts_os.artbook.manifest import load_manifest

        vault = _make_vault(tmp_path / "vault")
        manifest = load_manifest(_REPO_ROOT)
        agents_book = next(b for b in manifest.books if b.name == "agents")
        pull_book(agents_book, _REPO_ROOT, vault)

        canonical_files = sorted((vault / "artifacts" / "agents").glob("*.md"))
        promoted_files = sorted((vault / ".claude" / "agents").glob("*.md"))
        assert len(canonical_files) == len(promoted_files)

    def test_repull_agents_idempotent(self, tmp_path: Path) -> None:
        """A second pull of the agents book is byte-for-byte idempotent."""
        from artifacts_os.artbook.manifest import load_manifest

        vault = _make_vault(tmp_path / "vault")
        manifest = load_manifest(_REPO_ROOT)
        agents_book = next(b for b in manifest.books if b.name == "agents")

        pull_book(agents_book, _REPO_ROOT, vault)
        state1 = read_state(vault)

        pull_book(agents_book, _REPO_ROOT, vault)
        state2 = read_state(vault)

        assert state1["promotions"] == state2["promotions"]

        # Canonical file content unchanged — spot-check first file
        canon_files = sorted((vault / "artifacts" / "agents").glob("*.md"))
        assert len(canon_files) > 0
        first = canon_files[0]
        content_before = first.read_text()
        pull_book(agents_book, _REPO_ROOT, vault)
        assert first.read_text() == content_before
