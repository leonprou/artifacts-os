"""Settings models for artifacts_os.views.

Defines ViewConfig, ViewsConfig, and ViewsSettings — the settings
extension for the views module.

Spec: s0007-artifacts-os-views-module
"""

from dataclasses import dataclass, field
from typing import Any

from artifacts_os.core.models import Settings


@dataclass
class ViewConfig:
    """Configuration for a single named view."""

    columns: str
    filters: dict[str, Any] = field(default_factory=dict)
    sort: str | None = None


@dataclass
class ViewsConfig:
    """Parsed views and default_views sections from the settings file."""

    views: dict[str, ViewConfig]
    default_views: dict[str, str]


@dataclass(kw_only=True)
class ViewsSettings(Settings):
    """Settings subclass that adds typed access to the views section.

    Construct via ``ViewsSettings.from_base(base)`` where *base* is
    the result of ``core.load_settings``.
    """

    views: ViewsConfig | None = None

    @classmethod
    def from_base(cls, base: Settings) -> "ViewsSettings":
        """Parse the views / default_views sections from *base.raw*.

        Returns a ViewsSettings with ``views=None`` if neither key is
        present in the raw settings document.
        """
        raw_views: dict | None = base.raw.get("views")
        raw_defaults: dict | None = base.raw.get("default_views")

        if raw_views is None and raw_defaults is None:
            views_config = None
        else:
            parsed: dict[str, ViewConfig] = {}
            for name, entry in (raw_views or {}).items():
                parsed[name] = _parse_view(entry)
            views_config = ViewsConfig(
                views=parsed,
                default_views=dict(raw_defaults or {}),
            )

        return cls(
            layout_version=base.layout_version,
            project=base.project,
            raw=base.raw,
            views=views_config,
        )


def _parse_view(d: dict) -> ViewConfig:
    """Parse a single view entry dict into a ViewConfig.

    Raises ValueError if the required ``columns`` key is absent.
    """
    if "columns" not in d:
        raise ValueError("view entry missing required 'columns' field")
    return ViewConfig(
        columns=d["columns"],
        filters=dict(d.get("filters") or {}),
        sort=d.get("sort"),
    )
