"""cli list command — list artifacts with optional filters."""

import json

from rich.console import Console

import artifacts_os.views as views
from artifacts_os.core import list_artifacts, Registry
from artifacts_os.core.models import KindDef


def register(subparsers) -> None:
    p = subparsers.add_parser("list", help="list artifacts")
    p.add_argument("--kind", "-k", help="filter by kind")
    p.add_argument("--status", "-s", help="filter by status")
    p.add_argument("--fields", "-f", help="field spec string (e.g. 'id,name,status')")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-q", "--quiet", action="store_true", help="one name per line")
    mode.add_argument("-j", "--json", action="store_true", dest="json_out", help="JSON output")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    items = list_artifacts(
        registry,
        kind=args.kind or None,
        status=args.status or None,
    )

    if args.quiet:
        for item in items:
            print(item.name)
        return 0

    if args.json_out:
        print(json.dumps([item.frontmatter for item in items], default=str))
        return 0

    # Default: rich table
    if not items:
        return 0

    kind_def: KindDef | None = None
    if args.kind:
        try:
            kind_def = registry.get(args.kind)
        except ValueError:
            pass
    elif items:
        # All same kind when no filter; use first item's kind
        first_kind = items[0].kind
        try:
            kind_def = registry.get(first_kind)
        except ValueError:
            pass

    if args.fields:
        columns = views.parse_field_specs(args.fields)
    elif kind_def is not None:
        columns = views.default_columns(kind_def)
    else:
        columns = views.parse_field_specs("name,status,kind")

    table = views.render_table(items, columns, kind_def=kind_def)
    Console().print(table)
    return 0
