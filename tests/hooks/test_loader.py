"""Tests for hooks/loader.py — C4 hook loader.

Verification criteria: V6, V7 from s0025-artifact-events.
"""
import json
from pathlib import Path

import pytest
import yaml

from artifacts_os.core import events as _events
from artifacts_os.core.errors import BlockedByPreHook
from artifacts_os.hooks.loader import (
    Hook,
    load_hooks,
    match,
    run_matched,
    invalidate_cache,
)


@pytest.fixture(autouse=True)
def clean_emitters():
    _events._emitters.clear()
    invalidate_cache()
    yield
    _events._emitters.clear()
    invalidate_cache()


def _write_yaml(root: Path, content: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "artifacts.yaml").write_text(content)


# ---------------------------------------------------------------------------
# V6 — loader validation
# ---------------------------------------------------------------------------


def test_load_hooks_empty_section(tmp_path):
    _write_yaml(tmp_path, "layout_version: 1\nproject:\n  name: test\n")
    hooks = load_hooks(tmp_path)
    assert hooks == []


def test_load_hooks_missing_hooks_key(tmp_path):
    _write_yaml(tmp_path, "layout_version: 1\nproject:\n  name: test\n")
    hooks = load_hooks(tmp_path)
    assert hooks == []


def test_load_hooks_empty_list(tmp_path):
    _write_yaml(
        tmp_path,
        "layout_version: 1\nproject:\n  name: test\nhooks: []\n",
    )
    hooks = load_hooks(tmp_path)
    assert hooks == []


def test_load_hooks_rejects_missing_name(tmp_path):
    _write_yaml(
        tmp_path,
        "layout_version: 1\nproject:\n  name: test\nhooks:\n"
        "  - matcher:\n      event: artifact.created\n    action:\n      type: shell\n      command: echo\n",
    )
    with pytest.raises(ValueError, match="missing required 'name'"):
        load_hooks(tmp_path)


def test_load_hooks_rejects_missing_action_type(tmp_path):
    _write_yaml(
        tmp_path,
        "layout_version: 1\nproject:\n  name: test\nhooks:\n"
        "  - name: bad\n    matcher:\n      event: artifact.created\n    action:\n      command: echo\n",
    )
    with pytest.raises(ValueError, match="missing action.type"):
        load_hooks(tmp_path)


def test_load_hooks_rejects_unknown_matcher_key(tmp_path):
    _write_yaml(
        tmp_path,
        "layout_version: 1\nproject:\n  name: test\nhooks:\n"
        "  - name: bad\n    matcher:\n      event: artifact.created\n      unknown_key: foo\n"
        "    action:\n      type: shell\n      command: echo\n",
    )
    with pytest.raises(ValueError, match="unknown matcher key"):
        load_hooks(tmp_path)


def test_load_hooks_valid(tmp_path):
    _write_yaml(
        tmp_path,
        """
layout_version: 1
project:
  name: test
hooks:
  - name: my-hook
    matcher:
      event: artifact.created
      kind: task
    action:
      type: shell
      command: "echo $ART_ID"
    phase: post
    blocking: false
    timeout: 10
""",
    )
    hooks = load_hooks(tmp_path)
    assert len(hooks) == 1
    h = hooks[0]
    assert h.name == "my-hook"
    assert h.phase == "post"
    assert h.blocking is False
    assert h.timeout == 10


def test_load_hooks_valid_known_matcher_prefixes(tmp_path):
    """fields.<key>, before.<key>, after.<key>, path.* are valid."""
    _write_yaml(
        tmp_path,
        """
layout_version: 1
project:
  name: test
hooks:
  - name: h
    matcher:
      event: artifact.updated
      fields.status: review
      before.status: ready
      after.status: review
    action:
      type: shell
      command: echo
""",
    )
    hooks = load_hooks(tmp_path)
    assert len(hooks) == 1


# ---------------------------------------------------------------------------
# Matcher engine tests
# ---------------------------------------------------------------------------


def _shell_hook(name: str, matcher: dict, phase: str = "post", blocking: bool = False) -> Hook:
    from artifacts_os.hooks.actions import ShellAction
    return Hook(
        name=name,
        matcher=matcher,
        action=ShellAction(command="true"),
        phase=phase,
        blocking=blocking,
    )


def test_match_by_event():
    hook = _shell_hook("h", {"event": "artifact.created"})
    assert match([hook], "artifact.created", {}, phase="post") == [hook]
    assert match([hook], "artifact.updated", {}, phase="post") == []


def test_match_wildcard_event():
    hook = _shell_hook("h", {"event": "*"})
    assert match([hook], "artifact.created", {}, phase="post") == [hook]
    assert match([hook], "artifact.updated", {}, phase="post") == [hook]


def test_match_by_kind():
    hook = _shell_hook("h", {"event": "artifact.created", "kind": "task"})
    assert match([hook], "artifact.created", {"kind": "task"}, phase="post") == [hook]
    assert match([hook], "artifact.created", {"kind": "spec"}, phase="post") == []


def test_match_by_phase():
    pre = _shell_hook("pre", {"event": "artifact.created"}, phase="pre")
    post = _shell_hook("post", {"event": "artifact.created"}, phase="post")
    assert match([pre, post], "artifact.created", {}, phase="pre") == [pre]
    assert match([pre, post], "artifact.created", {}, phase="post") == [post]


def test_match_list_value_or_semantics():
    hook = _shell_hook("h", {"kind": ["task", "spec"]})
    assert match([hook], "artifact.created", {"kind": "task"}, phase="post") == [hook]
    assert match([hook], "artifact.created", {"kind": "spec"}, phase="post") == [hook]
    assert match([hook], "artifact.created", {"kind": "agent"}, phase="post") == []


def test_match_nested_fields_key():
    hook = _shell_hook("h", {"event": "artifact.updated", "fields.assignee": "developer"})
    payload = {"fields": {"assignee": "developer", "status": "ready"}}
    assert match([hook], "artifact.updated", payload, phase="post") == [hook]
    payload2 = {"fields": {"assignee": "user", "status": "ready"}}
    assert match([hook], "artifact.updated", payload2, phase="post") == []


def test_match_after_scalar(artifact_status_changed_payload=None):
    hook = _shell_hook("h", {"event": "artifact.status_changed", "after": "review"})
    payload = {"before": "ready", "after": "review"}
    assert match([hook], "artifact.status_changed", payload, phase="post") == [hook]
    payload2 = {"before": "ready", "after": "in-progress"}
    assert match([hook], "artifact.status_changed", payload2, phase="post") == []


def test_match_changed_list():
    hook = _shell_hook("h", {"event": "artifact.updated", "changed": ["status"]})
    payload = {"changed": ["status", "assignee"]}
    assert match([hook], "artifact.updated", payload, phase="post") == [hook]
    payload2 = {"changed": ["assignee"]}
    assert match([hook], "artifact.updated", payload2, phase="post") == []


# ---------------------------------------------------------------------------
# V7 — hook.fired and hook.failed events in the JSONL stream
# ---------------------------------------------------------------------------


def test_hook_fired_event_emitted(tmp_path):
    from artifacts_os.hooks.actions import ShellAction

    fired = []
    _events.register_emitter(lambda e, p: fired.append((e, p)))

    hook = Hook(
        name="good-hook",
        matcher={"event": "artifact.created"},
        action=ShellAction(command="true"),
        phase="post",
        blocking=False,
    )
    run_matched([hook], "artifact.created", {"kind": "task"}, root=tmp_path)
    fired_events = [e for e, p in fired if p.get("_phase") != "pre"]
    assert any(e == "hook.fired" for e, p in fired)


def test_hook_failed_event_emitted_non_blocking(tmp_path, capsys):
    from artifacts_os.hooks.actions import ShellAction

    failed_events = []
    _events.register_emitter(
        lambda e, p: failed_events.append(e) if e == "hook.failed" else None
    )

    hook = Hook(
        name="bad-hook",
        matcher={"event": "artifact.created"},
        action=ShellAction(command="exit 1"),
        phase="post",
        blocking=False,
    )
    # Should NOT raise
    run_matched([hook], "artifact.created", {"kind": "task"}, root=tmp_path)
    assert "hook.failed" in failed_events


def test_hook_failed_blocking_pre_raises(tmp_path):
    from artifacts_os.hooks.actions import ShellAction

    hook = Hook(
        name="blocking-hook",
        matcher={"event": "artifact.created"},
        action=ShellAction(command="exit 1"),
        phase="pre",
        blocking=True,
    )
    with pytest.raises(BlockedByPreHook, match="blocking-hook"):
        run_matched([hook], "artifact.created", {"kind": "task"}, root=tmp_path)
