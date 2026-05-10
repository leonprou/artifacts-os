"""Tests for cli/commands/events.py — C8 events tail.

Verification criteria: V15 from s0025-artifact-events.
"""
import json
from pathlib import Path

import pytest

from artifacts_os.cli import _run


@pytest.fixture
def vault_with_events(vault: Path) -> Path:
    """Create a vault with pre-populated event JSONL files."""
    events_dir = vault / "artifacts" / "logs" / "events"
    events_dir.mkdir(parents=True)

    # File for 2026-05-01
    (events_dir / "2026-05-01.jsonl").write_text(
        json.dumps({"ts": "2026-05-01T10:00:00+00:00", "event": "artifact.created",
                    "kind": "task", "id": "t0001", "stem": "t0001-first"}) + "\n"
    )
    # File for 2026-05-10 (today)
    (events_dir / "2026-05-10.jsonl").write_text(
        json.dumps({"ts": "2026-05-10T10:00:00+00:00", "event": "artifact.updated",
                    "kind": "task", "id": "t0001", "stem": "t0001-first"}) + "\n" +
        json.dumps({"ts": "2026-05-10T11:00:00+00:00", "event": "artifact.status_changed",
                    "kind": "task", "id": "t0001", "stem": "t0001-first"}) + "\n"
    )
    return vault


def test_events_tail_all(vault_with_events, capsys):
    code = _run(["events", "tail"])
    assert code == 0
    out = capsys.readouterr().out
    assert "artifact.created" in out
    assert "artifact.updated" in out


def test_events_tail_since_filters_by_date(vault_with_events, capsys):
    code = _run(["events", "tail", "--since", "2026-05-10"])
    assert code == 0
    out = capsys.readouterr().out
    # Only 2026-05-10 events should appear
    assert "artifact.updated" in out
    assert "artifact.created" not in out


def test_events_tail_event_filter(vault_with_events, capsys):
    code = _run(["events", "tail", "--event", "artifact.status_changed"])
    assert code == 0
    out = capsys.readouterr().out
    assert "artifact.status_changed" in out
    assert "artifact.created" not in out
    assert "artifact.updated" not in out


def test_events_tail_multiple_event_filters(vault_with_events, capsys):
    code = _run(["events", "tail", "--event", "artifact.created",
                 "--event", "artifact.updated"])
    assert code == 0
    out = capsys.readouterr().out
    assert "artifact.created" in out
    assert "artifact.updated" in out
    assert "artifact.status_changed" not in out


def test_events_tail_json_output(vault_with_events, capsys):
    code = _run(["events", "tail", "--json", "--event", "artifact.created"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    record = json.loads(out)
    assert record["event"] == "artifact.created"


def test_events_tail_empty_dir_returns_zero(vault: Path, capsys):
    """tail on a vault with no events dir returns 0."""
    code = _run(["events", "tail"])
    assert code == 0


def test_events_tail_default_limit(vault: Path, capsys):
    """Default limit of 50 shows last 50 of a larger set."""
    events_dir = vault / "artifacts" / "logs" / "events"
    events_dir.mkdir(parents=True)
    lines = [
        json.dumps({"ts": "2026-05-10T10:00:00+00:00", "event": "artifact.created",
                    "kind": "task", "id": f"t{i:04d}", "stem": f"t{i:04d}-x"})
        for i in range(80)
    ]
    (events_dir / "2026-05-10.jsonl").write_text("\n".join(lines) + "\n")

    code = _run(["events", "tail"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 50
    # last record should be visible; first 30 should be hidden
    assert "t0079" in out[-1]
    assert "t0000" not in "\n".join(out)


def test_events_tail_limit_flag(vault: Path, capsys):
    """--limit N shows last N records."""
    events_dir = vault / "artifacts" / "logs" / "events"
    events_dir.mkdir(parents=True)
    lines = [
        json.dumps({"ts": "2026-05-10T10:00:00+00:00", "event": "artifact.created",
                    "kind": "task", "id": f"t{i:04d}", "stem": f"t{i:04d}-x"})
        for i in range(10)
    ]
    (events_dir / "2026-05-10.jsonl").write_text("\n".join(lines) + "\n")

    code = _run(["events", "tail", "--limit", "3"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 3
    assert "t0009" in out[-1]


def test_events_tail_limit_zero_shows_all(vault: Path, capsys):
    """--limit 0 disables the cap."""
    events_dir = vault / "artifacts" / "logs" / "events"
    events_dir.mkdir(parents=True)
    lines = [
        json.dumps({"ts": "2026-05-10T10:00:00+00:00", "event": "artifact.created",
                    "kind": "task", "id": f"t{i:04d}", "stem": f"t{i:04d}-x"})
        for i in range(80)
    ]
    (events_dir / "2026-05-10.jsonl").write_text("\n".join(lines) + "\n")

    code = _run(["events", "tail", "--limit", "0"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 80
