"""Discovery: list_artifacts, resolve, search.

Spec: s2060-artifacts-os-architecture § discover.py
"""

import re
from pathlib import Path
from typing import TYPE_CHECKING

from artifacts_os.core import frontmatter as _frontmatter
from artifacts_os.core.errors import AmbiguousError, NotFoundError
from artifacts_os.core.models import ArtifactMeta, KindDef

if TYPE_CHECKING:
    from artifacts_os.core.registry import Registry


_PREFIXED_ID_RE = re.compile(r"^([a-z]+)(\d+)$")
_ALL_DIGITS_RE = re.compile(r"^\d+$")


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


def list_artifacts(
    registry: "Registry",
    *,
    kind: str | None = None,
    status: str | None = None,
    tag: str | None = None,
) -> list[ArtifactMeta]:
    """List artifacts; optionally filter by kind, status, or tag."""
    _require_root(registry)
    kinds = [registry.get(kind)] if kind else registry.all()

    results: list[ArtifactMeta] = []
    for kd in kinds:
        subdir = _kind_dir(registry, kd)
        if not subdir.is_dir():
            continue
        for path in sorted(subdir.glob("*.md")):
            meta = _meta_from_file(path)
            if status is not None and meta.status != status:
                continue
            if tag is not None and tag not in meta.tags:
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
