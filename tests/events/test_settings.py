"""Tests for events/settings.py and hooks/settings.py — C6.

Verification criteria: C6 pattern from s0025-artifact-events.
"""
from pathlib import Path

from artifacts_os.core.models import ProjectConfig, Settings
from artifacts_os.events.settings import EventsSettings
from artifacts_os.hooks.settings import HooksSettings


def _base(raw: dict) -> Settings:
    return Settings(
        layout_version=1,
        project=ProjectConfig(name="test"),
        raw=raw,
    )


class TestEventsSettings:
    def test_defaults(self):
        s = EventsSettings.from_base(_base({}))
        assert s.enabled is True
        assert s.dir is None

    def test_enabled_false(self):
        s = EventsSettings.from_base(_base({"events": {"enabled": False}}))
        assert s.enabled is False

    def test_custom_dir(self):
        s = EventsSettings.from_base(_base({"events": {"dir": "custom/logs"}}))
        assert s.dir == Path("custom/logs")

    def test_inherits_base_fields(self):
        raw = {"events": {"enabled": True}}
        s = EventsSettings.from_base(_base(raw))
        assert s.layout_version == 1
        assert s.project.name == "test"
        assert s.raw is raw

    def test_empty_events_section_uses_defaults(self):
        s = EventsSettings.from_base(_base({"events": {}}))
        assert s.enabled is True
        assert s.dir is None


class TestHooksSettings:
    def test_defaults(self):
        s = HooksSettings.from_base(_base({}))
        assert s.hooks == []

    def test_hooks_list(self):
        raw = {
            "hooks": [
                {
                    "name": "my-hook",
                    "matcher": {"event": "artifact.created"},
                    "action": {"type": "shell", "command": "echo"},
                }
            ]
        }
        s = HooksSettings.from_base(_base(raw))
        assert len(s.hooks) == 1
        assert s.hooks[0]["name"] == "my-hook"

    def test_inherits_base_fields(self):
        s = HooksSettings.from_base(_base({}))
        assert s.layout_version == 1
        assert s.project.name == "test"
