"""Tests for ViewConfig, ViewsConfig, and ViewsSettings.

Spec: s0007-artifacts-os-views-module
"""

import pytest

from artifacts_os.core import load_settings
from artifacts_os.views import ViewConfig, ViewsConfig, ViewsSettings


def _write_yaml(tmp_path, content: str):
    p = tmp_path / "artifacts.yaml"
    p.write_text(content)
    return p


def _base_yaml(extra: str = "") -> str:
    return f"layout_version: 1\nproject:\n  name: testproject\n{extra}"


# ---------------------------------------------------------------------------
# from_base with no views / default_views
# ---------------------------------------------------------------------------


def test_no_views_keys_gives_none(tmp_path):
    """from_base with no views/default_views keys → settings.views is None."""
    path = _write_yaml(tmp_path, _base_yaml())
    base = load_settings(path)
    settings = ViewsSettings.from_base(base)
    assert settings.views is None


# ---------------------------------------------------------------------------
# from_base with full views dict
# ---------------------------------------------------------------------------


def test_full_views_dict_populated(tmp_path):
    """from_base with full views dict → each ViewConfig populated correctly."""
    yaml_content = _base_yaml(
        "views:\n"
        "  active:\n"
        "    columns: id,name,status\n"
        "    filters:\n"
        "      status: in-progress\n"
        "    sort: name\n"
        "  sessions:\n"
        "    columns: id,task,agent\n"
        "    sort: -started\n"
    )
    path = _write_yaml(tmp_path, yaml_content)
    base = load_settings(path)
    settings = ViewsSettings.from_base(base)

    assert settings.views is not None
    assert isinstance(settings.views, ViewsConfig)

    active = settings.views.views["active"]
    assert active.columns == "id,name,status"
    assert active.filters == {"status": "in-progress"}
    assert active.sort == "name"

    sessions = settings.views.views["sessions"]
    assert sessions.columns == "id,task,agent"
    assert sessions.sort == "-started"


# ---------------------------------------------------------------------------
# default_views mapping preserved
# ---------------------------------------------------------------------------


def test_default_views_mapping_preserved(tmp_path):
    """default_views mapping is preserved exactly as parsed."""
    yaml_content = _base_yaml(
        "views:\n"
        "  sessions:\n"
        "    columns: id,task\n"
        "default_views:\n"
        "  session: sessions\n"
        "  task: active\n"
    )
    path = _write_yaml(tmp_path, yaml_content)
    base = load_settings(path)
    settings = ViewsSettings.from_base(base)

    assert settings.views is not None
    assert settings.views.default_views == {"session": "sessions", "task": "active"}


# ---------------------------------------------------------------------------
# missing columns raises ValueError
# ---------------------------------------------------------------------------


def test_missing_columns_raises_value_error(tmp_path):
    """A view entry without 'columns' raises ValueError."""
    yaml_content = _base_yaml(
        "views:\n"
        "  bad-view:\n"
        "    sort: name\n"
    )
    path = _write_yaml(tmp_path, yaml_content)
    base = load_settings(path)
    with pytest.raises(ValueError, match="columns"):
        ViewsSettings.from_base(base)


# ---------------------------------------------------------------------------
# sort with "-" prefix preserved
# ---------------------------------------------------------------------------


def test_sort_with_dash_prefix_preserved(tmp_path):
    """sort: -started is parsed as '-started' (prefix preserved)."""
    yaml_content = _base_yaml(
        "views:\n"
        "  log:\n"
        "    columns: id,started\n"
        "    sort: -started\n"
    )
    path = _write_yaml(tmp_path, yaml_content)
    base = load_settings(path)
    settings = ViewsSettings.from_base(base)
    assert settings.views is not None
    assert settings.views.views["log"].sort == "-started"


# ---------------------------------------------------------------------------
# empty filters defaults to {}
# ---------------------------------------------------------------------------


def test_empty_filters_defaults_to_empty_dict(tmp_path):
    """A view entry with no filters field defaults to {}."""
    yaml_content = _base_yaml(
        "views:\n"
        "  simple:\n"
        "    columns: id,name\n"
    )
    path = _write_yaml(tmp_path, yaml_content)
    base = load_settings(path)
    settings = ViewsSettings.from_base(base)
    assert settings.views is not None
    assert settings.views.views["simple"].filters == {}


# ---------------------------------------------------------------------------
# end-to-end: load_settings → ViewsSettings.from_base
# ---------------------------------------------------------------------------


def test_end_to_end_load_settings_then_from_base(tmp_path):
    """End-to-end: load_settings(path) → ViewsSettings.from_base(base) works."""
    yaml_content = _base_yaml(
        "views:\n"
        "  active:\n"
        "    columns: id,name,assignee,status\n"
        "    filters:\n"
        "      status: ready\n"
        "default_views:\n"
        "  task: active\n"
    )
    path = _write_yaml(tmp_path, yaml_content)
    base = load_settings(path)
    settings = ViewsSettings.from_base(base)

    # Base fields inherited
    assert settings.layout_version == 1
    assert settings.project.name == "testproject"

    # Views populated
    assert settings.views is not None
    vc = settings.views.views["active"]
    assert isinstance(vc, ViewConfig)
    assert vc.columns == "id,name,assignee,status"
    assert vc.filters == {"status": "ready"}
    assert vc.sort is None

    # default_views
    assert settings.views.default_views == {"task": "active"}
