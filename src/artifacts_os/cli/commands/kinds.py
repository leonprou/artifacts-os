"""cli kinds command — list registered artifact kinds.

Spec: s0017-artifact-kinds-discovery-mechanism § 8.2, § 8.3
"""

import json

from rich.console import Console
from rich.table import Table

from artifacts_os.core import Registry
from artifacts_os.core.kinds_catalog import KindCatalog

_DESCRIPTION_MAX_DISPLAY = 60  # characters shown in the table column


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
    # -q mode: one name per line — unchanged from baseline (s0017 § 8.3)
    if args.quiet:
        for kd in sorted(registry.all(), key=lambda kd: kd.name):
            print(kd.name)
        return 0

    # Build KindCatalog entries for table and JSON modes (D8: CLI is a thin
    # printer over KindCatalog.list_kinds()).
    root = registry.root
    catalog = KindCatalog(registry, root) if root is not None else None
    entries_by_name = {}
    if catalog is not None:
        for entry in catalog.list_kinds():
            entries_by_name[entry.name] = entry

    kinds = sorted(registry.all(), key=lambda kd: kd.name)

    if args.json_out:
        payload = []
        for kd in kinds:
            entry = entries_by_name.get(kd.name)
            payload.append(
                {
                    "name": kd.name,
                    "dir": kd.dir,
                    "prefix": kd.prefix,
                    "numbered": kd.numbered,
                    "statuses": kd.statuses,
                    "description": entry.description if entry else kd.description,
                    "has_template": entry.has_template if entry else kd.has_template,
                }
            )
        print(json.dumps(payload, default=str))
        return 0

    # Default: rich table with description column
    table = Table(show_header=True, header_style="bold")
    table.add_column("name")
    table.add_column("dir")
    table.add_column("prefix")
    table.add_column("numbered")
    table.add_column("statuses")
    table.add_column("description")

    for kd in kinds:
        entry = entries_by_name.get(kd.name)
        description = entry.description if entry else kd.description
        prefix_str = kd.prefix if kd.prefix else "[dim](none)[/dim]"
        statuses_str = ", ".join(kd.statuses) if kd.statuses else "[dim](none)[/dim]"
        numbered_str = "yes" if kd.numbered else "no"
        if description:
            desc_display = (
                description[:_DESCRIPTION_MAX_DISPLAY] + "…"
                if len(description) > _DESCRIPTION_MAX_DISPLAY
                else description
            )
        else:
            desc_display = "[dim](no description)[/dim]"
        table.add_row(kd.name, kd.dir, prefix_str, numbered_str, statuses_str, desc_display)

    Console().print(table)
    return 0
