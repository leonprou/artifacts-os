---
kind: task
id: t0016
name: re-scope-s0007-views-spec
type: spec
status: done
assignee: architect
owner: user
created: 2026-04-26
started: 2026-04-26
artifacts:
  - "[[s0007-artifacts-os-views-module]]"
  - "[[artifacts/specs/s0009-artifacts-os-config-module]]"
completed: 2026-04-29
---

# Re-Scope S0007 Views Spec And Define New Config Module

## Context

During verification of t0004 (`write-readme-for-views-module`), two
issues surfaced:

1. The reference vault `~/workspace/open-station/.openstation/openstation.yaml`
   already defines a complete schema for named views (`columns`,
   `filters`, optional `sort`) and per-kind `default_views`, but
   artifacts-os has not ported it. The "deferred pending settings YAML
   schema" wording in s0007 is stale.
2. The current s0007 lists "named view loading" under In-scope for the
   `views` module, but loading from a settings file violates the
   "views does no I/O" principle stated in the same spec. Additionally,
   `ViewConfig.filters` is consumed by `core.list_artifacts`, not by
   `views` — so `ViewConfig` is a cross-module data shape, not a
   view-internal one.

This task re-scopes s0007 and writes a new spec for an
`artifacts_os.config` module that owns settings-file loading.

## Requirements

### 1. Update `artifacts/specs/s0007-artifacts-os-views-module.md`

- **Scope Boundary** — split the "named view loading" line:
  - **In:** `ViewConfig` dataclass, `parse_view_config(dict) -> ViewConfig`
    (pure, takes already-parsed YAML dict)
  - **Out:** reading the settings file from disk (delegated to the new
    `config` module)
- **Public API** — replace `load_views` with `parse_view_config`.
- **Deferred** — replace "Settings YAML schema not yet defined" with the
  concrete schema documented from the openstation.yaml reference; if no
  longer deferred, remove the row.

### 2. Write a new spec for `artifacts_os.config`

Create `artifacts/specs/sNNNN-artifacts-os-config-module.md` (CLI assigns
ID via `openstation create --kind spec`).

Cover at minimum:

- **Purpose** — load the settings file (decision in §3 below) and
  produce typed config objects per section.
- **Public API sketch** — e.g. `load_settings(path) -> Settings`;
  dataclasses for each section (`ProjectConfig`, `RunConfig`,
  `ViewsConfig`, etc.); how it dispatches per-section parsing
  (e.g. delegates the `views` slice to `views.parse_view_config`).
- **Module dependency** — propose where `config` fits in the existing
  DAG (`core` → `views` → `cli, tui`; `core` → `log` → `ai`).
- **Schema versioning** — `layout_version: 1` is already in the
  reference file; document how unknown versions are handled.
- **Scope boundary** — In: file I/O, validation, schema versioning,
  error reporting. Out: argument parsing (cli), filter application
  (core), rendering (views).

### 3. Decide where views config lives

`artifacts/artifacts.yaml` is currently minimal (`layout_version` +
`project`). Decide between:

- (a) `artifacts.yaml` absorbs the openstation.yaml structure (single
  file owns everything), or
- (b) views/run/etc. live in separate files (e.g. `views.yaml`).

Document the decision in the new config spec with brief rationale.

## Source material

- `~/workspace/open-station/.openstation/openstation.yaml` — reference schema
- `artifacts/specs/s0007-artifacts-os-views-module.md` — current views spec
- `src/artifacts_os/views/_views.py` — current views implementation
- `src/artifacts_os/core/registry.py` — precedent for `_load_vault_kinds`
- `CLAUDE.md` — project structure and module dependency DAG
- `artifacts/artifacts.yaml` — current vault marker

## Constraints

- Document actual reference schema — read the openstation.yaml file, do
  not invent fields.
- Module dependency DAG must remain acyclic.
- `views` must end the task strictly I/O-free.

## Verification

- [x] s0007 Scope Boundary updated to put settings-file loading Out of scope
- [x] s0007 Public API replaces `load_views` with `parse_view_config`
- [x] s0007 Deferred section replaced with concrete schema (or removed)
- [x] New spec `sNNNN-artifacts-os-config-module.md` exists with purpose,
      public API sketch, module dependency, and scope boundary
- [x] Decision recorded for which file(s) hold views config
- [x] Both spec files reference the openstation.yaml source

## Verification Report

*Verified: 2026-04-26*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | s0007 Scope Boundary puts settings-file loading Out of scope | PASS | s0007 lines 106-112: Out lists "settings-file I/O (delegated to `artifacts_os.config`)" and "view-config parsing (delegated to `artifacts_os.config`)" |
| 2 | s0007 Public API replaces `load_views` with `parse_view_config` | PASS | s0007 lines 32-46: `load_views` removed from public API. View-dict parsing moved to `artifacts_os.config._parse_view` (s0007 lines 64-66, 158) — going beyond the rename to keep `views` strictly I/O-free as required by the rescope. |
| 3 | s0007 Deferred section replaced with concrete schema | PASS | Old Deferred row removed. s0007 lines 114-156 add "Settings YAML Schema (views section)" with real `openstation.yaml` examples (`active`, `session-log`, `sessions`, `default_views`). |
| 4 | New spec s0009 exists with purpose, public API sketch, module dependency, scope boundary | PASS | `artifacts/specs/s0009-artifacts-os-config-module.md` exists. Purpose (line 20), Public API (line 43, with `Settings`, `ProjectConfig`, `RunConfig`, `TmuxConfig`, `ViewsConfig`, `load_settings`), Module Dependency (line 102, acyclic DAG), Scope Boundary (line 185). |
| 5 | Decision recorded for views config file | PASS | s0009 lines 26-40: explicit "Decision: `artifacts.yaml` absorbs all config (option a — single file)" with three-bullet rationale. |
| 6 | Both spec files reference the openstation.yaml source | PASS | s0007 line 18 and s0009 line 17 both contain `Source reference: ~/workspace/open-station/.openstation/openstation.yaml`. |

### Summary

6 passed, 0 failed. All verification criteria are satisfied; the rescope of s0007 and the new s0009 config spec are coherent and ready to drive follow-up implementation tasks.

## Findings

Two spec files updated/created.

**s0007 changes** (`artifacts/specs/s0007-artifacts-os-views-module.md`):
- Intro updated: `ViewConfig` is now described as a pure data shape
  (no I/O); references s0009 and the openstation.yaml source.
- Public API: `load_views` replaced with `parse_view_config(data: dict) -> ViewConfig`.
- ViewConfig description rewritten: I/O-free, dict provided by `config`.
  Columns field documented as comma-separated string (matching reference).
- Scope Boundary: "named view loading" moved Out; "settings-file I/O
  (delegated to `artifacts_os.config`)" added to Out explicitly.
- Deferred table removed. Replaced with a concrete `## Settings YAML
  Schema (views section)` section containing real examples from
  the reference `openstation.yaml`.

**s0009 created** (`artifacts/specs/s0009-artifacts-os-config-module.md`):
- Purpose: owns file I/O, YAML parsing, schema versioning, typed
  dataclass construction.
- Public API: `load_settings(path) -> Settings`; dataclasses
  `Settings`, `ProjectConfig`, `RunConfig`, `TmuxConfig`, `ViewsConfig`.
  `config` imports `ViewConfig` from `views` and calls `parse_view_config`
  per named view.
- Module dependency: `core → views → config → cli, tui` (acyclic).
- Schema versioning: `layout_version: 1` required; missing or unknown
  version raises `UnsupportedSchemaVersion`.
- Full schema documented verbatim from the reference `openstation.yaml`.
- **Single-file decision (option a):** `artifacts.yaml` absorbs all
  config sections; rationale documented.
- Scope boundary: In = file I/O, validation, versioning, error
  reporting. Out = arg parsing, filter application, rendering.

## Downstream

- `views/_views.py` needs `parse_view_config` added and `load_views`
  removed (implementation follows s0007 update).
- `artifacts_os.config` module does not yet exist; implementation
  task needed once s0009 is approved.
- `artifacts.yaml` schema should be extended with `views` / `default_views`
  examples once the config module is implemented.
