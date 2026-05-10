"""artifacts-os cli module.

Exposes `artifacts-os` capabilities as a command-line tool. Parses
arguments, calls core + views, prints output.

Depends on `core` + `views`.

Spec: s2061-artifacts-os-module-system § cli
Implementation spec: s0003-artifacts-os-cli-module
"""

import sys
from pathlib import Path
from typing import Sequence

from artifacts_os.core import (
    __version__,
    find_vault_root,
    load_settings,
    Registry,
    KindDef,
    NotFoundError,
    AmbiguousError,
    ValidationError,
)
from artifacts_os.core.errors import BlockedByPreHook
from artifacts_os.cli.commands import list as _list_cmd
from artifacts_os.cli.commands import show as _show_cmd
from artifacts_os.cli.commands import create as _create_cmd
from artifacts_os.cli.commands import status as _status_cmd
from artifacts_os.cli.commands import verify as _verify_cmd
from artifacts_os.cli.commands import validate as _validate_cmd
from artifacts_os.cli.commands import init as _init_cmd
from artifacts_os.cli.commands import kinds as _kinds_cmd
from artifacts_os.cli.commands import views as _views_cmd
from artifacts_os.cli.commands import ai as _ai_cmd
from artifacts_os.cli.commands import events as _events_cmd
from artifacts_os.cli.settings import CliSettings


_registered_kinds: list[KindDef] = []


def _load_views_settings(root) -> "ViewsSettings | None":
    """Try to load ViewsSettings from the vault at *root*.

    Returns ``None`` on YAML / IO errors so callers can proceed without views
    config.  ``ValueError`` (e.g. a view entry missing the required ``columns``
    field) is re-raised so the ``_run`` cascade maps it to exit 1.

    Lazily imported so only the ``list`` and ``views`` commands pay the import
    cost.
    """
    try:
        from pathlib import Path
        from artifacts_os.views.models import ViewsSettings
        settings_path = Path(root) / "artifacts.yaml"
        base = load_settings(settings_path)
        return ViewsSettings.from_base(base)
    except ValueError:
        raise
    except Exception:
        return None


def _load_cli_settings(root) -> CliSettings | None:
    """Try to load CliSettings from the vault at *root*.

    Returns ``None`` on any error so callers can proceed without settings.
    """
    try:
        from pathlib import Path
        settings_path = Path(root) / "artifacts.yaml"
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


def _peek_kind_for_command(
    argv: list[str],
    command: str,
    root,
    *,
    fallback_kind: str | None = None,
) -> tuple[str | None, dict | None]:
    """Phase 1: pre-parse argv for --kind and load the matching schema.

    Returns ``(kind, schema)``.  ``schema`` is ``None`` when:
    - ``argv[0] != command`` (caller skips Phase 2 build)
    - ``--kind`` is absent and no fallback applies (cross-kind mode)
    - the resolved kind has no vault schema (host-app kind)
    """
    if not argv or argv[0] != command:
        return None, None

    import argparse
    import json
    from pathlib import Path

    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--kind", "-k", default=None)
    known, _ = pre.parse_known_args(argv[1:])

    kind: str | None = known.kind or fallback_kind
    if kind is None:
        return None, None

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


def _peek_create_kind_schema(
    argv: list[str],
    cli_settings,
    root,
) -> tuple[str | None, dict | None]:
    """Phase 1 wrapper for the ``create`` command.

    Reads the default kind from ``cli_settings.defaults.create.kind``
    (falling back to ``"task"``) and delegates to
    ``_peek_kind_for_command``.
    """
    fallback = "task"
    if cli_settings is not None:
        create_defaults = cli_settings.defaults.get("create") or {}
        fallback = create_defaults.get("kind") or "task"
    return _peek_kind_for_command(argv, "create", root, fallback_kind=fallback)


def _peek_list_kind_schema(
    argv: list[str],
    root,
) -> tuple[str | None, dict | None]:
    """Phase 1 wrapper for the ``list`` command.

    No fallback kind — absent ``--kind`` means cross-kind mode.
    Returns ``(None, None)`` when ``--kind`` is not supplied so the caller
    loads all vault schemas for the union parser.
    """
    return _peek_kind_for_command(argv, "list", root, fallback_kind=None)


def _load_all_vault_schemas(root) -> dict[str, dict]:
    """Load all kind schemas from ``<root>/artifacts/kinds/*.json``.

    Returns a ``{kind_name: schema_dict}`` mapping.  Malformed JSON files
    are silently skipped (same policy as ``_peek_kind_for_command``).
    """
    import json
    from pathlib import Path

    result: dict[str, dict] = {}
    kinds_dir = Path(root) / "artifacts" / "kinds"
    if not kinds_dir.is_dir():
        return result
    for path in sorted(kinds_dir.glob("*.json")):
        try:
            with open(path) as fh:
                result[path.stem] = json.load(fh)
        except Exception:
            pass
    return result


def _build_parser(
    create_kind: str | None = None,
    create_schema: dict | None = None,
    list_kind: str | None = None,
    list_schema: dict | None = None,
    list_all_schemas: "dict[str, dict] | None" = None,
):
    import argparse

    parser = argparse.ArgumentParser(
        prog="artifacts",
        description="artifacts-os command-line interface",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"artifacts {__version__}",
        help="show program version and exit",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    _init_cmd.register(subparsers)
    _list_cmd.register(
        subparsers,
        kind=list_kind,
        schema=list_schema,
        all_schemas=list_all_schemas,
    )
    _show_cmd.register(subparsers)
    _create_cmd.register(subparsers, kind=create_kind, schema=create_schema)
    _status_cmd.register(subparsers)
    _verify_cmd.register(subparsers)
    _validate_cmd.register(subparsers)
    _kinds_cmd.register(subparsers)
    _views_cmd.register(subparsers)
    _ai_cmd.register(subparsers)
    _events_cmd.register(subparsers)

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

    # Phase 1 — peek at list --kind; load all schemas for cross-kind mode.
    list_kind, list_schema = _peek_list_kind_schema(argv, root)
    list_all_schemas: dict[str, dict] | None = None
    if argv and argv[0] == "list" and list_kind is None and root is not None:
        list_all_schemas = _load_all_vault_schemas(root)

    parser = _build_parser(
        create_kind=create_kind,
        create_schema=create_schema,
        list_kind=list_kind,
        list_schema=list_schema,
        list_all_schemas=list_all_schemas,
    )
    args = parser.parse_args(argv)
    args.cli_settings = cli_settings

    try:
        # Pre-registry commands (e.g. init) run before vault/registry setup.
        if getattr(args, "_pre_registry", False):
            return args.func(args) or 0

        if root is None:
            print(
                "error: not in an artifacts-os vault (no artifacts.yaml found"
                f" walking up from {Path.cwd()}).\n"
                "If your vault was created before v0.3.0, see the migration"
                " note: docs/migration.md",
                file=sys.stderr,
            )
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
    except BlockedByPreHook as exc:
        print(f"error: blocked by pre-hook: {exc}", file=sys.stderr)
        return 11
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point for the `artifacts` console script."""
    code = _run(argv if argv is not None else sys.argv[1:])
    if code != 0:
        sys.exit(code)


__all__ = ["main", "register_kinds"]
