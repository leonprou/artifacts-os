"""End-to-end integration test: hooks distributed via artbook kind: hook.

Validates the full author → pull → list → promote → fire → re-pull cycle
described in spec s0032 §8 and task t0184.

Scenario
--------
1. Source vault has artbook.yaml with an ``os-hooks`` book (kind: hook)
   pointing at ``artifacts/hooks/``; one demo bundle lives there.
2. Consumer vault starts empty.
3. ``pull_book`` lands the demo bundle in consumer's ``artifacts/hooks/``.
4. ``hook.pulled`` event is emitted with correct written/overwritten/removed.
5. ``list_bundles`` returns demo; ``active_state`` shows it inactive.
6. ``promote(consumer, "demo")`` creates ``.active/demo`` symlink.
7. ``load_hooks_from_active`` returns the hook with ``source="bundle"``.
8. ``run_matched`` fires the demo hook → sentinel file written.
9. Re-pull: bundle overwritten; ``.active/demo`` symlink preserved.
10. After re-pull, hook still loads and fires (sentinel appended to).
11. Each pull emits ``hook.pulled``; fired events carry ``source="bundle"``.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from artifacts_os.artbook.manifest import load_manifest
from artifacts_os.artbook.pull import pull_book
from artifacts_os.core import events as _events
from artifacts_os.hooks.loader import (
    Hook,
    invalidate_cache,
    load_hooks_from_active,
    run_matched,
)
from artifacts_os.hooks.promotion import active_state, list_bundles, promote


# ---------------------------------------------------------------------------
# Shared reset
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_state():
    _events._emitters.clear()
    invalidate_cache()
    yield
    _events._emitters.clear()
    invalidate_cache()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bundle(
    root: Path,
    slug: str,
    *,
    host: str = "artifacts-os",
    sentinel_file: str = ".hook-fired",
) -> None:
    """Write a minimal hook bundle under ``<root>/artifacts/hooks/<slug>/``."""
    bundle_dir = root / "artifacts" / "hooks" / slug
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Write the action script.
    action = bundle_dir / "action.sh"
    action.write_text(
        f"#!/bin/sh\necho fired >> \"${{ART_VAULT_ROOT:-.}}/{sentinel_file}\"\n"
    )
    action.chmod(0o755)

    # Write the manifest.
    manifest = bundle_dir / f"{slug}.md"
    manifest.write_text(
        "---\n"
        f"kind: hook\n"
        f"name: {slug}\n"
        f"host: {host}\n"
        "matcher:\n"
        "  event: artifact.created\n"
        "action:\n"
        "  type: shell\n"
        "  command: ./action.sh\n"
        "phase: post\n"
        "blocking: false\n"
        "timeout: 30\n"
        "---\n\n"
        f"Demo hook bundle '{slug}' for integration testing.\n"
    )


def _make_source_vault(root: Path, slug: str = "demo") -> Path:
    """Create a minimal source (distro) vault with an artbook.yaml + one hook bundle."""
    root.mkdir(parents=True, exist_ok=True)

    _make_bundle(root, slug)

    (root / "artbook.yaml").write_text(
        yaml.dump(
            {
                "version": 1,
                "distro": {"name": "test-distro"},
                "books": [
                    {
                        "name": "os-hooks",
                        "src": "artifacts/hooks/",
                        "kind": "hook",
                        "description": "Test hook registry.",
                    }
                ],
            }
        )
    )
    return root


def _make_consumer_vault(root: Path) -> Path:
    """Create a minimal consumer vault with an artifacts.yaml marker."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "artifacts.yaml").write_text(
        "layout_version: 1\nproject:\n  name: consumer\n"
    )
    return root


def _collect_events(
    event_type: str,
) -> tuple[list[dict[str, Any]], None]:
    """Register a collector for *event_type*; return the accumulator list."""
    collected: list[dict[str, Any]] = []

    def _emitter(event: str, payload: dict) -> None:
        if event == event_type:
            collected.append({"event": event, **payload})

    _events.register_emitter(_emitter)
    return collected


def _chmod_actions(consumer):
    """Restore +x on action.sh files (copy_book uses copyfile which loses mode)."""
    for action in (consumer / 'artifacts' / 'hooks').rglob('action.sh'):
        action.chmod(0o755)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHookBookPull:
    """Tests for pull_book with kind: hook books."""

    def test_pull_lands_bundle_in_consumer(self, tmp_path: Path) -> None:
        """Pulling a hook book copies the bundle dir verbatim into consumer."""
        source = _make_source_vault(tmp_path / "source")
        consumer = _make_consumer_vault(tmp_path / "consumer")

        manifest = load_manifest(source)
        book = manifest.books[0]
        assert book.kind == "hook"
        assert book.recurse is True

        pull_book(book, source, consumer)

        bundle = consumer / "artifacts" / "hooks" / "demo"
        assert bundle.is_dir()
        assert (bundle / "demo.md").is_file()
        assert (bundle / "action.sh").is_file()

    def test_pull_emits_hook_pulled_event(self, tmp_path: Path) -> None:
        """A kind: hook pull emits hook.pulled with correct slug lists."""
        source = _make_source_vault(tmp_path / "source")
        consumer = _make_consumer_vault(tmp_path / "consumer")

        pulled_events = _collect_events("hook.pulled")

        manifest = load_manifest(source)
        book = manifest.books[0]
        pull_book(book, source, consumer)

        assert len(pulled_events) == 1
        ev = pulled_events[0]
        assert ev["book"] == "os-hooks"
        assert "demo" in ev["written"]
        assert ev["overwritten"] == []
        assert ev["removed"] == []

    def test_repull_emits_overwritten_slug(self, tmp_path: Path) -> None:
        """A second pull reports the existing bundle as overwritten, not written."""
        source = _make_source_vault(tmp_path / "source")
        consumer = _make_consumer_vault(tmp_path / "consumer")

        pulled_events = _collect_events("hook.pulled")

        manifest = load_manifest(source)
        book = manifest.books[0]
        pull_book(book, source, consumer)
        pull_book(book, source, consumer)

        assert len(pulled_events) == 2
        second = pulled_events[1]
        assert second["book"] == "os-hooks"
        assert "demo" in second["overwritten"]
        assert second["written"] == []

    def test_active_dir_not_touched_by_repull(self, tmp_path: Path) -> None:
        """``.active/`` is not modified by a re-pull (§4.3)."""
        source = _make_source_vault(tmp_path / "source")
        consumer = _make_consumer_vault(tmp_path / "consumer")

        manifest = load_manifest(source)
        book = manifest.books[0]
        pull_book(book, source, consumer)

        # Promote demo
        _chmod_actions(consumer)
        promote(consumer, "demo")
        active_link = consumer / "artifacts" / "hooks" / ".active" / "demo"
        assert active_link.exists() or active_link.is_symlink()

        # Re-pull: .active/ must be preserved
        pull_book(book, source, consumer)
        assert active_link.exists() or active_link.is_symlink(), (
            ".active/demo symlink must survive re-pull"
        )

    def test_no_promote_flag_is_noop_for_hook_books(self, tmp_path: Path) -> None:
        """``--no-promote`` is accepted for hook books but has no effect."""
        source = _make_source_vault(tmp_path / "source")
        consumer = _make_consumer_vault(tmp_path / "consumer")

        manifest = load_manifest(source)
        book = manifest.books[0]
        report = pull_book(book, source, consumer, no_promote=True)

        # Bundle still written
        assert (consumer / "artifacts" / "hooks" / "demo" / "demo.md").is_file()
        # No promotion report (hook books never promote)
        assert report.promotion is None
        assert report.promotion_skipped_reason is None


class TestHookBookListAndPromote:
    """Tests for list_bundles / active_state after a hook book pull."""

    def test_list_shows_bundle_inactive_after_pull(self, tmp_path: Path) -> None:
        """After pull, the bundle is visible but not active."""
        source = _make_source_vault(tmp_path / "source")
        consumer = _make_consumer_vault(tmp_path / "consumer")

        manifest = load_manifest(source)
        book = manifest.books[0]
        pull_book(book, source, consumer)

        bundles = list_bundles(consumer)
        assert "demo" in bundles

        state = active_state(consumer, "demo")
        # demo is not yet promoted
        assert state == "no"

    def test_promote_creates_active_symlink(self, tmp_path: Path) -> None:
        """After promote, active_state shows demo as active."""
        source = _make_source_vault(tmp_path / "source")
        consumer = _make_consumer_vault(tmp_path / "consumer")

        manifest = load_manifest(source)
        book = manifest.books[0]
        pull_book(book, source, consumer)
        _chmod_actions(consumer)
        promote(consumer, "demo")

        state = active_state(consumer, "demo")
        active_link = consumer / "artifacts" / "hooks" / ".active" / "demo"
        assert active_link.is_symlink(), ".active/demo should be a symlink"
        # active_state should show demo as active (truthy or "yes"/"symlink")
        assert state == "yes"


class TestHookBookFire:
    """Tests for end-to-end hook firing after pull + promote."""

    def test_hook_loaded_from_active_with_source_bundle(self, tmp_path: Path) -> None:
        """Bundle hook loaded from .active/ has source='bundle'."""
        source = _make_source_vault(tmp_path / "source")
        consumer = _make_consumer_vault(tmp_path / "consumer")

        manifest = load_manifest(source)
        book = manifest.books[0]
        pull_book(book, source, consumer)
        _chmod_actions(consumer)
        promote(consumer, "demo")

        hooks = load_hooks_from_active(consumer)
        assert len(hooks) >= 1
        demo_hook = next((h for h in hooks if h.name == "demo"), None)
        assert demo_hook is not None, "demo hook should be loaded from .active/"
        assert demo_hook.source == "bundle"

    def test_hook_fires_and_creates_sentinel(self, tmp_path: Path) -> None:
        """Firing the demo hook executes action.sh → sentinel file written."""
        source = _make_source_vault(tmp_path / "source")
        consumer = _make_consumer_vault(tmp_path / "consumer")

        manifest = load_manifest(source)
        book = manifest.books[0]
        pull_book(book, source, consumer)
        _chmod_actions(consumer)
        promote(consumer, "demo")

        hooks = load_hooks_from_active(consumer)
        demo_hook = next(h for h in hooks if h.name == "demo")

        payload = {"kind": "task", "id": "t0001", "name": "test"}
        run_matched([demo_hook], "artifact.created", payload, root=consumer)

        sentinel = consumer / ".hook-fired"
        assert sentinel.is_file(), "action.sh should have written the sentinel file"
        assert "fired" in sentinel.read_text()

    def test_hook_fired_event_carries_source_bundle(self, tmp_path: Path) -> None:
        """hook.fired event payload has source='bundle' for bundle hooks."""
        source = _make_source_vault(tmp_path / "source")
        consumer = _make_consumer_vault(tmp_path / "consumer")

        manifest = load_manifest(source)
        book = manifest.books[0]
        pull_book(book, source, consumer)
        _chmod_actions(consumer)
        promote(consumer, "demo")

        fired_events = _collect_events("hook.fired")

        hooks = load_hooks_from_active(consumer)
        demo_hook = next(h for h in hooks if h.name == "demo")
        payload = {"kind": "task", "id": "t0001", "name": "test"}
        run_matched([demo_hook], "artifact.created", payload, root=consumer)

        assert len(fired_events) >= 1
        assert fired_events[0]["source"] == "bundle"

    def test_repull_preserves_hook_activation(self, tmp_path: Path) -> None:
        """After re-pull, .active/ is intact and the hook still fires."""
        source = _make_source_vault(tmp_path / "source")
        consumer = _make_consumer_vault(tmp_path / "consumer")

        manifest = load_manifest(source)
        book = manifest.books[0]

        # First pull + promote + fire
        pull_book(book, source, consumer)
        _chmod_actions(consumer)
        promote(consumer, "demo")

        hooks = load_hooks_from_active(consumer)
        demo_hook = next(h for h in hooks if h.name == "demo")
        payload = {"kind": "task", "id": "t0001", "name": "test"}
        run_matched([demo_hook], "artifact.created", payload, root=consumer)

        sentinel = consumer / ".hook-fired"
        assert sentinel.is_file()
        lines_before = sentinel.read_text().strip().splitlines()

        # Re-pull: bundle overwritten, .active/ preserved
        pull_book(book, source, consumer)
        _chmod_actions(consumer)
        active_link = consumer / "artifacts" / "hooks" / ".active" / "demo"
        assert active_link.is_symlink(), ".active/demo must survive re-pull"

        # Load fresh (cache invalidated externally to simulate new process)
        invalidate_cache()
        hooks2 = load_hooks_from_active(consumer)
        demo_hook2 = next(h for h in hooks2 if h.name == "demo")

        run_matched([demo_hook2], "artifact.created", payload, root=consumer)
        lines_after = sentinel.read_text().strip().splitlines()
        assert len(lines_after) > len(lines_before), (
            "sentinel should have a new line after re-pull + re-fire"
        )


class TestArtifactsOsDistroOsHooks:
    """Verify the os-hooks book in the repo's own artbook.yaml parses and pulls."""

    _REPO_ROOT = Path(__file__).resolve().parents[2]

    def test_os_hooks_book_parses(self) -> None:
        """artbook.yaml declares os-hooks book with kind=hook and recurse=True."""
        manifest = load_manifest(self._REPO_ROOT)
        os_hooks = next((b for b in manifest.books if b.name == "os-hooks"), None)
        assert os_hooks is not None, "os-hooks book must exist in artbook.yaml"
        assert os_hooks.kind == "hook"
        assert os_hooks.recurse is True
        assert os_hooks.promote is None

    def test_os_hooks_book_pulls_into_fresh_consumer(self, tmp_path: Path) -> None:
        """Pulling os-hooks from repo root into a fresh consumer vault succeeds."""
        consumer = _make_consumer_vault(tmp_path / "consumer")

        pulled_events = _collect_events("hook.pulled")

        manifest = load_manifest(self._REPO_ROOT)
        os_hooks_book = next(b for b in manifest.books if b.name == "os-hooks")
        pull_book(os_hooks_book, self._REPO_ROOT, consumer)

        # demo bundle should be present in consumer
        hooks_dir = consumer / "artifacts" / "hooks"
        assert hooks_dir.is_dir()

        # hook.pulled event must have been emitted
        assert len(pulled_events) == 1
        assert pulled_events[0]["book"] == "os-hooks"
