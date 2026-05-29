"""cli transitions command — inspect legal next-values for state-machined properties."""

import json
from dataclasses import asdict

from rich.console import Console
from rich.table import Table

from artifacts_os.core import Registry, transitions_for
from artifacts_os.core.models import TransitionView


def _view_to_dict(view: TransitionView) -> dict:
    return {
        "property": view.property,
        "current": view.current,
        "allowed_next": list(view.allowed_next),
        "wildcard_targets": list(view.wildcard_targets),
        "locked": view.locked,
    }


def _render_table(views: list[TransitionView]) -> Table:
    table = Table(show_header=True, header_style="bold")
    table.add_column("property")
    table.add_column("current")
    table.add_column("allowed_next")
    table.add_column("wildcard_targets")
    table.add_column("locked?")
    for v in views:
        table.add_row(
            v.property,
            str(v.current) if v.current is not None else "",
            ", ".join(str(x) for x in v.allowed_next),
            ", ".join(str(x) for x in v.wildcard_targets),
            "yes" if v.locked else "no",
        )
    return table


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "transitions",
        help="show legal next-values for state-machined properties",
    )
    p.add_argument("ref", help="artifact reference (name, id, or partial)")
    p.add_argument(
        "property",
        nargs="?",
        default=None,
        help="property name; omit to show all state-machined properties",
    )
    p.add_argument("-j", "--json", action="store_true", dest="json_out",
                   help="JSON output")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    result = transitions_for(registry, args.ref, args.property)
    console = Console()

    if isinstance(result, TransitionView):
        # Single-property result.
        if args.json_out:
            print(json.dumps(_view_to_dict(result), default=str))
        else:
            console.print(_render_table([result]))
    else:
        # All-properties result (dict).
        if args.json_out:
            print(json.dumps(
                {prop: _view_to_dict(v) for prop, v in result.items()},
                default=str,
            ))
        else:
            if result:
                console.print(_render_table(list(result.values())))
            else:
                console.print("[dim]No state-machined properties declared for this kind.[/dim]")

    return 0
