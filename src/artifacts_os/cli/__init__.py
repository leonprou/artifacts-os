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


_registered_kinds: list[KindDef] = []


def register_kinds(kinds: list[KindDef]) -> None:
    """Called by host app before main() dispatches.

    Stores kind definitions so the Registry is built with them at startup.
    Call before main() to inject application-specific KindDefs.
    """
    _registered_kinds.extend(kinds)


def _build_parser():
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
    _create_cmd.register(subparsers)
    _status_cmd.register(subparsers)
    _verify_cmd.register(subparsers)
    _validate_cmd.register(subparsers)

    return parser


def _run(argv: Sequence[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv))

    try:
        # Pre-registry commands (e.g. init) run before vault/registry setup.
        if getattr(args, "_pre_registry", False):
            return args.func(args) or 0

        root = find_vault_root()
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
