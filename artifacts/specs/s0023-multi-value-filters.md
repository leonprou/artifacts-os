---
kind: spec
id: s0023
name: multi-value-filters
status: draft
task: "[[t0127-feat-multi-value-filters-in]]"
created: 2026-05-07
agent: architect
---

# Multi-Value Filters in Views and `--status`

Sub-spec of [[s0014-core-unified-filter-api]]. Extends the unified
filter dict so that a single key can carry **multiple allowed
values** (`status: [ready, in-progress, review]`) without a new
operator vocabulary or any change to the per-key merge precedence.

The motivating use case is the `active` view — "all in-flight
work" — that today requires fanning out one named view per
status. A second motivation is the CLI's `--status` flag, which
accepts a single value and forces users into multiple invocations
or a vault-wide "all" view to dodge the limit.

**Scope: design + implementation.** This spec lands together with
[[t0127-feat-multi-value-filters-in]].

## 1. Background

- `core.discover.list_artifacts` (`src/artifacts_os/core/discover.py`
  L155–L167) compares every `(key, value)` pair as
  `str(meta.frontmatter.get(key, "")) == str(value)`. The `tags`
  key is the only special case (list-membership). Today, a list
  in any other key is silently coerced into its `repr()` and
  never matches.
- `views.models.ViewConfig.filters: dict[str, Any]`
  (`src/artifacts_os/views/models.py` L31) accepts arbitrary
  values; `_parse_view` round-trips the dict verbatim and never
  validates the value type.
- The CLI's per-kind `--status` flag (added by
  `_add_schema_filter_flags` in
  `src/artifacts_os/cli/commands/list.py` L89–L112) registers
  argparse `choices=` from the kind's enum, so a single string
  value is the only currently parseable shape.

## 2. Goals and Non-Goals

**Goals:**

- Express "filter by a set of values for one key" everywhere the
  unified filter dict reaches: `core.list_artifacts`,
  `ViewConfig.filters`, and `--status` (and any other
  enum-string schema-derived flag).
- Backwards-compatible. Scalar values keep working unchanged.
- Predictable validation. Empty lists raise immediately at
  view-load time and at the CLI layer for the symmetric CSV
  case.

**Non-goals:**

- OR across keys. No `any_of` / `all_of` block at the view
  level. Conjunction across keys remains the only cross-key
  composition rule.
- Operator objects (`{in: [...]}`, `{not: x}`, `{gte: ...}`).
  Strictly additive — can be layered on later without breaking
  this v1 contract.
- Negation, regex, ranges. Out of scope; flag for a future spec.

## 3. Contract

### 3.1 Filter value shapes

| Filter value type | Meaning |
|---|---|
| Scalar (`str` / `int` / `bool`) | Equality, as today: `str(meta.frontmatter.get(k, "")) == str(v)`. |
| `list[Any]` | OR within that key — match if **any** element compares equal under the same stringified rule. |
| `tags` (special) | List-membership semantics, **unchanged**. A scalar `tags` filter still means "the meta has this tag". |
| Across keys | Always AND. |

```yaml
filters: { kind: task, status: ready }                                   # scalar
filters: { kind: task, status: [ready, in-progress, review] }            # list = OR within status
filters: { kind: task, status: [ready, in-progress], assignee: alice }   # AND-of-ORs
```

### 3.2 Type interaction

A list filter value applied to a field whose schema declares a
scalar type (string / integer / boolean) **just works** —
each element is stringified and compared per the rule in §3.1.
The schema validates each element's type at `validate` time
(out of scope for this spec); `list_artifacts` never enforces
schema types on filter values.

### 3.3 Empty lists

`status: []` (or any other key with an empty list value) is
**always a config bug**: an empty OR clause matches nothing, so
the only legitimate intent is "match nothing", which is better
expressed by deleting the view. Empty lists therefore raise
`ValidationError` at the layer that owns the value:

| Layer | When the error fires | Message form |
|---|---|---|
| `ViewConfig` (view config in `artifacts.yaml`) | `_parse_view`, at settings load. | `view filter '<key>' has empty list — empty filter values are not allowed (use a scalar or a non-empty list)` |
| CLI (`--status a,,b`, trailing comma `--status a,`) | argument parse, before dispatch. | `--<flag>: empty value in CSV (got '<input>'); use comma-separated non-empty values` |

The core `list_artifacts` API does not re-validate — by
contract, callers handing an empty list are programmer errors,
not user-input errors, and a `ValueError` from the underlying
`any()` would surface them. (Implementation note: an empty list
in core simply yields `match=False` for that key. Tests cover
this so we don't accidentally start raising — but we don't
*encourage* it either; the validation seam is the value-owning
layer above core.)

### 3.4 CLI parsing

`--status` (and any other `string`-typed schema field with an
`enum` declaration) accepts a CSV input:

```bash
art ls --kind task --status ready,in-progress,review
```

The parser splits on `,` and produces a `list[str]`. The
resulting list flows into `resolve_filters` per
[[s0014-core-unified-filter-api]] §5 unchanged: it's a value
in the filter dict, last-write-wins per key.

**Empty CSV elements** (`a,,b`, `,a`, `a,`) are a
`ValidationError` at the CLI layer (exit code `2`, per
`s0015-cli-schema-derived-filter-flags` §6.4 conventions).

**Single value** (`--status ready`) yields a single-element
list `["ready"]`. Core's filter loop folds this through the
`any()` branch and produces the same result as the legacy
scalar path; no special case is required.

**Choices validation** — when the schema declares an enum,
each element of the parsed list must be in `choices`. This is
enforced by a custom argparse `type=` callable (argparse's
built-in `choices=` only checks against the raw argument
string, which would always fail for CSV input). The error
message names the offending element:

```
--status: invalid value 'bogus' (choose from: backlog, ready, in-progress, done)
```

## 4. Implementation Plan

### 4.1 Core — `core.discover.list_artifacts`

Extend the per-key match loop to recognise list values:

```python
for k, v in filters.items():
    if k == "tags":
        if str(v) not in (meta.frontmatter.get("tags") or []):
            match = False
            break
    elif isinstance(v, list):
        meta_val = str(meta.frontmatter.get(k, ""))
        if not any(meta_val == str(elem) for elem in v):
            match = False
            break
    else:
        if str(meta.frontmatter.get(k, "")) != str(v):
            match = False
            break
```

`_validate_filters` is unchanged — it validates keys, not
values.

### 4.2 Views — `views.models.ViewConfig`

`_parse_view` walks each value in `filters`; when a list is
present, it raises `ValueError` if the list is empty. Scalar
values (incl. `bool`, `int`, `str`) and non-empty lists pass
through unchanged. The `ViewConfig.filters` type annotation is
`dict[str, Any]` already — no dataclass change needed.

### 4.3 CLI — `cli/commands/list.py`

`_flag_kwargs_for_prop` adds a CSV-aware `type=` callable for
`enum` properties whose underlying type is `string`. The
callable:

1. Splits on `,`.
2. Raises `argparse.ArgumentTypeError` if any element is empty.
3. Validates each element against the enum; raises if any
   element is not in `choices`.
4. Returns a `list[str]`.

`choices=` is dropped on the per-kind `--status` (and other
enum-string flags) because argparse's `choices` runs against
the raw string and would reject any CSV input. The custom
`type=` callable replaces it as the validation seam.

`metavar` shifts from `"backlog|ready|..."` to
`"backlog|ready|...[,...]"` to communicate the CSV shape.

`_add_union_filter_flags` (cross-kind) keeps its current
no-`choices=` behaviour but uses a simpler CSV splitter
(no enum validation, since per-kind enums diverge across
kinds — caller's responsibility).

### 4.4 Tests

- **`tests/core/test_discover.py`** (or `test_list_artifacts_filters.py`):
  list filter matches OR semantics; combined with another
  scalar key it AND-s; numeric scalar values via list comparison
  (`status: [1, 2]` against `status: 1` in frontmatter — string
  coercion); missing keys never match (no exceptions); the
  `tags` special case is **unaffected** by list-typed values
  for any other key.
- **`tests/cli/test_list_schema_flags.py`** (or
  `test_list_artifacts_filters.py`): `--status ready,in-progress`
  yields the union; trailing/empty CSV element exits 2 with a
  clear message; bogus enum value exits 2 with a clear message;
  single value still works (regression).
- **`tests/views/test_views_settings.py`**: `ViewConfig`
  round-trips a list-typed filter value (parsed equal to source);
  empty list rejected with `ValueError` naming the offending key.

## 5. Validation Errors — Exact Wording

| Layer | Trigger | Message |
|---|---|---|
| `ViewConfig._parse_view` | `filters: { status: [] }` | `view filter 'status' has empty list — empty filter values are not allowed` |
| CLI per-kind `--status` | `--status a,,b` | `argument --status: empty value in CSV (got 'a,,b')` |
| CLI per-kind `--status` | `--status bogus` | `argument --status: invalid value 'bogus' (choose from: backlog, ready, ...)` |

## 6. Migration

The vault's own `artifacts/artifacts.yaml` shipped three
per-status views (`active` = in-progress, `ready`, `review`)
plus `all`. With this spec in place, those collapse into a
single `active` view that carries the OR clause:

```yaml
active:
  columns: id,name,status,assignee
  filters: { kind: task, status: [ready, in-progress, review] }
  sort: id
```

`default_views.task` is rebound from `all` to `active` so
`artifacts list --kind task` shows in-flight work by default.
`all` and named-purpose views (`features`, `developer-queue`,
etc.) stay. The redundant `ready` / `review` views are
removed; the old single-status `active` (= in-progress only)
is replaced by the multi-status one.

## 7. Cross-References

- [[s0014-core-unified-filter-api]] — parent spec; per-key
  precedence and validation surface.
- [[s0015-cli-schema-derived-filter-flags]] — CLI schema flag
  generation rules.
- [[s0007-artifacts-os-views-module]] — `ViewConfig` model.
- [[t0127-feat-multi-value-filters-in]] — implementation task.
