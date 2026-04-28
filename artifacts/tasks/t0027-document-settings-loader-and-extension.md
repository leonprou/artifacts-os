---
kind: task
id: t0027
name: document-settings-loader-and-extension
type: documentation
status: verified
assignee: technical-writer
owner: user
depends_on:
  - "[[t0026-implement-views-viewssettings]]"
created: 2026-04-28
started: 2026-04-28
---

# Document Settings Loader And Extension Pattern

# Document Settings Loader and Extension Pattern

## Context

After `core.load_settings` and `views.ViewsSettings` land, the
module READMEs and any docs that touch the settings flow need to
catch up. This task is documentation-only.

See [[s0010-core-settings-module-spec]] for the design and
[[s0007-artifacts-os-views-module]] for the views public API.

## Requirements

1. **Update `src/artifacts_os/core/README.md`** (if present; create
   if not):
   - Document `load_settings(path) -> Settings` with a usage example.
   - Document `Settings` as the base class designed for extension
     by other modules (`ViewsSettings`, consumer-defined subclasses).
   - Document `UnsupportedSchemaVersion` and the schema-version
     handling rules.
2. **Update `src/artifacts_os/views/README.md`** (if present;
   create if not):
   - Document `ViewsSettings.from_base(base)` with the chained-call
     example:

     ```python
     base = load_settings(path)
     settings = ViewsSettings.from_base(base)
     ```
   - Document `ViewConfig` and `ViewsConfig` shapes.
3. **Add a short note** in `CLAUDE.md` (project root) under "Project
   Structure" or as a new "Settings" subsection:
   - `core` owns the base `Settings` class and `load_settings`.
   - Other modules extend `Settings` with a subclass + `from_base`
     parser; they own their section end-to-end (parse and write).
4. **Cross-check** for stale references to `artifacts_os.config` in
   any other docs (`docs/`, README.md). If found, update to point
   at `core.load_settings`.

## Verification

- [x] `core/README.md` has a Settings / `load_settings` section
- [x] `views/README.md` has a `ViewsSettings.from_base` section
- [x] `CLAUDE.md` mentions the base-Settings + extension-subclass
      pattern
- [x] No remaining references to `artifacts_os.config` outside
      s0009 (which is preserved as design history)

## Verification Report

*Verified: 2026-04-28*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `core/README.md` has a Settings / `load_settings` section | PASS | `src/artifacts_os/core/README.md` lines 95–173: "Settings (`settings.py`)" section documents the `load_settings` signature with usage example, the `Settings` base dataclass + module-ownership table, and a schema-versioning table covering `UnsupportedSchemaVersion`. |
| 2 | `views/README.md` has a `ViewsSettings.from_base` section | PASS | `src/artifacts_os/views/README.md` lines 167–245: "Settings Extension" section documents `ViewConfig`, `ViewsConfig`, and `ViewsSettings` shapes, plus `ViewsSettings.from_base` with the chained-call example (`base = load_settings(...); settings = ViewsSettings.from_base(base)`). |
| 3 | `CLAUDE.md` mentions the base-Settings + extension-subclass pattern | PASS | `CLAUDE.md` lines 38–56: new "Settings" subsection states `core` owns base `Settings` + `load_settings`, while other modules extend via subclass + `from_base` parser (cites `views.ViewsSettings` as canonical example) and links to s0010. |
| 4 | No remaining references to `artifacts_os.config` outside s0009 | PASS | Repo grep: zero matches in `src/`, `docs/`, or `README.md`. Remaining matches are confined to s0009 (allowed), s0010 (negative reference: "There is no `artifacts_os.config` module"), historical task specs (immutable), and the task file itself. |

### Summary

4 passed, 0 failed. All verification criteria are satisfied; task is ready to be marked `verified`.

## Out of Scope

- Wiring `load_settings` into `cli` / `tui` entry points (those
  modules are stubs per CLAUDE.md; this happens when they land).
- Defining a write API (deferred per s0010 § Future Work).

## Progress

### 2026-04-28 — author
> time: 18:25
> log: [[artifacts/logs/t0027-document-settings-loader-and-extension]]

Updated core/README.md (Settings section: loader, base class +
extension pattern, schema versioning table), views/README.md
(replaced Not Yet Implemented stub with ViewConfig / ViewsConfig /
ViewsSettings.from_base section incl. chained-call example), and
CLAUDE.md (new Settings subsection). Cross-check confirmed no
stale artifacts_os.config references in live source / docs /
README — remaining matches are historical artifacts (s0009
preserved as design history, task specs, jsonl logs).

## Findings

Documentation-only task. Updated three live docs to catch up with
`core.load_settings` (t0025) and `views.ViewsSettings` (t0026); no
source changes.

**`src/artifacts_os/core/README.md`**
- Added `load_settings`, `Settings`, `ProjectConfig`, and
  `UnsupportedSchemaVersion` to the public-API import block and
  models table.
- New "Settings (`settings.py`)" section covers: the loader signature
  and behaviour with a usage example; the `Settings` base dataclass
  and the section-ownership convention (table mapping `core`,
  `views`, and consumer modules to their owned keys + subclass);
  the `kw_only=True` extension pattern with a forward reference to
  `views.ViewsSettings`; the schema-versioning rules table for
  `UnsupportedSchemaVersion`.

**`src/artifacts_os/views/README.md`**
- Added `ViewConfig`, `ViewsConfig`, and `ViewsSettings` to the
  public-API import block.
- Replaced the obsolete "Not Yet Implemented" stub with a "Settings
  Extension" section: documents the section-ownership boundary
  (`views` owns `views`/`default_views`); shape of `ViewConfig`
  (columns / filters / sort) and `ViewsConfig`
  (views / default_views); the `from_base` chained-call example
  exactly as the spec asks; the `views=None` semantics when
  neither key is present; and the consumer composition note.

**`CLAUDE.md`** (project root)
- New "Settings" subsection inserted before "Coding Style":
  states that `core` owns the base `Settings` class and
  `load_settings`, while other modules extend `Settings` with a
  subclass + `from_base` parser and own their section end-to-end.
  Links to s0010 for the full design.

**Stale-reference cross-check**
- Live source, `docs/2026-04-20-artifacts-os-design.md`, and
  `README.md` contain no references to `artifacts_os.config`.
- Remaining matches are in `artifacts/tasks/*.md` (historical task
  specs, immutable), `artifacts/specs/s0009-*.md` (preserved as
  design history per the task), `artifacts/specs/s0010-*.md`
  (explicitly states "There is no `artifacts_os.config` module"),
  and `artifacts/logs/*.jsonl` (auto-generated). No edits needed.
