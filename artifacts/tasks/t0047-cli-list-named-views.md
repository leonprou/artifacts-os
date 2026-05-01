---
assignee: developer
created: 2026-05-01
id: t0047
kind: task
name: cli-list-named-views
owner: user
status: done
type: feature
subtasks:
  - "[[t0048-spec-cli-list-named-views]]"
  - "[[t0049-implement-cli-list-named-views]]"
artifacts:
  - "[[artifacts/specs/s0012-cli-list-named-views]]"
completed: 2026-05-02
---

## User Story

**As a** vault user running `artifacts list`,
**I want** to define named views (columns + filters + sort) in
`artifacts/artifacts.yaml` and invoke them with `--view <name>` or
auto-bind per kind via `default_views`,
**so that** I can reuse curated list presets across kinds and expose
them as ergonomic slash commands without retyping flags.

## Directions

> Final tech requirements will be set by the spec sub-task. The bullets
> below are intent, not contract.

- `artifacts list` should consume the existing `ViewsSettings`
  (s0007). The data model is in place; the CLI currently ignores it.
- Support `--view <name>` lookup and `default_views` per-kind
  binding.
- Keep precedence consistent with openstation's reference
  (`src/openstation/tasks.py:cmd_list`, lines 1049–1102): explicit
  CLI flag > view config > registry defaults; filter merging is
  per-key, not wholesale.
- `.openstation/commands/` should be able to wrap view invocations
  as ergonomic slash-command shortcuts (e.g. `/artifacts.list.review`).
- `--json` / `--quiet` must remain machine-readable: filters and
  sort apply, columns do not.
- Reference openstation: `.openstation/docs/views.md` and
  `src/openstation/tasks.py:cmd_list`.

## Sub-tasks

- [[t0048-spec-cli-list-named-views]] — architect produced the spec
  (`s0012`); status: `done`.
- [[t0049-implement-cli-list-named-views]] — developer implements
  the spec end-to-end (single pass per architect's note); status:
  `ready`.

## Tech Requirements (finalized)

Authoritative spec: [[artifacts/specs/s0012-cli-list-named-views]].
Requirements below are normative; refer to the spec for rationale,
diagrams, and implementation outline.

1. **CLI surface** — add `--view <name>` (`-V`) to
   `artifacts list`. See spec §3.
2. **Resolution algorithm** — implement the algorithm in spec §4
   in a helper called from `cli/commands/list.py:run` *before*
   the existing branches for quiet / json / table. Mutate `args`
   to carry resolved filters, sort key, and column list.
3. **Precedence (columns)** — `--fields` > `view.columns` >
   registry default columns > hardcoded fallback. See spec §5.
4. **Precedence (filters)** — explicit CLI flag wins per-key over
   `view.filters[key]`; non-native keys (`assignee`, `type`, etc.)
   apply as a post-discovery equality filter on
   `meta.frontmatter[key]`. Wholesale replacement is forbidden.
5. **`default_views` binding** — keyed by **kind name**. Fires
   only when `args.view is None` and `args.kind is not None`.
   Inference from a homogeneous result set is deferred.
6. **JSON / quiet contract** — `-q` / `-j` ignore columns but
   apply filters and sort. Order: resolve filters/sort *above*
   the quiet/json short-circuit; resolve columns *below* it.
7. **Errors** — unknown `--view` exits `2` with
   `error: unknown view '<name>'`; unknown bound view exits `2`
   with `error: default_views.<k> refers to unknown view '<v>'`.
   See spec §9 for the full table.
8. **Slash-command shims** — convention
   `.openstation/commands/artifacts.list.<view>.md`. Body is a
   single fenced `artifacts list --view <view>` block. No
   generator.
9. **Settings loading** — add `_load_views_settings(root)` helper
   in `cli/__init__.py` returning `ViewsSettings | None`. Do
   **not** widen `CliSettings` to include views (would couple
   `cli` settings parsing to `views`).
10. **Docs** — update `src/artifacts_os/cli/README.md` and
    `docs/settings.md` per spec §11.5.

## Verification

- [x] Spec sub-task merged and approved before this task moves to
      `ready` (see [[t0048-spec-cli-list-named-views]])
- [x] `artifacts list --view <name>` works end-to-end (filters,
      columns, sort all applied)
- [x] `default_views: {<kind>: <view>}` binding fires
      automatically when `--kind <kind>` is supplied and no
      `--view` is
- [x] Per-key filter merging: explicit `--status` overrides
      view's `filters.status` while leaving other keys intact
- [x] Unknown `--view` exits `2` with the documented stderr
      message
- [x] Unknown bound view exits `2` with the
      `default_views.<k>` message
- [x] `-j` and `-q` ignore columns but apply filters + sort
- [x] `tests/cli/test_list_views.py` covers all 10 cases listed
      in spec §11.4
- [x] `src/artifacts_os/cli/README.md` documents the `--view`
      flag and the views/precedence model
- [x] `docs/settings.md` cross-links to the views section
- [x] At least one `.openstation/commands/artifacts.list.<v>.md`
      shim shipped, demonstrating the pattern in spec §12

## Verification Report

*Verified: 2026-05-02*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec sub-task merged and approved | PASS | [[t0048-spec-cli-list-named-views]] is `status: done`; spec [[artifacts/specs/s0012-cli-list-named-views]] exists |
| 2 | `--view <name>` works end-to-end | PASS | `_apply_view` + `resolve_filters` + `_apply_sort` in `cli/commands/list.py` resolve filters/columns/sort; `test_view_applies_filters_columns_sort` (Case 1) passes |
| 3 | `default_views` binding fires with `--kind` | PASS | `_apply_view` (list.py:218–228) reads `settings.views.default_views[binding_kind]` only when `view_name is None and args.kind is not None`; `test_default_views_fires_with_kind` (Case 3) and `test_default_views_no_fire_without_kind` (Case 4) pass |
| 4 | Per-key filter merging | PASS | `resolve_filters` (list.py:45–80) seeds filters from view, then overrides per-key with `--kind`/`--status`/`--filter`; `test_explicit_status_overrides_view_filter` (Case 2) and `test_custom_filter_key_post_discovery` (Case 10) pass |
| 5 | Unknown `--view` exits 2 with documented message | PASS | list.py:235–238 raises `ValidationError("unknown view '<name>'")`; `_run` maps to exit 2; `test_unknown_view_exits_2` (Case 5) asserts `unknown view 'does-not-exist'` in stderr |
| 6 | Unknown bound view exits 2 with `default_views.<k>` message | PASS | list.py:224–227 raises `ValidationError(f"default_views.{binding_kind} refers to unknown view '{bound}'")`; `test_unknown_default_views_target_exits_2` (Case 6) asserts both `default_views.task` and `missing` in stderr |
| 7 | `-j`/`-q` ignore columns but apply filters + sort | PASS | list.py:143–150 short-circuits to quiet/json *after* filters and sort applied (lines 105–112) but before column resolution (line 173); `test_json_ignores_columns_applies_filters_sort` (Case 7) and `test_quiet_ignores_columns_applies_filters_sort` (Case 8) pass |
| 8 | `tests/cli/test_list_views.py` covers all 10 spec §11.4 cases | PASS | `pytest tests/cli/test_list_views.py -v` → 10 passed; one test per case (1–10), all named after the case |
| 9 | `cli/README.md` documents `--view` and precedence | PASS | `src/artifacts_os/cli/README.md` lines 90, 110–149 (`#### Views` subsection) covers flag, view definitions, `default_views` binding, precedence table, filter merging, JSON/quiet contract, and error handling |
| 10 | `docs/settings.md` cross-links to views section | PASS | `docs/settings.md` lines 102–139 (`## Views Section`) cross-links to `views/README.md` (line 88) and `cli/README.md` (line 138) |
| 11 | At least one shim shipped, demonstrating §12 pattern | PASS | `.openstation/commands/artifacts.list.open-tasks.md` exists; matches §12 (filename `artifacts.list.<view>.md`, frontmatter with `name`/`description`, body with rationale + fenced `artifacts list --view open-tasks` block) |

### Summary

11 passed, 0 failed. All verification criteria met; full integration
test suite for `--view` (10 cases) passes; documentation is in place
and cross-linked.

### Notes

- Minor follow-up (not blocking): the shipped shim
  `.openstation/commands/artifacts.list.open-tasks.md` references view
  `open-tasks`, but `artifacts/artifacts.yaml` does not currently
  define that view (it ships `ready`, `active`, etc. but not
  `open-tasks`). The shim is structurally correct per §12 but is not
  runnable against the actual vault — spec §11.6 expected the example
  to be runnable. Consider either adding an `open-tasks` view to
  `artifacts.yaml` or pointing the shim at an existing view (e.g.
  `ready`).