---
kind: task
id: t0056
name: core-unified-filter-api
type: feature
status: review
assignee: developer
owner: user
created: 2026-05-01
subtasks:
  - "[[t0053-spec-core-unified-filter-api]]"
  - "[[t0057-implement-core-unified-filter-api]]"
artifacts:
  - "[[s0014-core-unified-filter-api]]"
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
- [ ] `core.list_artifacts(kind, filters=...)` accepts the unified
      dict signature; keyword-only `filters` enforced
- [ ] `status=` kwarg works as deprecated alias and emits
      `DeprecationWarning`
- [ ] `cli/commands/list.py` no longer contains
      `_apply_extra_filters`; `_apply_view` reduced to a single
      dict merge (no per-key dispatch)
- [ ] `artifacts list --filter k=v` flag is wired and repeatable
- [ ] Per-key precedence: explicit `--status`/`--filter` wins over
      view filters; non-overridden view keys retained
- [ ] Unknown filter keys raise `ValidationError` with the documented
      message (see s0014 §6)
- [ ] Cross-kind queries validate per-key existence per s0014 §6.3
- [ ] All call sites in s0014 §11 migrated; `pytest` passes
- [ ] `core/README.md` documents the new API
- [ ] No regression on existing view behavior (spot-check
      shipped views in `artifacts.yaml`)
