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
