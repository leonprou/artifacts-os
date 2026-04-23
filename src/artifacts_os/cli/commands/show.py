"""cli show command — display a single artifact."""

import json
import os
import subprocess

from rich.console import Console

import artifacts_os.views as views
from artifacts_os.core import get, Registry
from artifacts_os.core.models import Artifact


def register(subparsers) -> None:
    p = subparsers.add_parser("show", help="show an artifact")
    p.add_argument("ref", help="artifact reference (name, id, or partial)")
    p.add_argument("--kind", "-k", help="narrow to a specific kind")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-j", "--json", action="store_true", dest="json_out", help="JSON output")
    mode.add_argument("-e", "--editor", action="store_true", help="open in $EDITOR")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    artifact: Artifact = get(registry, args.ref, kind=args.kind or None)

    if args.json_out:
        data = dict(artifact.frontmatter, body=artifact.body)
        print(json.dumps(data, default=str))
        return 0

    if args.editor:
        editor = os.environ.get("EDITOR", "vi")
        subprocess.run([editor, str(artifact.path)], check=False)
        return 0

    # Default: render frontmatter as a one-row table, then print body
    kind_def = None
    try:
        kind_def = registry.get(artifact.kind)
    except ValueError:
        pass

    if kind_def is not None:
        columns = views.default_columns(kind_def)
    else:
        columns = views.parse_field_specs("name,status,kind,created")

    console = Console()
    table = views.render_table([artifact], columns, kind_def=kind_def)
    console.print(table)

    if artifact.body.strip():
        console.print()
        console.print(artifact.body)

    return 0
