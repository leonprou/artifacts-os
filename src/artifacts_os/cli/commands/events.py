"""cli events subcommand — inspect the artifact event stream.

Usage::

    artifacts events tail [--since DATE] [--event TYPE] [--follow]

Spec: s0025-artifact-events § C8
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path


def register(subparsers) -> None:
    p = subparsers.add_parser("events", help="inspect the artifact event stream")
    event_sub = p.add_subparsers(dest="events_command", metavar="SUBCOMMAND")
    event_sub.required = True

    tail_p = event_sub.add_parser("tail", help="tail the event stream")
    tail_p.add_argument(
        "--since",
        metavar="DATE",
        default=None,
        help="show events from this date forward (YYYY-MM-DD)",
    )
    tail_p.add_argument(
        "--event",
        "-e",
        action="append",
        dest="event_types",
        metavar="TYPE",
        default=None,
        help="filter by event type (may be repeated)",
    )
    tail_p.add_argument(
        "--follow",
        "-f",
        action="store_true",
        default=False,
        help="continuously follow the stream for new entries",
    )
    tail_p.add_argument(
        "--json",
        "-j",
        action="store_true",
        dest="json_out",
        default=False,
        help="output raw JSONL lines (default: pretty-printed)",
    )
    tail_p.set_defaults(func=_run_tail)

    p.set_defaults(func=_dispatch_events)


def _dispatch_events(args, registry) -> int:
    """Fallback — should not be reached because subcommand is required."""
    print("Usage: artifacts events <subcommand>", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Tail implementation
# ---------------------------------------------------------------------------


def _events_dir(registry) -> Path | None:
    """Return the vault events directory, or None if not found."""
    if registry.root is None:
        return None
    return registry.root / "artifacts" / "logs" / "events"


def _parse_since(since_str: str | None) -> date | None:
    if since_str is None:
        return None
    try:
        return date.fromisoformat(since_str)
    except ValueError:
        print(f"error: --since {since_str!r} is not a valid YYYY-MM-DD date", file=sys.stderr)
        raise SystemExit(1)


def _daily_files(events_dir: Path, since: date | None) -> list[Path]:
    """Return sorted JSONL files from *events_dir*, optionally filtered by date."""
    if not events_dir.is_dir():
        return []
    files: list[Path] = sorted(events_dir.glob("*.jsonl"))
    if since is not None:
        files = [f for f in files if _file_date(f) >= since]
    return files


def _file_date(path: Path) -> date:
    """Parse ``YYYY-MM-DD`` from the stem; fall back to epoch."""
    try:
        return date.fromisoformat(path.stem)
    except ValueError:
        return date.min


def _filter_event(record: dict, event_types: list[str] | None) -> bool:
    if not event_types:
        return True
    return record.get("event", "") in event_types


def _format_record(record: dict, *, json_out: bool) -> str:
    if json_out:
        return json.dumps(record, ensure_ascii=False)
    ts = record.get("ts", "")
    event = record.get("event", "")
    stem = record.get("stem") or record.get("id") or record.get("hook") or ""
    return f"{ts}  {event:<30s}  {stem}"


def _run_tail(args, registry) -> int:
    events_dir = _events_dir(registry)
    if events_dir is None:
        print("error: vault root not found", file=sys.stderr)
        return 2

    since = _parse_since(getattr(args, "since", None))
    event_types: list[str] | None = getattr(args, "event_types", None)
    follow: bool = getattr(args, "follow", False)
    json_out: bool = getattr(args, "json_out", False)

    files = _daily_files(events_dir, since)

    # Track file positions for --follow
    file_positions: dict[Path, int] = {}

    def _emit_file(path: Path, start_pos: int = 0) -> int:
        """Emit records from *path* starting at *start_pos*. Returns new position."""
        if not path.exists():
            return start_pos
        with path.open("r", encoding="utf-8") as fh:
            fh.seek(start_pos)
            pos = start_pos
            for raw_line in fh:
                raw_line = raw_line.rstrip("\n")
                if not raw_line:
                    continue
                try:
                    record = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if _filter_event(record, event_types):
                    print(_format_record(record, json_out=json_out))
            pos = fh.tell()
        return pos

    # Initial pass
    for path in files:
        file_positions[path] = _emit_file(path)

    if not follow:
        return 0

    # --follow: poll for new content
    try:
        while True:
            time.sleep(0.25)
            # Check for new daily files
            current_files = _daily_files(events_dir, since)
            for path in current_files:
                if path not in file_positions:
                    file_positions[path] = 0
                pos = file_positions.get(path, 0)
                file_positions[path] = _emit_file(path, pos)
    except KeyboardInterrupt:
        pass

    return 0
