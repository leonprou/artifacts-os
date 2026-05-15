"""Tests for artbook.pull — find_book, pull_book, and end-to-end scenarios (v2 schema)."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.artbook.errors import UnknownBookError
from artifacts_os.artbook.manifest import Book, Manifest
from artifacts_os.artbook.pull import PullReport, find_book, pull_book


# ---------------------------------------------------------------------------
# find_book
# ---------------------------------------------------------------------------


def _make_manifest(*book_names: str) -> Manifest:
    books = tuple(
        Book(name=n, src=f"{n}/", dest=f".claude/{n}/") for n in book_names
    )
    return Manifest(version=1, name="test-distro", description=None, books=books)


def test_find_book_found() -> None:
    m = _make_manifest("agents", "kinds")
    book = find_book(m, "agents")
    assert book.name == "agents"


def test_find_book_not_found() -> None:
    m = _make_manifest("agents")
    with pytest.raises(UnknownBookError, match="'kinds' not found"):
        find_book(m, "kinds")


def test_find_book_includes_available_names_in_error() -> None:
    m = _make_manifest("agents")
    with pytest.raises(UnknownBookError, match="available books: agents"):
        find_book(m, "missing")


# ---------------------------------------------------------------------------
# pull_book — happy path with local fixture
# ---------------------------------------------------------------------------


def test_pull_book_happy_path(clone_root: Path, vault_root: Path) -> None:
    from artifacts_os.artbook.manifest import load_manifest

    manifest = load_manifest(clone_root)
    book = find_book(manifest, "agents")

    report = pull_book(book, clone_root, vault_root, distro_url="file:///fake", distro_sha="abc1234")

    dest = vault_root / ".claude" / "agents"
    assert dest.is_dir()
    written_names = {w.destination.name for w in report.written}
    assert "architect.md" in written_names
    assert "developer.md" in written_names
    # README.md must be excluded by D20
    assert "README.md" not in written_names

    assert report.distro_url == "file:///fake"
    assert report.distro_sha == "abc1234"
    assert isinstance(report, PullReport)


def test_pull_book_overwrites_existing(clone_root: Path, vault_root: Path) -> None:
    from artifacts_os.artbook.manifest import load_manifest

    # Pre-create the destination file
    dest = vault_root / ".claude" / "agents"
    dest.mkdir(parents=True)
    (dest / "architect.md").write_text("old content")

    manifest = load_manifest(clone_root)
    book = find_book(manifest, "agents")
    report = pull_book(book, clone_root, vault_root)

    overwritten = [w for w in report.written if w.destination.name == "architect.md"]
    assert len(overwritten) == 1
    assert overwritten[0].overwritten is True
    assert (dest / "architect.md").read_text() != "old content"


def test_pull_book_symlink_destination(clone_root: Path, vault_root: Path) -> None:
    from artifacts_os.artbook.manifest import load_manifest

    dest = vault_root / ".claude" / "agents"
    dest.mkdir(parents=True)
    # Create a symlink at the destination of one of the files
    target = vault_root / "target.md"
    target.write_text("symlink target")
    sym = dest / "architect.md"
    sym.symlink_to(target)

    manifest = load_manifest(clone_root)
    book = find_book(manifest, "agents")
    report = pull_book(book, clone_root, vault_root)

    sym_writes = [w for w in report.written if w.destination.name == "architect.md"]
    assert len(sym_writes) == 1
    assert sym_writes[0].was_symlink is True
    # Must be a regular file now, not a symlink
    assert not (dest / "architect.md").is_symlink()
    assert (dest / "architect.md").is_file()
    # Symlink target must be untouched
    assert target.read_text() == "symlink target"


def test_pull_book_creates_missing_parent_directory(
    clone_root: Path, vault_root: Path
) -> None:
    from artifacts_os.artbook.manifest import load_manifest

    # Ensure .claude/agents doesn't exist
    dest = vault_root / ".claude" / "agents"
    assert not dest.exists()

    manifest = load_manifest(clone_root)
    book = find_book(manifest, "agents")
    pull_book(book, clone_root, vault_root)

    assert dest.is_dir()


# ---------------------------------------------------------------------------
# pull_book — allowlist (D18)
# ---------------------------------------------------------------------------


def test_pull_book_allowlist(tmp_path: Path, vault_root: Path) -> None:
    """pull_book honours files: allowlist — only listed files written."""
    clone_root = tmp_path / "clone"
    agents_dir = clone_root / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").write_text("# Arch")
    (agents_dir / "developer.md").write_text("# Dev")

    book = Book(name="agents", src="agents/", dest=".claude/agents/", files=("architect.md",))
    report = pull_book(book, clone_root, vault_root)

    written_names = {w.destination.name for w in report.written}
    assert written_names == {"architect.md"}
    assert not (vault_root / ".claude" / "agents" / "developer.md").exists()


def test_pull_book_allowlist_missing_file_raises(
    tmp_path: Path, vault_root: Path
) -> None:
    from artifacts_os.artbook.errors import ManifestError

    clone_root = tmp_path / "clone"
    agents_dir = clone_root / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").write_text("# Arch")

    book = Book(name="agents", src="agents/", dest=".claude/agents/", files=("ghost.md",))
    with pytest.raises(ManifestError, match="'ghost.md' not found"):
        pull_book(book, clone_root, vault_root)
