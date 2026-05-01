"""Tests for kind-aware --help in the create command (two-phase parsing)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from artifacts_os.cli import main
from artifacts_os.core import frontmatter as _fm


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RICH_KINDS = {
    "task": {
        "x-dir": "tasks",
        "x-prefix": "t",
        "x-numbered": True,
        "x-columns": ["id", "name", "status", "assignee"],
        "title": "Task",
        "type": "object",
        "properties": {
            "status": {
                "enum": ["backlog", "ready", "in-progress", "done"],
                "description": "Task lifecycle status",
            },
            "priority": {
                "type": "string",
                "description": "Priority level (low/normal/high/urgent)",
            },
        },
    },
    "note": {
        "x-dir": "notes",
        "x-prefix": "n",
        "x-numbered": True,
        "x-columns": ["id", "name", "type", "created"],
        "title": "Note",
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "description": "Note sub-type (planning, meeting, decision, scratch)",
            },
        },
    },
}


@pytest.fixture
def rich_vault(tmp_path: Path, monkeypatch):
    """Vault with x-columns in kind schemas so Variant A/B apply."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")

    for name, schema in _RICH_KINDS.items():
        (kinds_dir / f"{name}.json").write_text(json.dumps(schema))
        kind_dir = schema["x-dir"]
        (root / "artifacts" / kind_dir).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)
    return root


def _meta(vault: Path, stem: str, kind_dir: str) -> dict:
    path = vault / "artifacts" / kind_dir / f"{stem}.md"
    meta, _ = _fm.parse(path.read_text())
    return meta


# ---------------------------------------------------------------------------
# Variant A — filter: convenience flags shown/hidden based on x-columns
# ---------------------------------------------------------------------------

def test_task_help_shows_assignee(rich_vault, capsys):
    """task: --assignee shown because 'assignee' is in x-columns."""
    with pytest.raises(SystemExit) as exc:
        main(["create", "--kind", "task", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--assignee" in out


def test_note_help_hides_assignee(rich_vault, capsys):
    """note: --assignee hidden because 'assignee' is not in x-columns."""
    with pytest.raises(SystemExit) as exc:
        main(["create", "--kind", "note", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--assignee" not in out


def test_note_help_shows_type_flag(rich_vault, capsys):
    """note: --type shown because 'type' is in x-columns."""
    with pytest.raises(SystemExit) as exc:
        main(["create", "--kind", "note", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--type" in out


# ---------------------------------------------------------------------------
# Variant B — augment: kind-specific flags from schema properties
# ---------------------------------------------------------------------------

def test_task_help_shows_augmented_status(rich_vault, capsys):
    """task: --status added via Variant B (in properties but not convenience flag)."""
    with pytest.raises(SystemExit) as exc:
        main(["create", "--kind", "task", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--status" in out


def test_task_help_shows_augmented_priority(rich_vault, capsys):
    """task: --priority added via Variant B (schema property, no existing flag)."""
    with pytest.raises(SystemExit) as exc:
        main(["create", "--kind", "task", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--priority" in out


# ---------------------------------------------------------------------------
# Distinct help per kind
# ---------------------------------------------------------------------------

def test_task_and_note_help_are_distinct(rich_vault, capsys):
    """task and note help render meaningfully different flag lists."""
    with pytest.raises(SystemExit):
        main(["create", "--kind", "task", "--help"])
    task_out = capsys.readouterr().out

    with pytest.raises(SystemExit):
        main(["create", "--kind", "note", "--help"])
    note_out = capsys.readouterr().out

    assert task_out != note_out
    # task has --assignee; note does not
    assert "--assignee" in task_out
    assert "--assignee" not in note_out


# ---------------------------------------------------------------------------
# Default-kind handling (no --kind given)
# ---------------------------------------------------------------------------

def test_default_kind_help_uses_task_schema(rich_vault, capsys):
    """No --kind → falls back to 'task'; help shows task-specific flags."""
    with pytest.raises(SystemExit) as exc:
        main(["create", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    # Task-specific augmented flags should appear
    assert "--priority" in out or "--status" in out


# ---------------------------------------------------------------------------
# Unknown kind — error handling
# ---------------------------------------------------------------------------

def test_unknown_kind_exits_1(rich_vault, capsys):
    """Unknown --kind exits 1 with a clear error naming the bad kind."""
    with pytest.raises(SystemExit) as exc:
        main(["create", "Thing", "--kind", "unknownkind"])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "unknownkind" in err


def test_unknown_kind_help_shows_generic_parser(rich_vault, capsys):
    """Unknown --kind with --help shows generic help without error."""
    with pytest.raises(SystemExit) as exc:
        main(["create", "--kind", "unknownkind", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    # Generic help still shows universal flags
    assert "--fields" in out
    assert "--dry-run" in out


# ---------------------------------------------------------------------------
# Kind-specific flags actually set frontmatter (Variant B functional test)
# ---------------------------------------------------------------------------

def test_augmented_priority_flag_sets_frontmatter(rich_vault, capsys):
    """--priority flag (augmented) writes the field to frontmatter."""
    main(["create", "My task", "--kind", "task", "--priority", "high"])
    stem = capsys.readouterr().out.strip()
    meta = _meta(rich_vault, stem, "tasks")
    assert meta["priority"] == "high"


def test_augmented_status_flag_sets_frontmatter(rich_vault, capsys):
    """--status flag (augmented) writes the field to frontmatter."""
    main(["create", "My task", "--kind", "task", "--status", "ready"])
    stem = capsys.readouterr().out.strip()
    meta = _meta(rich_vault, stem, "tasks")
    assert meta["status"] == "ready"


# ---------------------------------------------------------------------------
# --fields escape hatch — backwards compatibility
# ---------------------------------------------------------------------------

def test_fields_hatch_for_augmented_field(rich_vault, capsys):
    """--fields KEY=VALUE works for fields that also have dedicated flags."""
    main(["create", "My task", "--kind", "task", "--fields", "priority=urgent"])
    stem = capsys.readouterr().out.strip()
    meta = _meta(rich_vault, stem, "tasks")
    assert meta["priority"] == "urgent"


def test_fields_hatch_for_filtered_convenience_flag(rich_vault, capsys):
    """--fields works for fields hidden by filter (owner not in note x-columns)."""
    main(["create", "My note", "--kind", "note", "--fields", "owner=alice"])
    stem = capsys.readouterr().out.strip()
    meta = _meta(rich_vault, stem, "notes")
    assert meta["owner"] == "alice"


def test_fields_hatch_overridable_by_dedicated_flag(rich_vault, capsys):
    """Dedicated flag (--priority) takes precedence over --fields for same key."""
    main([
        "create", "My task", "--kind", "task",
        "--priority", "high",
        "--fields", "priority=low",
    ])
    stem = capsys.readouterr().out.strip()
    meta = _meta(rich_vault, stem, "tasks")
    # Dedicated flag wins
    assert meta["priority"] == "high"
