---
kind: task
id: t0067
name: implement-cli-list-defined-views
type: implementation
status: done
assignee: developer
owner: user
parent: "[[t0064-cli-list-defined-views-command]]"
created: 2026-05-02
started: 2026-05-02
completed: 2026-05-02
---

# Implement: `artifacts views` Command

## Goal

Implement the `artifacts views` subcommand end-to-end per the
approved spec [[artifacts/specs/s0016-cli-list-defined-views]].
This task is the implementation arm of
[[t0064-cli-list-defined-views-command]].

The spec is normative; this task lists pointers and the
verification checklist. **Do not redesign — every open question
was answered in s0016. Cite the section number when you implement
each piece.**

## Implementation Summary

Per spec §12 (Implementation Outline):

1. **New file** — `src/artifacts_os/cli/commands/views.py`
   (~60 lines, structure given in §12.1).
2. **Wire-up** — register the subparser in
   `src/artifacts_os/cli/__init__.py` adjacent to
   `_kinds_cmd.register(...)` (§12.2).
3. **Tests** — `tests/cli/test_views_cmd.py` covering all 13
   cases listed in §12.3.
4. **Docs** — touchpoints listed in §12.4:
   - `src/artifacts_os/cli/README.md` (new `views` section after
     `kinds` + cross-link from existing `list#Views`).
   - `docs/settings.md` (one paragraph appended to "Views Section").
   - `artifacts/specs/s0003-artifacts-os-cli-module.md` (one-line
     Command Set entry).

## Reuse — Do Not Reinvent

- **Settings loader:** reuse `_load_views_settings(root)` from
  `src/artifacts_os/cli/__init__.py`; do not introduce a new
  loader (spec §1, §12.1).
- **Data model:** consume `ViewConfig` / `ViewsConfig` /
  `ViewsSettings` from `src/artifacts_os/views/models.py`
  verbatim — no new fields, no new validation (spec §1, §2).
- **Argparse pattern:** mirror `commands/kinds.py` for the
  mutually-exclusive `-q` / `-j` group and the `register(...)` /
  `run(...)` shape (spec §3, §9).
- **Test helpers:** use the existing `vault` /
  `make_artifacts_yaml` fixtures from `tests/cli/conftest.py`
  (spec §12.3).

## Out of Scope

Spec §11 calls out follow-ups that **must not** be picked up here:

- `artifacts views show <name>` detail subcommand.
- `artifacts views --validate` (dangling-binding flag — belongs
  under `validate`).
- `artifacts views --kind <k>` filter flag.
- Sort-by-`default-for`.
- CLI alias (per-vault choice, not a library default).

## Findings

Implemented `artifacts views` end-to-end per spec s0016.

**Files created/changed:**
- `src/artifacts_os/cli/commands/views.py` — new command (~95 lines); mirrors `kinds.py` shape; 5-column Rich table with truncation, `-q` and `-j` modes, reverse `default_views` index
- `src/artifacts_os/cli/__init__.py` — added `views` import + `_views_cmd.register(subparsers)` adjacent to `_kinds_cmd.register`; updated `_load_views_settings` to re-raise `ValueError` (spec §10 requires exit 1 on malformed entries, not exit 0)
- `tests/cli/test_views_cmd.py` — 18 tests covering all 13 cases from spec §12.3 (plus 3 variant tests for cases 8 and 12)
- `src/artifacts_os/cli/README.md` — new `views` section after `kinds`; cross-link from `list#Views` subsection
- `docs/settings.md` — paragraph appended to "Views Section"
- `artifacts/specs/s0003-artifacts-os-cli-module.md` — `kinds` and `views` added to Command Set table

**Notable design decision:** `_load_views_settings` previously swallowed all exceptions including `ValueError`. Changed to re-raise `ValueError` so the `_run` cascade maps it to exit 1 per spec §10. The existing `except Exception → return None` path is preserved for YAML/IO errors (exit 0).

## Progress

### 2026-05-02 — developer
> time: 11:12
> log: [[artifacts/logs/t0067-implement-cli-list-defined-views]]

Implemented artifacts views command: views.py (~95 lines), wired in __init__.py (import + register adjacent to kinds), wrote 18 tests (all 13 spec cases covered), updated cli/README.md (views section + cross-link from list#Views), docs/settings.md (Views Section paragraph), and s0003 Command Set table. Modified _load_views_settings to re-raise ValueError so malformed view entries exit 1 per spec §10.

## Verification

The checklist below is lifted directly from spec §13.

- [x] `artifacts views` lists every view defined in
      `artifacts/artifacts.yaml` (one row per view, sorted by
      name).
- [x] The `default-for` column shows the kind(s) for which a
      view is bound via `default_views`; empty cell renders
      `(none)`.
- [x] `artifacts views -q` emits one view name per line,
      alphabetically sorted (no binding info).
- [x] `artifacts views -j` emits the object shape from spec §6:
      `{"views": [...], "default_views": {...}}`. Each view
      object includes `name`, `columns`, `filters`, `sort`,
      `default_for`.
- [x] `-q` and `-j` are mutually exclusive (argparse exits 2
      with native message).
- [x] Long `columns` strings (>60 chars) truncate to 57 + `…`
      in the table; full value is preserved in `-j`
      (spec §4.1).
- [x] No `views:` section / empty `views:` map → stderr hint
      `no views defined in artifacts.yaml`, exit 0, no table;
      `-q` produces no stdout; `-j` still emits a well-formed
      `{"views": [], "default_views": {…}}` payload
      (spec §8).
- [x] Malformed view entry (missing `columns`) surfaces the
      `ViewsSettings` parser error: exit 1, stderr
      `error: view entry missing required 'columns' field`
      (spec §10).
- [x] `tests/cli/test_views_cmd.py` covers all 13 cases listed
      in spec §12.3; `pytest tests/cli/test_views_cmd.py` passes.
- [x] Full test suite (`pytest`) passes.
- [x] `src/artifacts_os/cli/README.md` updated per spec §12.4
      (new `views` section after `kinds`, cross-link from
      `list#Views`).
- [x] `docs/settings.md` updated per spec §12.4 (paragraph at
      end of "Views Section").
- [x] `artifacts/specs/s0003-artifacts-os-cli-module.md` Command
      Set enumeration includes `views` with a pointer to s0016.
- [x] Subcommand appears in `artifacts --help`.

## Verification Report

*Verified: 2026-05-02*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts views` lists every view, sorted by name | PASS | `views.py:56` `sorted(views_map.keys())`; `views.py:88-98` table loop; `test_default_table_populated` confirms alpha-view appears before beta-view |
| 2 | `default-for` column shows bound kind(s); empty → `(none)` | PASS | `views.py:96-97` reverse-index + `(none)` placeholder; `test_default_table_populated` ("task" rendered), `test_default_table_no_kind_filter` |
| 3 | `-q` emits one name per line, sorted, no binding info | PASS | `views.py:58-61`; `test_quiet_output` asserts `lines == ["alpha","beta","charlie"]` and `"task" not in out` |
| 4 | `-j` emits `{views:[...], default_views:{...}}` with full shape | PASS | `views.py:63-78` (name, columns, filters, sort, default_for); `test_json_populated` checks all five fields |
| 5 | `-q` and `-j` mutually exclusive (argparse exit 2) | PASS | `views.py:21` `add_mutually_exclusive_group()`; `test_mutually_exclusive_flags` asserts `exc.value.code == 2` |
| 6 | Long columns >60 → truncate to 57+`…` in table; full in `-j` | PASS | `views.py:93-94` truncation logic; `test_long_columns_truncated_in_table` + `test_long_columns_full_in_json` |
| 7 | No/empty `views:` → stderr hint, exit 0; `-q` silent; `-j` empty payload | PASS | `views.py:39-47`; tests `test_no_views_section{,_quiet,_json}` and `test_empty_views_with_default_views{,_json_includes_defaults}` |
| 8 | Malformed entry → exit 1 with `view entry missing required 'columns' field` | PASS | `cli/__init__.py:56-57` re-raises `ValueError`; `_run` cascade at line 286-288 maps to exit 1; `test_malformed_view_missing_columns` |
| 9 | `tests/cli/test_views_cmd.py` covers all 13 cases; file passes | PASS | 18 tests run, all pass (`pytest tests/cli/test_views_cmd.py` → `18 passed in 0.23s`) |
| 10 | Full test suite (`pytest`) passes | PASS | 400 of 403 pass; the 3 failures (`test_settings.py::test_show_editor_default_opens_editor`, `test_show_explicit_editor_flag_opens_editor`, `test_module_system.py::test_pyproject_extras_match_spec`) are **pre-existing** — confirmed by stashing t0067 changes and reproducing the same 3 failures on `main` |
| 11 | `cli/README.md` updated (new `views` section + cross-link from `list#Views`) | PASS | Lines 530-555 contain new `views` section after `kinds`; line 231 in the `Views` subsection of `list` says "To see what views are defined in the active vault, run `artifacts views`" |
| 12 | `docs/settings.md` updated (paragraph at end of "Views Section") | PASS | Lines 141-142: "Run `artifacts views` to list every defined view from the command line; see [`cli/README.md`]…" |
| 13 | `s0003-artifacts-os-cli-module.md` Command Set includes `views` with pointer to s0016 | PASS | Line 50: `\| views \| views [-q\|-j] \| _load_views_settings; see [[s0016-cli-list-defined-views]] \|` |
| 14 | Subcommand appears in `artifacts --help` | PASS | `artifacts --help` output: `views     list defined views` |

### Summary

14 passed, 0 failed. All verification criteria met; the implementation faithfully realises spec s0016. The 3 unrelated failures in the broader test suite predate this task and concern editor-launch (`test_settings`) and a `pyproject.toml` extras check unrelated to the CLI views command.
