"""cli get command — read one or all frontmatter properties from an artifact."""

import json

from rich.console import Console
from rich.table import Table

from artifacts_os.core import Registry, get_prop
from artifacts_os.core.store import get as _store_get


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "get",
        help="read a frontmatter property (or all properties) from an artifact",
    )
    p.add_argument("ref", help="artifact reference (name, id, or partial)")
    p.add_argument(
        "property",
        nargs="?",
        default=None,
        help="property name; omit to list all frontmatter fields",
    )
    p.add_argument("-j", "--json", action="store_true", dest="json_out",
                   help="JSON output")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    if args.property is not None:
        # Single-property mode.
        value = get_prop(registry, args.ref, args.property)
        if args.json_out:
            print(json.dumps({"property": args.property, "value": value}, default=str))
        else:
            print(value)
        return 0

    # All-properties mode — print frontmatter as a key-value table (no body).
    artifact = _store_get(registry, args.ref)
    if args.json_out:
        print(json.dumps(artifact.frontmatter, default=str))
        return 0

    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Property")
    table.add_column("Value")
    for key, val in artifact.frontmatter.items():
        table.add_row(key, str(val) if val is not None else "")
    console.print(table)
    return 0
