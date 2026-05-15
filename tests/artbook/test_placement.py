"""Tests for artbook.placement — destination_for, copy_book, atomic write (v2 schema)."""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.artbook.errors import ArtbookError, ManifestError
from artifacts_os.artbook.manifest import Book
from artifacts_os.artbook.placement import (
    WrittenFile,
    _atomic_write,
    _select_files,
    copy_book,
    destination_for,
)


# ---------------------------------------------------------------------------
# destination_for (D25 — one-liner: vault_root / book.dest)
# ---------------------------------------------------------------------------


def test_destination_for_agents(tmp_path: Path) -> None:
    book = Book(name="agents", src="agents/", dest=".claude/agents/")
    dest = destination_for(tmp_path, book)
    assert dest == tmp_path / ".claude" / "agents"


def test_destination_for_custom_dest(tmp_path: Path) -> None:
    book = Book(name="skills", src="skills/", dest=".claude/skills/")
    dest = destination_for(tmp_path, book)
    assert dest == tmp_path / ".claude" / "skills"


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

    book = Book(name="agents", src="agents/", dest=".claude/agents/")
    selected = _select_files(agents_dir, book)
    # D26 — entries are (abs_source, rel_to_dest) tuples
    names = [src.name for src, _rel in selected]
    rels = [str(rel) for _src, rel in selected]
    assert names == ["architect.md", "developer.md"]
    # Flat mode: rel == filename
    assert rels == ["architect.md", "developer.md"]
    assert "README.md" not in names
    assert ".gitkeep" not in names
    assert "notes.txt" not in names


def test_select_files_d20_case_insensitive_readme(tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "readme.MD").write_text("ignore")
    book = Book(name="agents", src="agents/", dest=".claude/agents/")
    selected = _select_files(agents_dir, book)
    assert selected == []


def test_select_files_allowlist_happy(tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "architect.md").write_text("# Architect")
    (agents_dir / "developer.md").write_text("# Developer")

    book = Book(name="agents", src="agents/", dest=".claude/agents/", files=("architect.md",))
    selected = _select_files(agents_dir, book)
    assert len(selected) == 1
    src, rel = selected[0]
    assert src.name == "architect.md"
    assert str(rel) == "architect.md"


def test_select_files_allowlist_missing_file(tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "architect.md").write_text("# Architect")

    book = Book(name="agents", src="agents/", dest=".claude/agents/", files=("missing.md",))
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
# copy_book — integration (v2: src/dest fields, vault_root guard)
# ---------------------------------------------------------------------------


def test_copy_book_creates_dest_directory(tmp_path: Path) -> None:
    clone_root = tmp_path / "clone"
    agents_dir = clone_root / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "dev.md").write_text("# Dev")

    vault = tmp_path / "vault"
    vault.mkdir()
    book = Book(name="agents", src="agents/", dest=".claude/agents/")
    dest = destination_for(vault, book)  # vault / ".claude/agents/"

    written = list(copy_book(clone_root, book, dest, vault_root=vault))
    assert dest.is_dir()
    assert len(written) == 1
    assert (dest / "dev.md").read_text() == "# Dev"


def test_copy_book_d20_excludes_readme(tmp_path: Path) -> None:
    clone_root = tmp_path / "clone"
    agents_dir = clone_root / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").write_text("# Arch")
    (agents_dir / "README.md").write_text("readme")

    vault = tmp_path / "vault"
    vault.mkdir()
    book = Book(name="agents", src="agents/", dest=".claude/agents/")
    dest = destination_for(vault, book)
    written = list(copy_book(clone_root, book, dest, vault_root=vault))

    names = [w.destination.name for w in written]
    assert "architect.md" in names
    assert "README.md" not in names


def test_copy_book_allowlist_only_listed_files(tmp_path: Path) -> None:
    clone_root = tmp_path / "clone"
    agents_dir = clone_root / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "architect.md").write_text("# Arch")
    (agents_dir / "developer.md").write_text("# Dev")

    vault = tmp_path / "vault"
    vault.mkdir()
    book = Book(name="agents", src="agents/", dest=".claude/agents/", files=("architect.md",))
    dest = destination_for(vault, book)
    written = list(copy_book(clone_root, book, dest, vault_root=vault))
    assert len(written) == 1
    assert written[0].destination.name == "architect.md"
    assert not (dest / "developer.md").exists()


def test_copy_book_src_not_directory_raises(tmp_path: Path) -> None:
    clone_root = tmp_path / "clone"
    clone_root.mkdir()
    # book.src is a file, not a directory
    (clone_root / "agents").write_text("not a dir")

    vault = tmp_path / "vault"
    vault.mkdir()
    book = Book(name="agents", src="agents", dest=".claude/agents/")
    dest = destination_for(vault, book)
    with pytest.raises(ManifestError, match="not a directory"):
        list(copy_book(clone_root, book, dest, vault_root=vault))


# ---------------------------------------------------------------------------
# vault-escape guard at write time (D25 defense-in-depth)
# ---------------------------------------------------------------------------


def test_copy_book_dest_escapes_vault_raises(tmp_path: Path) -> None:
    """Write-time guard: if dest resolves outside vault_root, raise ArtbookError."""
    clone_root = tmp_path / "clone"
    agents_dir = clone_root / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "dev.md").write_text("content")

    vault = tmp_path / "vault"
    vault.mkdir()

    # Craft a dest that is outside the vault_root
    outside_dest = tmp_path / "outside"
    book = Book(name="agents", src="agents/", dest=".claude/agents/")

    with pytest.raises(ArtbookError, match="escapes vault"):
        list(copy_book(clone_root, book, outside_dest, vault_root=vault))


# ---------------------------------------------------------------------------
# _select_files — D26 recurse walker (folder-of-folders)
# ---------------------------------------------------------------------------


def _make_skills_fixture(root: Path) -> Path:
    """Create a folder-of-folders fixture matching the skills source layout.

    Layout:
        root/skills/
            artifacts-os/
                SKILL.md
                __init__.py
                nested/
                    helper.md
            release-changelog/
                SKILL.md
                __init__.py
            __pycache__/        # excluded
                foo.cpython.pyc
            .hidden/            # excluded
                ignore.md
            loose.md            # ignored (loose root file in recurse mode)
            artifacts-os/__pycache__/      # excluded at any depth
                bar.pyc
            artifacts-os/extra.pyc          # excluded by suffix
    """
    skills = root / "skills"
    skills.mkdir(parents=True)

    # Unit 1
    aos = skills / "artifacts-os"
    aos.mkdir()
    (aos / "SKILL.md").write_text("# Skill: artifacts-os")
    (aos / "__init__.py").write_text("")
    (aos / "nested").mkdir()
    (aos / "nested" / "helper.md").write_text("# Helper")
    # Excluded artefacts inside the unit
    (aos / "__pycache__").mkdir()
    (aos / "__pycache__" / "bar.cpython.pyc").write_text("compiled")
    (aos / "extra.pyc").write_text("compiled")
    (aos / ".dotfile").write_text("hidden")

    # Unit 2
    rc = skills / "release-changelog"
    rc.mkdir()
    (rc / "SKILL.md").write_text("# Skill: release-changelog")
    (rc / "__init__.py").write_text("")

    # Excluded top-level dirs
    (skills / "__pycache__").mkdir()
    (skills / "__pycache__" / "foo.cpython.pyc").write_text("compiled")
    (skills / ".hidden").mkdir()
    (skills / ".hidden" / "ignore.md").write_text("hidden unit")

    # Loose file at skills root — must be ignored in recurse mode
    (skills / "loose.md").write_text("loose")

    return skills


def test_select_files_d26_recurse_ships_nested_files(tmp_path: Path) -> None:
    """D26: walker descends each unit's subtree, yielding (src, rel) tuples."""
    skills_dir = _make_skills_fixture(tmp_path)
    book = Book(
        name="skills",
        src="skills/",
        dest=".claude/skills/",
        recurse=True,
    )

    selected = _select_files(skills_dir, book)
    rels = sorted(str(rel) for _src, rel in selected)

    # Expected: two units, each with SKILL.md and __init__.py; unit 1 also has nested/helper.md
    assert "artifacts-os/SKILL.md" in rels
    assert "artifacts-os/__init__.py" in rels
    assert "artifacts-os/nested/helper.md" in rels
    assert "release-changelog/SKILL.md" in rels
    assert "release-changelog/__init__.py" in rels


def test_select_files_d26_recurse_excludes_pycache_and_pyc(tmp_path: Path) -> None:
    """D26: __pycache__/ and *.pyc files are filtered out at any depth."""
    skills_dir = _make_skills_fixture(tmp_path)
    book = Book(name="skills", src="skills/", dest=".claude/skills/", recurse=True)

    selected = _select_files(skills_dir, book)
    rels = [str(rel) for _src, rel in selected]

    # Top-level __pycache__ is excluded
    for rel in rels:
        assert "__pycache__" not in rel, f"unexpected __pycache__ in {rel}"
        assert not rel.endswith(".pyc"), f"unexpected .pyc in {rel}"
        assert not rel.endswith(".pyo"), f"unexpected .pyo in {rel}"


def test_select_files_d26_recurse_skips_dotted_paths(tmp_path: Path) -> None:
    """D26: dotted dirs (.hidden/) and dotfiles (.foo) are excluded at any depth."""
    skills_dir = _make_skills_fixture(tmp_path)
    book = Book(name="skills", src="skills/", dest=".claude/skills/", recurse=True)

    selected = _select_files(skills_dir, book)
    rels = [str(rel) for _src, rel in selected]

    for rel in rels:
        # No dot-prefixed component anywhere in the relative path
        parts = Path(rel).parts
        for part in parts:
            assert not part.startswith("."), f"unexpected dotted part in {rel}"


def test_select_files_d26_recurse_ignores_loose_root_files(tmp_path: Path) -> None:
    """D26: files directly under src_dir (not inside a unit) are ignored."""
    skills_dir = _make_skills_fixture(tmp_path)
    book = Book(name="skills", src="skills/", dest=".claude/skills/", recurse=True)

    selected = _select_files(skills_dir, book)
    rels = [str(rel) for _src, rel in selected]

    assert "loose.md" not in rels
    # Every relative path starts with a unit name (has at least 2 parts)
    for rel in rels:
        assert len(Path(rel).parts) >= 2, f"loose file leaked: {rel}"


def test_select_files_d26_recurse_relative_paths_are_anchored_at_src_dir(
    tmp_path: Path,
) -> None:
    """D26: rel_path is computed as src_file.relative_to(src_dir)."""
    skills_dir = _make_skills_fixture(tmp_path)
    book = Book(name="skills", src="skills/", dest=".claude/skills/", recurse=True)

    selected = _select_files(skills_dir, book)
    for src, rel in selected:
        # The absolute src joined back from src_dir / rel must equal src
        assert (skills_dir / rel).resolve() == src.resolve()


def test_select_files_d26_recurse_descends_multiple_levels(tmp_path: Path) -> None:
    """D26: walker descends arbitrarily deep within a unit subtree."""
    skills_dir = tmp_path / "skills"
    unit = skills_dir / "deep-skill"
    deep = unit / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (deep / "file.md").write_text("deep file")
    (unit / "top.md").write_text("top file")

    book = Book(name="skills", src="skills/", dest=".claude/skills/", recurse=True)
    selected = _select_files(skills_dir, book)
    rels = sorted(str(rel) for _src, rel in selected)
    assert "deep-skill/top.md" in rels
    assert "deep-skill/a/b/c/file.md" in rels


# ---------------------------------------------------------------------------
# copy_book — D26 recurse mode end-to-end
# ---------------------------------------------------------------------------


def test_copy_book_d26_recurse_writes_nested_files(tmp_path: Path) -> None:
    """D26: copy_book in recurse mode writes nested files preserving structure."""
    clone_root = tmp_path / "clone"
    _make_skills_fixture(clone_root)  # creates clone_root/skills/...

    vault = tmp_path / "vault"
    vault.mkdir()
    book = Book(
        name="skills",
        src="skills/",
        dest=".claude/skills/",
        recurse=True,
    )
    dest = destination_for(vault, book)
    written = list(copy_book(clone_root, book, dest, vault_root=vault))

    # Every written file landed under vault/.claude/skills/
    rels = sorted(str(w.destination.relative_to(dest)) for w in written)
    assert "artifacts-os/SKILL.md" in rels
    assert "artifacts-os/__init__.py" in rels
    assert "artifacts-os/nested/helper.md" in rels
    assert "release-changelog/SKILL.md" in rels
    assert "release-changelog/__init__.py" in rels

    # Excluded artefacts must not appear
    for rel in rels:
        assert "__pycache__" not in rel
        assert not rel.endswith(".pyc")

    # On-disk verification
    assert (dest / "artifacts-os" / "SKILL.md").is_file()
    assert (dest / "artifacts-os" / "nested" / "helper.md").is_file()
    assert (dest / "release-changelog" / "SKILL.md").is_file()
