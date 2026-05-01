---
kind: spec
id: s0014
name: core-unified-filter-api
status: draft
task: "[[t0053-spec-core-unified-filter-api]]"
created: 2026-05-01
agent: architect
---

# Core: Unified Filter API for `list_artifacts`

Sub-spec of [[s0002-artifacts-os-architecture]]. Finalizes the
contract for unifying frontmatter-equality filter resolution into
`core.list_artifacts` so that views, the CLI, the TUI, and any
programmatic caller share a single filter pipeline.

The current API exposes only `kind` / `status` / `tag` as named
kwargs; every other axis (`assignee`, `type`, `owner`, `priority`,
`agent`) is reachable only through the CLI's post-discovery loop in
[[s0012-cli-list-named-views]] §11.3. This spec defines the unified
filter dict, the resolution algorithm that replaces the per-key
dispatch in `cli/commands/list.py:_apply_view`, and a deprecation
path for the legacy kwargs.

**Scope: design only.** Implementation is filed as a follow-up
task once this spec is approved (see §13).

## 1. Background and Cross-References

- **Task brief** — [[t0053-spec-core-unified-filter-api]] §
  "Today's architecture" enumerates the smell with line-precise
  references to `cli/commands/list.py`. This spec consumes that
  brief verbatim and does not re-litigate motivations.
- **CLI list contract** — [[s0012-cli-list-named-views]] § 4–5
  defines the resolution algorithm that currently lives in the
  CLI. This spec extends it into core — the **per-key merge** rule
  in §5 is preserved; only the *carrier* changes (a single dict
  flowing into core, not a split across native kwargs and
  `_extra_filters`).
- **Views model** — [[s0007-artifacts-os-views-module]] §
  "ViewConfig". `ViewConfig.filters: dict[str, Any]` is the
  source of truth and remains untouched. This spec changes how
  the dict is *consumed*, not how it is parsed or stored.
- **CLI module** — [[s0003-artifacts-os-cli-module]] § "Command
  Set". The new `--filter k=v` flag is appended to the `list`
  subparser; the existing `--status` / `--kind` flags retain
  their surface but are re-plumbed to flow through the same dict.
- **Settings extension** —
  [[s0010-core-settings-module-spec]]. Unaffected — this spec
  changes function signatures only.
- **Reference behavior** — Open Station's `cmd_list` keeps
  `status` / `assignee` / `type` in CLI post-discovery
  (`src/openstation/tasks.py`); this spec deliberately **diverges**
  by consolidating into core, on the rationale that TUI / AI /
  programmatic callers cannot reach the CLI loop and re-implementing
  it everywhere is a smell that compounds.

## 2. Goals and Non-Goals

**Goals:**

- One filter pipeline. `core.list_artifacts` accepts every
  frontmatter-equality predicate that the CLI today routes
  through `_extra_filters`.
- Single merge function. Per-key precedence (CLI flag > view
  filter) lives in **one** place — no per-key `if key == "..."`
  ladder.
- Symmetric reachability. TUI, AI, and programmatic callers get
  the same predicates the CLI gets without copying code.
- Backwards-compatible deprecation. Existing
  `list_artifacts(status=..., tag=...)` callers keep working
  through one minor release with a `DeprecationWarning`.
- Predictable validation. Unknown filter keys fail fast with a
  message that names the offending key.

**Non-goals:**

- New filter operators (negation, set membership, ranges,
  regex). Equality only — same expressiveness `ViewConfig`
  already permits.
- Changes to `ViewConfig` / `ViewsConfig` / `ViewsSettings`
  shapes or to `artifacts.yaml` parsing.
- Changes to the views resolution model defined in
  [[s0012-cli-list-named-views]] § 4–5 — only its CLI-side
  *implementation* changes.
- Cross-kind filter unification across schemas — see §6.3 for
  the limited rule.
- Removing `kind` from the public signature — see §5 for the
  full justification.

## 3. API Signature

```python
def list_artifacts(
    registry: "Registry",
    kind: str | None = None,
    *,
    filters: dict[str, Any] | None = None,
) -> list[ArtifactMeta]: ...
```

| Parameter | Position | Type | Default | Purpose |
|-----------|----------|------|---------|---------|
| `registry` | positional | `Registry` | required | Existing — vault registry |
| `kind`     | positional or kw | `str \| None` | `None` | Directory selection (see §5) |
| `filters`  | **keyword-only** | `dict[str, Any] \| None` | `None` | All frontmatter-equality predicates |

### 3.1 Why `filters` is keyword-only

Three reasons, in priority order:

1. **Future-proof against second positional.** A second positional
   would lock the dict in at position 2, blocking any future
   parameter (e.g. `*, body: bool = False` to read body fields).
   Keyword-only keeps the positional surface to one well-known
   axis.
2. **No accidental confusion with `kind`.** `list_artifacts(reg,
   "task")` reads as kind. `list_artifacts(reg, {"status":
   "ready"})` would silently work as kind if the dict were also
   positional, producing a `ValueError` from `Registry.get`. The
   keyword-only forces `filters={...}`, making intent explicit
   at every call site.
3. **Mirrors `views.ViewConfig.filters`.** The dict shape and
   keyword-only positioning matches how the views layer already
   talks about filters; the call site reads as a literal pass-through
   from `view_cfg.filters`.

### 3.2 Return type unchanged

`list[ArtifactMeta]` — identical to today. No new optional fields.
Filters apply during the directory walk; the CLI post-discovery
pass (`_apply_extra_filters`) is removed (see §8).

### 3.3 Registry stays positional

`registry` is positional and required. Every existing call site
already passes it positionally; promoting to keyword-only is gratuitous
churn that does not improve any property of the API.

## 4. Resolution Algorithm

Triggered by the CLI on every `list` invocation, before the
`list_artifacts` call. Applies equally to programmatic callers
(TUI, AI, scripts) — they construct `filters` directly and call
core; only the **CLI flag merge** (step 3) is CLI-specific.

```python
def resolve_filters(
    args: Namespace,
    view_cfg: ViewConfig | None,
) -> tuple[str | None, dict[str, Any]]:
    # 1. Seed from view config (may be empty).
    filters: dict[str, Any] = dict(view_cfg.filters) if view_cfg else {}

    # 2. Apply CLI flag overrides per-key. Explicit wins.
    if args.kind is not None:
        filters["kind"] = args.kind
    if args.status is not None:
        filters["status"] = args.status
    for key, val in (args.filter or []):           # repeatable --filter k=v
        filters[key] = val                          # explicit wins last

    # 3. Split kind out (directory axis — see §5).
    kind = filters.pop("kind", None)

    return kind, filters
```

The function is **single-pass and key-agnostic**: there is no
`if key == "status" elif key == "kind" else ...` ladder anywhere
in the CLI or core. The only key-aware step is the final
`filters.pop("kind")` — and that step is mandatory regardless of
whether `kind` lives inside or outside the dict (see §5).

### 4.1 Core's responsibilities

Core consumes `(kind, filters)` and:

1. Resolves `kind` to a `KindDef` via `Registry.get(kind)` if
   non-`None`; iterates `Registry.all()` otherwise.
2. Validates `filters` keys against the kind schema (§6).
3. Walks each kind directory, reads frontmatter, applies
   stringified equality (`str(meta.frontmatter.get(k, "")) ==
   str(v)`) for every `(k, v)` in `filters`.
4. Returns matches.

Stringified equality is the **same predicate** the CLI's
`_apply_extra_filters` uses today; no behavior change.

### 4.2 What changes for each caller

| Caller | Today | After |
|--------|-------|-------|
| `cli/commands/list.py` | per-key dispatch in `_apply_view` + post-discovery loop | one `resolve_filters` call + plain core call |
| `cli/commands/verify.py` | `list_artifacts(registry, kind=...)` | unchanged (no filters used) |
| `cli/commands/validate.py` | `list_artifacts(registry, kind=...)` | unchanged |
| `core.discover.children` | internal `list_artifacts(reg, kind=k, status=s)` | `list_artifacts(reg, kind=k, filters={"status": s} if s else None)` |
| TUI / AI (future) | would need to copy `_apply_extra_filters` | call core directly with `filters={...}` |

## 5. `kind` Asymmetry — Justification

`kind` stays a named parameter rather than living inside `filters`
for five concrete reasons. This decision is **load-bearing** — if
any one reason is contested, revisit before implementation.

### 5.1 Directory selection, not equality

`kind` controls **which subtree(s)** the walker opens. With
`kind="task"` only `artifacts/tasks/*.md` is read; with `kind=None`
every kind directory is walked. This is an I/O footprint
decision, not a frontmatter predicate — equality on the `kind`
frontmatter field would still walk every directory and discard
non-matching files. Conflating the two costs a 3–10× discovery
walk on vaults with multiple kinds.

### 5.2 Schema lookup precedes filter validation

To validate that `filters["status"]` is one of the kind's allowed
statuses (§6.1), the validator needs the `KindDef` first. If
`kind` lived inside the dict, the very first line of core would be
`kind = filters.pop("kind", None)` — i.e. the same special-case as
§4 step 3, just hidden inside core instead of explicit at the API
boundary.

### 5.3 Multi-value semantics differ

Were `filters` ever extended to lists (deferred — §2):

- `filters["status"] = ["ready", "in-progress"]` is **set
  membership** on a frontmatter scalar. Cheap.
- `filters["kind"] = ["task", "spec"]` is **directory union** —
  walk N subtrees instead of 1. Different machine entirely.

A unified machine that handles both correctly would force the
first thing inside core to be a kind-aware branch. Pulling `kind`
out at the API boundary keeps each axis with its natural
semantics.

### 5.4 Negation semantics differ

Same shape (deferred operator):

- `filters["status"] = "!done"` skips `done` rows during the
  per-file scan. Bounded by directory size.
- `filters["kind"] = "!task"` walks **every** non-task directory
  — surprising performance footgun. A user typing `--filter
  kind=!task` would expect cheap behavior; reality is N-1
  directory walks.

Keeping `kind` at the signature reminds the caller (and the
implementer) that the kind axis has different cost geometry.

### 5.5 Cross-kind queries — `kind=None`

When `kind is None`, filter keys must be valid across **all**
registered kinds. Schemas diverge per kind (a `task` has `status:
backlog|...`; a `spec` has `status: draft|...`). The validation
rule (§6.3) is "key must exist on at least one kind" rather than
"key must exist on the requested kind", which is the natural
relaxation only because `kind` is hoisted out as a separate
parameter. If `kind` were inside the dict, the validator would
need a flag to distinguish "no kind filter" from "kind is `None`
because directory union", muddling intent.

### 5.6 Non-justifications considered and rejected

- *"It's just consistent."* Consistency for its own sake costs
  the five points above. Asymmetry with a documented rationale is
  better than symmetry with hidden costs.
- *"Callers should be able to write `list_artifacts(reg,
  filters={"kind": "task", "status": "ready"})`."* They can — see
  §4 step 3. The implementation pops `kind` out before the walk;
  the `dict` form is sugar at the boundary, not a different
  internal pipeline. We choose **not** to expose this sugar
  because it leaks the directory-vs-equality asymmetry to every
  reader.

## 6. Validation Behavior

Validation runs **inside core** at the top of `list_artifacts`,
before the directory walk. Goals: typos fail fast, cross-kind
queries stay usable, errors blame the right input.

### 6.1 Known keys

A filter key is **known** for kind `K` if any of:

- It is a built-in `ArtifactMeta` field: `id`, `kind`, `name`,
  `title`, `status`, `tags`, `created`. (`tags` is a list field —
  see §6.5.)
- It appears in the kind schema's `properties` map
  (`artifacts/kinds/<K>.json`).
- It appears in the kind schema's `required` list (subset of
  `properties` in practice, but treated independently for
  forward-compat).

`kind` itself is consumed at the API boundary (§4 step 3) and is
**never** seen as a filter key inside core. Passing `filters={
"kind": "task"}` is permitted for caller convenience and is
folded into the named parameter via the same `pop` step.

### 6.2 Unknown key — hard error

```python
from artifacts_os.core.errors import ValidationError

raise ValidationError(
    f"unknown filter key {k!r} for kind {kind!r}; "
    f"known keys: {sorted(known_keys)}"
)
```

Exit code: `2` (matches existing `ValidationError` cascade in
`cli/__init__.py:_run`). The CLI surfaces the message verbatim on
stderr.

**Decision — hard error, not warning, not silent-no-match:**

- Silent-no-match (today's openstation reference behavior) hides
  typos: `--filter asignee=alice` returns `[]`, looks like
  "alice has no tasks", actually means "you misspelled
  assignee".
- Warning + continue forces every caller (TUI, AI, tests) to
  parse stderr or capture log records. The CLI pipeline's
  programmatic users (tests especially) would silently ignore
  bad keys.
- Hard error costs nothing to recover from (one re-run with a
  fixed key) and surfaces typos at the earliest possible
  point.

### 6.3 Cross-kind queries — `kind is None`

When the caller omits `kind`, a filter key is **known** if it is
known for **at least one** registered kind. Rationale: a query
like `--filter assignee=alice` should work even if not every
kind has an `assignee` field; the per-file walk simply yields
`""` from `frontmatter.get(k, "")` for kinds that lack the key,
and stringified inequality drops them naturally.

```python
def _validate_filters(
    registry: Registry,
    kind: str | None,
    filters: dict[str, Any],
) -> None:
    if not filters:
        return
    if kind is not None:
        known = _known_keys_for_kind(registry, kind)
    else:
        known = set()
        for kd in registry.all():
            known |= _known_keys_for_kind(registry, kd.name)
    for key in filters:
        if key not in known:
            raise ValidationError(...)
```

This is **per-key existence**, not per-key consistency. A query
where two kinds use the same key with different enums (e.g.
`status` on `task` vs `status` on `spec`) is valid: the value
filters whichever kind matches; the other kind drops out via
inequality.

### 6.4 Enum value validation — deferred

Validating that `filters["status"] = "ready"` is one of the kind's
allowed statuses (per `KindDef.statuses`) is **out of scope** for
this spec. Today's `list_artifacts(status="bogus")` returns `[]`
silently; that behavior is preserved. A follow-up task may add
opt-in enum validation; the API surface here is forward-compatible
(the validator is already a single hook in core).

### 6.5 List-valued frontmatter (`tags`)

The current `tag` kwarg uses **membership** (`tag in meta.tags`),
not equality. The unified filter dict preserves this for the
single key `tags` only:

```python
if k == "tags":
    if str(v) not in (meta.frontmatter.get("tags") or []):
        continue
else:
    if str(meta.frontmatter.get(k, "")) != str(v):
        continue
```

All other keys are stringified equality. This keeps
`filters={"tags": "urgent"}` working as the existing
`list_artifacts(tag="urgent")` does. List-typed frontmatter for
other keys (e.g. `assignee` on a multi-assignee kind, hypothetical)
is not supported in v1; pass a single value.

## 7. Precedence Rules

Per-key merge. Wholesale replacement is forbidden. The implementation
is the simple `dict.update`-style overwrite shown in §4 — listed
here as a normative table for the spec.

| Source                              | Wins over                  | Notes |
|-------------------------------------|----------------------------|-------|
| Explicit CLI flag (`--status`, `--kind`, `--filter k=v`) | view filter for the same key | Per-key. Other view keys still apply. |
| `view_cfg.filters[k]`               | nothing — bottom of stack  | Seeded first; overwritten by step 2. |
| `default_views[kind]` view filters  | nothing                    | Same precedence as `--view foo`; binding source is irrelevant once the `ViewConfig` is selected. |

**Wholesale replacement is forbidden.** A view declaring
`filters: {kind: task, status: ready}` and a CLI flag `--status
all` produces `{kind: task, status: all}` — *not* `{status:
all}`. This matches [[s0012-cli-list-named-views]] § 5
"Filters" and is the established mental model.

**Repeated `--filter k=v` for the same key:** last wins (standard
argparse `append` semantics over a final `dict.update`). Document
in the help string for the flag.

## 8. CLI Surface Changes

### 8.1 New flag — `--filter k=v`

```text
artifacts list [--kind KIND] [--status STATUS] [--filter K=V]...
               [--view NAME] [--fields FIELDS] [-q | -j]
```

- **Repeatable** via argparse `action="append"`.
- **Syntax:** `key=value`. Equals sign is the separator. Values
  are not quoted — argparse hands the whole token to us as one
  string.
- **Escaping:** literal `=` in the value is permitted (we
  `split("=", 1)`). Literal `=` in the key is not — keys are
  identifiers in practice.
- **Validation:** missing `=` → `ValidationError("--filter
  expects key=value, got: <token>")`.
- **Help:** `repeatable; e.g. --filter assignee=alice
  --filter type=feature. Last value wins per key.`

### 8.2 `--status` and `--kind` flags retained

No surface change. Internally they are folded into `filters`
in step 2 of §4. The user-facing flags exist because:

- `--kind` selects directory subtree (the asymmetry from §5);
  exposing it as a first-class flag matches its first-class
  internal status.
- `--status` is the most-used filter and benefits from the short
  form `-s`. Removing it would force every existing user to
  rewrite muscle memory for no semantic gain. Keeping it costs
  one line in the parser and zero behavior change.

### 8.3 `_apply_view` rewrite

Replace the per-key dispatch (`cli/commands/list.py:117–129`)
with a single seed:

```python
def _apply_view(args: Any, settings: ViewsSettings | None) -> None:
    args._view_cfg = None
    args._sort = None
    args._filters_seed = {}                # was: args._extra_filters

    # ... view name resolution unchanged (lines 167–190) ...

    if view_cfg is None:
        return

    args._filters_seed = dict(view_cfg.filters)   # whole dict, no per-key copy
    args._sort = view_cfg.sort
    args._view_cfg = view_cfg
```

Then in `run`:

```python
filters = dict(args._filters_seed)
if args.kind is not None:
    filters["kind"] = args.kind
if args.status is not None:
    filters["status"] = args.status
for token in (args.filter or []):
    k, _, v = token.partition("=")
    if not _:                              # missing '='
        raise ValidationError(...)
    filters[k] = v

kind = filters.pop("kind", None)
items = list_artifacts(registry, kind=kind, filters=filters or None)
items = _apply_sort(items, getattr(args, "_sort", None))   # sort still CLI
```

### 8.4 `_apply_extra_filters` removal

The function (`cli/commands/list.py:211–218`) is deleted. Its
behavior moves into core's per-file loop in §4.1 step 3. Tests
referencing `_apply_extra_filters` are rewritten to assert on
`list_artifacts` output (see §10).

### 8.5 Sort stays in CLI

Sorting is **not** moved into core. Rationale: sort is a *view*
concern (lexicographic, missing-last) that depends on the
projection layer; core stays a pure discovery + filter layer.
This matches the boundary set by [[s0012-cli-list-named-views]]
§ 6 and avoids growing core into a query engine.

### 8.6 Backwards compatibility — CLI

Every existing CLI invocation produces identical output:

- `artifacts list --kind task --status ready` — `--kind` and
  `--status` flow into `filters`, `kind` pops out, `status` is
  passed in `filters`. Same files matched.
- `artifacts list --view active` — view's `{kind: task, status:
  in-progress}` flows in via `args._filters_seed`. Same files
  matched.
- `artifacts list --view active --status all` — view seeds,
  `--status` overrides per-key. Same files matched.
- `artifacts list --view developer-queue` — view's `{kind:
  task, assignee: developer}` flows in. The `assignee` key now
  filters in core instead of the post-discovery loop. Same files
  matched, fewer post-walk passes.

## 9. Deprecation Path for Legacy Kwargs

Two kwargs are deprecated: `status` and `tag`.

### 9.1 Alias semantics

```python
def list_artifacts(
    registry,
    kind=None,
    *,
    filters=None,
    status=None,                      # deprecated
    tag=None,                         # deprecated
):
    if status is not None or tag is not None:
        warnings.warn(
            "list_artifacts(status=..., tag=...) is deprecated; "
            "use filters={'status': ..., 'tags': ...} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        filters = dict(filters or {})
        if status is not None:
            filters.setdefault("status", status)
        if tag is not None:
            filters.setdefault("tags", tag)
    # ... validation + walk ...
```

`setdefault` chosen so an explicit `filters={"status": "X"}` and
a redundant `status="Y"` resolve to `"X"` (explicit-dict-wins).
This matches the per-key precedence in §7: callers who reach for
the new API alongside the old should see the new API win.

### 9.2 Warning policy

- Class: `DeprecationWarning` (Python's standard, hidden by
  default but visible under `-W default::DeprecationWarning` and
  in pytest).
- `stacklevel=2` so the warning points at the caller, not at
  core.
- Single warning per caller per legacy kwarg passed (don't
  spam in loops). Implementation: emit unconditionally — Python
  keeps the simple-filter mode-default of "once per location"
  for `DeprecationWarning`, so this is automatic.

### 9.3 Removal timeline

- **v0.N (this spec ships):** kwargs warn, behavior preserved.
- **v0.N+1:** kwargs removed. Calls fail with
  `TypeError: list_artifacts() got an unexpected keyword
  argument 'status'`.
- **No long deprecation window.** Rationale: `artifacts-os` is
  pre-1.0 and the only known external caller is openstation
  itself; one minor cycle is sufficient. If usage broadens
  before removal, revisit.

### 9.4 Internal updates in this spec's PR

The deprecation surface only fires for **third-party** callers.
Internal callers (`children`, tests) are migrated in the same PR:

- `core.discover.children` (`discover.py:274`) — migrate to
  `filters={"status": status}` form.
- `tests/core/test_discover.py:35,43` — migrate calls to
  `filters={...}`. Add a parallel test that asserts the
  deprecation warning fires for the legacy form (see §10.5).

## 10. Test Plan

Tests live in `tests/core/test_discover.py` (core surface) and
`tests/cli/test_list_views.py` (CLI integration). The matrix
below is normative — every row must have a corresponding test.

### 10.1 Core API matrix

| Call | Expected | Notes |
|------|----------|-------|
| `list_artifacts(reg)` | all kinds, no filters | unchanged baseline |
| `list_artifacts(reg, kind="task")` | tasks dir only | unchanged |
| `list_artifacts(reg, kind="task", filters={"status": "ready"})` | tasks with `status: ready` | new shape |
| `list_artifacts(reg, filters={"status": "ready"})` | cross-kind, status=ready | new — replaces today's `status=` |
| `list_artifacts(reg, filters={"assignee": "alice"})` | cross-kind, assignee=alice | new — was CLI-only |
| `list_artifacts(reg, filters={"tags": "urgent"})` | membership in `tags` list | new — replaces `tag=` |
| `list_artifacts(reg, kind="task", filters={"status": "ready", "assignee": "alice"})` | conjunction | both must match |
| `list_artifacts(reg, kind="task", filters={})` | same as `filters=None` | empty dict no-op |
| `list_artifacts(reg, kind="task", filters={"asignee": "alice"})` | `ValidationError` | typo → §6.2 |
| `list_artifacts(reg, filters={"kind": "task"})` | same as `kind="task"` | dict-form sugar |
| `list_artifacts(reg, kind="task", filters={"kind": "spec"})` | `kind="spec"` wins (last) | per §4 step 2/3 |

### 10.2 Deprecated kwarg compat

| Call | Expected | Warning |
|------|----------|---------|
| `list_artifacts(reg, status="ready")` | == `filters={"status": "ready"}` | `DeprecationWarning` |
| `list_artifacts(reg, tag="urgent")` | == `filters={"tags": "urgent"}` | `DeprecationWarning` |
| `list_artifacts(reg, status="ready", filters={"status": "review"})` | `filters={"status": "review"}` wins | `DeprecationWarning` (still emitted) |

Use `pytest.warns(DeprecationWarning, match="list_artifacts")`.

### 10.3 CLI integration matrix

`(view filters) × (CLI flags) → expected effective filter dict
passed to core`. The test fixture stubs `list_artifacts` and
asserts on the exact `(kind, filters)` it received.

| View `filters` | CLI flags | Effective `kind` | Effective `filters` |
|----------------|-----------|------------------|---------------------|
| (none) | `--kind task` | `"task"` | `{}` (or `None`) |
| (none) | `--status ready` | `None` | `{"status": "ready"}` |
| (none) | `--filter assignee=alice` | `None` | `{"assignee": "alice"}` |
| (none) | `--filter assignee=alice --filter type=feature` | `None` | `{"assignee": "alice", "type": "feature"}` |
| (none) | `--filter assignee=alice --filter assignee=bob` | `None` | `{"assignee": "bob"}` (last wins) |
| `{kind: task, status: ready}` | (none) | `"task"` | `{"status": "ready"}` |
| `{kind: task, status: ready}` | `--status all` | `"task"` | `{"status": "all"}` |
| `{kind: task, assignee: alice}` | `--filter assignee=bob` | `"task"` | `{"assignee": "bob"}` |
| `{kind: task, assignee: alice}` | `--kind spec` | `"spec"` | `{"assignee": "alice"}` |
| `{kind: task, status: ready, type: spec}` | `--status all --filter type=feature` | `"task"` | `{"status": "all", "type": "feature"}` |
| `{assignee: alice}` (no kind) | `--kind task` | `"task"` | `{"assignee": "alice"}` |

### 10.4 Validation surface

| Input | Outcome |
|-------|---------|
| `--filter foo` (no `=`) | exit 2, stderr `error: --filter expects key=value, got: foo` |
| `--filter asignee=alice` (typo) | exit 2, stderr `error: unknown filter key 'asignee' for kind 'task'; known keys: [...]` |
| `--filter asignee=alice` without `--kind` | exit 2, stderr names cross-kind known keys |
| `--filter status=bogus` (unknown enum value) | exit 0, empty result | preserves §6.4 |

### 10.5 Migration coverage

- Update `tests/core/test_discover.py:35` (`status="ready"`) to
  `filters={"status": "ready"}`. Keep one parallel test that
  asserts the **deprecation warning** fires for the old form.
- Update `tests/core/test_discover.py:43` (`tag="urgent"`)
  similarly to `filters={"tags": "urgent"}` plus a parallel
  warning assertion.

### 10.6 Fixtures

- Reuse `tests/cli/conftest.py:vault` and `write_artifact`.
- Reuse `make_artifacts_yaml` from
  [[s0012-cli-list-named-views]] § 11.4 (already shipping).
- Add a `stub_list_artifacts` fixture that replaces
  `list_artifacts` with a `MagicMock` capturing `(kind,
  filters)` for the integration matrix.

## 11. Migration Impact

### 11.1 Call sites of `list_artifacts(status=...)` / `tag=...`

Comprehensive list — every call site is touched by this spec's
follow-up implementation task:

| File | Line | Current | Migration |
|------|------|---------|-----------|
| `src/artifacts_os/core/discover.py` | 274 | `list_artifacts(registry, kind=kind, status=status)` (inside `children`) | `list_artifacts(registry, kind=kind, filters={"status": status} if status else None)` |
| `src/artifacts_os/cli/commands/list.py` | 57 | `list_artifacts(registry, kind=..., status=...)` | unified `list_artifacts(registry, kind=kind, filters=filters)` per §8.3 |
| `src/artifacts_os/cli/commands/verify.py` | 65 | `list_artifacts(registry, kind=...)` | unchanged |
| `src/artifacts_os/cli/commands/validate.py` | 33 | `list_artifacts(registry, kind=...)` | unchanged |
| `tests/core/test_discover.py` | 12, 23, 35, 43 | mix of `kind=`, `status=`, `tag=` | migrate `status=` and `tag=` to `filters=`; keep one parallel deprecation test each |

No external (third-party) call sites are known. If openstation
or downstream tooling consumes `list_artifacts` directly, they
get the deprecation warning per §9 and one minor cycle to
migrate.

### 11.2 Affected modules

- `core` — `discover.py` (signature, validation, deprecation
  shim, internal `children` migration).
- `cli` — `commands/list.py` (`_apply_view` rewrite,
  `_apply_extra_filters` removal, `--filter` flag, run path).
- `views` — **not affected.** `ViewConfig.filters` shape
  unchanged; only the consumer changes.
- `log`, `tui`, `ai` — not affected. Future TUI / AI work that
  needs filters now has a one-line core API to call.
- Tests — `tests/core/test_discover.py`,
  `tests/cli/test_list_views.py`.
- Docs — `core/README.md` (list_artifacts signature),
  `cli/README.md` (`--filter` flag), `docs/architecture.md` if
  it mentions the filter pipeline.

### 11.3 Out-of-tree projects

OpenStation's `cmd_list` (`src/openstation/tasks.py:cmd_list`)
keeps its own post-discovery loop and is **not** rewritten here
— the openstation task vault is a separate concern. The spec's
divergence from the openstation reference is documented in
[[s0012-cli-list-named-views]] § 4 and reaffirmed here: artifacts-os
chooses to consolidate into core; openstation may follow in its
own time.

## 12. Open Questions — Resolved

| Question | Resolution | Rationale |
|----------|-----------|-----------|
| `filters` keyword-only? | Yes. | §3.1 — future-proofs second positional, prevents kind/dict confusion, mirrors `ViewConfig.filters`. |
| `kind` inside or outside `filters`? | Outside. | §5 — directory selection, schema lookup order, multi-value/negation cost, cross-kind semantics. |
| Unknown key behavior? | Hard error (`ValidationError`, exit 2). | §6.2 — typos must fail loud; warning + continue forces every caller to parse stderr. |
| Cross-kind filter validation? | Per-key existence across union of registered kinds. | §6.3 — natural relaxation, only because `kind` is hoisted out. |
| Enum value validation (`status: bogus`)? | **Deferred.** Empty result preserves today's behavior. | §6.4 — orthogonal feature; API is forward-compatible. |
| `tag` membership semantics? | Preserved as `filters["tags"]` membership-on-list. | §6.5 — only special-cased key; equality everywhere else. |
| Deprecation window for `status=` / `tag=`? | One minor release. | §9.3 — pre-1.0, sole external consumer is openstation. |
| `--filter k=v` repeatable? | Yes; last wins per key. | §8.1 — standard argparse `append` semantics + final `dict.update`. |
| Move sort into core? | **No.** Sort stays in CLI. | §8.5 — view concern, not discovery. |
| Cross-kind enum validation? | **Deferred** alongside §6.4. | Same forward-compat path. |

## 13. Implementation Outline (for follow-up task)

Filed as a follow-up task once this spec is approved. Outline
below is normative — the implementing developer must touch each
item.

1. `src/artifacts_os/core/discover.py`
   - New signature: `list_artifacts(registry, kind=None, *,
     filters=None, status=None, tag=None)`.
   - `_validate_filters` helper (§6.3).
   - Deprecation shim (§9.1) folding `status` / `tag` into
     `filters` with `DeprecationWarning`.
   - `tags` membership branch in the per-file loop (§6.5).
   - `children()` updated to use `filters={"status": status}`
     internally (§11.1).
2. `src/artifacts_os/cli/commands/list.py`
   - `--filter` flag (§8.1) on the parser.
   - `_apply_view` rewrite (§8.3) — single seed, no per-key
     dispatch.
   - `_apply_extra_filters` deletion (§8.4).
   - `run()` rewritten to compose `(kind, filters)` per §4 and
     §8.3.
3. `tests/core/test_discover.py` — migrate per §10.5; add the
   matrix in §10.1 + §10.2.
4. `tests/cli/test_list_views.py` — extend with §10.3 + §10.4.
5. Docs:
   - `src/artifacts_os/core/README.md` — update
     `list_artifacts` row in the discovery table; note `filters=`
     and the deprecation.
   - `src/artifacts_os/cli/README.md` — document `--filter`
     under `list`.
   - `docs/architecture.md` — update the filter-pipeline
     description if present.
6. Verify openstation's `--no-pager` and its own list path are
   unaffected (different command, different code path; smoke
   test only).

The follow-up task is **single-agent, single-PR sized** — all
changes are mechanical given this spec. No further design work
is required.

## 14. Verification

The parent task [[t0053-spec-core-unified-filter-api]] inherits:

- [ ] Spec file committed under `artifacts/specs/` as
      `s0014-core-unified-filter-api.md`.
- [ ] Covers all 10 task requirements (§3, §4, §7, §5, §6, §9,
      §8, §11, §10, §1).
- [ ] Cross-links [[s0007-artifacts-os-views-module]] (§1) and
      [[s0012-cli-list-named-views]] (§1, §7, §10).
- [ ] Cross-links `core/README.md` migration target (§11.2 +
      §13).
- [ ] Reviewed and approved by user.
- [ ] Follow-up implementation task can be filed against this
      spec without further design work — implementation outline
      §13 lists every file and every test row.

## 15. Decision Log

| Marker | Items |
|--------|-------|
| **Decided** | Signature `list_artifacts(reg, kind=None, *, filters=None)`. Per-key precedence (CLI > view filter). Unknown filter key → `ValidationError` exit 2. Cross-kind validation = per-key existence across union. `tags` membership semantics preserved. `status=` / `tag=` deprecated with one-cycle removal. `--filter k=v` repeatable, last-wins, `=` separator. Sort remains CLI-side. |
| **Recommended** | Single `resolve_filters` helper in CLI rather than scattering merge logic. Stub `list_artifacts` in CLI integration tests via fixture for clean assertions on `(kind, filters)` tuples. |
| **Deferred** | Enum-value validation (e.g. `status=bogus` → error). Negation operator (`!value`). Set-membership (`{key: [a, b]}`). Multi-kind union via `kind=[a, b]`. Sort migration into core. Generator for slash-command shims (already deferred in s0012 §10). |
