"""Placement logic — book dest → consumer path and file copy.

Also contains the promotion engine (post-pull step per D30, D32, D33, D36).

Spec: s0029-artbook-mvp-distribution-model §7, D24, D25
     s0031-artbook-post-pull-artifact-promotion D30, D32, D33, D36
"""

from __future__ import annotations

import os
import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from artifacts_os.artbook.errors import ArtbookError, ManifestError, PromotionError
from artifacts_os.artbook.manifest import Book, Promote
from artifacts_os.artbook.state import (
    entry_hash,
    entry_path,
    file_hash,
    make_copy_entry,
    make_symlink_entry,
    read_state,
    write_state,
)

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


@dataclass(frozen=True)
class PromotedFile:
    """One promotion write (D33)."""

    canonical: Path      # absolute path under artifacts/…
    target: Path         # absolute path under the promotion target
    mode: str            # 'symlink' or 'copy'
    overwritten: bool    # True if target existed before write
    fallback: bool       # True if symlink was requested but fell back to copy


@dataclass(frozen=True)
class PromotionReport:
    """Outcome of a promote step for one book (D33)."""

    book: Book
    target_root: Path              # absolute path of the promotion target dir
    mode: str                      # effective default mode ('symlink' or 'copy')
    promoted: tuple[PromotedFile, ...]
    cleaned: tuple[Path, ...]      # stale targets removed this run
    skipped: tuple[Path, ...]      # user-modified targets we declined to overwrite
    fallback_count: int            # files where symlink → copy fallback occurred
    errors: tuple[str, ...]        # per-file error messages (non-fatal)


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


def filter_entries_by_items(
    entries: list[tuple[Path, Path]],
    items: list[str],
    *,
    recurse: bool,
) -> tuple[list[tuple[Path, Path]], list[str], list[str]]:
    """Filter *(abs_src, rel)* entries by consumer-specified item names.

    For flat / allowlist books (*recurse=False*): each item matches by
    filename stem (``architect``) or full filename (``architect.md``).

    For recurse books (*recurse=True*): each item matches by unit folder
    name — the first path component of the relative path (``artifacts-os``).

    Returns:
        filtered   — matching ``(abs_src, rel)`` entries in original order
        unmatched  — sorted list of item names that did not match anything
        available  — sorted list of available item identifiers (stems for
                     flat, unit names for recurse) — suitable for error messages
    """
    if not items:
        # No filter requested — return everything; no need to compute available.
        return list(entries), [], []

    if recurse:
        unit_to_entries: dict[str, list[tuple[Path, Path]]] = {}
        for abs_src, rel in entries:
            unit = rel.parts[0] if rel.parts else ""
            if unit:
                unit_to_entries.setdefault(unit, []).append((abs_src, rel))
        available = sorted(unit_to_entries)
        item_set = set(items)
        matched_units = item_set & set(unit_to_entries)
        unmatched = sorted(item_set - matched_units)
        # Preserve original order from *entries*
        matched_rels = {rel for unit in matched_units for _src, rel in unit_to_entries[unit]}
        filtered = [(src, rel) for src, rel in entries if rel in matched_rels]
    else:
        # Build name → entry and stem → entry look-ups
        by_name: dict[str, tuple[Path, Path]] = {}
        by_stem: dict[str, tuple[Path, Path]] = {}
        for abs_src, rel in entries:
            by_name[rel.name] = (abs_src, rel)
            by_stem[rel.stem] = (abs_src, rel)

        available = sorted(by_stem)  # stems are the canonical display names

        matched_names: set[str] = set()  # rel.name values that matched
        unmatched_list: list[str] = []
        for item in items:
            if item in by_name:
                matched_names.add(by_name[item][1].name)
            elif item in by_stem:
                matched_names.add(by_stem[item][1].name)
            else:
                unmatched_list.append(item)
        unmatched = sorted(unmatched_list)
        filtered = [(src, rel) for src, rel in entries if rel.name in matched_names]

    return filtered, unmatched, available


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


def _copy_book(
    clone_root: Path,
    book: Book,
    dest: Path,
    vault_root: Path,
    *,
    preselected: list[tuple[Path, Path]] | None = None,
) -> Iterable[WrittenFile]:
    """Copy the book's files from *clone_root* into *dest*.

    Honours the ``files`` allowlist (D18) when set; otherwise uses the D20 walker.
    When *preselected* is given it is used directly instead of calling
    ``_select_files`` — pass this to apply item-level filtering before writing.
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

    for src_file, rel in (preselected if preselected is not None else _select_files(src_dir, book)):
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
    clone_root: Path,
    book: Book,
    dest: Path,
    vault_root: Path | None = None,
    *,
    preselected: list[tuple[Path, Path]] | None = None,
) -> Iterable[WrittenFile]:
    """Copy the book's files from *clone_root* into *dest*.

    *vault_root* is required for the write-time vault-escape guard (D25).
    When omitted, *dest* itself is used as the vault root sentinel (caller
    guarantees the path is safe — used only in tests that pre-validate dest).

    *preselected* — when provided, skip ``_select_files`` and use these
    ``(abs_src, rel)`` entries directly (e.g. after ``filter_entries_by_items``).
    """
    effective_vault_root = vault_root if vault_root is not None else dest.parent
    return _copy_book(clone_root, book, dest, effective_vault_root, preselected=preselected)


# ---------------------------------------------------------------------------
# Promotion engine (D30, D32, D33, D36)
# ---------------------------------------------------------------------------


def _relative_symlink_target(from_path: Path, to_path: Path) -> Path:
    """Compute the relative path from *from_path* to *to_path*.

    Used for creating relative symlinks per D30: e.g.
    ``.claude/agents/architect.md`` → ``../../artifacts/agents/architect.md``.
    Both paths should be absolute.
    """
    return Path(os.path.relpath(to_path, from_path.parent))


def _is_canonical_symlink(target_path: Path, vault_root: Path) -> bool:
    """Return True if *target_path* is a symlink pointing into the canonical tree.

    "Canonical tree" = any path that resolves under ``<vault_root>/artifacts/``.
    """
    if not target_path.is_symlink():
        return False
    try:
        # Resolve the symlink (relative to its parent directory)
        link_dest = Path(os.readlink(target_path))
        if not link_dest.is_absolute():
            link_dest = (target_path.parent / link_dest).resolve()
        else:
            link_dest = link_dest.resolve()
        artifacts_root = (vault_root / "artifacts").resolve()
        return link_dest.is_relative_to(artifacts_root)
    except OSError:
        return False


def promote_book(
    book: Book,
    vault_root: Path,
    *,
    mode_override: str | None = None,
    state: dict | None = None,
    dry_run: bool = False,
    clean: bool = False,
) -> PromotionReport:
    """Run the promotion step for *book* (post-canonical writes).

    This function assumes canonical files already exist under
    ``vault_root / book.dest``.  It does NOT clone or write canonical files.

    Args:
        book: The Book to promote. Must have a ``promote`` field.
        vault_root: Absolute path to the vault root.
        mode_override: Per-vault promote_mode from ArtbookSettings (D30).
                       ``None`` means use per-promotion mode or default 'symlink'.
        state: The current state dict (from read_state). Pass None to read
               from disk (convenience for callers that haven't read it yet).
        dry_run: If True, compute the report but make no filesystem changes.
        clean: If True, ignore existing ``state.promotions[<book.name>]``
               and rebuild from current canonical content.

    Returns:
        PromotionReport with the promotion result.

    Raises:
        ValueError if ``book.promote`` is None.
    """
    if book.promote is None:
        raise ValueError(f"book '{book.name}' has no promote: field; nothing to promote")

    promote: Promote = book.promote

    # Resolve effective mode (D30 precedence: per-promotion > per-vault > default symlink)
    if promote.mode is not None:
        effective_mode = promote.mode
    elif mode_override is not None:
        effective_mode = mode_override
    else:
        effective_mode = "symlink"

    target_root = vault_root / promote.target
    resolved_vault = vault_root.resolve()

    # Per-file vault-escape guard on the promote target root
    resolved_target_root = (vault_root / promote.target).resolve()
    # Note: promote.target is intentionally NOT canonical-only — it may be outside artifacts/

    # Read state
    if state is None:
        state = read_state(vault_root)

    prior_files: list = []
    if not clean:
        prior_record = state.get("promotions", {}).get(book.name, {})
        prior_files = prior_record.get("files", [])

    # Build set of prior vault-relative paths
    prior_paths: dict[str, object] = {}  # vault_rel_str → state_entry
    for entry in prior_files:
        p = entry_path(entry)
        if p:
            prior_paths[p] = entry

    # Collect current canonical entries (already written to disk)
    canonical_dir = vault_root / book.dest
    current_canonical: list[tuple[Path, Path]] = []  # (abs_canonical, rel_to_dest)
    if canonical_dir.is_dir():
        _collect_canonical(canonical_dir, canonical_dir, current_canonical)

    # Build mapping: vault_rel_target_path → abs_canonical
    current_target_paths: dict[str, Path] = {}
    for abs_can, rel in current_canonical:
        abs_target = target_root / rel
        vault_rel = str(abs_target.relative_to(vault_root))
        current_target_paths[vault_rel] = abs_can

    # --- Stale-target cleanup ---
    cleaned: list[Path] = []
    if not dry_run:
        stale_keys = set(prior_paths) - set(current_target_paths)
        for stale_vrel in stale_keys:
            stale_abs = vault_root / stale_vrel
            entry = prior_paths[stale_vrel]
            _cleanup_stale(stale_abs, entry, vault_root, cleaned)

    # --- Re-emit promotion for every current canonical file ---
    promoted: list[PromotedFile] = []
    skipped: list[Path] = []
    errors: list[str] = []
    fallback_count = 0
    fallback_warned = False

    if not dry_run:
        target_root.mkdir(parents=True, exist_ok=True)

    new_files_state: list = []

    for abs_can, rel in current_canonical:
        abs_target = target_root / rel

        # Per-file vault-escape guard
        resolved_target = (target_root / rel).resolve()
        if not resolved_target.is_relative_to(resolved_vault):
            errors.append(
                f"promotion target '{abs_target}' escapes vault root; skipping"
            )
            continue

        existed_before = abs_target.exists() or abs_target.is_symlink()

        if dry_run:
            vault_rel = str(abs_target.relative_to(vault_root))
            if effective_mode == "symlink":
                new_files_state.append(make_symlink_entry(vault_rel))
            else:
                new_files_state.append(make_copy_entry(vault_rel, "sha256:dry-run"))
            promoted.append(PromotedFile(
                canonical=abs_can,
                target=abs_target,
                mode=effective_mode,
                overwritten=existed_before,
                fallback=False,
            ))
            continue

        # Create parent dir
        abs_target.parent.mkdir(parents=True, exist_ok=True)

        used_mode = effective_mode
        fallback = False

        if effective_mode == "symlink":
            # Check if existing target is owned or user-modified
            if abs_target.exists() or abs_target.is_symlink():
                if _is_canonical_symlink(abs_target, vault_root):
                    abs_target.unlink()
                elif abs_target.is_file():
                    # Check if content matches canonical
                    try:
                        canonical_hash = file_hash(abs_can)
                        target_hash = file_hash(abs_target)
                        if canonical_hash == target_hash:
                            abs_target.unlink()
                        else:
                            # User-modified — skip
                            skipped.append(abs_target)
                            continue
                    except OSError as exc:
                        errors.append(f"could not read target '{abs_target}': {exc}")
                        continue
                elif abs_target.is_symlink():
                    # Broken symlink not pointing to canonical tree — skip
                    skipped.append(abs_target)
                    continue

            rel_link = _relative_symlink_target(abs_target, abs_can)
            try:
                os.symlink(rel_link, abs_target)
            except OSError:
                # Fallback to copy
                used_mode = "copy"
                fallback = True
                fallback_count += 1
                if not fallback_warned:
                    fallback_warned = True
                    import sys
                    print(
                        f"book '{book.name}' promotion: symlinks not supported on this "
                        "filesystem; using copy mode. "
                        "Set artbook.promote_mode: copy in artifacts.yaml to silence this notice.",
                        file=sys.stderr,
                    )

        if used_mode == "copy":
            try:
                tmp = abs_target.with_suffix(abs_target.suffix + ".tmp")
                shutil.copyfile(abs_can, tmp)
                os.replace(tmp, abs_target)
            except OSError as exc:
                errors.append(f"copy to '{abs_target}' failed: {exc}")
                continue

        # Record state entry
        vault_rel = str(abs_target.relative_to(vault_root))
        if used_mode == "symlink":
            new_files_state.append(make_symlink_entry(vault_rel))
        else:
            try:
                content_hash = file_hash(abs_can)
            except OSError:
                content_hash = "sha256:unknown"
            new_files_state.append(make_copy_entry(vault_rel, content_hash))

        promoted.append(PromotedFile(
            canonical=abs_can,
            target=abs_target,
            mode=used_mode,
            overwritten=existed_before,
            fallback=fallback,
        ))

    # Write updated state
    if not dry_run:
        state.setdefault("promotions", {})[book.name] = {
            "mode": effective_mode,
            "target_root": str(Path(promote.target)),
            "files": new_files_state,
        }
        write_state(vault_root, state)

    return PromotionReport(
        book=book,
        target_root=target_root,
        mode=effective_mode,
        promoted=tuple(promoted),
        cleaned=tuple(cleaned),
        skipped=tuple(skipped),
        fallback_count=fallback_count,
        errors=tuple(errors),
    )


def _collect_canonical(
    base_dir: Path,
    current_dir: Path,
    result: list[tuple[Path, Path]],
) -> None:
    """Recursively collect all files from *current_dir* into *result*.

    Each entry is (abs_path, rel_to_base_dir).
    """
    for item in sorted(current_dir.iterdir()):
        if item.is_symlink():
            continue  # Skip symlinks in the canonical dir
        if item.is_file():
            result.append((item, item.relative_to(base_dir)))
        elif item.is_dir():
            _collect_canonical(base_dir, item, result)


def _cleanup_stale(
    stale_abs: Path,
    entry: object,
    vault_root: Path,
    cleaned: list[Path],
) -> None:
    """Remove *stale_abs* if it is owned by the artbook promotion (D32).

    Ownership is established by:
    - For symlinks: ``os.readlink`` resolves under vault's ``artifacts/``
    - For regular files: content hash matches the recorded hash in *entry*

    Does not raise — failures are silently ignored.
    """
    try:
        if stale_abs.is_symlink():
            if _is_canonical_symlink(stale_abs, vault_root):
                stale_abs.unlink()
                cleaned.append(stale_abs)
        elif stale_abs.is_file():
            recorded_hash = entry_hash(entry)
            if recorded_hash:
                current_hash = file_hash(stale_abs)
                if current_hash == recorded_hash:
                    stale_abs.unlink()
                    cleaned.append(stale_abs)
            # If no hash recorded (symlink entry for a now-copy stale), skip
    except OSError:
        pass
