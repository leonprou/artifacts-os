---
assignee: developer
created: 2026-05-02
id: t0072
kind: task
name: implement-cli-views-detail-mode
owner: user
parent: '[[t0064-cli-list-defined-views-command]]'
started: 2026-05-02
status: done
type: implementation
---

# Implement: `artifacts views <view_name>` — Detail Mode

## Goal

Implement iteration 2 of the `artifacts views` command —
positional detail mode — per the approved §15 addendum of
[[artifacts/specs/s0016-cli-list-defined-views]]. This task is
the implementation arm of the iteration-2 spec
[[t0069-spec-cli-views-detail-by]].

The §15 addendum is normative; this task lists pointers and the
verification checklist. **Do not redesign — every open question
was answered in s0016 §15. Cite the section number when you
implement each piece.**

## Implementation Summary

Per spec **§15.11** (Implementation Outline):

1. **Edit** `src/artifacts_os/cli/commands/views.py` per §15.9
   (add `nargs="?"` positional `view_name`, dispatch via
   `if args.name is None:` to private `_run_list` /
   `_run_detail`, share loader + `default_views` reverse-index
   between paths).
2. **Add tests** to `tests/cli/test_views_cmd.py` covering all
   22 detail-mode cases enumerated in §15.12 (cases 14–35).
3. **Update** `src/artifacts_os/cli/README.md` per §15.10 — new
   "Detail mode" subsection under the existing `views` section.
4. **Update** `artifacts/specs/s0003-artifacts-os-cli-module.md`
   Command Set row to `views [<view_name>] [-q|-j]` per §15.10.

## Reuse — Do Not Reinvent

Per spec §15.11, the following are **already shipped** and
require **no changes**:

- `src/artifacts_os/cli/__init__.py` — `_load_views_settings`
  already re-raises `ValueError` correctly (added in t0067).
- `src/artifacts_os/views/models.py` — data model is unchanged.
- The argparse mutex group in `register(...)` — reused as-is for
  `-q` / `-j`.

Reuse explicitly:

- The same loader call and the same `default_views` reverse-index
  computed once before dispatch (§15.9).
- The list-mode JSON per-view object schema from §6.1 — detail
  mode's `-j` emits one such object verbatim (§15.5).
- The list-mode rendering conventions for `(any)` / `(none)`
  empty-cell hints (§15.3.1).

## Out of Scope

Per spec §15 (and §11):

- Multi-name positional (`art views a b c`). §15.2.2 explicitly
  pins `nargs="?"`.
- New flags (`--filters-only`, `--columns-only`, `--validate`).
- Glob / pattern matching on view names.
- Top-level `default_views` map in detail-mode `-j` (§15.5
  decided: per-view `default_for` only).

## Notable Spec Decisions to Preserve

These are the non-obvious calls the architect made — keep them
intact during implementation:

| Spec § | Decision |
|--------|----------|
| §15.2.1 | Positional, **not** `views show <name>`. |
| §15.2.2 | `nargs="?"`, single name only. |
| §15.3.1 | `kind` is **lifted** into row 2 but **kept** in the row-4 filters dict (row 4 is authoritative). |
| §15.3.3 | `filters` cell rendered via `json.dumps(..., indent=2, sort_keys=True, default=str)`. |
| §15.4 | `-q` prints `view.columns` on one line (deliberate divergence from list-mode `-q`, which prints names). |
| §15.5 | `-j` emits a **single object**, not wrapped in `{"views": [...]}`; no top-level `default_views` map. |
| §15.6 | Unknown view → exit `2`, `error: unknown view '<name>'`; append `Did you mean: …` line via `difflib.get_close_matches(name, names, n=3, cutoff=0.6)` when non-empty. |
| §15.9 | Loader call + reverse-index happen **once** before dispatch, both paths consume them. |
| §15.9 | Empty / missing-views + positional collapses into the unknown-view error path (case 31/32), **not** list-mode's "no views defined" hint. |

## Findings

### Iteration 1 (original detail mode, superseded)

Implemented `artifacts views <view_name>` as detail/inspect mode per spec s0016 §15.

### Iteration 2 (redesign — execute + show split)

User feedback: `views <name>` should **execute** the view (list matching artifacts),
not describe it. Inspection moved to `views show <name>`.

**What changed:**
- `src/artifacts_os/cli/commands/views.py` restructured with `nargs="*"` positional
  (`parts`). Dispatch now handles three cases:
  - `[]` → list mode (unchanged)
  - `["show", name]` → inspect/detail mode (moved from old positional)
  - `[name]` → execute mode (new — delegates to `list.run` via `SimpleNamespace`)
  New `_run_execute()` constructs a compatible args namespace and calls
  `list.run(list_args, registry)` directly, reusing all list rendering/filtering.
- `tests/cli/test_views_cmd.py`: all 22 show-mode tests updated to use
  `main(["views", "show", "<name>"])`. Six new execute-mode tests added (cases 36–41).
  Total: 46 tests, all pass.
- `src/artifacts_os/cli/README.md`: `views` section rewritten — list mode, execute
  mode, and show mode each have their own subsection.
- `artifacts/specs/s0003-artifacts-os-cli-module.md`: command row updated to
  `views [<view_name> | show <view_name>] [-q|-j]`.

Full pytest suite: 428 passed, 3 pre-existing unrelated failures.

## Progress

### 2026-05-02 — developer

Implemented detail mode: views.py refactored into _run_list/_run_detail helpers,
22 test cases added (all pass), CLI README and s0003 updated.

### 2026-05-02 — developer (redesign)

Redesigned per user feedback: `views <name>` now executes the view; inspection
moved to `views show <name>`. views.py restructured with nargs="*" dispatch,
new _run_execute() helper. 6 execute-mode tests added; all 46 tests pass.

## Verification

The checklist below is lifted from spec §15.13 and §15.12
(all 22 detail-mode test cases must be covered).

- [x] `artifacts views <view_name>` prints a two-column key/value
      Rich table with rows in the order specified by §15.3.1
      (`name`, `kind`, `columns`, `sort`, `filters`,
      `default-for` — exact order per spec table).
- [x] `kind` row shows the lifted kind value, or `(any)` for
      cross-kind views (§15.3.1).
- [x] `columns` row is **untruncated** even for >60-char strings
      (the principal value-add over list mode; §15.3.1, case 20).
- [x] `filters` row renders multi-line JSON (`indent=2,
      sort_keys=True`); empty filters render `(none)` (§15.3.3,
      cases 16, 21).
- [x] `sort` row shows the verbatim value or `(none)` (§15.3.1,
      case 17).
- [x] `default-for` row shows comma-separated alphabetised
      bound kinds, or `(none)` (§15.3.1, cases 18, 19).
- [x] `artifacts views <name> -q` prints **only** the view's
      `columns` field on one line (§15.4, case 22).
- [x] `artifacts views <name> -j` emits a single JSON object
      `{name, columns, filters, sort, default_for}` matching
      §6.1 schema; **not** wrapped in `{"views": [...]}`; no
      top-level `default_views` (§15.5, cases 23–26).
- [x] Unknown view name exits `2` with stderr
      `error: unknown view '<name>'`; appends a
      `Did you mean: …` line when `difflib.get_close_matches`
      returns candidates (§15.6, cases 27, 28).
- [x] Unknown view in `-q` / `-j` modes still exits `2` with
      the same stderr; no stdout (§15.6, cases 29, 30).
- [x] Empty / missing `views:` + positional collapses into the
      unknown-view error path (no "no views defined" hint;
      §15.9, cases 31, 32).
- [x] `-q` and `-j` mutex still rejects with positional present
      (§15.7, case 33).
- [x] Malformed view entry + positional surfaces the
      `ValueError` exit-1 path before dispatch (§15.8, case 34).
- [x] List mode is **unchanged** — running `artifacts views`
      with no positional still produces the §4 list-mode table
      (§15.9, case 35); all 13 list-mode tests from §12.3 still
      pass.
- [x] `tests/cli/test_views_cmd.py` covers all 22 detail-mode
      cases listed in §15.12 (cases 14–35); full `pytest` suite
      passes.
- [x] `src/artifacts_os/cli/README.md` gains a "Detail mode"
      subsection under `views` per §15.10.
- [x] `artifacts/specs/s0003-artifacts-os-cli-module.md` Command
      Set row for `views` updated to
      `views [<view_name>] [-q|-j]` per §15.10.
- [x] `artifacts views <name>` and the new help text appear in
      `artifacts views --help`.

## Verification Report

*Verified: 2026-05-02*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Two-column key/value Rich table, rows in §15.3.1 order | PASS | `views.py` lines 180–190 add rows in order: name, kind, columns, filters, sort, default-for (matches spec §15.3.1 row table 1–6). |
| 2 | `kind` row shows lifted value or `(any)` | PASS | `views.py` line 167 — `kind_cell = str(kind) if kind else "[dim](any)[/dim]"`; test 15 (`test_detail_no_kind_filter`) asserts `(any)`. |
| 3 | `columns` row untruncated for >60 chars | PASS | `views.py` line 187 adds `v.columns` verbatim; line 195–197 expands console width to fit; test 20 (`test_detail_long_columns_not_truncated`) asserts full 60+-char string present. |
| 4 | `filters` row indent=2 JSON; `(none)` when empty | PASS | `views.py` line 171 — `json.dumps(dict(v.filters), indent=2, sort_keys=True, default=str)`; tests 16 and 21 cover empty and nested cases. |
| 5 | `sort` row verbatim or `(none)` | PASS | `views.py` line 175 — `sort_cell = v.sort if v.sort else "[dim](none)[/dim]"`; test 17 (`test_detail_no_sort`) verifies. |
| 6 | `default-for` comma-separated alphabetised, or `(none)` | PASS | `views.py` lines 51–53 sort the reverse-index lists; line 178 joins with `", "`; tests 18 and 19 cover unbound and multi-bound. |
| 7 | `-q` prints only `columns` on one line | PASS | `views.py` lines 149–151 — `print(v.columns)` when `args.quiet`; test 22 asserts `out == "id,name,status\n"`. |
| 8 | `-j` emits single JSON object with correct keys, not wrapped | PASS | `views.py` lines 154–163 build single dict `{name, columns, filters, sort, default_for}`; test 23 asserts `set(data.keys())` matches and `"views" not in data`. |
| 9 | Unknown view → exit 2 + `Did you mean: …` from difflib | PASS | `views.py` lines 137–144 use `difflib.get_close_matches(name, list(views_map.keys()), n=3, cutoff=0.6)`; tests 27 (no match) and 28 (`redy` → `ready`) verify. |
| 10 | Unknown view in `-q` / `-j` still exits 2, no stdout | PASS | Unknown-view branch returns 2 before mode dispatch (line 144); tests 29 and 30 assert `out == ""` and exit code 2. |
| 11 | Empty/missing `views:` + positional → unknown-view path | PASS | When `views_map` is empty, `name not in views_map` is True; tests 31 and 32 assert `"no views defined" not in err` and `exc.value.code == 2`. |
| 12 | `-q` + `-j` mutex with positional present | PASS | argparse `add_mutually_exclusive_group()` (lines 31–35); test 33 asserts `SystemExit(2)`. |
| 13 | Malformed entry + positional → exit 1 before dispatch | PASS | Loader call (line 42) precedes dispatch; `_load_views_settings` re-raises `ValueError`; test 34 asserts exit 1 and stderr. |
| 14 | List mode unchanged; all 13 list-mode tests pass | PASS | `_run_list()` preserves §§3–10 behaviour; pytest `tests/cli/test_views_cmd.py` shows tests 1–13 (cases 1–13) and case 35 all pass (40/40). |
| 15 | All 22 detail-mode cases covered; full pytest suite passes | PASS | `test_views_cmd.py` includes `test_detail_*` cases 14–35 (27 tests); 40 tests in file all pass. Full suite: 422 passed, 3 pre-existing unrelated failures (`test_show_*` editor, `test_pyproject_extras_match_spec`). |
| 16 | README.md "Detail mode" subsection under `views` | PASS | `cli/README.md` lines 561–591 contain `#### Detail mode` subsection with synopsis, mode table, and examples. |
| 17 | s0003 Command Set row updated to `views [<view_name>] [-q\|-j]` | PASS | `s0003-artifacts-os-cli-module.md` line 50 reads `views [<view_name>] [-q\|-j]`. |
| 18 | `artifacts views --help` shows new positional and help text | PASS | `views --help` output shows `usage: artifacts views [-h] [-q \| -j] [name]` and `name show details for this single view (detail mode)`. |

### Summary

18 passed, 0 failed. All verification criteria satisfied; the task is ready to be marked verified.