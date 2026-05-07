"""Settings models for artifacts_os.views.

Defines LayoutConfig, ViewConfig, ViewsConfig, and ViewsSettings — the
settings extension for the views module.

Spec: s0007-artifacts-os-views-module, s0022-tree-layout §10.2 / §10.4
"""

from dataclasses import dataclass, field
from typing import Any

from artifacts_os.core.models import Settings


@dataclass(frozen=True)
class LayoutConfig:
    """Layout configuration for a single kind in ``default_layouts``.

    Spec: s0022-tree-layout §10.2; s0024-tree-prune-modes §5.3.
    """

    layout: str
    parent_field: str | None = None
    # Prune mode for the tree layout (s0024 §5.3). None = inherit implicit
    # default ("strict"). Must be unset for non-tree layouts.
    prune: str | None = None


@dataclass
class ViewConfig:
    """Configuration for a single named view."""

    columns: str
    filters: dict[str, Any] = field(default_factory=dict)
    sort: str | None = None
    layout: str | None = None  # None means fall through to default_layouts / implicit
    parent_field: str | None = None  # required when layout: tree
    # Prune mode for tree-layout views (s0024 §5.2). None = inherit from
    # default_layouts / implicit. Must be unset for non-tree views.
    prune: str | None = None


@dataclass
class ViewsConfig:
    """Parsed views and default_views sections from the settings file."""

    views: dict[str, ViewConfig]
    default_views: dict[str, str]
    default_layouts: dict[str, LayoutConfig] = field(default_factory=dict)


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
        raw_dl_raw: object = base.raw.get("default_layouts") or {}

        parsed_dl = _parse_default_layouts(raw_dl_raw)

        if raw_views is None and raw_defaults is None and not parsed_dl:
            views_config = None
        else:
            parsed_views: dict[str, ViewConfig] = {}
            for name, entry in (raw_views or {}).items():
                parsed_views[name] = _parse_view(entry)
            views_config = ViewsConfig(
                views=parsed_views,
                default_views=dict(raw_defaults or {}),
                default_layouts=parsed_dl,
            )

        return cls(
            layout_version=base.layout_version,
            project=base.project,
            raw=base.raw,
            views=views_config,
        )


def _parse_default_layouts(raw: object) -> dict[str, LayoutConfig]:
    """Parse and validate the ``default_layouts`` mapping from raw YAML.

    Accepts a dict of kind-name → string shorthand or object form.
    Raises ValueError on unknown layout, missing parent_field for tree,
    or spurious parent_field for non-tree layouts.

    Spec: s0022-tree-layout §10.2 / §3.5.
    """
    if not isinstance(raw, dict):
        raise ValueError("default_layouts must be a mapping")

    # Import inside function body to avoid circular import (views → layouts → views).
    from artifacts_os.views.layouts import LAYOUTS  # noqa: PLC0415

    # Imported here too — same circular-import dance as LAYOUTS above.
    from artifacts_os.views.layouts import PRUNE_MODES  # noqa: PLC0415

    out: dict[str, LayoutConfig] = {}
    for kind_name, entry in raw.items():
        if isinstance(entry, str):
            entry = {"layout": entry}
        if not isinstance(entry, dict):
            raise ValueError(
                f"default_layouts[{kind_name!r}] must be a string or mapping"
            )
        layout = entry.get("layout")
        if not isinstance(layout, str) or layout not in LAYOUTS:
            raise ValueError(
                f"default_layouts[{kind_name!r}].layout = {layout!r}"
                f" is not a registered layout; known: {sorted(LAYOUTS)}"
            )
        parent_field = entry.get("parent_field")
        if layout == "tree" and not parent_field:
            raise ValueError(
                f"default_layouts[{kind_name!r}] declares layout 'tree'"
                " but has no parent_field"
            )
        if layout != "tree" and parent_field is not None:
            raise ValueError(
                f"default_layouts[{kind_name!r}].parent_field is set but"
                f" layout is {layout!r}"
            )
        prune = entry.get("prune")
        if prune is not None:
            if prune not in PRUNE_MODES:
                raise ValueError(
                    f"default_layouts[{kind_name!r}].prune = {prune!r}"
                    f" is not a registered prune mode;"
                    f" known: {sorted(PRUNE_MODES)}"
                )
            if layout != "tree":
                raise ValueError(
                    f"default_layouts[{kind_name!r}].prune is set but"
                    f" layout is {layout!r} (prune is meaningful only for"
                    " tree layouts; s0024 §3.7)"
                )
        out[kind_name] = LayoutConfig(
            layout=layout, parent_field=parent_field, prune=prune
        )
    return out


def _parse_view(d: dict) -> ViewConfig:
    """Parse a single view entry dict into a ViewConfig.

    Raises ValueError if the required ``columns`` key is absent, if
    ``layout`` is unrecognised, or if ``layout`` / ``parent_field``
    are paired incorrectly.

    Spec: s0022-tree-layout §10.4.
    """
    if "columns" not in d:
        raise ValueError("view entry missing required 'columns' field")

    layout = d.get("layout")
    parent_field = d.get("parent_field")
    prune = d.get("prune")

    if layout is not None:
        # Import inside function body to avoid circular import.
        from artifacts_os.views.layouts import LAYOUTS, PRUNE_MODES  # noqa: PLC0415

        if layout not in LAYOUTS:
            raise ValueError(
                f"view 'layout' = {layout!r} is not a registered layout;"
                f" known: {sorted(LAYOUTS)}"
            )
        if layout == "tree" and not parent_field:
            raise ValueError("view declares layout 'tree' but has no parent_field")
        if layout != "tree" and parent_field is not None:
            raise ValueError(
                f"view 'parent_field' is set but layout is {layout!r} (not 'tree')"
            )
        if prune is not None:
            if prune not in PRUNE_MODES:
                raise ValueError(
                    f"view 'prune' = {prune!r} is not a registered prune mode;"
                    f" known: {sorted(PRUNE_MODES)}"
                )
            if layout != "tree":
                raise ValueError(
                    f"view 'prune' is set but layout is {layout!r} (prune is"
                    " meaningful only for tree layouts; s0024 §3.7)"
                )
    else:
        if parent_field is not None:
            # parent_field without any layout is also invalid.
            raise ValueError(
                f"view 'parent_field' is set but layout is {layout!r} (not 'tree')"
            )
        if prune is not None:
            raise ValueError(
                f"view 'prune' is set but layout is {layout!r} (prune is"
                " meaningful only for tree layouts; s0024 §3.7)"
            )

    raw_filters = dict(d.get("filters") or {})
    _validate_filters_shape(raw_filters)

    return ViewConfig(
        columns=d["columns"],
        filters=raw_filters,
        sort=d.get("sort"),
        layout=layout,
        parent_field=parent_field,
        prune=prune,
    )


def _validate_filters_shape(filters: dict[str, Any]) -> None:
    """Validate ViewConfig filter values.

    Per s0023-multi-value-filters § 3.3, an empty list value is always a
    config bug — it means "match nothing", which is better expressed by
    deleting the view. Raise ValueError naming the offending key.

    Scalar values and non-empty list values pass through unchanged.
    """
    for key, value in filters.items():
        if isinstance(value, list) and not value:
            raise ValueError(
                f"view filter {key!r} has empty list — "
                "empty filter values are not allowed "
                "(use a scalar or a non-empty list)"
            )
