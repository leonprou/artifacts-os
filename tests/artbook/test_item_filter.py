"""Tests for item-level filtering in book pull (t0162).

Covers:
  - filter_entries_by_items — flat and recurse modes
  - pull_book with preselected entries
  - CLI _run_pull with items argument
"""

from __future__ import annotations

from pathlib import Path

import pytest

from artifacts_os.artbook.manifest import Book
from artifacts_os.artbook.placement import filter_entries_by_items, _select_files
from artifacts_os.artbook.pull import pull_book


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _flat_entries(tmp_path: Path, names: list[str]) -> list[tuple[Path, Path]]:
    """Create flat .md files under tmp_path/src/ and return (abs, rel) entries."""
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    entries = []
    for name in names:
        f = src / name
        f.write_text(f"# {name}")
        entries.append((f, Path(name)))
    return entries


def _recurse_entries(
    tmp_path: Path, units: dict[str, list[str]]
) -> list[tuple[Path, Path]]:
    """Create folder-of-folders layout and return (abs, rel) entries."""
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    entries = []
    for unit, files in units.items():
        unit_dir = src / unit
        unit_dir.mkdir(exist_ok=True)
        for fname in files:
            f = unit_dir / fname
            f.write_text(f"# {fname}")
            entries.append((f, Path(unit) / fname))
    return entries


# ---------------------------------------------------------------------------
# filter_entries_by_items — flat mode
# ---------------------------------------------------------------------------


def test_filter_flat_by_stem(tmp_path: Path) -> None:
    entries = _flat_entries(tmp_path, ["architect.md", "developer.md"])
    filtered, unmatched, available = filter_entries_by_items(
        entries, ["architect"], recurse=False
    )
    assert len(filtered) == 1
    assert filtered[0][1] == Path("architect.md")
    assert unmatched == []
    assert "architect" in available


def test_filter_flat_by_full_filename(tmp_path: Path) -> None:
    entries = _flat_entries(tmp_path, ["architect.md", "developer.md"])
    filtered, unmatched, available = filter_entries_by_items(
        entries, ["architect.md"], recurse=False
    )
    assert len(filtered) == 1
    assert filtered[0][1] == Path("architect.md")
    assert unmatched == []


def test_filter_flat_multiple_items(tmp_path: Path) -> None:
    entries = _flat_entries(tmp_path, ["architect.md", "developer.md", "researcher.md"])
    filtered, unmatched, available = filter_entries_by_items(
        entries, ["architect", "developer"], recurse=False
    )
    names = {str(rel) for _src, rel in filtered}
    assert names == {"architect.md", "developer.md"}
    assert unmatched == []


def test_filter_flat_unmatched_item(tmp_path: Path) -> None:
    entries = _flat_entries(tmp_path, ["architect.md", "developer.md"])
    filtered, unmatched, available = filter_entries_by_items(
        entries, ["architect", "nonexistent"], recurse=False
    )
    assert len(filtered) == 1  # architect matched
    assert unmatched == ["nonexistent"]
    assert sorted(available) == ["architect", "developer"]


def test_filter_flat_empty_items_returns_all(tmp_path: Path) -> None:
    entries = _flat_entries(tmp_path, ["architect.md", "developer.md"])
    filtered, unmatched, available = filter_entries_by_items(
        entries, [], recurse=False
    )
    assert filtered == entries
    assert unmatched == []


def test_filter_flat_all_unmatched(tmp_path: Path) -> None:
    entries = _flat_entries(tmp_path, ["architect.md"])
    filtered, unmatched, available = filter_entries_by_items(
        entries, ["ghost"], recurse=False
    )
    assert filtered == []
    assert unmatched == ["ghost"]


def test_filter_flat_stem_and_extension_same_match(tmp_path: Path) -> None:
    """architect and architect.md both match the same file."""
    entries = _flat_entries(tmp_path, ["architect.md"])
    filtered_stem, _, _ = filter_entries_by_items(entries, ["architect"], recurse=False)
    filtered_full, _, _ = filter_entries_by_items(entries, ["architect.md"], recurse=False)
    assert len(filtered_stem) == 1
    assert len(filtered_full) == 1
    assert filtered_stem[0][1] == filtered_full[0][1]


def test_filter_flat_preserves_original_order(tmp_path: Path) -> None:
    """Filtered list preserves the order of the original entries list."""
    entries = _flat_entries(tmp_path, ["alpha.md", "beta.md", "gamma.md"])
    filtered, _, _ = filter_entries_by_items(
        entries, ["gamma", "alpha"], recurse=False
    )
    rels = [str(r) for _, r in filtered]
    assert rels == ["alpha.md", "gamma.md"]


# ---------------------------------------------------------------------------
# filter_entries_by_items — recurse mode
# ---------------------------------------------------------------------------


def test_filter_recurse_by_unit_name(tmp_path: Path) -> None:
    entries = _recurse_entries(tmp_path, {
        "artifacts-os": ["SKILL.md", "__init__.py"],
        "release-changelog": ["SKILL.md", "__init__.py"],
    })
    filtered, unmatched, available = filter_entries_by_items(
        entries, ["artifacts-os"], recurse=True
    )
    units = {rel.parts[0] for _src, rel in filtered}
    assert units == {"artifacts-os"}
    assert unmatched == []
    assert "artifacts-os" in available
    assert "release-changelog" in available


def test_filter_recurse_multiple_units(tmp_path: Path) -> None:
    entries = _recurse_entries(tmp_path, {
        "task": ["kind.json", "ARTIFACT.md"],
        "note": ["kind.json", "ARTIFACT.md"],
        "spec": ["kind.json", "ARTIFACT.md"],
    })
    filtered, unmatched, available = filter_entries_by_items(
        entries, ["task", "note"], recurse=True
    )
    units = {rel.parts[0] for _src, rel in filtered}
    assert units == {"task", "note"}
    assert unmatched == []


def test_filter_recurse_unmatched_unit(tmp_path: Path) -> None:
    entries = _recurse_entries(tmp_path, {
        "artifacts-os": ["SKILL.md"],
    })
    filtered, unmatched, available = filter_entries_by_items(
        entries, ["artifacts-os", "nonexistent"], recurse=True
    )
    assert len(filtered) == 1
    assert unmatched == ["nonexistent"]


def test_filter_recurse_empty_items_returns_all(tmp_path: Path) -> None:
    entries = _recurse_entries(tmp_path, {
        "unit-a": ["a.md"],
        "unit-b": ["b.md"],
    })
    filtered, unmatched, available = filter_entries_by_items(
        entries, [], recurse=True
    )
    assert filtered == entries
    assert unmatched == []


def test_filter_recurse_all_files_in_unit_included(tmp_path: Path) -> None:
    """All files in a matched unit are included."""
    entries = _recurse_entries(tmp_path, {
        "skill-a": ["SKILL.md", "__init__.py", "helper.py"],
        "skill-b": ["SKILL.md"],
    })
    filtered, _, _ = filter_entries_by_items(
        entries, ["skill-a"], recurse=True
    )
    rels = [str(rel) for _src, rel in filtered]
    assert "skill-a/SKILL.md" in rels
    assert "skill-a/__init__.py" in rels
    assert "skill-a/helper.py" in rels
    assert all(rel.startswith("skill-a/") for rel in rels)


# ---------------------------------------------------------------------------
# pull_book with preselected — integration
# ---------------------------------------------------------------------------


def test_pull_book_preselected_flat(tmp_path: Path) -> None:
    """pull_book with preselected entries writes only the filtered subset."""
    clone_root = tmp_path / "clone"
    agents = clone_root / "agents"
    agents.mkdir(parents=True)
    (agents / "architect.md").write_text("# Arch")
    (agents / "developer.md").write_text("# Dev")

    vault = tmp_path / "vault"
    vault.mkdir()
    book = Book(name="agents", src="agents/", dest=".claude/agents/")

    # Preselect only architect
    entries = _select_files(agents, book)
    preselected, _, _ = filter_entries_by_items(entries, ["architect"], recurse=False)

    report = pull_book(book, clone_root, vault, preselected=preselected)
    dest = vault / ".claude" / "agents"
    assert (dest / "architect.md").is_file()
    assert not (dest / "developer.md").exists()
    assert len(report.written) == 1


def test_pull_book_preselected_recurse(tmp_path: Path) -> None:
    """pull_book with preselected recurse entries writes only matched unit."""
    clone_root = tmp_path / "clone"
    skills = clone_root / "skills"
    (skills / "artifacts-os").mkdir(parents=True)
    (skills / "artifacts-os" / "SKILL.md").write_text("# aos")
    (skills / "release-changelog").mkdir()
    (skills / "release-changelog" / "SKILL.md").write_text("# rc")

    vault = tmp_path / "vault"
    vault.mkdir()
    book = Book(name="skills", src="skills/", dest=".claude/skills/", recurse=True)

    entries = _select_files(skills, book)
    preselected, _, _ = filter_entries_by_items(entries, ["artifacts-os"], recurse=True)

    report = pull_book(book, clone_root, vault, preselected=preselected)
    dest = vault / ".claude" / "skills"
    assert (dest / "artifacts-os" / "SKILL.md").is_file()
    assert not (dest / "release-changelog").exists()
    assert len(report.written) == 1


# ---------------------------------------------------------------------------
# CLI integration — _run_pull with items
# ---------------------------------------------------------------------------


def _make_flat_distro(root: Path) -> Path:
    """Minimal distro with a flat 'agents' book."""
    import subprocess, yaml  # noqa: E401

    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--initial-branch", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=root, check=True, capture_output=True)

    agents = root / "agents"
    agents.mkdir()
    (agents / "architect.md").write_text("# Arch")
    (agents / "developer.md").write_text("# Dev")

    (root / "artbook.yaml").write_text(yaml.dump({
        "version": 1,
        "distro": {"name": "test-distro"},
        "books": [{"name": "agents", "src": "agents/", "dest": ".claude/agents/"}],
    }))
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
    return root


def _make_recurse_distro(root: Path) -> Path:
    """Minimal distro with a recurse 'skills' book."""
    import subprocess, yaml  # noqa: E401

    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--initial-branch", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=root, check=True, capture_output=True)

    (root / "skills" / "artifacts-os").mkdir(parents=True)
    (root / "skills" / "artifacts-os" / "SKILL.md").write_text("# aos")
    (root / "skills" / "task").mkdir()
    (root / "skills" / "task" / "SKILL.md").write_text("# task")
    (root / "skills" / "note").mkdir()
    (root / "skills" / "note" / "SKILL.md").write_text("# note")

    (root / "artbook.yaml").write_text(yaml.dump({
        "version": 1,
        "distro": {"name": "test-distro"},
        "books": [{"name": "skills", "src": "skills/", "dest": ".claude/skills/", "recurse": True}],
    }))
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
    return root


def _make_vault(root: Path) -> tuple[Path, dict]:
    root.mkdir(parents=True, exist_ok=True)
    (root / "artifacts.yaml").write_text(
        "layout_version: 1\nproject:\n  name: test\n"
    )
    return root, {}


def _args(**kwargs):
    """Build a minimal args namespace for _run_pull."""
    import argparse
    defaults = {
        "name": "agents",
        "items": [],
        "dry_run": False,
        "json_out": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestRunPullItems:
    def test_no_items_pulls_all(self, tmp_path: Path) -> None:
        """Req 1: no items → all files pulled (regression)."""
        from artifacts_os.cli.commands.book import _run_pull

        distro = _make_flat_distro(tmp_path / "distro")
        vault, raw = _make_vault(tmp_path / "vault")
        raw = {"artbook": {"distro_url": str(distro)}}

        args = _args(name="agents", items=[])
        rc = _run_pull(args, vault, raw)
        assert rc == 0
        dest = vault / ".claude" / "agents"
        assert (dest / "architect.md").is_file()
        assert (dest / "developer.md").is_file()

    def test_items_filter_flat_by_stem(self, tmp_path: Path) -> None:
        """Req 2-3: items=['architect'] writes only architect.md."""
        from artifacts_os.cli.commands.book import _run_pull

        distro = _make_flat_distro(tmp_path / "distro")
        vault, raw = _make_vault(tmp_path / "vault")
        raw = {"artbook": {"distro_url": str(distro)}}

        args = _args(name="agents", items=["architect"])
        rc = _run_pull(args, vault, raw)
        assert rc == 0
        dest = vault / ".claude" / "agents"
        assert (dest / "architect.md").is_file()
        assert not (dest / "developer.md").exists()

    def test_items_filter_flat_by_extension(self, tmp_path: Path) -> None:
        """Req 3: architect.md (with extension) works the same as without."""
        from artifacts_os.cli.commands.book import _run_pull

        distro = _make_flat_distro(tmp_path / "distro")
        vault, raw = _make_vault(tmp_path / "vault")
        raw = {"artbook": {"distro_url": str(distro)}}

        args = _args(name="agents", items=["architect.md"])
        rc = _run_pull(args, vault, raw)
        assert rc == 0
        dest = vault / ".claude" / "agents"
        assert (dest / "architect.md").is_file()
        assert not (dest / "developer.md").exists()

    def test_items_filter_recurse_unit(self, tmp_path: Path) -> None:
        """Req 4: items=['artifacts-os'] pulls only the artifacts-os/ subtree."""
        from artifacts_os.cli.commands.book import _run_pull

        distro = _make_recurse_distro(tmp_path / "distro")
        vault, raw = _make_vault(tmp_path / "vault")
        raw = {"artbook": {"distro_url": str(distro)}}

        args = _args(name="skills", items=["artifacts-os"])
        rc = _run_pull(args, vault, raw)
        assert rc == 0
        dest = vault / ".claude" / "skills"
        assert (dest / "artifacts-os" / "SKILL.md").is_file()
        assert not (dest / "task").exists()
        assert not (dest / "note").exists()

    def test_items_filter_recurse_multiple_units(self, tmp_path: Path) -> None:
        """Req 4: items=['task', 'note'] writes task/ and note/ units."""
        from artifacts_os.cli.commands.book import _run_pull

        distro = _make_recurse_distro(tmp_path / "distro")
        vault, raw = _make_vault(tmp_path / "vault")
        raw = {"artbook": {"distro_url": str(distro)}}

        args = _args(name="skills", items=["task", "note"])
        rc = _run_pull(args, vault, raw)
        assert rc == 0
        dest = vault / ".claude" / "skills"
        assert (dest / "task" / "SKILL.md").is_file()
        assert (dest / "note" / "SKILL.md").is_file()
        assert not (dest / "artifacts-os").exists()

    def test_unknown_item_errors_before_writing(self, tmp_path: Path) -> None:
        """Req 5: unknown item exits with error, writes nothing."""
        from artifacts_os.cli.commands.book import _run_pull

        distro = _make_flat_distro(tmp_path / "distro")
        vault, raw = _make_vault(tmp_path / "vault")
        raw = {"artbook": {"distro_url": str(distro)}}

        args = _args(name="agents", items=["nonexistent"])
        rc = _run_pull(args, vault, raw)
        assert rc == 1
        # Nothing written
        dest = vault / ".claude" / "agents"
        assert not dest.exists()

    def test_mixed_valid_invalid_items_errors(self, tmp_path: Path) -> None:
        """Req 5: even if one item is valid, any unmatched item aborts with no writes."""
        from artifacts_os.cli.commands.book import _run_pull

        distro = _make_flat_distro(tmp_path / "distro")
        vault, raw = _make_vault(tmp_path / "vault")
        raw = {"artbook": {"distro_url": str(distro)}}

        args = _args(name="agents", items=["architect", "nonexistent"])
        rc = _run_pull(args, vault, raw)
        assert rc == 1
        dest = vault / ".claude" / "agents"
        assert not dest.exists()

    def test_dry_run_with_items(self, tmp_path: Path) -> None:
        """Req 6: --dry-run respects item filter (no files written, correct plan)."""
        from artifacts_os.cli.commands.book import _run_pull

        distro = _make_flat_distro(tmp_path / "distro")
        vault, raw = _make_vault(tmp_path / "vault")
        raw = {"artbook": {"distro_url": str(distro)}}

        args = _args(name="agents", items=["architect"], dry_run=True)
        rc = _run_pull(args, vault, raw)
        assert rc == 0
        # Nothing actually written
        dest = vault / ".claude" / "agents"
        assert not dest.exists()

    def test_json_with_items(self, tmp_path: Path, capsys) -> None:
        """Req 7: --json respects item filter — only records for filtered files."""
        import json
        from artifacts_os.cli.commands.book import _run_pull

        distro = _make_flat_distro(tmp_path / "distro")
        vault, raw = _make_vault(tmp_path / "vault")
        raw = {"artbook": {"distro_url": str(distro)}}

        args = _args(name="agents", items=["architect"], json_out=True)
        rc = _run_pull(args, vault, raw)
        assert rc == 0

        captured = capsys.readouterr()
        lines = [l for l in captured.out.strip().splitlines() if l]
        records = [json.loads(l) for l in lines]
        # Filter out the summary line
        file_records = [r for r in records if "action" in r]
        destinations = [r["destination"] for r in file_records]
        assert len(file_records) == 1
        assert any("architect.md" in d for d in destinations)
        assert all("developer.md" not in d for d in destinations)
