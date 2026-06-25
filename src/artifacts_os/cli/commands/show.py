"""cli show command — display a single artifact."""

import argparse
import json
import os
import subprocess
import sys

from rich.console import Console

import artifacts_os.views as views
from artifacts_os.core import get, Registry
from artifacts_os.core.errors import NotFoundError, ValidationError
from artifacts_os.core.models import Artifact


def _is_interactive() -> bool:
    """Return True when running in a human-interactive context.

    Settings-driven defaults that require a live terminal (e.g. opening an
    editor) must not fire for non-interactive callers such as agents, CI
    pipelines, or piped shells.

    Detection follows the artifact-kind prefix convention:
    - ``CLAUDECODE`` env var is set by the Claude Code agent runtime.
    - A missing stdout TTY covers other non-interactive callers.
    """
    if os.environ.get("CLAUDECODE"):
        return False
    return sys.stdout.isatty()


def register(subparsers) -> None:
    p = subparsers.add_parser("show", help="show an artifact")
    p.add_argument("ref", help="artifact reference (name, id, or partial)")
    p.add_argument("--kind", "-k", help="narrow to a specific kind")
    p.add_argument("--meta", action="store_true",
                   help="frontmatter only (no body)")
    # Rejected flags: parsed (suppressed) so we can emit clear error messages.
    p.add_argument("--view", "-V", dest="_view_reject", default=None,
                   help=argparse.SUPPRESS)
    p.add_argument("--status", "-s", dest="_status_reject", default=None,
                   help=argparse.SUPPRESS)
    p.add_argument("--children", dest="_children_reject", default=None,
                   help=argparse.SUPPRESS)
    p.add_argument("--parent", dest="_parent_reject", action="store_true",
                   help=argparse.SUPPRESS)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-j", "--json", action="store_true", dest="json_out",
                      help="JSON output")
    mode.add_argument("-e", "--editor", action="store_true",
                      help="open in $EDITOR")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    # Reject flags that are not valid on 'show'.
    if getattr(args, "_view_reject", None) is not None:
        raise ValidationError("--view is not valid on 'show' (use 'list --view')")
    if getattr(args, "_status_reject", None) is not None:
        raise ValidationError("--status is not valid on 'show'")
    if getattr(args, "_children_reject", None) is not None:
        raise ValidationError(
            "--children is not valid on 'show' (use 'list --children <ref>')"
        )
    if getattr(args, "_parent_reject", False):
        raise ValidationError(
            "--parent is not valid on 'show' (use 'list --parent <ref>')"
        )

    artifact: Artifact = get(registry, args.ref, kind=args.kind or None)

    if args.meta:
        return _render_meta(args, artifact, registry)

    if args.json_out:
        data = dict(artifact.frontmatter, body=artifact.body)
        print(json.dumps(data, default=str))
        return 0

    # editor mode: explicit -e flag, or default from cli settings (unless -j was given).
    # Built-in default is True — show opens the file in $EDITOR on any interactive TTY.
    # The config key cli.defaults.show.editor is now an opt-out (set to false to suppress).
    # The settings-driven default is suppressed in non-interactive / agent contexts
    # so that agents always receive artifact content on stdout.
    open_editor = args.editor
    if not open_editor and _is_interactive():
        cli_settings = getattr(args, "cli_settings", None)
        show_defaults = (cli_settings.defaults.get("show") or {}) if cli_settings is not None else {}
        open_editor = bool(show_defaults.get("editor", True))

    if open_editor:
        editor = os.environ.get("EDITOR", "vi")
        subprocess.run([editor, str(artifact.path)])
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
    status_colors = kind_def.meta.get("status_colors") if kind_def is not None else None
    table = views.render_table([artifact], columns, status_colors=status_colors)
    console.print(table)

    if artifact.body.strip():
        console.print()
        console.print(artifact.body, markup=False)

    return 0


def _render_meta(args, artifact: Artifact, registry: Registry) -> int:
    """Render frontmatter only (no body).

    JSON mode: emit ``json.dumps(frontmatter)``.
    Editor mode: open the artifact file directly (explicit ``-e`` flag only;
        settings-driven defaults do not apply inside ``--meta`` mode).
    Table mode: render all frontmatter keys as a one-row table.
    """
    if args.json_out:
        print(json.dumps(artifact.frontmatter, default=str))
        return 0

    # Editor mode: open the resolved file (--parent already redirected artifact).
    open_editor = args.editor
    if open_editor:
        editor = os.environ.get("EDITOR", "vi")
        subprocess.run([editor, str(artifact.path)])
        return 0

    # Table: all frontmatter keys in a deterministic order.
    kind_def = None
    try:
        kind_def = registry.get(artifact.kind)
    except ValueError:
        pass

    fm_keys = list(artifact.frontmatter.keys())
    columns = views.parse_field_specs(",".join(fm_keys)) if fm_keys else \
        views.parse_field_specs("id,kind,name,status")

    console = Console()
    status_colors = kind_def.meta.get("status_colors") if kind_def is not None else None
    table = views.render_table([artifact], columns, status_colors=status_colors)
    console.print(table)
    return 0
