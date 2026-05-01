"""artifacts-os cli module.

Exposes `artifacts-os` capabilities as a command-line tool. Parses
arguments, calls core + views, prints output.

Depends on `core` + `views`.

Spec: s2061-artifacts-os-module-system § cli
Implementation spec: s0003-artifacts-os-cli-module
"""

import sys
from typing import Sequence

from artifacts_os.core import (
    find_vault_root,
    load_settings,
    Registry,
    KindDef,
    NotFoundError,
    AmbiguousError,
    ValidationError,
)
from artifacts_os.cli.commands import list as _list_cmd
from artifacts_os.cli.commands import show as _show_cmd
from artifacts_os.cli.commands import create as _create_cmd
from artifacts_os.cli.commands import status as _status_cmd
from artifacts_os.cli.commands import verify as _verify_cmd
from artifacts_os.cli.commands import validate as _validate_cmd
from artifacts_os.cli.commands import init as _init_cmd
from artifacts_os.cli.commands import kinds as _kinds_cmd
from artifacts_os.cli.commands import ai as _ai_cmd
from artifacts_os.cli.settings import CliSettings


_registered_kinds: list[KindDef] = []


def _load_views_settings(root) -> "ViewsSettings | None":
    """Try to load ViewsSettings from the vault at *root*.

    Returns ``None`` on any error so callers can proceed without views config.
    Lazily imported so only the ``list`` command pays the import cost.
    """
    try:
        from pathlib import Path
        from artifacts_os.views.models import ViewsSettings
        settings_path = Path(root) / "artifacts" / "artifacts.yaml"
        base = load_settings(settings_path)
        return ViewsSettings.from_base(base)
    except Exception:
        return None


def _load_cli_settings(root) -> CliSettings | None:
    """Try to load CliSettings from the vault at *root*.

    Returns ``None`` on any error so callers can proceed without settings.
    """
    try:
        from pathlib import Path
        settings_path = Path(root) / "artifacts" / "artifacts.yaml"
        base = load_settings(settings_path)
        return CliSettings.from_base(base)
    except Exception:
        return None


def _apply_aliases(argv: list[str], aliases: dict[str, str]) -> list[str]:
    """Replace ``argv[0]`` with its mapped value if a matching alias exists."""
    if not argv:
        return argv
    mapped = aliases.get(argv[0])
    return [str(mapped)] + argv[1:] if mapped is not None else argv


def register_kinds(kinds: list[KindDef]) -> None:
    """Called by host app before main() dispatches.

    Stores kind definitions so the Registry is built with them at startup.
    Call before main() to inject application-specific KindDefs.

    Raises ``ValueError`` if any kind in *kinds* shares a name with an
    already-registered kind, or if *kinds* itself contains duplicate names.
    """
    # Check for duplicates within the incoming list.
    seen: set[str] = set()
    for kd in kinds:
        if kd.name in seen:
            raise ValueError(f"duplicate kind '{kd.name}' in register_kinds() input")
        seen.add(kd.name)
    # Check for conflicts with already-registered kinds.
    existing = {kd.name for kd in _registered_kinds}
    for kd in kinds:
        if kd.name in existing:
            raise ValueError(f"kind '{kd.name}' is already registered")
    _registered_kinds.extend(kinds)


def _peek_create_kind_schema(
    argv: list[str],
    cli_settings,
    root,
) -> tuple[str | None, dict | None]:
    """Phase 1: pre-parse to extract --kind and load its schema.

    Returns ``(kind, schema)`` when argv starts with ``"create"``, or
    ``(None, None)`` for any other command.  An unknown kind (no schema
    file) returns ``(kind, None)`` so Phase 2 falls back to static flags
    and the error surfaces cleanly in ``run()``.
    """
    if not argv or argv[0] != "create":
        return None, None

    import argparse
    import json
    from pathlib import Path

    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--kind", "-k", default=None)
    pre.add_argument("title", nargs="?", default=None)
    known, _ = pre.parse_known_args(argv[1:])

    kind: str | None = known.kind
    if kind is None and cli_settings is not None:
        create_defaults = cli_settings.defaults.get("create") or {}
        kind = create_defaults.get("kind")
    if kind is None:
        kind = "task"

    schema: dict | None = None
    if root is not None:
        schema_path = Path(root) / "artifacts" / "kinds" / f"{kind}.json"
        if schema_path.exists():
            try:
                with open(schema_path) as fh:
                    schema = json.load(fh)
            except Exception:
                schema = None

    return kind, schema


def _build_parser(
    create_kind: str | None = None,
    create_schema: dict | None = None,
):
    import argparse

    parser = argparse.ArgumentParser(
        prog="artifacts",
        description="artifacts-os command-line interface",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    _init_cmd.register(subparsers)
    _list_cmd.register(subparsers)
    _show_cmd.register(subparsers)
    _create_cmd.register(subparsers, kind=create_kind, schema=create_schema)
    _status_cmd.register(subparsers)
    _verify_cmd.register(subparsers)
    _validate_cmd.register(subparsers)
    _kinds_cmd.register(subparsers)
    _ai_cmd.register(subparsers)

    return parser


def _run(argv: Sequence[str]) -> int:
    argv = list(argv)

    # Find vault root early so aliases can be applied before argparse sees argv.
    # Aliases and defaults are silently ignored when no vault is found.
    root = find_vault_root()
    cli_settings = _load_cli_settings(root) if root is not None else None
    if cli_settings is not None:
        argv = _apply_aliases(argv, cli_settings.aliases)

    # Phase 1 — peek at create --kind to enable kind-aware help and flags.
    create_kind, create_schema = _peek_create_kind_schema(argv, cli_settings, root)

    parser = _build_parser(create_kind=create_kind, create_schema=create_schema)
    args = parser.parse_args(argv)
    args.cli_settings = cli_settings

    try:
        # Pre-registry commands (e.g. init) run before vault/registry setup.
        if getattr(args, "_pre_registry", False):
            return args.func(args) or 0

        if root is None:
            print("error: not in an artifacts-os project", file=sys.stderr)
            return 2

        registry = Registry(_registered_kinds, root=root)
        return args.func(args, registry) or 0
    except NotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except AmbiguousError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point for the `artifacts` console script."""
    code = _run(argv if argv is not None else sys.argv[1:])
    if code != 0:
        sys.exit(code)


__all__ = ["main", "register_kinds"]
