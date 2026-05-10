"""cli events command — inspect the artifact event stream.

Usage::

    artifacts events [--since DATE] [--event TYPE] [--follow]
                     [--tail [N]] [--json]
    artifacts events tail [...]    # hidden backward-compat alias

The flat ``events`` form mirrors ``artifacts list``: same command shape,
same Rich table style, same flag conventions. ``events tail`` is kept as
a hidden alias that forwards to the same handler — argv preprocessing in
``cli/__init__.py`` strips the deprecated ``tail`` token before parsing.

Spec: s0025-artifact-events § C8 (initial); aligned with t0139.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.table import Table


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------


def register(subparsers) -> None:
    """Register the flat ``events`` command on *subparsers*.

    All flags live at the top level — there is no required subcommand.
    The deprecated ``events tail`` form is handled by an argv-preprocessing
    step in ``cli/__init__.py`` that strips the ``tail`` token before
    argparse sees it.
    """
    p = subparsers.add_parser(
        "events",
        help="inspect the artifact event stream",
    )
    p.add_argument(
        "--since",
        metavar="DATE",
        default=None,
        help="show events from this date forward (YYYY-MM-DD)",
    )
    p.add_argument(
        "--event",
        "-e",
        action="append",
        dest="event_types",
        metavar="TYPE",
        default=None,
        help="filter by event type (may be repeated)",
    )
    p.add_argument(
        "--follow",
        "-f",
        action="store_true",
        default=False,
        help="continuously follow the stream for new entries",
    )
    p.add_argument(
        "--json",
        "-j",
        action="store_true",
        dest="json_out",
        default=False,
        help="output raw JSONL lines (default: Rich table)",
    )
    p.add_argument(
        "--tail",
        nargs="?",
        const=50,
        default=None,
        type=int,
        metavar="N",
        help=(
            "show only the last N events from the snapshot (default: 50). "
            "Without --tail, all matching events are shown old→new."
        ),
    )
    p.set_defaults(func=_run_events)


# ---------------------------------------------------------------------------
# Snapshot collection
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
        print(
            f"error: --since {since_str!r} is not a valid YYYY-MM-DD date",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _daily_files(events_dir: Path, since: date | None) -> list[Path]:
    """Return sorted JSONL files from *events_dir*, optionally filtered by date.

    Sort is ascending by filename (which is ``YYYY-MM-DD``) so callers see
    events in chronological order — old → new.
    """
    if not events_dir.is_dir():
        return []
    files: list[Path] = sorted(events_dir.glob("*.jsonl"))
    if since is not None:
        files = [f for f in files if _file_date(f) >= since]
    return files


def _file_date(path: Path) -> date:
    """Parse ``YYYY-MM-DD`` from the stem; fall back to epoch on malformed names."""
    try:
        return date.fromisoformat(path.stem)
    except ValueError:
        return date.min


def _filter_event(record: dict, event_types: list[str] | None) -> bool:
    if not event_types:
        return True
    return record.get("event", "") in event_types


def _collect_file(
    path: Path,
    start_pos: int,
    event_types: list[str] | None,
) -> tuple[list[dict], int]:
    """Read matching records from *path* starting at *start_pos*.

    Returns ``(records, new_position)``.  Malformed JSON lines are skipped
    silently; the file position advances past them so they are not retried.
    """
    records: list[dict] = []
    if not path.exists():
        return records, start_pos
    with path.open("r", encoding="utf-8") as fh:
        fh.seek(start_pos)
        for raw_line in fh:
            raw_line = raw_line.rstrip("\n")
            if not raw_line:
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if _filter_event(record, event_types):
                records.append(record)
        pos = fh.tell()
    return records, pos


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _artifact_label(record: dict) -> str:
    """Pick the best human-facing label for the event subject.

    Prefers ``stem`` (full ``id-name`` for numbered kinds), falling back to
    ``id``, then ``hook`` (for hook-fired/-failed events), then "".
    """
    return (
        record.get("stem")
        or record.get("id")
        or record.get("hook")
        or ""
    )


def _build_table(records: list[dict]) -> Table:
    """Build a Rich table for *records* with columns: ts, event, kind, artifact."""
    table = Table()
    table.add_column("ts")
    table.add_column("event")
    table.add_column("kind")
    table.add_column("artifact")
    for record in records:
        table.add_row(
            str(record.get("ts", "")),
            str(record.get("event", "")),
            str(record.get("kind", "")),
            _artifact_label(record),
        )
    return table


def _format_record_plain(record: dict) -> str:
    """Plain-text single-line format used during ``--follow`` streaming."""
    ts = record.get("ts", "")
    event = record.get("event", "")
    kind = record.get("kind", "")
    artifact = _artifact_label(record)
    return f"{ts}  {event:<30s}  {kind:<10s}  {artifact}"


# ---------------------------------------------------------------------------
# Command runner
# ---------------------------------------------------------------------------


def _run_events(args, registry) -> int:
    events_dir = _events_dir(registry)
    if events_dir is None:
        print("error: vault root not found", file=sys.stderr)
        return 2

    since = _parse_since(getattr(args, "since", None))
    event_types: list[str] | None = getattr(args, "event_types", None)
    follow: bool = getattr(args, "follow", False)
    json_out: bool = getattr(args, "json_out", False)
    tail: int | None = getattr(args, "tail", None)

    files = _daily_files(events_dir, since)

    # --- Initial snapshot: collect all matching records (old → new) ---
    snapshot: list[dict] = []
    file_positions: dict[Path, int] = {}

    for path in files:
        records, pos = _collect_file(path, 0, event_types)
        snapshot.extend(records)
        file_positions[path] = pos

    # Apply --tail to the snapshot only.  ``tail is None`` → show all;
    # ``tail <= 0`` → show none (matches Unix ``tail -n 0`` semantics and
    # the parallel ``_apply_tail`` helper in cli/commands/list.py).
    visible: list[dict]
    if tail is None:
        visible = snapshot
    elif tail <= 0:
        visible = []
    else:
        visible = snapshot[-tail:]

    if json_out:
        for record in visible:
            print(json.dumps(record, ensure_ascii=False))
    elif visible:
        # Empty snapshot → print nothing (consistent with ``list``).
        Console().print(_build_table(visible))

    if not follow:
        return 0

    # --- Follow: stream new lines without a cap, plain text per line. ---
    def _emit_new(path: Path, start_pos: int) -> int:
        records, pos = _collect_file(path, start_pos, event_types)
        for record in records:
            if json_out:
                print(json.dumps(record, ensure_ascii=False))
            else:
                print(_format_record_plain(record))
        return pos

    try:
        while True:
            time.sleep(0.25)
            current_files = _daily_files(events_dir, since)
            for path in current_files:
                if path not in file_positions:
                    file_positions[path] = 0
                file_positions[path] = _emit_new(path, file_positions[path])
    except KeyboardInterrupt:
        pass

    return 0
