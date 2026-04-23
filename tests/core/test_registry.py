import json
from pathlib import Path

import pytest

from artifacts_os import KindDef, Registry
from artifacts_os.core.errors import ValidationError


def _write_schema(root: Path, name: str, schema: dict) -> None:
    types = root / "artifacts" / "types"
    types.mkdir(parents=True, exist_ok=True)
    (types / f"{name}.json").write_text(json.dumps(schema), encoding="utf-8")


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


def test_vault_types_scan(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    (root / ".openstation").mkdir(parents=True)
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
    (root / ".openstation").mkdir(parents=True)
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
    (root / ".openstation").mkdir(parents=True)
    _write_schema(root, "broken", {"x-prefix": "b"})
    with pytest.raises(ValidationError):
        Registry([], root=root)


def test_no_types_dir_is_noop(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    (root / ".openstation").mkdir(parents=True)
    r = Registry(
        [KindDef(name="task", dir="tasks", prefix="t", numbered=True)],
        root=root,
    )
    assert [kd.name for kd in r.all()] == ["task"]
