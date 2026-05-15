"""Placement logic — book-type → consumer path mapping and file copy.

Spec: s0029-artbook-mvp-distribution-model §7
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from artifacts_os.artbook.errors import ArtbookError, ManifestError, UnknownBookTypeError
from artifacts_os.artbook.manifest import Book

# ---------------------------------------------------------------------------
# Placement table (D8, §7.1)
# ---------------------------------------------------------------------------

_PLACEMENT: dict[str, str] = {
    "agents": ".claude/agents",
}

# D20 — excluded filenames (case-insensitive set)
_EXCLUDE_NAMES: frozenset[str] = frozenset({"readme.md"})


# ---------------------------------------------------------------------------
# Dataclasses (§4.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WrittenFile:
    """Record of one file write produced by the agents handler (§4.3)."""

    source: Path        # absolute path inside the clone
    destination: Path   # absolute path in the consumer's project
    overwritten: bool   # True if destination existed before write
    was_symlink: bool   # True if destination was a symlink before unlinking (D19)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def destination_for(book: Book, vault_root: Path) -> Path:
    """Return the placement directory for *book* under *vault_root*.

    Raises UnknownBookTypeError for unrecognised book types.
    """
    try:
        rel = _PLACEMENT[book.type]
    except KeyError as exc:
        raise UnknownBookTypeError(
            f"unknown book type '{book.type}'; supported types: {', '.join(sorted(_PLACEMENT))}"
        ) from exc
    return vault_root / rel


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _select_files(src_dir: Path, book: Book) -> list[Path]:
    """Return the source files to ship for *book*, per D18 (allowlist) or D20 (walker)."""
    if book.files is not None:
        # D18 — explicit allowlist; every name must exist under src_dir.
        out: list[Path] = []
        for name in book.files:
            # Path-separator check is already done in manifest parsing, but be defensive.
            if "/" in name or "\\" in name:
                raise ManifestError(
                    f"book '{book.name}' files entry '{name}' contains a path separator; "
                    "files entries are flat filenames relative to book.path"
                )
            candidate = src_dir / name
            if not candidate.is_file():
                raise ManifestError(
                    f"book '{book.name}' files entry '{name}' not found at {candidate}"
                )
            out.append(candidate)
        return out

    # D20 — walker: *.md, exclude README.md (case-insensitive) and dotfiles, non-recursive.
    out = []
    for src_file in sorted(src_dir.iterdir()):
        if not src_file.is_file():
            continue
        if src_file.suffix.lower() != ".md":
            continue
        if src_file.name.startswith("."):
            continue
        if src_file.name.lower() in _EXCLUDE_NAMES:
            continue
        out.append(src_file)
    return out


def _atomic_write(src: Path, dst: Path) -> WrittenFile:
    """Unlink-then-write per D19; atomic via *.tmp + os.replace."""
    was_symlink = dst.is_symlink()
    # Determine whether destination existed (symlinks may be broken)
    existed = dst.exists() or was_symlink

    if was_symlink or (dst.exists() and not dst.is_file()):
        if dst.is_dir():
            raise ArtbookError(
                f"destination {dst} is a directory; refusing to overwrite"
            )
        # Symlink or other non-regular file → unlink first.
        dst.unlink()
    elif dst.is_dir():
        raise ArtbookError(
            f"destination {dst} is a directory; refusing to overwrite"
        )

    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)
    return WrittenFile(
        source=src,
        destination=dst,
        overwritten=existed,
        was_symlink=was_symlink,
    )


def copy_book(clone_root: Path, book: Book, dest: Path) -> Iterable[WrittenFile]:
    """Copy the book's files from *clone_root* into *dest*.

    Honours the ``files`` allowlist (D18) when set; otherwise uses the D20 walker.
    Creates *dest* if it does not exist.

    Yields a WrittenFile for each file copied.

    Raises ManifestError, ArtbookError, or UnknownBookTypeError on failure.
    """
    # Validate book type (before doing any I/O)
    if book.type not in _PLACEMENT:
        raise UnknownBookTypeError(
            f"unknown book type '{book.type}'; supported types: {', '.join(sorted(_PLACEMENT))}"
        )

    src_dir = clone_root / book.path
    if not src_dir.is_dir():
        raise ManifestError(
            f"book '{book.name}' path '{book.path}' is not a directory in the distro"
        )

    dest.mkdir(parents=True, exist_ok=True)

    for src_file in _select_files(src_dir, book):
        dest_file = dest / src_file.name
        yield _atomic_write(src_file, dest_file)
