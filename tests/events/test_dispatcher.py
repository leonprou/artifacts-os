"""Tests for core/events.py — C2 dispatcher.

Verification criteria: V2, V3 from s0025-artifact-events.
"""
import ast
import io
import sys
from pathlib import Path

import pytest

from artifacts_os.core import events as _events
from artifacts_os.core.errors import BlockedByPreHook


@pytest.fixture(autouse=True)
def clean_emitters():
    """Ensure _emitters is empty before and after each test."""
    _events._emitters.clear()
    yield
    _events._emitters.clear()


# ---------------------------------------------------------------------------
# V2 — _dispatch swallows every emitter exception and prints to stderr
# ---------------------------------------------------------------------------


def test_dispatch_calls_registered_emitter():
    captured = []
    _events.register_emitter(lambda e, p: captured.append((e, p)))
    _events._dispatch("artifact.created", kind="task", id="t0001")
    assert len(captured) == 1
    event, payload = captured[0]
    assert event == "artifact.created"
    assert payload["kind"] == "task"
    assert payload["id"] == "t0001"


def test_dispatch_swallows_emitter_exception_and_warns_stderr(capsys):
    def bad_emitter(event, payload):
        raise RuntimeError("boom")

    _events.register_emitter(bad_emitter)
    # Must not raise
    _events._dispatch("artifact.created")
    captured = capsys.readouterr()
    assert "warning" in captured.err
    assert "boom" in captured.err


def test_dispatch_calls_all_emitters_even_after_failure():
    called = []

    def bad(event, payload):
        raise ValueError("bad")

    def good(event, payload):
        called.append(event)

    _events.register_emitter(bad)
    _events.register_emitter(good)
    _events._dispatch("artifact.created")
    assert called == ["artifact.created"]


def test_dispatch_pre_propagates_blocked_by_pre_hook():
    def blocking_emitter(event, payload):
        raise BlockedByPreHook("blocked!")

    _events.register_emitter(blocking_emitter)
    with pytest.raises(BlockedByPreHook, match="blocked!"):
        _events._dispatch_pre("artifact.created")


def test_dispatch_pre_swallows_non_blocking_exceptions(capsys):
    def bad(event, payload):
        raise RuntimeError("oops")

    _events.register_emitter(bad)
    # Must not raise
    _events._dispatch_pre("artifact.created")
    captured = capsys.readouterr()
    assert "warning" in captured.err


def test_register_and_unregister():
    captured = []
    fn = lambda e, p: captured.append(e)
    _events.register_emitter(fn)
    assert fn in _events._emitters
    _events.unregister_emitter(fn)
    assert fn not in _events._emitters
    _events._dispatch("artifact.created")
    assert captured == []


def test_unregister_noop_if_not_registered():
    """unregister_emitter is a no-op when fn is not registered."""
    fn = lambda e, p: None
    _events.unregister_emitter(fn)  # should not raise


def test_dispatch_injects_phase_post():
    phases = []
    _events.register_emitter(lambda e, p: phases.append(p.get("_phase")))
    _events._dispatch("artifact.created")
    assert phases == ["post"]


def test_dispatch_pre_injects_phase_pre():
    phases = []
    _events.register_emitter(lambda e, p: phases.append(p.get("_phase")))
    _events._dispatch_pre("artifact.created")
    assert phases == ["pre"]


def test_no_emitters_dispatch_is_noop():
    """_dispatch with no emitters must not raise."""
    _events._dispatch("artifact.created", kind="task")


# ---------------------------------------------------------------------------
# V3 — core does not import events/, hooks/, or log/
# ---------------------------------------------------------------------------


def test_core_does_not_import_outward():
    """AST-walk core/*.py and verify no outward imports to events/, hooks/, log/."""
    core_dir = Path(__file__).resolve().parents[2] / "src" / "artifacts_os" / "core"
    forbidden_patterns = (
        "artifacts_os.events",
        "artifacts_os.hooks",
        "artifacts_os.log",
    )

    violations = []
    for py_file in sorted(core_dir.glob("*.py")):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for pat in forbidden_patterns:
                        if alias.name.startswith(pat):
                            violations.append((py_file.name, alias.name))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for pat in forbidden_patterns:
                    if module.startswith(pat):
                        violations.append((py_file.name, module))

    assert violations == [], f"core imports outward: {violations}"
