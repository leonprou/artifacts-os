import json
from pathlib import Path

import pytest

from artifacts_os import KindDef, Registry
from artifacts_os.core.errors import ValidationError


def _write_schema(root: Path, name: str, schema: dict) -> None:
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True, exist_ok=True)
    (kinds_dir / f"{name}.json").write_text(json.dumps(schema), encoding="utf-8")


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
# x-layouts validation and meta["layouts"] population
# ---------------------------------------------------------------------------

def _schema_with_parent(extra: dict | None = None) -> dict:
    """Minimal vault schema with a 'parent' property for x-layouts tests."""
    schema: dict = {
        "x-dir": "tasks",
        "x-prefix": "t",
        "x-numbered": True,
        "type": "object",
        "properties": {
            "parent": {"type": "string"},
        },
    }
    if extra:
        schema.update(extra)
    return schema


def test_x_layouts_valid_populates_meta(tmp_path: Path) -> None:
    """Valid x-layouts block is parsed and placed in meta['layouts']."""
    schema = _schema_with_parent(
        {
            "x-layouts": {
                "default": "tree",
                "tree": {"parent_field": "parent"},
            }
        }
    )
    root = tmp_path / "vault"
    _write_schema(root, "task", schema)
    r = Registry([], root=root)
    layouts = r.get("task").meta["layouts"]
    assert layouts == {"default": "tree", "tree": {"parent_field": "parent"}}


def test_x_layouts_absent_keeps_meta_clean(tmp_path: Path) -> None:
    """Kind without x-layouts has no 'layouts' key in meta."""
    root = tmp_path / "vault"
    _write_schema(root, "task", {"x-dir": "tasks", "x-prefix": "t"})
    r = Registry([], root=root)
    assert "layouts" not in r.get("task").meta


def test_x_layouts_unknown_default_raises(tmp_path: Path) -> None:
    """x-layouts.default with an unrecognised value raises ValidationError."""
    schema = _schema_with_parent({"x-layouts": {"default": "board"}})
    root = tmp_path / "vault"
    _write_schema(root, "task", schema)
    with pytest.raises(ValidationError, match="unknown layout"):
        Registry([], root=root)


def test_x_layouts_tree_default_without_tree_block_raises(tmp_path: Path) -> None:
    """default='tree' without a tree block raises ValidationError."""
    schema = _schema_with_parent({"x-layouts": {"default": "tree"}})
    root = tmp_path / "vault"
    _write_schema(root, "task", schema)
    with pytest.raises(ValidationError, match="x-layouts.tree"):
        Registry([], root=root)


def test_x_layouts_parent_field_not_in_properties_raises(tmp_path: Path) -> None:
    """tree.parent_field pointing at a non-existent property raises ValidationError."""
    schema = _schema_with_parent(
        {
            "x-layouts": {
                "default": "tree",
                "tree": {"parent_field": "nonexistent"},
            }
        }
    )
    root = tmp_path / "vault"
    _write_schema(root, "task", schema)
    with pytest.raises(ValidationError, match="nonexistent"):
        Registry([], root=root)


def test_x_layouts_parent_field_not_a_string_raises(tmp_path: Path) -> None:
    """tree.parent_field that is not a string raises ValidationError."""
    schema = _schema_with_parent(
        {
            "x-layouts": {
                "default": "tree",
                "tree": {"parent_field": 42},
            }
        }
    )
    root = tmp_path / "vault"
    _write_schema(root, "task", schema)
    with pytest.raises(ValidationError, match="parent_field"):
        Registry([], root=root)


def test_x_layouts_table_default_no_tree_block(tmp_path: Path) -> None:
    """default='table' without a tree block is valid — tree is optional."""
    schema = _schema_with_parent({"x-layouts": {"default": "table"}})
    root = tmp_path / "vault"
    _write_schema(root, "task", schema)
    r = Registry([], root=root)
    assert r.get("task").meta["layouts"] == {"default": "table"}


def test_x_layouts_not_a_dict_raises(tmp_path: Path) -> None:
    """x-layouts value that is not an object raises ValidationError."""
    schema = _schema_with_parent({"x-layouts": "tree"})
    root = tmp_path / "vault"
    _write_schema(root, "task", schema)
    with pytest.raises(ValidationError, match="must be an object"):
        Registry([], root=root)
