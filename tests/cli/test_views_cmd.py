"""Tests for the `artifacts views` command.

Covers:
- List mode: cases 1–13 (spec s0016 §12.3)
- Show mode: cases 14–35 (spec s0016 §15.12, invoked via 'views show <name>')
- Execute mode: cases 36–41 (execute a view, listing matching artifacts)
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
    base = root / "artifacts.yaml"
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
    out, err = capsys.readouterr().out, capsys.readouterr().err
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


# ===========================================================================
# Show-mode cases (§15.12, cases 14–35) — invoked via 'views show <name>'
# ===========================================================================


# ---------------------------------------------------------------------------
# Case 14 — show default, fully populated view
# ---------------------------------------------------------------------------


def test_show_default_fully_populated(vault, capsys):
    """Case 14: fully populated view → all 6 rows rendered with correct values."""
    _write_artifacts_yaml(vault, """
views:
  ready:
    columns: id,name,assignee,created:date
    filters:
      kind: task
      status: ready
    sort: created
default_views:
  task: ready
""")

    main(["views", "show", "ready"])
    out = capsys.readouterr().out
    assert "name" in out
    assert "ready" in out
    assert "kind" in out
    assert "task" in out
    assert "columns" in out
    assert "id,name,assignee,created:date" in out
    assert "filters" in out
    assert "status" in out
    assert "sort" in out
    assert "created" in out
    assert "default-for" in out


# ---------------------------------------------------------------------------
# Case 15 — show default, view with no kind filter
# ---------------------------------------------------------------------------


def test_show_no_kind_filter(vault, capsys):
    """Case 15: view without kind filter → kind row renders (any)."""
    _write_artifacts_yaml(vault, """
views:
  recent:
    columns: id,name
""")

    main(["views", "show", "recent"])
    out = capsys.readouterr().out
    assert "(any)" in out


# ---------------------------------------------------------------------------
# Case 16 — show default, view with empty filters dict
# ---------------------------------------------------------------------------


def test_show_empty_filters(vault, capsys):
    """Case 16: view with no filters → filters row renders (none)."""
    _write_artifacts_yaml(vault, """
views:
  all-things:
    columns: id,name
""")

    main(["views", "show", "all-things"])
    out = capsys.readouterr().out
    assert "(none)" in out


# ---------------------------------------------------------------------------
# Case 17 — show default, view with no sort
# ---------------------------------------------------------------------------


def test_show_no_sort(vault, capsys):
    """Case 17: view without sort → sort row renders (none)."""
    _write_artifacts_yaml(vault, """
views:
  unsorted:
    columns: id,name
    filters:
      kind: task
""")

    main(["views", "show", "unsorted"])
    out = capsys.readouterr().out
    assert "(none)" in out


# ---------------------------------------------------------------------------
# Case 18 — show default, view with no binding
# ---------------------------------------------------------------------------


def test_show_no_default_for_binding(vault, capsys):
    """Case 18: view with no default_views binding → default-for renders (none)."""
    _write_artifacts_yaml(vault, """
views:
  unbound:
    columns: id,name
""")

    main(["views", "show", "unbound"])
    out = capsys.readouterr().out
    assert "(none)" in out


# ---------------------------------------------------------------------------
# Case 19 — show default, view bound to multiple kinds
# ---------------------------------------------------------------------------


def test_show_multiple_kinds_bound(vault, capsys):
    """Case 19: view bound to note+task → default-for renders 'note, task' (sorted)."""
    _write_artifacts_yaml(vault, """
views:
  shared:
    columns: id,name
default_views:
  note: shared
  task: shared
""")

    main(["views", "show", "shared"])
    out = capsys.readouterr().out
    assert "note, task" in out


# ---------------------------------------------------------------------------
# Case 20 — show default, long columns is NOT truncated
# ---------------------------------------------------------------------------


def test_show_long_columns_not_truncated(vault, capsys):
    """Case 20: columns > 60 chars → full string appears verbatim (untruncated)."""
    long_cols = "id,name,status,assignee,owner,created,type,priority,extra,x,y,z"
    assert len(long_cols) > 60

    _write_artifacts_yaml(vault, f"""
views:
  wide:
    columns: {long_cols}
""")

    main(["views", "show", "wide"])
    out = capsys.readouterr().out
    assert long_cols in out
    assert "…" not in out


# ---------------------------------------------------------------------------
# Case 21 — show default, nested filters
# ---------------------------------------------------------------------------


def test_show_nested_filters(vault, capsys):
    """Case 21: nested filters dict → rendered as multi-line indented JSON."""
    _write_artifacts_yaml(vault, """
views:
  complex:
    columns: id,name
    filters:
      kind: task
      meta:
        priority: high
""")

    main(["views", "show", "complex"])
    out = capsys.readouterr().out
    assert "kind" in out
    assert "task" in out
    assert "meta" in out
    assert "priority" in out


# ---------------------------------------------------------------------------
# Case 22 — show -q quiet
# ---------------------------------------------------------------------------


def test_show_quiet(vault, capsys):
    """Case 22: 'show <name> -q' → stdout is exactly <columns>\\n."""
    _write_artifacts_yaml(vault, """
views:
  myview:
    columns: id,name,status
    filters:
      kind: task
""")

    main(["views", "show", "myview", "-q"])
    out, err = capsys.readouterr()
    assert out == "id,name,status\n"
    assert err == ""


# ---------------------------------------------------------------------------
# Case 23 — show -j JSON, populated view
# ---------------------------------------------------------------------------


def test_show_json_populated(vault, capsys):
    """Case 23: 'show <name> -j' → single JSON object with correct keys."""
    _write_artifacts_yaml(vault, """
views:
  active:
    columns: id,name,status
    filters:
      kind: task
      status: ready
    sort: -created
default_views:
  task: active
""")

    main(["views", "show", "active", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)

    # Single object, not wrapped in {"views": [...]}
    assert isinstance(data, dict)
    assert "views" not in data
    assert set(data.keys()) == {"name", "columns", "filters", "sort", "default_for"}
    assert data["name"] == "active"
    assert data["columns"] == "id,name,status"
    assert data["filters"] == {"kind": "task", "status": "ready"}
    assert data["sort"] == "-created"
    assert data["default_for"] == ["task"]


# ---------------------------------------------------------------------------
# Case 24 — show -j JSON, filters empty
# ---------------------------------------------------------------------------


def test_show_json_filters_empty(vault, capsys):
    """Case 24: 'show -j' with view having no filters → "filters": {}."""
    _write_artifacts_yaml(vault, """
views:
  plain:
    columns: id,name
""")

    main(["views", "show", "plain", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["filters"] == {}


# ---------------------------------------------------------------------------
# Case 25 — show -j JSON, sort absent
# ---------------------------------------------------------------------------


def test_show_json_sort_absent(vault, capsys):
    """Case 25: 'show -j' with view having no sort → "sort": null."""
    _write_artifacts_yaml(vault, """
views:
  plain:
    columns: id,name
""")

    main(["views", "show", "plain", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["sort"] is None


# ---------------------------------------------------------------------------
# Case 26 — show -j JSON, view not bound
# ---------------------------------------------------------------------------


def test_show_json_not_bound(vault, capsys):
    """Case 26: 'show -j' with unbound view → "default_for": []."""
    _write_artifacts_yaml(vault, """
views:
  plain:
    columns: id,name
""")

    main(["views", "show", "plain", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["default_for"] == []


# ---------------------------------------------------------------------------
# Case 27 — unknown view, no close matches
# ---------------------------------------------------------------------------


def test_show_unknown_no_close_match(vault, capsys):
    """Case 27: unknown view with no close match → stderr error, exit 2."""
    _write_artifacts_yaml(vault, """
views:
  alpha:
    columns: id,name
""")

    with pytest.raises(SystemExit) as exc:
        main(["views", "show", "zzzzzzz"])
    assert exc.value.code == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "error: unknown view 'zzzzzzz'" in err
    assert "Did you mean" not in err


# ---------------------------------------------------------------------------
# Case 28 — unknown view, with close match
# ---------------------------------------------------------------------------


def test_show_unknown_with_close_match(vault, capsys):
    """Case 28: typo of existing view → suggests close match in stderr."""
    _write_artifacts_yaml(vault, """
views:
  ready:
    columns: id,name
  recent:
    columns: id,name
""")

    with pytest.raises(SystemExit) as exc:
        main(["views", "show", "redy"])
    assert exc.value.code == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "error: unknown view 'redy'" in err
    assert "Did you mean:" in err
    assert "ready" in err


# ---------------------------------------------------------------------------
# Case 29 — unknown view in -j mode
# ---------------------------------------------------------------------------


def test_show_unknown_json_mode(vault, capsys):
    """Case 29: unknown view with 'show -j' → no stdout, stderr error, exit 2."""
    _write_artifacts_yaml(vault, """
views:
  alpha:
    columns: id,name
""")

    with pytest.raises(SystemExit) as exc:
        main(["views", "show", "zzzzzzz", "-j"])
    assert exc.value.code == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "error: unknown view 'zzzzzzz'" in err


# ---------------------------------------------------------------------------
# Case 30 — unknown view in -q mode
# ---------------------------------------------------------------------------


def test_show_unknown_quiet_mode(vault, capsys):
    """Case 30: unknown view with 'show -q' → no stdout, stderr error, exit 2."""
    _write_artifacts_yaml(vault, """
views:
  alpha:
    columns: id,name
""")

    with pytest.raises(SystemExit) as exc:
        main(["views", "show", "zzzzzzz", "-q"])
    assert exc.value.code == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "error: unknown view 'zzzzzzz'" in err


# ---------------------------------------------------------------------------
# Case 31 — no views: section + show subcommand
# ---------------------------------------------------------------------------


def test_show_no_views_section_positional(vault, capsys):
    """Case 31: no views: section + 'show <name>' → unknown-view error, exit 2."""
    with pytest.raises(SystemExit) as exc:
        main(["views", "show", "ready"])
    assert exc.value.code == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "error: unknown view 'ready'" in err
    assert "no views defined" not in err


# ---------------------------------------------------------------------------
# Case 32 — views: empty map + show subcommand
# ---------------------------------------------------------------------------


def test_show_empty_views_map_positional(vault, capsys):
    """Case 32: views: {} + 'show <name>' → unknown-view error, exit 2."""
    _write_artifacts_yaml(vault, """
views: {}
""")

    with pytest.raises(SystemExit) as exc:
        main(["views", "show", "ready"])
    assert exc.value.code == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "error: unknown view 'ready'" in err
    assert "no views defined" not in err


# ---------------------------------------------------------------------------
# Case 33 — -q + -j with show subcommand
# ---------------------------------------------------------------------------


def test_show_mutual_exclusion(vault):
    """Case 33: -q and -j together with 'show <name>' → argparse exits 2."""
    _write_artifacts_yaml(vault, """
views:
  alpha:
    columns: id,name
""")

    with pytest.raises(SystemExit) as exc:
        main(["views", "show", "alpha", "-q", "-j"])
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# Case 34 — malformed entry + show subcommand
# ---------------------------------------------------------------------------


def test_show_malformed_entry(vault, capsys):
    """Case 34: malformed view entry (missing columns) + 'show <name>' → exit 1."""
    _write_artifacts_yaml(vault, """
views:
  bad-view:
    filters:
      kind: task
""")

    with pytest.raises(SystemExit) as exc:
        main(["views", "show", "bad-view"])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "view entry missing required 'columns' field" in err


# ---------------------------------------------------------------------------
# Case 35 — show mode does not affect list mode
# ---------------------------------------------------------------------------


def test_show_does_not_affect_list_mode(vault, capsys):
    """Case 35: running 'views' (no args) still produces list-mode table."""
    _write_artifacts_yaml(vault, """
views:
  alpha:
    columns: id,name
  beta:
    columns: id,status
""")

    main(["views"])
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" in out


# ===========================================================================
# Execute-mode cases (cases 36–41)
# ===========================================================================


# ---------------------------------------------------------------------------
# Case 36 — execute mode, no artifacts
# ---------------------------------------------------------------------------


def test_execute_mode_empty(vault, capsys):
    """Case 36: 'views <name>' with no matching artifacts → exit 0, no error."""
    _write_artifacts_yaml(vault, """
views:
  open-tasks:
    columns: id,name,status
    filters:
      kind: task
      status: ready
""")

    main(["views", "open-tasks"])
    _, err = capsys.readouterr()
    assert err == ""


# ---------------------------------------------------------------------------
# Case 37 — execute mode, -j with no artifacts
# ---------------------------------------------------------------------------


def test_execute_mode_json_empty(vault, capsys):
    """Case 37: 'views <name> -j' with no artifacts → JSON empty array."""
    _write_artifacts_yaml(vault, """
views:
  open-tasks:
    columns: id,name,status
    filters:
      kind: task
""")

    main(["views", "open-tasks", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert data == []


# ---------------------------------------------------------------------------
# Case 38 — execute mode, -q with no artifacts
# ---------------------------------------------------------------------------


def test_execute_mode_quiet_empty(vault, capsys):
    """Case 38: 'views <name> -q' with no artifacts → empty stdout, exit 0."""
    _write_artifacts_yaml(vault, """
views:
  open-tasks:
    columns: id,name
    filters:
      kind: task
""")

    main(["views", "open-tasks", "-q"])
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""


# ---------------------------------------------------------------------------
# Case 39 — execute mode, matching artifacts appear in output
# ---------------------------------------------------------------------------


def test_execute_mode_filters_artifacts(vault, capsys, write_artifact):
    """Case 39: 'views <name>' lists only artifacts matching the view's filters."""
    _write_artifacts_yaml(vault, """
views:
  open-tasks:
    columns: id,name,status
    filters:
      kind: task
      status: ready
""")
    write_artifact(vault, "tasks", "t0001-fix-bug.md", {
        "id": "t0001", "name": "fix-bug", "kind": "task", "status": "ready",
    })
    write_artifact(vault, "tasks", "t0002-done.md", {
        "id": "t0002", "name": "done", "kind": "task", "status": "done",
    })

    main(["views", "open-tasks"])
    out = capsys.readouterr().out
    assert "t0001" in out
    assert "t0002" not in out


# ---------------------------------------------------------------------------
# Case 40 — execute mode, unknown view name
# ---------------------------------------------------------------------------


def test_execute_mode_unknown_view(vault, capsys):
    """Case 40: 'views <unknown>' → stderr error, exit 2, no stdout."""
    _write_artifacts_yaml(vault, """
views:
  alpha:
    columns: id,name
""")

    with pytest.raises(SystemExit) as exc:
        main(["views", "xyz"])
    assert exc.value.code == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "error: unknown view 'xyz'" in err


# ---------------------------------------------------------------------------
# Case 41 — execute mode, close-match suggestion
# ---------------------------------------------------------------------------


def test_execute_mode_unknown_close_match(vault, capsys):
    """Case 41: 'views <typo>' → suggests close matches in stderr."""
    _write_artifacts_yaml(vault, """
views:
  ready:
    columns: id,name
""")

    with pytest.raises(SystemExit) as exc:
        main(["views", "redy"])
    assert exc.value.code == 2
    _, err = capsys.readouterr()
    assert "error: unknown view 'redy'" in err
    assert "Did you mean:" in err
    assert "ready" in err
