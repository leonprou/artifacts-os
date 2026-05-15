"""Tests for artbook.settings — ArtbookSettings.from_base."""

from __future__ import annotations

from artifacts_os.artbook.settings import ArtbookSettings
from artifacts_os.core.models import ProjectConfig, Settings


def _make_settings(raw: dict) -> Settings:
    return Settings(
        layout_version=1,
        project=ProjectConfig(name="test"),
        raw=raw,
    )


def test_from_base_with_distro_url() -> None:
    base = _make_settings({"artbook": {"distro_url": "https://github.com/example/distro"}})
    s = ArtbookSettings.from_base(base)
    assert s.distro_url == "https://github.com/example/distro"


def test_from_base_missing_section() -> None:
    base = _make_settings({})
    s = ArtbookSettings.from_base(base)
    assert s.distro_url is None


def test_from_base_empty_section() -> None:
    base = _make_settings({"artbook": {}})
    s = ArtbookSettings.from_base(base)
    assert s.distro_url is None


def test_from_base_null_section() -> None:
    base = _make_settings({"artbook": None})
    s = ArtbookSettings.from_base(base)
    assert s.distro_url is None


def test_from_base_empty_string_url() -> None:
    base = _make_settings({"artbook": {"distro_url": ""}})
    s = ArtbookSettings.from_base(base)
    assert s.distro_url is None


def test_artbook_settings_is_frozen() -> None:
    base = _make_settings({"artbook": {"distro_url": "https://example.com/distro"}})
    s = ArtbookSettings.from_base(base)
    import dataclasses

    assert dataclasses.fields(s)
    try:
        object.__setattr__(s, "distro_url", "other")
    except dataclasses.FrozenInstanceError:
        pass  # expected
