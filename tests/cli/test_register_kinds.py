"""Tests for register_kinds() validation in artifacts_os.cli."""

import json
from pathlib import Path

import pytest

from artifacts_os import KindDef
from artifacts_os.cli import register_kinds


def _make_kind(name: str) -> KindDef:
    return KindDef(name=name, dir=f"{name}s", prefix=name[0], numbered=True)


@pytest.fixture(autouse=True)
def reset_registered_kinds(monkeypatch):
    """Isolate each test by resetting the global _registered_kinds list."""
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])


# ---------------------------------------------------------------------------
# Same-call duplicate
# ---------------------------------------------------------------------------

def test_same_call_duplicate_raises() -> None:
    """register_kinds([k, k]) raises ValueError with the correct message."""
    k = _make_kind("task")
    with pytest.raises(ValueError, match="duplicate kind 'task' in register_kinds\\(\\) input"):
        register_kinds([k, k])


def test_same_call_duplicate_different_objects() -> None:
    """Duplicate detected by name, not identity."""
    k1 = KindDef(name="task", dir="tasks", prefix="t", numbered=True)
    k2 = KindDef(name="task", dir="other", prefix="x", numbered=False)
    with pytest.raises(ValueError, match="duplicate kind 'task' in register_kinds\\(\\) input"):
        register_kinds([k1, k2])


def test_same_call_no_duplicate_passes() -> None:
    """Distinct names in one call are accepted."""
    register_kinds([_make_kind("task"), _make_kind("agent")])
    import artifacts_os.cli as cli_mod
    assert len(cli_mod._registered_kinds) == 2


# ---------------------------------------------------------------------------
# Multi-call duplicate
# ---------------------------------------------------------------------------

def test_multi_call_duplicate_raises() -> None:
    """register_kinds([k]); register_kinds([k]) raises ValueError."""
    k = _make_kind("task")
    register_kinds([k])
    with pytest.raises(ValueError, match="kind 'task' is already registered"):
        register_kinds([_make_kind("task")])


def test_multi_call_different_names_passes() -> None:
    """Separate calls with distinct names are accepted."""
    register_kinds([_make_kind("task")])
    register_kinds([_make_kind("agent")])
    import artifacts_os.cli as cli_mod
    assert len(cli_mod._registered_kinds) == 2


# ---------------------------------------------------------------------------
# Vault-override-caller (no error expected)
# ---------------------------------------------------------------------------

def test_vault_overrides_caller_no_error(tmp_path: Path, monkeypatch) -> None:
    """When vault has a kind with the same name as caller, no error is raised."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts.yaml").write_text("layout_version: 1\n")
    kind_folder = kinds_dir / "task"
    kind_folder.mkdir(parents=True, exist_ok=True)
    (kind_folder / "kind.json").write_text(
        json.dumps({"x-dir": "tasks", "x-prefix": "vault", "x-numbered": True})
    )

    from artifacts_os import Registry

    caller_kind = KindDef(name="task", dir="tasks", prefix="t", numbered=True)
    # Must not raise — vault wins silently
    r = Registry(kinds=[caller_kind], root=root)
    assert r.get("task").prefix == "vault"
