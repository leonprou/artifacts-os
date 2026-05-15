"""Pull orchestration — fetch → place → write.

Spec: s0029-artbook-mvp-distribution-model §4.4, §6, §7
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from artifacts_os.artbook.manifest import Book, Manifest
from artifacts_os.artbook.placement import WrittenFile, copy_book, destination_for


# ---------------------------------------------------------------------------
# Dataclasses (§4.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PullReport:
    """Outcome of a pull_book call."""

    book: Book
    written: tuple[WrittenFile, ...]
    distro_url: str
    distro_sha: str  # short SHA of the cloned commit


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


def pull_book(
    book: Book,
    clone_root: Path,
    vault_root: Path,
    distro_url: str = "",
    distro_sha: str = "",
) -> PullReport:
    """Copy *book*'s content from *clone_root* into the consumer vault.

    Returns a PullReport with the list of written files.
    """
    dest = destination_for(vault_root, book)
    written = tuple(copy_book(clone_root, book, dest, vault_root=vault_root))
    return PullReport(
        book=book,
        written=written,
        distro_url=distro_url,
        distro_sha=distro_sha,
    )
