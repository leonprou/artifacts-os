from pathlib import Path

from artifacts_os import find_vault_root


def test_found_at_cwd(tmp_path: Path) -> None:
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "artifacts.yaml").write_text("")
    assert find_vault_root(tmp_path) == tmp_path.resolve()


def test_found_at_ancestor(tmp_path: Path) -> None:
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "artifacts.yaml").write_text("")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_vault_root(nested) == tmp_path.resolve()


def test_not_found(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_vault_root(nested) is None
