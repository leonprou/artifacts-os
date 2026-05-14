import json
from pathlib import Path

import pytest

from artifacts_os import KindDef, Registry
from artifacts_os.core.errors import ValidationError


def _write_schema(root: Path, name: str, schema: dict) -> None:
    kind_folder = root / "artifacts" / "kinds" / name
    kind_folder.mkdir(parents=True, exist_ok=True)
    (kind_folder / "kind.json").write_text(json.dumps(schema), encoding="utf-8")


def test_no_root_no_scan() -> None:
    kinds = [KindDef(name="task", dir="tasks", prefix="t", numbered=True)]
    r = Registry(kinds)
    assert r.root is None
    assert r.get("task").name == "task"
    assert len(r.all()) == 1


def test_unknown_kind_raises() -> None:
    r = Registry([])
    with pytest.raises(ValueError):
        r.get("nope")


def test_for_dir_lookup() -> None:
    kinds = [
        KindDef(name="task", dir="tasks", prefix="t", numbered=True),
        KindDef(name="agent", dir="agents", prefix="", numbered=False),
    ]
    r = Registry(kinds)
    assert r.for_dir("tasks").name == "task"
    assert r.for_dir("nonexistent") is None


def test_vault_kinds_scan(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    _write_schema(
        root,
        "changelog",
        {
            "x-prefix": "c",
            "x-numbered": True,
            "x-dir": "changelogs",
            "type": "object",
            "properties": {
                "status": {"enum": ["draft", "published"]},
            },
        },
    )
    r = Registry([], root=root)
    kd = r.get("changelog")
    assert kd.dir == "changelogs"
    assert kd.prefix == "c"
    assert kd.numbered is True
    assert kd.statuses == ["draft", "published"]


def test_vault_override_caller_kind(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    _write_schema(
        root,
        "task",
        {"x-prefix": "xx", "x-numbered": True, "x-dir": "custom"},
    )
    caller_kinds = [KindDef(name="task", dir="tasks", prefix="t", numbered=True)]
    r = Registry(caller_kinds, root=root)
    kd = r.get("task")
    assert kd.prefix == "xx"
    assert kd.dir == "custom"


def test_missing_x_dir_raises(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    _write_schema(root, "broken", {"x-prefix": "b"})
    with pytest.raises(ValidationError):
        Registry([], root=root)


def test_no_types_dir_is_noop(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    root.mkdir(parents=True)
    r = Registry(
        [KindDef(name="task", dir="tasks", prefix="t", numbered=True)],
        root=root,
    )
    assert [kd.name for kd in r.all()] == ["task"]


def test_types_dir_is_not_scanned(tmp_path: Path) -> None:
    """artifacts/types/ is not a fallback — only artifacts/kinds/ is scanned."""
    root = tmp_path / "vault"
    # Write a schema to the old types/ path only (not kinds/)
    old_types = root / "artifacts" / "types"
    old_types.mkdir(parents=True, exist_ok=True)
    (old_types / "changelog.json").write_text(
        json.dumps({"x-dir": "changelogs", "x-prefix": "c", "x-numbered": True}),
        encoding="utf-8",
    )
    r = Registry([], root=root)
    # The schema in types/ must NOT be loaded
    assert len(r.all()) == 0
    with pytest.raises(ValueError):
        r.get("changelog")


# ---------------------------------------------------------------------------
# Duplicate name validation
# ---------------------------------------------------------------------------

def _task_kind(name: str = "task") -> KindDef:
    return KindDef(name=name, dir=f"{name}s", prefix=name[0], numbered=True)


def test_registry_duplicate_kinds_raises() -> None:
    """Registry.__init__ raises ValueError for duplicate kind names in the list."""
    k = _task_kind("task")
    with pytest.raises(ValueError, match="duplicate kind 'task' in Registry kinds list"):
        Registry(kinds=[k, k])


def test_registry_duplicate_kinds_same_name_different_object() -> None:
    """Duplicate detected by name, not identity."""
    k1 = KindDef(name="task", dir="tasks", prefix="t", numbered=True)
    k2 = KindDef(name="task", dir="other", prefix="x", numbered=False)
    with pytest.raises(ValueError, match="duplicate kind 'task' in Registry kinds list"):
        Registry(kinds=[k1, k2])


def test_registry_no_duplicate_kinds_passes() -> None:
    """Distinct kind names are accepted without error."""
    k1 = _task_kind("task")
    k2 = _task_kind("agent")
    r = Registry(kinds=[k1, k2])
    assert len(r.all()) == 2


def test_vault_override_caller_kind_no_error(tmp_path: Path) -> None:
    """Vault kind overriding a caller kind is silent — no ValueError raised."""
    root = tmp_path / "vault"
    _write_schema(
        root,
        "task",
        {"x-prefix": "xx", "x-numbered": True, "x-dir": "custom"},
    )
    caller_kinds = [KindDef(name="task", dir="tasks", prefix="t", numbered=True)]
    # Must not raise; vault kind wins silently
    r = Registry(caller_kinds, root=root)
    assert r.get("task").prefix == "xx"


# ---------------------------------------------------------------------------
# KindDef.schema_properties
# ---------------------------------------------------------------------------

def test_schema_properties_task_kind(tmp_path: Path) -> None:
    """schema_properties returns the set of property names from the kind's JSON schema."""
    task_json = Path(__file__).parents[2] / "artifacts" / "kinds" / "task" / "kind.json"
    schema = json.loads(task_json.read_text(encoding="utf-8"))
    kd = KindDef(name="task", dir="tasks", prefix="t", numbered=True, schema=schema)
    expected = set(schema["properties"].keys())
    assert kd.schema_properties == expected
    # Spot-check a few known properties to guard against silent regressions
    assert {"id", "name", "status", "assignee", "owner"} <= kd.schema_properties
