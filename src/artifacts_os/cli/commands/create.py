"""cli create command — create a new artifact."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from artifacts_os.core import create, Registry, ValidationError
from artifacts_os.core import frontmatter as _frontmatter


# Fields whose values are stored as wikilinks in frontmatter.
_WIKILINK_FIELDS = frozenset({"parent", "depends_on"})


def _wrap_wikilink(value: str) -> str:
    """Wrap *value* as ``[[value]]`` unless it is already wrapped."""
    value = value.strip()
    if value.startswith("[[") and value.endswith("]]"):
        return value
    return f"[[{value}]]"


def register(subparsers) -> None:
    p = subparsers.add_parser("create", help="create a new artifact")
    p.add_argument("title", help="artifact title")
    p.add_argument(
        "--kind", "-k",
        default=None,
        help=(
            "artifact kind — resolution order: explicit flag → "
            "cli.defaults.create.kind in artifacts.yaml → 'task'"
        ),
    )

    # Body input — mutually exclusive
    body_group = p.add_mutually_exclusive_group()
    body_group.add_argument("--body", "-b", default=None, help="artifact body text")
    body_group.add_argument(
        "--body-file",
        metavar="PATH",
        help="read body from PATH; use '-' to read from stdin",
    )

    # Convenience flags for common frontmatter fields
    p.add_argument("--assignee", help="set frontmatter assignee")
    p.add_argument("--owner", help="set frontmatter owner")
    p.add_argument(
        "--parent",
        help="set frontmatter parent (bare ref auto-wrapped as [[…]])",
    )
    p.add_argument(
        "--depends-on",
        dest="depends_on",
        action="append",
        metavar="REF",
        help="add a dependency (auto-wrapped as [[…]]); repeat for multiple",
    )
    p.add_argument("--type", dest="type_", help="set frontmatter type")

    # Name (slug) override
    p.add_argument("--name", help="override the auto-derived slug")

    # Generic key=value fields
    p.add_argument(
        "--fields",
        "-f",
        nargs="*",
        metavar="KEY=VALUE",
        help="extra frontmatter fields (e.g. status=ready priority=high); "
             "comma-separated values produce a list (e.g. tags=a,b,c)",
    )

    # Dry run
    p.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="print resolved frontmatter and body without writing",
    )
    p.set_defaults(func=run)


def _parse_fields(field_args: list[str] | None) -> dict:
    """Parse ``KEY=VALUE`` strings into a dict.

    Comma-separated values are split into lists.  Fields in
    ``_WIKILINK_FIELDS`` have each element auto-wrapped as ``[[…]]``.
    """
    if not field_args:
        return {}
    fields: dict = {}
    for item in field_args:
        if "=" not in item:
            raise ValueError(f"Invalid field spec {item!r} — expected KEY=VALUE")
        key, _, raw = item.partition("=")
        key = key.strip()
        raw = raw.strip()
        if "," in raw:
            parts = [v.strip() for v in raw.split(",") if v.strip()]
            if key in _WIKILINK_FIELDS:
                parts = [_wrap_wikilink(p) for p in parts]
            fields[key] = parts
        else:
            if key in _WIKILINK_FIELDS:
                raw = _wrap_wikilink(raw)
            fields[key] = raw
    return fields


def _read_body(args) -> str:
    """Return body text from ``--body``, ``--body-file``, or empty string."""
    if args.body_file is not None:
        if args.body_file == "-":
            return sys.stdin.read()
        path = Path(args.body_file)
        if not path.exists():
            raise ValueError(f"--body-file: file not found: {args.body_file!r}")
        return path.read_text(encoding="utf-8")
    return args.body or ""


def _build_fields(args) -> dict:
    """Merge ``--fields`` and convenience flags into a single dict.

    Convenience flags take precedence over ``--fields`` for the same key.
    """
    fields = _parse_fields(args.fields)
    if args.assignee is not None:
        fields["assignee"] = args.assignee
    if args.owner is not None:
        fields["owner"] = args.owner
    if args.parent is not None:
        fields["parent"] = _wrap_wikilink(args.parent)
    if getattr(args, "depends_on", None):
        fields["depends_on"] = [_wrap_wikilink(d) for d in args.depends_on]
    if args.type_ is not None:
        fields["type"] = args.type_
    # Auto-populate `created` with today's date unless the user supplied
    # one.  Pass a `date` object so YAML emits the value unquoted
    # (`created: 2026-04-30`) — PyYAML otherwise wraps a date-looking
    # string in quotes to disambiguate from a YAML date scalar.
    fields.setdefault("created", date.today())
    return fields


def _print_dry_run(kind: str, slug: str, fields: dict, body: str) -> None:
    """Render a dry-run preview to stdout using YAML frontmatter format."""
    fm_dict: dict = {"kind": kind, "id": "<auto>", "name": slug, **fields}
    preview = _frontmatter.dump(fm_dict, body)
    print("--- dry run (no file written) ---")
    print(preview, end="")
    if not preview.endswith("\n"):
        print()


def _resolve_kind(args) -> str:
    """Return the effective kind using the three-level resolution chain.

    Explicit ``--kind`` flag → ``cli.defaults.create.kind`` from settings
    → hardcoded fallback ``"task"``.
    """
    if args.kind is not None:
        return args.kind
    cli_settings = getattr(args, "cli_settings", None)
    if cli_settings is not None:
        create_defaults = cli_settings.defaults.get("create") or {}
        configured = create_defaults.get("kind")
        if configured:
            return configured
    return "task"


def run(args, registry: Registry) -> int:
    kind = _resolve_kind(args)

    try:
        body = _read_body(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        fields = _build_fields(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Resolve the effective title used to derive the slug.
    # --name overrides slug derivation; the title is kept for the body only.
    from artifacts_os.core.ids import slugify

    if args.name:
        slug = slugify(args.name)
        if not slug:
            print(
                f"error: cannot derive slug from --name {args.name!r}",
                file=sys.stderr,
            )
            return 1
        effective_title = args.name
    else:
        effective_title = args.title
        slug = slugify(effective_title)

    if args.dry_run:
        _print_dry_run(kind, slug, fields, body)
        return 0

    try:
        artifact = create(
            registry,
            kind,
            effective_title,
            body=body,
            fields=fields,
        )
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # Print the file stem — callers use it as a ref.
    print(artifact.path.stem)
    return 0
