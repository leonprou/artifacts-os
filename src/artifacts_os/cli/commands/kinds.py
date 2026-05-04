"""cli kinds command — list registered artifact kinds or show detail for one.

Spec: s0017-artifact-kinds-discovery-mechanism § 8.2, § 8.3
"""

import json
import os
import sys

from rich.console import Console
from rich.table import Table

from artifacts_os.core import Registry
from artifacts_os.core.kinds_catalog import KindCatalog

_DESCRIPTION_MAX_DISPLAY = 60  # characters shown in the table column


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "kinds",
        help="list registered kinds or show detail for one",
        description=(
            "List all artifact kinds registered with the active project, "
            "including any vault-defined kinds under artifacts/kinds/. "
            "When <name> is given, print the full ARTIFACT.md body for that kind. "
            "Use --meta to prepend kind metadata above the body, "
            "or -j for JSON output with both meta and body."
        ),
    )
    p.add_argument(
        "name",
        nargs="?",
        default=None,
        metavar="<name>",
        help="kind name; when given, print detail for that kind instead of the listing",
    )
    p.add_argument(
        "--meta",
        action="store_true",
        help="prepend a metadata block above the ARTIFACT.md body (requires <name>)",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-q", "--quiet", action="store_true", help="one kind name per line")
    mode.add_argument("-j", "--json", action="store_true", dest="json_out", help="JSON output")
    mode.add_argument(
        "-e",
        "--editor",
        action="store_true",
        help="open ARTIFACT.md in $EDITOR (requires <name>)",
    )
    p.set_defaults(func=run)


def _build_meta(kd) -> dict:
    """Build the metadata dict for a KindDef."""
    return {
        "name": kd.name,
        "dir": kd.dir,
        "prefix": kd.prefix,
        "numbered": kd.numbered,
        "statuses": kd.statuses,
        "description": kd.description,
    }


def _run_single(args, registry: Registry) -> int:
    """Handle `artifacts kinds <name>` — single-kind detail."""
    name = args.name

    # Resolve the kind; unknown name → error with available kinds list.
    try:
        kd = registry.get(name)
    except ValueError:
        available = sorted(kd.name for kd in registry.all())
        print(
            f"error: unknown kind {name!r}. "
            f"Available kinds: {', '.join(available)}",
            file=sys.stderr,
        )
        return 3

    # Locate ARTIFACT.md.
    artifact_md = None
    if registry.root is not None:
        candidate = registry.root / "artifacts" / "kinds" / name / "ARTIFACT.md"
        if candidate.exists():
            artifact_md = candidate

    meta = _build_meta(kd)

    # JSON mode: always includes meta; body is null when ARTIFACT.md absent.
    if args.json_out:
        body = artifact_md.read_text(encoding="utf-8") if artifact_md is not None else None
        print(json.dumps({"meta": meta, "body": body}, default=str))
        return 0

    # Editor mode: open ARTIFACT.md in $EDITOR. ARTIFACT.md must exist.
    # In non-interactive contexts (pipes, CI), silently downgrade to default
    # text output to avoid hanging — same policy as `show -e` (s0017 cli).
    if args.editor:
        if artifact_md is None:
            print(
                f"error: no `ARTIFACT.md` defined for kind `{name}`",
                file=sys.stderr,
            )
            return 3
        if sys.stdout.isatty():
            editor = os.environ.get("EDITOR", "vi")
            os.execvp(editor, [editor, str(artifact_md)])
        # fall through to default text rendering when not a TTY

    # Text modes: ARTIFACT.md must exist.
    if artifact_md is None:
        print(
            f"error: no `ARTIFACT.md` defined for kind `{name}`",
            file=sys.stderr,
        )
        return 3

    body = artifact_md.read_text(encoding="utf-8")

    if args.meta:
        # Prepend a YAML-like metadata block, visually separated from the body.
        lines = ["---"]
        for key, value in meta.items():
            if isinstance(value, list):
                lines.append(f"{key}: [{', '.join(value)}]")
            else:
                lines.append(f"{key}: {value}")
        lines.append("---")
        lines.append("")
        prefix_block = "\n".join(lines)
        print(prefix_block + body, end="")
    else:
        print(body, end="")

    return 0


def run(args, registry: Registry) -> int:
    # --meta without <name> is a usage error.
    if args.meta and not args.name:
        print("error: --meta requires <name>", file=sys.stderr)
        return 2

    # -e / --editor without <name> is a usage error.
    if args.editor and not args.name:
        print("error: --editor requires <name>", file=sys.stderr)
        return 2

    # Route to single-kind detail when <name> is given.
    if args.name:
        return _run_single(args, registry)

    # --- Listing mode (no <name>) ---

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
