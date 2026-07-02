"""Hook loader, matcher engine, and top-level emitter.

Parses ``hooks:`` from ``artifacts.yaml`` (legacy yaml-list form) and
reads bundle manifests from ``artifacts/hooks/.active/`` (bundle form).

The top-level ``notify(event, payload)`` function is registered with
``core.events.register_emitter`` when this module is imported (via
``hooks/__init__.py``).

All loaded hooks enter the fire-list regardless of ``host:`` value.
The ``host:`` field is tolerated (not validated) for one back-compat
release and will be dropped from the bundle schema thereafter (step 6
of s2073 migration).

Spec: s0025-artifact-events § C4; s0032-hooks-via-artbook §3, §6
"""
from __future__ import annotations

import fnmatch
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from artifacts_os.core.vault import find_vault_root
from artifacts_os.hooks.actions import BaseAction, from_config as action_from_config


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BundleError(Exception):
    """Raised when a hook bundle manifest cannot be safely loaded.

    Covers path-escape attempts, symlink resolution failures, and
    manifest parse failures that should block loading.
    """


# ---------------------------------------------------------------------------
# Valid matcher keys (unknown keys raise ValidationError at load time)
# ---------------------------------------------------------------------------

_VALID_MATCHER_KEYS: frozenset[str] = frozenset(
    [
        "event",
        "kind",
        "id",
        "name",
        "stem",
        "path",
        "changed",
        "result",
        "before",
        "after",
    ]
)

# Dynamic prefix keys (e.g. ``fields.assignee``, ``before.status``, ``after.status``)
_VALID_MATCHER_PREFIXES: tuple[str, ...] = ("fields.", "before.", "after.", "path.")


def _is_valid_matcher_key(key: str) -> bool:
    if key in _VALID_MATCHER_KEYS:
        return True
    return any(key.startswith(pfx) for pfx in _VALID_MATCHER_PREFIXES)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hook:
    """A parsed hook definition."""

    name: str
    matcher: dict[str, Any]
    action: BaseAction
    phase: str = "post"  # "pre" | "post"
    blocking: bool = False
    timeout: int = 30
    source: str = "yaml"  # "yaml" | "bundle"
    host: str = "artifacts-os"


# ---------------------------------------------------------------------------
# Loader helpers
# ---------------------------------------------------------------------------


def _parse_hook_entry(entry: dict, *, i: int, source: str = "yaml") -> Hook:
    """Parse a single hook dict into a Hook instance.

    Used by both yaml and bundle loaders — the only difference is the
    ``source`` label.
    """
    if not isinstance(entry, dict):
        raise ValueError(f"hooks[{i}] must be a mapping, got {type(entry)!r}")

    name: str = entry.get("name", "")
    if not name:
        raise ValueError(f"hooks[{i}] missing required 'name' field")

    matcher: dict[str, Any] = entry.get("matcher") or {}
    for key in matcher:
        if not _is_valid_matcher_key(key):
            raise ValueError(
                f"hook {name!r}: unknown matcher key {key!r}"
            )

    action_cfg: dict = entry.get("action") or {}
    if not action_cfg.get("type"):
        raise ValueError(f"hook {name!r}: missing action.type")
    action = action_from_config(action_cfg)

    phase: str = entry.get("phase", "post")
    if phase not in ("pre", "post"):
        raise ValueError(f"hook {name!r}: phase must be 'pre' or 'post'")

    blocking: bool = bool(entry.get("blocking", False))
    timeout: int = int(entry.get("timeout", 30))
    host: str = str(entry.get("host", "artifacts-os"))

    return Hook(
        name=name,
        matcher=matcher,
        action=action,
        phase=phase,
        blocking=blocking,
        timeout=timeout,
        source=source,
        host=host,
    )


# ---------------------------------------------------------------------------
# Legacy yaml-list loader
# ---------------------------------------------------------------------------

_legacy_deprecation_warned: bool = False


def load_hooks_from_yaml(root: Path) -> list[Hook]:
    """Parse the ``hooks:`` section from ``<root>/artifacts.yaml``.

    Returns an empty list when the section is absent or empty.
    Raises ``ValueError`` for malformed entries (missing name, missing
    action type, unknown matcher keys).

    Yaml-list hooks are implicitly treated as ``host: artifacts-os``.
    """
    import yaml

    settings_path = root / "artifacts.yaml"
    if not settings_path.exists():
        return []

    raw: dict = yaml.safe_load(settings_path.read_text()) or {}
    hooks_data = raw.get("hooks") or []
    if not hooks_data:
        return []

    # Emit legacy deprecation notice once per process.
    global _legacy_deprecation_warned
    if not _legacy_deprecation_warned:
        quiet = os.environ.get("ARTIFACTS_HOOKS_LEGACY_QUIET", "")
        if not quiet or quiet == "0":
            sys.stderr.write(
                "deprecation: hooks defined in artifacts.yaml are deprecated. "
                "Migrate to hook bundles (artifacts/hooks/<slug>/) and use "
                "'artifacts hooks promote <slug>'. "
                "Set ARTIFACTS_HOOKS_LEGACY_QUIET=1 to suppress this warning.\n"
            )
        _legacy_deprecation_warned = True

    hooks: list[Hook] = []
    for i, entry in enumerate(hooks_data):
        hooks.append(_parse_hook_entry(entry, i=i, source="yaml"))

    return hooks


# ---------------------------------------------------------------------------
# Bundle loader: reads .active/ symlinks / JSON stubs
# ---------------------------------------------------------------------------


def _read_frontmatter(path: Path) -> dict[str, Any]:
    """Read only the YAML frontmatter block from *path*.

    Returns an empty dict when the file has no ``---`` delimiters.
    """
    import yaml

    lines: list[str] = []
    with path.open("r", encoding="utf-8") as fh:
        first = fh.readline()
        if first.strip() != "---":
            return {}
        for line in fh:
            if line.rstrip("\n") == "---":
                break
            lines.append(line)
    return yaml.safe_load("".join(lines)) or {}


def _resolve_active_entry(
    entry: Path,
    hooks_dir: Path,
) -> tuple[str, Path | None, str | None]:
    """Resolve a single ``.active/<slug>`` entry.

    Returns ``(slug, manifest_path, error_reason)`` where:
    - ``manifest_path`` is not None on success.
    - ``error_reason`` is one of ``"missing-target"``, ``"escape-attempt"``
      on failure.
    """
    slug = entry.name
    if slug.startswith("."):
        return slug, None, "missing-target"

    # Resolve the entry (symlink or .json stub).
    if entry.suffix == ".json":
        # Stub form: {"target": "../<slug>/…"}
        try:
            import json
            data = json.loads(entry.read_text(encoding="utf-8"))
            rel_target = data.get("target", "")
        except Exception:
            return slug, None, "parse-error"
        manifest_path = (entry.parent / rel_target).resolve()
    elif entry.is_symlink():
        try:
            manifest_path = entry.resolve()
        except OSError:
            return slug, None, "missing-target"
        if not manifest_path.exists():
            return slug, None, "missing-target"
    else:
        # Might be a regular file in test fixtures — just use it directly
        manifest_path = entry.resolve()
        if not manifest_path.exists():
            return slug, None, "missing-target"

    # Security: manifest must live inside artifacts/hooks/ (no path escape).
    hooks_real = hooks_dir.resolve()
    try:
        manifest_path.relative_to(hooks_real)
    except ValueError:
        return slug, None, "escape-attempt"

    return slug, manifest_path, None


def _resolve_action_path(action_cfg: dict, bundle_dir: Path) -> dict:
    """Return a copy of *action_cfg* with relative ``command`` resolved
    against *bundle_dir*.

    Absolute paths and non-shell actions pass through unchanged.
    """
    if action_cfg.get("type") != "shell":
        return action_cfg
    cmd = action_cfg.get("command", "")
    if not cmd:
        return action_cfg
    # Only resolve paths that look like filesystem paths (contain / or are
    # simple names without spaces). Skip plain commands like "echo", "true".
    # A relative path is anything that doesn't start with / and contains /
    # OR starts with ./ or ../ OR is a single filename that exists in bundle_dir.
    is_relative = (
        not os.path.isabs(cmd)
        and (
            "/" in cmd
            or cmd.startswith("./")
            or cmd.startswith("../")
            or (bundle_dir / cmd).exists()
        )
    )
    if not is_relative:
        return action_cfg
    resolved = str((bundle_dir / cmd).resolve())
    return {**action_cfg, "command": resolved}


def load_hooks_from_active(root: Path) -> list[Hook]:
    """Load hooks from ``<root>/artifacts/hooks/.active/``.

    Reads each entry (symlink or ``.json`` stub), validates that the
    resolved manifest lives inside ``artifacts/hooks/``, parses frontmatter,
    and returns in-memory ``Hook`` records with ``source="bundle"``.

    Skipped entries emit ``hook.skipped`` events; they do not raise.
    Returns hooks sorted by slug.
    """
    from artifacts_os.core import events as _core_events

    hooks_dir = root / "artifacts" / "hooks"
    active_dir = hooks_dir / ".active"
    if not active_dir.exists():
        return []

    hooks: list[Hook] = []

    entries = sorted(active_dir.iterdir())
    for entry in entries:
        if entry.name.startswith("."):
            continue

        # Strip .json suffix for slug if it's a stub file
        slug = entry.stem if entry.suffix == ".json" else entry.name

        slug_resolved, manifest_path, error_reason = _resolve_active_entry(
            entry, hooks_dir
        )
        if error_reason is not None:
            _core_events._dispatch(
                "hook.skipped",
                hook=slug_resolved,
                reason=error_reason,
                path=str(entry),
            )
            continue

        # Parse manifest frontmatter.
        try:
            fm = _read_frontmatter(manifest_path)
        except Exception as exc:
            _core_events._dispatch(
                "hook.skipped",
                hook=slug_resolved,
                reason="parse-error",
                path=str(manifest_path),
            )
            continue

        if not fm:
            _core_events._dispatch(
                "hook.skipped",
                hook=slug_resolved,
                reason="parse-error",
                path=str(manifest_path),
            )
            continue

        # Resolve relative action.command against the bundle directory.
        bundle_dir = manifest_path.parent
        action_cfg = dict(fm.get("action") or {})
        if action_cfg:
            action_cfg = _resolve_action_path(action_cfg, bundle_dir)
            fm = {**fm, "action": action_cfg}

        try:
            hook = _parse_hook_entry(fm, i=0, source="bundle")
        except (ValueError, Exception) as exc:
            _core_events._dispatch(
                "hook.skipped",
                hook=slug_resolved,
                reason="parse-error",
                path=str(manifest_path),
            )
            continue

        hooks.append(hook)

    return hooks


# ---------------------------------------------------------------------------
# Merged loader
# ---------------------------------------------------------------------------


def load_hooks(root: Path) -> list[Hook]:
    """Load all hooks for *root*: yaml entries first, then bundle entries.

    - Yaml entries are loaded via ``load_hooks_from_yaml`` (implicit
      ``host: artifacts-os``).
    - Bundle entries are loaded via ``load_hooks_from_active`` (respect
      their declared ``host:``).
    - Bundle entries are sorted by slug within their group.
    - Returns yaml entries first, then bundle entries (sorted by slug).

    Raises ``ValueError`` for malformed yaml hook entries.
    """
    yaml_hooks = load_hooks_from_yaml(root)
    bundle_hooks = load_hooks_from_active(root)
    return yaml_hooks + bundle_hooks


# ---------------------------------------------------------------------------
# Fire-list: all loaded hooks are fireable (host: field is ignored)
# ---------------------------------------------------------------------------


def _fire_list(hooks: list[Hook]) -> list[Hook]:
    """Return all *hooks* for firing (host: field is tolerated but ignored).

    Prior to s2073 the foreign-host allowlist excluded bundles with
    host: values not in a reserved set.  That coupling was removed:
    the hook engine names no consumer; all bundles fire regardless of
    their host: tag.
    """
    return list(hooks)


# ---------------------------------------------------------------------------
# Matcher engine
# ---------------------------------------------------------------------------


def _match_value(expected: Any, actual: Any) -> bool:
    """Return True if *actual* satisfies the *expected* matcher value.

    - A list in *expected* means OR (any element matches).
    - The string ``"*"`` on the ``event`` key is handled by the caller.
    """
    if isinstance(expected, list):
        return any(_match_value(e, actual) for e in expected)
    if isinstance(expected, str) and isinstance(actual, str):
        return fnmatch.fnmatch(actual, expected)
    return expected == actual


def match(hooks: list[Hook], event: str, payload: dict, *, phase: str) -> list[Hook]:
    """Return the subset of *hooks* that match *event* + *payload* for *phase*.

    Matching rules:
    - ``phase`` must equal the hook's phase.
    - All matcher keys must match (AND across keys).
    - A list value uses OR within the key.
    - ``event: "*"`` matches any event type.
    - ``fields.<key>``, ``before.<key>``, ``after.<key>``,
      ``path.*`` matchers do nested lookup.
    """
    matched: list[Hook] = []
    for hook in hooks:
        if hook.phase != phase:
            continue
        if not _hook_matches(hook, event, payload):
            continue
        matched.append(hook)
    return matched


def _hook_matches(hook: Hook, event: str, payload: dict) -> bool:
    """Evaluate all matcher keys for one hook."""
    m = hook.matcher

    # event key
    evt_pattern = m.get("event", "*")
    if evt_pattern != "*" and not _match_value(evt_pattern, event):
        return False

    # Simple top-level keys
    for key in ("kind", "id", "name", "stem", "result", "before", "after", "changed"):
        if key not in m:
            continue
        actual = payload.get(key)
        if key == "changed":
            # changed: list-contains — check if any of expected values is in changed
            expected = m[key]
            if not isinstance(expected, list):
                expected = [expected]
            actual_list = actual or []
            if not any(e in actual_list for e in expected):
                return False
        else:
            if not _match_value(m[key], actual):
                return False

    # Path glob: path.* or path key
    if "path" in m:
        actual_path = payload.get("path", "")
        if not _match_value(m["path"], actual_path):
            return False

    # Nested keys: fields.<key>, before.<key>, after.<key>
    for full_key, expected in m.items():
        if "." not in full_key:
            continue
        # Skip path.* which is matched above as-is
        prefix, _, sub_key = full_key.partition(".")
        if prefix not in ("fields", "before", "after", "path"):
            continue
        if prefix == "path":
            # path.<something> glob on the path value
            actual_path = payload.get("path", "")
            if not fnmatch.fnmatch(actual_path, f"*{sub_key}*"):
                return False
            continue
        container = payload.get(prefix) or {}
        if not isinstance(container, dict):
            return False
        actual = container.get(sub_key)
        # Handle empty string comparison (e.g. fields.assignee: "")
        if not _match_value(expected, actual if actual is not None else ""):
            return False

    return True


# ---------------------------------------------------------------------------
# Action runner
# ---------------------------------------------------------------------------

_ART_VARS = (
    "ART_EVENT",
    "ART_KIND",
    "ART_ID",
    "ART_NAME",
    "ART_STEM",
    "ART_PATH",
    "ART_VAULT_ROOT",
    "ART_BEFORE_STATUS",
    "ART_AFTER_STATUS",
    "ART_CHANGED",
    "ART_PAYLOAD_JSON",
    "ART_TS",
)


def _build_env(event: str, payload: dict, *, root: Path | None = None) -> dict[str, str]:
    """Build the ``ART_``-prefixed environment for hook actions."""
    from datetime import datetime, timezone

    ts = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    env: dict[str, str] = {
        "ART_EVENT": event,
        "ART_KIND": str(payload.get("kind", "")),
        "ART_ID": str(payload.get("id", "")),
        "ART_NAME": str(payload.get("name", "")),
        "ART_STEM": str(payload.get("stem", "")),
        "ART_PATH": str(payload.get("path", "")),
        "ART_VAULT_ROOT": str(root) if root else "",
        "ART_TS": ts,
    }
    # Status helpers
    before = payload.get("before", "")
    after = payload.get("after", "")
    if isinstance(before, str):
        env["ART_BEFORE_STATUS"] = before
    elif isinstance(before, dict):
        env["ART_BEFORE_STATUS"] = str(before.get("status", ""))
    if isinstance(after, str):
        env["ART_AFTER_STATUS"] = after
    elif isinstance(after, dict):
        env["ART_AFTER_STATUS"] = str(after.get("status", ""))

    # Changed keys
    changed = payload.get("changed", [])
    env["ART_CHANGED"] = ",".join(str(c) for c in changed) if changed else ""

    # Full payload JSON
    import json
    try:
        env["ART_PAYLOAD_JSON"] = json.dumps({"event": event, **payload}, ensure_ascii=False)
    except Exception:
        env["ART_PAYLOAD_JSON"] = "{}"

    return env


def run_matched(
    matched: list[Hook],
    event: str,
    payload: dict,
    *,
    root: Path | None = None,
) -> None:
    """Run each matched hook action.

    - Successes emit ``hook.fired`` via ``core.events._dispatch``.
    - Failures emit ``hook.failed`` and raise ``BlockedByPreHook`` when
      the hook has ``blocking=true`` and ``phase=pre``; otherwise a
      warning is printed to stderr.
    - ``hook.fired`` and ``hook.failed`` payloads carry an optional
      ``source:`` key (``"yaml"`` | ``"bundle"``).
    """
    from artifacts_os.core import events as _core_events
    from artifacts_os.core.errors import BlockedByPreHook

    env = _build_env(event, payload, root=root)

    for hook in matched:
        start_ms = int(time.monotonic() * 1000)
        action_dict = hook.action.to_dict()
        matcher_dict = dict(hook.matcher)

        try:
            hook.action.run(payload, env)
            duration_ms = int(time.monotonic() * 1000) - start_ms
            _core_events._dispatch(
                "hook.fired",
                hook=hook.name,
                matcher=matcher_dict,
                action=action_dict,
                duration_ms=duration_ms,
                phase=hook.phase,
                source=hook.source,
            )
        except Exception as exc:
            duration_ms = int(time.monotonic() * 1000) - start_ms
            _core_events._dispatch(
                "hook.failed",
                hook=hook.name,
                matcher=matcher_dict,
                action=action_dict,
                phase=hook.phase,
                blocking=hook.blocking,
                error=str(exc),
                duration_ms=duration_ms,
                source=hook.source,
            )
            if hook.phase == "pre" and hook.blocking:
                raise BlockedByPreHook(
                    f"pre-hook {hook.name!r} blocked operation: {exc}"
                ) from exc
            else:
                sys.stderr.write(
                    f"warning: hook {hook.name!r} failed ({hook.phase}): {exc}\n"
                )


# ---------------------------------------------------------------------------
# Top-level emitter registered with core.events
# ---------------------------------------------------------------------------

_hooks_cache: list[Hook] | None = None
_hooks_root: Path | None = None
_notify_active: bool = False  # reentrancy guard


def notify(event: str, payload: dict) -> None:
    """Top-level emitter — registered with ``core.events.register_emitter``.

    Loads hooks from the vault root on first call (cached).  Matches the
    event and phase, then dispatches to the action runners.  Only hooks
    that pass the host dispatch filter (``_fire_list``) are executed.
    """
    global _hooks_cache, _hooks_root, _notify_active

    # Reentrancy guard: hook.fired / hook.failed are dispatched from inside
    # run_matched; if notify is already on the call stack, skip to prevent
    # infinite recursion when catch-all hooks match meta-events.
    if _notify_active:
        return
    _notify_active = True
    try:
        _notify_inner(event, payload)
    finally:
        _notify_active = False


def _notify_inner(event: str, payload: dict) -> None:
    """Implementation of notify; called with reentrancy guard active."""
    global _hooks_cache, _hooks_root

    # Resolve root
    root = find_vault_root()
    if root is None:
        return

    # (Re)load hooks if root changed or not yet loaded
    if _hooks_cache is None or _hooks_root != root:
        try:
            _hooks_cache = load_hooks(root)
            _hooks_root = root
        except Exception as e:
            sys.stderr.write(f"warning: hooks load failed: {e!r}\n")
            _hooks_cache = []

    hooks = _hooks_cache
    if not hooks:
        return

    # Apply host dispatch: only fire hooks targeting artifacts-os.
    fireable = _fire_list(hooks)
    if not fireable:
        return

    # Determine phase from event context:
    # Pre-phase events come from _dispatch_pre calls; they carry a
    # ``_phase`` sentinel that we inject via the emitter contract.
    # Hooks registered for "post" run during post-phase dispatches.
    # We use the payload ``_phase`` key if present (internal use),
    # falling back to "post" for all regular ``_dispatch`` calls.
    phase = payload.pop("_phase", "post")

    pre_hooks = match(fireable, event, payload, phase="pre")
    post_hooks = match(fireable, event, payload, phase="post")

    if phase == "pre":
        run_matched(pre_hooks, event, payload, root=root)
    else:
        run_matched(post_hooks, event, payload, root=root)


def invalidate_cache() -> None:
    """Force hooks to be re-read from disk on next ``notify()`` call.

    Useful in tests to reset state between cases.
    """
    global _hooks_cache, _hooks_root, _legacy_deprecation_warned
    _hooks_cache = None
    _hooks_root = None
    _legacy_deprecation_warned = False
