"""Tests for artbook.placement — destination_for, copy_book, atomic write."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.artbook.errors import ArtbookError, ManifestError, UnknownBookTypeError
from artifacts_os.artbook.manifest import Book
from artifacts_os.artbook.placement import (
    WrittenFile,
    _atomic_write,
    _select_files,
    copy_book,
    destination_for,
)


# ---------------------------------------------------------------------------
# destination_for
# ---------------------------------------------------------------------------


def test_destination_for_agents(tmp_path: Path) -> None:
    book = Book(name="agents", type="agents", path="agents/")
    dest = destination_for(book, tmp_path)
    assert dest == tmp_path / ".claude" / "agents"


def test_destination_for_unknown_type(tmp_path: Path) -> None:
    book = Book(name="widgets", type="widgets", path="widgets/")
    with pytest.raises(UnknownBookTypeError, match="unknown book type 'widgets'"):
        destination_for(book, tmp_path)


# ---------------------------------------------------------------------------
# _select_files — D20 walker
# ---------------------------------------------------------------------------


def test_select_files_d20_walker(tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "architect.md").write_text("# Architect")
    (agents_dir / "developer.md").write_text("# Developer")
    (agents_dir / "README.md").write_text("ignore me")
    (agents_dir / ".gitkeep").write_text("")
    (agents_dir / "notes.txt").write_text("not md")

    book = Book(name="agents", type="agents", path="agents/")
    selected = _select_files(agents_dir, book)
    names = [f.name for f in selected]
    assert names == ["architect.md", "developer.md"]
    assert "README.md" not in names
    assert ".gitkeep" not in names
    assert "notes.txt" not in names


def test_select_files_d20_case_insensitive_readme(tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "readme.MD").write_text("ignore")
    book = Book(name="agents", type="agents", path="agents/")
    selected = _select_files(agents_dir, book)
    assert selected == []


def test_select_files_allowlist_happy(tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "architect.md").write_text("# Architect")
    (agents_dir / "developer.md").write_text("# Developer")

    book = Book(name="agents", type="agents", path="agents/", files=("architect.md",))
    selected = _select_files(agents_dir, book)
    assert len(selected) == 1
    assert selected[0].name == "architect.md"


def test_select_files_allowlist_missing_file(tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "architect.md").write_text("# Architect")

    book = Book(name="agents", type="agents", path="agents/", files=("missing.md",))
    with pytest.raises(ManifestError, match="files entry 'missing.md' not found"):
        _select_files(agents_dir, book)


# ---------------------------------------------------------------------------
# _atomic_write — D19 symlink handling
# ---------------------------------------------------------------------------


def test_atomic_write_new_file(tmp_path: Path) -> None:
    src = tmp_path / "src.md"
    src.write_text("content")
    dst = tmp_path / "dst.md"

    result = _atomic_write(src, dst)
    assert dst.is_file()
    assert dst.read_text() == "content"
    assert result.overwritten is False
    assert result.was_symlink is False


def test_atomic_write_overwrites_existing(tmp_path: Path) -> None:
    src = tmp_path / "src.md"
    src.write_text("new content")
    dst = tmp_path / "dst.md"
    dst.write_text("old content")

    result = _atomic_write(src, dst)
    assert dst.read_text() == "new content"
    assert result.overwritten is True
    assert result.was_symlink is False


def test_atomic_write_unlinks_symlink(tmp_path: Path) -> None:
    src = tmp_path / "src.md"
    src.write_text("content")
    target = tmp_path / "target.md"
    target.write_text("symlink target")
    dst = tmp_path / "dst.md"
    dst.symlink_to(target)

    assert dst.is_symlink()
    result = _atomic_write(src, dst)

    assert dst.is_file()
    assert not dst.is_symlink()
    assert dst.read_text() == "content"
    assert result.was_symlink is True
    assert result.overwritten is True
    # Original symlink target must be untouched
    assert target.read_text() == "symlink target"


def test_atomic_write_unlinks_broken_symlink(tmp_path: Path) -> None:
    src = tmp_path / "src.md"
    src.write_text("content")
    dst = tmp_path / "dst.md"
    dst.symlink_to(tmp_path / "nonexistent.md")  # broken symlink

    result = _atomic_write(src, dst)
    assert dst.is_file()
    assert result.was_symlink is True
    assert result.overwritten is True


def test_atomic_write_destination_is_directory_raises(tmp_path: Path) -> None:
    src = tmp_path / "src.md"
    src.write_text("content")
    dst = tmp_path / "dst"
    dst.mkdir()

    with pytest.raises(ArtbookError, match="is a directory"):
        _atomic_write(src, dst)


# ---------------------------------------------------------------------------
# copy_book — integration
# ---------------------------------------------------------------------------


def test_copy_book_creates_dest_directory(tmp_path: Path) -> None:
    clone_root = tmp_path / "clone"
    agents_dir = clone_root / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "dev.md").write_text("# Dev")

    book = Book(name="agents", type="agents", path="agents/")
    dest = tmp_path / "vault" / ".claude" / "agents"  # does not exist yet

    written = list(copy_book(clone_root, book, dest))
    assert dest.is_dir()
    assert len(written) == 1
    assert (dest / "dev.md").read_text() == "# Dev"


def test_copy_book_d20_excludes_readme(tmp_path: Path) -> None:
    clone_root = tmp_path / "clone"
    agents_dir = clone_root / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").write_text("# Arch")
    (agents_dir / "README.md").write_text("readme")

    book = Book(name="agents", type="agents", path="agents/")
    dest = tmp_path / "dest"
    written = list(copy_book(clone_root, book, dest))

    names = [w.destination.name for w in written]
    assert "architect.md" in names
    assert "README.md" not in names


def test_copy_book_allowlist_only_listed_files(tmp_path: Path) -> None:
    clone_root = tmp_path / "clone"
    agents_dir = clone_root / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").write_text("# Arch")
    (agents_dir / "developer.md").write_text("# Dev")

    book = Book(name="agents", type="agents", path="agents/", files=("architect.md",))
    dest = tmp_path / "dest"
    written = list(copy_book(clone_root, book, dest))
    assert len(written) == 1
    assert written[0].destination.name == "architect.md"
    assert not (dest / "developer.md").exists()


def test_copy_book_unknown_type_raises(tmp_path: Path) -> None:
    clone_root = tmp_path / "clone"
    book = Book(name="widgets", type="widgets", path="widgets/")
    with pytest.raises(UnknownBookTypeError):
        list(copy_book(clone_root, book, tmp_path / "dest"))


def test_copy_book_path_not_directory_raises(tmp_path: Path) -> None:
    clone_root = tmp_path / "clone"
    clone_root.mkdir()
    # book.path is a file, not a directory
    (clone_root / "agents").write_text("not a dir")

    book = Book(name="agents", type="agents", path="agents")
    with pytest.raises(ManifestError, match="not a directory"):
        list(copy_book(clone_root, book, tmp_path / "dest"))
