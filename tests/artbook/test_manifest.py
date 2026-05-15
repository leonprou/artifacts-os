"""Tests for artbook.manifest — parsing, validation, and dataclasses (v2 schema)."""

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
        "books": [{"name": "agents", "src": "agents/", "dest": ".claude/agents/"}],
    }
    m = parse_manifest(data)
    assert m.version == 1
    assert m.name == "my-distro"
    assert m.description is None
    assert len(m.books) == 1
    assert m.books[0] == Book(name="agents", src="agents/", dest=".claude/agents/")


def test_parse_manifest_with_description_and_files() -> None:
    data = {
        "version": 1,
        "distro": {"name": "full-distro", "description": "Full distro."},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "dest": ".claude/agents/",
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
        "books": [{"name": "agents", "src": "agents/", "dest": ".claude/agents/"}],
    }
    with pytest.raises(ManifestError, match="speaks artbook manifest v1; distro declares v2"):
        parse_manifest(data)


def test_parse_manifest_missing_version() -> None:
    data = {
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "agents/", "dest": ".claude/agents/"}],
    }
    with pytest.raises(ManifestError, match="missing required field 'version'"):
        parse_manifest(data)


# ---------------------------------------------------------------------------
# parse_manifest — structural errors
# ---------------------------------------------------------------------------


def test_parse_manifest_missing_distro() -> None:
    data = {
        "version": 1,
        "books": [{"name": "agents", "src": "agents/", "dest": ".claude/agents/"}],
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
            {"name": "agents", "src": "a/", "dest": ".claude/a/"},
            {"name": "agents", "src": "b/", "dest": ".claude/b/"},
        ],
    }
    with pytest.raises(ManifestError, match="duplicate book name 'agents'"):
        parse_manifest(data)


# ---------------------------------------------------------------------------
# parse_manifest — v2 migration rejections (D24, D25)
# ---------------------------------------------------------------------------


def test_parse_manifest_rejects_v1_type_field() -> None:
    """D24: `type:` must be rejected with a clear migration hint."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "type": "agents", "src": "agents/", "dest": ".claude/agents/"}],
    }
    with pytest.raises(ManifestError, match="v1 schema field.*type.*removed in v2"):
        parse_manifest(data)


def test_parse_manifest_rejects_v1_path_field() -> None:
    """`path:` must be rejected with a 'renamed to src:' hint."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "path": "agents/", "dest": ".claude/agents/"}],
    }
    with pytest.raises(ManifestError, match="renamed to `src:`"):
        parse_manifest(data)


def test_parse_manifest_missing_dest() -> None:
    """D25: `dest:` is required on every book entry."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "agents/"}],
    }
    with pytest.raises(ManifestError, match="missing required field 'dest'"):
        parse_manifest(data)


def test_parse_manifest_missing_src() -> None:
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "dest": ".claude/agents/"}],
    }
    with pytest.raises(ManifestError, match="missing required field 'src'"):
        parse_manifest(data)


# ---------------------------------------------------------------------------
# parse_manifest — vault-escape guard on src and dest (D25)
# ---------------------------------------------------------------------------


def test_parse_manifest_book_absolute_src() -> None:
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "/etc/agents/", "dest": ".claude/agents/"}],
    }
    with pytest.raises(ManifestError, match="absolute"):
        parse_manifest(data)


def test_parse_manifest_book_src_traversal() -> None:
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "../agents/", "dest": ".claude/agents/"}],
    }
    with pytest.raises(ManifestError, match=r"'\.\.'"):
        parse_manifest(data)


def test_parse_manifest_book_absolute_dest() -> None:
    """D25: absolute dest must be rejected at parse time."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "agents/", "dest": "/etc/agents/"}],
    }
    with pytest.raises(ManifestError, match="absolute"):
        parse_manifest(data)


def test_parse_manifest_book_dest_traversal() -> None:
    """D25: dest containing '..' must be rejected at parse time."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "agents/", "dest": "../outside/"}],
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
                "src": "agents/",
                "dest": ".claude/agents/",
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
        "books": [{"name": "agents", "src": "agents/", "dest": ".claude/agents/"}],
    }
    (tmp_path / "artbook.yaml").write_text(yaml.dump(data))
    m = load_manifest(tmp_path)
    assert m.name == "roundtrip"
    assert m.books[0].name == "agents"
    assert m.books[0].src == "agents/"
    assert m.books[0].dest == ".claude/agents/"


def test_load_manifest_invalid_yaml(tmp_path: Path) -> None:
    (tmp_path / "artbook.yaml").write_text(": invalid: yaml: ][")
    with pytest.raises(ManifestError, match="YAML parse error"):
        load_manifest(tmp_path)


def test_load_manifest_rejects_v1_artbook_yaml(tmp_path: Path) -> None:
    """v1 artbook.yaml with type:/path: fails with migration hints."""
    v1_data = {
        "version": 1,
        "distro": {"name": "old-distro"},
        "books": [{"name": "agents", "type": "agents", "path": "agents/"}],
    }
    (tmp_path / "artbook.yaml").write_text(yaml.dump(v1_data))
    with pytest.raises(ManifestError, match="removed in v2"):
        load_manifest(tmp_path)
