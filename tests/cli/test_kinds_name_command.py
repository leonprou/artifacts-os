"""Tests for `artifacts kinds <name>` per-kind detail command (t0089)."""

import json
from pathlib import Path

import pytest

from artifacts_os.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_artifact_md(vault: Path, kind_name: str, content: str) -> Path:
    """Create artifacts/kinds/<kind_name>/ARTIFACT.md in the vault."""
    folder = vault / "artifacts" / "kinds" / kind_name
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "ARTIFACT.md"
    path.write_text(content, encoding="utf-8")
    return path


TASK_ARTIFACT_MD = """\
---
name: task
description: A unit of work tracked in the project backlog.
---

# Task

A task represents a single piece of work.
"""

SPEC_ARTIFACT_MD = """\
---
name: spec
description: A design specification document.
---

# Spec

Spec documents capture design decisions.
"""


# ---------------------------------------------------------------------------
# R2 — Default output: full ARTIFACT.md body
# ---------------------------------------------------------------------------

def test_kinds_name_prints_body(vault, capsys):
    """artifacts kinds <name> prints the full ARTIFACT.md body, byte-for-byte."""
    path = _write_artifact_md(vault, "task", TASK_ARTIFACT_MD)

    main(["kinds", "task"])
    out = capsys.readouterr().out

    assert out == TASK_ARTIFACT_MD


def test_kinds_name_body_exact_roundtrip(vault, tmp_path, capsys):
    """Output is byte-identical to the file content (binary round-trip)."""
    _write_artifact_md(vault, "task", TASK_ARTIFACT_MD)

    main(["kinds", "task"])
    out = capsys.readouterr().out

    assert out == TASK_ARTIFACT_MD


# ---------------------------------------------------------------------------
# R3 — --meta flag prepends metadata block
# ---------------------------------------------------------------------------

def test_kinds_name_meta_flag(vault, capsys):
    """artifacts kinds spec --meta prints metadata block then full body."""
    _write_artifact_md(vault, "spec", SPEC_ARTIFACT_MD)

    main(["kinds", "spec", "--meta"])
    out = capsys.readouterr().out

    # Body must still appear.
    assert SPEC_ARTIFACT_MD in out

    # Metadata block must appear before the body.
    meta_pos = out.index("name: spec")
    body_pos = out.index(SPEC_ARTIFACT_MD)
    assert meta_pos < body_pos, "metadata block should precede body"

    # Expected metadata fields present.
    assert "dir: specs" in out
    assert "prefix: s" in out
    assert "numbered: True" in out


def test_kinds_name_meta_block_visually_distinct(vault, capsys):
    """Metadata block uses --- delimiters, is distinct from markdown body."""
    _write_artifact_md(vault, "spec", SPEC_ARTIFACT_MD)

    main(["kinds", "spec", "--meta"])
    out = capsys.readouterr().out

    # Must open with --- delimiter.
    assert out.startswith("---\n")
    # Closing --- must appear before the body.
    closing_dash_pos = out.index("---\n", 4)  # skip opening ---
    body_pos = out.index(SPEC_ARTIFACT_MD)
    assert closing_dash_pos < body_pos


def test_kinds_name_meta_requires_name(vault):
    """--meta without <name> is a usage error (non-zero exit)."""
    with pytest.raises(SystemExit) as exc:
        main(["kinds", "--meta"])
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# R4 — -j (JSON) output
# ---------------------------------------------------------------------------

def test_kinds_name_json_output(vault, capsys):
    """artifacts kinds task -j emits JSON with meta and body keys."""
    _write_artifact_md(vault, "task", TASK_ARTIFACT_MD)

    main(["kinds", "task", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)

    assert "meta" in data
    assert "body" in data
    assert data["body"] == TASK_ARTIFACT_MD

    # Meta fields
    meta = data["meta"]
    assert meta["name"] == "task"
    assert meta["prefix"] == "t"
    assert meta["dir"] == "tasks"
    assert meta["numbered"] is True
    assert "backlog" in meta["statuses"]


def test_kinds_name_json_body_roundtrip(vault, capsys):
    """jq-equivalent: .body round-trips ARTIFACT.md content unchanged."""
    _write_artifact_md(vault, "task", TASK_ARTIFACT_MD)

    main(["kinds", "task", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)

    assert data["body"] == TASK_ARTIFACT_MD


def test_kinds_name_json_meta_wins_over_meta_flag(vault, capsys):
    """-j and --meta together: -j wins; output is JSON with meta embedded."""
    _write_artifact_md(vault, "task", TASK_ARTIFACT_MD)

    main(["kinds", "task", "-j", "--meta"])
    out = capsys.readouterr().out
    data = json.loads(out)

    # JSON output includes meta — --meta flag is redundant but not an error.
    assert "meta" in data
    assert data["meta"]["name"] == "task"


# ---------------------------------------------------------------------------
# R5 — Unknown kind: clear error, non-zero exit
# ---------------------------------------------------------------------------

def test_kinds_nonexistent_exits_nonzero(vault):
    """artifacts kinds nonexistent exits with non-zero code."""
    with pytest.raises(SystemExit) as exc:
        main(["kinds", "nonexistent"])
    assert exc.value.code != 0


def test_kinds_nonexistent_prints_error_to_stderr(vault, capsys):
    """artifacts kinds nonexistent prints error + available kinds to stderr."""
    with pytest.raises(SystemExit):
        main(["kinds", "nonexistent"])
    err = capsys.readouterr().err

    assert "nonexistent" in err
    # Available kinds should be listed in the error message.
    for expected_kind in ("agent", "research", "spec", "task"):
        assert expected_kind in err


# ---------------------------------------------------------------------------
# R6 — Missing ARTIFACT.md: graceful handling
# ---------------------------------------------------------------------------

def test_kinds_missing_artifact_md_text_error(vault, capsys):
    """Kind without ARTIFACT.md → clear stderr message and non-zero exit."""
    # Ensure the kind directory exists but ARTIFACT.md does not.
    kind_dir = vault / "artifacts" / "kinds" / "spec"
    kind_dir.mkdir(parents=True, exist_ok=True)
    # (No ARTIFACT.md written)

    with pytest.raises(SystemExit) as exc:
        main(["kinds", "spec"])
    assert exc.value.code != 0

    err = capsys.readouterr().err
    assert "ARTIFACT.md" in err
    assert "spec" in err


def test_kinds_missing_artifact_md_json_body_null(vault, capsys):
    """-j with missing ARTIFACT.md returns {"meta": {...}, "body": null}, exit 0."""
    # No ARTIFACT.md for the spec kind.
    kind_dir = vault / "artifacts" / "kinds" / "spec"
    kind_dir.mkdir(parents=True, exist_ok=True)

    main(["kinds", "spec", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)

    assert data["body"] is None
    assert data["meta"]["name"] == "spec"


def test_kinds_missing_artifact_md_json_exits_zero(vault, capsys):
    """-j with missing ARTIFACT.md exits 0."""
    kind_dir = vault / "artifacts" / "kinds" / "spec"
    kind_dir.mkdir(parents=True, exist_ok=True)

    # Should not raise SystemExit
    main(["kinds", "spec", "-j"])


# ---------------------------------------------------------------------------
# R7 — --help documents the new arguments
# ---------------------------------------------------------------------------

def test_kinds_help_documents_name_meta_j(vault, capsys):
    """--help documents <name>, --meta, and -j."""
    with pytest.raises(SystemExit):
        main(["kinds", "--help"])
    out = capsys.readouterr().out

    assert "<name>" in out or "name" in out
    assert "--meta" in out
    assert "-j" in out or "--json" in out


# ---------------------------------------------------------------------------
# Regression — listing still works without <name>
# ---------------------------------------------------------------------------

def test_kinds_listing_regression(vault, capsys):
    """`artifacts kinds` with no argument still produces the full listing."""
    main(["kinds", "-q"])
    out = capsys.readouterr().out
    names = out.strip().splitlines()
    assert set(names) == {"agent", "research", "spec", "task"}


def test_kinds_listing_table_regression(vault, capsys):
    """`artifacts kinds` default table output still works."""
    main(["kinds"])
    out = capsys.readouterr().out
    assert "description" in out.lower()
    assert "task" in out


def test_kinds_listing_json_regression(vault, capsys):
    """`artifacts kinds -j` still produces the listing JSON."""
    main(["kinds", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert len(data) == 4


# ---------------------------------------------------------------------------
# -e (editor) flag
# ---------------------------------------------------------------------------

def test_kinds_name_editor_invokes_execvp(vault, monkeypatch):
    """-e <name> calls os.execvp with $EDITOR and the ARTIFACT.md path."""
    artifact_path = _write_artifact_md(vault, "task", TASK_ARTIFACT_MD)

    calls: list = []
    monkeypatch.setenv("EDITOR", "myeditor")
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr(
        "os.execvp",
        lambda cmd, argv: calls.append((cmd, argv)),
    )

    main(["kinds", "task", "-e"])

    assert calls, "os.execvp should have been called"
    cmd, argv = calls[0]
    assert cmd == "myeditor"
    assert argv[0] == "myeditor"
    assert argv[-1] == str(artifact_path)


def test_kinds_name_editor_default_vi(vault, monkeypatch):
    """-e falls back to 'vi' when $EDITOR is unset."""
    _write_artifact_md(vault, "task", TASK_ARTIFACT_MD)

    calls: list = []
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setattr("os.execvp", lambda cmd, argv: calls.append((cmd, argv)))

    main(["kinds", "task", "-e"])

    assert calls
    assert calls[0][0] == "vi"


def test_kinds_name_editor_non_tty_downgrades(vault, monkeypatch, capsys):
    """-e in non-TTY context downgrades to default text output (no hang)."""
    _write_artifact_md(vault, "task", TASK_ARTIFACT_MD)

    calls: list = []
    monkeypatch.setenv("EDITOR", "myeditor")
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    monkeypatch.setattr("os.execvp", lambda cmd, argv: calls.append((cmd, argv)))

    main(["kinds", "task", "-e"])
    out = capsys.readouterr().out

    assert calls == [], "execvp must NOT be called in non-TTY mode"
    assert out == TASK_ARTIFACT_MD


def test_kinds_editor_requires_name(vault):
    """-e without <name> is a usage error (non-zero exit)."""
    with pytest.raises(SystemExit) as exc:
        main(["kinds", "-e"])
    assert exc.value.code != 0


def test_kinds_editor_missing_artifact_md_errors(vault, monkeypatch, capsys):
    """-e with kind that lacks ARTIFACT.md prints stderr error and exits 3."""
    # Kind exists, but no ARTIFACT.md
    kind_dir = vault / "artifacts" / "kinds" / "spec"
    kind_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    # If execvp is invoked we want the test to fail loudly.
    monkeypatch.setattr("os.execvp", lambda cmd, argv: (_ for _ in ()).throw(
        AssertionError("execvp must not be called when ARTIFACT.md is missing")
    ))

    with pytest.raises(SystemExit) as exc:
        main(["kinds", "spec", "-e"])
    assert exc.value.code == 3

    err = capsys.readouterr().err
    assert "ARTIFACT.md" in err
    assert "spec" in err


def test_kinds_editor_mutually_exclusive_with_json(vault):
    """-e and -j together produce a non-zero exit (argparse mutex)."""
    with pytest.raises(SystemExit) as exc:
        main(["kinds", "task", "-e", "-j"])
    assert exc.value.code != 0


def test_kinds_editor_mutually_exclusive_with_quiet(vault):
    """-e and -q together produce a non-zero exit (argparse mutex)."""
    with pytest.raises(SystemExit) as exc:
        main(["kinds", "task", "-e", "-q"])
    assert exc.value.code != 0


def test_kinds_help_documents_editor(vault, capsys):
    """--help mentions -e / --editor."""
    with pytest.raises(SystemExit):
        main(["kinds", "--help"])
    out = capsys.readouterr().out

    assert "-e" in out or "--editor" in out
