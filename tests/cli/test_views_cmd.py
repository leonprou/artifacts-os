"""Tests for the `artifacts views` command.

Covers all 13 cases from spec s0016 §12.3.
"""

import json
from pathlib import Path

import pytest

from artifacts_os.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_artifacts_yaml(root: Path, extra: str) -> None:
    """Rewrite artifacts.yaml with a valid base section plus *extra* YAML."""
    base = root / "artifacts" / "artifacts.yaml"
    content = "layout_version: 1\nproject:\n  name: test\n" + extra
    base.write_text(content)


# ---------------------------------------------------------------------------
# Case 1 — default table, populated views + default_views bindings
# ---------------------------------------------------------------------------


def test_default_table_populated(vault, capsys):
    """Case 1: views: + default_views: set → table with one row per view, sorted."""
    _write_artifacts_yaml(vault, """
views:
  beta-view:
    columns: id,name,status
    filters:
      kind: task
    sort: name
  alpha-view:
    columns: id,name
    filters:
      kind: agent
default_views:
  task: beta-view
""")

    main(["views"])
    out = capsys.readouterr().out
    # Both view names appear
    assert "alpha-view" in out
    assert "beta-view" in out
    # Sorted: alpha-view before beta-view
    assert out.index("alpha-view") < out.index("beta-view")
    # default-for column populated for beta-view
    assert "task" in out


# ---------------------------------------------------------------------------
# Case 2 — view with no kind filter renders (any)
# ---------------------------------------------------------------------------


def test_default_table_no_kind_filter(vault, capsys):
    """Case 2: view without kind filter renders (any) in the kind column."""
    _write_artifacts_yaml(vault, """
views:
  recent:
    columns: id,name
""")

    main(["views"])
    out = capsys.readouterr().out
    assert "recent" in out
    # Rich strips markup tags; (any) is the rendered text
    assert "(any)" in out


# ---------------------------------------------------------------------------
# Case 3 — view with no sort renders (none)
# ---------------------------------------------------------------------------


def test_default_table_no_sort(vault, capsys):
    """Case 3: view without sort renders (none) in the sort column."""
    _write_artifacts_yaml(vault, """
views:
  myview:
    columns: id,name
    filters:
      kind: task
""")

    main(["views"])
    out = capsys.readouterr().out
    assert "myview" in out
    assert "(none)" in out


# ---------------------------------------------------------------------------
# Case 4 — -q quiet output
# ---------------------------------------------------------------------------


def test_quiet_output(vault, capsys):
    """Case 4: -q emits one name per line, sorted alphabetically, exit 0."""
    _write_artifacts_yaml(vault, """
views:
  charlie:
    columns: id
  alpha:
    columns: id
  beta:
    columns: id
default_views:
  task: alpha
""")

    main(["views", "-q"])
    out, err = capsys.readouterr().out, capsys.readouterr().err
    lines = out.strip().splitlines()
    # Sorted alphabetically
    assert lines == ["alpha", "beta", "charlie"]
    # No binding info (no "task" in quiet output)
    assert "task" not in out
    assert err == ""


# ---------------------------------------------------------------------------
# Case 5 — -j JSON, populated
# ---------------------------------------------------------------------------


def test_json_populated(vault, capsys):
    """Case 5: -j emits {views: [...], default_views: {...}} with correct shape."""
    _write_artifacts_yaml(vault, """
views:
  active:
    columns: id,name,status
    filters:
      kind: task
      status: ready
    sort: -created
  recent:
    columns: id,name
default_views:
  task: active
""")

    main(["views", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)

    assert set(data.keys()) == {"views", "default_views"}
    # Views sorted alphabetically
    assert [v["name"] for v in data["views"]] == ["active", "recent"]
    # default_views verbatim
    assert data["default_views"] == {"task": "active"}
    # active view shape
    active = next(v for v in data["views"] if v["name"] == "active")
    assert active["columns"] == "id,name,status"
    assert active["filters"] == {"kind": "task", "status": "ready"}
    assert active["sort"] == "-created"
    assert active["default_for"] == ["task"]
    # recent has no binding
    recent = next(v for v in data["views"] if v["name"] == "recent")
    assert recent["default_for"] == []


# ---------------------------------------------------------------------------
# Case 6 — -j JSON, filters empty
# ---------------------------------------------------------------------------


def test_json_filters_empty(vault, capsys):
    """Case 6: view with no filters → "filters": {} in JSON."""
    _write_artifacts_yaml(vault, """
views:
  plain:
    columns: id,name
""")

    main(["views", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["views"][0]["filters"] == {}


# ---------------------------------------------------------------------------
# Case 7 — -j JSON, sort absent
# ---------------------------------------------------------------------------


def test_json_sort_absent(vault, capsys):
    """Case 7: view without sort → "sort": null in JSON."""
    _write_artifacts_yaml(vault, """
views:
  plain:
    columns: id,name
    filters:
      kind: task
""")

    main(["views", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["views"][0]["sort"] is None


# ---------------------------------------------------------------------------
# Case 8 — no views: section
# ---------------------------------------------------------------------------


def test_no_views_section(vault, capsys):
    """Case 8a: no views: key → stderr hint, no table, exit 0."""
    # artifacts.yaml has no views section at all
    main(["views"])
    _, err = capsys.readouterr().out, capsys.readouterr().err
    out2, err2 = capsys.readouterr().out, capsys.readouterr().err
    # Re-run to capture cleanly
    main(["views"])
    out3, err3 = capsys.readouterr()
    assert "no views defined in artifacts.yaml" in err3
    assert out3 == ""


def test_no_views_section_quiet(vault, capsys):
    """Case 8b: no views: + -q → no stdout, exit 0."""
    main(["views", "-q"])
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""


def test_no_views_section_json(vault, capsys):
    """Case 8c: no views: + -j → well-formed empty payload, exit 0."""
    main(["views", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data == {"views": [], "default_views": {}}


# ---------------------------------------------------------------------------
# Case 9 — views: empty map, default_views: set
# ---------------------------------------------------------------------------


def test_empty_views_with_default_views(vault, capsys):
    """Case 9a: empty views: + default_views: set → stderr hint, exit 0."""
    _write_artifacts_yaml(vault, """
views: {}
default_views:
  task: ready
""")

    main(["views"])
    out, err = capsys.readouterr()
    assert "no views defined in artifacts.yaml" in err
    assert out == ""


def test_empty_views_json_includes_defaults(vault, capsys):
    """Case 9b: empty views: + default_views: set → -j includes default_views."""
    _write_artifacts_yaml(vault, """
views: {}
default_views:
  task: ready
""")

    main(["views", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["views"] == []
    assert data["default_views"] == {"task": "ready"}


# ---------------------------------------------------------------------------
# Case 10 — mutually exclusive -q -j
# ---------------------------------------------------------------------------


def test_mutually_exclusive_flags(vault):
    """Case 10: -q and -j together → argparse exits 2."""
    with pytest.raises(SystemExit) as exc:
        main(["views", "-q", "-j"])
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# Case 11 — malformed view entry (missing columns)
# ---------------------------------------------------------------------------


def test_malformed_view_missing_columns(vault, capsys):
    """Case 11: view entry missing columns → exit 1, stderr error message."""
    _write_artifacts_yaml(vault, """
views:
  bad-view:
    filters:
      kind: task
""")

    with pytest.raises(SystemExit) as exc:
        main(["views"])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "view entry missing required 'columns' field" in err


# ---------------------------------------------------------------------------
# Case 12 — long columns string truncation
# ---------------------------------------------------------------------------


def test_long_columns_truncated_in_table(vault, capsys):
    """Case 12a: columns > 60 chars → truncated to 57 + … in table."""
    long_cols = "id,name,status,assignee,owner,created,type,priority,extra,x,y,z"
    assert len(long_cols) > 60

    _write_artifacts_yaml(vault, f"""
views:
  wide:
    columns: {long_cols}
""")

    main(["views"])
    out = capsys.readouterr().out
    # Full string does NOT appear (it was truncated before Rich renders it)
    assert long_cols not in out
    # An ellipsis appears as a truncation indicator
    assert "…" in out
    # At least the first portion of the columns string is visible
    assert "id,name,status,assignee" in out


def test_long_columns_full_in_json(vault, capsys):
    """Case 12b: full columns value preserved in -j even when > 60 chars."""
    long_cols = "id,name,status,assignee,owner,created,type,priority,extra,x,y,z"
    assert len(long_cols) > 60

    _write_artifacts_yaml(vault, f"""
views:
  wide:
    columns: {long_cols}
""")

    main(["views", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["views"][0]["columns"] == long_cols


# ---------------------------------------------------------------------------
# Case 13 — multiple kinds bound to one view
# ---------------------------------------------------------------------------


def test_multiple_kinds_bound_to_one_view(vault, capsys):
    """Case 13a: task + note both bound to same view → default_for sorted in JSON."""
    _write_artifacts_yaml(vault, """
views:
  shared:
    columns: id,name
default_views:
  task: shared
  note: shared
""")

    main(["views", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    shared = data["views"][0]
    assert shared["default_for"] == ["note", "task"]  # sorted alphabetically


def test_multiple_kinds_in_table(vault, capsys):
    """Case 13b: multiple bindings render as comma-separated in table."""
    _write_artifacts_yaml(vault, """
views:
  shared:
    columns: id,name
default_views:
  task: shared
  note: shared
""")

    main(["views"])
    out = capsys.readouterr().out
    assert "note" in out
    assert "task" in out
    # Both appear together (comma-separated)
    assert "note, task" in out
