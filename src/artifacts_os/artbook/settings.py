"""Settings extension for the artbook module.

Reads the ``artbook:`` top-level key from ``artifacts.yaml`` using the
``from_base`` extension pattern (see ``docs/settings.md``).

Spec: s0029-artbook-mvp-distribution-model §4.5
     s0031-artbook-post-pull-artifact-promotion D39
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
          promotion: enabled      # 'enabled' (default) or 'disabled' (D31)
          promote_mode: symlink   # None (default), 'symlink', or 'copy' (D30)
    """

    distro_url: str | None
    promotion: str = "enabled"         # 'enabled' | 'disabled' (D39)
    promote_mode: str | None = None    # None | 'symlink' | 'copy' (D39)

    @classmethod
    def from_base(cls, base: Settings) -> "ArtbookSettings":
        """Construct from a loaded Settings instance.

        Reads the ``artbook:`` key from ``base.raw``; returns defaults
        when the section or key is absent or empty.

        Raises SettingsError for invalid ``promotion`` or ``promote_mode`` values (D39).
        """
        from artifacts_os.artbook.errors import SettingsError

        raw = base.raw.get("artbook", {}) or {}

        distro_url = raw.get("distro_url") or None

        # D39 — promotion: must be 'enabled' or 'disabled' (case-sensitive)
        promotion_raw = raw.get("promotion")
        if promotion_raw is None:
            promotion = "enabled"
        else:
            if promotion_raw not in ("enabled", "disabled"):
                raise SettingsError(
                    f"artbook.promotion must be 'enabled' or 'disabled'; "
                    f"got '{promotion_raw}'"
                )
            promotion = promotion_raw

        # D39 — promote_mode: must be 'symlink' or 'copy' or absent
        promote_mode_raw = raw.get("promote_mode")
        if promote_mode_raw is None:
            promote_mode = None
        else:
            if promote_mode_raw not in ("symlink", "copy"):
                raise SettingsError(
                    f"artbook.promote_mode must be 'symlink' or 'copy'; "
                    f"got '{promote_mode_raw}'"
                )
            promote_mode = promote_mode_raw

        return cls(
            distro_url=distro_url,
            promotion=promotion,
            promote_mode=promote_mode,
        )
