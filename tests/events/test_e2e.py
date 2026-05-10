"""End-to-end tests for s0025 — four worked-example audiences.

Verification criteria: V16 from s0025-artifact-events.

Audience 1: Agent self-assigns via hook
Audience 2: User CLI hook (file-drop as proxy for notify)
Audience 3: External app tailing the JSONL stream
Audience 4: Async runtime via catch-all hook
"""
import json
from pathlib import Path

import pytest

from artifacts_os import KindDef, Registry, create, update
from artifacts_os.core import events as _events
from artifacts_os.events import stream as _stream
from artifacts_os.hooks.loader import invalidate_cache, notify as _hook_notify


# ---------------------------------------------------------------------------
# Shared vault factory
# ---------------------------------------------------------------------------


def _make_vault(root: Path) -> tuple[Path, Registry]:
    (root / "artifacts" / "tasks").mkdir(parents=True)
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


def _write_yaml(root: Path, content: str) -> None:
    (root / "artifacts" / "artifacts.yaml").write_text(content)


@pytest.fixture(autouse=True)
def reset_emitters():
    """Clear emitter state and hook cache before/after each test."""
    _events._emitters.clear()
    invalidate_cache()
    yield
    _events._emitters.clear()
    invalidate_cache()


def _register_stream(root: Path, monkeypatch) -> None:
    """Register stream emitter pointing at *root*."""
    monkeypatch.setattr("artifacts_os.events.stream.find_vault_root", lambda: root)
    _events.register_emitter(_stream.append)


def _register_hooks(root: Path, monkeypatch) -> None:
    """Register hook notify emitter pointing at *root*."""
    import artifacts_os.hooks.loader as _hook_loader
    monkeypatch.setattr(_hook_loader, "find_vault_root", lambda: root)
    invalidate_cache()
    _events.register_emitter(_hook_notify)


# ---------------------------------------------------------------------------
# Audience 1 — Agent self-assigns via file-drop hook
# ---------------------------------------------------------------------------


def test_audience1_agent_reaction_via_file_drop(tmp_path, monkeypatch):
    """Agent reacts to new spec-typed task by writing a file-drop notification.

    Uses file-drop (testable) instead of shell ``artifacts update`` to avoid
    CLI recursion in tests.  The hook fires and the drop file is written.
    """
    root, registry = _make_vault(tmp_path / "vault")
    drop_path = str(root / "artifacts" / ".notifications" / "{event}-{id}.json")

    _write_yaml(
        root,
        f"""
layout_version: 1
project:
  name: test
hooks:
  - name: agent-claims-spec-tasks
    matcher:
      event: artifact.created
      kind: task
      fields.type: spec
    action:
      type: file-drop
      path: "{drop_path}"
      payload: summary
""",
    )

    _register_hooks(root, monkeypatch)

    a = create(registry, "task", "Design auth module", fields={"type": "spec"})

    notifications_dir = root / "artifacts" / ".notifications"
    drops = list(notifications_dir.glob("*.json"))
    assert drops, "Expected a file-drop notification from the agent hook"
    record = json.loads(drops[0].read_text())
    assert record.get("event") == "artifact.created"


def test_audience1_non_spec_task_does_not_fire(tmp_path, monkeypatch):
    """Hook with fields.type: spec does NOT fire for tasks without type: spec."""
    root, registry = _make_vault(tmp_path / "vault")
    drop_path = str(root / "artifacts" / ".notifications" / "{event}-{id}.json")

    _write_yaml(
        root,
        f"""
layout_version: 1
project:
  name: test
hooks:
  - name: agent-claims-spec-tasks
    matcher:
      event: artifact.created
      kind: task
      fields.type: spec
    action:
      type: file-drop
      path: "{drop_path}"
      payload: summary
""",
    )

    _register_hooks(root, monkeypatch)
    create(registry, "task", "Regular task")  # no type: spec

    notifications_dir = root / "artifacts" / ".notifications"
    drops = list(notifications_dir.glob("*.json")) if notifications_dir.exists() else []
    assert drops == [], "Hook should not fire for non-spec tasks"


# ---------------------------------------------------------------------------
# Audience 2 — User CLI hook via file-drop
# ---------------------------------------------------------------------------


def test_audience2_user_file_drop_on_status_change(tmp_path, monkeypatch):
    """User hook fires on artifact.status_changed and drops a file."""
    root, registry = _make_vault(tmp_path / "vault")
    drop_path = str(root / "artifacts" / ".notifications" / "review-{id}.json")

    _write_yaml(
        root,
        f"""
layout_version: 1
project:
  name: test
hooks:
  - name: notify-review-ready
    matcher:
      event: artifact.status_changed
      kind: task
      after: review
    action:
      type: file-drop
      path: "{drop_path}"
      payload: full
""",
    )

    _register_hooks(root, monkeypatch)

    a = create(registry, "task", "Fix security issue", fields={"status": "ready"})
    update(registry, a.id, status="review")

    drops = list((root / "artifacts" / ".notifications").glob("review-*.json"))
    assert drops, "Expected file-drop on transition to review"
    record = json.loads(drops[0].read_text())
    assert record.get("event") == "artifact.status_changed"


def test_audience2_hook_does_not_fire_for_other_status(tmp_path, monkeypatch):
    """Hook for after: review does NOT fire when transitioning to a different status."""
    root, registry = _make_vault(tmp_path / "vault")
    drop_path = str(root / "artifacts" / ".notifications" / "review-{id}.json")

    _write_yaml(
        root,
        f"""
layout_version: 1
project:
  name: test
hooks:
  - name: notify-review-ready
    matcher:
      event: artifact.status_changed
      after: review
    action:
      type: file-drop
      path: "{drop_path}"
      payload: full
""",
    )

    _register_hooks(root, monkeypatch)

    a = create(registry, "task", "Task", fields={"status": "backlog"})
    update(registry, a.id, status="in-progress")

    notifications_dir = root / "artifacts" / ".notifications"
    drops = list(notifications_dir.glob("*.json")) if notifications_dir.exists() else []
    assert drops == [], "Hook for 'review' should not fire on 'in-progress'"


# ---------------------------------------------------------------------------
# Audience 3 — External app tailing the JSONL stream
# ---------------------------------------------------------------------------


def test_audience3_external_app_tails_jsonl(tmp_path, monkeypatch):
    """Create artifacts and verify the JSONL stream is readable externally."""
    root, registry = _make_vault(tmp_path / "vault")
    _write_yaml(root, "layout_version: 1\nproject:\n  name: test\n")
    _register_stream(root, monkeypatch)

    create(registry, "task", "External app test", fields={"status": "backlog"})
    update(registry, "t0001", status="in-progress")

    events_dir = root / "artifacts" / "logs" / "events"
    assert events_dir.is_dir()
    jsonl_files = list(events_dir.glob("*.jsonl"))
    assert jsonl_files

    all_records = []
    for f in jsonl_files:
        for line in f.read_text().splitlines():
            if line.strip():
                all_records.append(json.loads(line))

    event_types = [r["event"] for r in all_records]
    assert "artifact.created" in event_types
    assert "artifact.updated" in event_types
    assert "artifact.status_changed" in event_types

    # Verify all records have ts and event fields (V1)
    for rec in all_records:
        assert "ts" in rec, f"Missing ts in {rec}"
        assert "event" in rec, f"Missing event in {rec}"


# ---------------------------------------------------------------------------
# Audience 4 — Async runtime via catch-all hook
# ---------------------------------------------------------------------------


def test_audience4_catch_all_hook_receives_every_event(tmp_path, monkeypatch):
    """Catch-all hook (event: '*') receives all events for async dispatch."""
    root, registry = _make_vault(tmp_path / "vault")
    drop_path = str(root / "async-drop-{event}-{id}.json")

    _write_yaml(
        root,
        f"""
layout_version: 1
project:
  name: test
hooks:
  - name: forward-all-to-async-runtime
    matcher:
      event: "*"
    action:
      type: file-drop
      path: "{drop_path}"
      payload: full
""",
    )

    _register_hooks(root, monkeypatch)

    a = create(registry, "task", "Async test task", fields={"status": "backlog"})
    update(registry, a.id, status="ready")

    drops = list(root.glob("async-drop-*.json"))
    # Expect artifact.created, artifact.updated, artifact.status_changed at minimum
    # (hook.fired events also fire, but they use hook payload which has no kind/id)
    art_drops = [
        f for f in drops
        if any(evt in f.name for evt in ["artifact.created", "artifact.updated", "artifact.status_changed"])
    ]
    assert len(art_drops) >= 3


# ---------------------------------------------------------------------------
# Stream is always-on regardless of hooks being loaded
# ---------------------------------------------------------------------------


def test_stream_always_on_without_hooks(tmp_path, monkeypatch):
    """The stream writes events even when no hooks module is imported."""
    root, registry = _make_vault(tmp_path / "vault")
    _write_yaml(root, "layout_version: 1\nproject:\n  name: test\n")
    _register_stream(root, monkeypatch)

    create(registry, "task", "Stream only", fields={"status": "backlog"})

    events_dir = root / "artifacts" / "logs" / "events"
    lines = []
    for f in events_dir.glob("*.jsonl"):
        for line in f.read_text().splitlines():
            if line.strip():
                lines.append(json.loads(line))

    assert any(r["event"] == "artifact.created" for r in lines)
