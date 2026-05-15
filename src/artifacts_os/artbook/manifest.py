"""Manifest parsing and dataclasses for the artbook module.

Parses ``artbook.yaml`` from a distro repo into typed dataclasses.

Spec: s0029-artbook-mvp-distribution-model §3, §4.3, D24, D25
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from artifacts_os.artbook.errors import ManifestError

_MANIFEST_FILENAME = "artbook.yaml"
_REQUIRED_VERSION = 1


@dataclass(frozen=True)
class Book:
    """One book entry from the distro manifest (v2 schema: D24, D25, D26).

    ``files`` is an explicit allowlist (D18); ``None`` means use the D20 walker.
    ``src`` is the path relative to the distro root.
    ``dest`` is the vault-relative destination directory (D25).
    ``recurse`` (D26) — when ``True``, the walker treats each direct
    subdirectory of ``src`` as a unit and ships its full subtree to
    ``dest/<unit>/...``. Mutually exclusive with ``files``.
    """

    name: str
    src: str
    dest: str
    description: str | None = None
    files: tuple[str, ...] | None = None
    recurse: bool = False


@dataclass(frozen=True)
class Manifest:
    """Parsed distro manifest (artbook.yaml)."""

    version: int
    name: str           # distro.name
    description: str | None
    books: tuple[Book, ...]


def _parse_book(raw: Any, index: int) -> Book:
    """Parse one book entry dict, raising ManifestError on any problem."""
    if not isinstance(raw, dict):
        raise ManifestError(f"books[{index}] must be a mapping, got {type(raw).__name__}")

    # D24 — reject v1 `type:` field
    if "type" in raw:
        raise ManifestError(
            f"books[{index}] contains v1 schema field 'type' — removed in v2; "
            "remove `type:` from your manifest"
        )

    # Reject v1 `path:` field renamed to `src:` in v2
    if "path" in raw:
        raise ManifestError(
            f"books[{index}] contains v1 schema field 'path' — renamed to `src:` in v2; "
            "replace `path:` with `src:` in your manifest"
        )

    for field in ("name", "src", "dest"):
        if field not in raw:
            raise ManifestError(f"books[{index}] missing required field '{field}'")
        if not isinstance(raw[field], str) or not raw[field].strip():
            raise ManifestError(f"books[{index}].{field} must be a non-empty string")

    name: str = raw["name"]
    src: str = raw["src"]
    dest: str = raw["dest"]
    description: str | None = raw.get("description") or None

    # Reject path traversal and absolute paths on src (distro-relative)
    if src.startswith("/"):
        raise ManifestError(
            f"book '{name}' src '{src}' is absolute; src must be relative to the distro root"
        )
    if ".." in Path(src).parts:
        raise ManifestError(
            f"book '{name}' src '{src}' contains '..'; path traversal is not allowed"
        )

    # D25 — vault-escape guard on dest at parse time
    if dest.startswith("/"):
        raise ManifestError(
            f"book '{name}' dest '{dest}' is absolute; dest must be relative to the vault root"
        )
    if ".." in Path(dest).parts:
        raise ManifestError(
            f"book '{name}' dest '{dest}' contains '..'; path traversal is not allowed"
        )

    # Parse optional files allowlist (D18)
    files: tuple[str, ...] | None = None
    if "files" in raw:
        raw_files = raw["files"]
        if not isinstance(raw_files, list):
            raise ManifestError(f"book '{name}' files must be a list")
        for entry in raw_files:
            if not isinstance(entry, str):
                raise ManifestError(f"book '{name}' files entries must be strings")
            if "/" in entry or "\\" in entry:
                raise ManifestError(
                    f"book '{name}' files entry '{entry}' contains a path separator; "
                    "files entries are flat filenames relative to book.src"
                )
        files = tuple(raw_files)

    # D26 — parse optional recurse flag (default False); reject non-bool values.
    recurse: bool = False
    if "recurse" in raw:
        raw_recurse = raw["recurse"]
        if not isinstance(raw_recurse, bool):
            raise ManifestError(
                f"book '{name}' recurse must be a boolean (true/false); "
                f"got {type(raw_recurse).__name__}"
            )
        recurse = raw_recurse

    # D26 — `recurse: true` and `files: [...]` are mutually exclusive.
    if recurse and files is not None:
        raise ManifestError(
            f"book '{name}' cannot set both `recurse: true` and `files:`; "
            "they are mutually exclusive (D26). Choose one."
        )

    return Book(
        name=name,
        src=src,
        dest=dest,
        description=description,
        files=files,
        recurse=recurse,
    )


def parse_manifest(data: Any) -> Manifest:
    """Parse and validate a dict (from yaml.safe_load) into a Manifest.

    Raises ManifestError on any schema or validation problem.
    Version check (D17) runs first so old clients never partially interpret future schemas.
    """
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a YAML mapping at the top level")

    # D17 — version gate; must come first
    if "version" not in data:
        raise ManifestError("manifest is missing required field 'version'")
    version = data["version"]
    if version != _REQUIRED_VERSION:
        raise ManifestError(
            f"this artifacts-os version speaks artbook manifest v1; distro declares v{version}"
        )

    # distro section
    if "distro" not in data or not isinstance(data["distro"], dict):
        raise ManifestError("manifest is missing required 'distro' section")
    distro = data["distro"]
    if "name" not in distro or not isinstance(distro["name"], str) or not distro["name"].strip():
        raise ManifestError("manifest distro.name is required and must be a non-empty string")
    distro_name: str = distro["name"]
    distro_description: str | None = distro.get("description") or None

    # books section
    if "books" not in data:
        raise ManifestError("manifest is missing required 'books' section")
    raw_books = data["books"]
    if not isinstance(raw_books, list) or len(raw_books) == 0:
        raise ManifestError("manifest has no books")

    books: list[Book] = []
    seen_names: set[str] = set()
    for i, raw_book in enumerate(raw_books):
        book = _parse_book(raw_book, i)
        if book.name in seen_names:
            raise ManifestError(f"duplicate book name '{book.name}' in manifest")
        seen_names.add(book.name)
        books.append(book)

    return Manifest(
        version=version,
        name=distro_name,
        description=distro_description,
        books=tuple(books),
    )


def load_manifest(clone_root: Path) -> Manifest:
    """Read and parse ``artbook.yaml`` from *clone_root*.

    Raises ManifestError if the file is missing or invalid.
    """
    manifest_path = clone_root / _MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise ManifestError(f"artbook.yaml not found at distro root ({clone_root})")

    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"artbook.yaml YAML parse error: {exc}") from exc

    return parse_manifest(raw)
