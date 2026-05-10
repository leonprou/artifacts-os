"""Tests for C7 core integration — _dispatch calls in store.create/update.

Verification criteria: V10, V11, V12, V13, V14 from s0025-artifact-events.
"""
from pathlib import Path

import pytest

from artifacts_os import KindDef, Registry, create, update
from artifacts_os.core import events as _events
from artifacts_os.core.errors import BlockedByPreHook


@pytest.fixture()
def make_vault(tmp_path: Path):
    def _make():
        root = tmp_path / "vault"
        (root / "artifacts" / "tasks").mkdir(parents=True)
        (root / "artifacts.yaml").write_text("layout_version: 1\n")
        kinds = [
            KindDef(
                name="task",
                dir="tasks",
                prefix="t",
                numbered=True,
                statuses=["backlog", "ready", "in-progress", "done", "review"],
            )
        ]
        registry = Registry(kinds, root=root)
        return root, registry

    return _make


@pytest.fixture(autouse=True)
def clean_emitters():
    _events._emitters.clear()
    yield
    _events._emitters.clear()


# ---------------------------------------------------------------------------
# V10 — store.create and store.update succeed with no hooks configured
# ---------------------------------------------------------------------------


def test_create_succeeds_no_emitters(make_vault):
    root, registry = make_vault()
    a = create(registry, "task", "Test task")
    assert a.id == "t0001"


def test_update_succeeds_no_emitters(make_vault):
    root, registry = make_vault()
    a = create(registry, "task", "Test task")
    updated = update(registry, a.id, status="in-progress")
    assert updated.frontmatter["status"] == "in-progress"


# ---------------------------------------------------------------------------
# Dispatch fires correct events with correct payloads
# ---------------------------------------------------------------------------


def test_create_dispatches_artifact_created(make_vault):
    root, registry = make_vault()
    events_seen = []
    _events.register_emitter(lambda e, p: events_seen.append((e, dict(p))))

    a = create(registry, "task", "My task", fields={"status": "backlog"})

    post_events = [(e, p) for e, p in events_seen if p.get("_phase") == "post"]
    assert any(e == "artifact.created" for e, p in post_events)
    created_event = next(p for e, p in post_events if e == "artifact.created")
    assert created_event["kind"] == "task"
    assert created_event["id"] == "t0001"
    assert created_event["name"] == "my-task"
    assert "fields" in created_event


def test_update_dispatches_artifact_updated(make_vault):
    root, registry = make_vault()
    a = create(registry, "task", "My task", fields={"status": "backlog"})

    events_seen = []
    _events.register_emitter(lambda e, p: events_seen.append((e, dict(p))))

    update(registry, a.id, status="ready")

    post_events = [(e, p) for e, p in events_seen if p.get("_phase") == "post"]
    assert any(e == "artifact.updated" for e, p in post_events)
    upd = next(p for e, p in post_events if e == "artifact.updated")
    assert "status" in upd["changed"]
    assert upd["before"]["status"] == "backlog"
    assert upd["after"]["status"] == "ready"


# ---------------------------------------------------------------------------
# V14 — artifact.status_changed dispatched after artifact.updated when status changed
# ---------------------------------------------------------------------------


def test_update_dispatches_status_changed_when_status_in_changed(make_vault):
    root, registry = make_vault()
    a = create(registry, "task", "My task", fields={"status": "backlog"})

    events_seen = []
    _events.register_emitter(lambda e, p: events_seen.append((e, dict(p))))

    update(registry, a.id, status="ready")

    post_events = [e for e, p in events_seen if p.get("_phase") == "post"]
    assert "artifact.updated" in post_events
    assert "artifact.status_changed" in post_events

    # status_changed must come AFTER updated
    idx_updated = post_events.index("artifact.updated")
    idx_changed = post_events.index("artifact.status_changed")
    assert idx_changed > idx_updated


def test_update_status_changed_payload_has_scalar_before_after(make_vault):
    root, registry = make_vault()
    a = create(registry, "task", "My task", fields={"status": "backlog"})

    status_changed_payloads = []
    _events.register_emitter(
        lambda e, p: status_changed_payloads.append(dict(p))
        if e == "artifact.status_changed" else None
    )

    update(registry, a.id, status="ready")
    assert len(status_changed_payloads) == 1
    payload = status_changed_payloads[0]
    # before/after must be scalar strings, not dicts
    assert payload["before"] == "backlog"
    assert payload["after"] == "ready"


def test_update_does_not_dispatch_status_changed_when_status_not_changed(make_vault):
    """V14 — artifact.status_changed must NOT fire when status is unchanged."""
    root, registry = make_vault()
    a = create(registry, "task", "My task", fields={"status": "backlog"})

    events_seen = []
    _events.register_emitter(lambda e, p: events_seen.append(e))

    # Update a non-status field only
    update(registry, a.id, fields={"assignee": "developer"})

    assert "artifact.status_changed" not in events_seen


# ---------------------------------------------------------------------------
# V11 — pre-phase hook with blocking=true aborts CRUD, file unchanged
# ---------------------------------------------------------------------------


def test_pre_blocking_hook_aborts_create(make_vault):
    root, registry = make_vault()

    def blocking_pre(event, payload):
        if payload.get("_phase") == "pre" and event == "artifact.created":
            raise BlockedByPreHook("blocked by test")

    _events.register_emitter(blocking_pre)

    with pytest.raises(BlockedByPreHook):
        create(registry, "task", "Should not be created")

    # File must not exist
    tasks_dir = root / "artifacts" / "tasks"
    assert list(tasks_dir.glob("*.md")) == []


def test_pre_blocking_hook_aborts_update(make_vault):
    root, registry = make_vault()
    a = create(registry, "task", "Existing task", fields={"status": "backlog"})

    def blocking_pre(event, payload):
        if payload.get("_phase") == "pre" and event == "artifact.updated":
            raise BlockedByPreHook("update blocked")

    _events.register_emitter(blocking_pre)

    with pytest.raises(BlockedByPreHook):
        update(registry, a.id, status="ready")

    # Status must be unchanged
    from artifacts_os import get
    artifact = get(registry, a.id)
    assert artifact.frontmatter.get("status") == "backlog"


# ---------------------------------------------------------------------------
# V12 — pre-phase hook with blocking=false warns but CRUD completes
# ---------------------------------------------------------------------------


def test_pre_non_blocking_hook_warns_and_crud_completes(make_vault, capsys):
    root, registry = make_vault()

    def warn_pre(event, payload):
        if payload.get("_phase") == "pre":
            raise RuntimeError("non-blocking failure")  # not BlockedByPreHook

    _events.register_emitter(warn_pre)

    # Must NOT raise — non-blocking
    a = create(registry, "task", "Should exist")
    assert a.id == "t0001"
    captured = capsys.readouterr()
    assert "warning" in captured.err


# ---------------------------------------------------------------------------
# V13 — post-phase hook failure never affects CRUD outcome
# ---------------------------------------------------------------------------


def test_post_hook_failure_does_not_affect_crud(make_vault, capsys):
    root, registry = make_vault()

    def bad_post(event, payload):
        if payload.get("_phase") == "post":
            raise RuntimeError("post failure")

    _events.register_emitter(bad_post)

    # create must succeed despite post emitter failure
    a = create(registry, "task", "Post-fail task")
    assert a.id == "t0001"
    captured = capsys.readouterr()
    assert "warning" in captured.err
