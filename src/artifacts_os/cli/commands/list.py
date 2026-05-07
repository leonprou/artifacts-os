"""cli list command — list artifacts with optional filters."""

import argparse
import json
import sys
from typing import Any

from rich.console import Console

import artifacts_os.views as views
from artifacts_os.core import list_artifacts, Registry
from artifacts_os.core.models import KindDef
from artifacts_os.core.errors import ValidationError
from artifacts_os.views.models import ViewConfig, ViewsSettings


# ---------------------------------------------------------------------------
# Schema-derived flag helpers
# ---------------------------------------------------------------------------

# Flag names that the static ``list`` parser already registers.
# Schema properties whose generated flag would collide are silently skipped;
# the field remains reachable via ``--filter k=v``.
# §13.4: "layout" is reserved so a future kind property named "layout" does
# not silently collide with the --layout flag.
# s0024 §5.1: "prune" reserved for the same reason — `--prune` is a CLI
# flag, not a per-kind frontmatter filter.
_RESERVED_FILTER_FLAG_NAMES: frozenset[str] = frozenset({
    "help", "kind", "filter", "view", "fields", "meta",
    "quiet", "json", "children", "parent", "layout", "prune",
})


def _parse_bool(value: str) -> bool:
    """Parse a boolean CLI argument.

    Accepts ``true|false|1|0|yes|no`` case-insensitively.  Raises
    ``argparse.ArgumentTypeError`` for any other input.

    ``argparse``'s built-in ``type=bool`` is famously broken (returns
    ``True`` for any non-empty string), so a custom helper is required.
    """
    low = value.lower()
    if low in ("true", "1", "yes"):
        return True
    if low in ("false", "0", "no"):
        return False
    raise argparse.ArgumentTypeError(
        f"expected true/false/1/0/yes/no, got: {value!r}"
    )


def _split_csv(raw: str) -> list[str]:
    """Split *raw* on commas, rejecting empty elements.

    Per s0023-multi-value-filters § 3.4, an empty CSV element
    (``a,,b``, ``a,``, ``,a``) is a ValidationError. Single values
    return a single-element list.
    """
    parts = raw.split(",")
    if any(p == "" for p in parts):
        raise argparse.ArgumentTypeError(
            f"empty value in CSV (got {raw!r}); "
            "use comma-separated non-empty values"
        )
    return parts


def _make_enum_csv_type(enum_values: list, *, validate: bool):
    """Return an argparse ``type=`` callable for an enum-string field.

    The callable splits on ``,`` and (when *validate* is True) checks
    each element against *enum_values*. Returns ``list[str]``.

    Per s0023-multi-value-filters § 3.4, ``choices=`` on the underlying
    argparse argument is dropped because it runs against the raw CSV
    string and would reject any multi-value input.
    """
    enum_set = {str(v) for v in enum_values}
    enum_listing = ", ".join(str(v) for v in enum_values)

    def _csv_enum(raw: str) -> list[str]:
        parts = _split_csv(raw)
        if validate:
            for elem in parts:
                if elem not in enum_set:
                    raise argparse.ArgumentTypeError(
                        f"invalid value {elem!r} "
                        f"(choose from: {enum_listing})"
                    )
        return parts

    return _csv_enum


def _flag_kwargs_for_prop(field: str, prop: dict) -> dict | None:
    """Return the ``add_argument`` keyword arguments for *prop*, or ``None``.

    Returns ``None`` when the property should be skipped (list-typed, or
    has neither ``type`` nor ``enum`` — no useful filter semantics).
    The mapping follows s0015 §4.1.
    """
    # Skip list-typed properties (deferred in v1 per §4.5).
    if prop.get("type") == "array" or "items" in prop:
        return None

    enum = prop.get("enum")
    prop_type = prop.get("type")

    # Skip if neither type nor enum declared (no value semantics).
    if enum is None and prop_type is None:
        return None

    help_text = prop.get("description") or f"filter by {field}"
    kwargs: dict[str, Any] = {"dest": field, "default": None, "help": help_text}

    if enum is not None:
        # CSV-aware: --status ready,in-progress,review (s0023 § 3.4).
        # `choices=` is dropped because argparse runs it against the raw
        # string and would always reject multi-value input; the custom
        # `type=` callable enforces enum membership per element.
        kwargs["type"] = _make_enum_csv_type(enum, validate=True)
        kwargs["metavar"] = "|".join(str(v) for v in enum) + "[,...]"
    elif prop_type == "integer":
        kwargs["type"] = int
        kwargs["metavar"] = "INT"
    elif prop_type == "boolean":
        kwargs["type"] = _parse_bool
        kwargs["metavar"] = "BOOL"
    else:
        # "string" or any other declared type — free-form string.
        kwargs["type"] = str
        kwargs["metavar"] = "TEXT"

    return kwargs


def _add_schema_filter_flags(p: argparse.ArgumentParser, schema: dict) -> list[str]:
    """Add per-kind filter flags from *schema* ``properties``.

    Per s0015 §6.3, ``--status`` is handled here (not added statically)
    and gets the ``-s`` short form with kind-specific ``choices=``.
    All other schema-derived flags get only their long ``--<flag>`` form.

    Returns the list of ``dest`` names that were added.
    """
    generated: list[str] = []
    for field, prop in schema.get("properties", {}).items():
        if field in _RESERVED_FILTER_FLAG_NAMES:
            continue
        kwargs = _flag_kwargs_for_prop(field, prop)
        if kwargs is None:
            continue
        flag = f"--{field.replace('_', '-')}"
        if field == "status":
            # Special case: preserve -s short form (s0015 §6.3).
            p.add_argument(flag, "-s", **kwargs)
        else:
            p.add_argument(flag, **kwargs)
        generated.append(field)
    return generated


def _add_union_filter_flags(
    p: argparse.ArgumentParser,
    all_schemas: dict[str, dict],
) -> list[str]:
    """Add cross-kind union filter flags (no ``choices=``) from *all_schemas*.

    When ``--kind`` is absent, every property name across all registered
    vault schemas contributes one flag.  No ``choices=`` is set because the
    same property name may have different enums per kind (s0015 §5.2).

    Returns the list of ``dest`` names that were added.
    """
    # Collect all property names with their per-kind shapes.
    # Preserve insertion order so the first kind's description is stable.
    union: dict[str, list[tuple[str, dict]]] = {}  # field → [(kind, prop), ...]
    for kind_name, schema in all_schemas.items():
        for field, prop in schema.get("properties", {}).items():
            union.setdefault(field, []).append((kind_name, prop))

    generated: list[str] = []
    for field, kind_props in union.items():
        if field in _RESERVED_FILTER_FLAG_NAMES:
            continue

        # Skip list-typed in v1.
        if any(p.get("type") == "array" or "items" in p for _, p in kind_props):
            continue

        # Skip if no useful type info in any kind.
        if all(
            p.get("enum") is None and p.get("type") is None
            for _, p in kind_props
        ):
            continue

        flag = f"--{field.replace('_', '-')}"
        has_enum = any(kp.get("enum") is not None for _, kp in kind_props)

        # Help text: first kind's description; suffix if they differ.
        descs = [kp.get("description") or "" for _, kp in kind_props]
        base_desc = descs[0] or f"filter by {field}"
        if len(set(descs)) > 1 or has_enum:
            help_text = base_desc + " (varies by kind — pass --kind for choices)"
        else:
            help_text = base_desc

        kwargs: dict[str, Any] = {"dest": field, "default": None, "help": help_text}

        if has_enum:
            # Enums diverge across kinds — no per-element validation, but
            # still accept CSV input for parity with per-kind mode
            # (s0023 § 3.4). Core's silent-no-match handles bogus values.
            kwargs["type"] = _make_enum_csv_type([], validate=False)
            kwargs["metavar"] = (
                "STATUS[,...]" if field == "status" else "VARIES[,...]"
            )
        else:
            # Determine the most permissive compatible type.
            all_types = {kp.get("type") for _, kp in kind_props if kp.get("type")}
            if all_types == {"integer"}:
                kwargs["type"] = int
                kwargs["metavar"] = "INT"
            elif all_types == {"boolean"}:
                kwargs["type"] = _parse_bool
                kwargs["metavar"] = "BOOL"
            elif all_types == {"string"}:
                kwargs["type"] = str
                kwargs["metavar"] = "TEXT"
            else:
                kwargs["metavar"] = "VARIES"

        if field == "status":
            # Keep -s short form in cross-kind mode too (s0015 §4.3).
            p.add_argument(flag, "-s", **kwargs)
        else:
            p.add_argument(flag, **kwargs)
        generated.append(field)
    return generated


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------


def register(
    subparsers,
    kind: str | None = None,
    schema: dict | None = None,
    all_schemas: "dict[str, dict] | None" = None,
) -> None:
    """Register the ``list`` sub-command.

    When *schema* is provided (per-kind mode), schema-derived filter flags
    with ``choices=`` are added and ``--status`` is augmented with the
    kind-specific enum.  When *all_schemas* is provided (cross-kind mode),
    a union of all properties is added without ``choices=``.  Otherwise the
    static ``--status -s`` flag is used.
    """
    p = subparsers.add_parser("list", help="list artifacts")
    p.add_argument("--kind", "-k", help="filter by kind")
    p.add_argument(
        "--filter",
        dest="filter",
        action="append",
        metavar="K=V",
        help="repeatable frontmatter-equality filter; e.g. --filter assignee=alice "
             "--filter type=feature. Last value wins per key.",
    )
    p.add_argument("--children", help="direct children of <ref> (selection predicate)")
    p.add_argument("--parent", help="parent of <ref> (returns 0 or 1 records as array)")
    p.add_argument("--view", "-V", help="named view from artifacts.yaml")

    proj = p.add_mutually_exclusive_group()
    proj.add_argument("--fields", "-f",
                      help="field spec string (e.g. 'id,name,status')")
    proj.add_argument("--meta", action="store_true",
                      help="full frontmatter per row (overrides --fields/view.columns)")

    p.add_argument(
        "--layout",
        default=None,
        metavar="NAME",
        help=(
            "presentation layout for the result; auto-detects from kind when omitted"
            " (e.g. tasks render as a tree by default)"
        ),
    )

    # s0024 §5.1 — --prune NAME (tree-only). Choices read from PRUNE_MODES so
    # future modes register in one place.
    p.add_argument(
        "--prune",
        default=None,
        choices=sorted(views.PRUNE_MODES),
        metavar="NAME",
        help=(
            "pruning mode for tree layouts (strict|ancestors|subtree);"
            " ignored for non-tree layouts"
        ),
    )

    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-q", "--quiet", action="store_true", help="one name per line")
    mode.add_argument("-j", "--json", action="store_true", dest="json_out",
                      help="JSON output")

    # Schema-derived filter flags — sets _generated_filter_fields on the namespace.
    if schema is not None:
        # Per-kind mode: typed flags with choices= where schema has enum.
        generated = _add_schema_filter_flags(p, schema)
        if "status" not in generated:
            # Schema has no status property; add the static fallback.
            p.add_argument("--status", "-s", help="filter by status")
    elif all_schemas is not None:
        # Cross-kind mode: union of all properties, no choices=.
        generated = _add_union_filter_flags(p, all_schemas)
        if "status" not in generated:
            p.add_argument("--status", "-s", help="filter by status")
    else:
        # Static mode: no schema info available.
        p.add_argument("--status", "-s", help="filter by status")
        generated = []

    # Positional ref-set filter — placed last so it does not shadow options.
    p.add_argument(
        "refs",
        nargs="*",
        metavar="REF",
        default=[],
        help=(
            "optional ref-set: restrict output to these artifacts only "
            "(intersection with all other filters). Accepts numeric IDs (t1), "
            "full names, partial slugs, or [[wikilinks]]. "
            "When --kind is supplied, partial-slug refs resolve within that kind only. "
            "An unresolvable ref is an error; no partial output is produced."
        ),
    )

    p.set_defaults(func=run, _generated_filter_fields=generated)


# ---------------------------------------------------------------------------
# Filter resolution
# ---------------------------------------------------------------------------


def resolve_filters(
    args: Any,
    view_cfg: "ViewConfig | None",
) -> "tuple[str | None, dict[str, Any]]":
    """Compose the effective (kind, filters) from view config and CLI flags.

    Resolution order (per-key, last wins):
    1. View config ``filters`` dict — seeded first.
    2. Explicit ``--kind`` / ``--status`` CLI flags — override per key.
    3. Schema-derived generated flags (``--type``, ``--priority``, etc.) —
       override per key (s0015 §8.1).
    4. Repeated ``--filter k=v`` tokens — override per key, last wins.

    ``kind`` is then popped from the dict and returned as the first element
    of the tuple (directory-selection axis, not a frontmatter predicate).

    Raises ``ValidationError`` on malformed ``--filter`` tokens (missing ``=``).
    """
    # 1. Seed from view config.
    filters: dict[str, Any] = dict(view_cfg.filters) if view_cfg else {}

    # 2. Apply explicit CLI flag overrides per-key.
    if args.kind is not None:
        filters["kind"] = args.kind
    if args.status is not None:
        filters["status"] = args.status

    # 3. Apply schema-derived generated flags; each overrides per-key.
    for field in getattr(args, "_generated_filter_fields", ()):
        if field == "status":
            continue  # already handled in step 2 via args.status
        val = getattr(args, field, None)
        if val is not None:
            filters[field] = val

    # 4. Apply --filter k=v tokens; last value wins per key.
    for token in (getattr(args, "filter", None) or []):
        if "=" not in token:
            raise ValidationError(f"--filter expects key=value, got: {token}")
        k, _, v = token.partition("=")
        filters[k] = v

    # 5. Split kind out (directory axis — s0014 §5).
    kind = filters.pop("kind", None)

    return kind, filters


# ---------------------------------------------------------------------------
# Layout resolution (spec §8.2)
# ---------------------------------------------------------------------------


def resolve_layout(
    args: Any,
    view_cfg: "ViewConfig | None",
    settings: "ViewsSettings | None",
    kind_def: "KindDef | None",
) -> str:
    """Resolve the effective layout name per spec §8.2 precedence chain.

    Chain (first match wins):
    1. Explicit ``--layout NAME`` flag.
    2. Active view's ``layout`` field.
    3. ``default_layouts[kind]`` in artifacts.yaml.
    4. Implicit ``"table"`` — universal fallback.
    """
    if getattr(args, "layout", None):
        return args.layout
    if view_cfg is not None and getattr(view_cfg, "layout", None):
        return view_cfg.layout
    if settings is not None and settings.views is not None:
        m = settings.views.default_layouts
        if kind_def is not None and kind_def.name in m:
            return m[kind_def.name].layout
    return "table"


def resolve_parent_field(
    args: Any,
    view_cfg: "ViewConfig | None",
    settings: "ViewsSettings | None",
    kind_def: "KindDef | None",
) -> "str | None":
    """Resolve the effective parent_field for tree layout per spec §8.2.

    Chain (first match wins):
    1. Active view's ``parent_field`` field.
    2. ``default_layouts[kind].parent_field`` in artifacts.yaml.

    Returns ``None`` when no source provides a parent_field.
    """
    if view_cfg is not None and getattr(view_cfg, "parent_field", None):
        return view_cfg.parent_field
    if settings is not None and settings.views is not None:
        m = settings.views.default_layouts
        if kind_def is not None and kind_def.name in m:
            return m[kind_def.name].parent_field
    return None


def resolve_prune(
    args: Any,
    view_cfg: "ViewConfig | None",
    settings: "ViewsSettings | None",
    kind_def: "KindDef | None",
) -> str:
    """Resolve the effective prune mode per s0024 §4 precedence chain.

    Chain (first match wins):
    1. Explicit ``--prune NAME`` flag.
    2. Active view's ``prune`` field.
    3. ``default_layouts[kind].prune`` in artifacts.yaml.
    4. Implicit ``"strict"`` — preserves s0022 §6.4 / §7 v1 behaviour.
    """
    if getattr(args, "prune", None):
        return args.prune
    if view_cfg is not None and getattr(view_cfg, "prune", None):
        return view_cfg.prune
    if settings is not None and settings.views is not None:
        m = settings.views.default_layouts
        if (
            kind_def is not None
            and kind_def.name in m
            and m[kind_def.name].prune
        ):
            return m[kind_def.name].prune
    return "strict"


def _build_sort_key(sort_str: str | None):
    """Convert a sort string (e.g. ``"id"`` or ``"-created"``) to a key callable.

    The returned callable accepts an ``ArtifactMeta`` and returns a value
    suitable for ``sorted(..., key=...)``.  Missing-value behaviour matches
    ``_apply_sort``: missing values sort last for ascending, first for
    descending (consistent with the pre-existing ``_apply_sort``).

    Returns ``None`` when *sort_str* is falsy (no sort requested).
    """
    if not sort_str:
        return None

    reverse = sort_str.startswith("-")
    field = sort_str.lstrip("-")

    if not reverse:
        def _asc(m) -> tuple:
            val = str(m.frontmatter.get(field, ""))
            return (val == "", val)
        return _asc

    # Descending: wrap value so that comparisons are inverted, with missing
    # values sorting first (matching ``_apply_sort(reverse=True)`` behaviour).
    class _Rev:
        __slots__ = ("val",)

        def __init__(self, v: str) -> None:
            self.val = v

        def __lt__(self, other: "_Rev") -> bool:  # type: ignore[override]
            return self.val > other.val

        def __gt__(self, other: "_Rev") -> bool:  # type: ignore[override]
            return self.val < other.val

        def __le__(self, other: "_Rev") -> bool:  # type: ignore[override]
            return self.val >= other.val

        def __ge__(self, other: "_Rev") -> bool:  # type: ignore[override]
            return self.val <= other.val

        def __eq__(self, other: object) -> bool:
            return isinstance(other, _Rev) and self.val == other.val

    def _desc(m) -> tuple:
        val = str(m.frontmatter.get(field, ""))
        # missing=True sorts first in descending (matches _apply_sort reverse=True)
        return (val == "", _Rev(val))

    return _desc


# ---------------------------------------------------------------------------
# Command runner
# ---------------------------------------------------------------------------


def run(args, registry: Registry) -> int:
    from artifacts_os.cli import _load_views_settings

    views_settings = _load_views_settings(registry.root)
    _apply_view(args, views_settings)

    # Resolve --children ref before running list_artifacts.
    children_parent_path = None
    if getattr(args, "children", None):
        from artifacts_os.core.discover import resolve
        children_parent_path = resolve(registry, args.children)

    # Resolve --parent: list the parent record of <ref> as a 0-or-1 array.
    parent_meta = None
    parent_requested = False
    if getattr(args, "parent", None):
        from artifacts_os.core import parent as _parent_fn
        parent_requested = True
        parent_meta = _parent_fn(registry, args.parent)

    # Compose effective (kind, filters) from view + CLI flags.
    view_cfg: ViewConfig | None = getattr(args, "_view_cfg", None)
    effective_kind, effective_filters = resolve_filters(args, view_cfg)

    items = list_artifacts(
        registry,
        kind=effective_kind,
        filters=effective_filters or None,
    )

    # NOTE: flat _apply_sort is intentionally deferred — applied per output
    # mode below.  -q/-j always sort flat.  tree layout passes sort_key into
    # compute_tree; table layout applies _apply_sort before render_table.

    # Apply --children predicate as a post-discovery filter.
    if children_parent_path is not None:
        from artifacts_os.core.discover import _unwrap_wikilink, resolve as _resolve
        from artifacts_os.core.errors import NotFoundError, AmbiguousError
        filtered = []
        for item in items:
            raw_parent = item.frontmatter.get("parent")
            if not raw_parent:
                continue
            bare = _unwrap_wikilink(str(raw_parent))
            try:
                resolved = _resolve(registry, bare)
            except (NotFoundError, AmbiguousError):
                continue
            if resolved == children_parent_path:
                filtered.append(item)
        items = filtered

    # Apply --parent: replace items with the resolved parent (or empty).
    if parent_requested:
        if parent_meta is None:
            items = []
        else:
            # Match the parent record from items by path; honor kind/status filters.
            items = [m for m in items if m.path == parent_meta.path]
            if not items and effective_kind is None and not effective_filters:
                # No filters in play: include the parent directly.
                items = [parent_meta]

    # Apply positional ref-set filter if supplied.
    refs_arg: list[str] = getattr(args, "refs", None) or []
    if refs_arg:
        from artifacts_os.core.discover import _unwrap_wikilink
        from artifacts_os.core.discover import resolve as _resolve_ref
        from artifacts_os.core.errors import NotFoundError as _NotFoundError
        from artifacts_os.core.errors import AmbiguousError as _AmbiguousError

        resolved_paths: list = []
        not_found: list[str] = []
        ambiguous_msgs: list[str] = []

        for ref in refs_arg:
            bare = _unwrap_wikilink(ref)
            try:
                path = _resolve_ref(registry, bare, kind=effective_kind)
                resolved_paths.append(path)
            except _NotFoundError:
                not_found.append(bare)
            except _AmbiguousError as exc:
                ambiguous_msgs.append(str(exc))

        if not_found or ambiguous_msgs:
            for bare in not_found:
                print(f"error: unresolved ref '{bare}'", file=sys.stderr)
            for msg in ambiguous_msgs:
                print(f"error: {msg}", file=sys.stderr)
            return 4 if ambiguous_msgs else 3

        ref_paths: set = set(resolved_paths)
        items = [m for m in items if m.path in ref_paths]

    # -q and -j: layout selection skipped; sort still applies on flat data (§8.4).
    if args.quiet:
        for item in _apply_sort(items, getattr(args, "_sort", None)):
            print(item.path.stem)
        return 0

    if args.json_out:
        sorted_items = _apply_sort(items, getattr(args, "_sort", None))
        print(json.dumps([item.frontmatter for item in sorted_items], default=str))
        return 0

    # Default: rich table/tree
    if not items:
        return 0

    kind_def: KindDef | None = None
    if effective_kind:
        try:
            kind_def = registry.get(effective_kind)
        except ValueError:
            pass
    elif items:
        first_kind = items[0].kind
        try:
            kind_def = registry.get(first_kind)
        except ValueError:
            pass

    # Resolve effective layout (§8.2).
    layout = resolve_layout(args, view_cfg, views_settings, kind_def)
    if layout not in views.LAYOUTS:
        raise ValidationError(
            f"unknown layout {layout!r}; known: {sorted(views.LAYOUTS)}"
        )

    # --meta: project all frontmatter keys (union across items).
    if getattr(args, "meta", False):
        columns = _meta_columns(items)
    else:
        columns = _resolve_columns(args, view_cfg, registry, kind_def)

    sort_str = getattr(args, "_sort", None)

    if layout == "tree":
        # Resolve parent_field (§8.2 parallel chain).
        parent_field = resolve_parent_field(args, view_cfg, views_settings, kind_def)
        if parent_field is None:
            raise ValidationError(
                "layout 'tree' requires a parent_field but none was resolved; "
                "set default_layouts.<kind>.parent_field or view.parent_field "
                "in artifacts.yaml (spec §8.2)"
            )
        # Property-existence guard: parent_field must be in the kind schema (§3.6).
        if kind_def is not None and parent_field not in kind_def.schema_properties:
            raise ValidationError(
                f"parent_field {parent_field!r} is not a property of kind "
                f"{kind_def.name!r}; known properties: "
                f"{sorted(kind_def.schema_properties)}"
            )

        # Resolve prune mode (s0024 §4). --children / --parent neutralizes
        # prune (§3.5) — those flags already define an explicit slice.
        prune = resolve_prune(args, view_cfg, views_settings, kind_def)
        if children_parent_path is not None or parent_requested:
            prune = "strict"

        # When prune != strict the renderer needs the unfiltered set of the
        # same kind to walk ancestors / descendants (s0024 §6.3 / §6.4).
        full_items: list | None = None
        if prune != "strict":
            full_items = list_artifacts(registry, kind=effective_kind)

        # Sort flows into compute_tree (§6.2); flat _apply_sort not applied.
        sort_key_fn = _build_sort_key(sort_str)
        table = views.render_tree(
            items,
            columns,
            kind_def=kind_def,
            parent_field=parent_field,
            sort_key=sort_key_fn,
            is_known_stem=registry.exists_stem,
            prune=prune,
            full_items=full_items,
        )
    else:
        # Table layout: apply flat sort then render.
        items = _apply_sort(items, sort_str)
        table = views.render_table(items, columns, kind_def=kind_def)

    Console().print(table)
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _meta_columns(items: list) -> list:
    """Build an ordered column list from the union of all frontmatter keys.

    Canonical order: id, kind, name, status, created — then all remaining
    keys in sorted order.
    """
    leading = ["id", "kind", "name", "status", "created"]
    seen: set[str] = set()
    all_keys: list[str] = []
    for item in items:
        for k in item.frontmatter:
            if k not in seen:
                seen.add(k)
                all_keys.append(k)

    ordered = [k for k in leading if k in seen]
    ordered += sorted(k for k in all_keys if k not in set(leading))
    return views.parse_field_specs(",".join(ordered)) if ordered else \
        views.parse_field_specs("id,kind,name,status")


def _apply_view(args: Any, settings: ViewsSettings | None) -> None:
    """Resolve the active view and mutate *args* with sort cfg.

    Sets ``args._view_cfg`` and ``args._sort``.  Filter seeds are no
    longer stashed here — ``resolve_filters`` reads ``view_cfg.filters``
    directly (s0014 §8.3).

    Raises ValidationError on unknown view names so the caller's except
    cascade surfaces it as exit 2.
    """
    args._sort = None
    args._view_cfg = None

    binding_kind = args.kind  # may be None

    view_name: str | None = getattr(args, "view", None)

    # Auto-bind from default_views when no explicit --view.
    if view_name is None and binding_kind is not None and settings is not None:
        if settings.views is not None:
            bound = settings.views.default_views.get(binding_kind)
            if bound is not None:
                # Validate the bound view exists before using it.
                if bound not in settings.views.views:
                    raise ValidationError(
                        f"default_views.{binding_kind} refers to unknown view '{bound}'"
                    )
                view_name = bound

    # Resolve ViewConfig.
    view_cfg: ViewConfig | None = None
    if view_name is not None:
        if settings is None or settings.views is None:
            raise ValidationError(
                f"unknown view '{view_name}' (no 'views:' section in artifacts.yaml)"
            )
        if view_name not in settings.views.views:
            raise ValidationError(f"unknown view '{view_name}'")
        view_cfg = settings.views.views[view_name]

    if view_cfg is None:
        return

    args._sort = view_cfg.sort
    args._view_cfg = view_cfg


def _apply_sort(items: list, sort_key: str | None) -> list:
    """Lexicographic sort on *sort_key*, missing values sorted last."""
    if not sort_key:
        return items
    reverse = sort_key.startswith("-")
    key = sort_key.lstrip("-")
    return sorted(
        items,
        key=lambda m: (
            str(m.frontmatter.get(key, "")) == "",
            str(m.frontmatter.get(key, "")),
        ),
        reverse=reverse,
    )


def _resolve_columns(
    args: Any,
    view_cfg: ViewConfig | None,
    registry: Registry,
    kind_def: KindDef | None = None,
) -> list:
    """Precedence: explicit --fields > view.columns > registry default."""
    if args.fields:
        return views.parse_field_specs(args.fields)
    if view_cfg is not None and view_cfg.columns:
        return views.parse_field_specs(view_cfg.columns)
    if kind_def is not None:
        return views.default_columns(kind_def)
    return views.parse_field_specs("name,status,kind")
