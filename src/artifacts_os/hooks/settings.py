"""Settings extension for the hooks module.

Reads the ``hooks:`` top-level key from ``artifacts.yaml`` using the
``Settings.from_base`` extension pattern (see ``docs/settings.md``).

Spec: s0025-artifact-events § C6
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from artifacts_os.core.models import Settings


@dataclass(kw_only=True)
class HooksSettings(Settings):
    """Settings for the opt-in hook layer.

    YAML schema::

        hooks:
          - name: my-hook
            matcher:
              event: artifact.created
            action:
              type: shell
              command: "echo $ART_ID"
    """

    hooks: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_base(cls, base: Settings) -> "HooksSettings":
        """Construct from a loaded ``Settings`` instance.

        Reads the ``hooks:`` key from ``base.raw``; a missing or empty
        section produces an empty list.
        """
        raw_hooks: list[dict[str, Any]] = base.raw.get("hooks") or []

        return cls(
            layout_version=base.layout_version,
            project=base.project,
            raw=base.raw,
            hooks=list(raw_hooks),
        )
