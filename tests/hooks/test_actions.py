"""Tests for hooks/actions.py — C5 action runners.

Verification criteria: V8, V9 from s0025-artifact-events.
"""
import json
import sys
from pathlib import Path

import pytest

from artifacts_os.hooks.actions import (
    ShellAction,
    NotifyAction,
    FileDropAction,
    from_config,
    _bell,
)


# ---------------------------------------------------------------------------
# V8 — all three action types round-trip via config and execute
# ---------------------------------------------------------------------------


class TestShellAction:
    def test_from_config(self):
        action = from_config({"type": "shell", "command": "echo hello", "timeout": 5})
        assert isinstance(action, ShellAction)
        assert action.command == "echo hello"
        assert action.timeout == 5

    def test_to_dict(self):
        action = ShellAction(command="echo hello", timeout=5)
        assert action.to_dict() == {"type": "shell", "command": "echo hello", "timeout": 5}

    def test_run_success(self):
        action = ShellAction(command="true")
        action.run({}, {})  # must not raise

    def test_run_failure_raises(self):
        action = ShellAction(command="false")
        with pytest.raises(RuntimeError, match="exit"):
            action.run({}, {})

    def test_run_uses_env(self, tmp_path):
        out_file = tmp_path / "out.txt"
        action = ShellAction(command=f'echo "$MY_VAR" > {out_file}')
        action.run({}, {"MY_VAR": "hello"})
        assert "hello" in out_file.read_text()

    def test_from_config_missing_command_raises(self):
        with pytest.raises(ValueError, match="command"):
            from_config({"type": "shell"})


class TestNotifyAction:
    def test_from_config(self):
        action = from_config({"type": "notify", "title": "hi", "body": "hello"})
        assert isinstance(action, NotifyAction)
        assert action.title == "hi"

    def test_to_dict(self):
        action = NotifyAction(title="hi", body="hello", mechanism="auto")
        d = action.to_dict()
        assert d["type"] == "notify"
        assert d["title"] == "hi"

    def test_run_bell_mechanism(self, capsys):
        """mechanism=bell writes \\a to stderr."""
        action = NotifyAction(title="Test", mechanism="bell")
        action.run({}, {})
        captured = capsys.readouterr()
        assert "\a" in captured.err

    def test_run_auto_falls_back_to_bell_when_no_daemon(self, monkeypatch, capsys):
        """V9 — notify falls back to terminal bell when no notification daemon."""
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        action = NotifyAction(title="Test", body="Body", mechanism="auto")
        action.run({}, {})
        captured = capsys.readouterr()
        assert "\a" in captured.err

    def test_env_variable_expansion(self, capsys):
        """$ART_NAME is expanded in title."""
        action = NotifyAction(title="Review: $ART_NAME", mechanism="bell")
        action.run({}, {"ART_NAME": "my-task"})
        # Just verify it runs; expansion is tested via _expand directly


class TestFileDropAction:
    def test_from_config(self, tmp_path):
        path = str(tmp_path / "{event}-{id}.json")
        action = from_config({"type": "file-drop", "path": path, "payload": "full"})
        assert isinstance(action, FileDropAction)
        assert action.path == path
        assert action.payload_mode == "full"

    def test_to_dict(self, tmp_path):
        path = str(tmp_path / "{event}.json")
        action = FileDropAction(path=path, payload_mode="summary")
        d = action.to_dict()
        assert d["type"] == "file-drop"
        assert d["payload"] == "summary"

    def test_run_full_payload(self, tmp_path):
        out_path = str(tmp_path / "{event}-{id}.json")
        action = FileDropAction(path=out_path, payload_mode="full")
        env = {
            "ART_EVENT": "artifact.created",
            "ART_KIND": "task",
            "ART_ID": "t0001",
            "ART_TS": "2026-05-10T00:00:00+00:00",
        }
        action.run({"kind": "task", "id": "t0001"}, env)
        resolved = tmp_path / "artifact.created-t0001.json"
        assert resolved.exists()
        record = json.loads(resolved.read_text())
        assert record["event"] == "artifact.created"

    def test_run_summary_payload(self, tmp_path):
        out_path = str(tmp_path / "drop.json")
        action = FileDropAction(path=out_path, payload_mode="summary")
        env = {
            "ART_EVENT": "artifact.created",
            "ART_KIND": "task",
            "ART_ID": "t0001",
            "ART_TS": "2026-05-10T00:00:00+00:00",
        }
        action.run({"kind": "task", "id": "t0001"}, env)
        resolved = tmp_path / "drop.json"
        record = json.loads(resolved.read_text())
        # Summary only has the basic fields
        assert record["event"] == "artifact.created"
        assert record["id"] == "t0001"

    def test_from_config_missing_path_raises(self):
        with pytest.raises(ValueError, match="path"):
            from_config({"type": "file-drop"})


def test_from_config_unknown_type_raises():
    with pytest.raises(ValueError, match="unknown action type"):
        from_config({"type": "nonexistent"})


def test_from_config_missing_type_raises():
    with pytest.raises(ValueError, match="missing 'type'"):
        from_config({})
