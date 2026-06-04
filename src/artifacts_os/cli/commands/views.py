"""cli views command — list, execute, or inspect named views."""

import difflib
import json
import shutil
import sys
import types

from rich.console import Console
from rich.table import Table

from artifacts_os.core import Registry


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "views",
        help="list, execute, or inspect named views",
        description=(
            "With no argument, lists all named views defined in "
            "artifacts.yaml. "
            "Pass a view name to execute it (list matching artifacts). "
            "Use 'show <name>' to inspect a single view's full definition."
        ),
    )
    # nargs="*": [], ["<name>"], or ["show", "<name>"]
    p.add_argument(
        "parts",
        nargs="*",
        help="view name to execute, or 'show <name>' to inspect a view",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="one view name per line (list), columns string (show), or one stem per line (execute)",
    )
    mode.add_argument(
        "-j", "--json",
        action="store_true",
        dest="json_out",
        help="JSON output",
    )
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    # Loader call and reverse-index happen once before dispatch.
    from artifacts_os.cli import _load_views_settings
    _sp = getattr(args, "settings_path", None) or registry.root / "artifacts.yaml"
    settings = _load_views_settings(_sp)

    views_cfg = settings.views if settings is not None else None
    views_map = views_cfg.views if views_cfg is not None else {}
    defaults = views_cfg.default_views if views_cfg is not None else {}

    reverse: dict[str, list[str]] = {}
    for kind, view_name in defaults.items():
        reverse.setdefault(view_name, []).append(kind)
    for kinds_list in reverse.values():
        kinds_list.sort()

    parts = args.parts

    if not parts:
        return _run_list(args, views_map, defaults, reverse)

    if parts[0] == "show":
        if len(parts) != 2:
            print("error: 'views show' requires exactly one view name", file=sys.stderr)
            return 2
        return _run_detail(args, parts[1], views_map, reverse)

    if len(parts) != 1:
        print(f"error: unexpected arguments: {' '.join(parts[1:])}", file=sys.stderr)
        return 2

    return _run_execute(args, parts[0], views_map, registry)


def _run_list(
    args,
    views_map: dict,
    defaults: dict,
    reverse: dict[str, list[str]],
) -> int:
    """List mode — list all defined views."""
    if not views_map:
        if args.json_out:
            print(json.dumps({"views": [], "default_views": dict(defaults)},
                             default=str))
            return 0
        if args.quiet:
            return 0
        print("no views defined in artifacts.yaml", file=sys.stderr)
        return 0

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


def _run_detail(
    args,
    name: str,
    views_map: dict,
    reverse: dict[str, list[str]],
) -> int:
    """Show mode — inspect a single view's full definition."""
    if name not in views_map:
        print(f"error: unknown view '{name}'", file=sys.stderr)
        candidates = difflib.get_close_matches(
            name, list(views_map.keys()), n=3, cutoff=0.6
        )
        if candidates:
            print(f"Did you mean: {', '.join(candidates)}?", file=sys.stderr)
        return 2

    v = views_map[name]

    # -q: print columns field-spec string on one line
    if args.quiet:
        print(v.columns)
        return 0

    # -j: single JSON object (not wrapped in {"views": [...]})
    if args.json_out:
        obj = {
            "name": name,
            "columns": v.columns,
            "filters": dict(v.filters),
            "sort": v.sort,
            "default_for": reverse.get(name, []),
        }
        print(json.dumps(obj, default=str))
        return 0

    # Default: two-column key/value Rich table
    kind = v.filters.get("kind") if v.filters else None
    kind_cell = str(kind) if kind else "[dim](any)[/dim]"

    # filters rendered as indented JSON; (none) when empty
    if v.filters:
        filters_cell = json.dumps(dict(v.filters), indent=2, sort_keys=True, default=str)
    else:
        filters_cell = "[dim](none)[/dim]"

    sort_cell = v.sort if v.sort else "[dim](none)[/dim]"

    bound = reverse.get(name, [])
    bound_cell = ", ".join(bound) if bound else "[dim](none)[/dim]"

    table = Table(show_header=True, header_style="bold")
    table.add_column("field")
    table.add_column("value")

    # Row order: name, kind, columns, filters, sort, default-for
    table.add_row("name", name)
    table.add_row("kind", kind_cell)
    table.add_row("columns", v.columns)  # untruncated
    table.add_row("filters", filters_cell)
    table.add_row("sort", sort_cell)
    table.add_row("default-for", bound_cell)

    # Ensure v.columns is never truncated by a narrow console.
    min_width = len(v.columns) + 18
    term_width = shutil.get_terminal_size(fallback=(80, 24)).columns
    Console(width=max(term_width, min_width)).print(table)
    return 0


def _run_execute(
    args,
    name: str,
    views_map: dict,
    registry: Registry,
) -> int:
    """Execute mode — list artifacts using the named view."""
    if name not in views_map:
        print(f"error: unknown view '{name}'", file=sys.stderr)
        candidates = difflib.get_close_matches(
            name, list(views_map.keys()), n=3, cutoff=0.6
        )
        if candidates:
            print(f"Did you mean: {', '.join(candidates)}?", file=sys.stderr)
        return 2

    from artifacts_os.cli.commands.list import run as list_run

    # Construct a minimal args namespace compatible with list.run.
    list_args = types.SimpleNamespace(
        kind=None,
        status=None,
        filter=None,
        children=None,
        parent=None,
        view=name,
        fields=None,
        meta=False,
        quiet=args.quiet,
        json_out=args.json_out,
        _generated_filter_fields=[],
    )
    return list_run(list_args, registry)
