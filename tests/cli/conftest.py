"""Shared fixtures for cli tests."""

import json
from pathlib import Path

import pytest


_TASK_STATUSES = ["backlog", "ready", "in-progress", "done"]
_KINDS = {
    "task": {
        "x-dir": "tasks",
        "x-prefix": "t",
        "x-numbered": True,
        "properties": {
            "status": {
                "enum": _TASK_STATUSES,
                "initial": "backlog",
                # Permissive transitions table — every status reachable from
                # every other status. Lets CLI tests focus on the rest of the
                # surface without fighting the state machine.
                "transitions": {s: _TASK_STATUSES for s in _TASK_STATUSES},
            },
            "assignee": {"type": "string"},
            "owner": {"type": "string"},
            "type": {"type": "string"},
            "priority": {"type": "string"},
            "parent": {"type": "string", "pattern": r"^\[\[.+\]\]$"},
            "subtasks": {
                "type": "array",
                "items": {"type": "string", "pattern": r"^\[\[.+\]\]$"},
            },
            "depends_on": {
                "type": "array",
                "items": {"type": "string", "pattern": r"^\[\[.+\]\]$"},
            },
            "artifacts": {
                "type": "array",
                "items": {"type": "string", "pattern": r"^\[\[.+\]\]$"},
            },
        },
    },
    "agent": {
        "x-dir": "agents",
        "x-prefix": "",
        "x-numbered": False,
        "properties": {},
    },
    "research": {
        "x-dir": "research",
        "x-prefix": "r",
        "x-numbered": True,
        "properties": {},
    },
    "spec": {
        "x-dir": "specs",
        "x-prefix": "s",
        "x-numbered": True,
        "properties": {
            "status": {"enum": ["draft", "accepted"]}
        },
    },
}


@pytest.fixture
def vault(tmp_path: Path, monkeypatch):
    """Create a minimal vault, chdir into it, clear registered kinds."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts.yaml").write_text("layout_version: 1\n")

    for name, schema in _KINDS.items():
        kind_folder = kinds_dir / name
        kind_folder.mkdir(parents=True, exist_ok=True)
        (kind_folder / "kind.json").write_text(json.dumps(schema))
        kind_dir = schema["x-dir"]
        (root / "artifacts" / kind_dir).mkdir(parents=True, exist_ok=True)

    # Reset globally registered kinds so tests are isolated
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)
    return root


def make_vault_with_marker(tmp_path: Path, marker: str = "artifacts.yaml") -> Path:
    """Materialise a minimal vault under *tmp_path* with a custom marker name.

    The vault has a single ``task`` kind registered and an empty artifacts
    directory, matching the layout expected by the CLI.

    Spec: s0034 §11.3.
    """
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / marker).write_text("layout_version: 1\nproject:\n  name: test\n")
    # Register the task kind so common CLI verbs work.
    task_schema = {
        "x-dir": "tasks",
        "x-prefix": "t",
        "x-numbered": True,
        "properties": {
            "status": {
                "enum": ["backlog", "done"],
                "initial": "backlog",
                "transitions": {"backlog": ["backlog", "done"], "done": ["backlog", "done"]},
            },
        },
    }
    task_dir = kinds_dir / "task"
    task_dir.mkdir(parents=True)
    (task_dir / "kind.json").write_text(json.dumps(task_schema))
    (root / "artifacts" / "tasks").mkdir(parents=True)
    return root


@pytest.fixture
def write_artifact():
    """Helper fixture: write a markdown artifact file to the vault."""
    from artifacts_os.core import frontmatter as _frontmatter

    def _write(root: Path, kind_dir: str, filename: str, fm: dict, body: str = "") -> Path:
        path = root / "artifacts" / kind_dir / filename
        path.write_text(_frontmatter.dump(fm, body))
        return path

    return _write
