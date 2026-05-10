from pathlib import Path

import pytest

from artifacts_os import KindDef, Registry, create, get, update
from artifacts_os.core.errors import ValidationError


def test_create_numbered(make_vault) -> None:
    root, registry = make_vault()
    a = create(registry, "task", "Fix the bug")
    assert a.id == "t0001"
    # Persisted `name` is slug-only; the id-prefixed stem lives in the path.
    assert a.name == "fix-the-bug"
    assert a.path.stem == "t0001-fix-the-bug"
    assert a.path.name == "t0001-fix-the-bug.md"
    assert a.path.parent == root / "artifacts" / "tasks"


def test_create_increments(make_vault) -> None:
    _, registry = make_vault()
    create(registry, "task", "First")
    a = create(registry, "task", "Second")
    assert a.id == "t0002"


def test_create_non_numbered_agent(make_vault) -> None:
    root, registry = make_vault()
    a = create(registry, "agent", "researcher")
    assert a.id == "researcher"
    assert a.name == "researcher"
    assert a.path.name == "researcher.md"


def test_create_non_numbered_collision(make_vault) -> None:
    _, registry = make_vault()
    create(registry, "agent", "researcher")
    with pytest.raises(FileExistsError):
        create(registry, "agent", "researcher")


def test_create_empty_title_raises(make_vault) -> None:
    _, registry = make_vault()
    with pytest.raises(ValidationError):
        create(registry, "task", "!!!")


def test_create_schema_validation_fails(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    (root / "artifacts" / "tasks").mkdir(parents=True)
    (root / "artifacts.yaml").write_text("layout_version: 1\n")
    kinds = [
        KindDef(
            name="task",
            dir="tasks",
            prefix="t",
            numbered=True,
            schema={
                "type": "object",
                "required": ["priority"],
                "properties": {"priority": {"type": "string"}},
                "additionalProperties": True,
            },
        )
    ]
    registry = Registry(kinds, root=root)
    with pytest.raises(ValidationError):
        create(registry, "task", "No priority field")


def test_get_reads_body_and_title(make_vault) -> None:
    _, registry = make_vault()
    a = create(
        registry,
        "task",
        "Title",
        body="# Real H1 Title\n\nBody content.",
    )
    fetched = get(registry, a.id)
    assert fetched.title == "Real H1 Title"
    assert "Body content." in fetched.body


def test_get_no_h1_falls_back_to_name(make_vault) -> None:
    _, registry = make_vault()
    a = create(registry, "task", "Fix it", body="Plain body with no heading.")
    fetched = get(registry, a.id)
    assert fetched.title == a.name


def test_update_status(make_vault) -> None:
    _, registry = make_vault()
    a = create(registry, "task", "Do something")
    updated = update(registry, a.id, status="ready")
    assert updated.status == "ready"


def test_update_invalid_status(make_vault) -> None:
    _, registry = make_vault()
    a = create(registry, "task", "Do something")
    with pytest.raises(ValidationError):
        update(registry, a.id, status="bogus")


def test_update_preserves_body(make_vault) -> None:
    _, registry = make_vault()
    body = "# Heading\n\nKeep me verbatim.\n"
    a = create(registry, "task", "T", body=body)
    updated = update(registry, a.id, status="ready")
    text = updated.path.read_text(encoding="utf-8")
    assert "Keep me verbatim." in text


def test_update_merges_fields(make_vault) -> None:
    _, registry = make_vault()
    a = create(registry, "task", "T", fields={"owner": "alice"})
    updated = update(registry, a.id, fields={"priority": "high"})
    assert updated.frontmatter["owner"] == "alice"
    assert updated.frontmatter["priority"] == "high"
