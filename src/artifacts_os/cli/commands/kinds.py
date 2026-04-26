"""cli kinds command — list registered artifact kinds."""

import json

from rich.console import Console
from rich.table import Table

from artifacts_os.core import Registry


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "kinds",
        help="list registered kinds",
        description=(
            "List all artifact kinds registered with the active project, "
            "including any vault-defined kinds under artifacts/kinds/."
        ),
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-q", "--quiet", action="store_true", help="one kind name per line")
    mode.add_argument("-j", "--json", action="store_true", dest="json_out", help="JSON output")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    kinds = sorted(registry.all(), key=lambda kd: kd.name)

    if args.quiet:
        for kd in kinds:
            print(kd.name)
        return 0

    if args.json_out:
        payload = [
            {
                "name": kd.name,
                "dir": kd.dir,
                "prefix": kd.prefix,
                "numbered": kd.numbered,
                "statuses": kd.statuses,
            }
            for kd in kinds
        ]
        print(json.dumps(payload, default=str))
        return 0

    # Default: rich table
    table = Table(show_header=True, header_style="bold")
    table.add_column("name")
    table.add_column("dir")
    table.add_column("prefix")
    table.add_column("numbered")
    table.add_column("statuses")

    for kd in kinds:
        prefix_str = kd.prefix if kd.prefix else "[dim](none)[/dim]"
        statuses_str = ", ".join(kd.statuses) if kd.statuses else "[dim](none)[/dim]"
        numbered_str = "yes" if kd.numbered else "no"
        table.add_row(kd.name, kd.dir, prefix_str, numbered_str, statuses_str)

    Console().print(table)
    return 0
