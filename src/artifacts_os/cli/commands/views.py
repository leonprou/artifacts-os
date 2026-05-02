"""cli views command — list named views defined in artifacts.yaml."""

import json
import sys

from rich.console import Console
from rich.table import Table

from artifacts_os.core import Registry


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "views",
        help="list defined views",
        description=(
            "List all named views defined in artifacts/artifacts.yaml, "
            "including the per-kind default_views bindings."
        ),
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-q", "--quiet", action="store_true",
                      help="one view name per line")
    mode.add_argument("-j", "--json", action="store_true", dest="json_out",
                      help="JSON output")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    # Reuse the existing loader; it returns None on any error.
    from artifacts_os.cli import _load_views_settings
    settings = _load_views_settings(registry.root)

    views_cfg = settings.views if settings is not None else None
    views_map = views_cfg.views if views_cfg is not None else {}
    defaults = views_cfg.default_views if views_cfg is not None else {}

    # Empty path — no views defined
    if not views_map:
        if args.json_out:
            print(json.dumps({"views": [], "default_views": dict(defaults)},
                             default=str))
            return 0
        if args.quiet:
            return 0
        print("no views defined in artifacts.yaml", file=sys.stderr)
        return 0

    # Reverse-index default_views: kind → view  →  view → [kinds]
    reverse: dict[str, list[str]] = {}
    for kind, view_name in defaults.items():
        reverse.setdefault(view_name, []).append(kind)
    for kinds_list in reverse.values():
        kinds_list.sort()

    names = sorted(views_map.keys())

    if args.quiet:
        for name in names:
            print(name)
        return 0

    if args.json_out:
        payload = {
            "views": [
                {
                    "name": name,
                    "columns": views_map[name].columns,
                    "filters": dict(views_map[name].filters),
                    "sort": views_map[name].sort,
                    "default_for": reverse.get(name, []),
                }
                for name in names
            ],
            "default_views": dict(defaults),
        }
        print(json.dumps(payload, default=str))
        return 0

    # Default — rich table
    table = Table(show_header=True, header_style="bold")
    table.add_column("name")
    table.add_column("kind")
    table.add_column("columns")
    table.add_column("sort")
    table.add_column("default-for")

    for name in names:
        v = views_map[name]
        kind = v.filters.get("kind") if v.filters else None
        kind_cell = str(kind) if kind else "[dim](any)[/dim]"
        cols = v.columns
        if len(cols) > 60:
            cols = cols[:57] + "…"
        sort_cell = v.sort if v.sort else "[dim](none)[/dim]"
        bound = reverse.get(name, [])
        bound_cell = ", ".join(bound) if bound else "[dim](none)[/dim]"
        table.add_row(name, kind_cell, cols, sort_cell, bound_cell)

    Console().print(table)
    return 0
