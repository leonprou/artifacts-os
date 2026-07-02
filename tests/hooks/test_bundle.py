"""Tests for bundle-aware hook loader (load_hooks_from_active, load_hooks)
and the promotion/demotion mechanics.

Covers task t0182 requirements.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from artifacts_os.core import events as _events
from artifacts_os.hooks.loader import (
    Hook,
    BundleError,
    load_hooks,
    load_hooks_from_yaml,
    load_hooks_from_active,
    _fire_list,
    invalidate_cache,
)
from artifacts_os.hooks.promotion import (
    promote,
    demote,
    demote_prune,
    active_state,
    list_bundles,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_state():
    _events._emitters.clear()
    invalidate_cache()
    yield
    _events._emitters.clear()
    invalidate_cache()


def _make_bundle(root: Path, slug: str, *, host: str = "artifacts-os",
                 matcher: dict | None = None, action: dict | None = None,
                 phase: str = "post", extra_files: dict[str, str] | None = None) -> Path:
    """Create a minimal hook bundle at artifacts/hooks/<slug>/<slug>.md."""
    bundle_dir = root / "artifacts" / "hooks" / slug
    bundle_dir.mkdir(parents=True, exist_ok=True)
    manifest = bundle_dir / f"{slug}.md"
    fm: dict = {
        "kind": "hook",
        "name": slug,
        "host": host,
        "phase": phase,
        "blocking": False,
        "timeout": 30,
        "matcher": matcher or {"event": "artifact.created"},
        "action": action or {"type": "shell", "command": "echo hello"},
    }
    lines = ["---\n"]
    lines.append(yaml.dump(fm))
    lines.append("---\n\n# Hook body\n")
    manifest.write_text("".join(lines), encoding="utf-8")

    if extra_files:
        for rel_path, content in extra_files.items():
            p = bundle_dir / rel_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)

    return bundle_dir


def _promote_bundle(root: Path, slug: str) -> None:
    """Helper: create symlink in .active/."""
    active_dir = root / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    link = active_dir / slug
    target = f"../{slug}/{slug}.md"
    if not link.exists() and not link.is_symlink():
        os.symlink(target, link)


# ---------------------------------------------------------------------------
# Kind registration
# ---------------------------------------------------------------------------


def test_hook_kind_registered_from_vault(tmp_path):
    """Hook kind.json registers correctly via vault kinds discovery."""
    from artifacts_os.core import Registry, KindDef

    # Set up vault with hook kind.json copied from the real artifacts/kinds/hook/
    real_kind_json = (
        Path(__file__).parents[2] / "artifacts" / "kinds" / "hook" / "kind.json"
    )
    kinds_dir = tmp_path / "artifacts" / "kinds" / "hook"
    kinds_dir.mkdir(parents=True)
    (kinds_dir / "kind.json").write_text(real_kind_json.read_text())
    (kinds_dir / "ARTIFACT.md").write_text(
        "---\nkind: kind\nname: hook\ndescription: Hook bundle kind.\nagent: manual\n---\n"
    )
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    (tmp_path / "artifacts" / "hooks").mkdir(parents=True, exist_ok=True)

    registry = Registry([], root=tmp_path)
    kd = registry.get("hook")
    assert kd.name == "hook"
    assert kd.storage == "directory"
    assert kd.manifest_name == "{slug}.md"
    assert kd.numbered is False


def test_hook_kind_list_artifacts(tmp_path):
    """artifacts list --kind hook returns hook bundles via directory walker."""
    from artifacts_os.core import Registry, list_artifacts

    real_kind_json = (
        Path(__file__).parents[2] / "artifacts" / "kinds" / "hook" / "kind.json"
    )
    kinds_dir = tmp_path / "artifacts" / "kinds" / "hook"
    kinds_dir.mkdir(parents=True)
    (kinds_dir / "kind.json").write_text(real_kind_json.read_text())
    (kinds_dir / "ARTIFACT.md").write_text(
        "---\nkind: kind\nname: hook\ndescription: Hook bundle kind.\nagent: manual\n---\n"
    )
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")

    _make_bundle(tmp_path, "my-hook")

    registry = Registry([], root=tmp_path)
    items = list_artifacts(registry, kind="hook")
    assert len(items) == 1
    assert items[0].frontmatter.get("name") == "my-hook"


# ---------------------------------------------------------------------------
# Bundle manifest parsing and sibling-file resolution (D106)
# ---------------------------------------------------------------------------


def test_bundle_manifest_parses(tmp_path):
    """Bundle manifest frontmatter is read and Hook is constructed correctly."""
    _make_bundle(tmp_path, "test-hook")
    _promote_bundle(tmp_path, "test-hook")

    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    hooks = load_hooks_from_active(tmp_path)
    assert len(hooks) == 1
    h = hooks[0]
    assert h.name == "test-hook"
    assert h.source == "bundle"
    assert h.host == "artifacts-os"


def test_relative_action_command_resolves_against_bundle_dir(tmp_path):
    """Relative action.command paths are resolved against the bundle directory."""
    bundle_dir = _make_bundle(
        tmp_path, "rel-hook",
        action={"type": "shell", "command": "action.sh"}
    )
    # Create the script file so it exists (needed for path resolution).
    (bundle_dir / "action.sh").write_text("#!/bin/sh\necho hi\n")
    _promote_bundle(tmp_path, "rel-hook")

    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    hooks = load_hooks_from_active(tmp_path)
    assert len(hooks) == 1
    h = hooks[0]
    # The command should be an absolute path pointing inside the bundle dir.
    cmd = h.action.to_dict()["command"]
    assert os.path.isabs(cmd), f"expected absolute path, got: {cmd}"
    assert "rel-hook" in cmd


def test_relative_command_with_subdir(tmp_path):
    """Relative command like helpers/x.sh resolves against bundle dir."""
    bundle_dir = _make_bundle(
        tmp_path, "sub-hook",
        action={"type": "shell", "command": "helpers/util.sh"}
    )
    helpers = bundle_dir / "helpers"
    helpers.mkdir()
    (helpers / "util.sh").write_text("#!/bin/sh\n")
    _promote_bundle(tmp_path, "sub-hook")

    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    hooks = load_hooks_from_active(tmp_path)
    assert len(hooks) == 1
    cmd = hooks[0].action.to_dict()["command"]
    assert "helpers/util.sh" in cmd or "helpers" in cmd


def test_absolute_command_passes_through(tmp_path):
    """Absolute action.command paths pass through unchanged."""
    _make_bundle(
        tmp_path, "abs-hook",
        action={"type": "shell", "command": "/usr/bin/env"}
    )
    _promote_bundle(tmp_path, "abs-hook")

    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    hooks = load_hooks_from_active(tmp_path)
    assert len(hooks) == 1
    cmd = hooks[0].action.to_dict()["command"]
    assert cmd == "/usr/bin/env"


def test_plain_command_no_path_resolution(tmp_path):
    """A plain command name like 'echo' is not changed (no path resolution)."""
    _make_bundle(
        tmp_path, "echo-hook",
        action={"type": "shell", "command": "echo hello"}
    )
    _promote_bundle(tmp_path, "echo-hook")

    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    hooks = load_hooks_from_active(tmp_path)
    assert len(hooks) == 1
    cmd = hooks[0].action.to_dict()["command"]
    assert cmd == "echo hello"


# ---------------------------------------------------------------------------
# Loader merge: yaml + bundle, sorted
# ---------------------------------------------------------------------------


def _write_yaml_hooks(root: Path, entries: list[dict]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    data = {"layout_version": 1, "project": {"name": "test"}, "hooks": entries}
    (root / "artifacts.yaml").write_text(yaml.dump(data))


def test_load_hooks_merges_yaml_then_bundle(tmp_path):
    """load_hooks returns yaml entries first, then bundle entries sorted by slug."""
    _write_yaml_hooks(tmp_path, [
        {"name": "yaml-hook", "matcher": {"event": "*"}, "action": {"type": "shell", "command": "echo"}}
    ])
    _make_bundle(tmp_path, "bundle-hook")
    _promote_bundle(tmp_path, "bundle-hook")

    hooks = load_hooks(tmp_path)
    assert len(hooks) == 2
    assert hooks[0].name == "yaml-hook"
    assert hooks[0].source == "yaml"
    assert hooks[1].name == "bundle-hook"
    assert hooks[1].source == "bundle"


def test_load_hooks_bundle_sorted_by_slug(tmp_path):
    """Bundle hooks are returned sorted by slug."""
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    for slug in ["zebra-hook", "alpha-hook", "mango-hook"]:
        _make_bundle(tmp_path, slug)
        _promote_bundle(tmp_path, slug)

    hooks = load_hooks(tmp_path)
    names = [h.name for h in hooks]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# Host dispatch
# ---------------------------------------------------------------------------


def test_fire_list_includes_all_hosts(tmp_path):
    """s2073: host: field is tolerated but ignored — all hooks enter the fire-list."""
    from artifacts_os.hooks.actions import ShellAction

    hooks = [
        Hook(name="local", matcher={}, action=ShellAction(command="true"),
             source="bundle", host="artifacts-os"),
        Hook(name="foreign", matcher={}, action=ShellAction(command="true"),
             source="bundle", host="openstation"),
        Hook(name="unknown", matcher={}, action=ShellAction(command="true"),
             source="bundle", host="jira-bot"),
    ]
    fireable = _fire_list(hooks)
    assert len(fireable) == 3
    names = {h.name for h in fireable}
    assert names == {"local", "foreign", "unknown"}


def test_foreign_host_openstation_loaded_and_fired(tmp_path):
    """s2073: openstation hooks are loaded AND included in the fire-list."""
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    _make_bundle(tmp_path, "os-hook", host="openstation")
    _promote_bundle(tmp_path, "os-hook")

    hooks = load_hooks(tmp_path)
    # Loaded.
    assert any(h.name == "os-hook" for h in hooks)
    # Also in fire-list (host: ignored since s2073).
    fireable = _fire_list(hooks)
    assert any(h.name == "os-hook" for h in fireable)


def test_unknown_host_no_warning(tmp_path, capsys):
    """s2073: unknown host: values are silently tolerated — no warning emitted."""
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    _make_bundle(tmp_path, "jira-hook", host="jira-bot")
    _promote_bundle(tmp_path, "jira-hook")

    hooks = load_hooks(tmp_path)
    _fire_list(hooks)
    _fire_list(hooks)

    captured = capsys.readouterr()
    # No warning for unknown hosts since the host: field is now ignored
    assert "jira-bot" not in captured.err


# ---------------------------------------------------------------------------
# Legacy deprecation notice
# ---------------------------------------------------------------------------


def test_legacy_deprecation_printed_once(tmp_path, capsys):
    """Yaml hooks trigger the deprecation notice exactly once."""
    _write_yaml_hooks(tmp_path, [
        {"name": "h", "matcher": {"event": "*"}, "action": {"type": "shell", "command": "echo"}}
    ])

    load_hooks_from_yaml(tmp_path)
    load_hooks_from_yaml(tmp_path)  # second call — should NOT repeat

    captured = capsys.readouterr()
    assert captured.err.count("deprecation") == 1


def test_legacy_deprecation_suppressed_by_env(tmp_path, monkeypatch, capsys):
    """ARTIFACTS_HOOKS_LEGACY_QUIET=1 suppresses the deprecation notice."""
    monkeypatch.setenv("ARTIFACTS_HOOKS_LEGACY_QUIET", "1")
    _write_yaml_hooks(tmp_path, [
        {"name": "h", "matcher": {"event": "*"}, "action": {"type": "shell", "command": "echo"}}
    ])

    load_hooks_from_yaml(tmp_path)
    captured = capsys.readouterr()
    assert "deprecation" not in captured.err


# ---------------------------------------------------------------------------
# hook.skipped events
# ---------------------------------------------------------------------------


def test_hook_skipped_missing_target(tmp_path):
    """hook.skipped emitted when symlink target is missing."""
    skipped = []
    _events.register_emitter(
        lambda e, p: skipped.append(p) if e == "hook.skipped" else None
    )

    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    active_dir = tmp_path / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    # Create a dangling symlink (target doesn't exist).
    link = active_dir / "ghost-hook"
    os.symlink("../ghost-hook/ghost-hook.md", link)

    load_hooks_from_active(tmp_path)

    assert any(p["reason"] == "missing-target" for p in skipped)


def test_hook_skipped_parse_error(tmp_path):
    """hook.skipped emitted when manifest has no frontmatter."""
    skipped = []
    _events.register_emitter(
        lambda e, p: skipped.append(p) if e == "hook.skipped" else None
    )

    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    bundle_dir = tmp_path / "artifacts" / "hooks" / "bad-hook"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "bad-hook.md").write_text("# No frontmatter here\n")

    active_dir = tmp_path / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    os.symlink("../bad-hook/bad-hook.md", active_dir / "bad-hook")

    load_hooks_from_active(tmp_path)
    assert any(p["reason"] == "parse-error" for p in skipped)


def test_hook_skipped_escape_attempt(tmp_path):
    """hook.skipped emitted when manifest resolves outside artifacts/hooks/."""
    skipped = []
    _events.register_emitter(
        lambda e, p: skipped.append(p) if e == "hook.skipped" else None
    )

    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    # Create a manifest outside the hooks directory.
    escape_dir = tmp_path / "evil"
    escape_dir.mkdir()
    (escape_dir / "escape.md").write_text("---\nkind: hook\nname: escape\n---\n")

    active_dir = tmp_path / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    # Symlink pointing outside artifacts/hooks/.
    os.symlink(str(escape_dir / "escape.md"), active_dir / "escape")

    load_hooks_from_active(tmp_path)
    assert any(p["reason"] == "escape-attempt" for p in skipped)


# ---------------------------------------------------------------------------
# hook.fired / hook.failed source field
# ---------------------------------------------------------------------------


def test_hook_fired_carries_source(tmp_path):
    """hook.fired payload carries the source field (yaml | bundle)."""
    from artifacts_os.hooks.actions import ShellAction
    from artifacts_os.hooks.loader import run_matched

    fired = []
    _events.register_emitter(
        lambda e, p: fired.append(p) if e == "hook.fired" else None
    )

    yaml_hook = Hook(
        name="yaml-h", matcher={}, action=ShellAction(command="true"),
        source="yaml", host="artifacts-os"
    )
    bundle_hook = Hook(
        name="bundle-h", matcher={}, action=ShellAction(command="true"),
        source="bundle", host="artifacts-os"
    )
    run_matched([yaml_hook, bundle_hook], "artifact.created", {}, root=tmp_path)

    sources = [p.get("source") for p in fired]
    assert "yaml" in sources
    assert "bundle" in sources


def test_hook_failed_carries_source(tmp_path):
    """hook.failed payload carries the source field."""
    from artifacts_os.hooks.actions import ShellAction
    from artifacts_os.hooks.loader import run_matched

    failed = []
    _events.register_emitter(
        lambda e, p: failed.append(p) if e == "hook.failed" else None
    )

    hook = Hook(
        name="fail-h", matcher={}, action=ShellAction(command="exit 1"),
        source="bundle", host="artifacts-os"
    )
    run_matched([hook], "artifact.created", {})

    assert failed
    assert failed[0].get("source") == "bundle"


# ---------------------------------------------------------------------------
# Promote semantics
# ---------------------------------------------------------------------------


def test_promote_creates_symlink(tmp_path):
    """promote creates .active/<slug> → ../<slug>/<slug>.md."""
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\n")
    _make_bundle(tmp_path, "my-hook")

    result = promote(tmp_path, "my-hook")

    link = tmp_path / "artifacts" / "hooks" / ".active" / "my-hook"
    assert link.is_symlink() or link.exists()
    assert result.target == "../my-hook/my-hook.md"
    assert result.was_idempotent is False


def test_promote_idempotent_same_target(tmp_path):
    """promote is idempotent when called twice with the same target."""
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\n")
    _make_bundle(tmp_path, "idm-hook")

    promote(tmp_path, "idm-hook")
    result2 = promote(tmp_path, "idm-hook")

    assert result2.was_idempotent is True


def test_promote_divergent_target_errors_without_force(tmp_path):
    """Divergent target raises FileExistsError without --force."""
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\n")
    _make_bundle(tmp_path, "div-hook")

    # Create active entry with a different target.
    active_dir = tmp_path / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    link = active_dir / "div-hook"
    os.symlink("../other/other.md", link)

    with pytest.raises(FileExistsError, match="divergent"):
        promote(tmp_path, "div-hook", force=False)


def test_promote_divergent_target_force_succeeds(tmp_path):
    """With --force, a divergent target is overwritten."""
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\n")
    _make_bundle(tmp_path, "force-hook")

    active_dir = tmp_path / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    link = active_dir / "force-hook"
    os.symlink("../other/other.md", link)

    result = promote(tmp_path, "force-hook", force=True)
    assert result.target == "../force-hook/force-hook.md"


def test_promote_missing_bundle_raises(tmp_path):
    """promote raises FileNotFoundError for unknown bundle slug."""
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\n")
    with pytest.raises(FileNotFoundError):
        promote(tmp_path, "nonexistent")


def test_promote_emits_hook_promoted(tmp_path):
    """promote emits hook.promoted event."""
    promoted_events = []
    _events.register_emitter(
        lambda e, p: promoted_events.append(p) if e == "hook.promoted" else None
    )

    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\n")
    _make_bundle(tmp_path, "evt-hook")
    promote(tmp_path, "evt-hook")

    assert len(promoted_events) == 1
    assert promoted_events[0]["hook"] == "evt-hook"


# ---------------------------------------------------------------------------
# OSError stub fallback
# ---------------------------------------------------------------------------


def test_promote_oserror_fallback_writes_stub(tmp_path):
    """On OSError from os.symlink, promote writes a .json stub instead."""
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\n")
    _make_bundle(tmp_path, "stub-hook")

    with patch("os.symlink", side_effect=OSError("no symlinks")):
        result = promote(tmp_path, "stub-hook")

    assert result.was_stub is True
    stub = tmp_path / "artifacts" / "hooks" / ".active" / "stub-hook.json"
    assert stub.exists()
    data = json.loads(stub.read_text())
    assert data["target"] == "../stub-hook/stub-hook.md"


def test_loader_recognises_stub_form(tmp_path):
    """load_hooks_from_active reads .json stubs as well as symlinks."""
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\nproject:\n  name: test\n")
    _make_bundle(tmp_path, "stub-hook")

    # Write stub directly.
    active_dir = tmp_path / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    stub = active_dir / "stub-hook.json"
    stub.write_text(
        json.dumps({"target": "../stub-hook/stub-hook.md"}) + "\n",
        encoding="utf-8",
    )

    hooks = load_hooks_from_active(tmp_path)
    assert len(hooks) == 1
    assert hooks[0].name == "stub-hook"


# ---------------------------------------------------------------------------
# Demote semantics
# ---------------------------------------------------------------------------


def test_demote_unlinks_active(tmp_path):
    """demote removes the .active/ symlink."""
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\n")
    _make_bundle(tmp_path, "dm-hook")
    promote(tmp_path, "dm-hook")

    result = demote(tmp_path, "dm-hook")
    assert result is True

    link = tmp_path / "artifacts" / "hooks" / ".active" / "dm-hook"
    assert not link.exists() and not link.is_symlink()


def test_demote_noop_on_absent(tmp_path):
    """demote is a no-op when the slug is not active."""
    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\n")
    result = demote(tmp_path, "never-promoted")
    assert result is False


def test_demote_emits_hook_demoted(tmp_path):
    """demote emits hook.demoted event."""
    demoted_events = []
    _events.register_emitter(
        lambda e, p: demoted_events.append(p) if e == "hook.demoted" else None
    )

    (tmp_path / "artifacts.yaml").write_text("layout_version: 1\n")
    _make_bundle(tmp_path, "evtd-hook")
    promote(tmp_path, "evtd-hook")
    invalidate_cache()
    demoted_events.clear()

    demote(tmp_path, "evtd-hook")
    assert len(demoted_events) == 1
    assert demoted_events[0]["hook"] == "evtd-hook"


# ---------------------------------------------------------------------------
# active_state
# ---------------------------------------------------------------------------


def test_active_state_yes(tmp_path):
    _make_bundle(tmp_path, "st-hook")
    promote(tmp_path, "st-hook")
    assert active_state(tmp_path, "st-hook") == "yes"


def test_active_state_no(tmp_path):
    _make_bundle(tmp_path, "st-hook")
    assert active_state(tmp_path, "st-hook") == "no"


def test_active_state_dangling(tmp_path):
    active_dir = tmp_path / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    link = active_dir / "gone-hook"
    os.symlink("../gone-hook/gone-hook.md", link)
    assert active_state(tmp_path, "gone-hook") == "dangling"


# ---------------------------------------------------------------------------
# demote_prune
# ---------------------------------------------------------------------------


def test_prune_removes_dangling(tmp_path):
    """demote_prune removes dangling .active/ entries."""
    pruned_events = []
    _events.register_emitter(
        lambda e, p: pruned_events.append(p) if e == "hook.demoted" else None
    )

    active_dir = tmp_path / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    link = active_dir / "ghost"
    os.symlink("../ghost/ghost.md", link)

    pruned = demote_prune(tmp_path)
    assert "ghost" in pruned
    assert not link.is_symlink()
    assert any(p["reason"] == "prune" for p in pruned_events)


def test_prune_dry_run_is_inert(tmp_path):
    """demote_prune with dry_run=True makes no FS changes."""
    active_dir = tmp_path / "artifacts" / "hooks" / ".active"
    active_dir.mkdir(parents=True, exist_ok=True)
    link = active_dir / "ghost2"
    os.symlink("../ghost2/ghost2.md", link)

    pruned = demote_prune(tmp_path, dry_run=True)
    assert "ghost2" in pruned
    # File still exists.
    assert link.is_symlink()


# ---------------------------------------------------------------------------
# ALL_EVENT_TYPES
# ---------------------------------------------------------------------------


def test_all_event_types_includes_new_events():
    from artifacts_os.events.catalog import ALL_EVENT_TYPES

    for name in ("hook.skipped", "hook.promoted", "hook.demoted", "hook.pulled"):
        assert name in ALL_EVENT_TYPES, f"{name!r} missing from ALL_EVENT_TYPES"
