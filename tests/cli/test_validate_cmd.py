"""Integration tests for cli validate command."""

import json

import pytest

from artifacts_os.cli import main


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_all_valid_vault_returns_0(vault, write_artifact):
    """Vault with all valid artifacts exits 0."""
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug",
                    "title": "Fix bug", "created": "2026-01-01", "status": "ready"})
    # No SystemExit means exit code 0
    main(["validate"])


def test_vault_with_error_returns_2(vault, write_artifact, capsys):
    """Vault with one bad artifact (error) exits 2 and JSON output contains name."""
    write_artifact(vault, "tasks", "t0001-broken.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-broken",
                    "created": "2026-01-01", "status": "ready"})
    # missing title → error

    with pytest.raises(SystemExit) as exc:
        main(["validate", "-j"])
    assert exc.value.code == 2

    out = capsys.readouterr().out
    data = json.loads(out)
    assert any(r["name"] == "t0001-broken" for r in data)


def test_vault_with_only_warnings_returns_0(vault, write_artifact, capsys):
    """Vault with only warnings exits 0; warnings appear in JSON output."""
    write_artifact(vault, "tasks", "t0001-test.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-test",
                    "title": "Test", "created": "2026-01-01", "status": "ready",
                    "weirdkey": "value"})  # unknown field → warning

    main(["validate", "-j"])  # exits 0

    out = capsys.readouterr().out
    data = json.loads(out)
    # weirdkey warning should appear in JSON output
    assert len(data) >= 1
    warnings = [i for i in data[0]["issues"] if i["severity"] == "warning"]
    assert any(i["field"] == "weirdkey" for i in warnings)


def test_json_output(vault, write_artifact, capsys):
    """--json output is valid JSON and each issue has a severity key."""
    write_artifact(vault, "tasks", "t0001-broken.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-broken",
                    "created": "2026-01-01", "status": "ready"})
    # missing title → error

    with pytest.raises(SystemExit) as exc:
        main(["validate", "-j"])
    assert exc.value.code == 2

    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) >= 1
    issues = data[0]["issues"]
    assert all("severity" in i for i in issues)


def test_fix_corrects_status(vault, write_artifact):
    """--fix corrects bad status; re-validate returns 0."""
    write_artifact(vault, "tasks", "t0001-broken.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-broken",
                    "title": "Test", "created": "2026-01-01", "status": "wip"})
    # bad status → error, fixable

    # First validate fails
    with pytest.raises(SystemExit) as exc:
        main(["validate"])
    assert exc.value.code == 2

    # Fix it
    main(["validate", "--fix"])

    # Now re-validate should pass
    main(["validate"])


def test_fix_does_not_touch_warnings(vault, write_artifact, capsys):
    """--fix does not remove unknown fields (warnings)."""
    write_artifact(vault, "tasks", "t0001-test.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-test",
                    "title": "Test", "created": "2026-01-01", "status": "ready",
                    "weirdkey": "value"})

    main(["validate", "--fix"])  # fix runs; exits 0 (only warnings)

    # weirdkey should still be there
    path = vault / "artifacts" / "tasks" / "t0001-test.md"
    content = path.read_text()
    assert "weirdkey" in content


def test_dry_run_does_not_write(vault, write_artifact):
    """--dry-run produces no writes even when fixes are available."""
    path = write_artifact(vault, "tasks", "t0001-broken.md",
                          {"kind": "task", "id": "t0001", "name": "t0001-broken",
                           "title": "Test", "created": "2026-01-01", "status": "wip"})
    original_content = path.read_text()

    # dry-run still reports errors (exits 2), but must not write
    with pytest.raises(SystemExit) as exc:
        main(["validate", "--dry-run"])
    assert exc.value.code == 2

    # File must be unchanged
    assert path.read_text() == original_content


def test_ref_not_found_exits_3(vault):
    """<ref> not found raises NotFoundError → exit 3."""
    with pytest.raises(SystemExit) as exc:
        main(["validate", "nonexistent-artifact"])
    assert exc.value.code == 3


def test_kind_filter(vault, write_artifact, capsys):
    """--kind filter validates only named kind."""
    write_artifact(vault, "tasks", "t0001-good-task.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-good-task",
                    "title": "Good", "created": "2026-01-01", "status": "ready"})
    write_artifact(vault, "agents", "bad-agent.md",
                   {"kind": "agent", "id": "bad-agent", "name": "bad-agent",
                    "created": "2026-01-01"})
    # agent missing title → error, but we only validate "task" kind

    # Validate only tasks — should exit 0 (task is valid)
    main(["validate", "--kind", "task"])
