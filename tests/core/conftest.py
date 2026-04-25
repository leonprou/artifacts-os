"""Shared fixtures for core tests."""

from pathlib import Path

import pytest

from artifacts_os import KindDef, Registry


def _default_kinds() -> list[KindDef]:
    return [
        KindDef(
            name="task",
            dir="tasks",
            prefix="t",
            numbered=True,
            statuses=["backlog", "ready", "in-progress", "done"],
        ),
        KindDef(
            name="research",
            dir="research",
            prefix="r",
            numbered=True,
            statuses=[],
        ),
        KindDef(
            name="agent",
            dir="agents",
            prefix="",
            numbered=False,
            statuses=[],
        ),
    ]


@pytest.fixture
def make_vault(tmp_path: Path):
    """Factory: make_vault(kinds=None) -> (root, Registry)."""

    def _make(kinds: list[KindDef] | None = None) -> tuple[Path, Registry]:
        root = tmp_path / "vault"
        (root / "artifacts").mkdir(parents=True)
        (root / "artifacts" / "artifacts.yaml").write_text("layout_version: 1\n")
        ks = kinds if kinds is not None else _default_kinds()
        for kd in ks:
            (root / "artifacts" / kd.dir).mkdir(parents=True, exist_ok=True)
        registry = Registry(ks, root=root)
        return root, registry

    return _make
