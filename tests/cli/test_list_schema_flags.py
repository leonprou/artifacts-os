"""Tests for schema-derived filter flags on the ``list`` command (s0015).

Test IDs track the matrix in s0015 §10.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from artifacts_os.cli import main
from artifacts_os.core import frontmatter as _fm


# ---------------------------------------------------------------------------
# Vault fixture with rich schemas
# ---------------------------------------------------------------------------

_TASK_SCHEMA = {
    "x-dir": "tasks",
    "x-prefix": "t",
    "x-numbered": True,
    "x-columns": ["id", "name", "status", "assignee"],
    "title": "Task",
    "type": "object",
    "properties": {
        "status": {
            "enum": ["backlog", "ready", "in-progress", "review", "done", "rejected"],
            "description": "Task lifecycle stage.",
        },
        "priority": {
            "enum": ["low", "normal", "high", "urgent"],
            "description": "Priority hint.",
        },
        "assignee": {
            "type": "string",
            "description": "Assigned agent or person.",
        },
        "owner": {
            "type": "string",
            "description": "Owning agent or person.",
        },
        "type": {
            "enum": ["feature", "implementation", "spec", "documentation"],
            "description": "Task category.",
        },
    },
}

_SPEC_SCHEMA = {
    "x-dir": "specs",
    "x-prefix": "s",
    "x-numbered": True,
    "title": "Spec",
    "type": "object",
    "properties": {
        "status": {
            "enum": ["draft", "review", "approved"],
            "description": "Spec lifecycle.",
        },
        "agent": {
            "type": "string",
            "description": "Author agent.",
        },
    },
}

_AGENT_SCHEMA = {
    "x-dir": "agents",
    "x-prefix": "",
    "x-numbered": False,
    "title": "Agent",
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "description": "Agent category.",
        },
    },
}

_ALL_SCHEMAS = {"task": _TASK_SCHEMA, "spec": _SPEC_SCHEMA, "agent": _AGENT_SCHEMA}


def _write_artifact(root: Path, kind_dir: str, filename: str, fm: dict, body: str = "") -> Path:
    path = root / "artifacts" / kind_dir / filename
    path.write_text(_fm.dump(fm, body))
    return path


@pytest.fixture
def vault(tmp_path: Path, monkeypatch):
    """Vault with task + spec + agent schemas."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")

    for name, schema in _ALL_SCHEMAS.items():
        (kinds_dir / f"{name}.json").write_text(json.dumps(schema))
        kind_dir = schema["x-dir"]
        (root / "artifacts" / kind_dir).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)
    return root


# ---------------------------------------------------------------------------
# L1 — per-kind --help shows all filterable axes
# ---------------------------------------------------------------------------

def test_L1_per_kind_help_lists_generated_flags(vault, capsys):
    """L1: --kind task --help lists every filterable axis from task schema."""
    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--status" in out
    assert "--priority" in out
    assert "--assignee" in out
    assert "--owner" in out
    assert "--type" in out


def test_L1_per_kind_help_shows_enum_choices(vault, capsys):
    """L1: task --help shows enum choices for --status."""
    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    # choices metavar includes some status values
    assert "ready" in out
    assert "backlog" in out


# ---------------------------------------------------------------------------
# L2 — per-kind --status filter works
# ---------------------------------------------------------------------------

def test_L2_status_filter_per_kind(vault):
    """L2: --kind task --status ready filters by status."""
    _write_artifact(vault, "tasks", "t0001-alpha.md",
                    {"id": "t0001", "kind": "task", "name": "alpha", "status": "ready"})
    _write_artifact(vault, "tasks", "t0002-beta.md",
                    {"id": "t0002", "kind": "task", "name": "beta", "status": "backlog"})
    out = _quiet_output(["list", "--kind", "task", "--status", "ready"])
    assert "t0001-alpha" in out
    assert "t0002-beta" not in out


# ---------------------------------------------------------------------------
# L3 — schema-derived --type filter works
# ---------------------------------------------------------------------------

def test_L3_type_filter_per_kind(vault):
    """L3: --kind task --type feature filters by type field."""
    _write_artifact(vault, "tasks", "t0001-feat.md",
                    {"id": "t0001", "kind": "task", "name": "feat", "status": "ready",
                     "type": "feature"})
    _write_artifact(vault, "tasks", "t0002-spec.md",
                    {"id": "t0002", "kind": "task", "name": "spec", "status": "ready",
                     "type": "spec"})
    out = _quiet_output(["list", "--kind", "task", "--type", "feature"])
    assert "t0001-feat" in out
    assert "t0002-spec" not in out


# ---------------------------------------------------------------------------
# L4 — enum mismatch exits 2 with argparse error
# ---------------------------------------------------------------------------

def test_L4_invalid_enum_value_exits_2(vault, capsys):
    """L4: --kind task --status bogus produces a parse-time error (exit 2)."""
    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "--status", "bogus"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "invalid choice" in err or "bogus" in err


# ---------------------------------------------------------------------------
# L5 — multiple generated flags compose
# ---------------------------------------------------------------------------

def test_L5_multiple_generated_flags(vault):
    """L5: --priority urgent --assignee alice both apply."""
    _write_artifact(vault, "tasks", "t0001-match.md",
                    {"id": "t0001", "kind": "task", "name": "match",
                     "status": "ready", "priority": "urgent", "assignee": "alice"})
    _write_artifact(vault, "tasks", "t0002-wrong-priority.md",
                    {"id": "t0002", "kind": "task", "name": "wrong-priority",
                     "status": "ready", "priority": "low", "assignee": "alice"})
    _write_artifact(vault, "tasks", "t0003-wrong-assignee.md",
                    {"id": "t0003", "kind": "task", "name": "wrong-assignee",
                     "status": "ready", "priority": "urgent", "assignee": "bob"})
    out = _quiet_output(
        ["list", "--kind", "task", "--priority", "urgent", "--assignee", "alice"]
    )
    assert "t0001-match" in out
    assert "t0002-wrong-priority" not in out
    assert "t0003-wrong-assignee" not in out


# ---------------------------------------------------------------------------
# L6 — schema with no properties: static surface only, no crash
# ---------------------------------------------------------------------------

def test_L6_no_properties_schema_static_fallback(tmp_path, monkeypatch, capsys):
    """L6: schema with no properties emits only static flags; no crash."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    (root / "artifacts" / "tasks").mkdir(parents=True)
    # Schema with empty properties
    (kinds_dir / "task.json").write_text(json.dumps({
        "x-dir": "tasks", "x-prefix": "t", "x-numbered": True,
        "type": "object", "properties": {},
    }))
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "--help"])
    assert exc.value.code == 0
    # Static --status still shown via fallback
    out = capsys.readouterr().out
    assert "--status" in out


def test_L6_no_properties_help_no_crash(tmp_path, monkeypatch, capsys):
    """L6 variant: kind with no properties renders --help without crashing."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    (root / "artifacts" / "tasks").mkdir(parents=True)
    (kinds_dir / "task.json").write_text(json.dumps({
        "x-dir": "tasks", "x-prefix": "t", "x-numbered": True,
        "type": "object", "properties": {},
    }))
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    # Static --status is added as fallback when schema has no status property
    assert "--status" in out


# ---------------------------------------------------------------------------
# L7 — reserved flag name collision is silently skipped
# ---------------------------------------------------------------------------

def test_L7_reserved_name_skipped(tmp_path, monkeypatch, capsys):
    """L7: schema property 'children' collides with static flag — skipped."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    (root / "artifacts" / "tasks").mkdir(parents=True)
    schema = {
        "x-dir": "tasks", "x-prefix": "t", "x-numbered": True,
        "type": "object",
        "properties": {
            "children": {"type": "string", "description": "Collides with static flag."},
            "status": {"enum": ["backlog", "ready"], "description": "Status."},
        },
    }
    (kinds_dir / "task.json").write_text(json.dumps(schema))
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    # Argparse would have raised an error if --children were registered twice.
    # Exit 0 proves the collision was silently skipped; --children appears
    # from the static registration (usage line + options section = 2 is fine).
    assert "--children" in out
    assert "--status" in out  # schema-derived status is shown


# ---------------------------------------------------------------------------
# L8 — cross-kind mode: --status shown without choices=
# ---------------------------------------------------------------------------

def test_L8_cross_kind_help_status_no_choices(vault, capsys):
    """L8: no --kind → --status has no per-kind choices in --help."""
    with pytest.raises(SystemExit) as exc:
        main(["list", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--status" in out
    # No choices listed (both task and spec have different status enums)
    # The flag should appear but without the '|' separated enum in metavar
    assert "backlog" not in out or "draft" not in out  # not both enums shown


# ---------------------------------------------------------------------------
# L9 — cross-kind --status filter applied
# ---------------------------------------------------------------------------

def test_L9_cross_kind_status_filter(vault):
    """L9: --status review (no --kind) does a cross-kind walk."""
    _write_artifact(vault, "tasks", "t0001-a.md",
                    {"id": "t0001", "kind": "task", "name": "a", "status": "review"})
    _write_artifact(vault, "tasks", "t0002-b.md",
                    {"id": "t0002", "kind": "task", "name": "b", "status": "ready"})
    _write_artifact(vault, "specs", "s0001-spec-x.md",
                    {"id": "s0001", "kind": "spec", "name": "spec-x", "status": "review"})
    out = _quiet_output(["list", "--status", "review"])
    assert "t0001-a" in out
    assert "s0001-spec-x" in out
    assert "t0002-b" not in out


# ---------------------------------------------------------------------------
# L10 — cross-kind: invalid enum accepted at parse time (silent-no-match)
# ---------------------------------------------------------------------------

def test_L10_cross_kind_invalid_status_accepted(vault):
    """L10: --status superseded (no kind) accepted at parse time, returns []."""
    _write_artifact(vault, "tasks", "t0001-a.md",
                    {"id": "t0001", "kind": "task", "name": "a", "status": "ready"})
    # Should not raise SystemExit(2); returns empty (silent-no-match)
    out = _quiet_output(["list", "--status", "superseded"])
    assert out.strip() == ""


# ---------------------------------------------------------------------------
# L11 — cross-kind --type filter
# ---------------------------------------------------------------------------

def test_L11_cross_kind_type_filter(vault):
    """L11: --type feature (no --kind) filters across all kinds."""
    _write_artifact(vault, "tasks", "t0001-feat.md",
                    {"id": "t0001", "kind": "task", "name": "feat",
                     "status": "ready", "type": "feature"})
    _write_artifact(vault, "tasks", "t0002-impl.md",
                    {"id": "t0002", "kind": "task", "name": "impl",
                     "status": "ready", "type": "implementation"})
    out = _quiet_output(["list", "--type", "feature"])
    assert "t0001-feat" in out
    assert "t0002-impl" not in out


# ---------------------------------------------------------------------------
# L12 — cross-kind union includes all property names from all schemas
# ---------------------------------------------------------------------------

def test_L12_cross_kind_union_flags(vault, capsys):
    """L12: union mode includes flags from task, spec, and agent schemas."""
    with pytest.raises(SystemExit) as exc:
        main(["list", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    # task-only: --priority, --assignee, --owner, --type
    assert "--priority" in out
    assert "--assignee" in out
    assert "--owner" in out
    # spec-only: --agent
    assert "--agent" in out


# ---------------------------------------------------------------------------
# L13 — --filter wins over generated flag (s0014 precedence)
# ---------------------------------------------------------------------------

def test_L13_filter_wins_over_generated_flag(vault):
    """L13: --type feature --filter type=spec → type=spec wins."""
    _write_artifact(vault, "tasks", "t0001-spec.md",
                    {"id": "t0001", "kind": "task", "name": "spec-task",
                     "status": "ready", "type": "spec"})
    _write_artifact(vault, "tasks", "t0002-feat.md",
                    {"id": "t0002", "kind": "task", "name": "feat-task",
                     "status": "ready", "type": "feature"})
    out = _quiet_output(
        ["list", "--kind", "task", "--type", "feature", "--filter", "type=spec"]
    )
    assert "t0001-spec" in out
    assert "t0002-feat" not in out


# ---------------------------------------------------------------------------
# L14 — view's filter overridden by generated flag
# ---------------------------------------------------------------------------

def test_L14_generated_flag_overrides_view_filter(vault):
    """L14: view declares assignee=developer; --assignee alice overrides it."""
    # Add a view to artifacts.yaml
    yaml_path = vault / "artifacts" / "artifacts.yaml"
    yaml_path.write_text(
        "layout_version: 1\n"
        "project:\n"
        "  name: test\n"
        "views:\n"
        "  dev-queue:\n"
        "    columns: id,name,status\n"
        "    filters:\n"
        "      kind: task\n"
        "      assignee: developer\n"
    )
    _write_artifact(vault, "tasks", "t0001-alice.md",
                    {"id": "t0001", "kind": "task", "name": "alice-task",
                     "status": "ready", "assignee": "alice"})
    _write_artifact(vault, "tasks", "t0002-dev.md",
                    {"id": "t0002", "kind": "task", "name": "dev-task",
                     "status": "ready", "assignee": "developer"})
    out = _quiet_output(["list", "--view", "dev-queue", "--assignee", "alice"])
    assert "t0001-alice" in out
    assert "t0002-dev" not in out


# ---------------------------------------------------------------------------
# L15 — view filter preserved for keys not overridden
# ---------------------------------------------------------------------------

def test_L15_view_filter_preserved_for_non_overridden_keys(vault):
    """L15: view assignee=developer kept; --type feature adds a new key."""
    yaml_path = vault / "artifacts" / "artifacts.yaml"
    yaml_path.write_text(
        "layout_version: 1\n"
        "project:\n"
        "  name: test\n"
        "views:\n"
        "  dev-queue:\n"
        "    columns: id,name,status\n"
        "    filters:\n"
        "      kind: task\n"
        "      assignee: developer\n"
    )
    _write_artifact(vault, "tasks", "t0001-match.md",
                    {"id": "t0001", "kind": "task", "name": "match",
                     "status": "ready", "assignee": "developer", "type": "feature"})
    _write_artifact(vault, "tasks", "t0002-wrong-type.md",
                    {"id": "t0002", "kind": "task", "name": "wrong-type",
                     "status": "ready", "assignee": "developer", "type": "spec"})
    _write_artifact(vault, "tasks", "t0003-wrong-assignee.md",
                    {"id": "t0003", "kind": "task", "name": "wrong-assignee",
                     "status": "ready", "assignee": "alice", "type": "feature"})
    out = _quiet_output(["list", "--view", "dev-queue", "--type", "feature"])
    assert "t0001-match" in out
    assert "t0002-wrong-type" not in out
    assert "t0003-wrong-assignee" not in out


# ---------------------------------------------------------------------------
# L16 — --filter assignee=alice still works unaffected by generation
# ---------------------------------------------------------------------------

def test_L16_explicit_filter_flag_works(vault):
    """L16: --filter assignee=alice behaves exactly as before generation."""
    _write_artifact(vault, "tasks", "t0001-alice.md",
                    {"id": "t0001", "kind": "task", "name": "alice-task",
                     "status": "ready", "assignee": "alice"})
    _write_artifact(vault, "tasks", "t0002-bob.md",
                    {"id": "t0002", "kind": "task", "name": "bob-task",
                     "status": "ready", "assignee": "bob"})
    out = _quiet_output(["list", "--kind", "task", "--filter", "assignee=alice"])
    assert "t0001-alice" in out
    assert "t0002-bob" not in out


# ---------------------------------------------------------------------------
# L17 — --help with no --kind when kinds/ is empty
# ---------------------------------------------------------------------------

def test_L17_help_no_kind_empty_kinds_dir(tmp_path, monkeypatch, capsys):
    """L17: --help with empty kinds/ dir — no exception, static surface shown."""
    root = tmp_path / "vault"
    (root / "artifacts" / "kinds").mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    with pytest.raises(SystemExit) as exc:
        main(["list", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--kind" in out
    assert "--status" in out


# ---------------------------------------------------------------------------
# L18 — --kind notarealkind --help: static surface shown, no error
# ---------------------------------------------------------------------------

def test_L18_unknown_kind_help_shows_static_surface(vault, capsys):
    """L18: --kind notarealkind --help → static list help; no crash."""
    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "notarealkind", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--status" in out
    assert "--kind" in out


# ---------------------------------------------------------------------------
# L19 — --kind notarealkind --status ready: runs, returns []
# ---------------------------------------------------------------------------

def test_L19_unknown_kind_with_filter_exits_1(vault, capsys):
    """L19: --kind notarealkind --status ready → core raises Unknown kind (exit 1).

    The static parser accepts the args (no enum validation for unknown kinds),
    but core.list_artifacts raises ValueError because the kind is not registered.
    """
    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "notarealkind", "--status", "ready", "-q"])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "notarealkind" in err.lower() or "unknown" in err.lower()


# ---------------------------------------------------------------------------
# L20 — malformed JSON schema: falls back to static surface
# ---------------------------------------------------------------------------

def test_L20_malformed_schema_json_fallback(tmp_path, monkeypatch, capsys):
    """L20: malformed task.json → Phase 1 swallows error; static surface used."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    (root / "artifacts" / "tasks").mkdir(parents=True)
    (kinds_dir / "task.json").write_text("{invalid json!!!")
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--status" in out  # static fallback


# ---------------------------------------------------------------------------
# L22 — integer type coercion
# ---------------------------------------------------------------------------

def test_L22_integer_type_coercion(tmp_path, monkeypatch):
    """L22: integer schema property -- --weight 5 produces int in filters."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    (root / "artifacts" / "tasks").mkdir(parents=True)
    schema = {
        "x-dir": "tasks", "x-prefix": "t", "x-numbered": True,
        "type": "object",
        "properties": {
            "status": {"enum": ["ready"], "description": "Status."},
            "weight": {"type": "integer", "description": "Numeric weight."},
        },
    }
    (kinds_dir / "task.json").write_text(json.dumps(schema))
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    # Write an artifact with weight=5
    _write_artifact(root, "tasks", "t0001-a.md",
                    {"id": "t0001", "kind": "task", "name": "a",
                     "status": "ready", "weight": 5})
    _write_artifact(root, "tasks", "t0002-b.md",
                    {"id": "t0002", "kind": "task", "name": "b",
                     "status": "ready", "weight": 10})

    out = _quiet_output(["list", "--kind", "task", "--weight", "5"])
    assert "t0001-a" in out
    assert "t0002-b" not in out


def test_L23_integer_invalid_value_exits_2(tmp_path, monkeypatch, capsys):
    """L23: --weight notanumber → argparse type error, exit 2."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    (root / "artifacts" / "tasks").mkdir(parents=True)
    schema = {
        "x-dir": "tasks", "x-prefix": "t", "x-numbered": True,
        "type": "object",
        "properties": {
            "weight": {"type": "integer", "description": "Numeric weight."},
        },
    }
    (kinds_dir / "task.json").write_text(json.dumps(schema))
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "--weight", "notanumber"])
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# L24 — boolean type coercion
# ---------------------------------------------------------------------------

def test_L24_boolean_type_coercion(tmp_path, monkeypatch):
    """L24: --archived true/false produces bool values in filters."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    (root / "artifacts" / "tasks").mkdir(parents=True)
    schema = {
        "x-dir": "tasks", "x-prefix": "t", "x-numbered": True,
        "type": "object",
        "properties": {
            "status": {"enum": ["ready"], "description": "Status."},
            "archived": {"type": "boolean", "description": "Archived flag."},
        },
    }
    (kinds_dir / "task.json").write_text(json.dumps(schema))
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    _write_artifact(root, "tasks", "t0001-archived.md",
                    {"id": "t0001", "kind": "task", "name": "archived",
                     "status": "ready", "archived": True})
    _write_artifact(root, "tasks", "t0002-active.md",
                    {"id": "t0002", "kind": "task", "name": "active",
                     "status": "ready", "archived": False})

    out_true = _quiet_output(["list", "--kind", "task", "--archived", "true"])
    assert "t0001-archived" in out_true
    assert "t0002-active" not in out_true

    out_false = _quiet_output(["list", "--kind", "task", "--archived", "false"])
    assert "t0002-active" in out_false
    assert "t0001-archived" not in out_false


def test_L25_boolean_invalid_value_exits_2(tmp_path, monkeypatch, capsys):
    """L25: --archived maybe → _parse_bool error, exit 2."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    (root / "artifacts" / "tasks").mkdir(parents=True)
    schema = {
        "x-dir": "tasks", "x-prefix": "t", "x-numbered": True,
        "type": "object",
        "properties": {
            "archived": {"type": "boolean", "description": "Archived flag."},
        },
    }
    (kinds_dir / "task.json").write_text(json.dumps(schema))
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "--archived", "maybe"])
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# L26 — help text propagation from schema description
# ---------------------------------------------------------------------------

def test_L26_description_in_help(vault, capsys):
    """L26: schema description appears in --help text."""
    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "Priority hint" in out


def test_L27_missing_description_fallback(tmp_path, monkeypatch, capsys):
    """L27: property with no description gets 'filter by <field>'."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    (root / "artifacts" / "tasks").mkdir(parents=True)
    schema = {
        "x-dir": "tasks", "x-prefix": "t", "x-numbered": True,
        "type": "object",
        "properties": {
            "custom_field": {"type": "string"},  # no description
        },
    }
    (kinds_dir / "task.json").write_text(json.dumps(schema))
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "filter by custom" in out or "--custom-field" in out


def test_L28_cross_kind_diverging_description_has_varies_suffix(tmp_path, monkeypatch, capsys):
    """L28: cross-kind, two kinds with different descriptions → 'varies by kind' suffix."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
    (root / "artifacts" / "tasks").mkdir(parents=True)
    (root / "artifacts" / "specs").mkdir(parents=True)
    (kinds_dir / "task.json").write_text(json.dumps({
        "x-dir": "tasks", "x-prefix": "t", "x-numbered": True,
        "type": "object",
        "properties": {
            "status": {"enum": ["backlog", "ready"], "description": "Task status."},
        },
    }))
    (kinds_dir / "spec.json").write_text(json.dumps({
        "x-dir": "specs", "x-prefix": "s", "x-numbered": True,
        "type": "object",
        "properties": {
            "status": {"enum": ["draft", "approved"], "description": "Spec status."},
        },
    }))
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    with pytest.raises(SystemExit) as exc:
        main(["list", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "varies by kind" in out


# ---------------------------------------------------------------------------
# Regression: existing list invocations still work after schema-flag changes
# ---------------------------------------------------------------------------

def test_regression_existing_kind_status_filter(vault):
    """Regression: artifacts list --kind task --status ready still works."""
    _write_artifact(vault, "tasks", "t0001-ready.md",
                    {"id": "t0001", "kind": "task", "name": "ready-task",
                     "status": "ready"})
    _write_artifact(vault, "tasks", "t0002-backlog.md",
                    {"id": "t0002", "kind": "task", "name": "backlog-task",
                     "status": "backlog"})
    out = _quiet_output(["list", "--kind", "task", "--status", "ready"])
    assert "t0001-ready" in out
    assert "t0002-backlog" not in out


def test_regression_filter_kv_still_works(vault):
    """Regression: --filter assignee=alice still works alongside schema flags."""
    _write_artifact(vault, "tasks", "t0001-alice.md",
                    {"id": "t0001", "kind": "task", "name": "alice-task",
                     "status": "ready", "assignee": "alice"})
    _write_artifact(vault, "tasks", "t0002-bob.md",
                    {"id": "t0002", "kind": "task", "name": "bob-task",
                     "status": "ready", "assignee": "bob"})
    out = _quiet_output(["list", "--filter", "assignee=alice"])
    assert "t0001-alice" in out
    assert "t0002-bob" not in out


def test_regression_short_s_flag_per_kind(vault):
    """-s short form works in per-kind mode (schema-augmented)."""
    _write_artifact(vault, "tasks", "t0001-ready.md",
                    {"id": "t0001", "kind": "task", "name": "ready-task",
                     "status": "ready"})
    _write_artifact(vault, "tasks", "t0002-backlog.md",
                    {"id": "t0002", "kind": "task", "name": "backlog-task",
                     "status": "backlog"})
    out = _quiet_output(["list", "--kind", "task", "-s", "ready"])
    assert "t0001-ready" in out
    assert "t0002-backlog" not in out


def test_regression_short_s_flag_cross_kind(vault):
    """-s short form works in cross-kind mode."""
    _write_artifact(vault, "tasks", "t0001-ready.md",
                    {"id": "t0001", "kind": "task", "name": "ready-task",
                     "status": "ready"})
    _write_artifact(vault, "specs", "s0001-draft.md",
                    {"id": "s0001", "kind": "spec", "name": "draft-spec",
                     "status": "draft"})
    out = _quiet_output(["list", "-s", "ready"])
    assert "t0001-ready" in out
    assert "s0001-draft" not in out


def test_regression_create_kind_aware_unaffected(vault):
    """create --kind task --help still works after list-side peek refactor."""
    with pytest.raises(SystemExit) as exc:
        main(["create", "--kind", "task", "--help"])
    assert exc.value.code == 0


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _quiet_output(argv: list[str]) -> str:
    """Run main() with -q and return stdout lines joined."""
    import io
    import sys as _sys
    buf = io.StringIO()
    old_stdout = _sys.stdout
    _sys.stdout = buf
    try:
        try:
            main(argv + ["-q"])
        except SystemExit as exc:
            if exc.code != 0:
                raise
    finally:
        _sys.stdout = old_stdout
    return buf.getvalue()
