"""Artifact CRUD: create, get, update.

Spec: s2060-artifacts-os-architecture § store.py
"""

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

import jsonschema

from artifacts_os.core import frontmatter as _frontmatter
from artifacts_os.core.errors import ValidationError
from artifacts_os.core.ids import next_prefixed_id, slugify
from artifacts_os.core.models import Artifact, ArtifactMeta, KindDef

if TYPE_CHECKING:
    from artifacts_os.core.registry import Registry


_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _require_root(registry: "Registry") -> Path:
    if registry.root is None:
        raise RuntimeError("Registry.root is not set; cannot perform file I/O")
    return registry.root


def _kind_dir(registry: "Registry", kd: KindDef) -> Path:
    return _require_root(registry) / "artifacts" / kd.dir


def _validate_schema(kd: KindDef, meta: dict) -> None:
    if not kd.schema:
        return
    try:
        jsonschema.validate(meta, kd.schema)
    except jsonschema.ValidationError as e:
        raise ValidationError(str(e)) from e


def _extract_title(body: str, fallback: str) -> str:
    match = _H1_RE.search(body)
    if match:
        return match.group(1).strip()
    return fallback


def _build_artifact(
    path: Path, meta: dict, body: str, *, read_title: bool = True
) -> Artifact:
    name = meta.get("name", path.stem)
    title = _extract_title(body, name) if read_title else name
    tags = meta.get("tags", []) or []
    return Artifact(
        id=meta.get("id", ""),
        kind=meta.get("kind", ""),
        name=name,
        title=title,
        status=meta.get("status"),
        tags=list(tags),
        created=str(meta.get("created", "")),
        path=path,
        frontmatter=dict(meta),
        body=body,
    )


def create(
    registry: "Registry",
    kind: str,
    title: str,
    *,
    body: str = "",
    fields: dict | None = None,
) -> Artifact:
    """Create a new artifact. Returns the full Artifact."""
    fields = fields or {}
    kd = registry.get(kind)
    subdir = _kind_dir(registry, kd)
    subdir.mkdir(parents=True, exist_ok=True)

    slug = slugify(title)
    if not slug:
        raise ValidationError(f"Cannot derive slug from title: {title!r}")

    # Persisted `name` is slug-only across all kinds. The file path stem
    # encodes the full identifier — `{id}-{slug}` for numbered, `{slug}`
    # for non-numbered. See spec s0002 § Frontmatter — `name` field.
    if kd.numbered:
        last_err: OSError | None = None
        for _ in range(5):
            aid = next_prefixed_id(subdir, kd.prefix)
            stem = f"{aid}-{slug}"
            path = subdir / f"{stem}.md"
            try:
                fd = os.open(
                    path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644
                )
                break
            except FileExistsError as e:
                last_err = e
                continue
        else:
            raise last_err or FileExistsError(
                "Exhausted retries allocating numbered ID"
            )
    else:
        aid = slug
        path = subdir / f"{slug}.md"
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)

    fm_dict: dict = {"kind": kind, "id": aid, "name": slug, **fields}
    _validate_schema(kd, fm_dict)

    text = _frontmatter.dump(fm_dict, body)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        path.unlink(missing_ok=True)
        raise

    parsed_meta, parsed_body = _frontmatter.parse(text)
    return _build_artifact(path, parsed_meta, parsed_body)


def get(
    registry: "Registry",
    ref: str,
    *,
    kind: str | None = None,
) -> Artifact:
    """Resolve ref, read file, return Artifact (with body)."""
    from artifacts_os.core.discover import resolve

    path = resolve(registry, ref, kind=kind)
    text = path.read_text(encoding="utf-8")
    meta, body = _frontmatter.parse(text)
    return _build_artifact(path, meta, body)


def update(
    registry: "Registry",
    ref: str,
    *,
    status: str | None = None,
    fields: dict | None = None,
) -> Artifact:
    """Merge frontmatter updates. Body preserved verbatim."""
    from artifacts_os.core.discover import resolve

    fields = fields or {}
    path = resolve(registry, ref)
    text = path.read_text(encoding="utf-8")
    meta, body = _frontmatter.parse(text)

    kind = meta.get("kind")
    if not kind:
        raise ValidationError(f"Artifact missing 'kind': {path}")
    kd = registry.get(kind)

    if status is not None and kd.statuses and status not in kd.statuses:
        raise ValidationError(
            f"Invalid status {status!r} for kind {kind!r}. "
            f"Allowed: {kd.statuses}"
        )

    new_meta: dict = {**meta, **fields}
    if status is not None:
        new_meta["status"] = status

    _validate_schema(kd, new_meta)

    new_text = _frontmatter.dump(new_meta, body)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, path)

    parsed_meta, parsed_body = _frontmatter.parse(new_text)
    return _build_artifact(path, parsed_meta, parsed_body)
