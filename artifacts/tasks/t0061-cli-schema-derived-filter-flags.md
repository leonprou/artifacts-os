---
kind: task
id: t0061
name: cli-schema-derived-filter-flags
type: feature
status: done
assignee: developer
owner: user
created: 2026-05-02
subtasks:
  - "[[t0055-spec-cli-schema-derived-filter]]"
  - "[[t0062-implement-cli-schema-derived-filter]]"
artifacts:
  - "[[s0015-cli-schema-derived-filter-flags]]"
completed: 2026-05-02
---

# Cli-Schema-Derived-Filter-Flags

## User Story

**As a** user of `artifacts list`,
**I want** typed CLI filter flags auto-generated from each kind's
schema (e.g. `--status`, `--assignee`, `--type` for tasks; `--agent`
for specs) with enum values enforced at parse time,
**so that** I can run `artifacts list --kind task --type feature
--status ready` directly from the shell without defining a view or
typing `--filter k=v` strings — and discover the available filter
fields via `artifacts list --kind <K> --help`.

## Authoritative Spec

[[artifacts/specs/s0015-cli-schema-derived-filter-flags]] — produced
by [[t0055-spec-cli-schema-derived-filter]] (done). Architect signed
off on the design with **two-pass parse** as the generation strategy.
This task tracks implementation.

## Sub-tasks

- [[t0055-spec-cli-schema-derived-filter]] — architect produced
  s0015; status: `done`.
- Implementation sub-task — developer implements s0015 end-to-end;
  status: `backlog` (created alongside this feature; unblocks once
  t0054 + t0057 land).

## Tech Requirements (from s0015)

Authoritative reference: [[artifacts/specs/s0015-cli-schema-derived-filter-flags]].
Requirements below are normative; refer to s0015 for rationale,
diagrams, and the strategy comparison table.

1. **Generation strategy** — two-pass parse: pre-scan argv for
   `--kind`, load the kind's schema, build the `list` subparser
   with kind-specific flags, then parse for real. See s0015.
2. **Property → flag mapping** — every entry in the kind's
   `properties` block becomes an argparse flag. `enum` → `choices`.
   `type:string` → free-form. `description` → `help` text.
3. **Cross-kind fallback** — when `--kind` is absent, build a
   generic parser using the **union** of all kinds' properties with
   no `choices=` constraint. Validation deferred to core.
4. **Composition with t0057** — generated flag values rewrite into
   the unified `filters=` dict before reaching
   `core.list_artifacts`. No new resolution path.
5. **Composition with t0054** — flag generation reads from the
   schemas extended by t0054. Without t0054, only `status` and
   `priority` get flags.
6. **Conflict handling** — collisions with existing argparse flags
   (`--kind`, `--fields`, `--view`, `--quiet`, `--json`,
   `--filter`) handled per s0015.
7. **Lifecycle** — registry must load before parser construction.
   Use the `_peek_create_kind_schema` template established in
   s0011.
8. **Tests** — coverage matrix per s0015: enum match, enum
   mismatch (parse-time error), free-form string, cross-kind
   union mode, missing `--kind`, conflicting flag names.
9. **Docs** — update `src/artifacts_os/cli/README.md` to document
   the auto-generated flag surface and the two-pass model.
10. **Smoke** — all 25 shipped views in `artifacts/artifacts.yaml`
    must continue to work (regression guard).

## Verification (epic — drawn from s0015)

- [x] Spec sub-task done before this task moves to `ready`
      (see [[t0055-spec-cli-schema-derived-filter]])
- [ ] `artifacts list --kind task --help` shows
      `--status`/`--assignee`/`--type`/`--owner`/`--priority` with
      typed signatures
- [ ] `artifacts list --kind task --status invalid` exits with a
      parse-time error
- [ ] `artifacts list --type feature` (no `--kind`) succeeds via
      union mode and validates per-key in core
- [ ] Generated flags rewrite into `filters=` dict and flow through
      t0057's unified core API — no regression on
      `_apply_view` / view config merging
- [ ] All 25 shipped views in `artifacts/artifacts.yaml` continue
      to work (smoke test)
- [ ] `tests/cli/` covers the s0015 test matrix
- [ ] `src/artifacts_os/cli/README.md` documents the new surface
- [ ] `pytest` passes
