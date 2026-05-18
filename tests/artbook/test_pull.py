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

    dest = vault_root / "artifacts" / "agents"
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
    dest = vault_root / "artifacts" / "agents"
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

    dest = vault_root / "artifacts" / "agents"
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

    # Ensure artifacts/agents doesn't exist
    dest = vault_root / "artifacts" / "agents"
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


# ---------------------------------------------------------------------------
# pull_book — D26 recurse mode end-to-end
# ---------------------------------------------------------------------------


def test_pull_book_recurse_writes_nested_files(
    tmp_path: Path, vault_root: Path
) -> None:
    """D26 end-to-end: pull a recurse book → nested files at vault/<dest>/<unit>/..."""
    clone_root = tmp_path / "clone"
    skills = clone_root / "skills"

    # Unit 1
    aos = skills / "artifacts-os"
    aos.mkdir(parents=True)
    (aos / "SKILL.md").write_text("# Skill: artifacts-os")
    (aos / "__init__.py").write_text("")
    (aos / "nested").mkdir()
    (aos / "nested" / "helper.md").write_text("# Helper")

    # Unit 2
    rc = skills / "release-changelog"
    rc.mkdir()
    (rc / "SKILL.md").write_text("# Skill: release-changelog")
    (rc / "__init__.py").write_text("")

    # Excluded artefacts
    (skills / "__pycache__").mkdir()
    (skills / "__pycache__" / "foo.pyc").write_text("compiled")
    (aos / "extra.pyc").write_text("compiled")

    book = Book(
        name="skills",
        src="skills/",
        dest=".claude/skills/",
        recurse=True,
    )
    report = pull_book(book, clone_root, vault_root)

    dest = vault_root / ".claude" / "skills"
    assert dest.is_dir()

    # Verify on-disk layout
    assert (dest / "artifacts-os" / "SKILL.md").read_text() == "# Skill: artifacts-os"
    assert (dest / "artifacts-os" / "__init__.py").is_file()
    assert (dest / "artifacts-os" / "nested" / "helper.md").read_text() == "# Helper"
    assert (dest / "release-changelog" / "SKILL.md").is_file()
    assert (dest / "release-changelog" / "__init__.py").is_file()

    # __pycache__ and *.pyc must be absent
    assert not (dest / "__pycache__").exists()
    assert not (dest / "artifacts-os" / "extra.pyc").exists()

    # Report contains all written files
    written_rels = {
        str(w.destination.relative_to(dest)) for w in report.written
    }
    assert "artifacts-os/SKILL.md" in written_rels
    assert "artifacts-os/nested/helper.md" in written_rels
    assert "release-changelog/SKILL.md" in written_rels


def test_pull_book_recurse_overwrite_semantics(
    tmp_path: Path, vault_root: Path
) -> None:
    """D26: second pull overwrites prior nested files, marks them overwritten."""
    clone_root = tmp_path / "clone"
    skills = clone_root / "skills"
    aos = skills / "artifacts-os"
    aos.mkdir(parents=True)
    (aos / "SKILL.md").write_text("v2")

    book = Book(
        name="skills",
        src="skills/",
        dest=".claude/skills/",
        recurse=True,
    )

    # Pre-populate destination with an older copy
    dest = vault_root / ".claude" / "skills" / "artifacts-os"
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text("v1")

    report = pull_book(book, clone_root, vault_root)
    overwritten = [w for w in report.written if w.destination.name == "SKILL.md"]
    assert len(overwritten) == 1
    assert overwritten[0].overwritten is True
    assert (dest / "SKILL.md").read_text() == "v2"
