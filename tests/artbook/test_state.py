"""Tests for artbook.state — read_state, write_state, helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.artbook.state import (
    entry_hash,
    entry_path,
    file_hash,
    make_copy_entry,
    make_symlink_entry,
    read_state,
    write_state,
)


def test_read_state_absent_file(tmp_path: Path) -> None:
    state = read_state(tmp_path)
    assert state["version"] == 1
    assert state["promotions"] == {}


def test_write_read_roundtrip(tmp_path: Path) -> None:
    state = {
        "version": 1,
        "promotions": {
            "agents": {
                "mode": "symlink",
                "target_root": ".claude/agents",
                "files": [".claude/agents/architect.md"],
            }
        },
    }
    write_state(tmp_path, state)
    loaded = read_state(tmp_path)
    assert loaded["promotions"]["agents"]["mode"] == "symlink"
    assert ".claude/agents/architect.md" in loaded["promotions"]["agents"]["files"]


def test_string_form_entry_backwards_compat(tmp_path: Path) -> None:
    """String-form entries are symlink mode."""
    state = {
        "version": 1,
        "promotions": {
            "agents": {
                "mode": "symlink",
                "target_root": ".claude/agents",
                "files": [".claude/agents/architect.md"],
            }
        },
    }
    write_state(tmp_path, state)
    loaded = read_state(tmp_path)
    files = loaded["promotions"]["agents"]["files"]
    assert len(files) == 1
    assert entry_path(files[0]) == ".claude/agents/architect.md"
    assert entry_hash(files[0]) is None  # symlink entry has no hash


def test_copy_mode_entry_has_hash(tmp_path: Path) -> None:
    entry = make_copy_entry(".claude/agents/architect.md", "sha256:abc123")
    assert entry_path(entry) == ".claude/agents/architect.md"
    assert entry_hash(entry) == "sha256:abc123"


def test_symlink_entry_helpers(tmp_path: Path) -> None:
    entry = make_symlink_entry(".claude/agents/architect.md")
    assert entry_path(entry) == ".claude/agents/architect.md"
    assert entry_hash(entry) is None


def test_write_state_creates_parent_dirs(tmp_path: Path) -> None:
    """The state dir (artifacts/.artbook/) doesn't exist yet."""
    state = {"version": 1, "promotions": {}}
    write_state(tmp_path, state)
    state_file = tmp_path / "artifacts" / ".artbook" / "state.json"
    assert state_file.is_file()


def test_file_hash_deterministic(tmp_path: Path) -> None:
    f = tmp_path / "test.md"
    f.write_bytes(b"hello world")
    h1 = file_hash(f)
    h2 = file_hash(f)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_file_hash_different_content(tmp_path: Path) -> None:
    f1 = tmp_path / "a.md"
    f2 = tmp_path / "b.md"
    f1.write_bytes(b"content a")
    f2.write_bytes(b"content b")
    assert file_hash(f1) != file_hash(f2)


def test_read_state_bad_json_returns_empty(tmp_path: Path) -> None:
    state_dir = tmp_path / "artifacts" / ".artbook"
    state_dir.mkdir(parents=True)
    (state_dir / "state.json").write_text("not valid json")
    state = read_state(tmp_path)
    assert state["promotions"] == {}


def test_write_state_atomic_via_tmp(tmp_path: Path) -> None:
    """write_state uses tmp file approach — verify final file exists and tmp is gone."""
    state = {"version": 1, "promotions": {}}
    write_state(tmp_path, state)
    state_file = tmp_path / "artifacts" / ".artbook" / "state.json"
    tmp_file = state_file.with_suffix(".json.tmp")
    assert state_file.is_file()
    # Tmp file should be cleaned up after atomic replace
    assert not tmp_file.exists()


def test_entry_path_returns_none_for_unknown_type() -> None:
    assert entry_path(42) is None
    assert entry_path(None) is None


def test_entry_hash_returns_none_for_string() -> None:
    assert entry_hash(".claude/agents/architect.md") is None
