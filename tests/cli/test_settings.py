"""Tests for cli.settings and cli-settings integration.

Covers:
- CliSettings.from_base parses defaults and aliases correctly
- cli.defaults.show.editor: true activates editor without -e
- Explicit -j still overrides the editor default
- cli.aliases remaps command names before argparse
- Unknown aliases fall through to argparse error (no crash)
"""

import json
import subprocess
from pathlib import Path

import pytest

from artifacts_os.core import load_settings
from artifacts_os.cli import main
from artifacts_os.cli.settings import CliSettings, DEFAULT_ALIASES


# ── helpers ──────────────────────────────────────────────────────────────────

def _write_yaml(path: Path, content: str) -> Path:
    p = path / "artifacts.yaml"
    p.write_text(content)
    return p


def _full_yaml(**extra_sections) -> str:
    """Build a minimal valid artifacts.yaml string."""
    lines = ["layout_version: 1", "project:", "  name: test-project"]
    for key, value in extra_sections.items():
        lines.append(f"{key}:")
        for line in value.splitlines():
            lines.append(f"  {line}")
    return "\n".join(lines) + "\n"


# ── CliSettings unit tests ────────────────────────────────────────────────────

def test_from_base_empty_section(tmp_path):
    """cli section absent → empty defaults and aliases."""
    p = _write_yaml(tmp_path, "layout_version: 1\nproject:\n  name: test\n")
    settings = CliSettings.from_base(load_settings(p))
    assert settings.defaults == {}
    assert settings.aliases == {}


def test_from_base_parses_defaults(tmp_path):
    """cli.defaults.show.editor: true is parsed into defaults dict."""
    p = _write_yaml(
        tmp_path,
        "layout_version: 1\nproject:\n  name: test\n"
        "cli:\n  defaults:\n    show:\n      editor: true\n",
    )
    settings = CliSettings.from_base(load_settings(p))
    assert settings.defaults == {"show": {"editor": True}}


def test_from_base_parses_aliases(tmp_path):
    """cli.aliases are parsed into the aliases dict."""
    p = _write_yaml(
        tmp_path,
        "layout_version: 1\nproject:\n  name: test\n"
        "cli:\n  aliases:\n    ls: list\n    t: status\n",
    )
    settings = CliSettings.from_base(load_settings(p))
    assert settings.aliases == {"ls": "list", "t": "status"}


def test_from_base_partial_cli_section(tmp_path):
    """cli section with only aliases → defaults is empty (and vice versa)."""
    p = _write_yaml(
        tmp_path,
        "layout_version: 1\nproject:\n  name: test\n"
        "cli:\n  aliases:\n    ls: list\n",
    )
    settings = CliSettings.from_base(load_settings(p))
    assert settings.defaults == {}
    assert settings.aliases == {"ls": "list"}


def test_from_base_inherits_base_fields(tmp_path):
    """CliSettings carries layout_version and project from base."""
    p = _write_yaml(
        tmp_path,
        "layout_version: 1\nproject:\n  name: myproj\n  alias: mp\n",
    )
    settings = CliSettings.from_base(load_settings(p))
    assert settings.layout_version == 1
    assert settings.project.name == "myproj"
    assert settings.project.alias == "mp"


# ── Integration: show editor default ─────────────────────────────────────────

def test_show_editor_default_opens_editor(vault, write_artifact, monkeypatch):
    """cli.defaults.show.editor: true → subprocess.run called without -e."""
    (vault / "artifacts.yaml").write_text(
        "layout_version: 1\nproject:\n  name: test\n"
        "cli:\n  defaults:\n    show:\n      editor: true\n"
    )
    write_artifact(
        vault, "tasks", "t0001-fix-bug.md",
        {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
    )

    calls: list = []
    monkeypatch.setenv("EDITOR", "testedit")
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd))

    main(["show", "t0001"])
    assert calls, "subprocess.run should have been called"
    assert calls[0][0] == "testedit"


def test_show_explicit_editor_flag_opens_editor(vault, write_artifact, monkeypatch):
    """Explicit -e flag still opens editor (baseline; no settings needed)."""
    write_artifact(
        vault, "tasks", "t0001-fix-bug.md",
        {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
    )

    calls: list = []
    monkeypatch.setenv("EDITOR", "myeditor")
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd))

    main(["show", "t0001", "-e"])
    assert calls and calls[0][0] == "myeditor"


def test_show_json_overrides_editor_default(vault, write_artifact, capsys, monkeypatch):
    """Explicit -j overrides cli.defaults.show.editor: true."""
    (vault / "artifacts.yaml").write_text(
        "layout_version: 1\nproject:\n  name: test\n"
        "cli:\n  defaults:\n    show:\n      editor: true\n"
    )
    write_artifact(
        vault, "tasks", "t0001-fix-bug.md",
        {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
    )

    calls: list = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd))

    main(["show", "t0001", "-j"])

    assert calls == [], "subprocess.run must not be called when -j is passed"
    data = json.loads(capsys.readouterr().out)
    assert data["name"] == "t0001-fix-bug"


def test_show_no_editor_default_renders_table(vault, write_artifact, capsys):
    """No editor default → table output (existing behavior preserved)."""
    write_artifact(
        vault, "tasks", "t0001-fix-bug.md",
        {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
    )
    main(["show", "t0001"])
    assert "t0001-fix-bug" in capsys.readouterr().out


# ── Integration: alias remapping ─────────────────────────────────────────────

def test_alias_dispatches_to_list(vault, write_artifact, capsys):
    """cli.aliases.ls: list → 'artifacts ls' runs list command."""
    (vault / "artifacts.yaml").write_text(
        "layout_version: 1\nproject:\n  name: test\n"
        "cli:\n  aliases:\n    ls: list\n"
    )
    write_artifact(
        vault, "tasks", "t0001-fix-bug.md",
        {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
    )

    main(["ls"])
    assert "t0001-fix-bug" in capsys.readouterr().out


def test_alias_dispatches_to_status(vault, write_artifact, capsys):
    """cli.aliases.t: status → 'artifacts t' runs status command."""
    (vault / "artifacts.yaml").write_text(
        "layout_version: 1\nproject:\n  name: test\n"
        "cli:\n  aliases:\n    t: status\n"
    )
    write_artifact(
        vault, "tasks", "t0001-fix-bug.md",
        {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
    )

    main(["t", "t0001", "in-progress"])
    out = capsys.readouterr().out
    assert "in-progress" in out


def test_unknown_command_falls_to_argparse_error(vault):
    """An unmapped command name exits with argparse error code 2."""
    (vault / "artifacts.yaml").write_text(
        "layout_version: 1\nproject:\n  name: test\n"
        "cli:\n  aliases:\n    ls: list\n"
    )
    with pytest.raises(SystemExit) as exc:
        main(["unknowncmd"])
    assert exc.value.code == 2


def test_no_aliases_configured_unknown_command_exits_2(vault):
    """No aliases configured: unknown command still exits 2 (no crash)."""
    with pytest.raises(SystemExit) as exc:
        main(["unknowncmd"])
    assert exc.value.code == 2


# ── Default aliases (built-in set) ───────────────────────────────────────────

def test_default_aliases_applied_without_vault(tmp_path, monkeypatch):
    """Built-in alias 'ls→list' resolves even outside a vault.

    Alias resolves before argparse; the expected failure is the "not in a
    vault" exit (code 2), not an argparse unknown-command error.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    with pytest.raises(SystemExit) as exc:
        main(["ls"])
    # 'ls' resolved to 'list' (valid command) → vault-not-found → exit 2
    assert exc.value.code == 2


def test_default_aliases_applied_with_empty_vault(vault, write_artifact, capsys):
    """Built-in alias 'sh→show' works in a vault with no cli: section."""
    write_artifact(
        vault, "tasks", "t0001-fix-bug.md",
        {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
    )
    main(["sh", "t0001"])
    assert "t0001-fix-bug" in capsys.readouterr().out


def test_vault_override_replaces_default(vault, write_artifact, capsys):
    """Vault cli.aliases.ls: status overrides the built-in ls→list."""
    (vault / "artifacts.yaml").write_text(
        "layout_version: 1\nproject:\n  name: test\n"
        "cli:\n  aliases:\n    ls: status\n"
    )
    write_artifact(
        vault, "tasks", "t0001-fix-bug.md",
        {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
    )
    main(["ls", "t0001", "in-progress"])
    assert "in-progress" in capsys.readouterr().out


def test_vault_alias_adds_alongside_defaults(vault, write_artifact, capsys):
    """Vault adds a new alias; all built-in defaults remain active."""
    (vault / "artifacts.yaml").write_text(
        "layout_version: 1\nproject:\n  name: test\n"
        "cli:\n  aliases:\n    x: list\n"
    )
    write_artifact(
        vault, "tasks", "t0001-fix-bug.md",
        {"kind": "task", "id": "t0001", "name": "t0001-fix-bug", "status": "ready"},
    )
    # New vault alias 'x' resolves to 'list'
    main(["x"])
    assert "t0001-fix-bug" in capsys.readouterr().out
    # Built-in 'sh' still resolves to 'show'
    main(["sh", "t0001"])
    assert "t0001-fix-bug" in capsys.readouterr().out
