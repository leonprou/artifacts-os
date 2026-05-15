"""artifacts-os views module.

Produces renderable representations of artifact data for display in
`cli` and `tui`. Does not emit output itself — returns strings or rich
renderables.

Depends on `core` (plus `rich`).

Spec: s2061-artifacts-os-module-system § views
Implementation spec: s0007-artifacts-os-views-module
"""

from artifacts_os.core.models import ItemMeta
from artifacts_os.views._views import (
    FieldSpec,
    default_columns,
    format_field,
    parse_field_specs,
    render_table,
)
from artifacts_os.views.models import LayoutConfig, ViewConfig, ViewsConfig, ViewsSettings
from artifacts_os.views.layouts import (
    Layout,
    LAYOUTS,
    PRUNE_MODES,
    TreeNote,
    compute_tree,
    render_tree,
)

__all__ = [
    "ItemMeta",
    "FieldSpec",
    "default_columns",
    "format_field",
    "parse_field_specs",
    "render_table",
    "LayoutConfig",
    "ViewConfig",
    "ViewsConfig",
    "ViewsSettings",
    "Layout",
    "LAYOUTS",
    "PRUNE_MODES",
    "TreeNote",
    "compute_tree",
    "render_tree",
]
