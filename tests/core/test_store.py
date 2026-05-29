from pathlib import Path

import pytest

from artifacts_os import KindDef, Registry, create, get, update
from artifacts_os.core.errors import ValidationError
from artifacts_os.core.store import get_prop, set_prop


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


# ---------------------------------------------------------------------------
# Per-property state-machine integration tests (s0033)
# ---------------------------------------------------------------------------


def _sm_kind(make_vault, statuses=None, initial=None, transitions=None) -> tuple:
    """Build a make_vault result with a state-machined 'widget' kind.

    Uses a simple state machine on the 'status' property.
    """
    from artifacts_os.core.models import StateMachineDef

    enum = tuple(statuses or ["new", "active", "done"])
    sm = StateMachineDef(
        enum=enum,
        initial=initial,
        transitions=(
            {k: tuple(v) for k, v in transitions.items()}
            if transitions is not None
            else None
        ),
    )
    kd = KindDef(
        name="widget",
        dir="widgets",
        prefix="w",
        numbered=True,
        statuses=list(enum),
        state_machines={"status": sm},
    )
    return make_vault([kd])


def test_create_injects_initial_state_machine(make_vault) -> None:
    """D223: create() without status injects initial from state machine."""
    _, registry = _sm_kind(make_vault, statuses=["new", "active"], initial="new",
                            transitions={"new": ["active"], "active": []})
    a = create(registry, "widget", "My Widget")
    assert a.frontmatter["status"] == "new"


def test_create_rejects_non_initial_state_machine(make_vault) -> None:
    """D203: create() with status != initial raises ValidationError."""
    _, registry = _sm_kind(make_vault, statuses=["new", "active"], initial="new",
                            transitions={"new": ["active"]})
    with pytest.raises(ValidationError) as exc_info:
        create(registry, "widget", "Bad Start", fields={"status": "active"})
    assert "Illegal initial value" in str(exc_info.value)


def test_create_accepts_initial_explicitly_set(make_vault) -> None:
    """D203: create() with status == initial succeeds."""
    _, registry = _sm_kind(make_vault, statuses=["new", "active"], initial="new",
                            transitions={"new": ["active"]})
    a = create(registry, "widget", "Ok", fields={"status": "new"})
    assert a.frontmatter["status"] == "new"


def test_update_legal_transition(make_vault) -> None:
    """Legal transition via update() succeeds."""
    _, registry = _sm_kind(
        make_vault,
        statuses=["new", "active", "done"],
        initial="new",
        transitions={"new": ["active"], "active": ["done"]},
    )
    a = create(registry, "widget", "W")
    updated = update(registry, a.id, fields={"status": "active"})
    assert updated.frontmatter["status"] == "active"


def test_update_illegal_transition_raises_d212(make_vault) -> None:
    """D212: illegal transition via update() raises ValidationError."""
    _, registry = _sm_kind(
        make_vault,
        statuses=["new", "active", "done"],
        initial="new",
        transitions={"new": ["active"], "active": ["done"]},
    )
    a = create(registry, "widget", "W")
    with pytest.raises(ValidationError) as exc_info:
        update(registry, a.id, fields={"status": "done"})  # new → done not allowed
    msg = str(exc_info.value)
    assert "Illegal transition" in msg
    assert "status" in msg


def test_update_wildcard_target_accepted(make_vault) -> None:
    """D205: target in transitions['*'] is accepted even if not in current's row."""
    from artifacts_os.core.models import StateMachineDef
    sm = StateMachineDef(
        enum=("new", "active", "cancelled"),
        initial="new",
        transitions={
            "new": ("active",),
            "active": (),  # terminal, except wildcard
            "*": ("cancelled",),
        },
    )
    kd = KindDef(
        name="widget", dir="widgets", prefix="w", numbered=True,
        statuses=["new", "active", "cancelled"],
        state_machines={"status": sm},
    )
    _, registry = make_vault([kd])
    a = create(registry, "widget", "W")
    u = update(registry, a.id, fields={"status": "active"})
    # active has no explicit exits but wildcard allows cancelled
    u2 = update(registry, a.id, fields={"status": "cancelled"})
    assert u2.frontmatter["status"] == "cancelled"


def test_create_no_state_machine_passthrough(make_vault) -> None:
    """Kinds without state machines: create() is unchanged."""
    _, registry = make_vault()
    a = create(registry, "task", "Normal Task")
    assert a.id.startswith("t")


def test_update_via_vault_loaded_task_kind(tmp_path: Path) -> None:
    """End-to-end: vault-loaded task kind with permissive transitions accepts any status."""
    import json
    task_json = Path(__file__).parents[2] / "artifacts" / "kinds" / "task" / "kind.json"
    schema = json.loads(task_json.read_text(encoding="utf-8"))
    root = tmp_path / "vault"
    kind_dir = root / "artifacts" / "kinds" / "task"
    kind_dir.mkdir(parents=True)
    (kind_dir / "kind.json").write_text(json.dumps(schema), encoding="utf-8")
    (root / "artifacts" / "tasks").mkdir(parents=True, exist_ok=True)
    (root / "artifacts.yaml").write_text("layout_version: 1\n")
    registry = Registry([], root=root)
    kd = registry.get("task")
    # Verify state machine is loaded
    assert "status" in kd.state_machines
    assert kd.state_machines["status"].initial == "backlog"
    # Create a task — status=backlog injected
    a = create(registry, "task", "Test Task",
                fields={"type": "feature", "assignee": "dev", "owner": "user",
                        "created": "2026-01-01"})
    assert a.frontmatter["status"] == "backlog"
    # Update to in-progress (permissive table allows it)
    u = update(registry, a.id, fields={"status": "in-progress"})
    assert u.frontmatter["status"] == "in-progress"


# ---------------------------------------------------------------------------
# get_prop / set_prop (t0189)
# ---------------------------------------------------------------------------


def test_get_prop_returns_value(make_vault) -> None:
    """get_prop returns the current value of a frontmatter property."""
    _, registry = make_vault()
    a = create(registry, "task", "Test Task")
    # 'status' is injected as 'backlog' by the state machine
    val = get_prop(registry, a.id, "status")
    assert val == "backlog"


def test_get_prop_returns_non_status_field(make_vault) -> None:
    """get_prop works for free-form properties too."""
    _, registry = make_vault()
    a = create(registry, "task", "Task", fields={"assignee": "alice"})
    assert get_prop(registry, a.id, "assignee") == "alice"


def test_get_prop_unknown_property_raises(make_vault) -> None:
    """get_prop raises ValidationError on a property absent from frontmatter."""
    _, registry = make_vault()
    a = create(registry, "task", "Task")
    with pytest.raises(ValidationError) as exc_info:
        get_prop(registry, a.id, "nonexistent_field")
    msg = str(exc_info.value)
    assert "Unknown property" in msg
    assert "nonexistent_field" in msg


def test_set_prop_round_trip(make_vault) -> None:
    """set_prop writes the property; get_prop reads back the new value."""
    _, registry = make_vault()
    a = create(registry, "task", "Task")
    assert get_prop(registry, a.id, "status") == "backlog"

    set_prop(registry, a.id, "status", "ready")
    assert get_prop(registry, a.id, "status") == "ready"


def test_set_prop_free_form_property(make_vault) -> None:
    """set_prop writes a free-form (non-state-machined) property."""
    _, registry = make_vault()
    a = create(registry, "task", "Task")
    updated = set_prop(registry, a.id, "assignee", "bob")
    assert updated.frontmatter["assignee"] == "bob"


def test_set_prop_transition_validated(make_vault) -> None:
    """set_prop delegates to update(); illegal transitions are rejected."""
    from artifacts_os.core.models import StateMachineDef
    sm = StateMachineDef(
        enum=("open", "closed"),
        initial="open",
        transitions={"open": ("closed",), "closed": ()},
    )
    kd = KindDef(
        name="ticket", dir="tickets", prefix="x", numbered=True,
        state_machines={"status": sm},
    )
    _, registry = make_vault([kd])
    a = create(registry, "ticket", "Bug")
    assert a.frontmatter["status"] == "open"

    # Legal: open → closed
    set_prop(registry, a.id, "status", "closed")

    # Illegal: closed → open (no back-edge)
    with pytest.raises(ValidationError) as exc_info:
        set_prop(registry, a.id, "status", "open")
    msg = str(exc_info.value)
    assert "Illegal transition" in msg
    assert "status" in msg


def test_set_prop_preserves_body(make_vault) -> None:
    """set_prop does not modify the artifact body."""
    _, registry = make_vault()
    body = "# Heading\n\nKeep me verbatim.\n"
    a = create(registry, "task", "Task", body=body)
    set_prop(registry, a.id, "status", "ready")
    text = a.path.read_text(encoding="utf-8")
    assert "Keep me verbatim." in text
