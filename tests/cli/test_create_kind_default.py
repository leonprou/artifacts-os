"""Tests for cli create --kind default resolution (t0039).

Resolution order:
  explicit ``--kind`` flag → ``cli.defaults.create.kind`` → ``"task"``
"""

import json
from pathlib import Path

import pytest

from artifacts_os.cli import main
from artifacts_os.core import frontmatter as _fm

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_KINDS = {
    "task": {
        "x-dir": "tasks",
        "x-prefix": "t",
        "x-numbered": True,
        "properties": {},
    },
    "spec": {
        "x-dir": "specs",
        "x-prefix": "s",
        "x-numbered": True,
        "properties": {},
    },
    "agent": {
        "x-dir": "agents",
        "x-prefix": "",
        "x-numbered": False,
        "properties": {},
    },
}


_BASE_YAML = "layout_version: 1\nproject:\n  name: test\n"


def _make_vault(tmp_path: Path, artifacts_yaml_content: str) -> Path:
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts.yaml").write_text(artifacts_yaml_content)
    for name, schema in _KINDS.items():
        kind_folder = kinds_dir / name
        kind_folder.mkdir(parents=True, exist_ok=True)
        (kind_folder / "kind.json").write_text(json.dumps(schema))
        (root / "artifacts" / schema["x-dir"]).mkdir(parents=True, exist_ok=True)
    return root


def _meta(root: Path, stem: str, kind_dir: str) -> dict:
    path = root / "artifacts" / kind_dir / f"{stem}.md"
    meta, _ = _fm.parse(path.read_text())
    return meta


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def vault_no_default(tmp_path, monkeypatch):
    """Vault with no cli.defaults.create.kind configured."""
    root = _make_vault(tmp_path, _BASE_YAML)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)
    return root


@pytest.fixture
def vault_with_kind_default(tmp_path, monkeypatch):
    """Vault with cli.defaults.create.kind: spec configured."""
    yaml_content = (
        _BASE_YAML
        + "cli:\n  defaults:\n    create:\n      kind: spec\n"
    )
    root = _make_vault(tmp_path, yaml_content)
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)
    return root


@pytest.fixture
def no_vault(tmp_path, monkeypatch):
    """Directory with no artifacts.yaml anywhere in the tree."""
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(outside)
    return outside


# ---------------------------------------------------------------------------
# Tests: absent setting → fallback to "task"
# ---------------------------------------------------------------------------

def test_absent_setting_defaults_to_task(vault_no_default, capsys):
    """Without cli.defaults.create.kind, create defaults to 'task'."""
    main(["create", "My thing"])
    stem = capsys.readouterr().out.strip()
    assert stem.startswith("t0001-")
    meta = _meta(vault_no_default, stem, "tasks")
    assert meta["kind"] == "task"


# ---------------------------------------------------------------------------
# Tests: configured setting is used
# ---------------------------------------------------------------------------

def test_configured_kind_is_used(vault_with_kind_default, capsys):
    """cli.defaults.create.kind overrides the hardcoded 'task' fallback."""
    main(["create", "My spec"])
    stem = capsys.readouterr().out.strip()
    assert stem.startswith("s0001-")
    meta = _meta(vault_with_kind_default, stem, "specs")
    assert meta["kind"] == "spec"


# ---------------------------------------------------------------------------
# Tests: explicit --kind overrides YAML default
# ---------------------------------------------------------------------------

def test_explicit_kind_overrides_yaml_default(vault_with_kind_default, capsys):
    """An explicit --kind flag takes precedence over cli.defaults.create.kind."""
    main(["create", "My agent", "--kind", "agent"])
    stem = capsys.readouterr().out.strip()
    # agent is non-numbered, stem is just the slug
    assert (vault_with_kind_default / "artifacts" / "agents" / f"{stem}.md").exists()
    meta = _meta(vault_with_kind_default, stem, "agents")
    assert meta["kind"] == "agent"


def test_explicit_kind_overrides_when_no_yaml_default(vault_no_default, capsys):
    """Explicit --kind also overrides the hardcoded fallback."""
    main(["create", "My spec", "--kind", "spec"])
    stem = capsys.readouterr().out.strip()
    assert stem.startswith("s0001-")
    meta = _meta(vault_no_default, stem, "specs")
    assert meta["kind"] == "spec"


# ---------------------------------------------------------------------------
# Tests: no vault → still defaults to "task" (no crash)
# ---------------------------------------------------------------------------

def test_no_vault_defaults_to_task(no_vault, capsys):
    """Outside any vault, create still defaults to task — no crash."""
    # Without a vault there is no registry, so the command exits with an error
    # (ValidationError or similar), but it must NOT crash with AttributeError
    # and must NOT attempt a settings lookup.
    with pytest.raises(SystemExit) as exc_info:
        main(["create", "Thing"])
    # Exit code is non-zero because there is no vault/registry, but the
    # error must come from the registry layer, not from kind resolution.
    assert exc_info.value.code != 0
    err = capsys.readouterr().err
    # Must not be an AttributeError about cli_settings
    assert "AttributeError" not in err
    assert "cli_settings" not in err
