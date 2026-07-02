"""Always-on JSONL audit stream writer.

Appends one JSON line per event to ``artifacts/logs/events/YYYY-MM-DD.jsonl``
inside the vault root.  Failure prints a warning to stderr and returns —
this function must never raise.

Uses stdlib only (``json``, ``pathlib``, ``datetime``).

Spec: s0025-artifact-events § C3
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from artifacts_os.core.vault import find_vault_root


def _now_iso() -> str:
    """Current time as ISO 8601 string with UTC offset."""
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _serialize(obj: object) -> object:
    """Coerce non-JSON-serializable objects (e.g. Path, date) to str."""
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (_dt.datetime, _dt.date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


def append(event: str, payload: dict, *, root: Path | None = None) -> None:
    """Append one JSON line to the daily events JSONL file.

    Args:
        event:   The event type string (e.g. ``"artifact.created"``).
        payload: Event-specific key/value pairs (merged into the record).
        root:    Vault root directory.  Resolved via ``find_vault_root()``
                 from CWD when *None*.

    The record written is ``{"ts": <now>, "event": <event>, **payload}``.
    Any exception is caught, printed to stderr, and swallowed.
    """
    try:
        # Pre-phase events run before the file is written — skip them.
        phase = payload.get("_phase", "post")
        if phase == "pre":
            return

        if root is None:
            root = find_vault_root()
        if root is None:
            sys.stderr.write("warning: events stream: cannot find vault root\n")
            return

        events_dir = Path(root) / "artifacts" / "logs" / "events"
        events_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        log_path = events_dir / f"{today}.jsonl"

        # Strip internal sentinel before writing.
        clean_payload = {k: v for k, v in payload.items() if k != "_phase"}
        record: dict = {"ts": _now_iso(), "event": event, **_serialize(clean_payload)}
        line = json.dumps(record, ensure_ascii=False) + "\n"

        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"warning: events stream append failed: {e!r}\n")
