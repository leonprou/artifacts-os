"""Artifact CRUD: create, get, update.

Spec: s2060-artifacts-os-architecture § store.py
"""

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jsonschema
import yaml

from artifacts_os.core import frontmatter as _frontmatter
from artifacts_os.core import events as _events
from artifacts_os.core.errors import ValidationError


def _yaml_parse_error(path: Path, exc: "yaml.YAMLError") -> str:
    """Return a single-line error message for a YAML parse failure."""
    problem = getattr(exc, "problem", None) or str(exc).splitlines()[0]
    mark = getattr(exc, "problem_mark", None)
    loc = f" (line {mark.line + 1}, col {mark.column + 1})" if mark else ""
    return f"{path}: {problem}{loc}"
from artifacts_os.core.ids import next_prefixed_id, slugify
from artifacts_os.core.models import Artifact, ArtifactMeta, KindDef
from artifacts_os.core.transitions import check_create, check_transition

if TYPE_CHECKING:
    from artifacts_os.core.registry import Registry


_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _require_root(registry: "Registry") -> Path:
    if registry.root is None:
        raise RuntimeError("Registry.root is not set; cannot perform file I/O")
    return registry.root


def _kind_dir(registry: "Registry", kd: KindDef) -> Path:
    return _require_root(registry) / "artifacts" / kd.dir


def _coerce_for_schema(v: object) -> object:
    """Serialize date/datetime to ISO strings before JSON Schema validation.

    PyYAML auto-parses bare dates like ``2026-05-03`` into ``datetime.date``
    objects, but JSON Schema only validates JSON types — ``type: string``
    rejects a ``datetime.date``. Coerce so date-bearing fields validate
    against ``type: string`` schemas without forcing every artifact to
    quote its dates.
    """
    import datetime
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, list):
        return [_coerce_for_schema(x) for x in v]
    if isinstance(v, dict):
        return {k: _coerce_for_schema(x) for k, x in v.items()}
    return v


def _validate_schema(kd: KindDef, meta: dict) -> None:
    if not kd.schema:
        return
    try:
        jsonschema.validate(_coerce_for_schema(meta), kd.schema)
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
    # D203 + D223: enforce strict initial and inject defaults for state-machined properties.
    fields = check_create(kd, fields)
    subdir = _kind_dir(registry, kd)
    subdir.mkdir(parents=True, exist_ok=True)

    slug = slugify(title)
    if not slug:
        raise ValidationError(f"Cannot derive slug from title: {title!r}")

    # Persisted `name` is slug-only across all kinds. The file path stem
    # encodes the full identifier — `{id}-{slug}` for numbered, `{slug}`
    # for non-numbered. See spec s0002 § Frontmatter — `name` field.
    #
    # Directory-storage kinds (s0032 §2.2): bundle dir is `subdir/<stem>/`,
    # manifest is `<bundle_dir>/<manifest_name>`. Same O_EXCL atomicity.
    if kd.storage == "directory":
        if kd.numbered:
            last_err: OSError | None = None
            for _ in range(5):
                aid = next_prefixed_id(subdir, kd.prefix)
                stem = f"{aid}-{slug}"
                bundle_dir = subdir / stem
                manifest_filename = kd.manifest_name.format(
                    slug=slug, id=aid, name=slug, stem=stem
                )
                path = bundle_dir / manifest_filename
                try:
                    bundle_dir.mkdir(exist_ok=True)
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
            stem = slug
            bundle_dir = subdir / slug
            manifest_filename = kd.manifest_name.format(
                slug=slug, id=slug, name=slug, stem=slug
            )
            path = bundle_dir / manifest_filename
            bundle_dir.mkdir(exist_ok=True)
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    else:
        # File-storage kinds: original path.
        if kd.numbered:
            last_err = None
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
            stem = slug
            path = subdir / f"{slug}.md"
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)

    fm_dict: dict = {"kind": kind, "id": aid, "name": slug, **fields}

    # Validate and dispatch pre-phase hooks BEFORE writing content.
    # Any failure after os.open() must close the fd and unlink the
    # reserved (empty) file so no 0-byte orphan is left on disk.
    try:
        _validate_schema(kd, fm_dict)
        _events._dispatch_pre(
            "artifact.created",
            kind=kind,
            id=aid,
            name=slug,
            stem=stem,
            fields=dict(fm_dict),
        )
    except Exception:
        os.close(fd)
        path.unlink(missing_ok=True)
        raise

    text = _frontmatter.dump(fm_dict, body)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        path.unlink(missing_ok=True)
        raise

    parsed_meta, parsed_body = _frontmatter.parse(text)
    artifact = _build_artifact(path, parsed_meta, parsed_body)

    _events._dispatch(
        "artifact.created",
        kind=kind,
        id=aid,
        name=slug,
        stem=stem,
        path=str(path),
        fields=dict(parsed_meta),
    )

    return artifact


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
    try:
        meta, body = _frontmatter.parse(text)
    except yaml.YAMLError as exc:
        raise ValidationError(_yaml_parse_error(path, exc)) from exc
    return _build_artifact(path, meta, body)


def update(
    registry: "Registry",
    ref: "str | Path",
    *,
    status: str | None = None,
    fields: dict | None = None,
    force: bool = False,
    skip_validation: bool = False,
) -> Artifact:
    """Merge frontmatter updates. Body preserved verbatim.

    *ref* may be a name/stem string (resolved via the registry) or an
    absolute Path (used directly, skipping resolution). Passing a Path
    is useful when the caller has already resolved the file and it may
    not live under root/artifacts/ (e.g. legacy vault layouts).

    When *force* is True, state-machine transition validation is skipped.
    Use this when the caller has already validated the transition via its
    own domain rules (e.g. openstation's lifecycle guardrails).

    When *skip_validation* is True, JSON Schema validation is also skipped.
    Use this when the caller manages its own schema constraints and existing
    data may not conform to the kind's JSON Schema (e.g. openstation tasks
    with types outside the standard enum).
    """
    from artifacts_os.core.discover import resolve

    fields = fields or {}
    if isinstance(ref, Path) and ref.is_absolute():
        path = ref
    else:
        path = resolve(registry, str(ref))
    text = path.read_text(encoding="utf-8")
    try:
        meta, body = _frontmatter.parse(text)
    except yaml.YAMLError as exc:
        raise ValidationError(_yaml_parse_error(path, exc)) from exc

    kind = meta.get("kind")
    if not kind:
        raise ValidationError(f"Artifact missing 'kind': {path}")
    kd = registry.get(kind)

    new_meta: dict = {**meta, **fields}
    if status is not None:
        new_meta["status"] = status

    # D209: check every state-machined property whose value would change.
    # The unified check_transition is the single authority for status (and any
    # other state-machined property) at write time — s0033 §5.2. For properties
    # with enum-only declarations (D206), JSON Schema via _validate_schema
    # still enforces target ∈ enum.
    # Skip when force=True: the caller has applied its own validation.
    if not force:
        for prop in kd.state_machines:
            if meta.get(prop) != new_meta.get(prop):
                check_transition(kd, prop, meta.get(prop), new_meta.get(prop))

    if not skip_validation:
        _validate_schema(kd, new_meta)

    # Compute diff for dispatch payload.
    all_keys = set(meta) | set(new_meta)
    changed_keys = [k for k in all_keys if meta.get(k) != new_meta.get(k)]
    diff_before = {k: meta.get(k) for k in changed_keys}
    diff_after = {k: new_meta.get(k) for k in changed_keys}

    aid = meta.get("id", "")
    name = meta.get("name", path.stem)
    stem = path.stem

    _events._dispatch_pre(
        "artifact.updated",
        kind=kind,
        id=aid,
        name=name,
        stem=stem,
        changed=list(changed_keys),
        before=dict(diff_before),
        after=dict(diff_after),
        fields=dict(new_meta),
    )

    # Pre-phase status_changed: allows pre-hooks to block status transitions.
    if "status" in changed_keys:
        _events._dispatch_pre(
            "artifact.status_changed",
            kind=kind,
            id=aid,
            name=name,
            stem=stem,
            before=diff_before["status"],
            after=diff_after["status"],
            fields=dict(new_meta),
        )

    new_text = _frontmatter.dump(new_meta, body)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, path)

    parsed_meta, parsed_body = _frontmatter.parse(new_text)
    artifact = _build_artifact(path, parsed_meta, parsed_body)

    _events._dispatch(
        "artifact.updated",
        kind=kind,
        id=aid,
        name=name,
        stem=stem,
        path=str(path),
        changed=list(changed_keys),
        before=dict(diff_before),
        after=dict(diff_after),
        fields=dict(parsed_meta),
    )

    if "status" in changed_keys:
        _events._dispatch(
            "artifact.status_changed",
            kind=kind,
            id=aid,
            name=name,
            stem=stem,
            path=str(path),
            before=diff_before["status"],
            after=diff_after["status"],
            fields=dict(parsed_meta),
        )

    return artifact


def get_prop(
    registry: "Registry",
    ref: str,
    property: str,
) -> Any:
    """Return the value of a single frontmatter property.

    Raises:
        NotFoundError: when *ref* cannot be resolved.
        ValidationError: when *property* is not present in the artifact's
            frontmatter.

    Spec: t0189
    """
    artifact = get(registry, ref)
    if property not in artifact.frontmatter:
        kd = registry.get(artifact.kind)
        known = sorted(artifact.frontmatter.keys())
        raise ValidationError(
            f"Unknown property {property!r} for kind {artifact.kind!r} — known: {known}"
        )
    return artifact.frontmatter[property]


def set_prop(
    registry: "Registry",
    ref: str,
    property: str,
    value: Any,
) -> Artifact:
    """Write a single frontmatter property through ``update``.

    Transition validation (s0033) and JSON Schema validation are applied
    on every write — there is no fast path that bypasses them.

    Spec: t0189
    """
    return update(registry, ref, fields={property: value})
