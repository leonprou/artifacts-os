"""Tests for ``artifacts list [REF ...]`` positional ref-set filter.

Spec: t0075-cli-list-filter-by-refs
"""

import json

import pytest

from artifacts_os.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(root, write_artifact, n: int, name: str, status: str = "ready", **extra):
    num = f"{n:04d}"
    filename = f"t{num}-{name}.md"
    fm = {"kind": "task", "id": f"t{num}", "name": name, "status": status, **extra}
    return write_artifact(root, "tasks", filename, fm)


# ---------------------------------------------------------------------------
# Single ref by numeric ID
# ---------------------------------------------------------------------------

def test_single_ref_by_numeric_id(vault, write_artifact, capsys):
    """Single numeric ID returns exactly that one artifact."""
    _make_task(vault, write_artifact, 1, "alpha")
    _make_task(vault, write_artifact, 2, "beta")

    main(["list", "t1", "-j"])
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["id"] == "t0001"


# ---------------------------------------------------------------------------
# Multiple refs return exactly that set, in vault order
# ---------------------------------------------------------------------------

def test_multiple_refs_in_vault_order(vault, write_artifact, capsys):
    """Multiple refs return exactly that set; vault (filesystem) order is preserved."""
    _make_task(vault, write_artifact, 1, "alpha")
    _make_task(vault, write_artifact, 2, "beta")
    _make_task(vault, write_artifact, 3, "gamma")

    main(["list", "t1", "t3", "-j"])
    data = json.loads(capsys.readouterr().out)
    ids = [d["id"] for d in data]
    assert set(ids) == {"t0001", "t0003"}
    assert len(ids) == 2


def test_two_refs_json_length(vault, write_artifact, capsys):
    """artifacts list t0001 t0042 -j | jq length returns 2."""
    _make_task(vault, write_artifact, 1, "first")
    _make_task(vault, write_artifact, 42, "second")

    main(["list", "t0001", "t0042", "-j"])
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 2


# ---------------------------------------------------------------------------
# Full-name ref resolves
# ---------------------------------------------------------------------------

def test_full_name_ref_resolves(vault, write_artifact, capsys):
    """Full stem name (t0001-fix-bug) resolves to the correct artifact."""
    _make_task(vault, write_artifact, 1, "fix-bug")
    _make_task(vault, write_artifact, 2, "add-feature")

    main(["list", "t0001-fix-bug", "-j"])
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["id"] == "t0001"


# ---------------------------------------------------------------------------
# Partial-slug resolution
# ---------------------------------------------------------------------------

def test_unambiguous_partial_slug_resolves(vault, write_artifact, capsys):
    """An unambiguous partial slug resolves to the matching artifact."""
    _make_task(vault, write_artifact, 5, "migrate-database")
    _make_task(vault, write_artifact, 6, "add-logging")

    main(["list", "migrate", "-j"])
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["id"] == "t0005"


def test_ambiguous_partial_slug_fails_with_candidates(vault, write_artifact, capsys):
    """An ambiguous partial slug exits non-zero and reports candidates."""
    _make_task(vault, write_artifact, 1, "fix-auth-login")
    _make_task(vault, write_artifact, 2, "fix-auth-token")

    with pytest.raises(SystemExit) as exc:
        main(["list", "fix-auth", "-j"])

    assert exc.value.code != 0
    err = capsys.readouterr().err
    # Should mention the ambiguous query, which ends up in the error message
    assert "error:" in err


# ---------------------------------------------------------------------------
# Wikilink form
# ---------------------------------------------------------------------------

def test_wikilink_form_resolves(vault, write_artifact, capsys):
    """Wikilink-wrapped ref [[t0001]] resolves correctly."""
    _make_task(vault, write_artifact, 1, "the-task")
    _make_task(vault, write_artifact, 2, "other-task")

    main(["list", "[[t0001]]", "-j"])
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["id"] == "t0001"


def test_wikilink_full_stem_resolves(vault, write_artifact, capsys):
    """Full-stem wikilink [[t0001-the-task]] resolves correctly."""
    _make_task(vault, write_artifact, 1, "the-task")

    main(["list", "[[t0001-the-task]]", "-j"])
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["id"] == "t0001"


# ---------------------------------------------------------------------------
# Unresolved ref → non-zero exit, stderr names the ref, no partial output
# ---------------------------------------------------------------------------

def test_unresolved_ref_exits_nonzero(vault, write_artifact, capsys):
    """Unresolvable ref exits non-zero and names the ref on stderr."""
    _make_task(vault, write_artifact, 1, "real-task")

    with pytest.raises(SystemExit) as exc:
        main(["list", "t9999", "-j"])

    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "t9999" in err


def test_unresolved_ref_stderr_format(vault, write_artifact, capsys):
    """Unresolvable ref emits 'error: unresolved ref ...' on stderr."""
    _make_task(vault, write_artifact, 1, "real-task")

    with pytest.raises(SystemExit):
        main(["list", "no-such-ref"])

    err = capsys.readouterr().err
    assert "error:" in err
    assert "no-such-ref" in err


def test_unresolved_ref_no_partial_output(vault, write_artifact, capsys):
    """When one ref is unresolvable, no partial output (stdout empty)."""
    _make_task(vault, write_artifact, 1, "real-task")

    with pytest.raises(SystemExit):
        main(["list", "t0001", "t9999-missing", "-j"])

    out, err = capsys.readouterr()
    assert out == ""
    assert "t9999-missing" in err


def test_multiple_unresolved_refs_each_reported(vault, write_artifact, capsys):
    """Each unresolvable ref gets its own stderr line."""
    with pytest.raises(SystemExit):
        main(["list", "t9991-missing", "t9992-also-missing"])

    err = capsys.readouterr().err
    assert "t9991-missing" in err
    assert "t9992-also-missing" in err


# ---------------------------------------------------------------------------
# Intersection with --status
# ---------------------------------------------------------------------------

def test_intersection_with_status(vault, write_artifact, capsys):
    """artifacts list t0001 t0002 --status ready returns only those with status=ready."""
    _make_task(vault, write_artifact, 1, "first", status="ready")
    _make_task(vault, write_artifact, 2, "second", status="done")

    main(["list", "t0001", "t0002", "--status", "ready", "-j"])
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["id"] == "t0001"


def test_intersection_with_status_empty(vault, write_artifact, capsys):
    """Refs that exist but don't match --status → empty result, exit 0."""
    _make_task(vault, write_artifact, 1, "done-task", status="done")

    main(["list", "t0001", "--status", "ready", "-j"])
    data = json.loads(capsys.readouterr().out)
    assert data == []


# ---------------------------------------------------------------------------
# Intersection with --kind (constrains partial-slug resolution)
# ---------------------------------------------------------------------------

def test_kind_constrains_partial_slug_resolution(vault, write_artifact, capsys):
    """--kind task limits partial-slug resolution to tasks only."""
    # A task and a spec that both contain "migrate" in their slug
    write_artifact(vault, "tasks", "t0010-migrate-db.md",
                   {"kind": "task", "id": "t0010", "name": "migrate-db", "status": "ready"})
    write_artifact(vault, "specs", "s0010-migrate-schema.md",
                   {"kind": "spec", "id": "s0010", "name": "migrate-schema", "status": "draft"})

    # With --kind task, "migrate" should resolve to only the task
    main(["list", "--kind", "task", "migrate", "-j"])
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["id"] == "t0010"


def test_kind_constrains_resolution_not_found_in_kind(vault, write_artifact, capsys):
    """Ref that exists in a different kind but not the specified --kind exits non-zero."""
    write_artifact(vault, "specs", "s0001-some-spec.md",
                   {"kind": "spec", "id": "s0001", "name": "some-spec", "status": "draft"})

    with pytest.raises(SystemExit) as exc:
        main(["list", "--kind", "task", "s0001", "-j"])

    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# Intersection with --children
# ---------------------------------------------------------------------------

def test_intersection_with_children(vault, write_artifact, capsys):
    """list t1 t4 --children t0010 returns refs ∩ direct-children-of-t0010."""
    write_artifact(vault, "tasks", "t0010-epic.md",
                   {"kind": "task", "id": "t0010", "name": "epic", "status": "ready"})
    write_artifact(vault, "tasks", "t0001-child-of-epic.md",
                   {"kind": "task", "id": "t0001", "name": "child-of-epic",
                    "status": "ready", "parent": "[[t0010-epic]]"})
    write_artifact(vault, "tasks", "t0004-not-child.md",
                   {"kind": "task", "id": "t0004", "name": "not-child", "status": "ready"})

    main(["list", "t1", "t4", "--children", "t0010-epic", "-j"])
    data = json.loads(capsys.readouterr().out)
    ids = [d["id"] for d in data]
    assert "t0001" in ids
    assert "t0004" not in ids


# ---------------------------------------------------------------------------
# Output modes (-j, -q) — same narrowed set
# ---------------------------------------------------------------------------

def test_output_mode_json(vault, write_artifact, capsys):
    """Ref filter with -j returns a JSON array of the narrowed set."""
    _make_task(vault, write_artifact, 1, "alpha")
    _make_task(vault, write_artifact, 2, "beta")

    main(["list", "t1", "-j"])
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "t0001"


def test_output_mode_quiet(vault, write_artifact, capsys):
    """Ref filter with -q prints artifact stems, one per line."""
    _make_task(vault, write_artifact, 1, "alpha")
    _make_task(vault, write_artifact, 2, "beta")

    main(["list", "t1", "-q"])
    lines = [l for l in capsys.readouterr().out.strip().splitlines() if l]
    assert lines == ["t0001-alpha"]


def test_output_mode_fields(vault, write_artifact, capsys):
    """Ref filter with --fields produces a table with specified columns."""
    _make_task(vault, write_artifact, 1, "alpha")
    _make_task(vault, write_artifact, 2, "beta")

    # Should not raise; output contains the artifact
    main(["list", "t1", "--fields", "id,name,status"])
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" not in out


# ---------------------------------------------------------------------------
# Regression: no refs supplied → original list behavior unchanged
# ---------------------------------------------------------------------------

def test_no_refs_original_behavior(vault, write_artifact, capsys):
    """When no refs are supplied, list behaves exactly as before."""
    _make_task(vault, write_artifact, 1, "alpha")
    _make_task(vault, write_artifact, 2, "beta")

    main(["list", "-j"])
    data = json.loads(capsys.readouterr().out)
    ids = {d["id"] for d in data}
    assert {"t0001", "t0002"} == ids


def test_no_refs_with_status_filter(vault, write_artifact, capsys):
    """No refs + --status still applies status filter (regression)."""
    _make_task(vault, write_artifact, 1, "alpha", status="ready")
    _make_task(vault, write_artifact, 2, "beta", status="done")

    main(["list", "--status", "ready", "-j"])
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["id"] == "t0001"


def test_no_refs_empty_vault(vault, capsys):
    """No refs + empty vault returns exit 0 with no output."""
    main(["list", "-q"])  # no SystemExit → code 0
    out = capsys.readouterr().out
    assert out == ""
