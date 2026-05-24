"""cli hooks command — manage hook bundles.

Usage::

    artifacts hooks list [--host HOST] [--active | --inactive]
                         [--source yaml|bundle] [--tail [N]] [-j]
                         [--prune [--dry-run]]
    artifacts hooks show <slug> [-j]
    artifacts hooks promote <slug> [--force] [-j]
    artifacts hooks demote <slug> [-j]

All verbs: default Rich table output; ``-j`` switches to JSON/JSONL.
Exit codes: 0 success, 1 user error, 2 config error, 3 filesystem error.

Spec: s0032-hooks-via-artbook §7
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------


def register(subparsers) -> None:
    """Register the ``hooks`` sub-command group."""
    p = subparsers.add_parser("hooks", help="manage hook bundles")
    sub = p.add_subparsers(dest="hooks_verb", metavar="VERB")
    sub.required = True

    # --- list ---
    p_list = sub.add_parser("list", help="list hook bundles")
    p_list.add_argument("--host", default=None, help="filter by host")
    exclusive = p_list.add_mutually_exclusive_group()
    exclusive.add_argument(
        "--active", action="store_true", default=False, help="show only active hooks"
    )
    exclusive.add_argument(
        "--inactive",
        action="store_true",
        default=False,
        help="show only inactive hooks",
    )
    p_list.add_argument(
        "--source",
        choices=["yaml", "bundle"],
        default=None,
        help="filter by source (yaml | bundle)",
    )
    p_list.add_argument(
        "--tail",
        nargs="?",
        const=50,
        default=None,
        type=int,
        metavar="N",
        help="show only last N results (default: 50)",
    )
    p_list.add_argument(
        "-j",
        "--json",
        action="store_true",
        dest="json_out",
        default=False,
        help="JSON output",
    )
    p_list.add_argument(
        "--prune",
        action="store_true",
        default=False,
        help="remove dangling .active/ entries",
    )
    p_list.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        dest="dry_run",
        help="with --prune: show what would be removed without removing it",
    )
    p_list.set_defaults(func=_run_list)

    # --- show ---
    p_show = sub.add_parser("show", help="show hook bundle details")
    p_show.add_argument("slug", help="hook bundle slug")
    p_show.add_argument(
        "-j",
        "--json",
        action="store_true",
        dest="json_out",
        default=False,
        help="JSON output",
    )
    p_show.set_defaults(func=_run_show)

    # --- promote ---
    p_promote = sub.add_parser("promote", help="activate a hook bundle")
    p_promote.add_argument("slug", help="hook bundle slug")
    p_promote.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="overwrite a divergent .active/ entry",
    )
    p_promote.add_argument(
        "-j",
        "--json",
        action="store_true",
        dest="json_out",
        default=False,
        help="JSON output",
    )
    p_promote.set_defaults(func=_run_promote)

    # --- demote ---
    p_demote = sub.add_parser("demote", help="deactivate a hook bundle")
    p_demote.add_argument("slug", help="hook bundle slug")
    p_demote.add_argument(
        "-j",
        "--json",
        action="store_true",
        dest="json_out",
        default=False,
        help="JSON output",
    )
    p_demote.set_defaults(func=_run_demote)

    p.set_defaults(func=_dispatch_hooks)


def _dispatch_hooks(args, registry) -> int:
    """Fallback: called when no verb is given (shouldn't happen with required=True)."""
    print("error: specify a hooks verb: list, show, promote, demote", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _root_from_registry(registry) -> Path | None:
    return registry.root if registry is not None else None


def _get_root(registry) -> Path | None:
    root = _root_from_registry(registry)
    return root


def _read_frontmatter(path: Path) -> dict[str, Any]:
    """Read only the YAML frontmatter block from *path*."""
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


def _bundle_manifest(root: Path, slug: str) -> Path:
    """Return the manifest path for *slug*."""
    return root / "artifacts" / "hooks" / slug / f"{slug}.md"


def _list_all_hooks(root: Path) -> list[dict[str, Any]]:
    """Return one dict per hook (yaml + bundle), each with metadata for display.

    Each dict contains:
      name, host, active, phase, event (matcher.event), source, frontmatter
    """
    from artifacts_os.hooks.loader import (
        load_hooks_from_yaml,
        load_hooks_from_active,
    )
    from artifacts_os.hooks.promotion import active_state

    rows: list[dict[str, Any]] = []

    # Yaml hooks (from artifacts.yaml).
    try:
        yaml_hooks = load_hooks_from_yaml(root)
    except Exception:
        yaml_hooks = []
    for hook in yaml_hooks:
        rows.append(
            {
                "name": hook.name,
                "host": hook.host,
                "active": "yes",  # yaml hooks are always implicitly active
                "phase": hook.phase,
                "event": hook.matcher.get("event", "*"),
                "source": "yaml",
                "frontmatter": {
                    "name": hook.name,
                    "host": hook.host,
                    "phase": hook.phase,
                    "blocking": hook.blocking,
                    "timeout": hook.timeout,
                    "source": "yaml",
                    "matcher": hook.matcher,
                },
            }
        )

    # Bundle hooks (from .active/).
    from artifacts_os.hooks.promotion import list_bundles, _hooks_dir

    hooks_dir = _hooks_dir(root)
    for slug in list_bundles(root):
        manifest = _bundle_manifest(root, slug)
        try:
            fm = _read_frontmatter(manifest)
        except Exception:
            fm = {"name": slug}

        state = active_state(root, slug)
        rows.append(
            {
                "name": slug,
                "host": fm.get("host", "artifacts-os"),
                "active": state,
                "phase": fm.get("phase", "post"),
                "event": (fm.get("matcher") or {}).get("event", "*"),
                "source": "bundle",
                "frontmatter": {**fm, "source": "bundle", "active": state},
            }
        )

    return rows


# ---------------------------------------------------------------------------
# list verb
# ---------------------------------------------------------------------------


def _run_list(args, registry) -> int:
    root = _get_root(registry)
    if root is None:
        print("error: vault root not found", file=sys.stderr)
        return 2

    # --prune: remove dangling entries.
    if args.prune:
        from artifacts_os.hooks.promotion import demote_prune

        pruned = demote_prune(root, dry_run=args.dry_run)
        if args.json_out:
            print(json.dumps({"pruned": pruned, "dry_run": args.dry_run}, ensure_ascii=False))
        else:
            for slug in pruned:
                verb = "would remove" if args.dry_run else "removed"
                print(f"{verb}: .active/{slug}")
        return 0

    rows = _list_all_hooks(root)

    # Apply filters.
    if args.host:
        rows = [r for r in rows if r["host"] == args.host]
    if args.active:
        rows = [r for r in rows if r["active"] == "yes"]
    if args.inactive:
        rows = [r for r in rows if r["active"] != "yes"]
    if args.source:
        rows = [r for r in rows if r["source"] == args.source]

    # Apply --tail.
    tail: int | None = getattr(args, "tail", None)
    if tail is not None:
        rows = rows[-tail:] if tail > 0 else []

    if args.json_out:
        print(json.dumps([r["frontmatter"] for r in rows], ensure_ascii=False))
        return 0

    # Rich table.
    table = Table()
    table.add_column("name")
    table.add_column("host")
    table.add_column("active")
    table.add_column("phase")
    table.add_column("event")
    table.add_column("source")
    for row in rows:
        active_val = row["active"]
        style = ""
        if active_val == "dangling":
            style = "yellow"
        elif active_val == "no":
            style = "dim"
        table.add_row(
            row["name"],
            row["host"],
            active_val,
            row["phase"],
            str(row["event"]),
            row["source"],
            style=style,
        )
    Console().print(table)
    return 0


# ---------------------------------------------------------------------------
# show verb
# ---------------------------------------------------------------------------


def _sibling_files(bundle_dir: Path) -> list[dict[str, Any]]:
    """Return metadata for sibling files in *bundle_dir* (excluding manifest)."""
    items: list[dict[str, Any]] = []
    if not bundle_dir.is_dir():
        return items

    slug = bundle_dir.name

    for entry in sorted(bundle_dir.rglob("*")):
        if not entry.is_file():
            continue
        if entry.name == f"{slug}.md":
            continue  # skip the manifest itself
        rel = entry.relative_to(bundle_dir)
        is_exec = os.access(entry, os.X_OK)
        size = entry.stat().st_size
        items.append(
            {
                "path": str(rel),
                "executable": is_exec,
                "size": size,
            }
        )
    return items


def _recent_events(root: Path, slug: str, n: int = 5) -> list[dict]:
    """Return the last *n* hook.fired / hook.failed events for *slug*."""
    events_dir = root / "artifacts" / "logs" / "events"
    if not events_dir.is_dir():
        return []

    records: list[dict] = []
    for path in sorted(events_dir.glob("*.jsonl")):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event_type = rec.get("event", "")
                if event_type in ("hook.fired", "hook.failed"):
                    if rec.get("hook") == slug:
                        records.append(rec)
        except Exception:
            pass

    return records[-n:]


def _run_show(args, registry) -> int:
    root = _get_root(registry)
    if root is None:
        print("error: vault root not found", file=sys.stderr)
        return 2

    slug = args.slug
    from artifacts_os.hooks.promotion import active_state, find_bundle

    # Check if bundle exists.
    bundle_dir = root / "artifacts" / "hooks" / slug
    manifest = _bundle_manifest(root, slug)

    if not bundle_dir.is_dir() and not manifest.exists():
        print(f"error: hook bundle {slug!r} not found", file=sys.stderr)
        return 1

    # Read frontmatter.
    try:
        fm = _read_frontmatter(manifest)
    except FileNotFoundError:
        fm = {}
    except Exception as exc:
        print(f"error: failed to read manifest: {exc}", file=sys.stderr)
        return 2

    state = active_state(root, slug)
    siblings = _sibling_files(bundle_dir)
    recent = _recent_events(root, slug)

    if args.json_out:
        out = {
            "frontmatter": fm,
            "active": state,
            "siblings": siblings,
            "recent_events": recent,
        }
        print(json.dumps(out, ensure_ascii=False))
        return 0

    console = Console()

    # Frontmatter table.
    fm_table = Table(title=f"Hook: {slug}", show_header=True)
    fm_table.add_column("field")
    fm_table.add_column("value")
    for k, v in fm.items():
        fm_table.add_row(str(k), str(v))
    fm_table.add_row("active", state)
    console.print(fm_table)

    # Sibling files.
    if siblings:
        sib_table = Table(title="Sibling files")
        sib_table.add_column("path")
        sib_table.add_column("+x")
        sib_table.add_column("size")
        for sib in siblings:
            sib_table.add_row(
                sib["path"],
                "yes" if sib["executable"] else "no",
                str(sib["size"]),
            )
        console.print(sib_table)

    # Recent events.
    if recent:
        ev_table = Table(title="Recent events (last 5)")
        ev_table.add_column("ts")
        ev_table.add_column("event")
        ev_table.add_column("phase")
        ev_table.add_column("duration_ms")
        for rec in recent:
            ev_table.add_row(
                str(rec.get("ts", "")),
                str(rec.get("event", "")),
                str(rec.get("phase", "")),
                str(rec.get("duration_ms", "")),
            )
        console.print(ev_table)

    return 0


# ---------------------------------------------------------------------------
# promote verb
# ---------------------------------------------------------------------------


def _run_promote(args, registry) -> int:
    root = _get_root(registry)
    if root is None:
        print("error: vault root not found", file=sys.stderr)
        return 2

    slug = args.slug
    from artifacts_os.hooks.promotion import promote, find_bundle

    if find_bundle(root, slug) is None:
        print(f"error: hook bundle {slug!r} not found", file=sys.stderr)
        return 1

    try:
        result = promote(root, slug, force=args.force)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except PermissionError as exc:
        print(f"error: filesystem permission denied: {exc}", file=sys.stderr)
        return 3
    except OSError as exc:
        print(f"error: filesystem error: {exc}", file=sys.stderr)
        return 3

    if args.json_out:
        print(
            json.dumps(
                {
                    "slug": result.slug,
                    "active_path": str(result.active_path),
                    "target": result.target,
                    "was_stub": result.was_stub,
                    "was_idempotent": result.was_idempotent,
                },
                ensure_ascii=False,
            )
        )
    else:
        if result.was_idempotent:
            print(f"already active: {slug}")
        else:
            kind = "stub" if result.was_stub else "symlink"
            print(f"promoted: {slug} ({kind})")

    return 0


# ---------------------------------------------------------------------------
# demote verb
# ---------------------------------------------------------------------------


def _run_demote(args, registry) -> int:
    root = _get_root(registry)
    if root is None:
        print("error: vault root not found", file=sys.stderr)
        return 2

    slug = args.slug
    from artifacts_os.hooks.promotion import demote

    try:
        removed = demote(root, slug)
    except PermissionError as exc:
        print(f"error: filesystem permission denied: {exc}", file=sys.stderr)
        return 3
    except OSError as exc:
        print(f"error: filesystem error: {exc}", file=sys.stderr)
        return 3

    if args.json_out:
        print(json.dumps({"slug": slug, "removed": removed}, ensure_ascii=False))
    else:
        if removed:
            print(f"demoted: {slug}")
        else:
            print(f"not active: {slug}")

    return 0
