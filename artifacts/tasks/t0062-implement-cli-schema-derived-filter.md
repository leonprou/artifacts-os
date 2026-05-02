---
kind: task
id: t0062
name: implement-cli-schema-derived-filter
type: implementation
status: ready
assignee: developer
owner: user
parent: "[[t0061-cli-schema-derived-filter-flags]]"
depends_on:
  - "[[t0055-spec-cli-schema-derived-filter]]"
  - "[[t0054-complete-kind-schemas]]"
  - "[[t0057-implement-core-unified-filter-api]]"
created: 2026-05-02
---

# Implement Cli-Schema-Derived-Filter-Flags

## Goal

Implement the schema-derived CLI filter flags specified in
[[artifacts/specs/s0015-cli-schema-derived-filter-flags]]
end-to-end. Single developer pass once dependencies land.

## Context

### Why this task is backlog

Three blockers, all in flight:

- **t0054-complete-kind-schemas** (`ready`) — flag generation is
  schema-driven; it can only generate flags for declared
  `properties`. Without t0054, only `status` and `priority` would
  get flags.
- **t0057-implement-core-unified-filter-api** (`ready`) — generated
  flag values rewrite into the unified `filters=` dict. Without
  t0057's `core.list_artifacts(kind, filters=)` signature, there's
  no clean target to rewrite into.
- **t0055-spec-cli-schema-derived-filter** (`done`, produced
  s0015) — spec dependency satisfied; tracked for documentation.

This task moves to `ready` once t0054 and t0057 reach `done`.

### What lands in this task

Per s0015, the implementation introduces:

- A **two-pass argparse pipeline** for the `list` command:
  pre-scan argv for `--kind`, load the kind's schema, build the
  per-kind subparser with typed flags from `properties`, then
  parse for real.
- A **cross-kind fallback** when `--kind` is absent: union of all
  kinds' properties, no `choices=`, validation deferred to core.
- **Flag → `filters=` rewrite** at the boundary so all values flow
  through the unified core API from t0057.
- **Help-surface generation**:
  `artifacts list --kind <K> --help` lists all filterable axes for
  that kind with enum constraints and descriptions sourced from
  schema.

### Touch points (per s0015)

- `src/artifacts_os/cli/commands/list.py` — `register` (two-pass
  pre-scan + per-kind flag construction), `run` (rewrite to
  `filters=`).
- `src/artifacts_os/cli/__init__.py` — registry must be loadable
  before parser construction; reuse the
  `_peek_create_kind_schema` template established in s0011.
- `tests/cli/test_list_schema_flags.py` (new) — coverage matrix
  per s0015.
- `src/artifacts_os/cli/README.md` — document new surface.

### Test matrix (per s0015)

- Enum match: `--status ready` succeeds for `task` (in enum).
- Enum mismatch: `--status invalid` exits with parse-time error.
- Free-form string: `--priority high` accepts any string.
- Cross-kind union: `artifacts list --type feature` succeeds with
  no `--kind`; validation per-key in core.
- Missing `--kind`: union parser used; no per-kind enum
  validation at parse time.
- Conflicting flag names: schema property colliding with
  `--kind`/`--fields`/`--view`/`--quiet`/`--json`/`--filter`
  handled per s0015 §conflict-handling.
- Composition: explicit CLI flag wins per-key over view config;
  view config still applies for non-overridden keys.

### References

- Spec (authoritative):
  [[artifacts/specs/s0015-cli-schema-derived-filter-flags]]
- Parent feature: [[t0061-cli-schema-derived-filter-flags]]
- Spec sub-task (done):
  [[t0055-spec-cli-schema-derived-filter]]
- Dependent core API:
  [[t0057-implement-core-unified-filter-api]] →
  [[artifacts/specs/s0014-core-unified-filter-api]]
- Schema completion: [[t0054-complete-kind-schemas]]
- Cross-spec: [[s0007-artifacts-os-views-module]],
  [[s0011-cli-create-kind-aware-help]] (template for two-pass
  pre-scan), [[s0012-cli-list-named-views]]
- Current code: `src/artifacts_os/cli/commands/list.py`
  (lines 16–25 `register`; rewrite per s0015)

## Requirements

1. Two-pass parse pipeline per s0015. Pre-scan argv for `--kind`,
   load schema, build per-kind subparser, then parse for real.
2. Property-to-flag mapping per s0015: `enum` → `choices`;
   `type:string` → free-form; `description` → `help`.
3. Cross-kind fallback: union of properties, no `choices=`, no
   parse-time enum validation; defer to core.
4. Generated flag values rewrite into `filters=` dict before
   reaching `core.list_artifacts` (composes with t0057).
5. Conflict handling for collisions with existing flags
   (`--kind`, `--fields`, `--view`, `--quiet`, `--json`,
   `--filter`) per s0015.
6. Reuse `_peek_create_kind_schema` template from s0011 for
   pre-scan; do not duplicate logic.
7. Tests in `tests/cli/test_list_schema_flags.py` covering the
   matrix above.
8. `src/artifacts_os/cli/README.md` updated to document the
   auto-generated flag surface and the two-pass model.
9. All 25 shipped views in `artifacts/artifacts.yaml` continue
   to work after the change (regression smoke).
10. `pytest` passes; no new warnings.

## Verification

- [ ] `artifacts list --kind task --help` lists every filterable
      axis declared in `task.json` with typed signatures
- [ ] `artifacts list --kind task --status invalid` exits with a
      parse-time error and the documented message
- [ ] `artifacts list --type feature` (no `--kind`) succeeds via
      union mode and per-key validation happens in core
- [ ] Generated flags rewrite into `filters=` dict; values reach
      `core.list_artifacts(kind=, filters=)` per s0014
- [ ] Existing `--view` resolution still works; explicit CLI flag
      wins per-key over view filters
- [ ] Conflict cases handled per s0015 \§conflict-handling
- [ ] `tests/cli/test_list_schema_flags.py` covers the s0015 test
      matrix
- [ ] `cli/README.md` documents the new surface
- [ ] All 25 shipped views in `artifacts/artifacts.yaml` continue
      to render correctly (smoke test)
- [ ] `pytest` passes
- [ ] Reviewed and verified by user
