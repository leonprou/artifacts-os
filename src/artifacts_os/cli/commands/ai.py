"""cli ai command — manage AI command integrations."""

from __future__ import annotations

import sys
from pathlib import Path


def register(subparsers) -> None:
    p = subparsers.add_parser("ai", help="manage AI slash-command integrations")
    p.set_defaults(func=_dispatch)

    sub = p.add_subparsers(dest="ai_command", metavar="AI_COMMAND")
    sub.required = True

    # --- install ---
    pi = sub.add_parser(
        "install",
        help="install AI commands into a vault's .claude/ directory",
    )
    pi.add_argument(
        "--target",
        metavar="DIR",
        default=None,
        help="vault root (default: auto-detect from cwd)",
    )
    mode_grp = pi.add_mutually_exclusive_group()
    mode_grp.add_argument(
        "--copy",
        dest="mode",
        action="store_const",
        const="copy",
        help="copy command files (default: symlink)",
    )
    mode_grp.add_argument(
        "--link",
        dest="mode",
        action="store_const",
        const="link",
        help="symlink command files (default)",
    )
    pi.add_argument(
        "--tool",
        choices=["claude", "opencode"],
        default=None,
        help="target tool (default: auto-detect)",
    )
    pi.add_argument("--force", action="store_true", help="overwrite modified files")
    pi.add_argument("--dry-run", action="store_true", help="preview without writing")
    pi.set_defaults(func=_run_install)

    # --- uninstall ---
    pu = sub.add_parser(
        "uninstall",
        help="remove AI commands from a vault's .claude/ directory",
    )
    pu.add_argument(
        "--target",
        metavar="DIR",
        default=None,
        help="vault root (default: auto-detect from cwd)",
    )
    pu.add_argument(
        "--tool",
        default="claude",
        help="target tool (default: claude)",
    )
    pu.add_argument("--dry-run", action="store_true", help="preview without removing")
    pu.set_defaults(func=_run_uninstall)

    # --- list ---
    pl = sub.add_parser(
        "list",
        help="list installed AI commands in a vault",
    )
    pl.add_argument(
        "--target",
        metavar="DIR",
        default=None,
        help="vault root (default: auto-detect from cwd)",
    )
    pl.add_argument(
        "--tool",
        default="claude",
        help="target tool (default: claude)",
    )
    pl.set_defaults(func=_run_list)


def _dispatch(args, registry=None) -> int:
    """Fallback if no sub-command is parsed (should not normally be reached)."""
    print("error: expected ai subcommand: install, uninstall, list", file=sys.stderr)
    return 1


def _resolve_target(args, registry=None) -> Path | None:
    """Resolve the vault root from --target or registry."""
    if getattr(args, "target", None):
        return Path(args.target).resolve()
    if registry is not None and registry.root is not None:
        return registry.root
    # Last resort: find_vault_root from cwd
    from artifacts_os.core import find_vault_root
    root = find_vault_root()
    return root


def _run_install(args, registry=None) -> int:
    from artifacts_os.ai import install as ai_install, InstallReport

    target = _resolve_target(args, registry)
    if target is None:
        print("error: not in an artifacts-os vault. Run `artifacts init` first.", file=sys.stderr)
        return 2

    mode = getattr(args, "mode", None) or "link"
    dry_run = args.dry_run

    try:
        report: InstallReport = ai_install(
            target,
            mode=mode,
            tool=getattr(args, "tool", None),
            force=args.force,
            dry_run=dry_run,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    prefix = "[dry-run] " if dry_run else ""
    if report.refused:
        for a in report.actions:
            if a.action == "refuse":
                print(f"error: {a.target}: {a.reason}", file=sys.stderr)
        return 1

    for a in report.actions:
        if a.action in ("install-link", "replace-link"):
            print(f"{prefix}link  {a.target} -> {a.source}")
        elif a.action == "install-copy":
            print(f"{prefix}copy  {a.target}")
        elif a.action == "skip":
            print(f"{prefix}skip  {a.target}  ({a.reason})")

    summary = f"{prefix}installed {report.installed}, skipped {report.skipped}"
    if report.refused:
        summary += f", refused {report.refused}"
    print(summary)
    return 0


def _run_uninstall(args, registry=None) -> int:
    from artifacts_os.ai import uninstall as ai_uninstall

    target = _resolve_target(args, registry)
    if target is None:
        print("error: not in an artifacts-os vault.", file=sys.stderr)
        return 2

    dry_run = args.dry_run

    try:
        report = ai_uninstall(
            target,
            tool=args.tool,
            dry_run=dry_run,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    prefix = "[dry-run] " if dry_run else ""
    for a in report.actions:
        if a.action == "remove":
            print(f"{prefix}remove  {a.target}")

    print(f"{prefix}removed {report.removed}")
    return 0


def _run_list(args, registry=None) -> int:
    from artifacts_os.ai import list_installed

    target = _resolve_target(args, registry)
    if target is None:
        print("error: not in an artifacts-os vault.", file=sys.stderr)
        return 2

    assets = list_installed(target, tool=args.tool)

    if not assets:
        print("(no artifacts-os commands installed)")
        return 0

    for asset in assets:
        print(f"{asset.path}  [{asset.mode}]  <- {asset.source}")
    return 0
