---
kind: spec
id: s0015
name: cli-schema-derived-filter-flags
status: draft
created: 2026-05-02
agent: architect
task: "[[t0055-spec-cli-schema-derived-filter]]"
---

# CLI: Schema-Derived Filter Flags

Sub-spec of `s0003`. Builds on [[s0014-core-unified-filter-api]] (the
unified `filters=` dict in core) and [[t0054-complete-kind-schemas]]
(filterable axes declared in every kind schema). Designs an
`artifacts list --kind <K> --help` surface that auto-generates a
typed flag per `properties` entry — with enums enforced at parse
time — instead of forcing users into `--filter k=v` strings or
named views for every off-axis query.

Implementation is **out of scope**; a follow-up task will be filed
once this spec is approved.

---

## 1. Background and Cross-References

| Source | Role |
|--------|------|
| [[s0003-artifacts-os-cli-module]] | Parent spec for the `cli` module; this is a sub-spec. |
| [[s0007-artifacts-os-views-module]] | Defines the `ViewConfig.filters` shape that this spec's flags rewrite into. |
| [[s0011-cli-create-kind-aware-help]] | **Direct precedent.** `create` already uses two-phase parsing to derive kind-specific flags from schema. This spec extends the same pattern to `list`. |
| [[s0012-cli-list-named-views]] | Establishes per-key precedence semantics for view + CLI merging. Generated flags compose with view filters under the same rules. |
| [[s0014-core-unified-filter-api]] | **Hard dependency.** Defines `core.list_artifacts(kind, *, filters=dict)` and `--filter k=v`. Schema-derived flags are typed sugar on top of `--filter`. |
| [[t0054-complete-kind-schemas]] | **Hard dependency.** Made `properties` complete enough that flag generation has a useful surface (e.g. `task.assignee`, `task.type`, `task.owner`, `spec.agent`). |
| `artifacts/kinds/*.json` | Source of truth for the generated flag set. |
| `src/artifacts_os/core/registry.py` | `Registry.get(kind).schema` exposes the parsed schema at runtime. |
| `src/artifacts_os/cli/__init__.py:_peek_create_kind_schema` (lines 100–141) | The two-phase parsing template this spec generalises. |
| `src/artifacts_os/cli/commands/create.py:_add_kind_flags` (lines 67–89) | The schema → argparse mapping template this spec re-uses (with list-mode adaptations). |
| Openstation reference (`.openstation/`) | Does **not** auto-generate flags — keeps a hard-coded set. **Divergence is intentional.** Openstation's CLI predates `core.list_artifacts(filters=)`; artifacts-os is the upstream that consolidates. |

### Why this exists (one paragraph)

`artifacts list` ships with two filter flags (`--kind`, `--status`)
plus the catch-all `--filter k=v`. Other axes used by views
(`assignee`, `type`, `owner`, `priority`, `agent`) are reachable
only through `--filter k=v` — typeless, choice-less, and invisible
to `--help`. With the schemas now complete (t0054), every axis a
user might want to filter on is **declared** in the kind contract;
the only thing missing is the projection from schema declaration to
argparse flag. This spec defines that projection.

### Composition diagram

```
artifacts list --kind task --type feature --assignee alice
     │
     ▼
Phase 1: peek argv → resolve kind = "task"
     │
     ▼
Phase 2: build subparser with task-specific flags from
         registry.get("task").schema["properties"]
            --status   (choices = task status enum)
            --priority (choices = task priority enum)
            --assignee (free-form string)
            --owner    (free-form string)
            --type     (choices = task type enum)
     │
     ▼
parse_args → namespace with .type="feature", .assignee="alice"
     │
     ▼
resolve_filters() folds generated flags into the filter dict:
            {"type": "feature", "assignee": "alice"}
     │
     ▼
core.list_artifacts(kind="task", filters={...})
                                  (s0014 §3 contract)
```

---

## 2. Goals and Non-Goals

### Goals

1. Make every filterable schema property reachable via a typed
   flag, with `--help` showing the full per-kind surface.
2. Enforce schema enums at argparse-parse-time, not at core
   walk-time, so typos fail fast with a real argparse error
   message and exit code 2.
3. Preserve the `--filter k=v` escape hatch ([[s0014-core-unified-filter-api]] §8.1)
   verbatim. Generated flags are sugar; the dict path always works.
4. Re-use the two-phase pattern from [[s0011-cli-create-kind-aware-help]];
   no new CLI architecture.
5. Zero breaking change to the existing `artifacts list ...`
   command surface (`--kind`, `--status`, `--view`, `--filter`,
   `--fields`, `-q`, `-j` all keep their behaviour).

### Non-Goals

- **Flag generation for kinds passed via `register_kinds()` only**
  (host-app KindDefs without a vault `*.json` file) is out of scope.
  Vault-loaded schemas are the source. Host-app kinds may still
  use `--filter k=v`.
- **Enum-value validation on the unified filter dict** stays
  deferred (see [[s0014-core-unified-filter-api]] §6.4). When the
  user goes through `--filter status=bogus` they get the same
  silent-no-match behaviour core gives today; the typed flags
  enforce enums *before* reaching that path.
- **Subparser surgery** (`artifacts list task --status ready`).
  Considered and rejected in §3 below.
- **`artifacts show`, `artifacts kinds`, `artifacts validate`** —
  no flag derivation; only `list` filters by frontmatter axes.
- **Implementation.** Spec only.

---

## 3. Generation Strategy

### 3.1 Decision

**Two-pass parsing.** Pre-scan argv for `--kind`, load the kind's
schema, build the `list` subparser with kind-specific flags, then
let argparse parse argv normally.

### 3.2 The three options, scored

| Strategy | Per-kind `--help`? | Per-kind enum at parse time? | Breaking change? | Re-use existing code? | Cross-kind story |
|----------|--------------------|------------------------------|-------------------|------------------------|------------------|
| **Two-pass parse** (chosen) | Yes (after `--kind` is supplied) | Yes | None | Yes — `_peek_create_kind_schema` template | Cross-kind = no `--kind`; falls back to a "generic" parser using the **union** of all properties with **no `choices=`**. Validation deferred to core. |
| Union of all kinds | All flags shown always | No (would need union of enums; `--status review` collides between `task` and `spec` enums) | None | Partial | Trivial — same parser always. |
| Per-kind subparsers (`artifacts list task ...`) | Yes (argparse-native) | Yes | **Yes — every script and doc breaks** | Low — different CLI shape | Needs a separate `artifacts list` (no kind) parser. |

### 3.3 Why two-pass wins

- **Code template already exists.** `_peek_create_kind_schema`
  (`cli/__init__.py:100`) and `_add_kind_flags`
  (`cli/commands/create.py:67`) are 60 lines of code that this
  spec generalises. No new argparse machinery needed.
- **`--kind` stays a first-class flag.** This matches the
  asymmetry argued for in [[s0014-core-unified-filter-api]] §5
  (kind = directory selection, not a filter predicate).
- **Per-kind enums are real enums.** `argparse` raises:
  ```
  artifacts list: error: argument --status: invalid choice:
  'bogus' (choose from 'backlog', 'ready', ...)
  ```
  before the registry is consulted. No silent-no-match.
- **No CLI surface change.** Existing scripts, snippets in
  `docs/`, the dogfood loop in `.openstation/` all keep working.
  Subparsers would mean rewriting all of that.

### 3.4 The argparse footgun, addressed

> "argparse builds the parser **once** with a fixed flag set."

True, but the parser doesn't have to be **the same** parser every
time. `cli/__init__.py:_run` already builds the parser **inside**
`_run` after peeking argv (lines 180–183). The build is per-invocation,
not per-process. Two-pass parsing is just extending that peek
to read `list --kind` instead of (or in addition to) `create --kind`.

### 3.5 Worked argparse examples

The following all work with this design:

```text
$ artifacts list --kind task --help
usage: artifacts list [-h] [--kind KIND] [--status {backlog,ready,...}]
                      [--priority {low,normal,high,urgent}]
                      [--assignee TEXT] [--owner TEXT]
                      [--type {feature,implementation,spec,...}]
                      [--filter K=V] [--children REF] [--parent REF]
                      [--view VIEW] [--fields FIELDS | --meta]
                      [-q | -j]
options:
  --status {backlog,ready,in-progress,review,verified,done,cancelled,rejected}
                        Task lifecycle stage.
  --priority {low,normal,high,urgent}
                        Priority hint. Closed enum: small, stable vocabulary.
  --assignee TEXT       Agent or person assigned to work on this task. ...
  --type {feature,implementation,spec,documentation,research,refactor}
                        Task category. Closed enum: ...

$ artifacts list --kind task --status bogus
artifacts list: error: argument --status: invalid choice: 'bogus'
                (choose from 'backlog', 'ready', 'in-progress', ...)
exit 2

$ artifacts list --kind task --type feature --assignee alice
# → list_artifacts(reg, kind="task", filters={"type": "feature", "assignee": "alice"})

$ artifacts list --help                                   # no --kind
usage: artifacts list [-h] [--kind KIND] [--status STATUS]
                      [--priority PRIORITY] [--assignee TEXT]
                      [--type TYPE] [--owner TEXT] [--agent TEXT]
                      [--filter K=V] ...
# Cross-kind (generic) help — union of properties, no `choices=`.
```

---

## 4. Property → Flag Mapping

For each `(field, prop)` pair in `schema["properties"]`, the
generator emits exactly one `add_argument` call. The mapping is a
direct lift from `cli/commands/create.py:_add_kind_flags` (with
list-side adjustments — no `action="append"` for filters).

### 4.1 Mapping table

| Schema shape | Argparse signature | `metavar` |
|--------------|--------------------|-----------|
| `enum: [...]` (any `type`) | `add_argument(flag, dest=field, choices=enum, metavar="\|".join(map(str,enum)), help=desc)` | `\|`-joined enum values |
| `type: "string"` (no enum) | `add_argument(flag, dest=field, type=str, metavar="TEXT", help=desc)` | `TEXT` |
| `type: "integer"` | `add_argument(flag, dest=field, type=int, metavar="INT", help=desc)` | `INT` |
| `type: "boolean"` | `add_argument(flag, dest=field, type=_parse_bool, metavar="BOOL", help=desc)` | `BOOL` |
| `type: "array"` / has `items` | **Skipped in v1** — see §4.5 | n/a |
| `type` absent, `enum` absent | Skipped (would emit a flag with no value semantics) | n/a |

`_parse_bool` is a helper that accepts `true|false|1|0|yes|no`
case-insensitively and raises `argparse.ArgumentTypeError`
otherwise. (Argparse's `type=bool` is the well-known bug — it
returns `True` for any non-empty string.)

### 4.2 Flag naming

- Schema field `foo_bar` → CLI flag `--foo-bar`
  (underscore → hyphen, mirrors `create.py` precedent).
- argparse `dest` = field name **with underscores preserved**
  (so `args.foo_bar` is the access path). This matches argparse's
  default `dest` derivation; we set it explicitly for clarity.

### 4.3 No short flags

Schema-derived flags do **not** get short `-x` forms. Reasons:

- Short forms collide easily across kinds (e.g. `-t` could be
  `--type` or `--tag`).
- Short forms are reserved for the static surface (`-k`, `-s`,
  `-V`, `-f`, `-q`, `-j`). Adding more would crowd the namespace.
- `--help` already lists the long forms; users discover them
  the same way.

`--kind` keeps `-k`, `--status` keeps `-s` — see §7.

### 4.4 Default values

Generated flags have `default=None`. Sentinel value used by
`resolve_filters()` to distinguish "not passed" from "passed
empty string" (which would be a literal filter on `""`, useful
for "field is unset" queries someday).

```python
# In resolve_filters (extension to s0014 §8.3 logic):
for field in args._generated_filter_fields:
    val = getattr(args, field, None)
    if val is not None:
        filters[field] = val
```

### 4.5 List-typed properties — deferred

Some kinds may eventually declare list-typed frontmatter
(`tags`, `depends_on`). Today's filter contract
([[s0014-core-unified-filter-api]] §6.5) supports the **single**
key `tags` via membership. Schema-derived flag generation for
list types is deferred:

- Membership semantics differ from equality (the rest of the
  generated flags do equality).
- `action="append"` would imply "filter on multi-value", but
  core today does single-value membership only.

In v1, list-typed properties are silently skipped during flag
generation. A future spec may add `--tag <value>` or similar; for
now, list-typed filters use `--filter tags=urgent`.

### 4.6 Help text

Argparse `help` text comes verbatim from `prop["description"]`.
If `description` is missing, fall back to `f"filter by {field}"`.
This matches `create.py:80`'s policy.

`prop["title"]` is *not* used (argparse has no analogue; the help
column already wraps long descriptions). If a schema author
wants both, the description wins.

---

## 5. Enum Validation

### 5.1 Per-kind mode (when `--kind <K>` is supplied)

Argparse `choices=` does the work. A bad value:

```text
$ artifacts list --kind task --status superseded
artifacts list: error: argument --status: invalid choice:
                'superseded' (choose from 'backlog', 'ready', ...)
exit 2
```

This is **earlier and louder** than core's silent-no-match for
unrecognised statuses (preserved in [[s0014-core-unified-filter-api]] §6.4).

### 5.2 Cross-kind mode (no `--kind`)

When `--kind` is absent, the generator produces a **generic**
parser:

- Every property name across **all** registered vault kinds
  contributes a flag.
- **No `choices=`** is set, even on `enum` properties — because
  the same property name can have different enums per kind
  (e.g. `task.status` vs `spec.status`), and `choices=` cannot
  represent the per-kind disjunction.
- Help text for an enum field in cross-kind mode is suffixed
  with `" (varies by kind — pass --kind for choices)"`.

This matches [[s0014-core-unified-filter-api]] §6.3 (per-key
existence is the cross-kind validation rule; per-value validation
is deferred). It is also consistent with argparse's reality: a
single `--status` flag with `choices=union(all_status_enums)`
would *over-accept* (e.g. allow `--status superseded` for `task`
even though `task.status` doesn't list it) and *under-document*
(showing the union to a user who really wants per-kind choices).

### 5.3 The `--status` collision case (worked example)

| `--kind` | Generator output for `--status` | Runtime behaviour for `--status review` |
|----------|-------------------------------|-----------------------------------------|
| `task` | `choices=["backlog","ready","in-progress","review","verified","done","cancelled","rejected"]` | Accepted; `filters={"status":"review"}` → matches review-status tasks. |
| `spec` | `choices=["draft","review","approved","deprecated"]` | Accepted; matches review-status specs. |
| (omitted) | No `choices=`; `metavar=STATUS` | Accepted; cross-kind walk; only files where `status == "review"` survive (works for both task and spec). |
| `task` (with `--status superseded`) | argparse error (not in `choices`) | exit 2 before core. |
| (omitted, with `--status superseded`) | accepted at parse time (no choices) | core walks; no file matches; empty result. **Documented limitation, not a bug.** |

---

## 6. Conflict Handling

Two distinct kinds of conflict to resolve.

### 6.1 Schema property vs static-flag name

Schema fields whose generated flag name would collide with a
flag the static `list` parser already registered are **silently
skipped** during generation. Kept-for-skip list:

```python
_RESERVED_FLAG_NAMES = frozenset({
    "help", "kind", "filter", "view", "fields", "meta",
    "quiet", "json", "children", "parent",
})
```

(Mirrors `cli/commands/create.py:_RESERVED_FLAGS` policy.)

If a future schema declares `properties.view` or `properties.fields`,
the field stays reachable via `--filter view=foo`. The skip is
silent because surfacing a warning would interrupt every
`artifacts list --help` invocation; argparse will not double-register
silently — it raises `argparse.ArgumentError` — so the skip is
required for correctness, not just cosmetics.

### 6.2 Same property name, different shapes across kinds (cross-kind mode)

When `--kind` is absent and two kinds declare the same property
with different shapes (e.g. `task.status` enum vs `spec.status`
enum, or hypothetical `kindA.priority` enum vs `kindB.priority`
free-form), the generator picks the **most permissive shape**
deterministically:

| Combination | Generator picks |
|-------------|-----------------|
| All kinds declare an `enum` | No `choices=` (per §5.2 — union is misleading). `metavar=VARIES`. |
| Mixed: some `enum`, some free-form | No `choices=`. `metavar=VARIES`. |
| All free-form `string` | `type=str, metavar=TEXT`. |
| Mixed types (string vs integer) | `type=str, metavar=VARIES` (everything strings cleanly). |

Help text in cross-kind mode is the **first** kind's
`description`, suffixed with `" (varies by kind — pass --kind for
per-kind details)"` if the description differs across kinds.

### 6.3 Property-name conflict with `--status` and `--kind` static flags

`--status` and `--kind` are kept as **first-class flags** in the
static parser — for ergonomics (`-s` short form, `--kind` directs
the schema lookup). When the schema declares `properties.status`
(every shipped kind does), the generator **does not re-add**
`--status`; instead, in **per-kind mode**, the generator
**augments** the existing `--status` add_argument with the kind's
`choices=`, by removing it from the static set first and re-adding
inside Phase 2.

Mechanically:

```python
# Phase 2 in cli/commands/list.py:register():
def register(subparsers, kind=None, schema=None):
    p = subparsers.add_parser("list", ...)
    p.add_argument("--kind", "-k", ...)
    # NOTE: --status is NOT added here unconditionally — see below.
    ...
    if schema is not None:
        _add_schema_filter_flags(p, schema)        # adds --status with choices
    else:
        p.add_argument("--status", "-s", ...)      # static fallback
```

`_add_schema_filter_flags` is responsible for adding `--status`
with `choices=` from the schema, *and* `--priority`, `--type`,
etc. The static `--status` is the cross-kind fallback. This
preserves the `-s` short form in both modes (the schema-augmented
version sets `"-s"` too).

This is the only static-flag exception. All other generated
flags follow §6.1 (skip if name collides).

---

## 7. Lifecycle and Load Order

### 7.1 Phase 1 — peek

Generalise `_peek_create_kind_schema` (`cli/__init__.py:100–141`)
into a shared helper:

```python
# cli/__init__.py
def _peek_kind_for_command(
    argv: list[str],
    command: str,                # "create" or "list"
    cli_settings,
    root,
    *,
    fallback_kind: str | None = None,
) -> tuple[str | None, dict | None]:
    """Pre-parse argv for --kind and load the matching schema.

    Returns (kind, schema). schema is None when:
      - argv[0] != command (caller skips Phase 2 build)
      - --kind is absent and no fallback applies (cross-kind mode)
      - the resolved kind has no vault schema (host-app kind)
    """
```

The existing `_peek_create_kind_schema` becomes a thin wrapper
(default `fallback_kind="task"`, fallback chain reads
`cli_settings.defaults.create.kind`). A new
`_peek_list_kind_schema` wraps with `fallback_kind=None` and no
`cli_settings` defaults consulted.

**Why list has no `cli_settings` default:** users routinely run
`artifacts list` without `--kind` to see everything; defaulting
to a kind would break that ergonomic. Cross-kind mode is a
first-class case.

### 7.2 Phase 2 — build

`cli/__init__.py:_build_parser` already accepts `create_kind` and
`create_schema`. Extend its signature:

```python
def _build_parser(
    create_kind: str | None = None,
    create_schema: dict | None = None,
    list_kind: str | None = None,
    list_schema: dict | None = None,
    list_all_schemas: dict[str, dict] | None = None,   # cross-kind mode
):
    ...
    _list_cmd.register(
        subparsers,
        kind=list_kind,
        schema=list_schema,
        all_schemas=list_all_schemas,
    )
    ...
```

`list_all_schemas` is the union of `{kind_name: schema}` from the
vault, used by `_list_cmd.register` in cross-kind mode (§5.2,
§6.2).

### 7.3 Registry must be loaded before parser construction — no, schemas must be

[[t0055]]'s context flagged "registry must be loaded before parser
construction." That is **not exactly right**: the parser only
needs the **schema files**, not a constructed `Registry`. Schema
files live in `<root>/artifacts/kinds/*.json` and are loaded
directly from disk in Phase 1 (today's `_peek_create_kind_schema`
already does this without a Registry — `cli/__init__.py:131–141`).

The order in `_run` becomes:

1. Find vault `root` (`find_vault_root`).
2. Load `cli_settings` (`_load_cli_settings(root)`).
3. Apply argv aliases.
4. **Peek `create` argv** for `--kind` and load that schema.
5. **Peek `list` argv** for `--kind` and load that schema; if
   absent, load **all** vault schemas for cross-kind mode.
6. `_build_parser(create_kind=..., list_kind=..., list_schema=...,
   list_all_schemas=...)`.
7. `parser.parse_args(argv)`.
8. Construct `Registry` (`Registry(_registered_kinds, root=root)`).
9. Dispatch `args.func(args, registry)`.

Steps 4–5 are independent peeks; either may produce `(None, None)`
for non-matching commands. Step 6 builds the parser once.

### 7.4 Where the code lives

| File | Change |
|------|--------|
| `cli/__init__.py` | Generalise `_peek_create_kind_schema` → `_peek_kind_for_command`; add `_peek_list_kind_schema`; load all schemas when `list_kind is None`; thread through `_build_parser`. |
| `cli/commands/list.py` | Extend `register(subparsers, kind=None, schema=None, all_schemas=None)`; new helper `_add_schema_filter_flags(p, schema)`; new helper `_add_union_filter_flags(p, all_schemas)`; extend `resolve_filters` to fold generated-flag values into the dict (one new loop, see §8.1). |
| `cli/commands/create.py` | No change — `_add_kind_flags` stays kind-aware for create. (Optional refactor: extract a shared `_add_schema_flags` utility into `cli/_schema_flags.py`. Recommended for follow-up but not blocking.) |

---

## 8. Composition with [[s0014-core-unified-filter-api]]

### 8.1 Call trace

Generated flags compose with the existing seed-then-overwrite
algorithm in `resolve_filters`. The ordering is:

```python
# cli/commands/list.py:resolve_filters() — extended.
def resolve_filters(args, view_cfg):
    # 1. Seed from view config.
    filters = dict(view_cfg.filters) if view_cfg else {}

    # 2. Static convenience flags overwrite per-key.
    if args.kind   is not None: filters["kind"]   = args.kind
    if args.status is not None: filters["status"] = args.status

    # 3. NEW: Schema-derived flags overwrite per-key.
    for field in getattr(args, "_generated_filter_fields", ()):
        val = getattr(args, field, None)
        if val is not None:
            filters[field] = val

    # 4. --filter k=v tokens overwrite per-key, last wins.
    for token in (getattr(args, "filter", None) or []):
        if "=" not in token:
            raise ValidationError(...)
        k, _, v = token.partition("=")
        filters[k] = v

    # 5. Pop kind out (directory axis).
    kind = filters.pop("kind", None)
    return kind, filters
```

`args._generated_filter_fields` is populated by
`_add_schema_filter_flags` / `_add_union_filter_flags` in Phase 2.

### 8.2 Precedence — confirmed

The full precedence chain (low → high):

1. View config (`view_cfg.filters`)
2. Static `--kind` / `--status` flags
3. **Schema-derived flags** (`--type`, `--priority`, `--assignee`, ...)
4. `--filter k=v` tokens (last token wins per key)

Steps 2 and 3 sit at the same logical level — both are typed
flags — so their order would only matter if a key were registered
twice (e.g. `--status` static + `--status` from schema). Per §6.3,
the schema-augmented `--status` *replaces* the static `--status`
in per-kind mode; there is no double-register, and the logical
ordering above is consistent.

`--filter` last-wins is the documented escape hatch — explicitly
ordered above schema flags so `--filter status=anything` always
wins, even over `--status`. This matches §10.

### 8.3 Single source of truth for the generator

The generator operates on **schemas**, not on `KindDef` /
`registry.statuses`:

- `KindDef.statuses` is a derived list (extracted from the
  schema in `Registry._load_vault_kinds`); using the schema
  directly avoids a layering shortcut.
- The generator already has the schema in hand from Phase 1.
- Future enums on non-`status` fields (e.g. `priority`) live
  only in `properties[field]["enum"]`, never in `KindDef`.

---

## 9. Rollback / Opt-Out

### 9.1 The `--filter k=v` escape hatch

Always available, always wins. Users who hit a generator
limitation (see §9.3) drop down to:

```text
artifacts list --kind task --filter priority=high
artifacts list --filter agent=architect
artifacts list --filter status=review --filter type=spec
```

The `--filter` flag is documented in `--help` as the
"universal frontmatter equality predicate" — schema-derived
flags are sugar; this is the contract.

### 9.2 Disabling generation per-invocation

Users who want **only** the universal `--filter` surface (for
scripting, or to avoid argparse's `choices=` behaviour) can pass
`--no-schema-flags` (proposed):

```text
artifacts list --kind task --no-schema-flags --filter status=bogus
# → no choices= validation; goes straight to core.
```

**Decision: not in v1.** Reasoning:

- The escape hatch is `--filter` itself; an explicit toggle
  duplicates it.
- argparse `choices=` errors are short and clear; users who
  hit them can re-run with `--filter` after one error message.
- Adds parser complexity for a marginal use case.

The `--no-schema-flags` flag is **not** part of this spec. If a
real need surfaces, file a follow-up; the feature is forward-compatible.

### 9.3 Disabling generation per-installation

A vault may add to `artifacts.yaml`:

```yaml
cli:
  list:
    schema_filter_flags: false        # default: true
```

When `false`, Phase 2 builds the static list parser only
(`--kind`, `--status`, `--filter`, ...). All filter axes go
through `--filter k=v`.

**Decision: also not in v1.** Same reasoning as §9.2 — adds
parser-config surface for a hypothetical user. Document the
escape hatch as `--filter`; revisit if real users complain.

### 9.4 Static-flag conflict — automatic fallback

When a schema declares a property whose generated flag would
collide with a static flag (per §6.1's `_RESERVED_FLAG_NAMES`),
the generator silently skips it. The field remains reachable
via `--filter k=v`. This is the **automatic** rollback — no
flag, no dispatch, but `--filter` always works. The reserved
list itself is the rollback contract.

### 9.5 Unknown kind (Phase 1 schema = None)

When `--kind <unknown>` is passed:

- Phase 1 returns `(unknown, None)` (no schema file).
- Phase 2 builds the static `list` parser (no `_add_schema_filter_flags`).
- argparse parses the rest of argv against the static surface.
- `run()` calls `list_artifacts(kind="<unknown>", ...)`; core
  walks the directory `artifacts/<unknown>/` (which doesn't
  exist) and returns `[]`.

This matches the existing `create` command's unknown-kind
behaviour (s0011 §6).

---

## 10. Test Plan

Tests live in `tests/cli/test_list_schema_flags.py` (new file).
The matrix below is normative — every row → at least one test.

### 10.1 Per-kind flag generation

| Test ID | Setup | Assertion |
|---------|-------|-----------|
| L1 | vault has `task.json` with `properties: {status, priority, assignee, owner, type}`; run `artifacts list --kind task --help` | stdout includes `--status {backlog,...}`, `--priority {low,...}`, `--assignee TEXT`, `--owner TEXT`, `--type {feature,...}` |
| L2 | as L1; run `artifacts list --kind task --status ready` | `list_artifacts(kind="task", filters={"status": "ready"})` |
| L3 | as L1; run `artifacts list --kind task --type feature` | filters include `{"type": "feature"}` |
| L4 | as L1; run `artifacts list --kind task --status bogus` | exit 2; stderr includes `invalid choice: 'bogus'` |
| L5 | as L1; run `artifacts list --kind task --priority urgent --assignee alice` | `filters={"priority": "urgent", "assignee": "alice"}` |
| L6 | minimal task schema with **no** properties; run `artifacts list --kind task --help` | static surface only — no schema-derived flags emitted; argparse does not crash |
| L7 | schema declares `properties.children` (collides with static `--children`); run `artifacts list --kind task --help` | `--children` listed once (the static one); schema field reachable via `--filter children=...` |

### 10.2 Cross-kind (no `--kind`) flag generation

| Test ID | Setup | Assertion |
|---------|-------|-----------|
| L8 | vault has `task.json` + `spec.json` (different `status` enums); run `artifacts list --help` | `--status` shown without `choices=` (metavar `STATUS`); help description includes "varies by kind" |
| L9 | as L8; run `artifacts list --status review` | `list_artifacts(kind=None, filters={"status": "review"})` (cross-kind walk) |
| L10 | as L8; run `artifacts list --status superseded` | parse-time accepted (no `choices=`); core returns `[]` (silent-no-match per s0014 §6.4) |
| L11 | as L8; run `artifacts list --type feature` | `filters={"type": "feature"}` (kinds without `type` drop via inequality, per s0014 §6.5) |
| L12 | as L8 plus `agent.json` with `properties.status: enum` and `note.json` with `properties.type: string` | union: `--status`, `--type`, `--priority`, `--assignee`, `--owner`, `--agent` all listed |

### 10.3 Composition with `--filter` and `--view`

| Test ID | Setup | Assertion |
|---------|-------|-----------|
| L13 | run `artifacts list --kind task --type feature --filter type=spec` | `filters={"type": "spec"}` — `--filter` wins per s0014 §7 |
| L14 | view `developer-queue` declares `filters: {kind: task, assignee: developer}`; run `artifacts list --view developer-queue --assignee alice` | `filters={"assignee": "alice"}` — generated flag overrides view |
| L15 | as L14; run `artifacts list --view developer-queue --type feature` | `filters={"assignee": "developer", "type": "feature"}` — view's assignee preserved, type added |
| L16 | run `artifacts list --kind task --filter assignee=alice` | works as today; `--filter` is unaffected by generation |

### 10.4 Phase 1 / load-order regressions

| Test ID | Setup | Assertion |
|---------|-------|-----------|
| L17 | `--help` with no `--kind` | static + union surface shown; no exception when `artifacts/kinds/` is empty |
| L18 | `--kind notarealkind --help` | static-list `--help` shown (no schema → no augment); no error |
| L19 | `--kind notarealkind --status ready` | `list_artifacts(kind="notarealkind", filters={"status": "ready"})` — runs, returns `[]` |
| L20 | malformed `task.json` (invalid JSON) | Phase 1 swallows exception (per `_peek_create_kind_schema:138` precedent); falls back to static surface |
| L21 | `artifacts list --kind task --filter assignee=alice` from inside a worktree symlinked to a primary vault | resolves via `find_vault_root`; same generated flag set |

### 10.5 Type coercion

| Test ID | Setup | Assertion |
|---------|-------|-----------|
| L22 | hypothetical schema with `properties.weight: {type: "integer"}`; run `--weight 5` | `filters={"weight": 5}` (int, not str). Note: core stringifies on compare per s0014 §6.5; the int passes through as-is. |
| L23 | as L22; run `--weight notanumber` | exit 2; argparse error |
| L24 | hypothetical schema with `properties.archived: {type: "boolean"}`; run `--archived true` / `--archived false` | filters include `{"archived": True}` / `{"archived": False}` |
| L25 | as L24; run `--archived maybe` | exit 2; `_parse_bool` raises |

### 10.6 Help-text propagation

| Test ID | Setup | Assertion |
|---------|-------|-----------|
| L26 | `task.priority.description = "Priority hint. ..."` | `--help` shows `--priority ... Priority hint. ...` |
| L27 | property has no `description` | help text is `filter by <field>` |
| L28 | cross-kind, two kinds disagree on description | first kind's description plus suffix `(varies by kind ...)` |

### 10.7 Existing test suite

All tests in `tests/cli/test_list*.py`, `tests/cli/test_list_views.py`,
`tests/core/test_discover.py` must continue to pass unchanged. The
generator only adds flags; existing invocations
(`--kind/--status/--filter/--view/--fields/-q/-j`) are unchanged.

### 10.8 Fixtures

Re-use the `rich_vault` fixture pattern from
`tests/cli/test_create_kind_aware_help.py:54–69` (writes
`artifacts/kinds/*.json` under `tmp_path`, monkey-patches
`_registered_kinds=[]`, `chdir`s into the vault). A parallel
`tests/cli/conftest.py` helper is acceptable; no fixture
extraction is required for v1.

---

## 11. Migration Impact

### 11.1 Files changed in the implementation PR

| File | Change | Notes |
|------|--------|-------|
| `src/artifacts_os/cli/__init__.py` | Refactor `_peek_create_kind_schema` → `_peek_kind_for_command`; add list-side peek; thread `list_kind`, `list_schema`, `list_all_schemas` into `_build_parser`. | ~30 lines added / 15 changed. |
| `src/artifacts_os/cli/commands/list.py` | Extend `register()` signature; add `_add_schema_filter_flags(p, schema)` and `_add_union_filter_flags(p, all_schemas)`; extend `resolve_filters` to fold `_generated_filter_fields`. | ~80 lines added. |
| `tests/cli/test_list_schema_flags.py` | New file. ~25–30 tests per matrix above. | New. |
| `docs/cli.md` | Document schema-derived flags, generation strategy, the `--help` per-kind behaviour. | New section under `list`. |
| `docs/list-filter.md` | Cross-link this spec from the unified-filter doc. | New page or extension to `core/README.md`. |

### 11.2 No changes to

- `src/artifacts_os/core/*` — core stays exactly as
  [[s0014-core-unified-filter-api]] left it.
- Kind schemas in `artifacts/kinds/*.json` — t0054 finished
  the schema work. This spec consumes; it does not extend.
- `src/artifacts_os/views/*` — view config is unchanged.
- `cli/commands/create.py` — `create` already has its own
  schema-aware flags via Variant B (s0011); this spec does
  not touch them.

### 11.3 Out-of-tree projects

`artifacts-os` is consumed by openstation as a library. Openstation's
own CLI (`bin/openstation`) does **not** call into
`artifacts list` — it uses `core.list_artifacts(filters=...)`
directly via `s0014`. No openstation-side migration is required
for this spec.

If a downstream project wraps `artifacts list` in shell scripts:

- Existing invocations (`artifacts list --kind task --status ready`)
  keep working byte-identically.
- New invocations like `artifacts list --kind task --type feature`
  start working (previously required `--filter type=feature`).
- `--filter k=v` keeps working; that path is the rollback.

---

## 12. Open Questions — Resolved

| Question | Resolution |
|----------|------------|
| Two-pass / union / subparsers? | **Two-pass** (§3). Strongest precedent, no surface change, real argparse enums. |
| `--kind`-less mode: enums or no? | **No `choices=`** in cross-kind mode (§5.2). Per-kind enums conflict; union is misleading. |
| Where do generated flag values get folded into `filters`? | In `resolve_filters`, between static flags and `--filter` (§8.1). |
| What about list-typed properties? | Skipped in v1 (§4.5). `tags` etc. use `--filter`. |
| Per-kind override of `--status`'s static `choices=` — how? | `_add_schema_filter_flags` adds `--status` with `-s` short form and `choices=` from the schema; static `--status` only added when no schema (§6.3). |
| Does the generator need a constructed `Registry`? | No (§7.3). Schemas are loaded directly from `artifacts/kinds/*.json`, same as Phase 1 of `create`. |
| Should `_peek_create_kind_schema` and the new list-side peek share code? | Yes (§7.1) — generalise into `_peek_kind_for_command`. Mechanical refactor, not behavioural. |
| Is there an opt-out flag (`--no-schema-flags`)? | Not in v1 (§9.2). `--filter` is the escape hatch. |
| Is there a vault-level opt-out (`cli.list.schema_filter_flags: false`)? | Not in v1 (§9.3). Revisit when a real user complains. |
| Property-name conflict with reserved flag (e.g. `properties.fields`) | Silent skip (§6.1). Reachable via `--filter`. |
| Property name in cross-kind mode disagrees on type | Pick the most permissive shape (§6.2). Help text suffixed with "varies by kind". |
| Boolean coercion | Custom `_parse_bool` helper (§4.1) — argparse `type=bool` is unusable. |
| Short flags for generated flags? | No (§4.3). Reserved namespace too crowded. |
| Help text source | `prop["description"]`, fallback `f"filter by {field}"` (§4.6). |

---

## 13. Implementation Outline (for follow-up task)

A follow-up implementation task should:

1. Land the refactor of `_peek_create_kind_schema` →
   `_peek_kind_for_command` in `cli/__init__.py` (no behaviour
   change for `create`; covered by existing
   `tests/cli/test_create_kind_aware_help.py`).
2. Add `_peek_list_kind_schema` and the all-schemas loader.
3. Extend `_build_parser` signature; thread args through to
   `_list_cmd.register`.
4. In `cli/commands/list.py`:
   - Add `_RESERVED_FILTER_FLAG_NAMES`.
   - Add `_add_schema_filter_flags(p, schema)` — emits one
     `add_argument` per `properties` entry per §4.1.
   - Add `_add_union_filter_flags(p, all_schemas)` — cross-kind
     mode per §5.2 / §6.2.
   - Extend `register()` to dispatch on `(kind, schema, all_schemas)`.
   - Set `args._generated_filter_fields` (list of dest names) so
     `resolve_filters` knows what to fold in.
   - Extend `resolve_filters` per §8.1.
5. Author tests per §10. Aim for 25–30 tests, all in
   `tests/cli/test_list_schema_flags.py`.
6. Update `docs/cli.md` with the per-kind `--help` behaviour and
   the `--filter` escape-hatch contract.
7. Re-run `pytest`. No tests outside the new file should change.

Estimated effort: 1 day implementation + tests; LOC delta ≈ +180
src, +400 tests.

---

## 14. Verification Checklist (this spec)

- [ ] Spec file committed under `artifacts/specs/`.
- [ ] Covers all 10 task requirements (mapping below).
- [ ] One generation strategy chosen (two-pass, §3).
- [ ] Cross-links [[s0014-core-unified-filter-api]],
      [[t0054-complete-kind-schemas]], [[s0007-artifacts-os-views-module]],
      [[s0012-cli-list-named-views]], [[s0011-cli-create-kind-aware-help]].
- [ ] Reviewed and approved by user.
- [ ] Implementation task can be filed without further design work.

### Requirement coverage map

| Task req | Section |
|----------|---------|
| 1. Generation strategy + justification | §3 (table + worked argparse examples) |
| 2. Property → flag mapping | §4 (table per JSON Schema shape) |
| 3. `description` propagation | §4.6 |
| 4. Enum validation (per-kind + cross-kind) | §5 |
| 5. Conflict handling (reserved names + cross-kind shape conflict) | §6 |
| 6. Lifecycle / load order | §7 (peek → build → parse → registry → dispatch) |
| 7. Composition with t0053 | §8 (call trace + precedence) |
| 8. Rollback / opt-out | §9 |
| 9. Test plan | §10 |
| 10. Cross-link | §1, §11.3, §13 |

---

## 15. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-02 | Two-pass parsing over union or subparsers | Existing precedent (s0011); no breaking change; per-kind argparse enums work. |
| 2026-05-02 | Cross-kind mode emits flags **without** `choices=` | Per-kind enums diverge; union over-accepts and under-documents. |
| 2026-05-02 | Schemas, not `KindDef`, drive generation | Avoids layering shortcut; future enums on non-`status` fields live only in schemas. |
| 2026-05-02 | List-typed properties deferred | Membership semantics differ from equality; covered by `--filter tags=...` for now. |
| 2026-05-02 | No `--no-schema-flags` and no `cli.list.schema_filter_flags` opt-out in v1 | `--filter` is the contractually documented escape hatch; opt-outs duplicate it. |
| 2026-05-02 | `--status` augment, all other static flags untouched | `--status` is the only generated flag that already exists statically; per-kind enrichment without losing the cross-kind fallback. |
| 2026-05-02 | No short flags for generated flags | `-k -s -V -f -q -j` namespace is full; collisions across kinds make short forms unsafe. |
| 2026-05-02 | Custom `_parse_bool` for boolean schema fields | Argparse `type=bool` is famously broken; explicit helper is the standard workaround. |
