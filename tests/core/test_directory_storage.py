"""Tests for the directory-storage kind primitive (s0032 §2).

Coverage:
  - File-kind regression (no change to existing behaviour).
  - Directory-kind creation: non-numbered and numbered variants.
  - discover.iter_artifacts: one-level-deeper walk, dot-prefix exclusion,
    half-authored bundle skip-with-warning (at most once per invocation).
  - core.update on a directory-kind manifest (frontmatter-only; body preserved).
  - Registry validation: three new error cases from §2.1.
  - Fixture kind loaded from disk (tests/fixtures/).
"""

import json
import shutil
from pathlib import Path

import pytest

from artifacts_os import KindDef, Registry, create, get, update
from artifacts_os.core.discover import list_artifacts
from artifacts_os.core.errors import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _widget_kind(*, numbered: bool = False, prefix: str = "") -> KindDef:
    """Non-numbered or numbered directory-storage widget kind for tests."""
    return KindDef(
        name="widget",
        dir="widgets",
        prefix=prefix,
        numbered=numbered,
        storage="directory",
        manifest_name="{slug}.md",
    )


def _write_schema(root: Path, name: str, schema: dict) -> None:
    kind_folder = root / "artifacts" / "kinds" / name
    kind_folder.mkdir(parents=True, exist_ok=True)
    (kind_folder / "kind.json").write_text(json.dumps(schema), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. File-kind regression — existing kinds keep working unchanged
# ---------------------------------------------------------------------------

def test_file_kind_task_creation_unchanged(make_vault) -> None:
    root, registry = make_vault()
    a = create(registry, "task", "Fix Bug")
    assert a.path.parent == root / "artifacts" / "tasks"
    assert a.path.suffix == ".md"
    assert a.id == "t0001"
    assert a.name == "fix-bug"


def test_file_kind_agent_creation_unchanged(make_vault) -> None:
    root, registry = make_vault()
    a = create(registry, "agent", "researcher")
    assert a.path == root / "artifacts" / "agents" / "researcher.md"
    assert a.id == "researcher"


def test_file_kind_discovery_unchanged(make_vault) -> None:
    _, registry = make_vault()
    create(registry, "task", "First")
    create(registry, "task", "Second")
    results = list_artifacts(registry, "task")
    assert len(results) == 2


def test_file_kind_defaults(make_vault) -> None:
    """KindDef defaults: storage='file', manifest_name='{slug}.md'."""
    _, registry = make_vault()
    kd = registry.get("task")
    assert kd.storage == "file"
    assert kd.manifest_name == "{slug}.md"


# ---------------------------------------------------------------------------
# 2. Directory-kind creation
# ---------------------------------------------------------------------------

def test_create_directory_kind_non_numbered(make_vault) -> None:
    root, registry = make_vault(kinds=[_widget_kind()])
    a = create(registry, "widget", "My Widget")
    bundle_dir = root / "artifacts" / "widgets" / "my-widget"
    manifest_path = bundle_dir / "my-widget.md"
    # Bundle directory and manifest must both exist.
    assert bundle_dir.is_dir()
    assert manifest_path.is_file()
    # Artifact.path must be the manifest file (not the bundle dir).
    assert a.path == manifest_path
    assert a.id == "my-widget"
    assert a.name == "my-widget"


def test_create_directory_kind_numbered(make_vault) -> None:
    root, registry = make_vault(kinds=[_widget_kind(numbered=True, prefix="w")])
    a = create(registry, "widget", "First Widget")
    bundle_dir = root / "artifacts" / "widgets" / "w0001-first-widget"
    manifest_path = bundle_dir / "first-widget.md"
    assert bundle_dir.is_dir()
    assert manifest_path.is_file()
    assert a.path == manifest_path
    assert a.id == "w0001"


def test_create_directory_kind_numbered_increments(make_vault) -> None:
    root, registry = make_vault(kinds=[_widget_kind(numbered=True, prefix="w")])
    create(registry, "widget", "Alpha")
    b = create(registry, "widget", "Beta")
    assert b.id == "w0002"
    assert (root / "artifacts" / "widgets" / "w0002-beta").is_dir()


def test_create_directory_kind_collision_raises(make_vault) -> None:
    _, registry = make_vault(kinds=[_widget_kind()])
    create(registry, "widget", "Duplicate Slug")
    with pytest.raises(FileExistsError):
        create(registry, "widget", "Duplicate Slug")


def test_create_directory_kind_body_written(make_vault) -> None:
    root, registry = make_vault(kinds=[_widget_kind()])
    create(registry, "widget", "Bodied", body="Hello from body.")
    manifest = root / "artifacts" / "widgets" / "bodied" / "bodied.md"
    content = manifest.read_text(encoding="utf-8")
    assert "Hello from body." in content


# ---------------------------------------------------------------------------
# 3. Discovery: iter_artifacts one-level-deeper walk
# ---------------------------------------------------------------------------

def test_discovery_finds_directory_kind_artifacts(make_vault) -> None:
    root, registry = make_vault(kinds=[_widget_kind()])
    a1 = create(registry, "widget", "Alpha")
    a2 = create(registry, "widget", "Beta")
    results = list_artifacts(registry, "widget")
    paths = {r.path for r in results}
    assert a1.path in paths
    assert a2.path in paths
    assert len(results) == 2


def test_discovery_excludes_dot_prefixed_bundle_dirs(make_vault) -> None:
    root, registry = make_vault(kinds=[_widget_kind()])
    create(registry, "widget", "Visible")
    # Simulate .active/ or any dot-prefixed bundle dir.
    dot_dir = root / "artifacts" / "widgets" / ".active"
    dot_dir.mkdir()
    (dot_dir / "active.md").write_text(
        "---\nkind: widget\nid: active\nname: active\n---\n",
        encoding="utf-8",
    )
    results = list_artifacts(registry, "widget")
    assert len(results) == 1
    assert results[0].name == "visible"


def test_discovery_skips_half_authored_bundle_with_warning(
    make_vault, capsys
) -> None:
    root, registry = make_vault(kinds=[_widget_kind()])
    create(registry, "widget", "Present")
    # Half-authored bundle: directory exists but manifest is missing.
    half = root / "artifacts" / "widgets" / "no-manifest"
    half.mkdir()
    results = list_artifacts(registry, "widget")
    assert len(results) == 1
    assert results[0].name == "present"
    captured = capsys.readouterr()
    assert "no-manifest" in captured.err


def test_discovery_warns_at_most_once_per_list_invocation(
    make_vault, capsys
) -> None:
    root, registry = make_vault(kinds=[_widget_kind()])
    # Three bundles all missing their manifests.
    for name in ("aaa", "bbb", "ccc"):
        (root / "artifacts" / "widgets" / name).mkdir()
    list_artifacts(registry, "widget")
    captured = capsys.readouterr()
    warning_lines = [
        line for line in captured.err.splitlines() if "missing manifest" in line
    ]
    assert len(warning_lines) == 1


# ---------------------------------------------------------------------------
# 4. core.update on a directory-kind manifest
# ---------------------------------------------------------------------------

def test_update_directory_kind_manifest_frontmatter(make_vault) -> None:
    _, registry = make_vault(kinds=[_widget_kind()])
    create(registry, "widget", "Updatable")
    updated = update(registry, "updatable", fields={"color": "blue"})
    assert updated.frontmatter.get("color") == "blue"


def test_update_directory_kind_manifest_preserves_body(make_vault) -> None:
    _, registry = make_vault(kinds=[_widget_kind()])
    create(registry, "widget", "Updatable", body="Original body text.")
    updated = update(registry, "updatable", fields={"color": "red"})
    assert "Original body text." in updated.body


# ---------------------------------------------------------------------------
# 5. Registry validation — three new §2.1 error cases
# ---------------------------------------------------------------------------

def test_registry_unknown_x_storage_raises(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "artifacts.yaml").write_text("layout_version: 1\n", encoding="utf-8")
    _write_schema(root, "bad", {"x-dir": "bads", "x-storage": "blob"})
    with pytest.raises(ValidationError, match="unknown 'x-storage'"):
        Registry([], root=root)


def test_registry_manifest_name_on_file_kind_raises(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "artifacts.yaml").write_text("layout_version: 1\n", encoding="utf-8")
    _write_schema(
        root,
        "bad",
        {"x-dir": "bads", "x-storage": "file", "x-manifest-name": "{slug}.md"},
    )
    with pytest.raises(ValidationError, match="x-manifest-name"):
        Registry([], root=root)


def test_registry_unknown_template_token_raises(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    (root / "artifacts.yaml").write_text("layout_version: 1\n", encoding="utf-8")
    _write_schema(
        root,
        "bad",
        {
            "x-dir": "bads",
            "x-storage": "directory",
            "x-manifest-name": "{slug}-{version}.md",
        },
    )
    with pytest.raises(ValidationError, match="unknown token"):
        Registry([], root=root)


# ---------------------------------------------------------------------------
# 6. Fixture kind loaded from disk (tests/fixtures/kinds/widget/)
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_widget_kind_loads_from_fixture(tmp_path: Path) -> None:
    """Registry can load the widget kind from tests/fixtures/kinds/widget/."""
    root = tmp_path / "vault"
    root.mkdir()
    (root / "artifacts.yaml").write_text("layout_version: 1\n", encoding="utf-8")
    # Copy fixture kind into the test vault.
    dest = root / "artifacts" / "kinds" / "widget"
    shutil.copytree(_FIXTURES_DIR / "kinds" / "widget", dest)
    (root / "artifacts" / "widgets").mkdir(parents=True, exist_ok=True)

    registry = Registry([], root=root)
    kd = registry.get("widget")
    assert kd.storage == "directory"
    assert kd.manifest_name == "{slug}.md"
    assert kd.numbered is False


# ---------------------------------------------------------------------------
# 7. resolve / get work for directory-kind artifacts
# ---------------------------------------------------------------------------

def test_get_directory_kind_artifact(make_vault) -> None:
    _, registry = make_vault(kinds=[_widget_kind()])
    create(registry, "widget", "Findable", body="Hello from get.")
    artifact = get(registry, "findable")
    assert artifact.name == "findable"
    assert "Hello from get." in artifact.body


def test_resolve_partial_query_directory_kind(make_vault) -> None:
    _, registry = make_vault(kinds=[_widget_kind()])
    create(registry, "widget", "Unique Slug Widget")
    artifact = get(registry, "unique")
    assert artifact.name == "unique-slug-widget"
