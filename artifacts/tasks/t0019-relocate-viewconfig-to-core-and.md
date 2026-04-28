---
kind: task
id: t0019
name: relocate-viewconfig-to-core-and
type: spec
status: rejected
assignee: architect
owner: user
created: 2026-04-26
started: 2026-04-26
completed: 2026-04-26
---

# Relocate Viewconfig To Core And Decouple Config From Views

## Context

s0009 currently places `config` downstream of `views` in the dependency
DAG (`core → views → config → cli, tui`). This is forced by `config`
dispatching to `views.parse_view_config` per named view entry, which
makes a renderer a dependency of a loader.

Relocating the `ViewConfig` data shape to `core/models.py` removes this
inversion: `config` constructs `ViewConfig` directly via a private
helper, and `views` and `config` become parallel siblings under `core`.

## Requirements

1. **Update `artifacts/specs/s0009-artifacts-os-config-module.md`:**
   - Module Dependency section — replace DAG with two parallel branches:
     ```
     core → config → cli, tui
     core → views  → cli, tui
     core → log    → ai
     ```
   - Remove "depends on `views` (for `parse_view_config`)" — `config`
     now depends only on `core`.
   - Public API — remove the line stating `ViewConfig` is imported from
     `views`. Add note that `ViewConfig` lives in `core.models` and is
     imported from there.
   - `load_settings` step 4 — replace "call `views.parse_view_config(dict)`"
     with "construct `ViewConfig` via private `_parse_view(dict)` helper
     local to `config`".
   - Add a brief rationale paragraph under "Module Dependency" explaining
     why `ViewConfig` lives in `core` (pure data shape, consumed by both
     `config` and `views`, parallel to `KindDef`/`ArtifactMeta`).

2. **Update `artifacts/specs/s0007-artifacts-os-views-module.md`:**
   - Public API — remove `ViewConfig` and `parse_view_config` from the
     export list. Add a note: "`ViewConfig` is defined in `core.models`
     and consumed by `views` for column resolution."
   - Key Concepts → ViewConfig section — rewrite to state that `views`
     consumes the dataclass (via `.columns`) but does not own or parse
     it. Cross-reference s0009 for the parsing path.
   - Scope Boundary "In" — remove `ViewConfig` and `parse_view_config`
     entries.
   - Scope Boundary "Out" — add "view-config parsing (delegated to
     `artifacts_os.config`)".
   - Settings YAML Schema (views section) — keep the schema examples
     (still useful as views-domain documentation) but update the closing
     line to reference `config._parse_view` instead of
     `views.parse_view_config`.

3. **Document the `ViewConfig` placement in `core` (s-level decision):**
   - In s0009, briefly state `ViewConfig` will be added to
     `core/models.py` next to `KindDef` and `ArtifactMeta`. Fields:
     `columns: str`, `filters: dict[str, Any]`, `sort: str | None`.
   - No spec rewrite of `core` is needed — the addition is small enough
     to land via implementation. Note this in the s0009 "Module
     Dependency" rationale.

4. **Preserve boundaries — do NOT:**
   - Modify any source code under `src/` (this is a spec task only).
   - Re-open the "single file vs split files" decision in s0009
     (option a stands).
   - Change `views`'s rendering API (`render_table`, `FieldSpec`, etc.).
   - Touch `core`'s existing public API beyond noting the new `ViewConfig`
     dataclass addition.

## Verification

- [x] s0009 DAG section shows `core → config → cli, tui` (no `views` in path)
- [x] s0009 no longer says `config` imports from `views`
- [x] s0009 `load_settings` step 4 references a private helper, not `views.parse_view_config`
- [x] s0009 contains a rationale paragraph for `ViewConfig` living in `core`
- [x] s0007 Public API export list does not include `ViewConfig` or `parse_view_config`
- [x] s0007 ViewConfig section describes consumption only, references s0009
- [x] s0007 Scope Boundary "Out" includes view-config parsing delegation
- [x] Both specs cross-reference each other consistently

## Verification Report

*Verified: 2026-04-26*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | s0009 DAG section shows `core → config → cli, tui` (no `views` in path) | PASS | s0009 Module Dependency code block lines 106–110: `core → config → cli, tui` and `core → views → cli, tui` as parallel branches |
| 2 | s0009 no longer says `config` imports from `views` | PASS | s0009 line 103: "config depends only on core … views is a parallel sibling — neither imports from the other"; line 112 explicitly forbids `config` importing from `views` |
| 3 | s0009 `load_settings` step 4 references a private helper, not `views.parse_view_config` | PASS | s0009 line 63–64: "construct `ViewConfig` via the private `_parse_view(dict)` helper local to `config`" |
| 4 | s0009 contains a rationale paragraph for `ViewConfig` living in `core` | PASS | s0009 §"Rationale: ViewConfig in core" (lines 114–130) explains pure data shape, dual consumption by `config` and `views`, parallel to `KindDef`/`ArtifactMeta` |
| 5 | s0007 Public API export list does not include `ViewConfig` or `parse_view_config` | PASS | s0007 export block (lines 36–41) lists only `FieldSpec`, `parse_field_specs`, `format_field`, `render_table`, `default_columns` |
| 6 | s0007 ViewConfig section describes consumption only, references s0009 | PASS | s0007 §ViewConfig (lines 59–67): "views does not own, parse, or construct ViewConfig … see s0009 for the parsing path" |
| 7 | s0007 Scope Boundary "Out" includes view-config parsing delegation | PASS | s0007 Scope Boundary "Out" (lines 109–110): "view-config parsing (delegated to `artifacts_os.config`)" |
| 8 | Both specs cross-reference each other consistently | PASS | s0009 rationale references s0007; s0007 intro and ViewConfig section both reference s0009 |

### Summary

8 passed, 0 failed. All verification criteria met — both specs correctly reflect the decoupled DAG with `ViewConfig` in `core.models`.

## Findings

Updated `artifacts/specs/s0009-artifacts-os-config-module.md` and
`artifacts/specs/s0007-artifacts-os-views-module.md` to establish
`ViewConfig` as a `core.models` dataclass, decoupling `config` and
`views` into parallel siblings under `core`.

Key decisions recorded:

- **DAG** (s0009): replaced `core → views → config → cli, tui` with two
  parallel branches — `core → config → cli, tui` and `core → views → cli, tui`.
- **`_parse_view` helper** (s0009): `load_settings` step 4 now delegates to a
  private helper in `config`, not to `views.parse_view_config`.
- **`ViewConfig` in `core`** (s0009 rationale + dataclass definition): pure
  data shape with `columns: str`, `filters: dict[str, Any]`, `sort: str | None`;
  placed in `core/models.py` alongside `KindDef` and `ArtifactMeta`.
- **s0007 export list** cleaned of `ViewConfig` and `parse_view_config`; intro,
  ViewConfig section, and Scope Boundary updated to describe consumption only.
- **Cross-references**: s0007 references s0009 twice (intro + ViewConfig section);
  s0009 rationale references s0007.

No source code was touched — this is a spec-only change.

## Resolution

Closed as obsolete (status: rejected). The DAG fix this task proposed
is subsumed by [[s0010-core-settings-module-spec]], which folds
settings parsing into `core` directly — there is no longer a separate
`config` module to decouple from `views`. `ViewConfig` lands in
`core.models` as part of that spec.

See also `t0024-spec-core-settings-module-supersede` for the decision
to fold settings into `core`.
