---
created: 2026-05-02
id: t0075
kind: task
name: cli-list-filter-by-refs
type: implementation
status: done
assignee: developer
owner: user
priority: normal
started: 2026-05-02
completed: 2026-05-02
---

# Implement: `artifacts list` Ref-Set Filter

## Goal

Extend `artifacts list` so the user can pass one or more
artifact references as positional arguments and have the result
filtered down to just those artifacts.

```bash
artifacts list t1 t4
artifacts list t0001 t0042 --fields id,name,status,assignee
artifacts list t1 t4 -j
artifacts list t1 t4 --status ready    # intersection with other filters
```

## User Story (context)

**As a** user (or agent) of `artifacts list`,
**I want** to pass one or more artifact references and have the
result filtered down to just those artifacts,
**so that** I can inspect a known batch of refs in a single table
or JSON payload without writing a shell loop or running
`artifacts show` once per ref.

This pattern shows up routinely — sub-task lists, `depends_on`
arrays, parent/child traversals, and operator hand-offs all
yield a *set of refs*. Today the only options are a shell loop
over `artifacts show` or a wide filter the operator scans by
hand. Strategic context: [[n0003-programmatic-cli-access]].

## Resolved Design

The open questions raised during PM scoping are resolved as
follows:

| Question | Decision |
|---|---|
| Positional vs option flag | **Positional.** `artifacts list [REF …]`. Matches the user's natural invocation (`art list t1 t4`); idiomatic argparse `nargs='*'`. |
| Combine with `--children` / `--parent` | **Intersection.** Treat the ref-set as another filter predicate. `art list t1 t4 --children t0010` returns refs in {t1, t4} that are also direct children of t0010. |
| Combine with `--kind` | **Constrain resolution.** When `--kind` is given, partial-slug refs resolve only within that kind (matches `artifacts show --kind`). Numeric IDs and full names already encode their kind via prefix. |
| Unresolved ref | **Fail fast.** Non-zero exit, stderr error message naming each unresolved ref. Silent skips hide typos. |
| Wikilink form | **Accept.** Strip `[[…]]` wrapping before resolution, for symmetry with `create --parent` / `--depends-on`. |

## Implementation Direction

> Pointers, not a spec. Match existing `cli/` conventions; the
> implementer owns final structure.

1. **Argparse change** — add a positional `refs` argument to
   the `list` subparser with `nargs='*'`. Place it so it does
   not collide with existing options.
2. **Resolution** — for each supplied ref, call the same
   resolver used by `artifacts show` (numeric ID, full name,
   partial slug). Strip `[[…]]` wikilink wrapping first. When
   `--kind` is supplied, scope resolution to that kind.
3. **Composition** — once resolved, the ref-set narrows the
   row set produced by `core.list_artifacts(...)`. It composes
   as an additional predicate alongside `--kind`, `--status`,
   `--filter`, `--children`, `--parent`, `--type`, etc. — pure
   intersection semantics.
4. **Error model** — if any ref does not resolve, exit
   non-zero and emit a single stderr line per unresolved ref:
   `error: unresolved ref '<ref>'`. Do not partially execute.
5. **Output flags untouched** — `-j`, `-q`, `--fields`,
   `--meta`, `--view` continue to work unchanged; only the row
   set narrows.
6. **Help text** — update the `list` subparser help and the
   relevant section of `src/artifacts_os/cli/README.md` to
   document the positional ref-set and the intersection
   semantics with other filters.

## Tests

Add to `tests/cli/` (matching the file layout for other `list`
tests):

- Single ref by numeric ID returns one row.
- Multiple refs return exactly that set, in vault order.
- Full-name ref resolves.
- Unambiguous partial-slug ref resolves; ambiguous fails with
  candidates.
- Wikilink form (`[[t0001]]`) resolves.
- Unresolved ref → non-zero exit, stderr names the ref.
- Combination with `--status` returns the intersection.
- Combination with `--kind` constrains partial-slug resolution.
- Combination with `--children REF` returns refs ∩ children.
- `-j` and `-q` output modes return the same narrowed set.
- No refs supplied → existing `list` behavior unchanged
  (regression).

## Out of Scope

- New filter languages or boolean operators between refs (it's
  a set; AND with the rest of the filter stack).
- Body printing — this is still `list`, not `show`.
- Performance optimizations for very large ref-sets — the
  expected typical size is single digits.
- Changes to `artifacts show` or the underlying resolver.

## Findings

Added positional `refs` (`nargs='*'`) to the `list` subparser. When refs are
supplied, each is unwrapped from wikilink form then resolved via `discover.resolve()`
(with `kind=effective_kind` when `--kind` is active). All refs are resolved up-front;
if any fail (NotFoundError → exit 3, AmbiguousError → exit 4) all errors are printed
to stderr and no output is produced. On success, `items` is filtered to paths in the
resolved set — pure intersection with every other predicate already in place.

**Files changed:**
- `src/artifacts_os/cli/commands/list.py` — `register()` + `run()`
- `src/artifacts_os/cli/README.md` — new *Ref-set filter* subsection

**Tests:** 23 new cases in `tests/cli/test_list_filter_by_refs.py` covering all
required scenarios. 440 pre-existing tests continue to pass.

## Progress

### 2026-05-02 — developer
> time: 21:46

Implemented positional ref-set filter: added refs nargs='*' to register(), ref resolution and intersection logic in run(). 23 new tests in tests/cli/test_list_filter_by_refs.py all pass. Updated cli/README.md. No regressions in 440 previously-passing tests.

## Verification

- [x] `artifacts list t0001 t0042` returns a table containing
      exactly those two artifacts.
- [x] `artifacts list t0001 t0042 -j | jq length` returns `2`.
- [x] Numeric IDs (`t1`), full names
      (`t0001-migrate-docs-specs-to-openstation`), and
      unambiguous partial slugs all resolve.
- [x] `artifacts list "[[t0001]]"` resolves the wikilink form.
- [x] An unresolvable ref produces a non-zero exit with a
      stderr line naming the offending ref; no partial output
      is produced.
- [x] `artifacts list t0001 t0042 --status ready` returns the
      intersection (named refs whose status is `ready`).
- [x] `artifacts list <ambiguous-slug> --kind task` resolves
      within tasks only.
- [x] `artifacts list t1 t4 --children t0010` returns
      refs ∩ direct-children-of-t0010.
- [x] Output flags (`-j`, `-q`, `--fields`, `--meta`, `--view`)
      behave identically to a normal `list` call — only the
      row set narrows.
- [x] `artifacts list --help` documents the positional ref-set
      and intersection semantics.
- [x] `src/artifacts_os/cli/README.md` updated.
- [x] Existing `list` invocations (no refs supplied) are
      unchanged — full test suite passes; shipped views in
      `artifacts/artifacts.yaml` continue to work.

## Verification Report

*Verified: 2026-05-02*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts list t0001 t0042` returns exactly those two artifacts | PASS | Live run returned `['t0001', 't0042']` (length 2); `test_two_refs_json_length` & `test_multiple_refs_in_vault_order` cover this |
| 2 | `... -j \| jq length` returns 2 | PASS | Live `-j` output parsed to JSON of length 2 |
| 3 | Numeric IDs, full names, partial slugs all resolve | PASS | `test_single_ref_by_numeric_id`, `test_full_name_ref_resolves`, `test_unambiguous_partial_slug_resolves` all pass |
| 4 | `[[t0001]]` wikilink resolves | PASS | Live run resolved to t0001; `test_wikilink_form_resolves`, `test_wikilink_full_stem_resolves` pass |
| 5 | Unresolvable ref → non-zero exit + stderr + no partial output | PASS | Live `artifacts list t9999-no-such-thing` → exit 3, stderr `error: unresolved ref 't9999-no-such-thing'`; `test_unresolved_ref_*` tests pass; `list.py` lines 407–412 emit per-ref stderr and return early |
| 6 | Intersection with `--status` | PASS | Live `artifacts list t0075 t0001 --status review -j` returned only t0075; `test_intersection_with_status*` pass |
| 7 | `--kind task` constrains partial-slug resolution | PASS | `test_kind_constrains_partial_slug_resolution`, `test_kind_constrains_resolution_not_found_in_kind` pass; `list.py:400` passes `kind=effective_kind` to `_resolve_ref` |
| 8 | `t1 t4 --children t0010` returns refs ∩ children | PASS | `test_intersection_with_children` passes — only the child ref (t0001) returned, t0004 excluded |
| 9 | Output flags `-j`, `-q`, `--fields`, `--meta`, `--view` work identically | PASS | `test_output_mode_json`, `test_output_mode_quiet`, `test_output_mode_fields` pass; ref-set filter is applied before output formatting (list.py:415–451) |
| 10 | `artifacts list --help` documents the positional ref-set | PASS | Help text shows `[REF ...]` positional with full description of intersection semantics, accepted forms, and fail-fast behavior |
| 11 | `src/artifacts_os/cli/README.md` updated | PASS | README lines 78–146 include "Ref-set filter (positional arguments)" subsection with accepted forms, intersection semantics, fail-fast notes |
| 12 | Existing `list` invocations unchanged (regression) | PASS | `test_no_refs_original_behavior`, `test_no_refs_with_status_filter`, `test_no_refs_empty_vault` pass; `if refs_arg:` guard at list.py:387 makes the ref-filter a strict no-op when refs are absent. Pre-existing test failures in `test_settings.py` and `test_module_system.py` reproduce on `git stash` — unrelated to this change |

### Summary

12 passed, 0 failed. All verification criteria satisfied; the task is ready to be marked verified.
