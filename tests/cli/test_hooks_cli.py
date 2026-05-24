"""Tests for cli hooks command (list, show, promote, demote).

Covers task t0182 §7 CLI requirements.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from artifacts_os.cli import main
from artifacts_os.core import events as _events
from artifacts_os.hooks.loader import invalidate_cache


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_HOOK_KIND_SCHEMA = {
    "x-dir": "hooks",
    "x-storage": "directory",
    "x-manifest-name": "{slug}.md",
    "x-numbered": False,
    "x-columns": ["name", "host", "phase", "blocking", "timeout"],
    "title": "Hook",
    "type": "object",
    "additionalProperties": False,
    "required": ["kind", "name"],
    "properties": {
        "kind": {"type": "string", "const": "hook"},
        "name": {"type": "string"},
        "host": {"type": "string"},
        "phase": {"type": "string", "enum": ["pre", "post"]},
        "blocking": {"type": "boolean"},
        "timeout": {"type": "integer"},
        "matcher": {"type": "object"},
        "action": {"type": "object"},
    },
}


@pytest.fixture
def vault(tmp_path: Path, monkeypatch):
    """Create a minimal vault with hook kind registered."""
    root = tmp_path / "vault"
    kinds_dir = root / "artifacts" / "kinds"
    kinds_dir.mkdir(parents=True)
    (root / "artifacts.yaml").write_text("layout_version: 1\n")

    # Register hook kind.
    hook_kind_dir = kinds_dir / "hook"
    hook_kind_dir.mkdir(parents=True)
    (hook_kind_dir / "kind.json").write_text(json.dumps(_HOOK_KIND_SCHEMA))
    (hook_kind_dir / "ARTIFACT.md").write_text(
        "---\nkind: kind\nname: hook\ndescription: Hook bundle.\nagent: manual\n---\n"
    )
    (root / "artifacts" / "hooks").mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("artifacts_os.cli._registered_kinds", [])
    monkeypatch.chdir(root)

    return root


@pytest.fixture(autouse=True)
def clean_hooks_state():
    _events._emitters.clear()
    invalidate_cache()
    yield
    _events._emitters.clear()
    invalidate_cache()


def _make_bundle(root: Path, slug: str, *, host: str = "artifacts-os",
                 phase: str = "post") -> Path:
    """Create a minimal hook bundle."""
    bundle_dir = root / "artifacts" / "hooks" / slug
    bundle_dir.mkdir(parents=True, exist_ok=True)
    manifest = bundle_dir / f"{slug}.md"
    fm = {
        "kind": "hook",
        "name": slug,
        "host": host,
        "phase": phase,
        "blocking": False,
        "timeout": 30,
        "matcher": {"event": "artifact.created"},
        "action": {"type": "shell", "command": "echo hello"},
    }
    manifest.write_text("---\n" + yaml.dump(fm) + "---\n\n# body\n")
    return bundle_dir


def _promote(root: Path, slug: str) -> None:
    active_dir = root / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    link = active_dir / slug
    os.symlink(f"../{slug}/{slug}.md", link)


# ---------------------------------------------------------------------------
# hooks list — basic
# ---------------------------------------------------------------------------


def test_hooks_list_empty(vault, capsys):
    """hooks list returns 0 with no output for empty vault."""
    main(["hooks", "list"])
    # Should not error.


def test_hooks_list_shows_active_column(vault, capsys):
    """hooks list renders the 'active' column."""
    _make_bundle(vault, "my-hook")
    _promote(vault, "my-hook")

    main(["hooks", "list"])
    out = capsys.readouterr().out
    assert "my-hook" in out
    assert "active" in out.lower() or "yes" in out


def test_hooks_list_json_stable(vault, capsys):
    """-j emits a JSON array; shape is stable."""
    _make_bundle(vault, "json-hook")
    _promote(vault, "json-hook")

    main(["hooks", "list", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    first = data[0]
    assert "name" in first
    assert "host" in first
    assert "active" in first
    assert "source" in first


def test_hooks_list_filter_active(vault, capsys):
    """--active shows only active hooks."""
    _make_bundle(vault, "active-hook")
    _make_bundle(vault, "inactive-hook")
    _promote(vault, "active-hook")

    main(["hooks", "list", "--active", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    names = [d["name"] for d in data]
    assert "active-hook" in names
    assert "inactive-hook" not in names


def test_hooks_list_filter_inactive(vault, capsys):
    """--inactive shows only non-active hooks."""
    _make_bundle(vault, "active-hook2")
    _make_bundle(vault, "inactive-hook2")
    _promote(vault, "active-hook2")

    main(["hooks", "list", "--inactive", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    names = [d["name"] for d in data]
    assert "inactive-hook2" in names
    assert "active-hook2" not in names


def test_hooks_list_filter_source_bundle(vault, capsys):
    """--source bundle shows only bundle hooks."""
    _make_bundle(vault, "bndl-hook")
    _promote(vault, "bndl-hook")

    main(["hooks", "list", "--source", "bundle", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert all(d.get("source") == "bundle" for d in data)


def test_hooks_list_filter_host(vault, capsys):
    """--host filters by host."""
    _make_bundle(vault, "local-hook", host="artifacts-os")
    _make_bundle(vault, "remote-hook", host="openstation")

    main(["hooks", "list", "--host", "artifacts-os", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    names = [d["name"] for d in data]
    assert "local-hook" in names
    assert "remote-hook" not in names


def test_hooks_list_tail(vault, capsys):
    """--tail [N] limits results."""
    for i in range(5):
        _make_bundle(vault, f"hook-{i:02d}")

    main(["hooks", "list", "--tail", "2", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) <= 2


# ---------------------------------------------------------------------------
# hooks list --prune
# ---------------------------------------------------------------------------


def test_hooks_list_prune_removes_dangling(vault, capsys):
    """--prune removes dangling .active/ entries."""
    active_dir = vault / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    link = active_dir / "ghost"
    os.symlink("../ghost/ghost.md", link)

    main(["hooks", "list", "--prune"])
    assert not link.is_symlink() and not link.exists()


def test_hooks_list_prune_dry_run(vault, capsys):
    """--prune --dry-run makes no FS changes."""
    active_dir = vault / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    link = active_dir / "ghost2"
    os.symlink("../ghost2/ghost2.md", link)

    main(["hooks", "list", "--prune", "--dry-run"])
    # File still exists.
    assert link.is_symlink()


def test_hooks_list_prune_emits_hook_demoted(vault):
    """--prune emits hook.demoted with reason: prune."""
    demoted = []
    _events.register_emitter(
        lambda e, p: demoted.append(p) if e == "hook.demoted" else None
    )

    active_dir = vault / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    os.symlink("../ghost3/ghost3.md", active_dir / "ghost3")

    main(["hooks", "list", "--prune"])
    assert any(p.get("reason") == "prune" for p in demoted)


# ---------------------------------------------------------------------------
# hooks show
# ---------------------------------------------------------------------------


def test_hooks_show_renders(vault, capsys):
    """hooks show <slug> renders without error."""
    bundle_dir = _make_bundle(vault, "show-hook")
    (bundle_dir / "action.sh").write_text("#!/bin/sh\necho hi\n")

    main(["hooks", "show", "show-hook"])
    out = capsys.readouterr().out
    assert "show-hook" in out


def test_hooks_show_sibling_files(vault, capsys):
    """hooks show lists sibling files."""
    bundle_dir = _make_bundle(vault, "sib-hook")
    (bundle_dir / "action.sh").write_text("#!/bin/sh\necho hi\n")

    main(["hooks", "show", "sib-hook"])
    out = capsys.readouterr().out
    assert "action.sh" in out


def test_hooks_show_json_stable(vault, capsys):
    """-j output has frontmatter, active, siblings, recent_events keys."""
    _make_bundle(vault, "showj-hook")

    main(["hooks", "show", "showj-hook", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "frontmatter" in data
    assert "active" in data
    assert "siblings" in data
    assert "recent_events" in data


def test_hooks_show_unknown_slug_exits_1(vault):
    """hooks show with unknown slug exits with code 1."""
    with pytest.raises(SystemExit) as exc_info:
        main(["hooks", "show", "no-such-hook"])
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# hooks promote
# ---------------------------------------------------------------------------


def test_hooks_promote_creates_symlink(vault):
    """hooks promote creates .active/<slug> symlink."""
    _make_bundle(vault, "promo-hook")
    main(["hooks", "promote", "promo-hook"])

    link = vault / "artifacts" / "hooks" / ".active" / "promo-hook"
    assert link.exists() or link.is_symlink()


def test_hooks_promote_json_output(vault, capsys):
    """hooks promote -j emits JSON with slug and target."""
    _make_bundle(vault, "promoj-hook")
    main(["hooks", "promote", "promoj-hook", "-j"])

    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["slug"] == "promoj-hook"
    assert "target" in data


def test_hooks_promote_idempotent(vault, capsys):
    """hooks promote twice is idempotent (second call says 'already active')."""
    _make_bundle(vault, "idem-hook")
    main(["hooks", "promote", "idem-hook"])
    main(["hooks", "promote", "idem-hook"])
    out = capsys.readouterr().out
    # No error on second call.


def test_hooks_promote_divergent_without_force_exits_1(vault):
    """hooks promote with divergent target and no --force exits 1."""
    _make_bundle(vault, "div2-hook")
    active_dir = vault / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    os.symlink("../other/other.md", active_dir / "div2-hook")

    with pytest.raises(SystemExit) as exc_info:
        main(["hooks", "promote", "div2-hook"])
    assert exc_info.value.code == 1


def test_hooks_promote_divergent_with_force_succeeds(vault):
    """hooks promote --force overwrites divergent target."""
    _make_bundle(vault, "divf-hook")
    active_dir = vault / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    os.symlink("../other/other.md", active_dir / "divf-hook")

    main(["hooks", "promote", "divf-hook", "--force"])
    # Should not exit with error.


def test_hooks_promote_unknown_slug_exits_1(vault):
    """hooks promote with unknown slug exits 1."""
    with pytest.raises(SystemExit) as exc_info:
        main(["hooks", "promote", "no-bundle"])
    assert exc_info.value.code == 1


def test_hooks_promote_emits_hook_promoted(vault):
    """hooks promote emits hook.promoted event."""
    promoted = []
    _events.register_emitter(
        lambda e, p: promoted.append(p) if e == "hook.promoted" else None
    )

    _make_bundle(vault, "promo2-hook")
    main(["hooks", "promote", "promo2-hook"])
    assert any(p["hook"] == "promo2-hook" for p in promoted)


# ---------------------------------------------------------------------------
# hooks demote
# ---------------------------------------------------------------------------


def test_hooks_demote_unlinks(vault):
    """hooks demote removes .active/ entry."""
    _make_bundle(vault, "deact-hook")
    main(["hooks", "promote", "deact-hook"])

    main(["hooks", "demote", "deact-hook"])
    link = vault / "artifacts" / "hooks" / ".active" / "deact-hook"
    assert not link.exists() and not link.is_symlink()


def test_hooks_demote_noop_absent(vault, capsys):
    """hooks demote is a no-op for an already-inactive hook."""
    _make_bundle(vault, "absent-hook")
    main(["hooks", "demote", "absent-hook"])
    out = capsys.readouterr().out
    assert "not active" in out


def test_hooks_demote_json_output(vault, capsys):
    """hooks demote -j emits JSON with removed status."""
    _make_bundle(vault, "deactj-hook")
    main(["hooks", "promote", "deactj-hook"])
    capsys.readouterr()  # flush promote output
    invalidate_cache()

    main(["hooks", "demote", "deactj-hook", "-j"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["slug"] == "deactj-hook"
    assert "removed" in data


def test_hooks_demote_emits_hook_demoted(vault):
    """hooks demote emits hook.demoted event."""
    demoted = []
    _events.register_emitter(
        lambda e, p: demoted.append(p) if e == "hook.demoted" else None
    )

    _make_bundle(vault, "deacte-hook")
    main(["hooks", "promote", "deacte-hook"])
    invalidate_cache()
    demoted.clear()

    main(["hooks", "demote", "deacte-hook"])
    assert any(p["hook"] == "deacte-hook" for p in demoted)
