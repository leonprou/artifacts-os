"""cli list command — list artifacts with optional filters."""

import json
import sys
from typing import Any

from rich.console import Console

import artifacts_os.views as views
from artifacts_os.core import list_artifacts, Registry
from artifacts_os.core.models import KindDef
from artifacts_os.core.errors import ValidationError
from artifacts_os.views.models import ViewConfig, ViewsSettings


def register(subparsers) -> None:
    p = subparsers.add_parser("list", help="list artifacts")
    p.add_argument("--kind", "-k", help="filter by kind")
    p.add_argument("--status", "-s", help="filter by status")
    p.add_argument("--children", help="direct children of <ref> (selection predicate)")
    p.add_argument("--parent", help="parent of <ref> (returns 0 or 1 records as array)")
    p.add_argument("--view", "-V", help="named view from artifacts.yaml")

    proj = p.add_mutually_exclusive_group()
    proj.add_argument("--fields", "-f",
                      help="field spec string (e.g. 'id,name,status')")
    proj.add_argument("--meta", action="store_true",
                      help="full frontmatter per row (overrides --fields/view.columns)")

    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-q", "--quiet", action="store_true", help="one name per line")
    mode.add_argument("-j", "--json", action="store_true", dest="json_out",
                      help="JSON output")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    from artifacts_os.cli import _load_views_settings

    views_settings = _load_views_settings(registry.root)
    _apply_view(args, views_settings)

    # Resolve --children ref before running list_artifacts.
    children_parent_path = None
    if getattr(args, "children", None):
        from artifacts_os.core.discover import resolve
        children_parent_path = resolve(registry, args.children)

    # Resolve --parent: list the parent record of <ref> as a 0-or-1 array.
    parent_meta = None
    parent_requested = False
    if getattr(args, "parent", None):
        from artifacts_os.core import parent as _parent_fn
        parent_requested = True
        parent_meta = _parent_fn(registry, args.parent)

    items = list_artifacts(
        registry,
        kind=args.kind or None,
        status=args.status or None,
    )
    items = _apply_extra_filters(items, getattr(args, "_extra_filters", {}))
    items = _apply_sort(items, getattr(args, "_sort", None))

    # Apply --children predicate as a post-discovery filter.
    if children_parent_path is not None:
        from artifacts_os.core.discover import _unwrap_wikilink, resolve as _resolve
        from artifacts_os.core.errors import NotFoundError, AmbiguousError
        filtered = []
        for item in items:
            raw_parent = item.frontmatter.get("parent")
            if not raw_parent:
                continue
            bare = _unwrap_wikilink(str(raw_parent))
            try:
                resolved = _resolve(registry, bare)
            except (NotFoundError, AmbiguousError):
                continue
            if resolved == children_parent_path:
                filtered.append(item)
        items = filtered

    # Apply --parent: replace items with the resolved parent (or empty).
    if parent_requested:
        if parent_meta is None:
            items = []
        else:
            # Match the parent record from items by path; honor kind/status filters.
            items = [m for m in items if m.path == parent_meta.path]
            if not items and (args.kind is None and args.status is None
                              and not getattr(args, "_extra_filters", {})):
                # No filters in play: include the parent directly.
                items = [parent_meta]

    if args.quiet:
        for item in items:
            print(item.path.stem)
        return 0

    if args.json_out:
        print(json.dumps([item.frontmatter for item in items], default=str))
        return 0

    # Default: rich table
    if not items:
        return 0

    view_cfg: ViewConfig | None = getattr(args, "_view_cfg", None)

    kind_def: KindDef | None = None
    if args.kind:
        try:
            kind_def = registry.get(args.kind)
        except ValueError:
            pass
    elif items:
        first_kind = items[0].kind
        try:
            kind_def = registry.get(first_kind)
        except ValueError:
            pass

    # --meta: project all frontmatter keys (union across items).
    if getattr(args, "meta", False):
        columns = _meta_columns(items)
    else:
        columns = _resolve_columns(args, view_cfg, registry, kind_def)

    table = views.render_table(items, columns, kind_def=kind_def)
    Console().print(table)
    return 0


def _meta_columns(items: list) -> list:
    """Build an ordered column list from the union of all frontmatter keys.

    Canonical order: id, kind, name, status, created — then all remaining
    keys in sorted order.
    """
    leading = ["id", "kind", "name", "status", "created"]
    seen: set[str] = set()
    all_keys: list[str] = []
    for item in items:
        for k in item.frontmatter:
            if k not in seen:
                seen.add(k)
                all_keys.append(k)

    ordered = [k for k in leading if k in seen]
    ordered += sorted(k for k in all_keys if k not in set(leading))
    return views.parse_field_specs(",".join(ordered)) if ordered else \
        views.parse_field_specs("id,kind,name,status")


def _apply_view(args: Any, settings: ViewsSettings | None) -> None:
    """Resolve the active view and mutate *args* with merged filters/sort/cfg.

    Raises ValidationError on unknown view names so the caller's except
    cascade surfaces it as exit 2.
    """
    args._extra_filters = {}
    args._sort = None
    args._view_cfg = None

    binding_kind = args.kind  # may be None

    view_name: str | None = getattr(args, "view", None)

    # Auto-bind from default_views when no explicit --view.
    if view_name is None and binding_kind is not None and settings is not None:
        if settings.views is not None:
            bound = settings.views.default_views.get(binding_kind)
            if bound is not None:
                # Validate the bound view exists before using it.
                if bound not in settings.views.views:
                    raise ValidationError(
                        f"default_views.{binding_kind} refers to unknown view '{bound}'"
                    )
                view_name = bound

    # Resolve ViewConfig.
    view_cfg: ViewConfig | None = None
    if view_name is not None:
        if settings is None or settings.views is None:
            raise ValidationError(
                f"unknown view '{view_name}' (no 'views:' section in artifacts.yaml)"
            )
        if view_name not in settings.views.views:
            raise ValidationError(f"unknown view '{view_name}'")
        view_cfg = settings.views.views[view_name]

    if view_cfg is None:
        return

    # Per-key filter merge — explicit CLI flags win.
    for key, val in view_cfg.filters.items():
        if key == "status":
            if args.status is None:
                args.status = str(val)
        elif key == "kind":
            if args.kind is None:
                args.kind = str(val)
        else:
            # Non-native key: stash for post-discovery filtering.
            args._extra_filters[key] = val

    args._sort = view_cfg.sort
    args._view_cfg = view_cfg


def _apply_extra_filters(items: list, extra: dict[str, Any]) -> list:
    """Post-discovery equality filter for non-native frontmatter keys."""
    if not extra:
        return items
    return [
        m for m in items
        if all(str(m.frontmatter.get(k, "")) == str(v) for k, v in extra.items())
    ]


def _apply_sort(items: list, sort_key: str | None) -> list:
    """Lexicographic sort on *sort_key*, missing values sorted last."""
    if not sort_key:
        return items
    reverse = sort_key.startswith("-")
    key = sort_key.lstrip("-")
    return sorted(
        items,
        key=lambda m: (
            str(m.frontmatter.get(key, "")) == "",
            str(m.frontmatter.get(key, "")),
        ),
        reverse=reverse,
    )


def _resolve_columns(
    args: Any,
    view_cfg: ViewConfig | None,
    registry: Registry,
    kind_def: KindDef | None = None,
) -> list:
    """Precedence: explicit --fields > view.columns > registry default."""
    if args.fields:
        return views.parse_field_specs(args.fields)
    if view_cfg is not None and view_cfg.columns:
        return views.parse_field_specs(view_cfg.columns)
    if kind_def is not None:
        return views.default_columns(kind_def)
    return views.parse_field_specs("name,status,kind")
