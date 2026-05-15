"""End-to-end tests for cli/commands/book.py — list, show, pull verbs.

Tests drive the verbs against a fixture distro repo created in tmp_path
via git init, mirroring the artbook conftest pattern.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from artifacts_os.cli import _run


# ---------------------------------------------------------------------------
# Distro repo factory (adapted from tests/artbook/conftest.py)
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def make_distro_repo(
    root: Path,
    *,
    artbook_yaml: dict | None = None,
    agent_files: dict[str, str] | None = None,
) -> Path:
    """Create a minimal distro git repo under *root*."""
    root.mkdir(parents=True, exist_ok=True)
    _git(["git", "init", "--initial-branch", "main"], root)
    _git(["git", "config", "user.email", "test@test.com"], root)
    _git(["git", "config", "user.name", "Test"], root)

    if agent_files:
        for rel_path, content in agent_files.items():
            dest = root / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

    if artbook_yaml is not None:
        (root / "artbook.yaml").write_text(yaml.dump(artbook_yaml), encoding="utf-8")

    _git(["git", "add", "."], root)
    _git(["git", "commit", "--allow-empty", "-m", "init"], root)
    return root


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def distro_repo(tmp_path: Path) -> Path:
    """Minimal distro repo with one 'agents' book (D20 walker mode, v2 schema)."""
    return make_distro_repo(
        tmp_path / "distro",
        artbook_yaml={
            "version": 1,
            "distro": {
                "name": "test-distro",
                "description": "Test distro for CLI tests.",
            },
            "books": [
                {
                    "name": "agents",
                    "src": "agents/",
                    "dest": ".claude/agents/",
                    "description": "Test agents.",
                }
            ],
        },
        agent_files={
            "agents/architect.md": "# Architect\nAgent body.",
            "agents/developer.md": "# Developer\nAgent body.",
            "agents/README.md": "# README",  # excluded by D20
        },
    )


@pytest.fixture
def vault_with_distro(vault: Path, distro_repo: Path, monkeypatch) -> tuple[Path, Path]:
    """A vault with artbook.distro_url pointing to the fixture distro repo."""
    distro_url = str(distro_repo)
    (vault / "artifacts.yaml").write_text(
        f"layout_version: 1\nartbook:\n  distro_url: '{distro_url}'\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(vault)
    return vault, distro_repo


@pytest.fixture
def vault_no_distro(vault: Path, monkeypatch) -> Path:
    """A vault without artbook.distro_url configured."""
    (vault / "artifacts.yaml").write_text(
        "layout_version: 1\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(vault)
    return vault


# ---------------------------------------------------------------------------
# Help / registration
# ---------------------------------------------------------------------------


def test_book_help_shows_three_verbs(vault_with_distro, capsys):
    """`artifacts book --help` exits 0 and lists list/show/pull."""
    with pytest.raises(SystemExit) as exc:
        _run(["book", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "list" in out
    assert "show" in out
    assert "pull" in out


# ---------------------------------------------------------------------------
# book list
# ---------------------------------------------------------------------------


def test_book_list_table(vault_with_distro, capsys):
    """`book list` renders a Rich table and exits 0."""
    code = _run(["book", "list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "agents" in out
    assert "test-distro" in out


def test_book_list_json(vault_with_distro, capsys):
    """`book list --json` outputs a single JSON object (v2: src/dest fields)."""
    code = _run(["book", "list", "--json"])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["distro"]["name"] == "test-distro"
    assert data["distro"]["description"] == "Test distro for CLI tests."
    assert len(data["books"]) == 1
    assert data["books"][0]["name"] == "agents"
    assert data["books"][0]["src"] == "agents/"
    assert data["books"][0]["dest"] == ".claude/agents/"
    assert "type" not in data["books"][0]
    assert "url" in data["distro"]
    assert "sha" in data["distro"]


def test_book_list_no_distro_url(vault_no_distro, capsys):
    """`book list` exits 4 when distro_url is not configured."""
    code = _run(["book", "list"])
    assert code == 4
    err = capsys.readouterr().err
    assert "distro_url" in err


def test_book_list_vault_not_found(tmp_path, monkeypatch, capsys):
    """`book list` exits 3 when not inside a vault."""
    monkeypatch.chdir(tmp_path)
    code = _run(["book", "list"])
    assert code == 3
    err = capsys.readouterr().err
    assert "vault" in err.lower()


# ---------------------------------------------------------------------------
# book show
# ---------------------------------------------------------------------------


def test_book_show_table(vault_with_distro, capsys):
    """`book show agents` renders Source/Destination (no Type) and exits 0."""
    code = _run(["book", "show", "agents"])
    assert code == 0
    out = capsys.readouterr().out
    assert "agents" in out
    # Source and Destination should be shown; no Type line
    assert "Source:" in out
    assert "Destination:" in out
    assert "Type:" not in out
    assert ".claude/agents" in out
    # At least one content file listed (D20 walker, README excluded)
    assert "architect.md" in out
    assert "developer.md" in out
    # README.md excluded by D20
    assert "README.md" not in out


def test_book_show_json(vault_with_distro, capsys):
    """`book show agents --json` outputs a JSON object with src/dest (v2 schema)."""
    code = _run(["book", "show", "agents", "--json"])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["book"]["name"] == "agents"
    assert data["book"]["src"] == "agents/"
    assert data["book"]["dest"] == ".claude/agents/"
    assert "type" not in data["book"]
    # standalone `destination` key removed in v2 (dest lives in book.dest)
    assert "destination" not in data
    assert "contents" in data
    assert "architect.md" in data["contents"]
    assert "developer.md" in data["contents"]
    assert "README.md" not in data["contents"]
    assert "distro" in data
    assert "sha" in data["distro"]


def test_book_show_unknown_name(vault_with_distro, capsys):
    """`book show missing` exits 1 with an error about available books."""
    code = _run(["book", "show", "missing"])
    assert code == 1
    err = capsys.readouterr().err
    assert "not found" in err
    assert "agents" in err  # available books listed


def test_book_show_no_distro_url(vault_no_distro, capsys):
    """`book show` exits 4 when distro_url is not configured."""
    code = _run(["book", "show", "agents"])
    assert code == 4


# ---------------------------------------------------------------------------
# book pull
# ---------------------------------------------------------------------------


def test_book_pull_writes_files(vault_with_distro, capsys):
    """`book pull agents` writes .md files to .claude/agents/ and exits 0."""
    vault, _ = vault_with_distro
    code = _run(["book", "pull", "agents"])
    assert code == 0

    agents_dir = vault / ".claude" / "agents"
    assert agents_dir.is_dir()
    assert (agents_dir / "architect.md").is_file()
    assert (agents_dir / "developer.md").is_file()
    assert not (agents_dir / "README.md").exists()

    out = capsys.readouterr().out
    assert "architect.md" in out
    assert "developer.md" in out
    assert "Summary:" in out
    assert "2 written" in out


def test_book_pull_dry_run(vault_with_distro, capsys):
    """`book pull agents --dry-run` plans but does not write files."""
    vault, _ = vault_with_distro
    code = _run(["book", "pull", "agents", "--dry-run"])
    assert code == 0

    # Files should NOT have been written
    agents_dir = vault / ".claude" / "agents"
    assert not agents_dir.exists()

    out = capsys.readouterr().out
    assert "[would]" in out
    assert "architect.md" in out
    assert "developer.md" in out


def test_book_pull_dry_run_no_writes(vault_with_distro):
    """--dry-run leaves the destination directory untouched."""
    vault, _ = vault_with_distro
    _run(["book", "pull", "agents", "--dry-run"])
    assert not (vault / ".claude" / "agents").exists()


def test_book_pull_json(vault_with_distro, capsys):
    """`book pull agents --json` emits JSONL writes + final summary."""
    code = _run(["book", "pull", "agents", "--json"])
    assert code == 0
    lines = [l for l in capsys.readouterr().out.strip().splitlines() if l]
    records = [json.loads(l) for l in lines]

    write_records = [r for r in records if "action" in r]
    assert len(write_records) >= 2
    for r in write_records:
        assert r["action"] in ("write", "overwrite")
        assert "destination" in r
        assert "overwritten" in r
        assert "was_symlink" in r

    summary_records = [r for r in records if "summary" in r]
    assert len(summary_records) == 1
    summary = summary_records[0]
    assert summary["book"] == "agents"
    assert summary["summary"]["written"] >= 2
    assert "distro" in summary
    assert "sha" in summary["distro"]


def test_book_pull_overwrite(vault_with_distro, capsys):
    """Pulling twice reports 'overwrite' on second run."""
    vault, _ = vault_with_distro
    _run(["book", "pull", "agents"])  # first pull

    capsys.readouterr()  # clear stdout
    code = _run(["book", "pull", "agents"])
    assert code == 0
    out = capsys.readouterr().out
    assert "overwrite" in out
    assert "Summary:" in out


def test_book_pull_symlink_replaced(vault_with_distro, capsys):
    """Symlinked destination is replaced with a regular file and reported."""
    vault, _ = vault_with_distro
    agents_dir = vault / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    target = vault / "target.md"
    target.write_text("old")
    sym = agents_dir / "architect.md"
    sym.symlink_to(target)

    code = _run(["book", "pull", "agents"])
    assert code == 0

    # Symlink replaced with real file
    assert not sym.is_symlink()
    assert sym.is_file()

    out = capsys.readouterr().out
    assert "symlink" in out.lower()


def test_book_pull_unknown_name(vault_with_distro, capsys):
    """`book pull missing` exits 1."""
    code = _run(["book", "pull", "missing"])
    assert code == 1
    err = capsys.readouterr().err
    assert "not found" in err


def test_book_pull_no_distro_url(vault_no_distro, capsys):
    """`book pull` exits 4 when distro_url is not configured."""
    code = _run(["book", "pull", "agents"])
    assert code == 4


def test_book_pull_vault_not_found(tmp_path, monkeypatch, capsys):
    """`book pull` exits 3 when not inside a vault."""
    monkeypatch.chdir(tmp_path)
    code = _run(["book", "pull", "agents"])
    assert code == 3


# ---------------------------------------------------------------------------
# End-to-end: fresh vault + fixture distro → agents at .claude/agents/
# ---------------------------------------------------------------------------


def test_e2e_pull_agents_end_to_end(tmp_path, monkeypatch, capsys):
    """Fresh vault + fixture distro → pull → working agents at .claude/agents/."""
    # Build distro (v2 schema)
    distro = make_distro_repo(
        tmp_path / "distro",
        artbook_yaml={
            "version": 1,
            "distro": {"name": "e2e-distro"},
            "books": [
                {"name": "agents", "src": "agents/", "dest": ".claude/agents/"}
            ],
        },
        agent_files={
            "agents/researcher.md": "---\nname: researcher\n---\n# Researcher",
        },
    )

    # Set up vault
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "artifacts.yaml").write_text(
        f"layout_version: 1\nartbook:\n  distro_url: '{distro}'\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(vault)

    # Pull
    code = _run(["book", "pull", "agents"])
    assert code == 0

    # Verify files landed
    agent_file = vault / ".claude" / "agents" / "researcher.md"
    assert agent_file.is_file()
    assert "Researcher" in agent_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# D23 — local-manifest auto-detect
# ---------------------------------------------------------------------------


@pytest.fixture
def vault_with_local_manifest(vault: Path) -> Path:
    """A vault with artbook.yaml at its root and no artbook.distro_url.

    The distro manifest points to an ``agents/`` subfolder that
    exists inside the vault root (vault IS the distro root for this fixture).
    """
    # Write artbook.yaml (the distro manifest) at vault root (v2 schema)
    local_artbook = {
        "version": 1,
        "distro": {
            "name": "local-distro",
            "description": "Local test distro.",
        },
        "books": [
            {
                "name": "agents",
                "src": "agents/",
                "dest": ".claude/agents/",
                "description": "Local agents.",
            }
        ],
    }
    (vault / "artbook.yaml").write_text(yaml.dump(local_artbook), encoding="utf-8")

    # Populate the book source directory
    agents_src = vault / "agents"
    agents_src.mkdir(exist_ok=True)
    (agents_src / "architect.md").write_text("# Architect\nLocal agent.", encoding="utf-8")
    (agents_src / "developer.md").write_text("# Developer\nLocal agent.", encoding="utf-8")
    (agents_src / "README.md").write_text("# README", encoding="utf-8")  # excluded by D20

    # No artbook.distro_url in artifacts.yaml
    return vault


def test_book_list_local_manifest_table(vault_with_local_manifest: Path, capsys):
    """`book list` reads local artbook.yaml without network access, exits 0."""
    code = _run(["book", "list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "agents" in out
    assert "local-distro" in out
    assert "(local)" in out


def test_book_list_local_manifest_json(vault_with_local_manifest: Path, capsys):
    """`book list --json` with local manifest returns local=True, url/sha null (v2 fields)."""
    code = _run(["book", "list", "--json"])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["distro"]["name"] == "local-distro"
    assert data["distro"]["local"] is True
    assert data["distro"]["url"] is None
    assert data["distro"]["sha"] is None
    assert len(data["books"]) == 1
    assert data["books"][0]["name"] == "agents"
    assert data["books"][0]["src"] == "agents/"
    assert data["books"][0]["dest"] == ".claude/agents/"
    assert "type" not in data["books"][0]


def test_book_show_local_manifest(vault_with_local_manifest: Path, capsys):
    """`book show agents` reads from local manifest, shows local files, exits 0."""
    code = _run(["book", "show", "agents"])
    assert code == 0
    out = capsys.readouterr().out
    assert "agents" in out
    assert "(local)" in out
    assert "architect.md" in out
    assert "developer.md" in out
    # README excluded by D20 walker
    assert "README.md" not in out


def test_book_show_local_manifest_json(vault_with_local_manifest: Path, capsys):
    """`book show agents --json` with local manifest has local=True and v2 fields."""
    code = _run(["book", "show", "agents", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["book"]["name"] == "agents"
    assert data["book"]["src"] == "agents/"
    assert data["book"]["dest"] == ".claude/agents/"
    assert "type" not in data["book"]
    assert "destination" not in data  # standalone key removed in v2
    assert data["distro"]["local"] is True
    assert data["distro"]["url"] is None
    assert "architect.md" in data["contents"]
    assert "developer.md" in data["contents"]
    assert "README.md" not in data["contents"]


def test_book_list_remote_flag_bypasses_local(vault_with_local_manifest: Path, capsys):
    """`book list --remote` skips local manifest and exits 4 (no distro_url)."""
    code = _run(["book", "list", "--remote"])
    assert code == 4
    err = capsys.readouterr().err
    assert "distro_url" in err


def test_book_show_remote_flag_bypasses_local(vault_with_local_manifest: Path, capsys):
    """`book show agents --remote` skips local manifest and exits 4 (no distro_url)."""
    code = _run(["book", "show", "agents", "--remote"])
    assert code == 4
    err = capsys.readouterr().err
    assert "distro_url" in err


def test_book_pull_ignores_local_manifest(vault_with_local_manifest: Path, capsys):
    """`book pull` always uses remote clone path; exits 4 without distro_url."""
    code = _run(["book", "pull", "agents"])
    assert code == 4
    err = capsys.readouterr().err
    assert "distro_url" in err


# ---------------------------------------------------------------------------
# D26 — recurse (folder-of-folders) CLI rendering
# ---------------------------------------------------------------------------


@pytest.fixture
def vault_with_recurse_book(vault: Path, monkeypatch) -> Path:
    """A vault with a local artbook.yaml featuring a recurse skills book."""
    local_artbook = {
        "version": 1,
        "distro": {"name": "recurse-distro"},
        "books": [
            {
                "name": "skills",
                "src": "skills/",
                "dest": ".claude/skills/",
                "description": "Skills book.",
                "recurse": True,
            }
        ],
    }
    (vault / "artbook.yaml").write_text(yaml.dump(local_artbook), encoding="utf-8")

    skills = vault / "skills"
    # Unit 1
    aos = skills / "artifacts-os"
    aos.mkdir(parents=True)
    (aos / "SKILL.md").write_text("# Skill: artifacts-os", encoding="utf-8")
    (aos / "__init__.py").write_text("", encoding="utf-8")
    # Unit 2
    rc = skills / "release-changelog"
    rc.mkdir(parents=True)
    (rc / "SKILL.md").write_text("# Skill: release-changelog", encoding="utf-8")
    (rc / "__init__.py").write_text("", encoding="utf-8")
    # __pycache__ must not surface
    (skills / "__pycache__").mkdir()
    (skills / "__pycache__" / "foo.cpython.pyc").write_text("compiled", encoding="utf-8")

    monkeypatch.chdir(vault)
    return vault


def test_book_list_recurse_marker_in_table(vault_with_recurse_book: Path, capsys):
    """`book list` annotates recurse books with `(recurse)` in the Description column."""
    code = _run(["book", "list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "skills" in out
    assert "(recurse)" in out


def test_book_list_json_includes_recurse_flag(vault_with_recurse_book: Path, capsys):
    """`book list --json` exposes `recurse` on each book object."""
    code = _run(["book", "list", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["books"]) == 1
    book = data["books"][0]
    assert book["name"] == "skills"
    assert book["recurse"] is True


def test_book_show_recurse_grouped_output(vault_with_recurse_book: Path, capsys):
    """`book show skills` groups Contents by unit and shows the Mode line."""
    code = _run(["book", "show", "skills"])
    assert code == 0
    out = capsys.readouterr().out
    # Mode line announces recurse mode
    assert "Mode:" in out
    assert "recurse" in out
    # Unit headers appear with trailing slash
    assert "artifacts-os/" in out
    assert "release-changelog/" in out
    # Files appear under their unit
    assert "SKILL.md" in out
    assert "__init__.py" in out
    # __pycache__ must not leak
    assert "__pycache__" not in out
    # Header counts (2 units, 4 files)
    assert "2 units" in out
    assert "4 files" in out


def test_book_show_recurse_json_shape(vault_with_recurse_book: Path, capsys):
    """`book show skills --json` returns contents as a list of unit objects."""
    code = _run(["book", "show", "skills", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["book"]["recurse"] is True
    contents = data["contents"]
    assert isinstance(contents, list)
    # Each entry is a {unit, files} object
    units = {entry["unit"]: entry["files"] for entry in contents}
    assert "artifacts-os" in units
    assert "release-changelog" in units
    assert "SKILL.md" in units["artifacts-os"]
    assert "__init__.py" in units["artifacts-os"]
    assert "SKILL.md" in units["release-changelog"]
    # __pycache__ must not surface anywhere
    for unit, files in units.items():
        assert "__pycache__" not in unit
        for f in files:
            assert "__pycache__" not in f
            assert not f.endswith(".pyc")
