"""Tests for events/stream.py — C3 JSONL stream writer.

Verification criteria: V4, V5 from s0025-artifact-events.
"""
import json
import stat
from datetime import datetime, timezone
from pathlib import Path

import pytest

from artifacts_os.events import stream


# ---------------------------------------------------------------------------
# V4 — stream creates JSONL file and appends one valid JSON line per dispatch
# ---------------------------------------------------------------------------


def test_append_creates_daily_file(tmp_path):
    stream.append("artifact.created", {"kind": "task", "id": "t0001"}, root=tmp_path)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    log_file = tmp_path / "artifacts" / "logs" / "events" / f"{today}.jsonl"
    assert log_file.exists()


def test_append_writes_valid_json_line(tmp_path):
    stream.append("artifact.created", {"kind": "task", "id": "t0001"}, root=tmp_path)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    log_file = tmp_path / "artifacts" / "logs" / "events" / f"{today}.jsonl"
    lines = [l for l in log_file.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "artifact.created"
    assert record["kind"] == "task"
    assert record["id"] == "t0001"
    assert "ts" in record


def test_append_accumulates_lines(tmp_path):
    stream.append("artifact.created", {"id": "t0001"}, root=tmp_path)
    stream.append("artifact.updated", {"id": "t0001"}, root=tmp_path)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    log_file = tmp_path / "artifacts" / "logs" / "events" / f"{today}.jsonl"
    lines = [l for l in log_file.read_text().splitlines() if l.strip()]
    assert len(lines) == 2
    events = [json.loads(l)["event"] for l in lines]
    assert events == ["artifact.created", "artifact.updated"]


def test_append_strips_phase_sentinel(tmp_path):
    """The _phase internal sentinel must not appear in the JSONL output."""
    stream.append("artifact.created", {"id": "t0001", "_phase": "post"}, root=tmp_path)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    log_file = tmp_path / "artifacts" / "logs" / "events" / f"{today}.jsonl"
    record = json.loads(log_file.read_text().strip())
    assert "_phase" not in record


def test_append_skips_pre_phase(tmp_path):
    """Pre-phase events must not be written to the stream."""
    stream.append("artifact.created", {"id": "t0001", "_phase": "pre"}, root=tmp_path)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    log_file = tmp_path / "artifacts" / "logs" / "events" / f"{today}.jsonl"
    assert not log_file.exists()


# ---------------------------------------------------------------------------
# V5 — stream writer failure prints warning, returns, does not raise
# ---------------------------------------------------------------------------


def test_append_no_vault_root_warns_stderr(tmp_path, capsys, monkeypatch):
    """When vault root cannot be found, print a warning but don't raise."""
    monkeypatch.setattr(
        "artifacts_os.events.stream.find_vault_root",
        lambda: None,
    )
    # Must not raise even though root is not found
    stream.append("artifact.created", {})
    captured = capsys.readouterr()
    assert "warning" in captured.err


def test_append_read_only_dir_warns_stderr(tmp_path, capsys):
    """Write failure (read-only events dir) warns and does not raise."""
    events_dir = tmp_path / "artifacts" / "logs" / "events"
    events_dir.mkdir(parents=True)
    # Make the directory read-only so file creation fails
    events_dir.chmod(stat.S_IREAD | stat.S_IEXEC)
    try:
        stream.append("artifact.created", {"id": "t0001"}, root=tmp_path)
    finally:
        events_dir.chmod(stat.S_IRWXU)  # restore
    captured = capsys.readouterr()
    assert "warning" in captured.err
