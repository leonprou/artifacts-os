---
assignee: developer
created: 2026-05-11
id: t0142
kind: task
name: drop-legacy-flat-kind-schema
owner: user
status: done
type: implementation
started: 2026-05-11
completed: 2026-05-14
---

## Why

The vault loader supports two ways to declare a kind: the legacy
flat `artifacts/kinds/<name>.json` form and the preferred folder
form (`artifacts/kinds/<name>/kind.json` + `ARTIFACT.md`). The
shipped vault uses a hybrid (flat schema + sibling folder for
`ARTIFACT.md`), which means none of the shipped kinds actually
exercise the documented preferred form, and authors reading
`docs/adding-a-kind.md` are forced to choose between two
equivalent paths with no real reason to prefer one. Removing the
legacy form gives us a single canonical layout, lets the shipped
kinds serve as the worked example, and shrinks the loader's
collision-handling logic.

## Requirements

- The vault loader recognises kinds **only** in folder form
  (`artifacts/kinds/<name>/kind.json`). Flat
  `artifacts/kinds/<name>.json` files are no longer registered as
  kinds.
- All five shipped kinds (`note`, `task`, `spec`, `research`,
  `agent`) ship as folder-form kinds. No top-level
  `<name>.json` remains under `artifacts/kinds/` in the repo.
- Authors with a stray flat `<name>.json` get a clear, actionable
  signal (whether warning or error is the implementer's call) so
  the failure mode is not silent.
- `docs/adding-a-kind.md` describes a single canonical layout —
  folder form. References to the legacy flat form, the collision
  rule, and the "flat vs folder" precedence are removed or
  rewritten. The worked example and Reference Templates table use
  folder form throughout. The stale claim that `agent` has no
  `ARTIFACT.md` is corrected.
- The test suite still passes. Tests that exercised the flat form
  (`test_legacy_flat_kind_json_still_loads`,
  `test_flat_and_folder_collision_folder_wins`, and any helpers
  that wrote flat `<name>.json` files) are removed or rewritten
  against folder form.
- No regression in observable CLI behaviour for the five shipped
  kinds — `artifacts kinds`, `artifacts create`, and
  schema-derived filter flags continue to work exactly as before.

## Out of scope

- Adding new fields, behaviours, or layout variants beyond
  collapsing the two existing forms into one.
- Changes to the `ARTIFACT.md` contract or to schema validation
  semantics.

## Verification

- [x] No `artifacts/kinds/<name>.json` files remain under the
      repository's `artifacts/kinds/` directory.
- [x] Each of `note`, `task`, `spec`, `research`, `agent` is
      registered from `artifacts/kinds/<name>/kind.json` and
      `artifacts kinds` lists all five with their existing
      `description` and `has_template` values unchanged.
- [x] A flat `artifacts/kinds/<name>.json` placed in a vault is
      not registered as a kind and produces a clearly worded
      diagnostic (warning or error) telling the author to migrate.
- [x] `docs/adding-a-kind.md` no longer documents the flat form
      or the flat-vs-folder collision rule; the worked example
      and Reference Templates section use folder form only; the
      `agent` `ARTIFACT.md` claim is updated.
- [x] Full test suite (`pytest`) passes; legacy-form tests are
      removed or migrated, and folder-form coverage remains
      intact.
- [x] Reviewed and approved by user.

## Verification Report

*Verified: 2026-05-11*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | No flat `<name>.json` files under `artifacts/kinds/` | PASS | `find artifacts/kinds -maxdepth 1 -type f` returns nothing; only the five kind folders exist. |
| 2 | All five kinds registered from folder form with unchanged description and `has_template` | PASS | `artifacts kinds --json` lists `agent`, `note`, `research`, `spec`, `task` each with `has_template: true` and full description strings; table view shows all five. |
| 3 | Flat `<name>.json` skipped with clear diagnostic | PASS | `registry.py:124-130` emits a `UserWarning` ("flat schema file ... is not supported. Migrate to folder form: artifacts/kinds/<name>/kind.json. The flat file will not be registered as a kind."); reproduced live with a stray `widget.json` (zero kinds registered, warning fired). |
| 4 | Docs describe folder form only; `agent` `ARTIFACT.md` claim corrected | PASS | `docs/adding-a-kind.md` § File Layout, Worked Example, and Reference Templates all use folder form; the only "flat" reference is the migration warning note; Reference Templates row for `agent` now reads "has `ARTIFACT.md`" and `artifacts/kinds/agent/ARTIFACT.md` exists (3110 bytes). |
| 5 | Test suite passes; legacy tests migrated | PASS | `pytest` → 888 passed, 1 skipped, 4 failed — all 4 failures are in `tests/ai/test_release_changelog_skill.py` and reproduce on the pre-change tree (verified via `git stash`), so they are pre-existing and unrelated. Legacy tests `test_legacy_flat_kind_json_still_loads` and `test_folder_form_wins_on_collision` removed; replaced by `test_flat_kind_json_not_registered_and_warns` (tests/core/test_kinds_catalog.py:318). Folder-form coverage intact (`pytest tests/core/test_kinds_catalog.py tests/core/test_registry.py` → 25 passed, 1 skipped). |
| 6 | Reviewed and approved by user | PASS | User invoked `/openstation.verify` as task owner. |

### Summary

6 passed, 0 failed. All verification criteria satisfied; task is ready to transition to `verified`.

## Findings

Collapsed flat + folder dual layout into folder-only form throughout.

**Vault changes:**
- Created `artifacts/kinds/{agent,note,task,spec,research}/kind.json` (copied from removed flat files)
- Removed all five top-level `artifacts/kinds/<name>.json` flat files

**Source changes:**
- `src/artifacts_os/core/registry.py` — `_load_vault_kinds` now only scans folder form; emits an actionable `UserWarning` with migration instructions when a stray flat `.json` is found; removed collision-handling logic
- `src/artifacts_os/cli/commands/init.py` — `init` command now writes `kind.json` inside the kind folder instead of a sibling flat file
- `src/artifacts_os/cli/__init__.py` — `_peek_kind_for_command` and `_load_all_vault_schemas` updated to load from folder form

**Test changes:**
- `tests/core/test_kinds_catalog.py` — replaced `test_legacy_flat_kind_json_still_loads` and `test_folder_form_wins_on_collision` with `test_flat_kind_json_not_registered_and_warns`
- `tests/core/test_registry.py` — `_write_schema` helper and `test_schema_properties_task_kind` updated to folder form
- 8 additional test files updated: `tests/cli/conftest.py`, `test_init.py`, `test_list_schema_flags.py`, `test_list_layout.py`, `test_graph.py`, `test_list_artifacts_filters.py`, `test_body_loader.py`, `test_register_kinds.py`, `test_create_kind_default.py`, `test_create_kind_aware_help.py`, `test_kinds.py`

**Docs changes:**
- `docs/adding-a-kind.md` — removed flat form and collision rule; updated File Layout section, Reference Templates table, and "What You Get for Free" section; corrected stale `agent` `ARTIFACT.md` claim
- `src/artifacts_os/core/README.md` — updated two registry doc lines
- `src/artifacts_os/cli/README.md` — updated two schema-path references

**Results:** `pytest` — 888 passed, 4 pre-existing failures (all in `test_release_changelog_skill.py`, unrelated), 1 skipped. `artifacts kinds` lists all five kinds with descriptions and `has_template=true` unchanged.
