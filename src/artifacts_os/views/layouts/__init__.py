"""Layout registry for artifacts_os.views.

Defines the Layout callable type alias and the LAYOUTS dict that maps
layout name → layout function.  A third layout slots in by adding one
entry here — no other code changes required.

Spec: s0022-tree-layout §4, §5.4
"""

from collections.abc import Callable
from typing import Any

from rich.console import RenderableType

from artifacts_os.core.models import ArtifactMeta, KindDef
from artifacts_os.views._views import FieldSpec, render_table
from artifacts_os.views.layouts.tree import TreeNote, compute_tree, render_tree

# Layout callable type alias.
# Concrete signature: (items, columns, *, kind_def=None, **kwargs) → RenderableType
Layout = Callable[..., RenderableType]

#: Registry mapping layout name → layout callable.
#: The CLI looks up the chosen name here; unknown name → ValidationError.
LAYOUTS: dict[str, Layout] = {
    "table": render_table,
    "tree": render_tree,
}

__all__ = [
    "Layout",
    "LAYOUTS",
    "TreeNote",
    "compute_tree",
    "render_tree",
]
