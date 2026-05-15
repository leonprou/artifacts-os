"""Placement logic — book dest → consumer path and file copy.

Spec: s0029-artbook-mvp-distribution-model §7, D24, D25
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from artifacts_os.artbook.errors import ArtbookError, ManifestError
from artifacts_os.artbook.manifest import Book

# D20 — excluded filenames (case-insensitive set)
_EXCLUDE_NAMES: frozenset[str] = frozenset({"readme.md"})

# D26 — recurse mode exclusions
_RECURSE_EXCLUDE_DIRS: frozenset[str] = frozenset({"__pycache__"})
_RECURSE_EXCLUDE_SUFFIXES: frozenset[str] = frozenset({".pyc", ".pyo"})


# ---------------------------------------------------------------------------
# Dataclasses (§4.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WrittenFile:
    """Record of one file write produced by the copy handler (§4.3)."""

    source: Path        # absolute path inside the clone
    destination: Path   # absolute path in the consumer's project
    overwritten: bool   # True if destination existed before write
    was_symlink: bool   # True if destination was a symlink before unlinking (D19)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def destination_for(vault_root: Path, book: Book) -> Path:
    """Return the placement directory for *book* under *vault_root* (D25).

    One-liner: vault_root / book.dest.  The vault-escape guard at parse time
    (manifest.py) already rejected absolute paths and ``..`` components; this
    function is intentionally minimal.
    """
    return vault_root / book.dest


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _select_files(src_dir: Path, book: Book) -> list[tuple[Path, Path]]:
    """Return [(absolute_source, relative_to_dest), ...] for *book*.

    Three modes:
      - D18 allowlist (``book.files`` set)             → flat, explicit
      - D20 flat walker (default, ``recurse=False``)   → *.md only, top-level only
      - D26 recurse walker (``recurse=True``)          → folder-of-folders
    """
    if book.files is not None:
        # D18 — explicit allowlist; every name must exist under src_dir.
        out: list[tuple[Path, Path]] = []
        for name in book.files:
            # Path-separator check is already done in manifest parsing, but be defensive.
            if "/" in name or "\\" in name:
                raise ManifestError(
                    f"book '{book.name}' files entry '{name}' contains a path separator; "
                    "files entries are flat filenames relative to book.src"
                )
            candidate = src_dir / name
            if not candidate.is_file():
                raise ManifestError(
                    f"book '{book.name}' files entry '{name}' not found at {candidate}"
                )
            out.append((candidate, Path(name)))
        return out

    if book.recurse:
        # D26 — folder-of-folders. For each subdirectory of src_dir, walk
        # the entire subtree and yield (abs_file, relative_path_from_src_dir).
        # Loose files at src_dir's root are silently ignored.
        out = []
        for unit in sorted(src_dir.iterdir()):
            if not unit.is_dir():
                continue
            if unit.name.startswith(".") or unit.name in _RECURSE_EXCLUDE_DIRS:
                continue
            for src_file in sorted(unit.rglob("*")):
                if not src_file.is_file():
                    continue
                rel = src_file.relative_to(src_dir)
                # Skip anything under an excluded directory at any depth, including dotdirs.
                if any(
                    part.startswith(".") or part in _RECURSE_EXCLUDE_DIRS
                    for part in rel.parts[:-1]
                ):
                    continue
                if src_file.name.startswith("."):
                    continue
                if src_file.suffix.lower() in _RECURSE_EXCLUDE_SUFFIXES:
                    continue
                out.append((src_file, rel))
        return out

    # D20 — flat walker: *.md, exclude README.md (case-insensitive) and dotfiles.
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
        out.append((src_file, Path(src_file.name)))
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


def _copy_book(clone_root: Path, book: Book, dest: Path, vault_root: Path) -> Iterable[WrittenFile]:
    """Copy the book's files from *clone_root* into *dest*.

    Honours the ``files`` allowlist (D18) when set; otherwise uses the D20 walker.
    Creates *dest* if it does not exist.

    Yields a WrittenFile for each file copied.

    Raises ManifestError or ArtbookError on failure.
    """
    # D25 — write-time defense-in-depth: re-check dest is within vault_root.
    resolved_dest = dest.resolve()
    resolved_vault = vault_root.resolve()
    if not resolved_dest.is_relative_to(resolved_vault):
        raise ArtbookError(
            f"book '{book.name}' dest '{book.dest}' escapes vault root: "
            f"resolved path '{resolved_dest}' is outside '{resolved_vault}'; refusing to write"
        )

    src_dir = clone_root / book.src
    if not src_dir.is_dir():
        raise ManifestError(
            f"book '{book.name}' src '{book.src}' is not a directory in the distro"
        )

    dest.mkdir(parents=True, exist_ok=True)

    for src_file, rel in _select_files(src_dir, book):
        dest_file = dest / rel
        # D26 — recurse may create nested destination dirs; ensure they exist
        # before write. No-op for flat/allowlist modes (rel is a flat filename).
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        # D25 write-time defense-in-depth: re-check each per-file dest is inside vault.
        resolved_file = dest_file.resolve()
        if not resolved_file.is_relative_to(resolved_vault):
            raise ArtbookError(
                f"book '{book.name}' file '{rel}' resolves to '{resolved_file}', "
                f"outside vault root '{resolved_vault}'; refusing to write"
            )
        yield _atomic_write(src_file, dest_file)


# Public alias kept for callers that pass (clone_root, book, dest) — the vault_root
# parameter is required for the write-time escape guard.
def copy_book(
    clone_root: Path, book: Book, dest: Path, vault_root: Path | None = None
) -> Iterable[WrittenFile]:
    """Copy the book's files from *clone_root* into *dest*.

    *vault_root* is required for the write-time vault-escape guard (D25).
    When omitted, *dest* itself is used as the vault root sentinel (caller
    guarantees the path is safe — used only in tests that pre-validate dest).
    """
    effective_vault_root = vault_root if vault_root is not None else dest.parent
    return _copy_book(clone_root, book, dest, effective_vault_root)
