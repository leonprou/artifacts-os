"""Settings extension for the events module.

Reads the ``events:`` top-level key from ``artifacts.yaml`` using the
``Settings.from_base`` extension pattern (see ``docs/settings.md``).

Spec: s0025-artifact-events § C6
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from artifacts_os.core.models import Settings


@dataclass(kw_only=True)
class EventsSettings(Settings):
    """Settings for the always-on event stream.

    YAML schema::

        events:
          enabled: true          # default true; set false to disable stream
          dir: artifacts/logs/events  # override directory
    """

    enabled: bool = True
    dir: Path | None = None

    @classmethod
    def from_base(cls, base: Settings) -> "EventsSettings":
        """Construct from a loaded ``Settings`` instance.

        Reads the ``events:`` key from ``base.raw``; missing or empty
        sections use defaults.
        """
        raw_events: dict[str, Any] = base.raw.get("events") or {}
        enabled: bool = raw_events.get("enabled", True)
        dir_raw = raw_events.get("dir")
        dir_path: Path | None = Path(dir_raw) if dir_raw else None

        return cls(
            layout_version=base.layout_version,
            project=base.project,
            raw=base.raw,
            enabled=enabled,
            dir=dir_path,
        )
