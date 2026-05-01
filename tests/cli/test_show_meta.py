"""Tests for ``artifacts show --meta`` flag.

Spec: s0013-programmatic-cli-access §3, §5.3, §8.1, §11.5
"""

import json
import pytest

from artifacts_os.cli import main


def test_show_meta_table_no_body(vault, write_artifact, capsys):
    """show --meta renders a table with frontmatter keys and no body."""
    write_artifact(vault, "tasks", "t0046-fix-bug.md",
                   {"kind": "task", "id": "t0046", "name": "fix-bug", "status": "ready"},
                   body="# Fix the bug\n\nSome body text.")
    main(["show", "t0046-fix-bug", "--meta"])
    out = capsys.readouterr().out
    # Table should contain frontmatter fields.
    assert "t0046" in out
    # Body text must NOT appear.
    assert "Some body text" not in out


def test_show_meta_json_object(vault, write_artifact, capsys):
    """show --meta -j emits a JSON object of frontmatter."""
    write_artifact(vault, "tasks", "t0046-fix-bug.md",
                   {"kind": "task", "id": "t0046", "name": "fix-bug", "status": "ready"},
                   body="Body text that should not appear.")
    main(["show", "t0046-fix-bug", "--meta", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, dict), "Expected a JSON object, not array"
    assert data["id"] == "t0046"
    assert data["status"] == "ready"


def test_show_meta_json_no_body_key(vault, write_artifact, capsys):
    """show --meta -j output must not contain a 'body' key."""
    write_artifact(vault, "tasks", "t0046-fix-bug.md",
                   {"kind": "task", "id": "t0046", "name": "fix-bug", "status": "ready"},
                   body="# Body content")
    main(["show", "t0046-fix-bug", "--meta", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "body" not in data


def test_show_meta_json_is_dict_not_list(vault, write_artifact, capsys):
    """show --meta -j shape is always a dict (not a list)."""
    write_artifact(vault, "tasks", "t0046-fix-bug.md",
                   {"kind": "task", "id": "t0046", "name": "fix-bug", "status": "ready"})
    main(["show", "t0046-fix-bug", "--meta", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, dict)


def test_show_meta_not_found_exits_3(vault, capsys):
    """show <unknown> --meta exits with code 3."""
    with pytest.raises(SystemExit) as exc:
        main(["show", "nonexistent", "--meta"])
    assert exc.value.code == 3
    assert "error:" in capsys.readouterr().err


def test_show_meta_jq_field_extraction(vault, write_artifact, capsys):
    """Verify individual frontmatter fields are accessible from JSON output."""
    write_artifact(vault, "tasks", "t0046-fix-bug.md",
                   {"kind": "task", "id": "t0046", "name": "fix-bug", "status": "ready",
                    "parent": "[[t0041-epic]]"})
    main(["show", "t0046-fix-bug", "--meta", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["status"] == "ready"
    assert "t0041-epic" in data["parent"]
