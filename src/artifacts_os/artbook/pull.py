"""Pull orchestration — fetch → place → write → promote.

Spec: s0029-artbook-mvp-distribution-model §4.4, §6, §7
     s0031-artbook-post-pull-artifact-promotion D33, D36
     s0032-hooks-via-artbook §8.2 (kind: hook pull semantics)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from artifacts_os.artbook.manifest import Book, Manifest
from artifacts_os.artbook.placement import (
    PromotionReport,
    WrittenFile,
    copy_book,
    destination_for,
    promote_book,
)
from artifacts_os.artbook.state import read_state


# ---------------------------------------------------------------------------
# Dataclasses (§4.3, D33)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PullReport:
    """Outcome of a pull_book call (extended per D33)."""

    book: Book
    written: tuple[WrittenFile, ...]
    distro_url: str
    distro_sha: str                             # short SHA of the cloned commit
    promotion: PromotionReport | None = None    # None if no promote: or skipped (D33)
    promotion_skipped_reason: str | None = None # 'flag' | 'setting' | None (D33)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def find_book(manifest: Manifest, name: str) -> Book:
    """Return the Book with *name* from *manifest*.

    Raises UnknownBookError if not found.
    """
    from artifacts_os.artbook.errors import UnknownBookError

    for book in manifest.books:
        if book.name == name:
            return book
    available = ", ".join(b.name for b in manifest.books)
    raise UnknownBookError(
        f"book '{name}' not found in distro '{manifest.name}'; available books: {available}"
    )


def _slugs_from_written(written: tuple[WrittenFile, ...], dest: Path) -> tuple[list[str], list[str]]:
    """Extract (written_slugs, overwritten_slugs) from a set of WrittenFile records.

    For a recurse book (hook books are always recurse), each destination path
    has the form ``<dest>/<slug>/...``.  The slug is the first path component
    relative to *dest*.

    Returns two de-duped slug lists (order: first appearance in *written*).
    """
    seen_written: dict[str, bool] = {}  # slug → any_overwritten
    for wf in written:
        try:
            rel = wf.destination.relative_to(dest)
        except ValueError:
            continue
        if not rel.parts:
            continue
        slug = rel.parts[0]
        if slug not in seen_written:
            seen_written[slug] = wf.overwritten
        elif wf.overwritten:
            seen_written[slug] = True

    written_slugs = [s for s, ov in seen_written.items() if not ov]
    overwritten_slugs = [s for s, ov in seen_written.items() if ov]
    return written_slugs, overwritten_slugs


def _pre_existing_bundle_slugs(dest: Path) -> set[str]:
    """Return the set of existing bundle dir names under *dest* (ignoring dotfile dirs)."""
    if not dest.is_dir():
        return set()
    return {
        d.name
        for d in dest.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    }


def pull_book(
    book: Book,
    clone_root: Path,
    vault_root: Path,
    distro_url: str = "",
    distro_sha: str = "",
    *,
    preselected: list[tuple[Path, Path]] | None = None,
    no_promote: bool = False,
    promote_disabled: bool = False,
    promote_mode_override: str | None = None,
) -> PullReport:
    """Copy *book*'s content from *clone_root* into the consumer vault.

    *preselected* — when provided, only these ``(abs_src, rel)`` entries
    are written.  Pass the result of ``filter_entries_by_items`` to limit
    the pull to a consumer-specified subset of items.

    *no_promote* — when True, skip the promotion step (--no-promote flag, D31).
      For ``kind: hook`` books this flag is accepted but is a no-op (D117).
    *promote_disabled* — when True, skip promotion due to settings (D31).
    *promote_mode_override* — per-vault artbook.promote_mode value (D30).

    Returns a PullReport with canonical writes and optional PromotionReport.
    Promotion failures are non-fatal-for-canonical but set exit code to 1
    (the caller checks report.promotion.errors; D36).
    """
    dest = destination_for(vault_root, book)

    # For kind: hook books, record pre-existing bundles to compute "removed" list.
    pre_existing: set[str] = set()
    if book.kind == "hook":
        pre_existing = _pre_existing_bundle_slugs(dest)

    written = tuple(copy_book(clone_root, book, dest, vault_root=vault_root, preselected=preselected))

    # D36 — canonical writes complete before promotion runs.
    promotion: PromotionReport | None = None
    skipped_reason: str | None = None

    if book.kind == "hook":
        # D117: hook books never auto-promote; --no-promote is a no-op.
        # Emit hook.pulled event once per book (s0032 §5, §8.2).
        from artifacts_os.core import events as _events
        from artifacts_os.events.catalog import HOOK_PULLED

        written_slugs, overwritten_slugs = _slugs_from_written(written, dest)
        all_new_slugs = set(written_slugs) | set(overwritten_slugs)
        removed_slugs = sorted(pre_existing - all_new_slugs)

        _events._dispatch(
            HOOK_PULLED,
            book=book.name,
            written=sorted(written_slugs),
            overwritten=sorted(overwritten_slugs),
            removed=removed_slugs,
        )
    elif book.promote is not None:
        if no_promote:
            skipped_reason = "flag"
        elif promote_disabled:
            skipped_reason = "setting"
        else:
            # Run the promotion step. Failures are non-fatal for canonical writes.
            state = read_state(vault_root)
            promotion = promote_book(
                book,
                vault_root,
                mode_override=promote_mode_override,
                state=state,
            )

    return PullReport(
        book=book,
        written=written,
        distro_url=distro_url,
        distro_sha=distro_sha,
        promotion=promotion,
        promotion_skipped_reason=skipped_reason,
    )
