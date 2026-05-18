"""artbook — distro manifest, fetch, placement, and pull for artifacts-os.

Public API (spec: s0029-artbook-mvp-distribution-model §4.4, D24, D25
            s0031-artbook-post-pull-artifact-promotion D29, D33):

Dataclasses
-----------
Book, Manifest, Promote, WrittenFile, PullReport,
PromotedFile, PromotionReport

Functions
---------
read_manifest(distro_url, clone_into=None) -> (Manifest, Path)
find_book(manifest, name) -> Book
pull_book(book, clone_root, vault_root, distro_url="", distro_sha="") -> PullReport
promote_book(book, vault_root, *, mode_override, state, dry_run, clean) -> PromotionReport
destination_for(vault_root, book) -> Path
filter_entries_by_items(entries, items, *, recurse) -> (filtered, unmatched, available)

Settings
--------
ArtbookSettings

Exceptions
----------
ArtbookError, ManifestError, FetchError,
UnknownBookError, DistroNotConfiguredError,
PromotionError, SettingsError
"""

from artifacts_os.artbook.errors import (
    ArtbookError,
    DistroNotConfiguredError,
    FetchError,
    ManifestError,
    PromotionError,
    SettingsError,
    UnknownBookError,
)
from artifacts_os.artbook.fetch import read_manifest
from artifacts_os.artbook.manifest import Book, Manifest, Promote
from artifacts_os.artbook.placement import (
    PromotedFile,
    PromotionReport,
    WrittenFile,
    destination_for,
    filter_entries_by_items,
    promote_book,
)
from artifacts_os.artbook.pull import PullReport, find_book, pull_book
from artifacts_os.artbook.settings import ArtbookSettings

__all__ = [
    # Dataclasses
    "Book",
    "Manifest",
    "Promote",
    "WrittenFile",
    "PullReport",
    "PromotedFile",
    "PromotionReport",
    # Functions
    "read_manifest",
    "find_book",
    "pull_book",
    "promote_book",
    "destination_for",
    "filter_entries_by_items",
    # Settings
    "ArtbookSettings",
    # Exceptions
    "ArtbookError",
    "ManifestError",
    "FetchError",
    "UnknownBookError",
    "DistroNotConfiguredError",
    "PromotionError",
    "SettingsError",
]
