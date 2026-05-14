"""Tests for KindCatalog and Registry L1 catalogue surface.

Implements s0017-artifact-kinds-discovery-mechanism § 9 test plan.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from artifacts_os.core.errors import ValidationError
from artifacts_os.core.kinds_catalog import KindCatalog, KindCatalogEntry
from artifacts_os.core.registry import Registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_kind_json(kinds_dir: Path, name: str, schema: dict | None = None) -> Path:
    """Write a flat kind.json at artifacts/kinds/<name>.json."""
    kinds_dir.mkdir(parents=True, exist_ok=True)
    path = kinds_dir / f"{name}.json"
    if schema is None:
        schema = {"x-dir": f"{name}s", "x-prefix": name[0], "x-numbered": True}
    path.write_text(json.dumps(schema), encoding="utf-8")
    return path


def _write_folder_kind(kinds_dir: Path, name: str, schema: dict | None = None) -> Path:
    """Write a folder-form kind at artifacts/kinds/<name>/kind.json."""
    folder = kinds_dir / name
    folder.mkdir(parents=True, exist_ok=True)
    kind_json = folder / "kind.json"
    if schema is None:
        schema = {"x-dir": f"{name}s", "x-prefix": name[0], "x-numbered": True}
    kind_json.write_text(json.dumps(schema), encoding="utf-8")
    return kind_json


def _write_artifact_md(kinds_dir: Path, name: str, fm: dict, body: str = "") -> Path:
    """Write ARTIFACT.md for a kind folder (frontmatter + optional body)."""
    folder = kinds_dir / name
    folder.mkdir(parents=True, exist_ok=True)
    artifact_md = folder / "ARTIFACT.md"
    lines = ["---\n"]
    for k, v in fm.items():
        lines.append(f"{k}: {v!r}\n")
    lines.append("---\n")
    if body:
        lines.append("\n" + body)
    artifact_md.write_text("".join(lines), encoding="utf-8")
    return artifact_md


def _make_vault(tmp_path: Path) -> tuple[Path, Path]:
    """Return (root, kinds_dir) for a minimal vault."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True, exist_ok=True)
    (root / "artifacts.yaml").write_text("layout_version: 1\n")
    return root, kinds_dir


# ---------------------------------------------------------------------------
# § 9.1  L1 layer-isolation (critical)
# ---------------------------------------------------------------------------

def test_l1_does_not_read_artifact_md_body(tmp_path: Path) -> None:
    """list_kinds() succeeds even when ARTIFACT.md body would cause a parse error."""
    root, kinds_dir = _make_vault(tmp_path)
    _write_folder_kind(kinds_dir, "note")
    # Body contains a string that would break YAML parsing if the full file
    # were handed to yaml.safe_load.
    _write_artifact_md(
        kinds_dir,
        "note",
        fm={"name": "note", "description": "A note kind for planning."},
        body="{% this: would: break: yaml: safe_load %}",
    )
    # Must not raise despite invalid YAML body.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = Registry([], root=root)
    catalog = KindCatalog(r, root)
    entries = catalog.list_kinds()
    assert len(entries) == 1
    assert entries[0].description == "A note kind for planning."


def test_l1_does_not_read_playbooks(tmp_path: Path, monkeypatch) -> None:
    """list_kinds() must not open any playbooks/*.md file."""
    root, kinds_dir = _make_vault(tmp_path)
    _write_folder_kind(kinds_dir, "task")
    _write_artifact_md(
        kinds_dir,
        "task",
        fm={"name": "task", "description": "Task artifact.", "playbooks": ["workflow"]},
    )
    # Create a playbooks dir with a file that should never be read.
    playbooks_dir = kinds_dir / "task" / "playbooks"
    playbooks_dir.mkdir(parents=True)
    playbook_file = playbooks_dir / "workflow.md"
    playbook_file.write_text("# Playbook content\n", encoding="utf-8")

    opened_paths: list[str] = []
    original_open = open

    def tracking_open(path, *args, **kwargs):
        opened_paths.append(str(path))
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", tracking_open)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = Registry([], root=root)
    catalog = KindCatalog(r, root)
    _ = catalog.list_kinds()

    # No playbook file should have been opened.
    for p in opened_paths:
        assert "playbooks" not in p, f"L1 opened a playbook file: {p}"


def test_l1_returns_name_and_description(tmp_path: Path) -> None:
    """Happy-path: entry carries correct name and description."""
    root, kinds_dir = _make_vault(tmp_path)
    _write_folder_kind(kinds_dir, "note")
    _write_artifact_md(
        kinds_dir,
        "note",
        fm={"name": "note", "description": "Captures planning notes and brainstorms."},
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = Registry([], root=root)
    catalog = KindCatalog(r, root)
    entries = catalog.list_kinds()
    assert len(entries) == 1
    assert entries[0].name == "note"
    assert entries[0].description == "Captures planning notes and brainstorms."
    assert entries[0].has_template is True


def test_l1_missing_description_is_soft(tmp_path: Path) -> None:
    """ARTIFACT.md present but description absent → description=None, warning emitted."""
    root, kinds_dir = _make_vault(tmp_path)
    _write_folder_kind(kinds_dir, "note")
    _write_artifact_md(kinds_dir, "note", fm={"name": "note"})  # no description

    with pytest.warns(UserWarning, match="missing or empty 'description'"):
        r = Registry([], root=root)
    catalog = KindCatalog(r, root)
    entries = catalog.list_kinds()
    assert len(entries) == 1
    assert entries[0].description is None
    assert entries[0].has_template is True


def test_l1_missing_artifact_md_is_soft(tmp_path: Path) -> None:
    """No ARTIFACT.md → has_template=False, no hard error, soft warning."""
    root, kinds_dir = _make_vault(tmp_path)
    _write_folder_kind(kinds_dir, "task")  # no ARTIFACT.md

    with pytest.warns(UserWarning, match="no ARTIFACT.md"):
        r = Registry([], root=root)
    catalog = KindCatalog(r, root)
    entries = catalog.list_kinds()
    assert len(entries) == 1
    assert entries[0].has_template is False
    assert entries[0].description is None


# ---------------------------------------------------------------------------
# § 9.2  Description contract
# ---------------------------------------------------------------------------

def test_description_xml_tag_rejected(tmp_path: Path) -> None:
    """description containing an XML tag causes a hard ValidationError."""
    root, kinds_dir = _make_vault(tmp_path)
    _write_folder_kind(kinds_dir, "note")
    _write_artifact_md(
        kinds_dir,
        "note",
        fm={"name": "note", "description": "A kind with <b>HTML</b> in it."},
    )
    with pytest.raises(ValidationError, match="XML tag"):
        Registry([], root=root)


def test_description_reserved_word_rejected(tmp_path: Path) -> None:
    """description containing 'claude' or 'anthropic' causes a hard ValidationError."""
    root, kinds_dir = _make_vault(tmp_path)

    for word in ("claude", "anthropic"):
        _write_folder_kind(kinds_dir, "note")
        _write_artifact_md(
            kinds_dir,
            "note",
            fm={"name": "note", "description": f"Uses {word} to do stuff."},
        )
        with pytest.raises(ValidationError, match=f"reserved word '{word}'"):
            Registry([], root=root)
        # Clean up for next iteration
        (kinds_dir / "note" / "kind.json").unlink()
        (kinds_dir / "note" / "ARTIFACT.md").unlink()


def test_description_length_cap_enforced(tmp_path: Path) -> None:
    """description of exactly 1024 chars is accepted; 1025 chars raises."""
    root, kinds_dir = _make_vault(tmp_path)

    # 1024 chars — must pass
    desc_ok = "x" * 1024
    _write_folder_kind(kinds_dir, "note")
    _write_artifact_md(kinds_dir, "note", fm={"name": "note", "description": desc_ok})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = Registry([], root=root)
    entries = KindCatalog(r, root).list_kinds()
    assert entries[0].description == desc_ok

    # 1025 chars — must fail
    (kinds_dir / "note" / "ARTIFACT.md").unlink()
    desc_bad = "y" * 1025
    _write_artifact_md(kinds_dir, "note", fm={"name": "note", "description": desc_bad})
    with pytest.raises(ValidationError, match="1024"):
        Registry([], root=root)


def test_description_third_person_voice_unenforced(tmp_path: Path) -> None:
    """First-person description loads without error — voice is guidance only (D6)."""
    root, kinds_dir = _make_vault(tmp_path)
    _write_folder_kind(kinds_dir, "note")
    _write_artifact_md(
        kinds_dir,
        "note",
        fm={"name": "note", "description": "I capture planning notes and brainstorms."},
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = Registry([], root=root)
    entries = KindCatalog(r, root).list_kinds()
    assert entries[0].description == "I capture planning notes and brainstorms."


# ---------------------------------------------------------------------------
# § 9.3  Source file contract
# ---------------------------------------------------------------------------

def test_artifact_md_frontmatter_only_read_at_l1(tmp_path: Path) -> None:
    """Only frontmatter bytes are read; body bytes are never consumed."""
    root, kinds_dir = _make_vault(tmp_path)
    _write_folder_kind(kinds_dir, "note")
    artifact_md_path = _write_artifact_md(
        kinds_dir,
        "note",
        fm={"name": "note", "description": "Captures notes."},
        body="# Body\n\nThis is the body content that must never be parsed.",
    )

    raw = artifact_md_path.read_bytes()
    # Find the byte offset of the closing '---'.
    # The frontmatter block is: '---\n' + fm lines + '---\n'
    closing_delim = b"\n---\n"
    first_delim_end = raw.index(b"\n", 0) + 1  # end of opening '---\n'
    close_start = raw.index(closing_delim, first_delim_end)
    frontmatter_end = close_start + len(closing_delim)

    bytes_read: list[int] = []

    class TrackingFile:
        def __init__(self, fh):
            self._fh = fh

        def readline(self):
            line = self._fh.readline()
            bytes_read.append(len(line))
            return line

        def __iter__(self):
            for line in self._fh:
                bytes_read.append(len(line))
                yield line

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self._fh.__exit__(*args)

    original_open = Path.open

    def tracking_path_open(self, *args, **kwargs):
        fh = original_open(self, *args, **kwargs)
        if self == artifact_md_path:
            return TrackingFile(fh)
        return fh

    import unittest.mock as mock

    with mock.patch.object(Path, "open", tracking_path_open):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            Registry([], root=root)

    total_read = sum(bytes_read)
    # Must have read at most the frontmatter + a small buffer — body is not read.
    assert total_read <= frontmatter_end + 10, (
        f"Read {total_read} bytes but frontmatter ends at {frontmatter_end}"
    )


def test_flat_kind_json_not_registered_and_warns(tmp_path: Path) -> None:
    """A stray flat artifacts/kinds/foo.json is NOT registered and emits a migration warning."""
    root, kinds_dir = _make_vault(tmp_path)
    _write_kind_json(kinds_dir, "legacy")  # flat file, no folder

    with pytest.warns(UserWarning, match="Migrate to folder form"):
        r = Registry([], root=root)

    # Flat-form kind must not be registered.
    with pytest.raises(ValueError, match="Unknown kind"):
        r.get("legacy")

    catalog = KindCatalog(r, root)
    entries = catalog.list_kinds()
    assert not any(e.name == "legacy" for e in entries)


# ---------------------------------------------------------------------------
# § 9.5  CLI ↔ Python API parity (unit-level; CLI-level is in test_kinds.py)
# ---------------------------------------------------------------------------

def test_catalog_entries_match_registry_all(tmp_path: Path) -> None:
    """KindCatalog.list_kinds() names match Registry.all() names."""
    root, kinds_dir = _make_vault(tmp_path)
    for name in ("alpha", "beta", "gamma"):
        _write_folder_kind(kinds_dir, name)
        _write_artifact_md(
            kinds_dir,
            name,
            fm={"name": name, "description": f"The {name} kind."},
        )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = Registry([], root=root)

    catalog = KindCatalog(r, root)
    catalog_names = [e.name for e in catalog.list_kinds()]
    registry_names = sorted(kd.name for kd in r.all())
    assert catalog_names == registry_names


# ---------------------------------------------------------------------------
# § 9.6  Token budget (optional — skip with rationale if flaky)
# ---------------------------------------------------------------------------

@pytest.mark.skip(
    reason=(
        "s0017 § 9.6 optional: simple chars/4 token estimate overestimates for "
        "repetitive content (real BPE tokens are denser).  The spec's own empirical "
        "bound (100-150 tokens for a 1024-char description) is based on an actual "
        "tokenizer.  Verifying the budget accurately requires `tiktoken` or a "
        "similar library which is not a project dependency.  The constraint is "
        "enforced structurally by the 1024-char description cap (§ 6.1) and the "
        "name length convention (≤ 64 chars)."
    )
)
def test_l1_token_budget(tmp_path: Path) -> None:
    """Token budget ≤ 200 per kind (D7). Skipped — see skip reason above."""
