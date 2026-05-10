"""Tests for cli/commands/events.py — flat events command + --tail.

Originally for s0025-artifact-events § C8 (V15). Updated for t0139 to
align the events CLI with `artifacts list`: flat command, Rich table
output by default, `--tail [N]` instead of `--limit`.
"""
import json
from pathlib import Path

import pytest

from artifacts_os.cli import _run


@pytest.fixture
def vault_with_events(vault: Path) -> Path:
    """Create a vault with pre-populated event JSONL files (3 events total)."""
    events_dir = vault / "artifacts" / "logs" / "events"
    events_dir.mkdir(parents=True)

    # Older file
    (events_dir / "2026-05-01.jsonl").write_text(
        json.dumps({"ts": "2026-05-01T10:00:00+00:00", "event": "artifact.created",
                    "kind": "task", "id": "t0001", "stem": "t0001-first"}) + "\n"
    )
    # Newer file (today)
    (events_dir / "2026-05-10.jsonl").write_text(
        json.dumps({"ts": "2026-05-10T10:00:00+00:00", "event": "artifact.updated",
                    "kind": "task", "id": "t0001", "stem": "t0001-first"}) + "\n" +
        json.dumps({"ts": "2026-05-10T11:00:00+00:00", "event": "artifact.status_changed",
                    "kind": "task", "id": "t0001", "stem": "t0001-first"}) + "\n"
    )
    return vault


# ---------------------------------------------------------------------------
# Flat command (no subcommand) + backward compat
# ---------------------------------------------------------------------------


def test_events_flat_no_subcommand(vault_with_events, capsys):
    """`artifacts events` runs without a subcommand and prints all events."""
    code = _run(["events"])
    assert code == 0
    out = capsys.readouterr().out
    assert "artifact.created" in out
    assert "artifact.updated" in out
    assert "artifact.status_changed" in out


def test_events_tail_subcommand_backcompat(vault_with_events, capsys):
    """`artifacts events tail` still works as a hidden alias of `events`."""
    code = _run(["events", "tail"])
    assert code == 0
    out = capsys.readouterr().out
    assert "artifact.created" in out
    assert "artifact.updated" in out
    assert "artifact.status_changed" in out


def test_events_tail_subcommand_with_flags(vault_with_events, capsys):
    """`events tail --since` is identical to `events --since`."""
    code = _run(["events", "tail", "--since", "2026-05-10"])
    assert code == 0
    out = capsys.readouterr().out
    assert "artifact.updated" in out
    assert "artifact.created" not in out


# ---------------------------------------------------------------------------
# Default output: Rich table, chronological, no truncation
# ---------------------------------------------------------------------------


def test_events_default_is_rich_table(vault_with_events, capsys):
    """Default output is a Rich table with headers ts/event/kind/artifact."""
    code = _run(["events"])
    assert code == 0
    out = capsys.readouterr().out
    # Rich table column headers
    assert "ts" in out
    assert "event" in out
    assert "kind" in out
    assert "artifact" in out
    # Box-drawing characters mean Rich rendered the table
    assert "─" in out or "━" in out


def test_events_default_chronological_old_to_new(vault_with_events, capsys):
    """Without --tail, events are shown old → new with no implicit cap."""
    code = _run(["events"])
    assert code == 0
    out = capsys.readouterr().out
    # All three events present
    assert out.count("artifact.created") == 1
    assert out.count("artifact.updated") == 1
    assert out.count("artifact.status_changed") == 1
    # Earlier event (created on 05-01) appears before later events (05-10)
    pos_created = out.index("artifact.created")
    pos_updated = out.index("artifact.updated")
    pos_changed = out.index("artifact.status_changed")
    assert pos_created < pos_updated < pos_changed


def test_events_no_default_truncation(vault: Path, capsys):
    """Without --tail, all 80 events are emitted (no implicit 50-cap)."""
    events_dir = vault / "artifacts" / "logs" / "events"
    events_dir.mkdir(parents=True)
    lines = [
        json.dumps({"ts": "2026-05-10T10:00:00+00:00", "event": "artifact.created",
                    "kind": "task", "id": f"t{i:04d}", "stem": f"t{i:04d}-x"})
        for i in range(80)
    ]
    (events_dir / "2026-05-10.jsonl").write_text("\n".join(lines) + "\n")

    code = _run(["events", "--json"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 80
    # First emitted record is the earliest (t0000); last is t0079.
    assert json.loads(out[0])["id"] == "t0000"
    assert json.loads(out[-1])["id"] == "t0079"


# ---------------------------------------------------------------------------
# --tail [N]
# ---------------------------------------------------------------------------


def test_events_tail_default_50(vault: Path, capsys):
    """`--tail` (no value) shows the last 50 of a larger set."""
    events_dir = vault / "artifacts" / "logs" / "events"
    events_dir.mkdir(parents=True)
    lines = [
        json.dumps({"ts": "2026-05-10T10:00:00+00:00", "event": "artifact.created",
                    "kind": "task", "id": f"t{i:04d}", "stem": f"t{i:04d}-x"})
        for i in range(80)
    ]
    (events_dir / "2026-05-10.jsonl").write_text("\n".join(lines) + "\n")

    code = _run(["events", "--tail", "--json"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 50
    # First visible record is the 31st (t0030); last is t0079.
    assert json.loads(out[0])["id"] == "t0030"
    assert json.loads(out[-1])["id"] == "t0079"


def test_events_tail_n(vault: Path, capsys):
    """`--tail N` shows the last N records."""
    events_dir = vault / "artifacts" / "logs" / "events"
    events_dir.mkdir(parents=True)
    lines = [
        json.dumps({"ts": "2026-05-10T10:00:00+00:00", "event": "artifact.created",
                    "kind": "task", "id": f"t{i:04d}", "stem": f"t{i:04d}-x"})
        for i in range(10)
    ]
    (events_dir / "2026-05-10.jsonl").write_text("\n".join(lines) + "\n")

    code = _run(["events", "--tail", "3", "--json"])
    assert code == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 3
    assert json.loads(out[0])["id"] == "t0007"
    assert json.loads(out[-1])["id"] == "t0009"


def test_events_tail_zero_yields_empty(vault: Path, capsys):
    """`--tail 0` yields no records (Unix tail -n 0 semantics)."""
    events_dir = vault / "artifacts" / "logs" / "events"
    events_dir.mkdir(parents=True)
    (events_dir / "2026-05-10.jsonl").write_text(
        json.dumps({"ts": "2026-05-10T10:00:00+00:00", "event": "artifact.created",
                    "kind": "task", "id": "t0001", "stem": "t0001-x"}) + "\n"
    )

    code = _run(["events", "--tail", "0", "--json"])
    assert code == 0
    out = capsys.readouterr().out
    assert out == ""


# ---------------------------------------------------------------------------
# Filters and JSON output
# ---------------------------------------------------------------------------


def test_events_since_filters_by_date(vault_with_events, capsys):
    code = _run(["events", "--since", "2026-05-10"])
    assert code == 0
    out = capsys.readouterr().out
    assert "artifact.updated" in out
    assert "artifact.created" not in out


def test_events_event_filter(vault_with_events, capsys):
    code = _run(["events", "--event", "artifact.status_changed"])
    assert code == 0
    out = capsys.readouterr().out
    assert "artifact.status_changed" in out
    assert "artifact.created" not in out
    assert "artifact.updated" not in out


def test_events_multiple_event_filters(vault_with_events, capsys):
    code = _run(["events", "--event", "artifact.created",
                 "--event", "artifact.updated"])
    assert code == 0
    out = capsys.readouterr().out
    assert "artifact.created" in out
    assert "artifact.updated" in out
    assert "artifact.status_changed" not in out


def test_events_json_output(vault_with_events, capsys):
    """`--json` emits one JSON record per line, no Rich table."""
    code = _run(["events", "--json", "--event", "artifact.created"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    record = json.loads(out)
    assert record["event"] == "artifact.created"
    # Box-drawing characters absent in JSON mode
    assert "─" not in out
    assert "━" not in out


def test_events_empty_dir_returns_zero(vault: Path, capsys):
    """Vault with no events dir returns 0 with no output."""
    code = _run(["events"])
    assert code == 0
    assert capsys.readouterr().out == ""


# ---------------------------------------------------------------------------
# Removed flags
# ---------------------------------------------------------------------------


def test_events_no_limit_flag(vault: Path):
    """`--limit` and `-n` are not registered; argparse exits with code 2."""
    import pytest

    with pytest.raises(SystemExit) as exc_info:
        _run(["events", "--limit", "10"])
    assert exc_info.value.code == 2

    with pytest.raises(SystemExit) as exc_info:
        _run(["events", "-n", "10"])
    assert exc_info.value.code == 2
