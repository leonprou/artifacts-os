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
        "x-prefix": "r",
        "x-numbered": True,
        "x-columns": ["id", "name", "created:date", "status"],
        "title": "Research",
        "type": "object",
        "properties": {"status": {"enum": ["draft", "done"]}},
    },
}


def _default_settings(name: str, created: str) -> str:
    return f"""\
layout_version: 1

project:
  name: "{name}"
  created: "{created}"
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
    p.add_argument("--no-ai", action="store_true", help="skip AI command installation")
    p.set_defaults(func=run, _pre_registry=True)


def run(args) -> int:  # no registry — called before vault setup
    import datetime

    target = Path(args.directory).resolve()

    # Refuse if already initialised
    if (target / "artifacts" / "artifacts.yaml").is_file():
        print(f"error: already initialised at {target}", file=sys.stderr)
        return 2

    name = args.name or target.name
    created = datetime.date.today().isoformat()

    # --- artifacts/ with kind subdirs, kind schemas, and vault marker ---
    artifacts_dir = target / "artifacts"
    kinds_dir = artifacts_dir / "kinds"
    kinds_dir.mkdir(parents=True, exist_ok=True)

    (artifacts_dir / "artifacts.yaml").write_text(
        _default_settings(name, created), encoding="utf-8"
    )

    for kind_name, schema in _DEFAULT_KINDS.items():
        # kind schema definition
        (kinds_dir / f"{kind_name}.json").write_text(
            json.dumps(schema, indent=2) + "\n", encoding="utf-8"
        )
        # storage directory
        kind_dir = artifacts_dir / schema["x-dir"]
        kind_dir.mkdir(parents=True, exist_ok=True)

    # --- openstation -> artifacts symlink (compat for external openstation CLI) ---
    symlink = target / "openstation"
    if not symlink.exists() and not symlink.is_symlink():
        os.symlink("artifacts", symlink)

    print(f"Initialised artifacts-os project: {target}")
    print(f"  artifacts/artifacts.yaml")
    print(f"  artifacts/kinds/  ({len(_DEFAULT_KINDS)} kinds)")
    for schema in _DEFAULT_KINDS.values():
        print(f"  artifacts/{schema['x-dir']}/")
    print(f"  openstation -> artifacts")

    # Install AI commands (unless opted out)
    if not getattr(args, "no_ai", False):
        try:
            from artifacts_os.ai import install as ai_install
            ai_install(target, mode="link", dry_run=False)
        except Exception:
            pass  # best-effort; don't fail init if AI install fails

    return 0
