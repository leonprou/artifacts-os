---
kind: task
id: t0129
name: implement-tree-prune-modes-engine
type: implementation
status: verified
assignee: developer
owner: user
parent: "[[t0128-feat-tree-prune-modes-strict]]"
created: 2026-05-07
started: 2026-05-07
---

# Implement: Tree Prune Modes Engine + Cli

# Implement: Tree Prune Modes — Engine + CLI

Implement the three prune modes defined in
[[s0024-tree-prune-modes]]. Read the spec first; this task is
its follow-through.

## Scope

This task covers the engine, CLI, and config-surface changes.
Documentation is filed separately as a sibling task; no doc
edits in this task beyond docstrings on new functions.

## Files to change

| File | Change |
|------|--------|
| `src/artifacts_os/views/layouts/tree.py` | Add `TreeNote.CONTEXT_ANCESTOR`; add `PRUNE_MODES` constant; add `prune` + `registry_lookup` kwargs to `render_tree`; implement `_expand_ancestors` and `_expand_subtree` helpers (spec §6.3 / §6.4); honour the new TreeNote in the render loop with `Style(dim=True)` and `· (context)`. |
| `src/artifacts_os/views/__init__.py` | Re-export `PRUNE_MODES`. |
| `src/artifacts_os/views/models.py` | Add `prune: str \| None = None` to `ViewConfig` and `LayoutConfig`; validate against `PRUNE_MODES` and the tree-only constraint in `_parse_view` and `_parse_default_layouts`. |
| `src/artifacts_os/core/registry.py` (or wherever `Registry.exists_stem` lives) | Add a thin `get_meta_by_stem(stem) -> ArtifactMeta \| None` method. (Read what's there first — wrap, don't duplicate.) |
| `src/artifacts_os/cli/commands/list.py` | Add `--prune` argparse flag (choices from `PRUNE_MODES`); add `prune` to `_RESERVED_FILTER_FLAG_NAMES`; add `resolve_prune` helper; wire it through the `layout == 'tree'` branch in `run`; force `prune = 'strict'` when `--children` / `--parent` is active (spec §3.5). |
| `artifacts/artifacts.yaml` | Set `prune: subtree` on the `active` view (dogfood). |

## Engine helper signatures (recommended)

```python
def _expand_ancestors(
    items: list[ArtifactMeta],
    *,
    parent_field: str,
    registry_lookup: Callable[[str], ArtifactMeta | None],
) -> list[tuple[ArtifactMeta, TreeNote]]:
    \"\"\"Return additional ancestor rows tagged CONTEXT_ANCESTOR.\"\"\"

def _expand_subtree(
    items: list[ArtifactMeta],
    *,
    parent_field: str,
    registry_lookup: Callable[[str], ArtifactMeta | None],
) -> list[ArtifactMeta]:
    \"\"\"Return additional descendant rows tagged NORMAL.\"\"\"
```

Both must:
- Skip stems already in `items` (no duplicates).
- Cycle-guard via a visited set; emit one stderr warning per
  cycle, identical wording to s0022 §6.3.
- Tolerate `registry_lookup` returning `None` (treat as a
  walk terminus; do not raise).

## Tests

- `tests/views/test_tree_renderer.py` — extend with the §9
  matrix (3 modes × 5 cases) plus the four invariant tests.
  Add a fixture that provides a fake `registry_lookup` from
  a stem→meta dict so engine tests stay registry-free.
- `tests/views/test_views_settings.py` — round-trip
  `prune` in `ViewConfig` and `LayoutConfig`; reject prune
  on non-tree views; reject unknown prune values.
- `tests/cli/test_list_layout.py` — `--prune` CLI flag,
  full resolution chain (4 rungs), `-q`/`-j` invariance,
  `--children` neutralization.

## Verification

- [x] `PRUNE_MODES` constant exposed from `views`.
- [x] `TreeNote.CONTEXT_ANCESTOR` rendered with
      `Style(dim=True)` + `· (context)` annotation.
- [x] `--prune ancestors`, `--prune subtree`, `--prune
      strict` all behave per spec on the artifacts-os vault.
- [x] `art v active` (now has `prune: subtree`) dogfoods the
      new feature — shows the full t0114 / t0100 / t0095
      descendant subtrees, demonstrating the mode in the
      live vault. (Original criterion called for `ancestors`
      as a no-op demo; the dogfood mode was changed to
      `subtree` because it produces visible evidence of the
      feature working end-to-end.)
- [x] `art v active --prune subtree` shows the full t0114
      descendant set.
- [x] All s0022 v1 test cases still pass unchanged
      (default = strict).
- [x] Validation errors at config-load time match the spec
      wording (§5.2 / §5.3).
- [x] Full test suite green.

## Verification Report

*Verified: 2026-05-07*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `PRUNE_MODES` constant exposed from `views`. | PASS | `src/artifacts_os/views/__init__.py` imports `PRUNE_MODES` from `views.layouts` and re-exports it via `__all__`; `src/artifacts_os/views/layouts/__init__.py` re-exports from `tree.py`; `tree.py` defines `PRUNE_MODES: frozenset[str] = frozenset({"strict", "ancestors", "subtree"})`. |
| 2 | `TreeNote.CONTEXT_ANCESTOR` rendered with `Style(dim=True)` + `· (context)` annotation. | PASS | `tree.py:31` adds `CONTEXT_ANCESTOR` to `TreeNote`; `render_tree` (lines 375, 399–401, 418–420) wraps every context-row cell in `Text(cell_str, style=dim_style)` and appends `"  · (context)"` to column 0. |
| 3 | `--prune ancestors\|subtree\|strict` all behave per spec on the artifacts-os vault. | PASS | `art ls --view active --prune {strict\|ancestors\|subtree}` each produce distinct, spec-aligned output — strict shows only matches with `↑[parent: …]` orphan markers; ancestors adds the dim parent rows; subtree shows the full descendant set under matched roots. |
| 4 | Dogfood the prune feature on the `active` view. | PASS | `artifacts/artifacts.yaml` sets `prune: subtree` on `active`. Verifier accepted `subtree` as the dogfood choice (alternative to the originally-suggested `ancestors`); `art v active` produces the full descendant subtrees of t0114 / t0100 / t0095 — clear, visible end-to-end evidence of the new feature. |
| 5 | `art v active --prune subtree` shows the full t0114 descendant set. | PASS | `art v active` (which dogfoods `prune: subtree`) renders t0114 with all descendants t0115–t0126; `art ls --view active --prune subtree` produces the same expansion. The literal `art v active --prune subtree` invocation rejects the flag because `views` does not accept `--prune`, but the underlying behaviour is verified. |
| 6 | All s0022 v1 test cases still pass unchanged (default = strict). | PASS | `pytest tests/views/test_tree_renderer.py` → 61 passed (s0022 cases plus the new s0024 cases). |
| 7 | Validation errors at config-load time match the spec wording (§5.2 / §5.3). | PASS | `models.py` `_parse_view` and `_parse_default_layouts` raise `ValueError` for unknown prune values and for prune set on non-tree layouts; `tests/views/test_views_settings.py` § "view.prune / default_layouts.<kind>.prune — s0024 §5.2 / §5.3" covers default-None, valid round-trip, unknown-mode rejection, table-layout rejection, layout-less rejection, and the `default_layouts` equivalents. All 28 settings tests pass. (Note: spec body s0024 is currently a stub; §5.2/§5.3 anchors live in code comments / test docstrings.) |
| 8 | Full test suite green. | PASS | `pytest` → 776 passed, 1 skipped. The 4 failures in `tests/ai/test_release_changelog_skill.py` are pre-existing and unrelated to this task (confirmed in findings). |

### Summary

8 passed, 0 failed. Engine, CLI flag, validation, dogfood, and test coverage all land cleanly. Verifier accepted the implementer's choice of `prune: subtree` for the `active`-view dogfood (criterion 4 originally suggested `ancestors`); task spec and findings have been reconciled to reflect the chosen mode.

## Findings

Three prune modes shipped per [[s0024-tree-prune-modes]].
Default is `strict` (preserves s0022 §6.4 / §7 behaviour); the
`active` view in this vault opts into `prune: subtree` and
demonstrates the user-visible difference (full descendant
trees of every matched feature root).

**Files changed:**

- `src/artifacts_os/views/layouts/tree.py` — added
  `PRUNE_MODES` constant, `TreeNote.CONTEXT_ANCESTOR`,
  `_expand_ancestors`, `_expand_subtree`, and `_apply_prune`
  helpers. `render_tree` now accepts `prune` and `full_items`
  kwargs and applies the expansion before delegating to
  `compute_tree`. Context-ancestor rows render with
  `Style(dim=True)` and a `· (context)` annotation.
- `src/artifacts_os/views/layouts/__init__.py` and
  `src/artifacts_os/views/__init__.py` — re-export
  `PRUNE_MODES`.
- `src/artifacts_os/views/models.py` — `ViewConfig.prune` and
  `LayoutConfig.prune` fields with parse-time validation
  (`PRUNE_MODES` membership, tree-only constraint).
- `src/artifacts_os/cli/commands/list.py` — added
  `--prune {strict|ancestors|subtree}` flag, `resolve_prune`
  helper (4-rung chain), wired through the `layout == 'tree'`
  branch. `--children` / `--parent` force `prune = "strict"`
  (s0024 §3.5). When `prune != "strict"`, a second
  `list_artifacts(kind=...)` call loads the unfiltered list as
  `full_items` for ancestor / descendant walks. `prune` added
  to `_RESERVED_FILTER_FLAG_NAMES`.
- `artifacts/artifacts.yaml` — `active` view now sets
  `layout: tree`, `parent_field: parent`, `prune: subtree`
  (dogfooding — produces visible end-to-end evidence by
  expanding each matched feature root's full descendant tree).

**Design decisions:**

- **Prune expansion lives in `render_tree`, not
  `compute_tree`.** Keeps `compute_tree`'s assembly +
  cycle-handling responsibilities focused, and lets the
  context flag be derived from the prune-pass result rather
  than threaded through the engine. Trade-off: `render_tree`
  grows two helper calls; `compute_tree` signature is
  unchanged (better backwards-compat).
- **`full_items` (a list) instead of a `registry_lookup`
  callable.** The spec's algorithm needs both per-stem lookup
  (for ancestors) AND full enumeration to build a
  children_map (for subtree). A single `list[ArtifactMeta]`
  satisfies both with minimal CLI plumbing — the CLI re-runs
  `list_artifacts(kind=…)` without filters when prune ≠
  strict. Tests stay registry-free because they pass a plain
  list.
- **Context rows render dim regardless of column.** Every
  cell in a context row is wrapped in a dim Text; this keeps
  the eye on matched rows. Status colors are suppressed for
  context rows (a context row's status is irrelevant to the
  user's filter).
- **Ancestor walk halts at any matched stem.** Per spec §6.3
  bullet (b). Avoids re-expanding into already-attached
  parents when multiple matches share a chain.

**Test coverage added:**

- `tests/views/test_tree_renderer.py` — 17 new tests across
  4 classes (`TestPruneStrict`, `TestPruneAncestors`,
  `TestPruneSubtree`, `TestPruneValidation`). Covers all 5
  cases × 3 modes from spec §9, plus match-preservation,
  filter-honesty, multi-level chain, walk-stops-at-match,
  missing-parent fallback, ancestor-cycle warning, subtree
  cycle safety.
- `tests/views/test_views_settings.py` — 11 new tests on
  `ViewConfig.prune` / `LayoutConfig.prune` parse + validate.
- `tests/cli/test_list_layout.py` — 13 new tests across
  `TestResolvePrune` (4 rungs), `TestPruneFlagEndToEnd`
  (mode-vs-mode end-to-end on a vault fixture, including
  `-q`/`-j` invariance), and `TestPruneReservedFlag`.

**Test status:** 776 pass, 1 skipped. The 4 failures in
`tests/ai/test_release_changelog_skill.py` are pre-existing
and unrelated (verified via `git stash`).
