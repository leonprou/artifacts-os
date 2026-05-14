"""Tests for cli kinds command."""

import json
from pathlib import Path

import pytest

from artifacts_os.cli import main


def test_kinds_quiet_default_four(vault, capsys):
    """Fresh vault lists all four registered kinds sorted."""
    main(["kinds", "-q"])
    out = capsys.readouterr().out
    names = out.strip().splitlines()
    assert names == sorted(names), "names should be sorted"
    assert names == ["agent", "research", "spec", "task"]


def test_kinds_json_output(vault, capsys):
    """JSON output produces list of dicts including original and new L1 keys."""
    main(["kinds", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 4
    # Original keys must still be present (backwards-compat, s0017 § 8.3).
    required_keys = {"name", "dir", "prefix", "numbered", "statuses"}
    for obj in data:
        assert required_keys.issubset(obj.keys()), f"missing required keys in {obj}"
    # New L1 keys must also be present.
    for obj in data:
        assert "description" in obj, f"'description' missing from {obj}"
        assert "has_template" in obj, f"'has_template' missing from {obj}"
    # Spot-check values for task kind
    task = next(o for o in data if o["name"] == "task")
    assert task["dir"] == "tasks"
    assert task["prefix"] == "t"
    assert task["numbered"] is True
    assert "backlog" in task["statuses"]


def test_kinds_custom_vault_kind_appears(vault, capsys):
    """A kind defined only in artifacts/kinds/ shows up in output."""
    kinds_dir = vault / "artifacts" / "kinds"
    schema = {"x-dir": "changelogs", "x-prefix": "c", "x-numbered": True}
    kind_folder = kinds_dir / "changelog"
    kind_folder.mkdir(parents=True, exist_ok=True)
    (kind_folder / "kind.json").write_text(json.dumps(schema))

    main(["kinds", "-q"])
    out = capsys.readouterr().out
    assert "changelog" in out.strip().splitlines()


def test_kinds_vault_overrides_caller_kind(vault, monkeypatch, capsys):
    """A vault-defined kind wins over a caller-registered kind of the same name."""
    from artifacts_os.core.models import KindDef
    import artifacts_os.cli as cli_module

    # Register a caller-provided "task" kind with a different dir
    caller_task = KindDef(name="task", dir="caller-tasks", prefix="x", numbered=False)
    monkeypatch.setattr(cli_module, "_registered_kinds", [caller_task])

    main(["kinds", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    task = next(o for o in data if o["name"] == "task")
    # Vault definition (dir="tasks") should win over caller (dir="caller-tasks")
    assert task["dir"] == "tasks"


def test_kinds_mutually_exclusive_flags(vault):
    """-q and -j together produce a non-zero exit."""
    with pytest.raises(SystemExit) as exc:
        main(["kinds", "-q", "-j"])
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# § 9.4  CLI / output
# ---------------------------------------------------------------------------

def test_cli_table_includes_description_column(vault, capsys):
    """Default table output includes a 'description' column header."""
    main(["kinds"])
    out = capsys.readouterr().out
    assert "description" in out.lower()


def test_cli_quiet_mode_unchanged(vault, capsys):
    """-q output is one name per line — no description column, byte-stable."""
    main(["kinds", "-q"])
    out = capsys.readouterr().out
    lines = out.strip().splitlines()
    # Every line must be a plain kind name with no extra content.
    for line in lines:
        assert " " not in line, f"unexpected content in quiet output: {line!r}"
        assert "description" not in line.lower()


def test_cli_json_keys_additive(vault, capsys):
    """JSON output retains original keys and adds description + has_template."""
    main(["kinds", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    for obj in data:
        # Original keys preserved
        assert "name" in obj
        assert "dir" in obj
        assert "prefix" in obj
        assert "numbered" in obj
        assert "statuses" in obj
        # New L1 keys present
        assert "description" in obj
        assert "has_template" in obj


def test_cli_description_shown_when_artifact_md_present(vault, capsys):
    """Kind with ARTIFACT.md + description shows description in table and JSON."""
    kinds_dir = vault / "artifacts" / "kinds"
    # Create folder-form kind with ARTIFACT.md
    folder = kinds_dir / "changelog"
    folder.mkdir(parents=True, exist_ok=True)
    schema = {"x-dir": "changelogs", "x-prefix": "c", "x-numbered": True}
    (folder / "kind.json").write_text(json.dumps(schema))
    artifact_md = folder / "ARTIFACT.md"
    artifact_md.write_text(
        "---\nname: changelog\ndescription: 'Tracks release notes and version history.'\n---\n",
        encoding="utf-8",
    )

    # Table output
    main(["kinds"])
    table_out = capsys.readouterr().out
    assert "Tracks release" in table_out or "release notes" in table_out.lower()

    # JSON output
    main(["kinds", "-j"])
    json_out = capsys.readouterr().out
    data = json.loads(json_out)
    cl = next(o for o in data if o["name"] == "changelog")
    assert cl["description"] == "Tracks release notes and version history."
    assert cl["has_template"] is True


def test_cli_json_no_description_is_none(vault, capsys):
    """Kind without ARTIFACT.md has description=None and has_template=False in JSON."""
    kinds_dir = vault / "artifacts" / "kinds"
    schema = {"x-dir": "foos", "x-prefix": "f", "x-numbered": True}
    kind_folder = kinds_dir / "foo"
    kind_folder.mkdir(parents=True, exist_ok=True)
    (kind_folder / "kind.json").write_text(json.dumps(schema))

    main(["kinds", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    foo = next(o for o in data if o["name"] == "foo")
    assert foo["description"] is None
    assert foo["has_template"] is False


# ---------------------------------------------------------------------------
# § 9.5  CLI ↔ Python API parity
# ---------------------------------------------------------------------------

def test_cli_json_matches_python_api(vault, capsys):
    """artifacts kinds -j payload matches KindCatalog.list_kinds() for each kind."""
    from artifacts_os.core import Registry, find_vault_root
    from artifacts_os.core.kinds_catalog import KindCatalog

    main(["kinds", "-j"])
    out = capsys.readouterr().out
    cli_data = json.loads(out)

    # Build registry + catalog the same way the CLI does.
    import os
    root = find_vault_root()
    r = Registry([], root=root)
    catalog = KindCatalog(r, root)
    api_entries = {e.name: e for e in catalog.list_kinds()}

    for obj in cli_data:
        name = obj["name"]
        assert name in api_entries, f"CLI kind '{name}' not in Python API"
        entry = api_entries[name]
        assert obj["description"] == entry.description, f"description mismatch for '{name}'"
        assert obj["has_template"] == entry.has_template, f"has_template mismatch for '{name}'"
