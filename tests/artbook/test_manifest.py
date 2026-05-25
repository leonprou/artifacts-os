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
        "books": [{"name": "agents", "src": "agents/", "dest": "artifacts/agents/"}],
    }
    m = parse_manifest(data)
    assert m.version == 1
    assert m.name == "my-distro"
    assert m.description is None
    assert len(m.books) == 1
    assert m.books[0] == Book(name="agents", src="agents/", dest="artifacts/agents/")


def test_parse_manifest_with_description_and_files() -> None:
    data = {
        "version": 1,
        "distro": {"name": "full-distro", "description": "Full distro."},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "dest": "artifacts/agents/",
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
            {"name": "agents", "src": "a/", "dest": "artifacts/a/"},
            {"name": "agents", "src": "b/", "dest": "artifacts/b/"},
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
    """D37: `dest:` is optional; when absent it defaults to `artifacts/<basename(src)>/`."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "agents/"}],
    }
    m = parse_manifest(data)
    # D37 default: artifacts/<basename(src)>/ = artifacts/agents/
    assert m.books[0].dest == "artifacts/agents/"


def test_parse_manifest_missing_src() -> None:
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "dest": "artifacts/agents/"}],
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
                "dest": "artifacts/agents/",
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
        "books": [{"name": "agents", "src": "agents/", "dest": "artifacts/agents/"}],
    }
    (tmp_path / "artbook.yaml").write_text(yaml.dump(data))
    m = load_manifest(tmp_path)
    assert m.name == "roundtrip"
    assert m.books[0].name == "agents"
    assert m.books[0].src == "agents/"
    assert m.books[0].dest == "artifacts/agents/"


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


# ---------------------------------------------------------------------------
# parse_manifest — recurse flag (D26)
# ---------------------------------------------------------------------------


def test_parse_book_recurse_default_false() -> None:
    """D26: `recurse` defaults to False when absent."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "agents/", "dest": "artifacts/agents/"}],
    }
    m = parse_manifest(data)
    assert m.books[0].recurse is False


def test_parse_book_recurse_true() -> None:
    """D26: `recurse: true` parses to Book.recurse=True."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "skills",
                "src": "skills/",
                "dest": "artifacts/skills/",
                "recurse": True,
            }
        ],
    }
    m = parse_manifest(data)
    assert m.books[0].recurse is True


def test_parse_book_recurse_false_explicit() -> None:
    """D26: `recurse: false` is accepted and equivalent to default."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "dest": "artifacts/agents/",
                "recurse": False,
            }
        ],
    }
    m = parse_manifest(data)
    assert m.books[0].recurse is False


def test_parse_book_recurse_rejects_int() -> None:
    """D26: non-bool `recurse` (int) is rejected with a clear error."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "skills",
                "src": "skills/",
                "dest": "artifacts/skills/",
                "recurse": 1,
            }
        ],
    }
    with pytest.raises(ManifestError, match="recurse must be a boolean"):
        parse_manifest(data)


def test_parse_book_recurse_rejects_string() -> None:
    """D26: non-bool `recurse` (string) is rejected with a clear error."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "skills",
                "src": "skills/",
                "dest": "artifacts/skills/",
                "recurse": "true",
            }
        ],
    }
    with pytest.raises(ManifestError, match="recurse must be a boolean"):
        parse_manifest(data)


def test_parse_book_recurse_and_files_mutually_exclusive() -> None:
    """D26: setting both `recurse: true` and `files:` is rejected."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "skills",
                "src": "skills/",
                "dest": "artifacts/skills/",
                "recurse": True,
                "files": ["SKILL.md"],
            }
        ],
    }
    with pytest.raises(ManifestError, match="mutually exclusive"):
        parse_manifest(data)


# ---------------------------------------------------------------------------
# D28 — canonical-only dest constraint
# ---------------------------------------------------------------------------


def test_parse_manifest_dest_must_be_under_artifacts() -> None:
    """D28: dest not under artifacts/ is rejected with a clear migration hint."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "agents/", "dest": ".claude/agents/"}],
    }
    with pytest.raises(ManifestError, match="not under 'artifacts/'"):
        parse_manifest(data)


def test_parse_manifest_dest_nested_under_artifacts_is_valid() -> None:
    """D28: dest nested under artifacts/ is accepted."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "agents/", "dest": "artifacts/my/agents/"}],
    }
    m = parse_manifest(data)
    assert m.books[0].dest == "artifacts/my/agents/"


def test_parse_manifest_promote_field_accepts_tool_path() -> None:
    """D29: promote: can target a tool-specific path like .claude/agents/."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "dest": "artifacts/agents/",
                "promote": ".claude/agents/",
            }
        ],
    }
    m = parse_manifest(data)
    assert m.books[0].promote is not None
    assert m.books[0].promote.target == ".claude/agents/"


# ---------------------------------------------------------------------------
# D37 — default dest from src basename
# ---------------------------------------------------------------------------


def test_parse_manifest_default_dest_from_src() -> None:
    """D37: when dest is absent, default is artifacts/<basename(src)>/."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "agents/"}],
    }
    m = parse_manifest(data)
    assert m.books[0].dest == "artifacts/agents/"


def test_parse_manifest_default_dest_nested_src() -> None:
    """D37: basename is computed correctly even for nested src paths."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "tools", "src": "some/tools/"}],
    }
    m = parse_manifest(data)
    assert m.books[0].dest == "artifacts/tools/"


def test_parse_manifest_default_dest_src_skills() -> None:
    """D37: src=src/skills/ → dest=artifacts/skills/ (task spec representative value)."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "skills", "src": "src/skills/"}],
    }
    m = parse_manifest(data)
    assert m.books[0].dest == "artifacts/skills/"


def test_parse_manifest_default_dest_kinds() -> None:
    """D37: src=kinds/ → dest=artifacts/kinds/ (task spec representative value)."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "kinds", "src": "kinds/"}],
    }
    m = parse_manifest(data)
    assert m.books[0].dest == "artifacts/kinds/"


# ---------------------------------------------------------------------------
# D29 — promote: field parsing (string shorthand, object form, rejection cases)
# ---------------------------------------------------------------------------


def test_parse_manifest_promote_string_shorthand_mode_is_none() -> None:
    """D29: string shorthand → Promote(target=<path>, mode=None)."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "agents/", "promote": ".claude/agents/"}],
    }
    m = parse_manifest(data)
    p = m.books[0].promote
    assert p is not None
    assert p.target == ".claude/agents/"
    assert p.mode is None


def test_parse_manifest_promote_object_form_with_mode() -> None:
    """D29: object form with explicit mode parses correctly."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "promote": {"target": ".claude/agents/", "mode": "copy"},
            }
        ],
    }
    m = parse_manifest(data)
    p = m.books[0].promote
    assert p is not None
    assert p.target == ".claude/agents/"
    assert p.mode == "copy"


def test_parse_manifest_promote_object_form_mode_symlink() -> None:
    """D29: object form with mode: symlink parses correctly."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "promote": {"target": ".claude/agents/", "mode": "symlink"},
            }
        ],
    }
    m = parse_manifest(data)
    p = m.books[0].promote
    assert p is not None
    assert p.mode == "symlink"


def test_parse_manifest_promote_object_form_no_mode_is_none() -> None:
    """D29: object form without mode field → Promote.mode=None."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "promote": {"target": ".claude/agents/"},
            }
        ],
    }
    m = parse_manifest(data)
    p = m.books[0].promote
    assert p is not None
    assert p.target == ".claude/agents/"
    assert p.mode is None


def test_parse_manifest_promote_rejects_unknown_mode() -> None:
    """D29: promote.mode must be 'symlink' or 'copy'; anything else is ManifestError."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "promote": {"target": ".claude/agents/", "mode": "hardlink"},
            }
        ],
    }
    with pytest.raises(ManifestError, match="promote.mode must be 'symlink' or 'copy'"):
        parse_manifest(data)


def test_parse_manifest_promote_rejects_missing_target() -> None:
    """D29: object form without 'target' field raises ManifestError."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "promote": {"mode": "copy"},
            }
        ],
    }
    with pytest.raises(ManifestError, match="requires a 'target' field"):
        parse_manifest(data)


def test_parse_manifest_promote_rejects_empty_string() -> None:
    """D29: empty string target raises ManifestError."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "promote": "   ",
            }
        ],
    }
    with pytest.raises(ManifestError, match="non-empty string"):
        parse_manifest(data)


def test_parse_manifest_promote_rejects_empty_mapping() -> None:
    """D29: empty mapping raises ManifestError."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "promote": {},
            }
        ],
    }
    with pytest.raises(ManifestError, match="must not be empty"):
        parse_manifest(data)


def test_parse_manifest_promote_rejects_list() -> None:
    """D29: list form is explicitly rejected (deferred per spec)."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "promote": [".claude/agents/", ".cursor/rules/"],
            }
        ],
    }
    with pytest.raises(ManifestError, match="must be a string or a mapping, not a list"):
        parse_manifest(data)


def test_parse_manifest_promote_rejects_non_string_non_mapping() -> None:
    """D29: neither string nor mapping (e.g. integer) raises ManifestError."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "promote": 42,
            }
        ],
    }
    with pytest.raises(ManifestError, match="must be a string or a mapping"):
        parse_manifest(data)


def test_parse_manifest_promote_rejects_dotdot_target() -> None:
    """D29: promote.target with '..' raises ManifestError (vault-escape guard)."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "promote": "../outside/.claude/agents/",
            }
        ],
    }
    with pytest.raises(ManifestError, match=r"'\.\.'"):
        parse_manifest(data)


def test_parse_manifest_promote_rejects_absolute_target() -> None:
    """D29: absolute promote.target raises ManifestError."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "promote": "/etc/claude/agents/",
            }
        ],
    }
    with pytest.raises(ManifestError, match="absolute"):
        parse_manifest(data)


def test_parse_manifest_promote_target_outside_artifacts_is_permitted() -> None:
    """D29: promote.target outside artifacts/ is valid (promote exists for this purpose)."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "promote": ".cursor/rules/",
            }
        ],
    }
    m = parse_manifest(data)
    p = m.books[0].promote
    assert p is not None
    assert p.target == ".cursor/rules/"


def test_manifest_has_no_warnings_field() -> None:
    """D38: Manifest dataclass has no warnings field (strictly fail-fast)."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "agents/", "dest": "artifacts/agents/"}],
    }
    m = parse_manifest(data)
    assert not hasattr(m, "warnings")


# ---------------------------------------------------------------------------
# D116-D118 — kind: hook book field
# ---------------------------------------------------------------------------


def test_parse_book_kind_hook_sets_field_and_auto_recurse() -> None:
    """D116/D118: kind: hook sets Book.kind and auto-sets recurse=True."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {"name": "os-hooks", "src": "artifacts/hooks/", "kind": "hook"}
        ],
    }
    m = parse_manifest(data)
    b = m.books[0]
    assert b.kind == "hook"
    assert b.recurse is True


def test_parse_book_kind_hook_explicit_recurse_true_ok() -> None:
    """D118: explicit recurse: true on kind: hook is harmless."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "os-hooks",
                "src": "artifacts/hooks/",
                "kind": "hook",
                "recurse": True,
            }
        ],
    }
    m = parse_manifest(data)
    assert m.books[0].recurse is True


def test_parse_book_kind_hook_rejects_explicit_recurse_false() -> None:
    """D118: kind: hook with recurse: false raises ManifestError."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "os-hooks",
                "src": "artifacts/hooks/",
                "kind": "hook",
                "recurse": False,
            }
        ],
    }
    with pytest.raises(ManifestError, match="explicit `recurse: false` is not"):
        parse_manifest(data)


def test_parse_book_kind_hook_rejects_promote() -> None:
    """D117: kind: hook + promote: raises ManifestError with exact wording."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {
                "name": "os-hooks",
                "src": "artifacts/hooks/",
                "kind": "hook",
                "promote": ".claude/hooks/",
            }
        ],
    }
    with pytest.raises(
        ManifestError,
        match=r"book 'os-hooks' has `kind: hook`; hook books cannot declare "
              r"`promote:` — activation is an explicit operator step",
    ):
        parse_manifest(data)


def test_parse_book_kind_unknown_value_rejected() -> None:
    """D116: unknown kind: values raise ManifestError (closed enum)."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {"name": "weird", "src": "weird/", "kind": "skill"}
        ],
    }
    with pytest.raises(ManifestError, match="is not a recognised book type"):
        parse_manifest(data)


def test_parse_book_kind_empty_string_rejected() -> None:
    """kind: must be a non-empty string."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {"name": "x", "src": "x/", "kind": "   "}
        ],
    }
    with pytest.raises(ManifestError, match="kind must be a non-empty string"):
        parse_manifest(data)


def test_parse_book_kind_independent_from_v1_type() -> None:
    """D116: new kind: field is parsed independently of the rejected v1 type: field."""
    # type: alone still raises (regression check)
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [
            {"name": "x", "src": "x/", "type": "agents"}
        ],
    }
    with pytest.raises(ManifestError, match="v1 schema field"):
        parse_manifest(data)


def test_parse_book_kind_absent_defaults_to_none() -> None:
    """When kind: is absent, Book.kind is None (default)."""
    data = {
        "version": 1,
        "distro": {"name": "x"},
        "books": [{"name": "agents", "src": "agents/"}],
    }
    m = parse_manifest(data)
    assert m.books[0].kind is None
