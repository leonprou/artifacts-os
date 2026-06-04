"""Tests for ``artifacts --config <ref>`` CLI flag.

Spec: s0034-artifacts-cli-config-flag §11.1.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from artifacts_os.cli import _run, main
from tests.cli.conftest import make_vault_with_marker


# ── Helpers ────────────────────────────────────────────────────────────────


def _write_task(root: Path, name: str = "t0001-hello.md") -> None:
    """Write a minimal task artifact into the vault."""
    task_path = root / "artifacts" / "tasks" / name
    task_path.write_text(
        "---\nkind: task\nid: t0001\nname: hello\nstatus: backlog\n---\n"
    )


# ── Test 1: --config <abs-path> resolves explicit path ─────────────────────


def test_config_abs_path(tmp_path, monkeypatch, capsys):
    """--config <abs-path> resolves a vault outside CWD."""
    vault = make_vault_with_marker(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])

    code = _run(["--config", str(vault / "artifacts.yaml"), "list", "-q"])
    assert code == 0


# ── Test 2: --config ./<rel-path> resolves relative path ───────────────────


def test_config_rel_path(tmp_path, monkeypatch, capsys):
    """--config ./<rel-path> resolves a relative path from CWD."""
    vault = make_vault_with_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])

    rel = "./" + str((vault / "artifacts.yaml").relative_to(tmp_path))
    code = _run(["--config", rel, "list", "-q"])
    assert code == 0


# ── Test 3: --config <basename> walks up ───────────────────────────────────


def test_config_basename_walks_up(tmp_path, monkeypatch, capsys):
    """Basename form walks up from CWD and finds the custom-named marker."""
    vault = make_vault_with_marker(tmp_path, marker="openstation.yaml")
    deep = vault / "a" / "b"
    deep.mkdir(parents=True)
    monkeypatch.chdir(deep)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])

    code = _run(["--config", "openstation.yaml", "list", "-q"])
    assert code == 0


# ── Test 4: --config <missing-path> exits 2 ────────────────────────────────


def test_config_missing_path_exits_2(tmp_path, monkeypatch, capsys):
    """Missing explicit path exits 2 with the value in the error message."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])

    with pytest.raises(SystemExit) as exc:
        main(["--config", "./missing.yaml", "list"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--config:" in err
    assert "missing.yaml" in err
    assert "file not found" in err


# ── Test 5: --config <missing-basename> exits 2 ────────────────────────────


def test_config_missing_basename_exits_2(tmp_path, monkeypatch, capsys):
    """Basename not found anywhere up the tree exits 2 with the CWD in msg."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])

    with pytest.raises(SystemExit) as exc:
        main(["--config", "openstation.yaml", "list"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--config:" in err
    assert "openstation.yaml" in err
    assert "no file with that name found walking up from" in err


# ── Test 6: --config "" exits 2 via argparse ───────────────────────────────


def test_config_empty_string_exits_2(tmp_path, monkeypatch, capsys):
    """An empty --config value is rejected by the argparse type hook."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])

    with pytest.raises(SystemExit) as exc:
        main(["--config", "", "list"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--config" in err


# ── Test 7: symmetric position ─────────────────────────────────────────────


def test_config_symmetric_position(tmp_path, monkeypatch, capsys):
    """``--config`` before verb and after verb produce identical output."""
    vault = make_vault_with_marker(tmp_path)
    _write_task(vault)
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])

    config_path = str(vault / "artifacts.yaml")

    _run(["--config", config_path, "list", "-q"])
    out_before = capsys.readouterr().out

    _run(["list", "--config", config_path, "-q"])
    out_after = capsys.readouterr().out

    assert out_before == out_after


# ── Test 8: verb coverage ──────────────────────────────────────────────────


@pytest.mark.parametrize("verb_args,expected_codes", [
    # read verbs — succeed (exit 0)
    (["list", "-q"], {0}),
    (["events"], {0}),
    # read verbs that need a ref — fail with NotFoundError (3), not vault (2)
    (["show", "t9999"], {3}),
    (["get", "t9999", "status"], {3}),
    # write verbs that need an existing artifact — NotFoundError (3), not vault (2)
    (["set", "t9999", "status", "done"], {3}),
    (["status", "t9999", "done"], {3}),
    # create succeeds (exit 0)
    (["create", "test artifact"], {0}),
])
def test_config_verb_coverage(verb_args, expected_codes, tmp_path, monkeypatch, capsys):
    """Each verb honours ``--config`` — vault resolution works for all verbs."""
    vault = make_vault_with_marker(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])

    config_path = str(vault / "artifacts.yaml")
    code = _run(["--config", config_path] + verb_args)
    # Must not exit 2 (vault not found), and must match expected codes.
    assert code != 2, f"vault resolution failed for {verb_args}"
    assert code in expected_codes, f"unexpected exit {code} for {verb_args}"


# ── Test 9: init carve-out ─────────────────────────────────────────────────


def test_config_init_carve_out(tmp_path, monkeypatch, capsys):
    """``--config foo.yaml init`` writes artifacts.yaml, not foo.yaml."""
    target = tmp_path / "project"
    target.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])

    code = _run(["--config", "openstation.yaml", "init", str(target), "--template", "minimal", "-y"])
    assert code == 0
    # artifacts.yaml is written, not openstation.yaml.
    assert (target / "artifacts.yaml").is_file()
    assert not (target / "openstation.yaml").is_file()
    # Courtesy note goes to stderr.
    err = capsys.readouterr().err
    assert "--config is ignored by `artifacts init`" in err


# ── Test 10: default behaviour unchanged ───────────────────────────────────


def test_default_behaviour_unchanged(tmp_path, monkeypatch, capsys):
    """Without ``--config``, discovery from CWD still works."""
    vault = make_vault_with_marker(tmp_path)
    monkeypatch.chdir(vault)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])

    code = _run(["list", "-q"])
    assert code == 0


# ── Test 11: default + no vault ────────────────────────────────────────────


def test_default_no_vault(tmp_path, monkeypatch, capsys):
    """Without ``--config`` and no vault marker, existing error is unchanged."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])

    with pytest.raises(SystemExit) as exc:
        main(["list"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "not in an artifacts-os vault" in err


# ── Test 12: custom-basename vault ─────────────────────────────────────────


def test_custom_basename_vault(tmp_path, monkeypatch, capsys):
    """A vault with only ``openstation.yaml`` works under ``--config`` and
    fails under bare ``artifacts list`` (regression for the carve-out)."""
    vault = make_vault_with_marker(tmp_path, marker="openstation.yaml")
    deep = vault / "sub"
    deep.mkdir()
    monkeypatch.chdir(deep)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])

    # Works with --config openstation.yaml
    code = _run(["--config", "openstation.yaml", "list", "-q"])
    assert code == 0

    # Bare `list` fails — no artifacts.yaml anywhere in the tree.
    with pytest.raises(SystemExit) as exc:
        main(["list"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "not in an artifacts-os vault" in err
