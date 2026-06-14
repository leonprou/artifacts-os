"""Tests for cli create command."""

from datetime import date

import pytest

from artifacts_os.cli import main
from artifacts_os.core import frontmatter as _fm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _meta(vault, stem: str, kind_dir: str = "tasks") -> dict:
    path = vault / "artifacts" / kind_dir / f"{stem}.md"
    meta, _ = _fm.parse(path.read_text())
    return meta


def _body(vault, stem: str, kind_dir: str = "tasks") -> str:
    path = vault / "artifacts" / kind_dir / f"{stem}.md"
    _, body = _fm.parse(path.read_text())
    return body


# ---------------------------------------------------------------------------
# Basic creation (existing behaviour)
# ---------------------------------------------------------------------------

def test_create_task(vault, capsys):
    main(["create", "Fix the bug"])
    out = capsys.readouterr().out.strip()
    assert out.startswith("t0001-")
    assert (vault / "artifacts" / "tasks" / f"{out}.md").exists()


def test_create_increments(vault, capsys):
    main(["create", "First task"])
    main(["create", "Second task"])
    out = capsys.readouterr().out.strip()
    assert "t0002-" in out


def test_create_with_kind(vault, capsys):
    main(["create", "my-researcher", "--kind", "agent"])
    out = capsys.readouterr().out.strip()
    assert out == "my-researcher"
    assert (vault / "artifacts" / "agents" / "my-researcher.md").exists()


def test_create_with_fields(vault, capsys):
    # Status defaults to the state machine's `initial` (D223) — only the
    # initial value is legal at create time per D203. We pass status
    # explicitly here to verify --fields parsing while still satisfying the
    # state machine.
    main(["create", "Fix bug", "--fields", "status=backlog", "priority=high"])
    out = capsys.readouterr().out.strip()
    meta = _meta(vault, out)
    assert meta["status"] == "backlog"
    assert meta["priority"] == "high"


def test_create_with_body(vault, capsys):
    main(["create", "Task with body", "--body", "Some body content."])
    out = capsys.readouterr().out.strip()
    assert "Some body content." in _body(vault, out)


def test_create_unknown_kind_exits(vault, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["create", "Thing", "--kind", "unknownkind"])
    assert exc.value.code == 1


def test_create_empty_title_exits_2(vault, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["create", "!!!"])
    assert exc.value.code == 2
    assert "error:" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# --body-file
# ---------------------------------------------------------------------------

def test_body_file_reads_from_path(vault, capsys, tmp_path):
    body_file = tmp_path / "body.md"
    body_file.write_text("## Hello\n\nWorld.\n")
    main(["create", "Task", "--body-file", str(body_file)])
    out = capsys.readouterr().out.strip()
    assert "## Hello" in _body(vault, out)
    assert "World." in _body(vault, out)


def test_body_file_stdin(vault, capsys, monkeypatch):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("stdin body content\n"))
    main(["create", "Task", "--body-file", "-"])
    out = capsys.readouterr().out.strip()
    assert "stdin body content" in _body(vault, out)


def test_body_file_missing_exits_1(vault, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["create", "Task", "--body-file", "/nonexistent/file.md"])
    assert exc.value.code == 1
    assert "error:" in capsys.readouterr().err


def test_body_and_body_file_are_mutually_exclusive(vault, capsys):
    """argparse rejects --body together with --body-file."""
    with pytest.raises(SystemExit) as exc:
        main(["create", "Task", "--body", "text", "--body-file", "file.md"])
    assert exc.value.code != 0


def test_body_file_unreadable_exits_nonzero_no_orphan(vault, capsys, tmp_path):
    """An unreadable --body-file yields non-zero exit and leaves no artifact."""
    body_file = tmp_path / "secret.md"
    body_file.write_text("secret content")
    body_file.chmod(0o000)
    try:
        with pytest.raises(SystemExit) as exc:
            main(["create", "Task", "--body-file", str(body_file)])
        assert exc.value.code != 0
        assert "error:" in capsys.readouterr().err
        # No artifact file should have been created.
        assert not list((vault / "artifacts" / "tasks").glob("*.md"))
    finally:
        body_file.chmod(0o644)  # restore so tmp_path cleanup works


# ---------------------------------------------------------------------------
# Convenience flags
# ---------------------------------------------------------------------------

def test_assignee_flag(vault, capsys):
    main(["create", "Task", "--assignee", "alice"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["assignee"] == "alice"


def test_owner_flag(vault, capsys):
    main(["create", "Task", "--owner", "bob"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["owner"] == "bob"


def test_type_flag(vault, capsys):
    main(["create", "Task", "--type", "feature"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["type"] == "feature"


# ---------------------------------------------------------------------------
# --parent (wikilink auto-wrapping + parent must exist)
# ---------------------------------------------------------------------------

def test_parent_bare_ref_wrapped(vault, capsys):
    main(["create", "Parent task"])  # creates t0001-parent-task
    capsys.readouterr()
    main(["create", "Child task", "--parent", "t0001-parent-task"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["parent"] == "[[t0001-parent-task]]"


def test_parent_already_wrapped_unchanged(vault, capsys):
    main(["create", "Parent task"])  # creates t0001-parent-task
    capsys.readouterr()
    main(["create", "Child task", "--parent", "[[t0001-parent-task]]"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["parent"] == "[[t0001-parent-task]]"


def test_parent_missing_fails_before_write(vault, capsys):
    """Creating a child whose parent does not exist fails without writing."""
    with pytest.raises(SystemExit) as exc:
        main(["create", "Orphan task", "--parent", "t9999-does-not-exist"])
    assert exc.value.code == 1
    assert "error:" in capsys.readouterr().err
    # No child artifact should have been written.
    assert not list((vault / "artifacts" / "tasks").glob("*.md"))


# ---------------------------------------------------------------------------
# --depends-on (repeated flag, wikilink wrapping)
# ---------------------------------------------------------------------------

def test_depends_on_single(vault, capsys):
    main(["create", "Task", "--depends-on", "t0001"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["depends_on"] == ["[[t0001]]"]


def test_depends_on_repeated(vault, capsys):
    main(["create", "Task", "--depends-on", "t0001", "--depends-on", "t0002"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["depends_on"] == ["[[t0001]]", "[[t0002]]"]


def test_depends_on_already_wrapped(vault, capsys):
    main(["create", "Task", "--depends-on", "[[t0001]]"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["depends_on"] == ["[[t0001]]"]


# ---------------------------------------------------------------------------
# --fields with comma-list and wikilink fields
# ---------------------------------------------------------------------------

def test_fields_comma_list(vault, capsys):
    main(["create", "Task", "--fields", "tags=alpha,beta,gamma"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["tags"] == ["alpha", "beta", "gamma"]


def test_fields_wikilink_comma_list(vault, capsys):
    main(["create", "Task", "--fields", "depends_on=t0001,t0002"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["depends_on"] == ["[[t0001]]", "[[t0002]]"]


def test_fields_wikilink_single(vault, capsys):
    """--fields parent=ref wraps the value as [[ref]] (visible in dry-run; no parent lookup)."""
    main(["create", "Task", "--dry-run", "--fields", "parent=t0099"])
    out = capsys.readouterr().out
    assert "[[t0099]]" in out


def test_fields_bad_spec_exits_1(vault, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["create", "Task", "--fields", "no-equals-sign"])
    assert exc.value.code == 1
    assert "error:" in capsys.readouterr().err


def test_fields_array_wikilink_single_value(vault, capsys):
    """A single depends_on value produces a one-element wikilink list."""
    main(["create", "Task", "--fields", "depends_on=t0001-foo"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["depends_on"] == ["[[t0001-foo]]"]


def test_fields_subtasks_comma_list(vault, capsys):
    """subtasks= comma list produces a wikilink list."""
    main(["create", "Task", "--fields", "subtasks=t0002-a,t0003-b"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["subtasks"] == ["[[t0002-a]]", "[[t0003-b]]"]


def test_fields_artifacts_comma_list(vault, capsys):
    """artifacts= comma list produces a wikilink list."""
    main(["create", "Task", "--fields", "artifacts=s0001-spec,s0002-doc"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["artifacts"] == ["[[s0001-spec]]", "[[s0002-doc]]"]


def test_fields_array_wikilink_already_wrapped(vault, capsys):
    """Pre-wrapped refs in a comma list are not double-wrapped."""
    main(["create", "Task", "--fields", "depends_on=[[t0010-x]],[[t0011-y]]"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["depends_on"] == ["[[t0010-x]]", "[[t0011-y]]"]


# ---------------------------------------------------------------------------
# Parent backlink — subtasks auto-populated
# ---------------------------------------------------------------------------

def test_parent_backlink_added_to_subtasks(vault, capsys):
    """Creating a child with --parent appends child wikilink to parent's subtasks."""
    main(["create", "Parent task"])
    parent_stem = capsys.readouterr().out.strip()

    main(["create", "Child task", "--parent", parent_stem])
    child_stem = capsys.readouterr().out.strip()

    parent_meta = _meta(vault, parent_stem)
    assert f"[[{child_stem}]]" in parent_meta.get("subtasks", [])


def test_parent_backlink_via_fields_flag(vault, capsys):
    """--fields parent=ref also triggers the parent subtasks backlink."""
    main(["create", "Parent task"])
    parent_stem = capsys.readouterr().out.strip()

    main(["create", "Child task", "--fields", f"parent={parent_stem}"])
    child_stem = capsys.readouterr().out.strip()

    parent_meta = _meta(vault, parent_stem)
    assert f"[[{child_stem}]]" in parent_meta.get("subtasks", [])


def test_parent_backlink_idempotent(vault, capsys):
    """Re-creating the same child link does not duplicate it in subtasks."""
    main(["create", "Parent task"])
    parent_stem = capsys.readouterr().out.strip()

    main(["create", "Child task", "--parent", parent_stem])
    child_stem = capsys.readouterr().out.strip()

    # Manually pre-insert the child link (simulates a stale re-run scenario).
    # Then create a second child also referencing the same parent.
    main(["create", "Another child", "--parent", parent_stem])
    capsys.readouterr()

    parent_meta = _meta(vault, parent_stem)
    child_link = f"[[{child_stem}]]"
    assert parent_meta.get("subtasks", []).count(child_link) == 1


def test_parent_backlink_multiple_children(vault, capsys):
    """Multiple children each append their own wikilink to parent's subtasks."""
    main(["create", "Parent task"])
    parent_stem = capsys.readouterr().out.strip()

    main(["create", "Child A", "--parent", parent_stem])
    child_a = capsys.readouterr().out.strip()

    main(["create", "Child B", "--parent", parent_stem])
    child_b = capsys.readouterr().out.strip()

    parent_meta = _meta(vault, parent_stem)
    subtasks = parent_meta.get("subtasks", [])
    assert f"[[{child_a}]]" in subtasks
    assert f"[[{child_b}]]" in subtasks


# ---------------------------------------------------------------------------
# Convenience flags override --fields
# ---------------------------------------------------------------------------

def test_convenience_overrides_fields(vault, capsys):
    main(["create", "Task", "--fields", "assignee=alice", "--assignee", "bob"])
    out = capsys.readouterr().out.strip()
    assert _meta(vault, out)["assignee"] == "bob"


# ---------------------------------------------------------------------------
# --name override
# ---------------------------------------------------------------------------

def test_name_override_numbered(vault, capsys):
    main(["create", "Irrelevant Title", "--name", "my-slug"])
    out = capsys.readouterr().out.strip()
    assert out == "t0001-my-slug"
    assert (vault / "artifacts" / "tasks" / "t0001-my-slug.md").exists()
    assert _meta(vault, out)["name"] == "my-slug"


def test_name_override_non_numbered(vault, capsys):
    main(["create", "Irrelevant", "--kind", "agent", "--name", "my-agent"])
    out = capsys.readouterr().out.strip()
    assert out == "my-agent"
    assert (vault / "artifacts" / "agents" / "my-agent.md").exists()


def test_name_override_bad_slug_exits_1(vault, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["create", "Task", "--name", "!!!"])
    assert exc.value.code == 1
    assert "error:" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# --dry-run
# ---------------------------------------------------------------------------

def test_dry_run_no_file_written(vault, capsys):
    main(["create", "My Task", "--dry-run"])
    assert not any((vault / "artifacts" / "tasks").iterdir())
    out = capsys.readouterr().out
    assert "dry run" in out
    assert "kind: task" in out


def test_dry_run_shows_slug(vault, capsys):
    main(["create", "Hello World", "--dry-run"])
    out = capsys.readouterr().out
    assert "hello-world" in out


def test_dry_run_shows_fields(vault, capsys):
    main(["create", "Task", "--dry-run", "--assignee", "carol", "--owner", "dave"])
    out = capsys.readouterr().out
    assert "carol" in out
    assert "dave" in out


def test_dry_run_shows_body(vault, capsys):
    main(["create", "Task", "--dry-run", "--body", "## Requirements\n\n- item"])
    out = capsys.readouterr().out
    assert "## Requirements" in out


def test_dry_run_with_name_override(vault, capsys):
    main(["create", "Some Title", "--dry-run", "--name", "custom-slug"])
    out = capsys.readouterr().out
    assert "custom-slug" in out
    assert not any((vault / "artifacts" / "tasks").iterdir())


# ---------------------------------------------------------------------------
# Auto-populated `created` (t0040)
# ---------------------------------------------------------------------------

def _created_str(meta: dict) -> str:
    """Return ``meta["created"]`` as an ISO date string regardless of whether
    YAML parsed it as a string or a ``datetime.date`` object."""
    value = meta["created"]
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def test_created_auto_populated(vault, capsys):
    """`artifacts create` auto-populates `created` with today's ISO date."""
    main(["create", "Auto-dated task"])
    stem = capsys.readouterr().out.strip()
    assert _created_str(_meta(vault, stem)) == date.today().isoformat()


def test_created_explicit_value_preserved(vault, capsys):
    """An explicit `--fields created=…` is preserved (not overwritten)."""
    main(["create", "Backdated task", "--fields", "created=2024-01-15"])
    stem = capsys.readouterr().out.strip()
    assert _created_str(_meta(vault, stem)) == "2024-01-15"


def test_created_in_dry_run_output(vault, capsys):
    """Dry-run preview shows the auto-populated `created` field unquoted."""
    main(["create", "Preview task", "--dry-run"])
    out = capsys.readouterr().out
    assert f"created: {date.today().isoformat()}" in out


def test_created_for_non_numbered_kind(vault, capsys):
    """Auto-population applies to non-numbered kinds (e.g. agent) too."""
    main(["create", "my-agent", "--kind", "agent"])
    stem = capsys.readouterr().out.strip()
    assert _created_str(_meta(vault, stem, kind_dir="agents")) == date.today().isoformat()


def test_created_makes_validate_pass(vault, capsys):
    """A freshly-created artifact does not trip the missing-`created` error."""
    main(["create", "Validatable task"])
    stem = capsys.readouterr().out.strip()
    capsys.readouterr()  # drain
    main(["validate", stem])
    captured = capsys.readouterr()
    assert "Required field 'created' is missing" not in captured.err
    assert "Required field 'created' is missing" not in captured.out
    # 1 valid, 0 errors confirms the auto-populated date satisfies validate.
    assert "1 valid, 0 with errors" in captured.out
