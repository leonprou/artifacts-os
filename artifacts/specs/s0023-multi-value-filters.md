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
work" — which today fans out one named view per status; a second
is the CLI's `--status` flag, single-valued today, which forces
multiple invocations or a vault-wide "all" view to dodge the
limit. Scalar values keep working unchanged; the extension is
strictly additive.

## Out of Scope

- **OR across keys.** No `any_of` / `all_of` block at the view
  level — conjunction across keys remains the only cross-key rule.
- **Operator objects** (`{in: [...]}`, `{not: x}`, `{gte: ...}`).
  Layerable later without breaking this v1 contract.
- **Negation, regex, ranges** — flag for a future spec.
- **Schema type-checking of filter elements** — `list_artifacts`
  never enforces schema types on filter values; `validate` owns
  that.

## Architecture

A list value in any filter key means **OR within that key**;
across keys the rule stays **AND**. Two entry points (the CLI
`--status` flag and a `ViewConfig.filters` block) feed the same
unified filter dict into `core.discover.list_artifacts`, whose
per-key match loop is the single place the OR/AND semantics live.

```
  CLI:  art ls --status ready,in-progress       View:  filters: {status: [ready, review]}
          │  split on ',' + enum-validate                │  _parse_view: reject empty list
          ▼                                              ▼
      ["ready","in-progress"]  ──────────►  filter dict  {kind: task, status: [...] }
                                                          │
                                                          ▼
                                  core.discover.list_artifacts  — per-key match loop
                                    • scalar value → equality, str-coerced  (as today)
                                    • list value   → OR within key (any element ==)
                                    • tags         → membership             (unchanged)
                                    • across keys  → AND
                                                          │
                                                          ▼
                                                  matched artifacts
```

### Invariants

- Backwards-compatible: a scalar value folds through the same
  `any()` branch as a single-element list and yields the identical
  result; no legacy path changes behaviour.
- Empty lists are always a config bug (an empty OR matches
  nothing) and raise at the value-owning layer — never silently in
  core.

## Components

| # | Component | Location | Purpose |
|---|---|---|---|
| C1 | `list_artifacts` match loop | `src/artifacts_os/core/discover.py` L155–L167 | Apply scalar/list/tags/AND semantics per key. |
| C2 | `ViewConfig` parse | `src/artifacts_os/views/models.py` (`_parse_view`) | Reject empty list filter values at settings load. |
| C3 | Schema-derived `--status` flag | `src/artifacts_os/cli/commands/list.py` L89–L112 | Parse CSV input, enum-validate each element. |

### C1 — core match loop

Extend the per-key loop to recognise list values; `tags` keeps its
membership special case, scalars keep equality:

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

`_validate_filters` is unchanged — it validates keys, not values.
An empty list in core simply yields `match=False` for that key;
core does not re-validate (callers handing an empty list are
programmer errors, caught by the layers above), but tests pin this
so it never starts raising.

### C2 — ViewConfig parse

`_parse_view` walks each value in `filters`; when a list is
present and empty, it raises `ValueError`. Scalars (`bool`, `int`,
`str`) and non-empty lists pass through unchanged. The
`filters: dict[str, Any]` annotation already accommodates lists —
no dataclass change.

### C3 — CLI `--status` flag

`_flag_kwargs_for_prop` adds a CSV-aware `type=` callable for
`enum` properties whose underlying type is `string`. It splits on
`,`, raises `argparse.ArgumentTypeError` on any empty element,
validates each element against the enum, and returns a `list[str]`.
`choices=` is dropped on the per-kind enum flags (argparse's
`choices` runs against the raw CSV string and would reject any
multi-value input); the custom `type=` callable becomes the
validation seam. `metavar` shifts from `"backlog|ready|..."` to
`"backlog|ready|...[,...]"`. `_add_union_filter_flags` (cross-kind)
keeps a simpler splitter without enum validation, since per-kind
enums diverge.

## Data Models

The filter dict value type determines the match rule:

| Filter value | Meaning |
|---|---|
| Scalar (`str` / `int` / `bool`) | Equality, as today: `str(meta.get(k,"")) == str(v)`. |
| `list[Any]` | OR within the key — match if **any** element compares equal under the same stringified rule. |
| `tags` key (special) | List-membership, **unchanged**: a scalar `tags` filter means "meta has this tag". |
| Across keys | Always AND. |

```yaml
filters: { kind: task, status: ready }                                   # scalar
filters: { kind: task, status: [ready, in-progress, review] }            # list = OR within status
filters: { kind: task, status: [ready, in-progress], assignee: alice }   # AND-of-ORs
```

A list value against a scalar-typed schema field just works — each
element is stringified and compared. `status: []` (any empty list)
is a config bug and raises at the value-owning layer.

## Surfaces

### CLI — `--status` (and any enum-string schema flag)

```bash
art ls --kind task --status ready,in-progress,review
```

- Splits on `,` → `list[str]`, flowing into `resolve_filters`
  (per [[s0014-core-unified-filter-api]] §5) as a normal filter
  value (last-write-wins per key).
- **Single value** (`--status ready`) → `["ready"]`; folds through
  the same `any()` branch as the legacy scalar path.
- **Empty CSV elements** (`a,,b`, `,a`, `a,`) → exit code `2`
  (per `s0015-cli-schema-derived-filter-flags` §6.4).
- **Enum validation** — each element must be in `choices`,
  enforced by the custom `type=` callable.

Exact error wording:

| Layer | Trigger | Message |
|---|---|---|
| `ViewConfig._parse_view` | `filters: { status: [] }` | `view filter 'status' has empty list — empty filter values are not allowed` |
| CLI `--status` | `--status a,,b` | `argument --status: empty value in CSV (got 'a,,b')` |
| CLI `--status` | `--status bogus` | `argument --status: invalid value 'bogus' (choose from: backlog, ready, ...)` |

## Test Plan

Grouped by the property each test verifies:

- **OR/AND semantics (C1)** — `tests/core/test_discover.py`: list
  filter matches OR; combined with a scalar key AND-s; numeric
  scalar via list (`status: [1, 2]` vs frontmatter `1`, string
  coercion); missing keys never match (no exceptions); the `tags`
  special case is unaffected by list values for other keys.
- **CLI parsing + validation (C3)** —
  `tests/cli/test_list_schema_flags.py`: `--status
  ready,in-progress` yields the union; trailing/empty CSV element
  exits `2` with a clear message; bogus enum value exits `2`;
  single value still works (regression).
- **View config validation (C2)** —
  `tests/views/test_views_settings.py`: `ViewConfig` round-trips a
  list-typed value (parsed equal to source); empty list rejected
  with `ValueError` naming the offending key.

## Migration

The vault's own `artifacts/artifacts.yaml` shipped three
per-status views (`active` = in-progress, `ready`, `review`) plus
`all`. They collapse into a single `active` view carrying the OR
clause:

```yaml
active:
  columns: id,name,status,assignee
  filters: { kind: task, status: [ready, in-progress, review] }
  sort: id
```

`default_views.task` is rebound from `all` to `active` so
`artifacts list --kind task` shows in-flight work by default. `all`
and named-purpose views (`features`, `developer-queue`, etc.) stay;
the redundant `ready` / `review` views are removed; the old
single-status `active` (in-progress only) is replaced by the
multi-status one.

## Cross-References

- [[s0014-core-unified-filter-api]] — parent spec; per-key
  precedence and validation surface.
- [[s0015-cli-schema-derived-filter-flags]] — CLI schema flag
  generation rules.
- [[s0007-artifacts-os-views-module]] — `ViewConfig` model.
- [[t0127-feat-multi-value-filters-in]] — implementation task.
