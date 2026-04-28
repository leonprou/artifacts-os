"""Tests for core.load_settings and related dataclasses.

Spec: s0010-core-settings-module-spec
"""

import pytest

from artifacts_os.core import (
    load_settings,
    UnsupportedSchemaVersion,
    Settings,
    ProjectConfig,
)


def _write_yaml(tmp_path, content: str):
    p = tmp_path / "artifacts.yaml"
    p.write_text(content)
    return p


def test_happy_path(tmp_path):
    """layout_version: 1 + valid project → populated Settings."""
    path = _write_yaml(
        tmp_path,
        "layout_version: 1\nproject:\n  name: myproject\n  alias: mp\n",
    )
    settings = load_settings(path)
    assert isinstance(settings, Settings)
    assert settings.layout_version == 1
    assert isinstance(settings.project, ProjectConfig)
    assert settings.project.name == "myproject"
    assert settings.project.alias == "mp"


def test_missing_layout_version(tmp_path):
    """Missing layout_version → UnsupportedSchemaVersion."""
    path = _write_yaml(tmp_path, "project:\n  name: myproject\n")
    with pytest.raises(UnsupportedSchemaVersion, match="missing layout_version"):
        load_settings(path)


def test_unsupported_layout_version(tmp_path):
    """layout_version: 2 → UnsupportedSchemaVersion."""
    path = _write_yaml(
        tmp_path,
        "layout_version: 2\nproject:\n  name: myproject\n",
    )
    with pytest.raises(UnsupportedSchemaVersion, match="unsupported version 2"):
        load_settings(path)


def test_missing_project_section(tmp_path):
    """Missing project section → raises (KeyError)."""
    path = _write_yaml(tmp_path, "layout_version: 1\n")
    with pytest.raises(KeyError):
        load_settings(path)


def test_project_alias_absent(tmp_path):
    """project.alias absent → ProjectConfig.alias is None."""
    path = _write_yaml(
        tmp_path,
        "layout_version: 1\nproject:\n  name: myproject\n",
    )
    settings = load_settings(path)
    assert settings.project.alias is None


def test_extra_top_level_keys_preserved_in_raw(tmp_path):
    """Extra top-level keys (views, run) are preserved verbatim in Settings.raw."""
    path = _write_yaml(
        tmp_path,
        (
            "layout_version: 1\n"
            "project:\n  name: myproject\n"
            "views:\n  active: compact\n"
            "run:\n  timeout: 30\n"
        ),
    )
    settings = load_settings(path)
    assert settings.raw["views"] == {"active": "compact"}
    assert settings.raw["run"] == {"timeout": 30}
    # Core fields also present in raw
    assert settings.raw["layout_version"] == 1
