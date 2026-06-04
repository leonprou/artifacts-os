from pathlib import Path

from artifacts_os import find_vault_root


def test_found_at_cwd(tmp_path: Path) -> None:
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts.yaml").write_text("")
    assert find_vault_root(tmp_path) == tmp_path.resolve()


def test_found_at_ancestor(tmp_path: Path) -> None:
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts.yaml").write_text("")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_vault_root(nested) == tmp_path.resolve()


def test_not_found(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_vault_root(nested) is None


# ── New tests per s0026 §14.3 ────────────────────────────────────────────────


def test_cwd_at_root(tmp_path: Path) -> None:
    """CWD == <root> — first candidate matches immediately."""
    (tmp_path / "artifacts.yaml").write_text("")
    (tmp_path / "artifacts").mkdir()
    assert find_vault_root(tmp_path) == tmp_path.resolve()


def test_cwd_inside_artifacts_dir(tmp_path: Path) -> None:
    """CWD == <root>/artifacts — walk-up finds marker at parent.

    Before this spec, <root>/artifacts/artifacts.yaml would have matched on
    the <root>/artifacts candidate.  Under the new layout the check is
    <candidate>/artifacts.yaml, so <root>/artifacts does not match and the
    walk continues to <root>.
    """
    (tmp_path / "artifacts.yaml").write_text("")
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    assert find_vault_root(artifacts_dir) == tmp_path.resolve()


def test_cwd_inside_artifacts_specs(tmp_path: Path) -> None:
    """CWD == <root>/artifacts/specs — climbs two levels to find marker."""
    (tmp_path / "artifacts.yaml").write_text("")
    specs_dir = tmp_path / "artifacts" / "specs"
    specs_dir.mkdir(parents=True)
    assert find_vault_root(specs_dir) == tmp_path.resolve()


def test_no_marker_returns_none(tmp_path: Path) -> None:
    """No artifacts.yaml anywhere up the tree — returns None."""
    deep = tmp_path / "x" / "y" / "z"
    deep.mkdir(parents=True)
    assert find_vault_root(deep) is None


def test_find_vault_root_custom_marker(tmp_path: Path) -> None:
    """find_vault_root(marker_filename=...) walks up looking for the custom name.

    Spec: s0034 §6.4 / §11.2.
    """
    (tmp_path / "openstation.yaml").write_text("layout_version: 1\n")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    assert find_vault_root(deep, marker_filename="openstation.yaml") == tmp_path.resolve()


def test_find_vault_root_default_unchanged(tmp_path: Path) -> None:
    """Without the kwarg, find_vault_root behaves identically to before.

    Regression guard for s0034 §11.2.
    """
    (tmp_path / "artifacts.yaml").write_text("")
    assert find_vault_root(tmp_path) == tmp_path.resolve()
    # Custom marker does NOT match artifacts.yaml (different filename).
    assert find_vault_root(tmp_path, marker_filename="openstation.yaml") is None


def test_legacy_layout_only_returns_none(tmp_path: Path) -> None:
    """Legacy <root>/artifacts/artifacts.yaml is NOT recognised (D3 hard cutover).

    Only <root>/artifacts.yaml is the valid marker.  Vaults that have not
    been migrated produce None, directing the user to docs/migration.md.
    """
    legacy_dir = tmp_path / "artifacts"
    legacy_dir.mkdir()
    (legacy_dir / "artifacts.yaml").write_text("")
    # No <root>/artifacts.yaml — find_vault_root must return None
    assert find_vault_root(tmp_path) is None
