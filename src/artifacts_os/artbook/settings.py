"""Settings extension for the artbook module.

Reads the ``artbook:`` top-level key from ``artifacts.yaml`` using the
``from_base`` extension pattern (see ``docs/settings.md``).

Spec: s0029-artbook-mvp-distribution-model §4.5
"""

from __future__ import annotations

from dataclasses import dataclass

from artifacts_os.core.models import Settings


@dataclass(frozen=True)
class ArtbookSettings:
    """Settings for the artbook module.

    YAML schema::

        artbook:
          distro_url: https://github.com/example/artbook-defaults
    """

    distro_url: str | None

    @classmethod
    def from_base(cls, base: Settings) -> "ArtbookSettings":
        """Construct from a loaded Settings instance.

        Reads the ``artbook:`` key from ``base.raw``; returns
        ``distro_url=None`` when the section or key is absent or empty.
        """
        raw = base.raw.get("artbook", {}) or {}
        return cls(distro_url=raw.get("distro_url") or None)
