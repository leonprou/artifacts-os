"""Tests for cli show command."""

import json
from unittest.mock import patch

import pytest

from artifacts_os.cli import main


def test_show_json(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
                   body="# Fix the bug\n\nSome body text.")

    main(["show", "t0001-fix-bug", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["name"] == "t0001-fix-bug"
    assert data["status"] == "ready"
    assert "body" in data


def test_show_by_partial_ref(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"})

    main(["show", "t0001", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["name"] == "t0001-fix-bug"


def test_show_with_kind(vault, write_artifact, capsys):
    write_artifact(vault, "agents", "researcher.md",
                   {"kind": "agent", "id": "researcher", "name": "researcher"})

    main(["show", "researcher", "--kind", "agent", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["name"] == "researcher"


def test_show_not_found_exits_3(vault, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["show", "nonexistent"])
    assert exc.value.code == 3
    assert "error:" in capsys.readouterr().err


def test_show_default_output(vault, write_artifact, capsys):
    write_artifact(vault, "tasks", "t0001-fix-bug.md",
                   {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
                   body="# Fix the bug\n\nBody text.")

    main(["show", "t0001-fix-bug"])
    out = capsys.readouterr().out
    assert "t0001-fix-bug" in out


def test_show_body_with_rich_markup_chars(vault, write_artifact, capsys):
    """Body containing bracket sequences must not crash Rich markup parser."""
    body = "Use [/<normalisedName>] syntax.\n\nAlso [bold] and [/bold] are common."
    write_artifact(vault, "tasks", "t0002-markup.md",
                   {"kind": "task", "id": "t0002", "name": "t0002-markup", "status": "ready"},
                   body=body)

    main(["show", "t0002-markup"])
    out = capsys.readouterr().out
    assert "t0002-markup" in out
    assert "[/<normalisedName>]" in out


# ---------------------------------------------------------------------------
# Editor-default TTY/agent guard tests
# ---------------------------------------------------------------------------

def _write_editor_default_yaml(vault):
    """Overwrite artifacts.yaml to enable cli.defaults.show.editor."""
    (vault / "artifacts.yaml").write_text(
        "layout_version: 1\n"
        "project:\n  name: test\n"
        "cli:\n  defaults:\n    show:\n      editor: true\n"
    )


def test_show_editor_default_suppressed_in_agent_context(
    vault, write_artifact, capsys, monkeypatch
):
    """CLAUDECODE env var → editor default is suppressed, content printed to stdout."""
    write_artifact(vault, "tasks", "t0003-agent.md",
                   {"kind": "task", "id": "t0003", "name": "t0003-agent", "status": "ready"},
                   body="agent body")
    _write_editor_default_yaml(vault)
    monkeypatch.setenv("CLAUDECODE", "1")

    with patch("subprocess.run") as mock_run:
        main(["show", "t0003-agent"])
        mock_run.assert_not_called()

    out = capsys.readouterr().out
    assert "t0003-agent" in out


def test_show_editor_default_suppressed_when_not_tty(
    vault, write_artifact, capsys, monkeypatch
):
    """Non-tty stdout (no CLAUDECODE) → editor default is suppressed."""
    write_artifact(vault, "tasks", "t0004-notty.md",
                   {"kind": "task", "id": "t0004", "name": "t0004-notty", "status": "ready"},
                   body="piped body")
    _write_editor_default_yaml(vault)
    monkeypatch.delenv("CLAUDECODE", raising=False)

    # Patch _is_interactive to return False (simulates non-tty stdout)
    with patch("artifacts_os.cli.commands.show._is_interactive", return_value=False), \
         patch("subprocess.run") as mock_run:
        main(["show", "t0004-notty"])
        mock_run.assert_not_called()

    out = capsys.readouterr().out
    assert "t0004-notty" in out


def test_show_editor_default_fires_in_interactive_context(
    vault, write_artifact, monkeypatch
):
    """Interactive context + editor default (via yaml) → subprocess.run is called."""
    write_artifact(vault, "tasks", "t0005-interactive.md",
                   {"kind": "task", "id": "t0005", "name": "t0005-interactive",
                    "status": "ready"},
                   body="human body")
    _write_editor_default_yaml(vault)
    monkeypatch.delenv("CLAUDECODE", raising=False)

    with patch("artifacts_os.cli.commands.show._is_interactive", return_value=True), \
         patch("subprocess.run") as mock_run:
        main(["show", "t0005-interactive"])
        mock_run.assert_called_once()
        assert "t0005-interactive.md" in str(mock_run.call_args)


def test_show_built_in_default_opens_editor_no_config(
    vault, write_artifact, monkeypatch
):
    """Built-in default (no cli: block in yaml) opens editor in interactive context."""
    write_artifact(vault, "tasks", "t0005b-builtin.md",
                   {"kind": "task", "id": "t0005b", "name": "t0005b-builtin",
                    "status": "ready"},
                   body="built-in body")
    # No cli: section written — relying on the built-in True default.
    monkeypatch.delenv("CLAUDECODE", raising=False)

    with patch("artifacts_os.cli.commands.show._is_interactive", return_value=True), \
         patch("subprocess.run") as mock_run:
        main(["show", "t0005b-builtin"])
        mock_run.assert_called_once()
        assert "t0005b-builtin.md" in str(mock_run.call_args)


def test_show_config_editor_false_suppresses_default(
    vault, write_artifact, capsys, monkeypatch
):
    """cli.defaults.show.editor: false in yaml overrides the built-in True default."""
    write_artifact(vault, "tasks", "t0005c-optout.md",
                   {"kind": "task", "id": "t0005c", "name": "t0005c-optout",
                    "status": "ready"},
                   body="opt-out body")
    # Explicitly disable editor via config.
    (vault / "artifacts.yaml").write_text(
        "layout_version: 1\n"
        "project:\n  name: test\n"
        "cli:\n  defaults:\n    show:\n      editor: false\n"
    )
    monkeypatch.delenv("CLAUDECODE", raising=False)

    with patch("artifacts_os.cli.commands.show._is_interactive", return_value=True), \
         patch("subprocess.run") as mock_run:
        main(["show", "t0005c-optout"])
        mock_run.assert_not_called()

    out = capsys.readouterr().out
    assert "t0005c-optout" in out


def test_show_explicit_editor_flag_always_opens_editor(
    vault, write_artifact, monkeypatch
):
    """Explicit -e flag opens editor even in agent (non-interactive) context."""
    write_artifact(vault, "tasks", "t0006-explicit.md",
                   {"kind": "task", "id": "t0006", "name": "t0006-explicit",
                    "status": "ready"},
                   body="explicit editor body")
    monkeypatch.setenv("CLAUDECODE", "1")

    with patch("subprocess.run") as mock_run:
        main(["show", "t0006-explicit", "-e"])
        mock_run.assert_called_once()


def test_show_explicit_json_flag_overrides_editor_default(
    vault, write_artifact, capsys, monkeypatch
):
    """Explicit -j flag produces JSON output even when editor default is enabled."""
    write_artifact(vault, "tasks", "t0007-json.md",
                   {"kind": "task", "id": "t0007", "name": "t0007-json", "status": "ready"},
                   body="json body")
    _write_editor_default_yaml(vault)
    monkeypatch.delenv("CLAUDECODE", raising=False)

    with patch("artifacts_os.cli.commands.show._is_interactive", return_value=True), \
         patch("subprocess.run") as mock_run:
        main(["show", "t0007-json", "-j"])
        mock_run.assert_not_called()

    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["name"] == "t0007-json"


# ---------------------------------------------------------------------------
# Malformed frontmatter — t0210
# ---------------------------------------------------------------------------

_MALFORMED_AGENT = (
    "---\n"
    "kind: agent\n"
    "id: broken-agent\n"
    "name: broken-agent\n"
    "description: >- inline content on block-scalar line\n"
    "---\n"
    "body\n"
)


def _write_malformed_agent(vault):
    path = vault / "artifacts" / "agents" / "broken-agent.md"
    path.write_text(_MALFORMED_AGENT)
    return path


def test_show_malformed_frontmatter_exits_2(vault, capsys):
    """show on malformed YAML: exit 2, single-line stderr error, no traceback."""
    _write_malformed_agent(vault)

    with pytest.raises(SystemExit) as exc:
        main(["show", "broken-agent", "--kind", "agent"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    err_lines = [l for l in captured.err.splitlines() if l.strip()]
    assert len(err_lines) == 1
    assert err_lines[0].startswith("error:")
    assert "broken-agent" in err_lines[0]
    # No Python traceback frames.
    assert "Traceback" not in captured.err
    assert "yaml.scanner" not in captured.err


def test_show_malformed_frontmatter_json_flag_exits_2(vault, capsys):
    """show --json on malformed YAML: exit 2, single-line stderr, no traceback."""
    _write_malformed_agent(vault)

    with pytest.raises(SystemExit) as exc:
        main(["show", "broken-agent", "--kind", "agent", "-j"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    err_lines = [l for l in captured.err.splitlines() if l.strip()]
    assert len(err_lines) == 1
    assert err_lines[0].startswith("error:")
    assert "Traceback" not in captured.err


def test_show_malformed_frontmatter_editor_flag_exits_2(vault, capsys, monkeypatch):
    """show -e on malformed YAML: exit 2, single-line stderr, no traceback."""
    _write_malformed_agent(vault)
    monkeypatch.setenv("CLAUDECODE", "1")

    with pytest.raises(SystemExit) as exc:
        main(["show", "broken-agent", "--kind", "agent", "-e"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "Traceback" not in captured.err


def test_show_malformed_frontmatter_claudecode_env_exits_2(vault, capsys, monkeypatch):
    """show with CLAUDECODE=1 on malformed YAML: exit 2, single-line stderr, no traceback."""
    _write_malformed_agent(vault)
    monkeypatch.setenv("CLAUDECODE", "1")

    with pytest.raises(SystemExit) as exc:
        main(["show", "broken-agent", "--kind", "agent"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "Traceback" not in captured.err


def test_list_malformed_frontmatter_skips_with_warning(vault, capsys):
    """list --kind agent with malformed file: skips it, exits 0, emits warning."""
    _write_malformed_agent(vault)
    # Write a valid agent too so list has something to show.
    from artifacts_os.core import frontmatter as _fm
    good = vault / "artifacts" / "agents" / "good-agent.md"
    good.write_text(_fm.dump({"kind": "agent", "id": "good-agent", "name": "good-agent"}, ""))

    main(["list", "--kind", "agent"])
    captured = capsys.readouterr()
    assert "warning" in captured.err
    assert "broken-agent" in captured.err
    assert "good-agent" in captured.out
