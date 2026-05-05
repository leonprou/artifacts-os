"""Module-system conformance tests.

Spec: s2061-artifacts-os-module-system

Verifies the package layout decisions: subpackages are importable, the
core public API is unchanged, and ``KindDef.meta`` exists for inter-
module configuration.
"""

import importlib
import tomllib
from pathlib import Path

import pytest

from artifacts_os import KindDef


MODULE_SUBPACKAGES = [
    "artifacts_os.views",
    "artifacts_os.log",
    "artifacts_os.cli",
    "artifacts_os.cli.commands",
    "artifacts_os.tui",
    "artifacts_os.tui.screens",
    "artifacts_os.ai",
]


@pytest.mark.parametrize("name", MODULE_SUBPACKAGES)
def test_subpackage_importable(name: str) -> None:
    importlib.import_module(name)


def test_kinddef_has_meta_field() -> None:
    kd = KindDef(name="task", dir="tasks", prefix="t", numbered=True)
    assert kd.meta == {}
    kd.meta["ai"] = {"context_sections": ["Requirements"]}
    assert kd.meta["ai"]["context_sections"] == ["Requirements"]


def test_cli_entry_point_exposes_main() -> None:
    from artifacts_os.cli import main

    assert callable(main)


def test_pyproject_extras_match_spec() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text())
    extras = data["project"]["optional-dependencies"]
    for key in ("views", "log", "cli", "tui", "ai", "dev", "all"):
        assert key in extras, f"missing extras key: {key}"
    assert extras["log"] == []
    assert extras["ai"] == []
    assert extras["views"] == []  # rich is a base dependency, not a views extra
    assert any("rich" in dep for dep in data["project"]["dependencies"])
    assert any("textual" in dep for dep in extras["tui"])
