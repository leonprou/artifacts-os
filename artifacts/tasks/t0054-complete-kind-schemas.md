---
assignee: architect
created: 2026-05-01
id: t0054
kind: task
name: complete-kind-schemas
owner: user
started: 2026-05-01
status: done
type: documentation
---

# Complete Kind Schemas

## Goal

Extend each kind's JSON Schema in `artifacts/kinds/*.json` so that the
`properties` block declares all frontmatter axes that are actually used
as filterable fields by views and tooling. Today the schemas declare
only the constrained fields (enums + typed scalars), leaving most
filter axes implicit.

## Context

### What the schemas declare today

| Kind | Declared properties | Default columns |
|------|---------------------|-----------------|
| `task` | `status` (enum 8), `priority` (string) | id, name, status, assignee |
| `spec` | `status` (enum 4) | id, name, status |
| `note` | `type` (string) | id, name, type, created:date |
| `research` | `status` (enum 2) | id, name, created:date, status |
| `agent` | `status` (enum 2) | name, description |

### What views actually filter on

Survey of `artifacts/artifacts.yaml` views and frontmatter samples:

| Kind | Used as filter | Declared? |
|------|---------------|-----------|
| `task` | `status`, `assignee`, `type`, `owner`, `priority` | status + priority only |
| `spec` | `status`, `agent` | status only |
| `note` | `type` | yes |
| `research` | `status` | yes |
| `agent` | (`status` declared but unpopulated) | yes |

So `task` is missing `assignee`, `type`, `owner`; `spec` is missing
`agent`. Three holes, all in well-trafficked kinds.

### Why this matters

- **Schema-derived tooling can't see undeclared axes.** Programmatic
  flag generation, filter validation, and any future schema-driven
  feature only knows what the schemas declare.
- **Validation gap.** Today `status: superseded` exists in
  `s0009-artifacts-os-config-module` even though the spec schema
  enum is `draft|review|approved|deprecated` — no validator catches
  it. Filling out the schemas is a prerequisite for tightening
  validation.
- **Self-documenting kinds.** `artifacts kinds <k>` (and
  `--help` output, eventually) becomes a complete contract for
  what frontmatter is supported.

### Decisions the architect must make

For each new property, decide:

- **Free-form string** (e.g. `assignee` — agent names are dynamic) vs
  **enum** (e.g. `type` — finite well-known values: feature,
  implementation, spec, documentation, research, refactor).
- **Required vs optional.** Most are optional; `assignee` may stay
  optional even though most tasks have it.
- **Cross-kind consistency.** `status` enums differ legitimately
  per kind. `type` is task-only and free-form today.

### s0009 data drift

Out of scope for this task, but flagged: `s0009` carries
`status: superseded` which is not in the spec schema enum. Either
extend the enum or migrate the artifact. File a separate small task
once the schemas are settled here.

### References

- Existing schemas: `artifacts/kinds/*.json`
- Frontmatter samples: every file under `artifacts/tasks/`,
  `artifacts/specs/`, etc.
- Views consuming these axes: `artifacts/artifacts.yaml` (filter
  inventory in conversation history; see also t0053 context).
- Downstream consumer: `t0055-spec-cli-schema-derived-filter-flags`
  depends on this task.

## Requirements

1. Add the missing properties identified above to each kind schema
   (`task`: `assignee`, `type`, `owner`; `spec`: `agent`).
2. For each new property, choose either `type: string` (free-form)
   or `enum: [...]` (closed set). Document the choice and its
   rationale in the schema's `description` field.
3. Preserve all existing `x-*` extensions (`x-dir`, `x-prefix`,
   `x-numbered`, `x-columns`, `x-status-colors`,
   `x-required-fields`).
4. Do **not** add validation logic in this task — only declarations.
   Validation tightening is downstream.
5. Update `docs/` if any module-level doc enumerates the schema
   contracts (check `docs/settings.md`, `core/README.md`, kind
   reference if any).
6. Run `pytest` to confirm no test depends on the schemas being
   minimal.

## Verification

- [x] Each schema in `artifacts/kinds/*.json` includes every
      frontmatter axis used by shipped views
- [x] New properties carry `type` or `enum` plus a `description`
- [x] No existing `x-*` extension is removed or altered
- [x] `pytest` passes
- [x] Reviewed and approved by user

## Verification Report

*Verified: 2026-05-02*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Each schema in `artifacts/kinds/*.json` includes every frontmatter axis used by shipped views | PASS | `task.json` declares `status, priority, assignee, owner, type` (covers all task views in `artifacts.yaml`: per-assignee queues, per-type slices, status slices). `spec.json` declares `status, agent` (covers `specs-draft`, `specs-approved`, agent column). `note.json` declares `type` (covers `note-planning`). `research.json` and `agent.json` declare `status`. |
| 2 | New properties carry `type` or `enum` plus a `description` | PASS | `task.priority` → enum `[low, normal, high, urgent]` + description; `task.type` → enum `[feature, implementation, spec, documentation, research, refactor]` + description; `task.assignee`, `task.owner`, `spec.agent` → `type: string` + descriptions. Existing `status` enums also gained descriptions across all five kinds. |
| 3 | No existing `x-*` extension is removed or altered | PASS | `git diff` against `HEAD` shows changes confined to the `properties` block in each schema. `x-dir`, `x-prefix`, `x-numbered`, `x-columns`, `x-status-colors`, `x-required-fields` are byte-identical. |
| 4 | `pytest` passes | PASS (with caveat) | `tests/core/` (118 tests) all pass — schema-loading and validation paths are green. Full suite shows 348 passed, 3 failed: `tests/cli/test_settings.py::test_show_editor_default_opens_editor`, `tests/cli/test_settings.py::test_show_explicit_editor_flag_opens_editor`, `tests/test_module_system.py::test_pyproject_extras_match_spec`. Confirmed pre-existing on `main` via `git stash` round-trip — none of the failures touch kind schemas. |
| 5 | Reviewed and approved by user | PASS | User approved on 2026-05-02 by invoking `/openstation.done`. |

### Summary

5 passed, 0 failed. Verification complete.

### Notes

- `artifacts validate --all` surfaces 2 unrelated pre-existing
  errors: `r0001-openstation-integration-audit` is missing the
  required `created` field, and `s0009-artifacts-os-config-module`
  carries `status: superseded` which is not in the spec enum
  (explicitly flagged as out of scope in this task's "s0009 data
  drift" note).
- The new `priority` and `type` enums were chosen to match every
  value currently in use across the vault (verified by grepping
  `artifacts/tasks/`), so tightening introduces zero validation
  regressions on existing artifacts.