"""Tests for cli init command."""

import json
from pathlib import Path

import pytest

from artifacts_os.cli import main


def test_init_creates_structure(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init"])

    assert (tmp_path / "artifacts" / "artifacts.yaml").is_file()
    assert (tmp_path / "artifacts" / "kinds").is_dir()
    assert (tmp_path / "artifacts" / "tasks").is_dir()
    assert (tmp_path / "artifacts" / "specs").is_dir()
    assert (tmp_path / "artifacts" / "agents").is_dir()
    assert (tmp_path / "artifacts" / "research").is_dir()
    symlink = tmp_path / "openstation"
    assert symlink.is_symlink()
    assert symlink.resolve() == (tmp_path / "artifacts").resolve()


def test_init_kind_jsons_valid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    main(["init"])

    kinds_dir = tmp_path / "artifacts" / "kinds"
    jsons = list(kinds_dir.glob("*.json"))
    assert len(jsons) == 4
    for path in jsons:
        schema = json.loads(path.read_text())
        assert "x-dir" in schema, f"{path.name} missing x-dir"


def test_init_settings_uses_name(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init", "--name", "my-proj"])

    text = (tmp_path / "artifacts" / "artifacts.yaml").read_text()
    assert "my-proj" in text


def test_init_defaults_dir_name_as_project_name(tmp_path, monkeypatch):
    project = tmp_path / "cool-project"
    project.mkdir()
    monkeypatch.chdir(project)
    main(["init"])

    text = (project / "artifacts" / "artifacts.yaml").read_text()
    assert "cool-project" in text


def test_init_target_directory_arg(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "sub"
    target.mkdir()
    main(["init", str(target)])

    assert (target / "artifacts" / "artifacts.yaml").is_file()
    assert (target / "artifacts" / "tasks").is_dir()


def test_init_refuses_if_already_initialised(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main(["init"])  # first init succeeds

    with pytest.raises(SystemExit) as exc:
        main(["init"])  # second should fail
    assert exc.value.code == 2
    assert "already initialised" in capsys.readouterr().err


def test_init_then_list_works(tmp_path, monkeypatch, capsys):
    """After init, art list should run without error (empty result)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    main(["init"])
    capsys.readouterr()  # discard init output
    main(["list", "-q"])  # no SystemExit → exit code 0
    out = capsys.readouterr().out
    assert out == ""  # empty vault, no output
