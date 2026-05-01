"""Shared fixtures for cli tests."""

import json
from pathlib import Path

import pytest


_KINDS = {
    "task": {
        "x-dir": "tasks",
        "x-prefix": "t",
        "x-numbered": True,
        "properties": {
            "status": {"enum": ["backlog", "ready", "in-progress", "done"]},
            "assignee": {"type": "string"},
            "owner": {"type": "string"},
            "type": {"type": "string"},
            "priority": {"type": "string"},
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
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")

    for name, schema in _KINDS.items():
        (kinds_dir / f"{name}.json").write_text(json.dumps(schema))
        kind_dir = schema["x-dir"]
        (root / "artifacts" / kind_dir).mkdir(parents=True, exist_ok=True)

    # Reset globally registered kinds so tests are isolated
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)
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
