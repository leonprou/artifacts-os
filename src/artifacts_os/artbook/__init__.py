"""artbook — distro manifest, fetch, placement, and pull for artifacts-os.

Public API (spec: s0029-artbook-mvp-distribution-model §4.4, D24, D25):

Dataclasses
-----------
Book, Manifest, WrittenFile, PullReport

Functions
---------
read_manifest(distro_url, clone_into=None) -> (Manifest, Path)
find_book(manifest, name) -> Book
pull_book(book, clone_root, vault_root, distro_url="", distro_sha="") -> PullReport
destination_for(vault_root, book) -> Path

Settings
--------
ArtbookSettings

Exceptions
----------
ArtbookError, ManifestError, FetchError,
UnknownBookError, DistroNotConfiguredError
"""

from artifacts_os.artbook.errors import (
    ArtbookError,
    DistroNotConfiguredError,
    FetchError,
    ManifestError,
    UnknownBookError,
)
from artifacts_os.artbook.fetch import read_manifest
from artifacts_os.artbook.manifest import Book, Manifest
from artifacts_os.artbook.placement import WrittenFile, destination_for
from artifacts_os.artbook.pull import PullReport, find_book, pull_book
from artifacts_os.artbook.settings import ArtbookSettings

__all__ = [
    # Dataclasses
    "Book",
    "Manifest",
    "WrittenFile",
    "PullReport",
    # Functions
    "read_manifest",
    "find_book",
    "pull_book",
    "destination_for",
    # Settings
    "ArtbookSettings",
    # Exceptions
    "ArtbookError",
    "ManifestError",
    "FetchError",
    "UnknownBookError",
    "DistroNotConfiguredError",
]
