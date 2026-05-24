"""Hook promotion and demotion mechanics.

Promotes a hook bundle to ``.active/`` by creating a relative symlink
(or a ``.json`` stub when symlinks are unavailable).  Demotes by unlinking.

Spec: s0032-hooks-via-artbook §4
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


class PromoteResult(NamedTuple):
    """Outcome of a promote operation."""

    slug: str
    active_path: Path        # path to the created symlink or stub
    target: str              # relative target string used
    was_stub: bool           # True when a .json stub was written instead of a symlink
    was_idempotent: bool     # True when the entry already existed with the same target


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _hooks_dir(root: Path) -> Path:
    return root / "artifacts" / "hooks"


def _active_dir(root: Path) -> Path:
    return _hooks_dir(root) / ".active"


def _bundle_dir(root: Path, slug: str) -> Path:
    return _hooks_dir(root) / slug


def _manifest_name(slug: str) -> str:
    """Manifest file name for *slug* per kind.json ``x-manifest-name``."""
    return f"{slug}.md"


def _relative_target(slug: str) -> str:
    """Relative target for the ``.active/<slug>`` → ``../<slug>/<slug>.md`` link."""
    return f"../{slug}/{_manifest_name(slug)}"


def find_bundle(root: Path, slug: str) -> Path | None:
    """Return the bundle directory path if it exists, else None."""
    bundle = _bundle_dir(root, slug)
    if bundle.is_dir():
        return bundle
    return None


def promote(
    root: Path,
    slug: str,
    *,
    force: bool = False,
) -> PromoteResult:
    """Promote *slug* hook bundle to ``.active/``.

    Semantics (§4.2):
    - Resolves the bundle at ``artifacts/hooks/<slug>/``; raises
      ``FileNotFoundError`` when absent.
    - Creates ``artifacts/hooks/.active/<slug>`` → ``../<slug>/<slug>.md``.
    - Idempotent: if the symlink (or stub) already points to the same target,
      returns a result with ``was_idempotent=True``.
    - Divergent target → raises ``FileExistsError`` unless *force* is True.
    - On OSError (no symlink support) writes a ``.json`` stub instead.
    - Emits ``hook.promoted`` event.

    Raises:
        FileNotFoundError: bundle directory or manifest does not exist.
        FileExistsError: active entry has a divergent target and force is False.
    """
    from artifacts_os.core import events as _core_events

    bundle = find_bundle(root, slug)
    if bundle is None:
        raise FileNotFoundError(
            f"hook bundle {slug!r} not found at {_bundle_dir(root, slug)}"
        )

    manifest = bundle / _manifest_name(slug)
    if not manifest.exists():
        raise FileNotFoundError(
            f"hook bundle manifest {manifest} does not exist"
        )

    active = _active_dir(root)
    active.mkdir(parents=True, exist_ok=True)

    rel_target = _relative_target(slug)
    link_path = active / slug
    stub_path = active / f"{slug}.json"

    # Check if already promoted (symlink or stub).
    for existing_path, is_stub in [(link_path, False), (stub_path, True)]:
        if existing_path.exists() or existing_path.is_symlink():
            if is_stub:
                try:
                    existing_target = json.loads(
                        existing_path.read_text(encoding="utf-8")
                    ).get("target", "")
                except Exception:
                    existing_target = ""
            else:
                try:
                    existing_target = os.readlink(existing_path)
                except OSError:
                    existing_target = ""

            if existing_target == rel_target:
                # Idempotent — same target.
                return PromoteResult(
                    slug=slug,
                    active_path=existing_path,
                    target=rel_target,
                    was_stub=is_stub,
                    was_idempotent=True,
                )
            else:
                # Divergent target.
                if not force:
                    raise FileExistsError(
                        f"divergent target: .active/{slug} already points to "
                        f"{existing_target!r}; expected {rel_target!r}. "
                        "Use --force to overwrite."
                    )
                # Force: remove and recreate.
                existing_path.unlink()
                break

    # Create the symlink.
    was_stub = False
    try:
        os.symlink(rel_target, link_path)
        result_path = link_path
    except OSError:
        # Symlink not supported (e.g. Windows without privilege) — write stub.
        stub_path.write_text(
            json.dumps({"target": rel_target}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        result_path = stub_path
        was_stub = True

    _core_events._dispatch("hook.promoted", hook=slug, target=rel_target)

    return PromoteResult(
        slug=slug,
        active_path=result_path,
        target=rel_target,
        was_stub=was_stub,
        was_idempotent=False,
    )


def demote(root: Path, slug: str) -> bool:
    """Demote *slug* from ``.active/``.

    Removes ``<active>/<slug>`` (symlink) or ``<active>/<slug>.json`` (stub)
    if present.  No-op if neither exists.

    Returns True when something was removed, False when already absent.
    Emits ``hook.demoted`` event when something is removed.

    Args:
        root: vault root path.
        slug: hook bundle slug.
    """
    from artifacts_os.core import events as _core_events

    active = _active_dir(root)
    link_path = active / slug
    stub_path = active / f"{slug}.json"

    removed = False
    for path in (link_path, stub_path):
        if path.exists() or path.is_symlink():
            path.unlink()
            removed = True
            break  # only one form should exist at a time

    if removed:
        _core_events._dispatch("hook.demoted", hook=slug, reason="")

    return removed


def demote_prune(root: Path, *, dry_run: bool = False) -> list[str]:
    """Remove all dangling ``.active/`` entries.

    A dangling entry is one whose resolved target does not exist.
    Emits ``hook.demoted`` with ``reason: "prune"`` for each removed entry.

    Returns the list of slugs that were (or would be) removed.
    """
    from artifacts_os.core import events as _core_events

    active = _active_dir(root)
    if not active.exists():
        return []

    pruned: list[str] = []
    for entry in sorted(active.iterdir()):
        if entry.name.startswith("."):
            continue

        slug = entry.stem if entry.suffix == ".json" else entry.name
        is_stub = entry.suffix == ".json"
        is_symlink = entry.is_symlink()

        dangling = False
        if is_symlink:
            resolved = (active / entry).resolve() if False else None
            try:
                target = entry.resolve()
                dangling = not target.exists()
            except OSError:
                dangling = True
        elif is_stub:
            try:
                data = json.loads(entry.read_text(encoding="utf-8"))
                rel_target = data.get("target", "")
                target_path = (active / rel_target).resolve()
                dangling = not target_path.exists()
            except Exception:
                dangling = True
        else:
            # Regular file or non-existent — check if it exists
            dangling = not entry.exists()

        if dangling:
            pruned.append(slug)
            if not dry_run:
                try:
                    entry.unlink()
                except OSError:
                    pass
                _core_events._dispatch("hook.demoted", hook=slug, reason="prune")

    return pruned


def active_state(root: Path, slug: str) -> str:
    """Return ``"yes"``, ``"dangling"``, or ``"no"`` for *slug*.

    - ``"yes"`` — ``.active/<slug>`` (or stub) exists and resolves.
    - ``"dangling"`` — entry exists but target is missing.
    - ``"no"`` — no ``.active/`` entry.
    """
    active = _active_dir(root)
    link_path = active / slug
    stub_path = active / f"{slug}.json"

    for path, is_stub in [(link_path, False), (stub_path, True)]:
        if path.exists() or path.is_symlink():
            if is_stub:
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    rel_target = data.get("target", "")
                    target_path = (active / rel_target).resolve()
                    return "yes" if target_path.exists() else "dangling"
                except Exception:
                    return "dangling"
            else:
                # Symlink or regular file
                try:
                    target = path.resolve()
                    return "yes" if target.exists() else "dangling"
                except OSError:
                    return "dangling"

    return "no"


def list_bundles(root: Path) -> list[str]:
    """Return slugs of all hook bundles in ``artifacts/hooks/``.

    Skips ``.active/`` and dotfiles.
    """
    hooks_dir = _hooks_dir(root)
    if not hooks_dir.exists():
        return []

    slugs: list[str] = []
    for entry in sorted(hooks_dir.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            # Only include directories that have a manifest.
            manifest = entry / _manifest_name(entry.name)
            if manifest.exists():
                slugs.append(entry.name)

    return slugs
