"""cli init command — bootstrap a new artifacts-os project."""

import json
import os
import sys
from pathlib import Path


_DEFAULT_KINDS: dict[str, dict] = {
    "task": {
        "x-dir": "tasks",
        "x-prefix": "t",
        "x-numbered": True,
        "x-columns": ["id", "name", "status", "assignee"],
        "x-status-colors": {
            "backlog": "dim",
            "ready": "cyan",
            "in-progress": "yellow",
            "review": "blue",
            "done": "green",
            "cancelled": "dim strike",
        },
        "title": "Task",
        "type": "object",
        "properties": {
            "status": {
                "enum": [
                    "backlog",
                    "ready",
                    "in-progress",
                    "review",
                    "done",
                    "cancelled",
                ]
            }
        },
    },
    "spec": {
        "x-dir": "specs",
        "x-prefix": "s",
        "x-numbered": True,
        "x-columns": ["id", "name", "status"],
        "x-status-colors": {
            "draft": "yellow",
            "review": "blue",
            "approved": "green",
            "deprecated": "dim",
        },
        "title": "Spec",
        "type": "object",
        "properties": {
            "status": {"enum": ["draft", "review", "approved", "deprecated"]}
        },
    },
    "agent": {
        "x-dir": "agents",
        "x-prefix": "",
        "x-numbered": False,
        "x-columns": ["name", "description"],
        "title": "Agent",
        "type": "object",
        "properties": {"status": {"enum": ["active", "inactive"]}},
    },
    "research": {
        "x-dir": "research",
        "x-prefix": "",
        "x-numbered": False,
        "x-columns": ["name", "created:date", "status"],
        "title": "Research",
        "type": "object",
        "properties": {"status": {"enum": ["draft", "done"]}},
    },
}


def _default_settings(name: str, alias: str) -> str:
    return f"""\
layout_version: 1

project:
  name: "{name}"
  alias: "{alias}"

defaults:
  show:
    editor: true
"""


def register(subparsers) -> None:
    p = subparsers.add_parser("init", help="initialise a new artifacts-os project")
    p.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="target directory (default: current directory)",
    )
    p.add_argument("--name", default=None, help="project name (default: directory name)")
    p.add_argument("--alias", default=None, help="short alias for tmux/display (default: name)")
    p.set_defaults(func=run, _pre_registry=True)


def run(args) -> int:  # no registry — called before vault setup
    target = Path(args.directory).resolve()

    # Refuse if already initialised
    if (target / ".openstation").is_dir():
        print(f"error: already initialised at {target}", file=sys.stderr)
        return 2

    name = args.name or target.name
    alias = args.alias or name[:16]  # keep alias short

    # --- .openstation/ ---
    openstation_dir = target / ".openstation"
    openstation_dir.mkdir(parents=True, exist_ok=False)
    (openstation_dir / "openstation.yaml").write_text(
        _default_settings(name, alias), encoding="utf-8"
    )

    # --- artifacts/ with kind subdirs and types ---
    artifacts_dir = target / "artifacts"
    types_dir = artifacts_dir / "types"
    types_dir.mkdir(parents=True, exist_ok=True)

    for kind_name, schema in _DEFAULT_KINDS.items():
        # type definition
        (types_dir / f"{kind_name}.json").write_text(
            json.dumps(schema, indent=2) + "\n", encoding="utf-8"
        )
        # storage directory
        kind_dir = artifacts_dir / schema["x-dir"]
        kind_dir.mkdir(parents=True, exist_ok=True)

    # --- openstation -> artifacts symlink (compat) ---
    symlink = target / "openstation"
    if not symlink.exists() and not symlink.is_symlink():
        os.symlink("artifacts", symlink)

    print(f"Initialised artifacts-os project: {target}")
    print(f"  .openstation/openstation.yaml")
    print(f"  artifacts/types/  ({len(_DEFAULT_KINDS)} kinds)")
    for schema in _DEFAULT_KINDS.values():
        print(f"  artifacts/{schema['x-dir']}/")
    print(f"  openstation -> artifacts")
    return 0
