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
    layout: str | None = None  # None means fall through to default_layouts / kind / implicit


@dataclass
class ViewsConfig:
    """Parsed views and default_views sections from the settings file."""

    views: dict[str, ViewConfig]
    default_views: dict[str, str]
    default_layouts: dict[str, str] = field(default_factory=dict)


@dataclass(kw_only=True)
class ViewsSettings(Settings):
    """Settings subclass that adds typed access to the views section.

    Construct via ``ViewsSettings.from_base(base)`` where *base* is
    the result of ``core.load_settings``.
    """

    views: ViewsConfig | None = None

    @classmethod
    def from_base(cls, base: Settings) -> "ViewsSettings":
        """Parse the views / default_views / default_layouts sections from *base.raw*.

        Returns a ViewsSettings with ``views=None`` if none of the three keys is
        present in the raw settings document.
        """
        raw_views: dict | None = base.raw.get("views")
        raw_defaults: dict | None = base.raw.get("default_views")
        raw_dl: dict = base.raw.get("default_layouts") or {}

        if not isinstance(raw_dl, dict):
            raise ValueError("default_layouts must be a mapping")

        # Import inside function body to avoid circular import (views → layouts → views).
        from artifacts_os.views.layouts import LAYOUTS  # noqa: PLC0415

        for k, v in raw_dl.items():
            if v not in LAYOUTS:
                raise ValueError(
                    f"default_layouts[{k!r}] = {v!r} is not a registered layout;"
                    f" known: {sorted(LAYOUTS)}"
                )

        if raw_views is None and raw_defaults is None and not raw_dl:
            views_config = None
        else:
            parsed: dict[str, ViewConfig] = {}
            for name, entry in (raw_views or {}).items():
                parsed[name] = _parse_view(entry)
            views_config = ViewsConfig(
                views=parsed,
                default_views=dict(raw_defaults or {}),
                default_layouts=dict(raw_dl),
            )

        return cls(
            layout_version=base.layout_version,
            project=base.project,
            raw=base.raw,
            views=views_config,
        )


def _parse_view(d: dict) -> ViewConfig:
    """Parse a single view entry dict into a ViewConfig.

    Raises ValueError if the required ``columns`` key is absent or if
    ``layout`` is set to an unrecognised layout name.
    """
    if "columns" not in d:
        raise ValueError("view entry missing required 'columns' field")

    layout = d.get("layout")
    if layout is not None:
        # Import inside function body to avoid circular import.
        from artifacts_os.views.layouts import LAYOUTS  # noqa: PLC0415

        if layout not in LAYOUTS:
            raise ValueError(
                f"view 'layout' = {layout!r} is not a registered layout;"
                f" known: {sorted(LAYOUTS)}"
            )

    return ViewConfig(
        columns=d["columns"],
        filters=dict(d.get("filters") or {}),
        sort=d.get("sort"),
        layout=layout,
    )
