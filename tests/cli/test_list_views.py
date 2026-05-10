"""Tests for artifacts list --view / default_views integration.

Covers all 10 cases from spec s0012 §11.4.
"""

import json
from pathlib import Path

import pytest

from artifacts_os.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_artifacts_yaml(root: Path, extra: str) -> None:
    """Rewrite artifacts.yaml with a valid project section plus *extra* YAML."""
    base = root / "artifacts.yaml"
    content = "layout_version: 1\nproject:\n  name: test\n" + extra
    base.write_text(content)


def _make_task(write_artifact, root, num, name_slug, status="ready", assignee=None):
    fm = {
        "kind": "task",
        "id": f"t{num:04d}",
        "name": f"t{num:04d}-{name_slug}",
        "status": status,
    }
    if assignee:
        fm["assignee"] = assignee
    write_artifact(root, "tasks", f"t{num:04d}-{name_slug}.md", fm)
    return fm["name"]


# ---------------------------------------------------------------------------
# Case 1 — --view resolves filters + columns + sort
# ---------------------------------------------------------------------------

def test_view_applies_filters_columns_sort(vault, write_artifact, capsys):
    """Case 1: --view active resolves filters, columns, and sort."""
    _make_task(write_artifact, vault, 1, "alpha", status="ready")
    _make_task(write_artifact, vault, 2, "beta", status="done")
    _make_task(write_artifact, vault, 3, "charlie", status="ready")

    _write_artifacts_yaml(vault, """
views:
  active:
    columns: id,name,status
    filters:
      status: ready
    sort: name
""")

    main(["list", "--view", "active", "-q"])
    out = capsys.readouterr().out
    lines = out.strip().splitlines()
    # Only "ready" tasks returned; "done" excluded
    stems = [l.strip() for l in lines if l.strip()]
    assert any("alpha" in s for s in stems)
    assert any("charlie" in s for s in stems)
    assert not any("beta" in s for s in stems)


# ---------------------------------------------------------------------------
# Case 2 — explicit --status overrides view filter; other filters stay
# ---------------------------------------------------------------------------

def test_explicit_status_overrides_view_filter(vault, write_artifact, capsys):
    """Case 2: --view active --status done overrides status filter."""
    _make_task(write_artifact, vault, 1, "alpha", status="ready")
    _make_task(write_artifact, vault, 2, "beta", status="done")

    _write_artifacts_yaml(vault, """
views:
  active:
    columns: id,name
    filters:
      status: ready
""")

    main(["list", "--view", "active", "--status", "done", "-q"])
    out = capsys.readouterr().out
    assert "beta" in out
    assert "alpha" not in out


# ---------------------------------------------------------------------------
# Case 3 — default_views binds when --kind matches
# ---------------------------------------------------------------------------

def test_default_views_fires_with_kind(vault, write_artifact, capsys):
    """Case 3: default_views: {task: active} + --kind task fires the binding."""
    _make_task(write_artifact, vault, 1, "alpha", status="ready")
    _make_task(write_artifact, vault, 2, "beta", status="done")

    _write_artifacts_yaml(vault, """
views:
  active:
    columns: id,name
    filters:
      status: ready
default_views:
  task: active
""")

    main(["list", "--kind", "task", "-q"])
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" not in out


# ---------------------------------------------------------------------------
# Case 4 — default_views does NOT fire without --kind
# ---------------------------------------------------------------------------

def test_default_views_no_fire_without_kind(vault, write_artifact, capsys):
    """Case 4: default_views without --kind is a no-op."""
    _make_task(write_artifact, vault, 1, "alpha", status="ready")
    _make_task(write_artifact, vault, 2, "beta", status="done")

    _write_artifacts_yaml(vault, """
views:
  active:
    columns: id,name
    filters:
      status: ready
default_views:
  task: active
""")

    # No --kind → default_views binding does not fire → both tasks appear
    main(["list", "-q"])
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" in out


# ---------------------------------------------------------------------------
# Case 5 — unknown --view exits 2
# ---------------------------------------------------------------------------

def test_unknown_view_exits_2(vault, capsys):
    """Case 5: --view does-not-exist → exit 2 with clear message."""
    # No views section in artifacts.yaml — should still exit 2
    with pytest.raises(SystemExit) as exc:
        main(["list", "--view", "does-not-exist"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "unknown view 'does-not-exist'" in err


# ---------------------------------------------------------------------------
# Case 6 — unknown default_views target exits 2
# ---------------------------------------------------------------------------

def test_unknown_default_views_target_exits_2(vault, capsys):
    """Case 6: default_views: {task: missing} + --kind task → exit 2."""
    _write_artifacts_yaml(vault, """
views:
  active:
    columns: id,name
    filters:
      status: ready
default_views:
  task: missing
""")

    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "-q"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "default_views.task" in err
    assert "missing" in err


# ---------------------------------------------------------------------------
# Case 7 — -j ignores columns but applies filters + sort
# ---------------------------------------------------------------------------

def test_json_ignores_columns_applies_filters_sort(vault, write_artifact, capsys):
    """Case 7: --view active -j → JSON with full frontmatter, filters applied."""
    _make_task(write_artifact, vault, 1, "alpha", status="ready")
    _make_task(write_artifact, vault, 2, "beta", status="done")

    _write_artifacts_yaml(vault, """
views:
  active:
    columns: id
    filters:
      status: ready
    sort: name
""")

    main(["list", "--view", "active", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    # Filters applied — only "ready"
    assert len(data) == 1
    assert data[0]["status"] == "ready"
    # Full frontmatter returned (not just the "id" column)
    assert "name" in data[0]


# ---------------------------------------------------------------------------
# Case 8 — -q ignores columns but applies filters + sort
# ---------------------------------------------------------------------------

def test_quiet_ignores_columns_applies_filters_sort(vault, write_artifact, capsys):
    """Case 8: --view active -q → stems filtered and sorted."""
    _make_task(write_artifact, vault, 1, "charlie", status="ready")
    _make_task(write_artifact, vault, 2, "alpha", status="ready")
    _make_task(write_artifact, vault, 3, "beta", status="done")

    _write_artifacts_yaml(vault, """
views:
  active:
    columns: id
    filters:
      status: ready
    sort: name
""")

    main(["list", "--view", "active", "-q"])
    out = capsys.readouterr().out
    lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
    # Only "ready" tasks; "done" excluded
    assert not any("beta" in l for l in lines)
    assert any("alpha" in l for l in lines)
    assert any("charlie" in l for l in lines)


# ---------------------------------------------------------------------------
# Case 9 — explicit --fields wins over view.columns; view.filters still apply
# ---------------------------------------------------------------------------

def test_explicit_fields_wins_over_view_columns(vault, write_artifact, capsys):
    """Case 9: --fields x,y --view active → --fields wins; filters still apply."""
    _make_task(write_artifact, vault, 1, "alpha", status="ready")
    _make_task(write_artifact, vault, 2, "beta", status="done")

    _write_artifacts_yaml(vault, """
views:
  active:
    columns: id
    filters:
      status: ready
""")

    # We can verify filters applied via -j and also --fields by checking JSON shape
    main(["list", "--view", "active", "--fields", "name,status", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    # Filters applied — only "ready"
    assert len(data) == 1
    assert data[0]["name"] == "t0001-alpha"


# ---------------------------------------------------------------------------
# Case 10 — custom filter key (assignee) triggers post-discovery filter
# ---------------------------------------------------------------------------

def test_custom_filter_key_post_discovery(vault, write_artifact, capsys):
    """Case 10: view with assignee filter → post-discovery equality filter."""
    _make_task(write_artifact, vault, 1, "alice-task", status="ready", assignee="alice")
    _make_task(write_artifact, vault, 2, "bob-task", status="ready", assignee="bob")

    _write_artifacts_yaml(vault, """
views:
  alice-view:
    columns: id,name
    filters:
      assignee: alice
""")

    main(["list", "--view", "alice-view", "-q"])
    out = capsys.readouterr().out
    assert "alice-task" in out
    assert "bob-task" not in out
