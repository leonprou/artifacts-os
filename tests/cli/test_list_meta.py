"""Tests for ``artifacts list --meta`` flag.

Spec: s0013-programmatic-cli-access §3, §5.3, §8.3, §11.5
"""

import json
from pathlib import Path

import pytest

from artifacts_os.cli import main


def _write_yaml(root: Path, extra: str) -> None:
    base = root / "artifacts" / "artifacts.yaml"
    content = "layout_version: 1\nproject:\n  name: test\n" + extra
    base.write_text(content)


def test_list_meta_table_has_all_keys(vault, write_artifact, capsys):
    """list --meta table columns include union of frontmatter keys."""
    write_artifact(vault, "tasks", "t0001-alpha.md",
                   {"kind": "task", "id": "t0001", "name": "alpha", "status": "ready"})
    write_artifact(vault, "tasks", "t0002-beta.md",
                   {"kind": "task", "id": "t0002", "name": "beta", "status": "done",
                    "assignee": "alice"})

    main(["list", "--meta"])
    out = capsys.readouterr().out
    # All keys from both artifacts should appear in the output.
    assert "id" in out
    assert "status" in out


def test_list_meta_json_array(vault, write_artifact, capsys):
    """list --meta -j emits a JSON array of frontmatter dicts."""
    write_artifact(vault, "tasks", "t0001-alpha.md",
                   {"kind": "task", "id": "t0001", "name": "alpha", "status": "ready"})
    write_artifact(vault, "tasks", "t0002-beta.md",
                   {"kind": "task", "id": "t0002", "name": "beta", "status": "done"})

    main(["list", "--meta", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    ids = {item["id"] for item in data}
    assert "t0001" in ids
    assert "t0002" in ids


def test_list_meta_json_kind_filter(vault, write_artifact, capsys):
    """list --kind task --meta -j returns only tasks."""
    write_artifact(vault, "tasks", "t0001-task.md",
                   {"kind": "task", "id": "t0001", "name": "task", "status": "ready"})
    write_artifact(vault, "specs", "s0001-spec.md",
                   {"kind": "spec", "id": "s0001", "name": "spec", "status": "draft"})

    main(["list", "--kind", "task", "--meta", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert all(item["kind"] == "task" for item in data)


def test_list_meta_view_applies_filters(vault, write_artifact, capsys):
    """list --view active --meta -j: view filters and sort apply, columns switch."""
    write_artifact(vault, "tasks", "t0001-ready.md",
                   {"kind": "task", "id": "t0001", "name": "ready-task", "status": "ready"})
    write_artifact(vault, "tasks", "t0002-done.md",
                   {"kind": "task", "id": "t0002", "name": "done-task", "status": "done"})

    _write_yaml(vault, """
views:
  active:
    columns: id,name
    filters:
      status: ready
    sort: name
""")

    main(["list", "--view", "active", "--meta", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    # View filter still applies.
    assert all(item["status"] == "ready" for item in data)
    # Full frontmatter keys present (not limited to view.columns).
    assert all("kind" in item for item in data)


def test_list_meta_view_overrides_columns_table(vault, write_artifact, capsys):
    """list --view active --meta (table): --meta overrides view.columns."""
    write_artifact(vault, "tasks", "t0001-ready.md",
                   {"kind": "task", "id": "t0001", "name": "ready-task", "status": "ready",
                    "created": "2026-01-01"})

    _write_yaml(vault, """
views:
  active:
    columns: id,name
    filters:
      status: ready
""")

    main(["list", "--view", "active", "--meta"])
    out = capsys.readouterr().out
    # --meta should override view.columns; extra fields should be visible.
    assert "kind" in out or "created" in out


def test_list_meta_fields_mutually_exclusive(vault, capsys):
    """list --fields id,name --meta exits 2 (mutually exclusive)."""
    with pytest.raises(SystemExit) as exc:
        main(["list", "--fields", "id,name", "--meta"])
    assert exc.value.code == 2


def test_list_meta_quiet_wins(vault, write_artifact, capsys):
    """list --meta -q: quiet wins; prints names only."""
    write_artifact(vault, "tasks", "t0001-alpha.md",
                   {"kind": "task", "id": "t0001", "name": "alpha", "status": "ready"})

    main(["list", "--meta", "-q"])
    out = capsys.readouterr().out
    lines = [l for l in out.strip().splitlines() if l]
    assert lines == ["t0001-alpha"]


def test_list_meta_json_stable(vault, write_artifact, capsys):
    """list --meta -j shape is stable across two calls."""
    write_artifact(vault, "tasks", "t0001-alpha.md",
                   {"kind": "task", "id": "t0001", "name": "alpha", "status": "ready"})

    main(["list", "--meta", "-j"])
    out1 = capsys.readouterr().out

    main(["list", "--meta", "-j"])
    out2 = capsys.readouterr().out

    assert json.loads(out1) == json.loads(out2)


def test_list_json_without_meta(vault, write_artifact, capsys):
    """list -j (without --meta) also returns frontmatter dicts (existing behaviour)."""
    write_artifact(vault, "tasks", "t0001-alpha.md",
                   {"kind": "task", "id": "t0001", "name": "alpha", "status": "ready"})

    main(["list", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert data[0]["id"] == "t0001"
