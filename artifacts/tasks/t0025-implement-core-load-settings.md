---
kind: task
id: t0025
name: implement-core-load-settings
type: implementation
status: done
assignee: developer
owner: user
created: 2026-04-28
started: 2026-04-28
completed: 2026-04-28
---

# Implement Core.Load_Settings

# Implement core.load_settings

## Context

s0010-core-settings-module-spec defines a settings facility owned by
`artifacts_os.core`. This task implements the base loader and the
`Settings` / `ProjectConfig` dataclasses.

See [[s0010-core-settings-module-spec]] for the full design,
including the rationale for `core.Settings` being a base class that
other modules extend.

## Requirements

1. **Add `src/artifacts_os/core/settings.py`** with:
   - `class UnsupportedSchemaVersion(ValueError)` — raised on
     missing or unsupported `layout_version`.
   - `def load_settings(path: Path) -> Settings`:
     - Read and YAML-parse the file at `path`.
     - Validate `layout_version`: missing → raise
       `UnsupportedSchemaVersion("missing layout_version")`;
       value not in `{1}` → raise
       `UnsupportedSchemaVersion(f"unsupported version {N}")`.
     - Build `ProjectConfig` from the `project` section (required).
     - Store the full parsed YAML dict on `Settings.raw`.
     - Return the populated `Settings`.
2. **Add to `src/artifacts_os/core/models.py`:**
   - `@dataclass class ProjectConfig` with `name: str`,
     `alias: str | None = None`.
   - `@dataclass(kw_only=True) class Settings` with
     `layout_version: int`, `project: ProjectConfig`,
     `raw: dict[str, Any] = field(default_factory=dict)`.
3. **Re-export from `src/artifacts_os/core/__init__.py`:**
   - `load_settings`, `UnsupportedSchemaVersion`,
     `Settings`, `ProjectConfig`.
4. **Tests in `tests/core/test_settings.py`** (use `tmp_path` +
   `make_vault` fixture per project conventions; no mocking):
   - happy path: `layout_version: 1` + valid `project` →
     returns populated `Settings`.
   - missing `layout_version` → `UnsupportedSchemaVersion`.
   - `layout_version: 2` → `UnsupportedSchemaVersion`.
   - missing `project` section → raises.
   - `project.alias` absent → `ProjectConfig.alias is None`.
   - extra top-level keys (e.g. `views`, `run`) preserved verbatim
     in `Settings.raw`.

## Findings

Implemented the full settings facility for `artifacts_os.core`:

- **`src/artifacts_os/core/settings.py`** — `load_settings(path)` reads + YAML-parses the file, validates `layout_version` (missing → `UnsupportedSchemaVersion("missing layout_version")`; unsupported N → `UnsupportedSchemaVersion(f"unsupported version {N}")`), builds `ProjectConfig`, stores the full dict in `Settings.raw`, returns populated `Settings`.
- **`src/artifacts_os/core/models.py`** — added `ProjectConfig` (`name: str`, `alias: str | None = None`) and `Settings` (`kw_only=True` dataclass with `layout_version`, `project`, `raw`). `typing.Any` import added.
- **`src/artifacts_os/core/__init__.py`** — re-exports all four symbols: `load_settings`, `UnsupportedSchemaVersion`, `Settings`, `ProjectConfig`.
- **`tests/core/test_settings.py`** — 6 tests covering all required cases: happy path, missing layout_version, unsupported version, missing project, alias absent, extra top-level keys in raw.

All 6 new tests pass; full core suite (69 tests) remains green. No imports from `views`, `cli`, `tui`, `log`, or `ai` in `core`.

## Progress

### 2026-04-28 — developer
> time: 18:08

Implemented settings.py with load_settings + UnsupportedSchemaVersion, added ProjectConfig + Settings to models.py, re-exported from core/__init__.py, wrote 6 tests — all pass (69 core tests green).

## Verification

- [ ] `core/settings.py` exists with `load_settings` and
      `UnsupportedSchemaVersion`
- [ ] `core/models.py` exports `Settings` and `ProjectConfig`
- [ ] `core/__init__.py` re-exports the four symbols
- [ ] Test file covers all six listed cases
- [ ] `pytest tests/core/test_settings.py` passes
- [ ] No imports from `views`, `cli`, `tui`, `log`, or `ai` in `core`
