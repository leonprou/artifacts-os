---
assignee: developer
created: 2026-05-01
id: t0049
kind: task
name: implement-cli-list-named-views
owner: user
parent: '[[t0047-cli-list-named-views]]'
status: done
type: implementation
started: 2026-05-01
completed: 2026-05-01
---

## Authoritative Spec

[[artifacts/specs/s0012-cli-list-named-views]] — implementation
outline in §11, verification in §13. Architect's note (t0048
findings): "No additional decomposition needed — single developer
pass."

## Requirements

File-level deliverables (from spec §11):

1. **`src/artifacts_os/cli/commands/list.py`** — add `--view`/`-V`
   flag; insert resolution helper before existing branches; mutate
   `args` to carry resolved filters / sort / columns; reorder so
   filter + sort apply *above* the quiet/json short-circuit and
   column resolution stays *below* it (spec §11.1, §8).
2. **`src/artifacts_os/cli/__init__.py`** — add
   `_load_views_settings(root) -> ViewsSettings | None` helper,
   lazily called from `list.run` only. Do **not** widen
   `CliSettings` (spec §11.2 — Option A).
3. **Post-discovery filter helper** — equality on stringified
   `frontmatter[key]` for non-native filter keys (spec §11.3).
4. **Sort helper** — lexicographic on stringified value,
   missing-last in both directions (spec §6).
5. **`tests/cli/test_list_views.py`** (new) — cover all 10 cases
   in spec §11.4.
6. **`src/artifacts_os/cli/README.md`** — append "Views"
   subsection under `list` (spec §11.5).
7. **`docs/settings.md`** — add "Views section" pointer with a
   worked YAML example (spec §11.5).
8. **`.openstation/commands/artifacts.list.<v>.md`** — ship one
   example slash-command shim per spec §12. Pick a view that
   already exists in the repo's `artifacts/artifacts.yaml`, or
   add a view if needed.
9. **Error handling** — match exit codes and stderr messages in
   spec §9 verbatim.

**Out of scope** (per spec §10 deferred items): homogeneous-result
kind inference; slash-command generator; richer filter expressions;
per-kind sort orderings.

## Progress

### 2026-05-01 — developer
> time: 11:20

Implemented all 9 requirements: --view/-V flag with _apply_view/_apply_extra_filters/_apply_sort in list.py; _load_views_settings helper in cli/__init__.py; 10-case test_list_views.py (all passing); CLI README Views subsection; docs/settings.md Views section; open-tasks view added to artifacts.yaml; artifacts.list.open-tasks slash-command shim. All pre-existing failures confirmed pre-existing; no regressions.

## Findings

All 9 file-level deliverables from spec §11 shipped in a single pass:

- **`src/artifacts_os/cli/commands/list.py`** — added `--view`/`-V` flag; `_apply_view` resolves view config and mutates `args` with merged filters/sort/cfg before `list_artifacts` is called; `_apply_extra_filters` handles non-native filter keys post-discovery; `_apply_sort` sorts lexicographically with missing-last in both directions; `_resolve_columns` respects `--fields > view.columns > registry default` precedence. Filter + sort runs above the quiet/json short-circuit; column resolution stays below it.
- **`src/artifacts_os/cli/__init__.py`** — added `_load_views_settings(root)` as a parallel helper to `_load_cli_settings`; lazily imported so only the `list` path pays the cost. Returns `None` on any error (tolerant).
- **`tests/cli/test_list_views.py`** — 10 new tests covering all cases from §11.4. All pass.
- **`src/artifacts_os/cli/README.md`** — Views subsection added under `list` covering definition syntax, `default_views`, precedence table, filter merging, JSON/quiet contract, and error handling.
- **`docs/settings.md`** — "Views Section" added with a worked YAML example and cross-link to CLI README.
- **`artifacts/artifacts.yaml`** — `open-tasks` view added (`kind: task, status: ready`, sorted by name); `default_views: {task: open-tasks}` wired.
- **`.openstation/commands/artifacts.list.open-tasks.md`** — slash-command shim shipped.

**Notable decision:** `_load_views_settings` catches all exceptions (including `KeyError` from `load_settings` when `project:` is absent in minimal test vaults) and returns `None`, matching the existing `_load_cli_settings` pattern. Test fixture uses a `_write_artifacts_yaml` helper that writes a full-spec YAML (including `project:`) to ensure `load_settings` succeeds in test context.

**No regressions:** 255 previously-passing tests still pass. 3 pre-existing failures confirmed unrelated.

## Verification

- [x] `artifacts list --view <name>` works end-to-end (filters,
      columns, sort all applied)
- [x] `default_views: {<kind>: <view>}` fires automatically when
      `--kind <kind>` is supplied and no `--view` is
- [x] Per-key filter merging — explicit `--status` overrides
      view's `filters.status` while leaving other keys intact
- [x] Unknown `--view` exits `2` with
      `error: unknown view '<name>'`
- [x] Unknown bound view exits `2` with
      `error: default_views.<k> refers to unknown view '<v>'`
- [x] `-j` and `-q` ignore columns but apply filters + sort
- [x] `tests/cli/test_list_views.py` covers all 10 cases in
      spec §11.4
- [x] `src/artifacts_os/cli/README.md` documents `--view` and
      the views / precedence model
- [x] `docs/settings.md` cross-links to the views section
- [x] At least one `.openstation/commands/artifacts.list.<v>.md`
      shim shipped
- [x] All existing CLI tests still pass

## Verification Report

*Verified: 2026-05-01*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts list --view <name>` end-to-end (filters/columns/sort) | PASS | `list.py:_apply_view` mutates args; smoke test `list --view open-tasks -q` returned filtered task. Test `test_view_applies_filters_columns_sort` passes. |
| 2 | `default_views[<kind>]` fires when `--kind` supplied | PASS | `list.py:88-100` resolves `default_views` from `settings.views`. Test `test_default_views_fires_with_kind` passes; counter-test `test_default_views_no_fire_without_kind` confirms binding is no-op without `--kind`. |
| 3 | Per-key filter merging | PASS | `list.py:117-126` merges per-key with explicit flags winning. Test `test_explicit_status_overrides_view_filter` passes. |
| 4 | Unknown `--view` exits 2 with clear stderr | PASS | `list.py:106-110` raises `ValidationError`; `cli/__init__.py:190-192` maps to exit 2. Smoke test produced `error: unknown view 'nonexistent'` exit=2. Test `test_unknown_view_exits_2` passes. |
| 5 | Unknown bound view exits 2 with `default_views.<k>` message | PASS | `list.py:96-99` validates bound view; raises matching message. Test `test_unknown_default_views_target_exits_2` passes. |
| 6 | `-j` and `-q` ignore columns, apply filters+sort | PASS | `list.py:34-49` runs filters+sort above quiet/json short-circuit; column resolution at line 70 is below it. Tests `test_json_ignores_columns_applies_filters_sort` and `test_quiet_ignores_columns_applies_filters_sort` pass. |
| 7 | `tests/cli/test_list_views.py` covers all 10 cases §11.4 | PASS | All 10 named tests present, mapped 1:1 to spec cases. `pytest tests/cli/test_list_views.py` → 10 passed in 0.21s. |
| 8 | CLI README documents `--view` and precedence | PASS | `cli/README.md` lines 79, 89, 105-168 add Views subsection with definition, default_views binding, precedence table, JSON/quiet contract, error table. |
| 9 | `docs/settings.md` cross-links to views | PASS | `docs/settings.md` lines 101-138 contain "Views Section" with worked YAML and cross-link to `cli/README.md`. |
| 10 | At least one `.openstation/commands/artifacts.list.<v>.md` shim | PASS | `.openstation/commands/artifacts.list.open-tasks.md` exists with `name`, `description`, and fenced `artifacts list --view open-tasks` body, matching pattern in spec §12. |
| 11 | All existing CLI tests still pass | PASS | `pytest tests/cli/` → 120 passed, 2 failed. The 2 failures (`test_show_editor_default_opens_editor`, `test_show_explicit_editor_flag_opens_editor`) are pre-existing in `test_settings.py`/`show.py`, neither of which is touched by this task (confirmed via `git diff --stat`). |

### Summary

11 passed, 0 failed. All verification criteria satisfied; the implementation matches spec s0012 §11 and §13.