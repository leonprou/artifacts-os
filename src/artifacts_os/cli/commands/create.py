"""cli create command — create a new artifact."""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

from artifacts_os.core import create, Registry, ValidationError, NotFoundError
from artifacts_os.core import frontmatter as _frontmatter
from artifacts_os.core.discover import resolve as _resolve, unwrap_wikilink as _unwrap_wikilink


# Scalar wikilink fields — value stored as a single "[[ref]]" string.
_SCALAR_WIKILINK_FIELDS = frozenset({"parent"})
# Array wikilink fields — value stored as a list of "[[ref]]" strings.
_ARRAY_WIKILINK_FIELDS = frozenset({"depends_on", "subtasks", "artifacts"})
# Combined — kept for convenience / back-compat.
_WIKILINK_FIELDS = _SCALAR_WIKILINK_FIELDS | _ARRAY_WIKILINK_FIELDS

# Schema property names that already have dedicated convenience flags.
# Augment (Variant B) skips these to avoid double-registration.
_CONVENIENCE_FIELD_NAMES = frozenset({"assignee", "owner", "parent", "depends_on", "type"})

# Flag names that must never be re-registered by augment (conflict avoidance).
_RESERVED_FLAGS = frozenset({
    "help", "version", "kind", "body", "body_file", "name",
    "fields", "dry_run", "title",
})


def _wrap_wikilink(value: str) -> str:
    """Wrap *value* as ``[[value]]`` unless it is already wrapped."""
    value = value.strip()
    if value.startswith("[[") and value.endswith("]]"):
        return value
    return f"[[{value}]]"


def _array_wikilink_fields_from_schema(schema: dict | None) -> frozenset[str]:
    """Return the set of array wikilink fields, augmented by schema detection.

    Starts from the hardcoded ``_ARRAY_WIKILINK_FIELDS`` baseline and adds
    any schema ``properties`` whose ``items.pattern`` contains ``[[``
    (i.e. wikilink array fields declared in the kind schema).
    """
    if not schema:
        return _ARRAY_WIKILINK_FIELDS
    detected: set[str] = set()
    for field, prop in schema.get("properties", {}).items():
        if prop.get("type") != "array" and "items" not in prop:
            continue
        items_pattern = prop.get("items", {}).get("pattern", "")
        if r"\[\[" in items_pattern or "[[" in items_pattern:
            detected.add(field)
    return _ARRAY_WIKILINK_FIELDS | frozenset(detected)


def _field_in_schema(field: str, schema: dict) -> bool:
    """Return True if *field* is declared in schema properties or x-columns."""
    if field in schema.get("properties", {}):
        return True
    for col in schema.get("x-columns", []):
        col_name = col.split(":")[0]
        if col_name == field:
            return True
    return False


def _schema_has_columns(schema: dict) -> bool:
    """Return True when the schema has explicit x-columns declarations.

    The filter (Variant A) is applied only when x-columns is present —
    that signals the kind has an explicit opinion about which fields matter.
    Schemas with only ``properties`` (e.g. minimal test schemas) are treated
    as generic and show all convenience flags.
    """
    return bool(schema.get("x-columns"))


def _metavar_for_prop(prop: dict) -> str:
    t = prop.get("type", "string")
    if t == "integer":
        return "INT"
    enum = prop.get("enum")
    if enum:
        return "|".join(str(v) for v in enum)
    return "TEXT"


def _add_kind_flags(p, schema: dict) -> list[str]:
    """Add kind-specific flags from schema properties (Variant B).

    Returns the list of field names that were added as dedicated flags.
    """
    kind_fields: list[str] = []
    for field, prop in schema.get("properties", {}).items():
        if field in _CONVENIENCE_FIELD_NAMES:
            continue
        dest = field  # dest uses the raw field name (underscores)
        if dest in _RESERVED_FLAGS:
            continue
        flag = f"--{field.replace('_', '-')}"
        help_text = prop.get("description", f"set frontmatter {field}")
        enum = prop.get("enum")
        if prop.get("type") == "array" or "items" in prop:
            p.add_argument(flag, dest=dest, action="append", metavar="VAL", help=help_text)
        elif enum:
            p.add_argument(flag, dest=dest, choices=enum, metavar="|".join(str(v) for v in enum), help=help_text)
        else:
            p.add_argument(flag, dest=dest, metavar=_metavar_for_prop(prop), help=help_text)
        kind_fields.append(field)
    return kind_fields


def register(subparsers, kind: str | None = None, schema: dict | None = None) -> None:
    """Register the ``create`` sub-command.

    When *kind* and *schema* are provided (Phase 2 of two-phase parsing)
    the parser is built with kind-aware flags (Variant A filter + Variant B
    augment).  When *schema* is ``None`` the parser falls back to the static
    flag set so that unknown-kind errors surface cleanly in ``run()``.
    """
    kind_title = schema.get("title", kind) if schema and kind else None
    description = (
        f"Create a new {kind_title} artifact." if kind_title else None
    )
    p = subparsers.add_parser(
        "create",
        help="create a new artifact",
        description=description,
    )
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

    # Determine which convenience flags to show (Variant A filter).
    # Filter only applies when schema has x-columns (explicit column declarations).
    # Schemas without x-columns are treated as generic: show all convenience flags.
    show_all = schema is None or not _schema_has_columns(schema)

    if show_all or _field_in_schema("assignee", schema):
        p.add_argument("--assignee", help="set frontmatter assignee")

    if show_all or _field_in_schema("owner", schema):
        p.add_argument("--owner", help="set frontmatter owner")

    if show_all or _field_in_schema("parent", schema):
        p.add_argument(
            "--parent",
            help="set frontmatter parent (bare ref auto-wrapped as [[…]])",
        )

    if show_all or _field_in_schema("depends_on", schema):
        p.add_argument(
            "--depends-on",
            dest="depends_on",
            action="append",
            metavar="REF",
            help="add a dependency (auto-wrapped as [[…]]); repeat for multiple",
        )

    if show_all or _field_in_schema("type", schema):
        p.add_argument("--type", dest="type_", help="set frontmatter type")

    # Variant B: augment with kind-specific flags from schema properties.
    kind_fields: list[str] = []
    if schema:
        kind_fields = _add_kind_flags(p, schema)

    # Name (slug) override — always shown
    p.add_argument("--name", help="override the auto-derived slug")

    # Generic key=value fields — always shown (universal escape hatch)
    p.add_argument(
        "--fields",
        "-f",
        nargs="*",
        metavar="KEY=VALUE",
        help=(
            "extra frontmatter fields (e.g. status=ready priority=high); "
            "comma-separated values produce a list (e.g. tags=a,b,c); "
            "wikilink array fields (depends_on, subtasks, artifacts) accept "
            "comma-separated refs auto-wrapped as [[…]] "
            "(e.g. depends_on=t0001,t0002); "
            "setting parent=REF also appends this artifact to the parent's "
            "subtasks array — parent must already exist"
        ),
    )

    # Dry run — always shown
    p.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="print resolved frontmatter and body without writing",
    )
    p.set_defaults(func=run, _kind_specific_fields=kind_fields)


def _parse_fields(field_args: list[str] | None, *, schema: dict | None = None) -> dict:
    """Parse ``KEY=VALUE`` strings into a dict.

    Array wikilink fields (``depends_on``, ``subtasks``, ``artifacts``, and
    any schema-detected equivalents) always produce a list with each element
    wrapped as ``[[…]]``.  A comma-separated value like ``t0001,t0002``
    becomes ``["[[t0001]]", "[[t0002]]"]``.

    Scalar wikilink fields (``parent``) produce a single wrapped string.

    Other fields with a comma-separated value produce a plain list.
    Other fields with a scalar value are stored as-is.
    """
    if not field_args:
        return {}

    array_wikilink = _array_wikilink_fields_from_schema(schema)

    fields: dict = {}
    for item in field_args:
        if "=" not in item:
            raise ValueError(f"Invalid field spec {item!r} — expected KEY=VALUE")
        key, _, raw = item.partition("=")
        key = key.strip()
        raw = raw.strip()

        if key in array_wikilink:
            # Always a list; wrap each element as [[…]].
            parts = [v.strip() for v in raw.split(",") if v.strip()] if "," in raw else [raw]
            fields[key] = [_wrap_wikilink(p) for p in parts]
        elif "," in raw:
            parts = [v.strip() for v in raw.split(",") if v.strip()]
            if key in _SCALAR_WIKILINK_FIELDS:
                parts = [_wrap_wikilink(p) for p in parts]
            fields[key] = parts
        else:
            if key in _SCALAR_WIKILINK_FIELDS:
                raw = _wrap_wikilink(raw)
            fields[key] = raw
    return fields


def _read_body(args) -> str:
    """Return body text from ``--body``, ``--body-file``, or empty string."""
    if args.body_file is not None:
        if args.body_file == "-":
            return sys.stdin.read()
        try:
            return Path(args.body_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(
                f"--body-file: cannot read {args.body_file!r}: {exc.strerror}"
            ) from exc
    return args.body or ""


def _backlink_parent(parent_path: Path, child_stem: str) -> None:
    """Append ``[[child_stem]]`` to the parent's ``subtasks`` list.

    The write is atomic (tmp → replace).  Idempotent: if the wikilink is
    already present the file is left untouched.
    """
    child_link = f"[[{child_stem}]]"
    text = parent_path.read_text(encoding="utf-8")
    meta, body = _frontmatter.parse(text)

    subtasks: list = list(meta.get("subtasks") or [])
    if child_link in subtasks:
        return  # already present — no-op

    subtasks.append(child_link)
    new_meta = {**meta, "subtasks": subtasks}
    new_text = _frontmatter.dump(new_meta, body)

    tmp = parent_path.with_suffix(parent_path.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, parent_path)


def _build_fields(args, *, schema: dict | None = None) -> dict:
    """Merge ``--fields``, convenience flags, and kind-specific flags into a dict.

    Convenience flags take precedence over ``--fields`` for the same key.
    Kind-specific flags (Variant B) also take precedence over ``--fields``.
    """
    fields = _parse_fields(args.fields, schema=schema)

    # Convenience flags (may be absent from namespace if filtered out).
    if getattr(args, "assignee", None) is not None:
        fields["assignee"] = args.assignee
    if getattr(args, "owner", None) is not None:
        fields["owner"] = args.owner
    if getattr(args, "parent", None) is not None:
        fields["parent"] = _wrap_wikilink(args.parent)
    if getattr(args, "depends_on", None):
        fields["depends_on"] = [_wrap_wikilink(d) for d in args.depends_on]
    if getattr(args, "type_", None) is not None:
        fields["type"] = args.type_

    # Kind-specific flags added by Variant B augment.
    for field in getattr(args, "_kind_specific_fields", []):
        val = getattr(args, field, None)
        if val is not None:
            fields[field] = val

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

    # Fetch kind schema for field-type inference (best-effort; errors surface later).
    try:
        schema: dict | None = registry.get(kind).schema
    except Exception:
        schema = None

    try:
        fields = _build_fields(args, schema=schema)
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

    # Parent backlink: resolve parent BEFORE writing the child so a missing
    # parent fails cleanly with no orphaned artifact on disk.
    parent_ref = fields.get("parent")
    parent_path: Path | None = None
    if parent_ref and not args.dry_run:
        parent_inner = _unwrap_wikilink(parent_ref)
        try:
            parent_path = _resolve(registry, parent_inner)
        except NotFoundError:
            print(
                f"error: parent {parent_ref!r} not found — create it first",
                file=sys.stderr,
            )
            return 1

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

    # Back-link child into parent's subtasks array.
    if parent_path is not None:
        _backlink_parent(parent_path, artifact.path.stem)

    # Print the file stem — callers use it as a ref.
    print(artifact.path.stem)
    return 0
