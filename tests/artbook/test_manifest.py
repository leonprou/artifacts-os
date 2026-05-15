"""Tests for artbook.manifest — parsing, validation, and dataclasses."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from artifacts_os.artbook.errors import ManifestError
from artifacts_os.artbook.manifest import Book, Manifest, load_manifest, parse_manifest


# ---------------------------------------------------------------------------
# parse_manifest — happy path
# ---------------------------------------------------------------------------


def test_parse_minimal_manifest() -> None:
    data = {
        "version": 1,
        "distro": {"name": "my-distro"},
        "books": [{"name": "agents", "type": "agents", "path": "agents/"}],
    }
    m = parse_manifest(data)
    assert m.version == 1
    assert m.name == "my-distro"
    assert m.description is None
    assert len(m.books) == 1
    assert m.books[0] == Book(name="agents", type="agents", path="agents/")


def test_parse_manifest_with_description_and_files() -> None:
    data = {
        "version": 1,
        "distro": {"name": "full-distro", "description": "Full distro."},
        "books": [
            {
                "name": "agents",
                "type": "agents",
                "path": "agents/",
                "description": "Agents book.",
                "files": ["architect.md", "developer.md"],
            }
        ],
    }
    m = parse_manifest(data)
    assert m.description == "Full distro."
    b = m.books[0]
    assert b.description == "Agents book."
    assert b.files == ("architect.md", "developer.md")


# ---------------------------------------------------------------------------
# parse_manifest — version mismatch (D17)
# ---------------------------------------------------------------------------


def test_parse_manifest_version_mismatch() -> None:
    data = {
        "version": 2,
        "distro": {"name": "future-distro"},
        "books": [{"name": "agents", "type": "agents", "path": "agents/"}],
    }
    with pytest.raises(ManifestError, match="speaks artbook manifest v1; distro declares v2"):
        parse_manifest(data)


def test_parse_manifest_missing_version() -> None:
    data = {
        "distro": {"name": "x"},
        "books": [{"name": "agents", "type": "agents", "path": "agents/"}],
    }
    with pytest.raises(ManifestError, match="missing required field 'version'"):
        parse_manifest(data)


# ---------------------------------------------------------------------------
# parse_manifest — structural errors
# ---------------------------------------------------------------------------


def test_parse_manifest_missing_distro() -> None:
    data = {
        "version": 1,
        "books": [{"name": "agents", "type": "agents", "path": "agents/"}],
    }
    with pytest.raises(ManifestError, match="missing required 'distro' section"):
        parse_manifest(data)


def test_parse_manifest_empty_books() -> None:
    data = {"version": 1, "distro": {"name": "x"}, "books": []}
    with pytest.raises(ManifestError, match="has no books"):
        parse_manifest(data)


def test_parse_manifest_missing_books() -> None:
    data = {"version": 1, "distro": {"name": "x"}}
    with pytest.raises(ManifestError, match="missing required 'books' section"):
        parse_manifest(data)


def test_parse_manifest_duplicate_book_name() -> None:
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {"name": "agents", "type": "agents", "path": "a/"},
            {"name": "agents", "type": "agents", "path": "b/"},
        ],
    }
    with pytest.raises(ManifestError, match="duplicate book name 'agents'"):
        parse_manifest(data)


def test_parse_manifest_book_absolute_path() -> None:
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "type": "agents", "path": "/etc/agents/"}],
    }
    with pytest.raises(ManifestError, match="absolute"):
        parse_manifest(data)


def test_parse_manifest_book_path_traversal() -> None:
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "type": "agents", "path": "../agents/"}],
    }
    with pytest.raises(ManifestError, match=r"'\.\.'"):
        parse_manifest(data)


def test_parse_manifest_files_entry_with_slash() -> None:
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "type": "agents",
                "path": "agents/",
                "files": ["sub/file.md"],
            }
        ],
    }
    with pytest.raises(ManifestError, match="path separator"):
        parse_manifest(data)


# ---------------------------------------------------------------------------
# load_manifest — file I/O
# ---------------------------------------------------------------------------


def test_load_manifest_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="artbook.yaml not found"):
        load_manifest(tmp_path)


def test_load_manifest_roundtrip(tmp_path: Path) -> None:
    data = {
        "version": 1,
        "distro": {"name": "roundtrip"},
        "books": [{"name": "agents", "type": "agents", "path": "agents/"}],
    }
    (tmp_path / "artbook.yaml").write_text(yaml.dump(data))
    m = load_manifest(tmp_path)
    assert m.name == "roundtrip"
    assert m.books[0].name == "agents"


def test_load_manifest_invalid_yaml(tmp_path: Path) -> None:
    (tmp_path / "artbook.yaml").write_text(": invalid: yaml: ][")
    with pytest.raises(ManifestError, match="YAML parse error"):
        load_manifest(tmp_path)
