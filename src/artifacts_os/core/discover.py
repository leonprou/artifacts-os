"""Discovery: list_artifacts, resolve, search.

Spec: s2060-artifacts-os-architecture § discover.py
"""

import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

from artifacts_os.core import frontmatter as _frontmatter
from artifacts_os.core.errors import AmbiguousError, NotFoundError, ValidationError
from artifacts_os.core.models import ArtifactMeta, KindDef

if TYPE_CHECKING:
    from artifacts_os.core.registry import Registry


_PREFIXED_ID_RE = re.compile(r"^([a-z]+)(\d+)$")
_ALL_DIGITS_RE = re.compile(r"^\d+$")
_WIKILINK_RE = re.compile(r"^\[\[(.+?)\]\]$")

# Built-in ArtifactMeta fields always accepted as filter keys.
_BUILTIN_FILTER_KEYS: frozenset[str] = frozenset(
    {"id", "kind", "name", "title", "status", "tags", "created"}
)


def _require_root(registry: "Registry") -> Path:
    if registry.root is None:
        raise RuntimeError("Registry.root is not set; cannot perform file I/O")
    return registry.root


def _kind_dir(registry: "Registry", kd: KindDef) -> Path:
    return _require_root(registry) / "artifacts" / kd.dir


def _meta_from_file(path: Path) -> ArtifactMeta:
    text = path.read_text(encoding="utf-8")
    fm, _ = _frontmatter.parse(text)
    name = fm.get("name", path.stem)
    tags = fm.get("tags", []) or []
    return ArtifactMeta(
        id=fm.get("id", ""),
        kind=fm.get("kind", ""),
        name=name,
        title=name,
        status=fm.get("status"),
        tags=list(tags),
        created=str(fm.get("created", "")),
        path=path,
        frontmatter=dict(fm),
    )


def _known_keys_for_kind(registry: "Registry", kind_name: str) -> set[str]:
    """Return the set of known filter keys for a given kind name."""
    known: set[str] = set(_BUILTIN_FILTER_KEYS)
    try:
        kd = registry.get(kind_name)
    except ValueError:
        return known
    schema = kd.schema
    known |= set(schema.get("properties", {}).keys())
    known |= set(schema.get("required", []))
    return known


def _validate_filters(
    registry: "Registry",
    kind: str | None,
    filters: dict[str, Any],
) -> None:
    """Raise ValidationError if *filters* contains keys unknown for *kind*.

    When *kind* is None (cross-kind query), a key is known if it is known
    for at least one registered kind — per s0014 §6.3.
    """
    if not filters:
        return
    if kind is not None:
        known = _known_keys_for_kind(registry, kind)
    else:
        known = set()
        for kd in registry.all():
            known |= _known_keys_for_kind(registry, kd.name)
    for key in filters:
        if key not in known:
            raise ValidationError(
                f"unknown filter key {key!r} for kind {kind!r}; "
                f"known keys: {sorted(known)}"
            )


def list_artifacts(
    registry: "Registry",
    kind: str | None = None,
    *,
    filters: dict[str, Any] | None = None,
    status: str | None = None,   # deprecated — use filters={"status": ...}
    tag: str | None = None,      # deprecated — use filters={"tags": ...}
) -> list[ArtifactMeta]:
    """List artifacts; optionally filter by kind and/or frontmatter predicates.

    Parameters
    ----------
    registry:
        Vault registry.
    kind:
        Restrict to this kind's directory (see s0014 §5 for why ``kind``
        is a named parameter rather than living inside ``filters``).
    filters:
        Keyword-only dict of frontmatter-equality predicates.  Every
        ``(key, value)`` pair must match for an artifact to be included.
        The special key ``"tags"`` uses list-membership semantics
        (``str(value) in meta.tags``); all other keys use stringified
        equality (``str(meta.frontmatter.get(key, "")) == str(value)``).
        A list value (other than for ``"tags"``) is interpreted as
        OR-within-key — the artifact matches when **any** element
        compares equal under the same stringified rule. See
        s0023-multi-value-filters § 3.

    Deprecated
    ----------
    status:
        Use ``filters={"status": ...}`` instead.  Emits
        ``DeprecationWarning`` when passed.  Scheduled for removal in
        the next minor release (v0.N+1).
    tag:
        Use ``filters={"tags": ...}`` instead.  Same deprecation policy.
    """
    # Deprecation shim — fold legacy kwargs into filters.
    if status is not None or tag is not None:
        warnings.warn(
            "list_artifacts(status=..., tag=...) is deprecated; "
            "use filters={'status': ..., 'tags': ...} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        filters = dict(filters or {})
        if status is not None:
            filters.setdefault("status", status)
        if tag is not None:
            filters.setdefault("tags", tag)

    _require_root(registry)
    _validate_filters(registry, kind, filters or {})

    kinds = [registry.get(kind)] if kind else registry.all()

    results: list[ArtifactMeta] = []
    for kd in kinds:
        subdir = _kind_dir(registry, kd)
        if not subdir.is_dir():
            continue
        for path in sorted(subdir.glob("*.md")):
            meta = _meta_from_file(path)
            if filters:
                match = True
                for k, v in filters.items():
                    if k == "tags":
                        # `tags` keeps list-membership semantics. A scalar
                        # value means "the meta has this tag"; a list value
                        # means "any of these tags is present".
                        meta_tags = meta.frontmatter.get("tags") or []
                        if isinstance(v, list):
                            if not any(str(elem) in meta_tags for elem in v):
                                match = False
                                break
                        elif str(v) not in meta_tags:
                            match = False
                            break
                    elif isinstance(v, list):
                        # Multi-value OR within key (s0023 § 3.1).
                        meta_val = str(meta.frontmatter.get(k, ""))
                        if not any(meta_val == str(elem) for elem in v):
                            match = False
                            break
                    else:
                        if str(meta.frontmatter.get(k, "")) != str(v):
                            match = False
                            break
                if not match:
                    continue
            results.append(meta)
    return results


def _find_in_dir(subdir: Path, query: str, kind_prefix: str) -> list[Path]:
    """Apply match strategies and return candidates (may be 0, 1, or >1)."""
    if not subdir.is_dir():
        return []

    all_mds = list(subdir.glob("*.md"))

    # 1. Exact stem
    exact = [p for p in all_mds if p.stem == query]
    if len(exact) == 1:
        return exact

    # 2. Prefixed short/full ID (e.g. t42 → t0042)
    m = _PREFIXED_ID_RE.match(query)
    if m:
        letters, digits = m.group(1), m.group(2)
        expanded = f"{letters}{int(digits):04d}"
        prefixed = [
            p
            for p in all_mds
            if p.stem == expanded or p.stem.startswith(f"{expanded}-")
        ]
        if len(prefixed) == 1:
            return prefixed
        if prefixed:
            return prefixed

    # 3. Old-style numeric (all digits)
    if _ALL_DIGITS_RE.match(query):
        padded = query.zfill(4)
        numeric = [
            p
            for p in all_mds
            if p.stem.startswith(f"{padded}-")
            or (kind_prefix and p.stem.startswith(f"{kind_prefix}{padded}-"))
        ]
        if len(numeric) == 1:
            return numeric
        if numeric:
            return numeric

    # 4. Partial stem
    partial = [p for p in all_mds if query in p.stem]
    return partial


def _resolve_in_kind(
    registry: "Registry", query: str, kd: KindDef
) -> list[Path]:
    return _find_in_dir(_kind_dir(registry, kd), query, kd.prefix)


def resolve(
    registry: "Registry",
    query: str,
    *,
    kind: str | None = None,
) -> Path:
    """Resolve a query to a single Path. Raises NotFound or Ambiguous."""
    _require_root(registry)

    if kind is not None:
        kd = registry.get(kind)
        matches = _resolve_in_kind(registry, query, kd)
        return _pick_one(matches, query)

    # All kinds: first kind directory with an unambiguous single match wins.
    candidates_per_kind: list[list[Path]] = []
    for kd in registry.all():
        matches = _resolve_in_kind(registry, query, kd)
        if len(matches) == 1:
            return matches[0]
        if matches:
            candidates_per_kind.append(matches)

    merged: list[Path] = [p for group in candidates_per_kind for p in group]
    return _pick_one(merged, query)


def _pick_one(matches: list[Path], query: str) -> Path:
    if not matches:
        raise NotFoundError(f"No artifact matches {query!r}")
    if len(matches) == 1:
        return matches[0]
    exact = [p for p in matches if p.stem == query]
    if len(exact) == 1:
        return exact[0]
    listing = "\n  ".join(str(p) for p in matches)
    raise AmbiguousError(
        f"Query {query!r} matches multiple artifacts:\n  {listing}"
    )


def search(
    registry: "Registry",
    query: str,
    *,
    kind: str | None = None,
) -> list[ArtifactMeta]:
    """Like resolve, but returns all matches as ArtifactMeta (no raises)."""
    _require_root(registry)

    kinds = [registry.get(kind)] if kind else registry.all()
    all_matches: list[Path] = []
    seen: set[Path] = set()
    for kd in kinds:
        for path in _resolve_in_kind(registry, query, kd):
            if path not in seen:
                seen.add(path)
                all_matches.append(path)

    return [_meta_from_file(p) for p in sorted(all_matches)]


# ---------------------------------------------------------------------------
# Graph traversal — parent / children
# ---------------------------------------------------------------------------

def unwrap_wikilink(value: str) -> str:
    """Return the inner ref of ``[[ref]]``, or the value unchanged."""
    m = _WIKILINK_RE.match(value.strip())
    return m.group(1) if m else value.strip()


# Back-compat alias — kept private for one release cycle.
_unwrap_wikilink = unwrap_wikilink


def _ensure_meta(
    registry: "Registry",
    ref: "str | ArtifactMeta | Path",
    *,
    kind: str | None = None,
) -> ArtifactMeta:
    """Coerce *ref* to an ArtifactMeta."""
    if isinstance(ref, ArtifactMeta):
        return ref
    if isinstance(ref, Path):
        return _meta_from_file(ref)
    # String ref — resolve and read.
    path = resolve(registry, ref, kind=kind)
    return _meta_from_file(path)


def parent(
    registry: "Registry",
    ref: "str | ArtifactMeta | Path",
    *,
    kind: str | None = None,
) -> ArtifactMeta | None:
    """Resolve and return the parent ArtifactMeta of *ref*.

    Reads the ``parent`` frontmatter field (Obsidian wikilink ``[[ref]]`` or
    bare ref string), unwraps it to a bare ref, and resolves cross-kind via
    :func:`resolve` (no ``kind`` restriction so task → spec works).

    Returns ``None`` if the artifact has no ``parent`` field at all.
    Raises :class:`~artifacts_os.core.errors.NotFoundError` if the field
    exists but the wikilink does not resolve (broken link).
    Raises :class:`~artifacts_os.core.errors.AmbiguousError` if the
    wikilink resolves to multiple artifacts.
    """
    meta = _ensure_meta(registry, ref, kind=kind)
    parent_val = meta.frontmatter.get("parent")
    if not parent_val:
        return None
    bare_ref = _unwrap_wikilink(str(parent_val))
    try:
        parent_path = resolve(registry, bare_ref)
    except NotFoundError:
        raise NotFoundError(
            f"parent of '{meta.path.stem}' refers to '{bare_ref}' which does not exist"
        )
    except AmbiguousError as exc:
        raise AmbiguousError(
            f"parent of '{meta.path.stem}' refers to '{bare_ref}' which is ambiguous:\n  {exc}"
        ) from exc
    return _meta_from_file(parent_path)


def children(
    registry: "Registry",
    ref: "str | ArtifactMeta | Path",
    *,
    kind: str | None = None,
    status: str | None = None,
) -> list[ArtifactMeta]:
    """List direct children of *ref*.

    Iterates :func:`list_artifacts` filtered by *kind* and *status*, then
    returns those whose ``parent`` frontmatter field resolves to the same
    artifact as *ref*.  Resolution uses :func:`resolve` for identity
    comparison by canonical path, so different ref forms (``t36``,
    ``t0036``, ``t0036-name``, ``[[t0036-name]]``) all match correctly.

    Returns ``[]`` if the artifact has no children.  Never raises on an
    empty result — empty is a valid answer to a predicate query.
    """
    parent_meta = _ensure_meta(registry, ref, kind=None)
    parent_path = parent_meta.path

    items = list_artifacts(
        registry,
        kind=kind,
        filters={"status": status} if status is not None else None,
    )
    result: list[ArtifactMeta] = []
    for item in items:
        raw_parent = item.frontmatter.get("parent")
        if not raw_parent:
            continue
        bare_ref = _unwrap_wikilink(str(raw_parent))
        try:
            resolved_path = resolve(registry, bare_ref)
        except (NotFoundError, AmbiguousError):
            continue
        if resolved_path == parent_path:
            result.append(item)
    return result
