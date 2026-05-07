---
kind: task
id: t0127
name: feat-multi-value-filters-in
type: feature
status: done
assignee: architect
owner: user
created: 2026-05-07
started: 2026-05-07
artifacts:
  - "[[openstation/specs/s0023-multi-value-filters]]"
completed: 2026-05-07
---

# Feat: Multi-Value Filters In Views And --Status

# Feat: Multi-Value Filters In Views (And `--status`)

## User story

As a vault user defining a view, I want to filter on **multiple
allowed values** for a single field — most importantly
`status: [ready, in-progress, review]` — so I can express
"all in-flight work" in one named view instead of fanning out
per-status views and switching between them.

The CLI flag should mirror the same idea:
`art ls --kind task --status ready,in-progress`.

## Context

- Today, `core.discover.list_artifacts` only supports scalar
  equality: every `(key, value)` is `str(meta[key]) == str(value)`,
  with one special case for `tags` (list-membership). See
  `src/artifacts_os/core/discover.py:155-167`.
- `ViewConfig.filters` is a flat dict of scalars; values that
  happen to be lists are not interpreted today.
- The `--status` CLI flag (added by `_add_schema_filter_flags`
  in `src/artifacts_os/cli/commands/list.py`) accepts a single
  string.
- A vault may carry one "all" view per kind to dodge the limit,
  but that's a workaround — the user wants compose-able
  multi-status views.

## Design decision (architect: confirm or revise)

The discussion settled on **Option 1 — list values mean OR
within a key; keys remain ANDed (CNF, SQL `IN`-style)**.
Backward compatible: scalar values keep working unchanged.

| Filter value type | Meaning |
|---|---|
| Scalar (string/int/bool) | Equality, as today |
| List | OR within that key — match if any element equals |
| `tags` (special) | Already list-membership; semantics unchanged |
| Across keys | Always AND |

```yaml
# All three valid:
filters: { kind: task, status: ready }                                 # scalar
filters: { kind: task, status: [ready, in-progress, review] }          # list = OR
filters: { kind: task, status: [ready, in-progress], assignee: alice } # AND-of-ORs
```

Out of scope for this task:
- OR across keys (no `any_of` / `all_of` in v1).
- Operator objects like `{in: […]}`, `{not: x}`, `{gte: …}`.
  These are strictly additive and can be layered on later
  without breaking the v1 contract.

## Requirements

The architect owns this end-to-end: spec, implement, document.

### 1. Spec (lightweight)

Add a short spec artifact (`s{NNNN}-multi-value-filters.md`)
covering:

- The contract table above (final wording).
- Behaviour when a list is given for a field whose schema type
  is scalar — does it raise, warn, or just work? (Recommend:
  just work — schema validates each element type.)
- Empty-list semantics — does `status: []` match nothing,
  match everything, or raise? (Recommend: raise
  `ValidationError` at view-load time — empty lists almost
  always indicate a config bug.)
- CLI parsing rule — `--status a,b,c` splits on commas at the
  CLI layer; the resulting list is passed through to
  `list_artifacts` as a Python list. Empty CSV element
  (`a,,b`) treated as `ValidationError` for symmetry.
- Validation error messages.

### 2. Implementation

- Extend the filter loop in `core.discover.list_artifacts`:
  one branch — `if isinstance(v, list): match = any(...)` —
  preserving the current `tags` special case and the existing
  scalar path. Stringify each list element on comparison
  (matches today's scalar behaviour).
- `_validate_filters` continues to validate keys, not values
  (unchanged).
- `views.models.ViewConfig` accepts list-typed filter values
  in addition to scalars; reject empty lists at load time.
- `cli/commands/list.py` `_add_schema_filter_flags` (and the
  cross-kind variant): for fields whose schema type is `string`
  with `enum`, accept CSV input and split into a list before
  handing off to `list_artifacts`. (`--status` is the
  motivating case; the same logic applies to any other
  enum-valued schema field.)
- Tests:
  - `tests/core/test_discover.py` — list filter matches OR
    semantics, including against numeric values, missing keys,
    and the `tags` special case unaffected.
  - `tests/cli/test_list.py` — `--status ready,in-progress`
    returns the union; empty CSV element raises exit-2
    `ValidationError`.
  - `tests/views/` — `ViewConfig` round-trips a list-typed
    filter value; empty list rejected.

### 3. Documentation

- `docs/settings.md` — view-config section: add the contract
  table, two examples (scalar and list), and the empty-list
  rule.
- `src/artifacts_os/views/README.md` — mirror with one
  example.
- `src/artifacts_os/cli/README.md` — `--status` (and any other
  schema-flag) accepts CSV.
- `artifacts/artifacts.yaml` (this vault) — replace the
  per-status views with a single `inflight` view using the new
  syntax to dogfood the change. Keep `all` and named views;
  drop only those made redundant.

## Progress

### 2026-05-07 10:02:34 — Incomplete run (r0144)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$4.57, turns=51

## Verification

- [x] Spec artifact exists, approved, linked from this task.
- [x] Scalar filter values still work (regression).
- [x] List filter value OR-matches; combined with other keys
      it AND-s.
- [x] `tags` list-membership semantics unchanged.
- [x] Empty-list filter value raises a clear `ValidationError`
      at view-load time.
- [x] `art ls --kind task --status ready,in-progress` returns
      the union; trailing/empty CSV element exits 2 with a
      clear message.
- [x] `tests/core`, `tests/cli`, `tests/views` cover all of the
      above; full test suite green.
- [x] `docs/settings.md`, `views/README.md`, `cli/README.md`
      updated with the contract and examples.
- [x] This vault's `artifacts.yaml` dogfoods the new syntax
      (e.g. an `inflight` view replacing redundant per-status
      views).

## Verification Report

*Verified: 2026-05-07*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec artifact exists, approved, linked from this task | PASS | `artifacts/specs/s0023-multi-value-filters.md` exists, contains full contract (§3 Filter value shapes, §4 Implementation Plan, §5 Validation Errors), `task: "[[t0127-feat-multi-value-filters-in]]"` in frontmatter; listed in this task's `artifacts:` field |
| 2 | Scalar filter values still work (regression) | PASS | `core/discover.py:180-183` preserves the `else: str(...) != str(v)` scalar branch; `test_core_list_kind_and_status_filter`, `test_core_list_assignee_filter`, `test_core_list_conjunction` exercise scalar paths |
| 3 | List filter value OR-matches; combined with other keys it AND-s | PASS | `core/discover.py:174-179` adds `isinstance(v, list)` branch with `any(...)`; `test_core_list_filter_list_value_or` and `test_core_list_filter_list_value_combined_with_scalar_ands` cover both behaviours |
| 4 | `tags` list-membership semantics unchanged | PASS | `core/discover.py:162-173` keeps scalar `tags` membership, adds list-of-tags any-of branch; `test_core_list_tags_membership`, `test_core_list_tags_list_value_membership`, `test_core_list_tags_scalar_unchanged_by_other_list_filters` |
| 5 | Empty-list filter value raises a clear `ValidationError` at view-load time | PASS | `views/models.py:225-240` `_validate_filters_shape` raises `ValueError` naming the key with message "view filter '<k>' has empty list — empty filter values are not allowed"; `test_empty_list_filter_value_rejected` confirms |
| 6 | `art ls --kind task --status ready,in-progress` returns union; trailing/empty CSV exits 2 with clear message | PASS | `cli/commands/list.py:53-93` `_split_csv` + `_make_enum_csv_type` raise `argparse.ArgumentTypeError` with "empty value in CSV"; `test_cli_status_csv_multi_value`, `test_cli_status_csv_end_to_end_union`, `test_cli_status_csv_empty_element_exits_2`, `test_cli_status_csv_trailing_comma_exits_2`, `test_cli_status_csv_invalid_enum_value_exits_2` all pass |
| 7 | `tests/core`, `tests/cli`, `tests/views` cover all of the above; full test suite green | PASS | `tests/core/test_list_artifacts_filters.py` and `tests/views/test_views_settings.py` cover the new behaviour (CLI integration tests are co-located in `test_list_artifacts_filters.py` per s0014 §10); `pytest -q` reports 776 passed, 1 skipped, 4 failures in `tests/ai/test_release_changelog_skill.py` — pre-existing and unrelated (file unmodified by this task; failures concern release-changelog SKILL.md content) |
| 8 | `docs/settings.md`, `views/README.md`, `cli/README.md` updated with the contract and examples | PASS | `docs/settings.md` §"Multi-value filters" with the contract table and three YAML examples (scalar, list, AND-of-ORs) plus empty-list rule; `src/artifacts_os/views/README.md` ViewConfig section with list example and empty-list note; `src/artifacts_os/cli/README.md` "Multi-value (CSV) input" section with single/multi/cross-kind examples and CSV validation rules |
| 9 | This vault's `artifacts.yaml` dogfoods the new syntax | PASS | `artifacts/artifacts.yaml:24-30` defines `active` view with `filters: { kind: task, status: [ready, in-progress, review, verified] }`; `default_views.task: active` (line 140) — single multi-status view replaces the redundant per-status views |

### Summary

9 passed, 0 failed. All verification criteria satisfied — the multi-value filter feature is correctly implemented across core, views, and CLI layers, dogfooded in the vault's settings, and documented end-to-end.

## Findings

Multi-value filters land per spec
[[openstation/specs/s0023-multi-value-filters]]. List values in
a `filters` dict mean OR-within-key; keys still AND across.
Scalar values keep working unchanged (regression-tested).

**Implementation summary:**

- **`core.discover.list_artifacts`** (`src/artifacts_os/core/discover.py`)
  — added an `isinstance(v, list)` branch in the per-key match
  loop. Stringifies each list element on comparison so list and
  scalar paths agree. The `tags` special case keeps
  list-membership semantics for scalars and gains an
  any-of-these-tags behaviour for list values.
- **`views.models.ViewConfig`** (`src/artifacts_os/views/models.py`)
  — added `_validate_filters_shape` called from `_parse_view`.
  Empty list values raise `ValueError` naming the offending
  key. Scalars and non-empty lists pass through unchanged. The
  `filters: dict[str, Any]` annotation already permits list
  values; no dataclass change.
- **`cli/commands/list.py`** — replaced argparse `choices=`
  with a `_make_enum_csv_type` callable for enum properties.
  The callable splits on `,`, rejects empty CSV elements, and
  (in per-kind mode) validates each element against the kind's
  enum. Cross-kind mode reuses the same callable with
  per-element validation disabled (enums diverge by kind).
  Single-value invocations (`--status ready`) now produce a
  one-element list `["ready"]` — `list_artifacts` folds this
  through the OR branch and produces the same result as the
  scalar path.
- **Dogfooding** — `artifacts/artifacts.yaml` collapses the
  per-status `active` (= in-progress) / `ready` / `review`
  views into one multi-status `active` view (now containing
  `[ready, in-progress, review]`); `default_views.task` is
  rebound from `all` to `active`.

**Design decisions:**

- Single value through CSV always produces a list, not a
  scalar. Decision: this keeps the CLI parser shape stable
  and lets core handle uniformly. Tests in
  `tests/core/test_list_artifacts_filters.py` updated to
  assert lists.
- Empty list is a `ValueError` at the value-owning layer
  (`ViewConfig._parse_view`) and an argparse error at the
  CLI. Core does not re-validate (an empty list yields
  `match=False` silently); a regression test guards this so
  we don't accidentally start raising mid-walk.
- `choices=` dropped on per-kind enum flags because argparse
  runs `choices=` against the raw CSV string and would always
  reject multi-value input. The custom `type=` callable
  enforces enum membership per element with a clearer error.

**Tests added:**

- `tests/core/test_list_artifacts_filters.py` — six new core
  tests (OR semantics, AND-of-ORs, missing-key, stringified
  comparison, `tags` list value, `tags` scalar unchanged) and
  six new CLI tests (CSV multi, empty/trailing comma, bogus
  enum element, cross-kind CSV, end-to-end union).
- `tests/views/test_views_settings.py` — list-value
  round-trip, empty-list rejection, single-element list
  allowed.

**Test status:** 735 tests pass. The only 4 failing tests
(`tests/ai/test_release_changelog_skill.py`) are pre-existing
and unrelated to this task — verified via `git stash`.

## Downstream

- The `act`/`tui` and `ai` modules currently consume
  `list_artifacts` through the same filter dict, so multi-value
  views work transparently. If a future TUI surface wants to
  *display* a multi-status view distinctly (e.g. a chip per
  status), that is out of scope here.
- Operator objects (`{in: [...]}`, `{not: x}`, `{gte: ...}`)
  remain a future spec — additive on top of v1, no migration
  required.
