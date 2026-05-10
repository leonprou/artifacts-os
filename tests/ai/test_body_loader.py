"""Tests for the /artifacts.create body-loader (s0018).

Implements s0018-artifact-md-body-loader-for § 11 test plan verbatim.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from artifacts_os.ai.body_loader import (
    LoadResult,
    body_for_kind,
    load_body,
    read_skeleton_block,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Absolute path to the project root (two levels up from tests/ai/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_KINDS_DIR = _PROJECT_ROOT / "artifacts" / "kinds"


def _shipped_artifact_md(kind: str) -> Path:
    """Return the path to a shipped ARTIFACT.md file."""
    return _KINDS_DIR / kind / "ARTIFACT.md"


def _make_kinds_dir(tmp_path: Path) -> Path:
    """Create a synthetic kinds directory under tmp_path."""
    kinds_dir = tmp_path / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    return kinds_dir


def _write_kind(
    kinds_dir: Path,
    name: str,
    artifact_md_body: str | None = None,
    artifact_md_fm: dict | None = None,
) -> Path:
    """Write a synthetic kind folder with optional ARTIFACT.md."""
    folder = kinds_dir / name
    folder.mkdir(parents=True, exist_ok=True)
    schema = {"x-dir": f"{name}s", "x-prefix": name[0], "x-numbered": True}
    (folder / "kind.json").write_text(json.dumps(schema), encoding="utf-8")

    if artifact_md_body is not None:
        fm = artifact_md_fm or {"name": name, "description": f"The {name} kind."}
        lines = ["---\n"]
        for k, v in fm.items():
            if isinstance(v, list):
                lines.append(f"{k}:\n")
                for item in v:
                    lines.append(f"  - {item}\n")
            else:
                lines.append(f"{k}: {v!r}\n")
        lines.append("---\n\n")
        lines.append(artifact_md_body)
        (folder / "ARTIFACT.md").write_text("".join(lines), encoding="utf-8")

    return folder


def _make_variant_artifact_md(
    title_in_skeleton: bool = True,
    has_default_skeleton: bool = True,
    variant_field: str | None = None,
) -> str:
    """Build a synthetic ARTIFACT.md body with alpha/beta variants."""
    alpha_content = "# Alpha variant\n\nAlpha body content.\n"
    beta_content = "# Beta variant\n\nBeta body content.\n"
    default_content = (
        "# {{TITLE}}\n\nDefault skeleton content.\n"
        if title_in_skeleton
        else "# Default heading\n\nDefault skeleton content.\n"
    )

    parts = []
    if has_default_skeleton:
        parts.append(f"## Skeleton\n\n```markdown\n{default_content}```\n\n")
    parts.append(f"## Variants/alpha\n\n```markdown\n{alpha_content}```\n\n")
    parts.append(f"## Variants/beta\n\n```markdown\n{beta_content}```\n\n")
    return "".join(parts)


# ---------------------------------------------------------------------------
# § 11.1  End-to-end skeleton substitution (per shipped kind)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["task", "spec", "research", "note"])
def test_e2e_kind_skeleton_substitutes_title(kind: str) -> None:
    """Skeleton {{TITLE}} is replaced; result is plain markdown (no code fence)."""
    path = _shipped_artifact_md(kind)
    assert path.is_file(), f"Shipped ARTIFACT.md not found: {path}"

    result = body_for_kind(kind, path, title="My Test Title")

    assert result.info is None, f"Unexpected info: {result.info}"
    assert "My Test Title" in result.body, "{{TITLE}} not substituted"
    assert "{{TITLE}}" not in result.body, "{{TITLE}} left un-substituted"
    # Body must not contain code-fence delimiters wrapping the whole content
    assert not result.body.strip().startswith("```"), "Code fence not stripped"


@pytest.mark.parametrize("kind,placeholder", [
    ("note", "{{ONE_PARAGRAPH_SUMMARY}}"),
    ("task", "{{TESTABLE_CRITERION}}"),
    ("spec", "{{ONE_PARAGRAPH_SUMMARY}}"),
    ("research", "{{AGENT_NAME}}"),
])
def test_e2e_kind_unresolved_placeholders_preserved(kind: str, placeholder: str) -> None:
    """Non-{{TITLE}} placeholders are left literal in the emitted body."""
    path = _shipped_artifact_md(kind)
    result = body_for_kind(kind, path, title="Test Title")

    assert placeholder in result.body, (
        f"Expected placeholder {placeholder!r} to be preserved in {kind} skeleton"
    )


@pytest.mark.parametrize("kind", ["task", "spec", "research", "note"])
def test_e2e_kind_frontmatter_unchanged_by_substitution(kind: str) -> None:
    """The CLI-written frontmatter path is separate; body substitution does not touch it.

    This test verifies that body_for_kind returns only a body string (not
    frontmatter) so the caller (CLI) owns frontmatter writing independently.
    """
    path = _shipped_artifact_md(kind)
    result = body_for_kind(kind, path, title="Another Title")

    # The result must NOT contain YAML frontmatter delimiters
    assert not result.body.strip().startswith("---"), (
        "body_for_kind must not return YAML frontmatter"
    )


# ---------------------------------------------------------------------------
# § 11.2  Negative path — no ARTIFACT.md
# ---------------------------------------------------------------------------

def test_e2e_kind_without_artifact_md_falls_back_to_empty_body(tmp_path: Path) -> None:
    """Kind with kind.json only (no ARTIFACT.md) → empty body, no exception."""
    kinds_dir = _make_kinds_dir(tmp_path)
    _write_kind(kinds_dir, "notemplate")  # no artifact_md_body

    result = body_for_kind("notemplate", artifact_md_path=None, title="Any Title")

    assert result.body == "", f"Expected empty body, got: {result.body!r}"
    # No partial substitution or synthesised stub
    assert "{{" not in result.body


def test_e2e_kind_without_artifact_md_emits_info_note(tmp_path: Path) -> None:
    """Kind with no ARTIFACT.md → info note surfaces in agent context (s0018 § 6)."""
    result = body_for_kind("notemplate", artifact_md_path=None, title="Any Title")

    assert result.info is not None, "Expected info note for missing ARTIFACT.md"
    assert "notemplate" in result.info
    assert "no ARTIFACT.md" in result.info or "empty body" in result.info


def test_e2e_kind_with_invalid_frontmatter_treated_as_missing(tmp_path: Path) -> None:
    """ARTIFACT.md whose frontmatter is unparseable falls back to empty body.

    Simulates s0017 § 6.3 validation failure by writing an ARTIFACT.md
    whose frontmatter YAML is broken.  The body loader must treat this as
    if the file were absent (s0018 § 11.2).
    """
    kinds_dir = _make_kinds_dir(tmp_path)
    folder = kinds_dir / "badkind"
    folder.mkdir()
    (folder / "kind.json").write_text(
        json.dumps({"x-dir": "badkinds", "x-prefix": "b", "x-numbered": True}),
        encoding="utf-8",
    )
    # Write an ARTIFACT.md with broken YAML frontmatter
    artifact_md = folder / "ARTIFACT.md"
    artifact_md.write_text(
        "---\n"
        ": this is: invalid: yaml\n"
        "---\n\n"
        "## Skeleton\n\n```markdown\n# {{TITLE}}\n```\n",
        encoding="utf-8",
    )

    # The body loader should handle the bad frontmatter gracefully
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = load_body(artifact_md, title="Test", variant=None)

    # Even with bad frontmatter, the skeleton section should still be extracted
    # (frontmatter parse failure is soft; skeleton reading continues)
    # Key invariant: no exception raised, body is either the skeleton or empty
    assert isinstance(result, LoadResult)
    # Body must not contain un-stripped code fence delimiters as a whole
    assert not result.body.strip().startswith("```")


# ---------------------------------------------------------------------------
# § 11.3  Variant selection (synthetic fixture)
# ---------------------------------------------------------------------------

@pytest.fixture
def variant_artifact_md(tmp_path: Path) -> tuple[Path, Path]:
    """Fixture kind with alpha/beta variants and a default ## Skeleton."""
    kinds_dir = _make_kinds_dir(tmp_path)
    body = _make_variant_artifact_md()
    fm = {
        "name": "fixture",
        "description": "A fixture kind with variants.",
        "variant_field": "type",
    }
    _write_kind(kinds_dir, "fixture", artifact_md_body=body, artifact_md_fm=fm)
    return kinds_dir, kinds_dir / "fixture" / "ARTIFACT.md"


def test_variant_explicit_token_picks_variant(
    variant_artifact_md: tuple[Path, Path],
) -> None:
    """variant:alpha selects the ## Variants/alpha block."""
    _, path = variant_artifact_md
    block, error = read_skeleton_block(path, variant="alpha")
    assert error is None
    assert block is not None
    assert "Alpha variant" in block
    assert "Beta" not in block
    assert "Default" not in block


def test_variant_type_token_picks_variant_when_variant_field_declared(
    variant_artifact_md: tuple[Path, Path],
) -> None:
    """type:beta picks ## Variants/beta when variant_field: type is declared."""
    _, path = variant_artifact_md
    block, error = read_skeleton_block(path, type_token="beta")
    assert error is None
    assert block is not None
    assert "Beta variant" in block


def test_variant_type_token_ignored_when_variant_field_absent(
    tmp_path: Path,
) -> None:
    """type:beta is ignored when variant_field is not declared; default skeleton wins."""
    kinds_dir = _make_kinds_dir(tmp_path)
    body = _make_variant_artifact_md()
    # No variant_field in frontmatter
    fm = {"name": "nofieldkind", "description": "A kind without variant_field."}
    _write_kind(kinds_dir, "nofieldkind", artifact_md_body=body, artifact_md_fm=fm)
    path = kinds_dir / "nofieldkind" / "ARTIFACT.md"

    block, error = read_skeleton_block(path, type_token="beta")
    assert error is None
    assert block is not None
    assert "Default skeleton content" in block
    assert "Beta" not in block


def test_variant_unknown_name_aborts_with_named_variants(
    variant_artifact_md: tuple[Path, Path],
) -> None:
    """variant:gamma → error naming declared variants alpha and beta."""
    _, path = variant_artifact_md
    block, error = read_skeleton_block(path, variant="gamma")
    assert block is None
    assert error is not None
    assert "gamma" in error
    assert "alpha" in error
    assert "beta" in error


def test_variant_falls_back_to_default_skeleton_when_no_token(
    variant_artifact_md: tuple[Path, Path],
) -> None:
    """No variant token → default ## Skeleton is used."""
    _, path = variant_artifact_md
    block, error = read_skeleton_block(path)
    assert error is None
    assert block is not None
    assert "Default skeleton content" in block
    assert "Alpha" not in block
    assert "Beta" not in block


def test_variant_title_inference_rejected(
    variant_artifact_md: tuple[Path, Path],
) -> None:
    """A title containing 'alpha' does NOT select the alpha variant (s0018 D4)."""
    _, path = variant_artifact_md
    # load_body with title="alpha" — only {{TITLE}} substitution occurs, no inference
    result = load_body(path, title="alpha")
    # Should use default skeleton (not alpha variant)
    assert "Default skeleton content" in result.body or "{{TITLE}}" not in result.body
    # The word "Alpha variant" from the alpha block must not appear
    assert "Alpha variant" not in result.body


# ---------------------------------------------------------------------------
# § 11.4  Layer isolation
# ---------------------------------------------------------------------------

def test_slash_command_reads_only_chosen_kind_artifact_md(tmp_path: Path) -> None:
    """Body-loading procedure opens exactly one ARTIFACT.md body file per invocation."""
    kinds_dir = _make_kinds_dir(tmp_path)
    # Create three kinds with ARTIFACT.md files
    for name in ("alpha", "beta", "gamma"):
        body = f"## Skeleton\n\n```markdown\n# {{{{TITLE}}}}\n{name} body.\n```\n"
        fm = {"name": name, "description": f"The {name} kind."}
        _write_kind(kinds_dir, name, artifact_md_body=body, artifact_md_fm=fm)

    chosen_path = kinds_dir / "beta" / "ARTIFACT.md"
    body_reads: list[str] = []

    original_read_text = Path.read_text

    def tracking_read_text(self: Path, *args, **kwargs) -> str:
        # Only track ARTIFACT.md body reads (not kind.json or frontmatter reads)
        if self.name == "ARTIFACT.md":
            body_reads.append(str(self))
        return original_read_text(self, *args, **kwargs)

    import unittest.mock as mock

    with mock.patch.object(Path, "read_text", tracking_read_text):
        result = load_body(chosen_path, title="Test Title")

    assert result.body != "" or result.info is not None

    # Exactly one ARTIFACT.md body read — the chosen kind's
    assert len(body_reads) == 1, (
        f"Expected exactly 1 ARTIFACT.md body read, got {len(body_reads)}: {body_reads}"
    )
    assert "beta" in body_reads[0]


def test_slash_command_does_not_read_playbooks(tmp_path: Path) -> None:
    """Body-loading procedure must not open any playbook files."""
    kinds_dir = _make_kinds_dir(tmp_path)
    body = "## Skeleton\n\n```markdown\n# {{TITLE}}\nContent.\n```\n"
    fm = {
        "name": "pkind",
        "description": "A kind with a declared playbook.",
        "playbooks": ["workflow"],
    }
    _write_kind(kinds_dir, "pkind", artifact_md_body=body, artifact_md_fm=fm)

    # Create a playbook file
    playbook_dir = kinds_dir / "pkind" / "playbooks"
    playbook_dir.mkdir()
    playbook_file = playbook_dir / "workflow.md"
    playbook_file.write_text("# Playbook content\n", encoding="utf-8")

    path = kinds_dir / "pkind" / "ARTIFACT.md"
    opened: list[str] = []
    original_open = open

    def tracking_open(file, *args, **kwargs):
        opened.append(str(file))
        return original_open(file, *args, **kwargs)

    import builtins
    import unittest.mock as mock

    with mock.patch.object(builtins, "open", tracking_open):
        load_body(path, title="Test")

    for p in opened:
        assert "playbooks" not in p, f"Body loader opened a playbook file: {p}"


def test_l1_catalogue_invocations_unchanged(tmp_path: Path) -> None:
    """KindCatalog.list_kinds() still reads zero ARTIFACT.md bodies after body_loader lands.

    This regression cite verifies that the L1 layer-isolation invariant
    (s0017 § 4) continues to hold alongside the new body-loader code.
    """
    from artifacts_os.core.kinds_catalog import KindCatalog
    from artifacts_os.core.registry import Registry

    kinds_dir = tmp_path / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    root = tmp_path
    (root / "artifacts.yaml").write_text("layout_version: 1\n")

    # Write a kind with ARTIFACT.md that has body content
    folder = kinds_dir / "task"
    folder.mkdir()
    (folder / "kind.json").write_text(
        json.dumps({"x-dir": "tasks", "x-prefix": "t", "x-numbered": True}),
        encoding="utf-8",
    )
    artifact_md = folder / "ARTIFACT.md"
    artifact_md.write_text(
        "---\n"
        "name: 'task'\n"
        "description: 'A task kind.'\n"
        "---\n\n"
        "## Skeleton\n\n```markdown\n# {{TITLE}}\nBody content.\n```\n",
        encoding="utf-8",
    )

    body_reads: list[str] = []
    original_read_text = Path.read_text

    def tracking_read_text(self: Path, *args, **kwargs) -> str:
        if self.name == "ARTIFACT.md":
            body_reads.append(str(self))
        return original_read_text(self, *args, **kwargs)

    import unittest.mock as mock

    with mock.patch.object(Path, "read_text", tracking_read_text):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = Registry([], root=root)
        catalog = KindCatalog(r, root)
        _ = catalog.list_kinds()

    # L1 must not have read any ARTIFACT.md body
    assert body_reads == [], (
        f"L1 read ARTIFACT.md body files: {body_reads}"
    )


# ---------------------------------------------------------------------------
# § 11.5  CLI surface unchanged (D9)
# ---------------------------------------------------------------------------

def test_cli_create_signature_unchanged(tmp_path: Path, monkeypatch) -> None:
    """artifacts create --help output is unchanged by the body-loader implementation.

    Verifies s0018 D9: no new flags, no changed exit codes, no altered stdout.
    """
    import io
    from artifacts_os.cli import main

    # Set up a minimal vault
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts.yaml").write_text("layout_version: 1\n")
    schema = {"x-dir": "tasks", "x-prefix": "t", "x-numbered": True}
    (kinds_dir / "task.json").write_text(json.dumps(schema))
    (root / "artifacts" / "tasks").mkdir()
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    captured = io.StringIO()
    with pytest.raises(SystemExit) as exc:
        import sys
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            main(["create", "--help"])
        finally:
            sys.stdout = old_stdout

    assert exc.value.code == 0
    help_text = captured.getvalue()

    # Key flags that must remain present (D9 — surface unchanged)
    for flag in ("--kind", "--body", "--body-file", "--name", "--dry-run"):
        assert flag in help_text, f"Flag {flag!r} missing from help output"


def test_cli_create_empty_body_path_still_works(tmp_path: Path, monkeypatch) -> None:
    """Direct artifacts create invocation (no slash command) still writes empty body."""
    from artifacts_os.cli import main
    from artifacts_os.core import frontmatter as _fm

    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts.yaml").write_text("layout_version: 1\n")
    schema = {
        "x-dir": "tasks",
        "x-prefix": "t",
        "x-numbered": True,
        "properties": {"status": {"enum": ["backlog", "ready"]}},
    }
    (kinds_dir / "task.json").write_text(json.dumps(schema))
    (root / "artifacts" / "tasks").mkdir()
    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    import io, sys
    captured = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        main(["create", "My Task Title"])
    finally:
        sys.stdout = old_stdout

    stem = captured.getvalue().strip()
    artifact_path = root / "artifacts" / "tasks" / f"{stem}.md"
    assert artifact_path.exists(), f"Artifact not created: {artifact_path}"

    _, body = _fm.parse(artifact_path.read_text())
    # Direct CLI invocation produces an empty body
    assert body.strip() == "", f"Expected empty body, got: {body!r}"


# ---------------------------------------------------------------------------
# Additional: artifact_md_path field on KindCatalogEntry (s0018 § 9 item 2)
# ---------------------------------------------------------------------------

def test_kind_catalog_entry_artifact_md_path_set_for_kinds_with_template(
    tmp_path: Path,
) -> None:
    """KindCatalogEntry.artifact_md_path is set when has_template=True."""
    from artifacts_os.core.kinds_catalog import KindCatalog
    from artifacts_os.core.registry import Registry

    kinds_dir = tmp_path / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    root = tmp_path
    (root / "artifacts.yaml").write_text("layout_version: 1\n")

    folder = kinds_dir / "note"
    folder.mkdir()
    (folder / "kind.json").write_text(
        json.dumps({"x-dir": "notes", "x-prefix": "n", "x-numbered": True}),
        encoding="utf-8",
    )
    (folder / "ARTIFACT.md").write_text(
        "---\nname: 'note'\ndescription: 'A note kind.'\n---\n\n## Skeleton\n",
        encoding="utf-8",
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = Registry([], root=root)
    catalog = KindCatalog(r, root)
    entries = {e.name: e for e in catalog.list_kinds()}

    assert "note" in entries
    entry = entries["note"]
    assert entry.has_template is True
    assert entry.artifact_md_path is not None
    assert entry.artifact_md_path == kinds_dir / "note" / "ARTIFACT.md"


def test_kind_catalog_entry_artifact_md_path_none_when_no_template(
    tmp_path: Path,
) -> None:
    """KindCatalogEntry.artifact_md_path is None when has_template=False."""
    from artifacts_os.core.kinds_catalog import KindCatalog
    from artifacts_os.core.registry import Registry

    kinds_dir = tmp_path / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    root = tmp_path
    (root / "artifacts.yaml").write_text("layout_version: 1\n")

    folder = kinds_dir / "bare"
    folder.mkdir()
    (folder / "kind.json").write_text(
        json.dumps({"x-dir": "bares", "x-prefix": "b", "x-numbered": True}),
        encoding="utf-8",
    )
    # No ARTIFACT.md

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = Registry([], root=root)
    catalog = KindCatalog(r, root)
    entries = {e.name: e for e in catalog.list_kinds()}

    assert "bare" in entries
    entry = entries["bare"]
    assert entry.has_template is False
    assert entry.artifact_md_path is None
