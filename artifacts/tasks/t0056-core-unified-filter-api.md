---
kind: task
id: t0056
name: core-unified-filter-api
type: feature
status: done
assignee: developer
owner: user
created: 2026-05-01
subtasks:
  - "[[t0053-spec-core-unified-filter-api]]"
  - "[[t0057-implement-core-unified-filter-api]]"
artifacts:
  - "[[s0014-core-unified-filter-api]]"
completed: 2026-05-02
---

# Core-Unified-Filter-Api

## User Story

**As a** consumer of `core.list_artifacts` (CLI, TUI, AI, scripts),
**I want** a single filter API where `kind` selects the directory
and `filters: dict` carries all equality predicates,
**so that** view configs in `artifacts.yaml` and CLI flags merge
through one path — config writes filters first, CLI overrides
per-key, both end up at the same core call.

## Authoritative Spec

[[artifacts/specs/s0014-core-unified-filter-api]] — produced by
[[t0053-spec-core-unified-filter-api]] (done). Architect signed off
on the design; this task tracks implementation.

## Sub-tasks

- [[t0053-spec-core-unified-filter-api]] — architect produced
  s0014; status: `done`.
- Implementation sub-task — developer implements s0014 end-to-end;
  status: `ready` (created alongside this feature).

## Tech Requirements (from s0014)

Authoritative reference: [[artifacts/specs/s0014-core-unified-filter-api]].
Requirements below are normative; refer to s0014 for rationale,
diagrams, and migration tables.

1. **API signature** — `core.list_artifacts(kind=None, *, filters=None)`
   per s0014 §3. `filters` is keyword-only (s0014 §3.1).
2. **Resolution algorithm** — single `resolve_filters` pass replaces
   per-key dispatch in `cli/commands/list.py:_apply_view`. See
   s0014 §4.
3. **Precedence** — explicit CLI flag wins per-key over view config.
   Wholesale replacement forbidden. See s0014 §7.
4. **`kind` placement** — stays a named param (directory selection,
   schema lookup, validation order). See s0014 §5.
5. **Validation** — hard `ValidationError` on unknown filter keys.
   Cross-kind: per-key existence rule (s0014 §6.3).
6. **`status=` deprecation** — alias for `filters={"status":...}`
   with `DeprecationWarning`, removed after one minor cycle.
   See s0014 §9.
7. **CLI surface** — `--filter k=v` repeatable flag added to
   `artifacts list`. `_apply_view` rewrite. `_apply_extra_filters`
   removed. See s0014 §8.
8. **Migration** — update all call sites of
   `core.list_artifacts(status=...)`. Affected modules: `cli`,
   `views`, tests. See s0014 §11 for the call-site table.
9. **Tests** — coverage matrix per s0014 §10 (core API matrix,
   deprecation compat, CLI integration matrix, validation surface).
10. **Docs** — update `core/README.md` per s0014 §13.

## Verification (epic — drawn from s0014 §13)

- [x] Spec sub-task done before this task moves to `ready`
      (see [[t0053-spec-core-unified-filter-api]])
- [x] `core.list_artifacts(kind, filters=...)` accepts the unified
      dict signature; keyword-only `filters` enforced
- [x] `status=` kwarg works as deprecated alias and emits
      `DeprecationWarning`
- [x] `cli/commands/list.py` no longer contains
      `_apply_extra_filters`; `_apply_view` reduced to a single
      dict merge (no per-key dispatch)
- [x] `artifacts list --filter k=v` flag is wired and repeatable
- [x] Per-key precedence: explicit `--status`/`--filter` wins over
      view filters; non-overridden view keys retained
- [x] Unknown filter keys raise `ValidationError` with the documented
      message (see s0014 §6)
- [x] Cross-kind queries validate per-key existence per s0014 §6.3
- [x] All call sites in s0014 §11 migrated; `pytest` passes
- [x] `core/README.md` documents the new API
- [x] No regression on existing view behavior (spot-check
      shipped views in `artifacts.yaml`)

## Verification Report

*Verified: 2026-05-02*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec sub-task done before parent moves to `ready` | PASS | `t0053-spec-core-unified-filter-api` status: `done`; spec `s0014` committed under `artifacts/specs/`. |
| 2 | `core.list_artifacts(kind, filters=...)` keyword-only `filters` | PASS | `src/artifacts_os/core/discover.py:96-103` — signature `list_artifacts(registry, kind=None, *, filters=None, status=None, tag=None)`; `*` makes `filters` keyword-only. |
| 3 | `status=` kwarg deprecated alias emits `DeprecationWarning` | PASS | `discover.py:130-141` deprecation shim using `warnings.warn(..., DeprecationWarning, stacklevel=2)`; tests `test_deprecated_status_kwarg_returns_correct_result`, `test_deprecated_tag_kwarg_returns_correct_result`, `test_deprecated_status_explicit_filters_wins` all pass with `pytest.warns(DeprecationWarning)`. |
| 4 | `_apply_extra_filters` removed; `_apply_view` is a single dict merge | PASS | `grep -rn _apply_extra_filters` returns no hits. `cli/commands/list.py:_apply_view` (lines 201-245) only sets `args._sort` / `args._view_cfg`; merge logic lives in `resolve_filters` (lines 45-80) as a single key-agnostic loop. |
| 5 | `artifacts list --filter k=v` repeatable | PASS | `cli/commands/list.py:20-27` registers `--filter` with `action="append"`. Smoke test: `artifacts list --filter assignee=developer -q` returns expected rows. |
| 6 | Per-key precedence (CLI flag wins over view filters; other view keys retained) | PASS | Tests `test_cli_view_status_overridden_by_flag`, `test_cli_view_assignee_overridden_by_filter`, `test_cli_view_assignee_kind_flag_overrides`, `test_cli_view_complex_override` all pass. `resolve_filters` seeds view first, then overwrites per-key. |
| 7 | Unknown filter keys raise `ValidationError` with documented message | PASS | `discover.py:88-93` raises `ValidationError(f"unknown filter key {key!r} for kind {kind!r}; known keys: {sorted(known)}")`. CLI smoke: `artifacts list --filter asignee=alice` → exit 2, message printed. Tests `test_core_list_unknown_key_raises`, `test_cli_filter_unknown_key_with_kind_exits_2` pass. |
| 8 | Cross-kind queries validate per-key existence (s0014 §6.3) | PASS | `discover.py:84-87` unions known keys across `registry.all()` when `kind is None`. Test `test_cli_filter_unknown_key_cross_kind_exits_2` passes; CLI smoke confirms `kind 'None'` message. |
| 9 | All call sites migrated; pytest passes | PASS | `core/discover.py:children` migrated to `filters={"status": status}` (line 372); `cli/commands/list.py:run` uses unified `list_artifacts(registry, kind=kind, filters=filters or None)`. `tests/core/test_discover.py` updated; new `tests/core/test_list_artifacts_filters.py` (44 tests) passes. Three failing tests in `tests/cli/test_settings.py` and `tests/test_module_system.py` are pre-existing (introduced by t0038 / initial commit) and unrelated to filter API. |
| 10 | `core/README.md` documents new API | PASS | `src/artifacts_os/core/README.md` has dedicated `list_artifacts — unified filter API (s0014)` section (lines 64-116) with signature, examples (kind+filters, cross-kind, conjunction, tags membership, dict-form sugar), validation rules, and deprecation guidance. |
| 11 | No regression on shipped views in `artifacts.yaml` | PASS | Smoke tested `artifacts list --view ready`, `--view developer-queue`, `--view active`, `--kind task --status ready --filter assignee=developer` — all return expected results. View seeding + per-key CLI override works end-to-end. |

### Summary

11 passed, 0 failed. All verification criteria for t0056 are
satisfied. The unified filter API is implemented end-to-end:
core API, CLI surface, deprecation shim, validation, tests, docs,
and shipped-view compatibility.
