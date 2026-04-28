---
kind: task
id: t0026
name: implement-views-viewssettings
type: implementation
status: done
assignee: developer
owner: user
depends_on:
  - "[[t0025-implement-core-load-settings]]"
created: 2026-04-28
started: 2026-04-28
completed: 2026-04-28
---

# Implement Views.Viewssettings

# Implement views.ViewsSettings

## Context

s0007-artifacts-os-views-module defines the views module, including
its settings: `ViewConfig`, `ViewsConfig`, and `ViewsSettings(Settings)`.
This task implements those types and the `from_base` parser.

Depends on the base `Settings` class landing first (task to implement
`core.load_settings`).

See [[s0007-artifacts-os-views-module]] and
[[s0010-core-settings-module-spec]] for the design.

## Requirements

1. **Add to `src/artifacts_os/views/models.py`:**
   - `@dataclass class ViewConfig`:
     - `columns: str` (required, comma-separated field spec string)
     - `filters: dict[str, Any] = field(default_factory=dict)`
     - `sort: str | None = None`
   - `@dataclass class ViewsConfig`:
     - `views: dict[str, ViewConfig]`
     - `default_views: dict[str, str]`
   - `@dataclass(kw_only=True) class ViewsSettings(Settings)`:
     - inherits `layout_version`, `project`, `raw` from `Settings`
     - adds `views: ViewsConfig | None = None`
     - `@classmethod from_base(cls, base: Settings) -> "ViewsSettings"`
       reads `base.raw["views"]` and `base.raw["default_views"]`,
       parses each view entry via private `_parse_view`, and returns
       a populated `ViewsSettings`. If neither key is present,
       `views=None`.
   - private `_parse_view(d: dict) -> ViewConfig`:
     - require `columns`; raise `ValueError` if missing
     - default `filters` to `{}`
     - pass through `sort` as-is (preserve `-` prefix)
2. **Update `src/artifacts_os/views/__init__.py`** to export
   `ViewConfig`, `ViewsConfig`, `ViewsSettings`.
3. **Tests in `tests/views/test_views_settings.py`** (no mocking):
   - `from_base` with no `views`/`default_views` keys →
     `settings.views is None`.
   - `from_base` with full views dict → each `ViewConfig` populated
     correctly (`columns`, `filters`, `sort`).
   - `default_views` mapping preserved.
   - missing `columns` in a view entry → `ValueError`.
   - `sort: -started` parsed as `"-started"` (prefix preserved).
   - empty `filters` defaults to `{}`.
   - end-to-end: `load_settings(path)` → `ViewsSettings.from_base(base)`
     produces a usable settings object.

## Findings

Created `src/artifacts_os/views/models.py` with `ViewConfig`, `ViewsConfig`, and `ViewsSettings`. `ViewsSettings.from_base` reads only from `base.raw` — never opens a file. Updated `views/__init__.py` to re-export all three symbols. Added `tests/views/test_views_settings.py` covering all seven required cases. Full suite: 163 tests pass. DAG constraint verified: `core` has no imports of the new symbols.

## Progress

### 2026-04-28 — developer
> time: 18:11

Implemented ViewConfig, ViewsConfig, ViewsSettings in views/models.py; updated views/__init__.py exports; wrote 7 tests — all 163 tests pass.

## Verification

- [x] `views/models.py` defines `ViewConfig`, `ViewsConfig`, `ViewsSettings`
- [x] `ViewsSettings.from_base` reads only from `base.raw`, never
      opens a file
- [x] `views/__init__.py` re-exports the three new symbols
- [x] Test file covers all seven listed cases
- [x] `pytest tests/views/test_views_settings.py` passes
- [x] `core` does not import `ViewConfig` / `ViewsConfig` / `ViewsSettings`

## Verification Report

*Verified: 2026-04-28*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `views/models.py` defines `ViewConfig`, `ViewsConfig`, `ViewsSettings` | PASS | `src/artifacts_os/views/models.py` lines 15, 24, 32 declare all three dataclasses |
| 2 | `ViewsSettings.from_base` reads only from `base.raw`, never opens a file | PASS | `models.py` contains no `open(`, `read_text`, or `loads` calls; `from_base` only reads `base.raw.get("views")` and `base.raw.get("default_views")` |
| 3 | `views/__init__.py` re-exports the three new symbols | PASS | `__init__.py` line 20 imports them and lines 28–30 list all three in `__all__` |
| 4 | Test file covers all seven listed cases | PASS | `tests/views/test_views_settings.py` has 7 tests covering: no-keys-None, full-dict, default_views preserved, missing-columns ValueError, sort dash-prefix, empty filters, end-to-end |
| 5 | `pytest tests/views/test_views_settings.py` passes | PASS | All 7 tests passed in 0.65s |
| 6 | `core` does not import `ViewConfig` / `ViewsConfig` / `ViewsSettings` | PASS | Grep over `src/artifacts_os/core` returned no matches |

### Summary

6 passed, 0 failed. All verification criteria met — task ready to transition to verified.
