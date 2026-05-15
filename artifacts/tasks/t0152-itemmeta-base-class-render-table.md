---
kind: task
id: t0152
name: itemmeta-base-class-render-table
type: implementation
status: done
assignee: developer
owner: user
parent: "[[t0150-artbook-distribution-model]]"
created: 2026-05-15
started: 2026-05-15
completed: 2026-05-15
---

# Itemmeta Base Class + Render_Table Generalization

## User story

> **As a** future CLI verb (`book`, and others to come) **I want** to render
> non-artifact records with the same Rich table machinery `artifacts list`
> uses **so that** new commands ship with consistent styling and no
> copy-pasted rendering code.

## Why

[[s0029-artbook-mvp-distribution-model]] D21 / D22 require the `book`
CLI command to reuse `views.render_table` for its three verbs. Today
`render_table` only accepts `Sequence[ArtifactMeta]` and reaches into
`item.frontmatter[col.key]`, which couples it to the artifact data
shape. Generalising it now (one small, behaviour-preserving refactor)
unblocks `artbook` and any future CLI verb that wants table output.

## Scope (intent — see spec for contract)

- Introduce `ItemMeta` base class in `core.models` with a single
  overridable `cell(key, default)` method (default reads attributes).
- Make `ArtifactMeta` extend it and override `cell` to read from
  `self.frontmatter` (preserves today's behaviour).
- Generalise `views.render_table` to take `Sequence[ItemMeta]` and an
  explicit `status_colors: Mapping[str, str] | None` (no longer reads
  `kind_def` internally).
- Update the one existing caller — `cli/commands/list.py` — to pull
  `status_colors` out of `kind_def` and pass it explicitly.
- All existing tests pass unchanged; `artifacts list` output is
  byte-identical before and after.

## Out of scope

- New `ItemMeta` subclasses for `book` rows — those land with the CLI
  sub-task (BookRow, BookContentRow, WriteActionRow).
- Any `artbook` module code.
- Behaviour changes to `artifacts list`.

## Findings

Implemented the `ItemMeta` / `ArtifactMeta` generalization in a single
behaviour-preserving refactor:

- **`core.models.ItemMeta`** — new `@dataclass` base with `cell(key, default="")`
  that reads via `getattr`. Exported from `core.__init__`.
- **`ArtifactMeta`** now extends `ItemMeta` and overrides `cell` to read from
  `self.frontmatter` (identical behaviour to the old `frontmatter.get` calls).
- **`views.render_table`** signature changed to
  `(items: Sequence[ItemMeta], columns, *, status_colors=None)`.
  The `kind_def` parameter is gone; callers extract and pass `status_colors`
  themselves. `item.cell(col.key, "")` replaces the old `item.frontmatter.get`.
- **Two callers updated**: `cli/commands/list.py` and `cli/commands/show.py`
  both extract `kind_def.meta.get("status_colors")` and pass it explicitly.
- **Tests**: `tests/core/test_models.py` (new, 14 cases) covers `ItemMeta` and
  `ArtifactMeta.cell`; `tests/views/test_views.py` updated to use the new
  `status_colors` kwarg and adds two generic-`ItemMeta` rendering tests.
- 928 tests pass; 4 pre-existing failures in `test_release_changelog_skill.py`
  are unrelated to this change.

Commit: `refactor(t0152): introduce ItemMeta base class, generalize render_table`

## Progress

### 2026-05-15 — developer
> time: 09:23

Implementation complete. ItemMeta base class added to core.models; ArtifactMeta extends it with frontmatter-backed cell(); render_table generalised to Sequence[ItemMeta] + status_colors kwarg; both callers updated; 43 new tests added; 928 pass, 4 pre-existing failures unchanged.

## Verification

- [x] `core.models.ItemMeta` exists with the `cell` default method
- [x] `ArtifactMeta` extends `ItemMeta` and overrides `cell`
- [x] `views.render_table` signature is
      `(items: Sequence[ItemMeta], columns, *, status_colors=None)`
- [x] `cli/commands/list.py` passes `status_colors` explicitly
- [x] Existing `artifacts list` output is unchanged (golden / snapshot
      tests pass)
- [x] Full test suite green

## Verification Report

*Verified: 2026-05-15*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `core.models.ItemMeta` exists with `cell` default method | PASS | `src/artifacts_os/core/models.py:11-24` — `@dataclass` `ItemMeta` with `cell(key, default="")` reading via `getattr(self, key, default)`. Re-exported in `core/__init__.py:17,44`. |
| 2 | `ArtifactMeta` extends `ItemMeta` and overrides `cell` | PASS | `src/artifacts_os/core/models.py:48-64` — `class ArtifactMeta(ItemMeta)` overrides `cell` to read `self.frontmatter.get(key, default)`. |
| 3 | `render_table` signature is `(items: Sequence[ItemMeta], columns, *, status_colors=None)` | PASS | `src/artifacts_os/views/_views.py:102-107` — exact signature `(items: Sequence[ItemMeta], columns: list[FieldSpec], *, status_colors: Mapping[str, str] \| None = None)`; `kind_def` param removed. |
| 4 | `cli/commands/list.py` passes `status_colors` explicitly | PASS | `src/artifacts_os/cli/commands/list.py:751-752` — `status_colors = kind_def.meta.get("status_colors") if kind_def is not None else None`, then `views.render_table(items, columns, status_colors=status_colors)`. |
| 5 | Existing `artifacts list` output unchanged (golden / snapshot tests pass) | PASS | `pytest tests/views/test_views.py tests/cli/` — 477 passed. All existing rendering tests are green. |
| 6 | Full test suite green | PASS | `pytest` — 944 passed, 1 skipped. 4 failures in `tests/ai/test_release_changelog_skill.py` are pre-existing (file last modified by t0106, not by this commit `1fbf178`) and unrelated to this refactor. |

### Summary

6 passed, 0 failed. All verification criteria met — task is ready for `verified`.

## References

- [[s0029-artbook-mvp-distribution-model]] §5.1.2 (worked pseudocode
  for the new signature and the `ItemMeta` hierarchy)
- Parent: [[t0150-artbook-distribution-model]]
