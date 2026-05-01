---
kind: spec
id: s0013
name: programmatic-cli-access
status: draft
created: 2026-05-01
agent: architect
task: "[[t0051-spec-programmatic-cli-access-frontmatter]]"
---

# CLI: Programmatic Access — Frontmatter & Relationships

Sub-spec of [[s0003-artifacts-os-cli-module]]. Specifies the v1
contract for three composable surfaces on `artifacts show` and
`artifacts list`:

- `--meta` (both commands) — frontmatter-only projection.
- `list --children <ref>` — direct children of `<ref>`.
- `show <ref> --parent` — direct parent of `<ref>`.

Together these turn the CLI into a structured data interface that AI
agents and other modules can pipe through `jq`. The data primitive
(graph traversal, frontmatter projection) is reusable by [[n0002-layouts-tree-view-scoping]]'s
tree-view layout work without further abstraction.

## 1. Background and Cross-References

- **Primary input** — [[n0003-programmatic-cli-access]]. Mental
  model, layered flag model, composition matrix, and rejected flag
  shapes are all sourced from there. **This spec converts those
  decisions into a normative contract** — it does not re-litigate
  them.
- **Sibling effort** — [[n0002-layouts-tree-view-scoping]]. The
  tree-view layout consumes the graph-traversal primitive defined
  in §6 below.
- **Named views** — [[s0012-cli-list-named-views]]. Composes with
  this surface; precedence rules in §5.
- **Views data model** — [[s0007-artifacts-os-views-module]]. No
  changes to `ViewConfig` / `ViewsConfig` / `ViewsSettings`.
- **Parent CLI spec** — [[s0003-artifacts-os-cli-module]]. The new
  flags are added under the existing `show` and `list` synopses.
- **Settings infrastructure** — [[s0010-core-settings-module-spec]].

## 2. Goals and Non-Goals

**Goals:**

- AI agents (and other modules) can fetch any artifact's
  frontmatter as a structured dict — `show <ref> --meta -j`.
- The same agents can fetch many artifacts' frontmatter as an
  array — `list … --meta -j`.
- `list --children <ref>` returns the direct children of `<ref>`
  as a flat result set, composable with all existing filters.
- `show <ref> --parent` returns the parent record of `<ref>`,
  composable with `--meta`, `-j`, and `-e`.
- Cross-kind relationships work without an explicit `--kind`
  flag (e.g. a task whose parent is a spec).
- All new behaviour is **read-only**. None of these flags mutate
  any artifact.
- The graph-traversal primitive lives in `core` and is reusable
  by [[n0002-layouts-tree-view-scoping]] without rework.

**Non-goals (explicitly v1-out-of-scope):**

- **Transitive traversal.** No `--subtree`, `--ancestors`,
  `--descendants`. Pipelines cover multi-hop (Use case 5 in
  n0003); revisit only after v1 lands.
- **Generic field-filter flags.** No `--field key=value`,
  `--owner alice`, etc. Saved-view filters (s0012 §5) are the
  current path for non-native equality filters.
- **Mutation.** `--parent` is a query, never an assignment. There
  is no `set-parent` / `attach` flag in this spec.
- **Tree rendering.** Visual hierarchy belongs to
  [[n0002-layouts-tree-view-scoping]].
- **TUI integration.** Downstream consumer of this surface.
- **`ai/` consumers.** Downstream consumer; ships separately.

## 3. CLI Surface

```text
artifacts show <ref> [--kind KIND] [--parent]
                     [--meta] [-j | -e]

artifacts list [--kind KIND] [--status STATUS]
               [--children REF] [--view NAME]
               [--fields FIELDS | --meta]
               [-q | -j]
```

| Command | Flag | Type | New? | Description |
|---------|------|------|------|-------------|
| `show` | `--parent`     | bool | **new** | Resolve and show the parent of `<ref>` instead of `<ref>` itself. |
| `show` | `--meta`       | bool | **new** | Render frontmatter only; suppress body. |
| `show` | `--kind`, `-k` | str  | existing | Narrow resolution to a specific kind. |
| `show` | `-j`, `--json` | bool | existing | JSON output (object). |
| `show` | `-e`, `--editor` | bool | existing | Open in `$EDITOR`. |
| `list` | `--children`   | str  | **new** | Predicate: artifacts whose `parent` resolves to `<ref>`. |
| `list` | `--meta`       | bool | **new** | Project full frontmatter (overrides `--fields`/`view.columns`). |
| `list` | `--kind`, `-k` | str  | existing | Filter by kind. |
| `list` | `--status`, `-s` | str | existing | Filter by status. |
| `list` | `--view`, `-V` | str  | existing (s0012) | Named view from `artifacts.yaml`. |
| `list` | `--fields`, `-f` | str | existing | Field spec string. |
| `list` | `-q`, `--quiet` | bool | existing | One name per line. |
| `list` | `-j`, `--json` | bool | existing | JSON output (array). |

### 3.1 No new short aliases

`--meta`, `--children`, and `--parent` ship without short aliases.
The `-m`, `-c`, and `-p` slots are reserved for future surfaces
that have not yet been specced. Dropping aliases here costs a few
keystrokes but avoids a one-letter slot that becomes hard to
reclaim.

### 3.2 Argparse rejections (compile-time guardrails)

The following flag combinations are **rejected at parse time**
via argparse mutually-exclusive groups; argparse emits its usage
message and the wrapper exits `2`:

| Rejected | Reason |
|----------|--------|
| `list --fields … --meta`        | Both are projection-layer choices on the same record. They answer different questions; pick one. |
| `show --json --editor`          | Existing rejection in s0003. Unchanged. |
| `list --quiet --json`           | Existing rejection in s0003. Unchanged. |

The following combinations are **silently rejected at runtime**
(see §7 for exit codes and stderr messages):

| Rejected | Reason |
|----------|--------|
| `show --view <name>`        | `show` is identity-based; views bundle filter+sort+columns which are meaningless on one record. |
| `show --status <s>`         | Same: `show` resolves by ID, not by predicate. |
| `show --children <ref>`     | Collapses 1↔N; use `list --children <ref>`. |
| `list <ref>` (positional)   | Conflates predicate with identity; use `show <ref>`. |
| `list --parent <ref>`       | Reserves the relationship vocabulary asymmetrically — see §4. |

These guardrails are encoded as argparse choices where possible
and as explicit `ValidationError` raises where not (see §11.4).

## 4. Identity vs Predicate — Locked Principle

> **CLI shape principle.** `show` is **identity-based** and
> returns exactly one record (JSON shape: object). `list` is
> **predicate-based** and returns zero or more records (JSON
> shape: array). All future flags must fit one of these shapes;
> flags that collapse the distinction are rejected.

| Axis | `show` | `list` |
|------|--------|--------|
| Input | A reference (or relationship derived from a ref) | A predicate (zero or more filters) |
| Output cardinality | Exactly 1 | 0..N |
| JSON shape (`-j`) | Object `{}` | Array `[…]` |
| Default content | Full body + frontmatter | Column projection |
| `--meta` switches default to | Frontmatter only (object) | Frontmatter only per row (array) |
| Failure mode (unmatched) | Exit 3 (NotFoundError) | Exit 0, empty output |
| Filter / order / view flags | **Rejected** | Allowed |
| Relationship traversal | `--parent` (one edge → one node) | `--children <ref>` (predicate using one edge) |

### 4.1 Asymmetry of `--parent` and `--children`

The asymmetric placement is **deliberate** and reflects
cardinality, not oversight:

| Direction | Command | Cardinality | Why |
|-----------|---------|-------------|-----|
| Get **parent of** `<ref>` | `show <ref> --parent` | 1 | Parent edge points to one node. |
| Get **children of** `<ref>` | `list --children <ref>` | N | Children is a set; predicate-shaped. |

This principle is **load-bearing**: it justifies why
`list --parent <ref>` is rejected (would be a 1-cardinality
query in `list`, breaking the shape) and why
`show <ref> --children` is rejected (would be N-cardinality in
`show`).

### 4.2 Test for any future flag

Apply this decision tree to any newly-proposed flag:

1. Does it take a ref and return one record?  → `show` flag.
2. Does it take a predicate and return a set? → `list` flag.
3. Does it shift projection on either?        → may apply to both
   (e.g. `--meta`, `-j`, `--fields` on `list`).

### 4.3 Rejected flag shapes — kept on file as guardrails

These are normative — implementations must reject them and tests
must cover the rejection (see §11.4):

| Tempting but wrong | Why it's wrong |
|--------------------|----------------|
| `show <ref> --children` (expand inline) | Collapses 1↔N. Use `list --children <ref>`. |
| `list <ref>` (positional ref) | Conflates predicate with identity. Use `show <ref>`. |
| `list --parent <ref>` | Reserves cardinality vocabulary. Use `show <ref> --parent`. |
| `show --kind task` (no ref, first match) | Predicate disguised as identity. Use `list --kind task -j \| jq '.[0]'`. |
| `show <ref> --view <name>` | Views bundle filter+sort+columns; meaningless on one record. |
| `show <ref> --status <s>` | Filter, not identity. Use `list --status … -j` and project. |

## 5. Layered Model and Composition Matrix

### 5.1 Layered model (settled in n0003)

`artifacts list` flags fall into five conceptual layers. Every
new flag in this spec slots into exactly one layer:

| Layer | Controls | Flags |
|-------|----------|-------|
| 1. Selection  | Which artifacts come back | `--kind`, `--status`, **`--children`** |
| 2. Ordering   | What order              | view-only: `view.sort` |
| 3. Projection | Which fields per record | `--fields`, **`--meta`** |
| 4. Format     | How rendered            | default table, `-q`, `-j` |
| 5. Preset     | Bundles 1+2+3 from YAML | `--view`, `default_views[kind]` |

**`--children`** is a **selection-layer predicate**, semantically
equivalent to "filter for artifacts whose `parent` resolves to
`<ref>`". It composes with other selection flags via per-key
merge — there is no override semantics because `parent` is not a
dimension of `view.filters`.

**`--meta`** is a **projection-layer flag**. It overrides
`--fields` (rejected at parse time, §3.2) and `view.columns`
(precedence below).

### 5.2 Composition rules

Three rules govern every cell of the matrix:

1. **Within a layer, explicit flags win and merge per-key.**
   (Inherited from s0012 §5.)
2. **Across layers, projection is independent of selection.**
   `--meta` wins over `view.columns` and `--fields`.
3. **Format flags interact with projection per the table below.**
   `-q` ignores projection (always prints `path.stem`); `-j`
   honours projection (`--meta -j` → frontmatter dicts;
   default `-j` → frontmatter dicts via existing
   `[item.frontmatter for item in items]` shape).

### 5.3 Composition matrix — exhaustive

Every cell is derivable from §5.2. The matrix below makes that
mechanical.

#### `list` matrix

| Invocation | Selection | Sort | Projection | Format |
|------------|-----------|------|------------|--------|
| `list` | all kinds, all statuses | default | registry default columns | table |
| `list --kind task` | kind=task | default | task default columns | table |
| `list --kind task --status ready` | kind=task ∧ status=ready | default | task default columns | table |
| `list --view active` | view.filters | view.sort | view.columns | table |
| `list --view active --status ready` | view.filters merged with status=ready | view.sort | view.columns | table |
| `list --view active --meta` | view.filters | view.sort | **full frontmatter** | table |
| `list --view active --meta -j` | view.filters | view.sort | **full frontmatter** | **JSON array** |
| `list --view active --fields id,name` | view.filters | view.sort | `--fields` (overrides view.columns) | table |
| `list --view active --fields id,name --meta` | — | — | **rejected at parse time** (§3.2) | — |
| `list --view active -q` | view.filters | view.sort | (ignored) | names only |
| `list --view active -j` | view.filters | view.sort | full frontmatter (existing `-j` shape) | JSON array |
| `list --children t0041` | parent==t0041 | default | registry default columns | table |
| `list --children t0041 -j` | parent==t0041 | default | full frontmatter | JSON array |
| `list --children t0041 --meta -j` | parent==t0041 | default | full frontmatter | JSON array |
| `list --children t0041 -q` | parent==t0041 | default | (ignored) | names only |
| `list --children t0041 --kind task --status ready` | parent==t0041 ∧ kind=task ∧ status=ready | default | task default columns | table |
| `list --children t0041 --view active` | parent==t0041 merged with view.filters | view.sort | view.columns | table |
| `list --children t0041 --view active --meta -j` | parent==t0041 merged with view.filters | view.sort | full frontmatter | JSON array |
| `list --kind task --meta` | kind=task | default | full frontmatter | table |
| `list --meta -j` | all | default | full frontmatter | JSON array |

#### `show` matrix

| Invocation | Resolution | Projection | Format |
|------------|------------|------------|--------|
| `show t0046` | t0046 | full record | table + body |
| `show t0046 --meta` | t0046 | frontmatter only | table |
| `show t0046 --meta -j` | t0046 | frontmatter only | **JSON object** |
| `show t0046 -j` | t0046 | full record (frontmatter + body) | JSON object |
| `show t0046 -e` | t0046 | (n/a) | open file in `$EDITOR` |
| `show t0046 --parent` | parent of t0046 | full record | table + body |
| `show t0046 --parent --meta` | parent of t0046 | frontmatter only | table |
| `show t0046 --parent --meta -j` | parent of t0046 | frontmatter only | JSON object |
| `show t0046 --parent -e` | parent of t0046 | (n/a) | open parent's file in `$EDITOR` |
| `show t0046 --view active` | — | — | **rejected** (§3.2) |
| `show t0046 --children` | — | — | **rejected** (§3.2) |

If the user can predict every cell from the rules in §5.2, the
surface is learnable.

### 5.4 Precedence — projection layer

Existing precedence (s0012 §5) extended for `--meta`:

```text
--meta  >  --fields  >  view.columns  >  registry default columns
```

`--meta` wins **outright**, not per-key. There is no merge
semantics for projection — projection is a single choice.

### 5.5 Precedence — selection layer

`--children` is a **predicate**, not a key/value filter, so the
existing per-key merge in s0012 §5 ("explicit CLI flag > view
filter") does not apply directly. Instead:

- `--children <ref>` adds a `parent==<resolved-ref>` predicate
  to the selection layer **unconditionally**.
- It composes with `--kind`, `--status`, and any non-native
  view filters via logical AND.
- It does **not** override or merge with view filters (no view
  filter has the same dimension).

### 5.6 Quiet / JSON contract — extended

The s0012 §8 contract is extended verbatim with a `--meta`
column:

| Output mode | `args.fields` | `view.columns` | `view.filters` | `view.sort` | `--meta` |
|-------------|---------------|----------------|----------------|-------------|----------|
| default (table) | applied | applied (if no `--fields`/`--meta`) | applied | applied | applied (overrides columns) |
| `-q` / `--quiet` | **ignored** | **ignored** | applied | applied | **ignored** (`-q` wins) |
| `-j` / `--json` | **ignored** | **ignored** | applied | applied | applied — switches `-j` shape from "list of frontmatter dicts (existing)" to "list of frontmatter dicts (now normative as the v1 contract)" |

**Note on `-j`'s shape.** The existing `list -j` already emits
`[item.frontmatter for item in items]` (see
`src/artifacts_os/cli/commands/list.py:48`). `--meta -j` does
not change that shape — it makes that shape **normative and
documented** under the `--meta` flag rather than an undocumented
implementation detail of bare `-j`. See §8 for the stability
contract.

## 6. Graph Traversal Primitive

### 6.1 Where it lives — `core`

The traversal primitive lives in `artifacts_os.core.discover`,
not in CLI command modules. Rationale:

- **Module DAG** — `core` already owns `list_artifacts` and
  `resolve`; `parent` and `children` are the same logical
  layer. `views` and `cli` already depend on `core`, so this
  placement adds no new dependencies.
- **Reusability** — [[n0002-layouts-tree-view-scoping]]'s tree
  layout will live in `views/` and consume `children()` to
  render `└─` rows. Putting traversal in `core` means
  `views/` does not need to inline the same logic.
- **Testability** — keeping the primitive `core`-side lets
  `tests/core/test_discover.py` cover edge cases (broken
  wikilinks, cross-kind, missing parent) without spinning up
  argparse.

### 6.2 Public API

Two new functions, re-exported from `artifacts_os.core`:

```python
def parent(
    registry: Registry,
    ref: str | ArtifactMeta | Path,
    *,
    kind: str | None = None,
) -> ArtifactMeta | None:
    """Resolve and return the parent ArtifactMeta of <ref>.

    Reads the `parent` frontmatter field (Obsidian wikilink
    `[[ref]]` or bare ref string), unwraps to a bare ref, and
    resolves cross-kind via discover.resolve(registry, ref).

    Returns None if the artifact has no `parent` field at all.
    Raises NotFoundError if the field exists but the wikilink
    does not resolve (broken link). Raises AmbiguousError if
    the wikilink resolves to multiple kinds (extremely rare;
    surface the candidate list).
    """

def children(
    registry: Registry,
    ref: str | ArtifactMeta | Path,
    *,
    kind: str | None = None,
    status: str | None = None,
) -> list[ArtifactMeta]:
    """List direct children of <ref>.

    Iterates list_artifacts(registry, kind=kind, status=status)
    and returns those whose `parent` frontmatter field resolves
    to the same artifact as <ref>. Wikilink unwrapping handled
    here; resolution uses discover.resolve so the comparison is
    by canonical path.

    Returns [] if the artifact has no children. Never raises
    on empty result — empty is a valid answer to a predicate
    query.
    """
```

### 6.3 Resolution semantics

- **Source field.** v1 only consults the `parent` frontmatter
  field. No alternative names, no array form (single value).
  This mirrors n0002's tree-view scope.
- **Wikilink unwrapping.** The CLI's existing wikilink wrapping
  on `--parent` (s0003) means stored values look like
  `"[[t0036]]"` or `"[[t0036-name-slug]]"`. The traversal
  helper strips `[[` / `]]` and resolves the inner string via
  `discover.resolve(...)`, **without** a `kind` argument so
  cross-kind parents (task → spec) work.
- **Cross-kind.** `discover.resolve` already iterates all kinds
  when `kind=None`. Cross-kind parents (e.g. a task whose
  parent is a spec) work without explicit `--kind`. Tests
  cover this in §11.5.
- **Identity comparison in `children()`.** Compare on
  resolved-path equality, not raw wikilink strings. Two
  refs (`t36` and `t0036-name`) that resolve to the same path
  must be treated as equal. This makes the primitive robust
  to the rich set of ref forms `discover._find_in_dir` accepts.

### 6.4 Performance note

`children()` is `O(N)` over all artifacts of the candidate kind
set. For v1 this is fine — vaults are hundreds of files, not
millions. Caching / index files are out of scope.

### 6.5 What the primitive deliberately does NOT do

- No transitive closure (`subtree`, `ancestors`).
- No back-edges (`depends_on`, `blocks`, etc. — they have
  their own frontmatter conventions).
- No graph-as-data export (no `to_dot`, no NetworkX
  dependency).

These are exclusions that keep the primitive cheap to maintain
until a concrete consumer needs them.

## 7. Error Semantics

### 7.1 Exit-code table

| Condition | Exit | Stderr message |
|-----------|------|----------------|
| `show <unknown>` | 3 | `error: No artifact matches '<ref>'` (existing) |
| `show <ref> --parent` and `<ref>` has no `parent` field | 3 | `error: artifact '<ref>' has no parent` |
| `show <ref> --parent` and `parent` wikilink does not resolve | 3 | `error: parent of '<ref>' refers to '<bare-ref>' which does not exist` |
| `show <ref> --parent` and `parent` wikilink is ambiguous | 4 | `error: parent of '<ref>' refers to '<bare-ref>' which is ambiguous:\n  <candidates>` |
| `show <ref> --view <name>` | 2 | `error: --view is not valid on 'show' (use 'list --view')` |
| `show <ref> --status <s>` | 2 | `error: --status is not valid on 'show'` |
| `show <ref> --children` | 2 | `error: --children is not valid on 'show' (use 'list --children <ref>')` |
| `list --children <unknown>` | 3 | `error: No artifact matches '<ref>'` (resolution fails before predicate runs) |
| `list --children <leaf>` (resolves but has no children) | 0 | empty output (table: empty; `-j`: `[]`; `-q`: empty) |
| `list <ref>` (positional) | 2 | argparse: `unrecognized arguments: <ref>` (or explicit reject) |
| `list --parent <ref>` | 2 | argparse: `unrecognized arguments: --parent` |
| `list --fields … --meta` | 2 | argparse mutually-exclusive usage error |

### 7.2 Why `--parent` failures are exit 3, not exit 0

`show` is identity-based; the user named a record (the parent
of `<ref>`) and the system could not produce it. That is a
"no record found" condition, the exact contract for exit 3
(`NotFoundError`). Returning exit 0 with empty output would
silently mask broken parent links in shell pipelines.

The reverse choice for `list --children` (empty → exit 0) is
correct **for the same reason**: a predicate matching zero
records is a valid empty answer, not a missing record.

### 7.3 Broken-wikilink reporting

When `parent` refers to a missing artifact, the error message
must name the **dangling wikilink contents**, not the
canonical path. Pipeline consumers grep stderr for the bad
ref to fix it.

```
error: parent of 't0046-foo' refers to 't0099-deleted' which does not exist
```

## 8. JSON Stability Contract

This contract is **public, normative, and version-stable**.
Downstream consumers (AI agents, CI scripts, IDE plugins) build
parsers against it. Any future change is a breaking change and
must move to a new flag or major version.

### 8.1 `show <ref> [--parent] --meta -j`

```json
{
  "id": "t0046",
  "kind": "task",
  "name": "fix-bug",
  "status": "ready",
  "created": "2026-04-29",
  "parent": "[[t0041-redo-pipeline]]",
  ...
}
```

- Shape: **JSON object** (`{}`).
- Keys: every frontmatter key, verbatim.
- Values: stringified by `json.dumps(..., default=str)` (mirrors
  existing `show -j` behaviour for path/date types).
- No `body` key (suppressed by `--meta`).
- No nesting under `frontmatter` — the dict **is** the
  frontmatter.
- Missing keys absent (no `null` placeholders).

### 8.2 `show <ref> -j` (without `--meta`)

```json
{
  "id": "t0046",
  ...,
  "body": "# Title\n\n…"
}
```

- Same as `--meta -j`, plus a `body` string key. Existing
  shape; documented here for completeness.

### 8.3 `list … --meta -j` and `list … -j`

```json
[
  { "id": "t0041", "kind": "task", ... },
  { "id": "t0042", "kind": "task", ... }
]
```

- Shape: **JSON array** of objects.
- Each element: full frontmatter dict (no body — `list` has
  never read bodies into `ArtifactMeta`).
- `--meta -j` and bare `-j` produce **the same shape today**
  (this spec makes that explicit and normative). The
  difference is only that `--meta` is the documented
  on-ramp; bare `-j` continues to work for backward
  compatibility.
- Order: post-sort, post-filter, deterministic per the rules
  in §5.

### 8.4 What is NOT in the contract

- Field **ordering inside an object** — JSON object key order
  is not guaranteed. Consumers must look up by key, not by
  position.
- Stringification of non-string scalars (integers, lists) —
  `default=str` is the existing implementation; this spec
  adopts it as the v1 contract but reserves the right to
  emit native JSON types in v2 if a need arises.

## 9. Eight Open Questions from n0003 — Resolved

| # | Question | Resolution | Rationale |
|---|----------|-----------|-----------|
| 1 | `-q` + `--meta` — `-q` wins or rejected? | **`-q` wins; `--meta` silently ignored.** | `-q` is the existing cardinality reducer; ignoring projection is its long-standing contract (s0012 §8). Symmetry with `--fields` (also ignored under `-q`) keeps the rule "format flags trump projection" universal. Rejecting the combination would force scripts to branch on output mode, fighting the layered model. |
| 2 | `--fields` + `--meta` interaction | **Mutually exclusive (parse-time error, exit 2).** | They are competing projection-layer choices, not composable. `--meta` does not "filter the meta dict" — that surface (`--meta-fields`?) is intentionally not in v1. Explicit rejection at parse time gives the clearest possible error. |
| 3 | `show --parent -e` legality | **Legal — open the parent's file in `$EDITOR`.** | `-e` is "open the resolved target". `--parent` redirects what "the target" means; the rest of editor semantics carries over unchanged. Useful in practice (jump from a child to edit its parent). Existing TTY-detection downgrades to text output in non-interactive contexts (s0003 / show.py:42); same rule applies here. |
| 4 | Missing-relationship behaviour | **`show <root> --parent` → exit 3 with explicit message; broken wikilink → exit 3 naming the dangling ref; `list --children <leaf>` → exit 0 empty (settled in n0003).** | See §7.1 / §7.2. The asymmetry follows directly from identity-vs-predicate: `show` failing to resolve is exit 3; `list` returning zero rows is exit 0. |
| 5 | Where graph traversal lives | **`core/discover.py`, exposed as `parent()` / `children()` in `artifacts_os.core` public API.** | See §6.1. Module DAG, reusability for n0002, testability all align. |
| 6 | Resolution source for relationships | **v1 = `parent` frontmatter wikilink only.** Single value, no array form, no alternative field names. | Matches n0002 scope. Prevents ambiguity if a future kind grows multiple parent edges; the back-compat surface is a single key only. |
| 7 | `--view` × `--meta` precedence | **`--meta` overrides `view.columns` outright; `view.filters` and `view.sort` still apply.** | See §5.4 / §5.6. Parallels `-j`'s existing precedence over `view.columns`: format/projection wins over preset's column choice; selection and ordering survive. |
| 8 | `--view` × `--children` composition | **`--children <ref>` adds a `parent==<resolved-ref>` predicate at the selection layer; composes with view filters via logical AND. Not subject to per-key merge (no view filter has this dimension).** | See §5.5. Documented in row 16 of the §5.3 matrix. |

## 10. v1 Scope — Explicit Exclusions

Repeated here so the developer (and the user verifying t0050) has
a single point of reference:

- **No transitive traversal.** `--subtree`, `--ancestors`,
  `--descendants` are out. Multi-hop is shell composition (Use
  case 5 in n0003).
- **No generic field-filter flags.** `--field key=value`,
  `--owner alice` are out. Saved-view filters are the v1
  workaround.
- **No mutation flags.** `--parent` is a query, never an
  assignment. No `set-parent`, no `attach`, no auto-write.
- **No tree rendering.** `└─` characters belong to
  [[n0002-layouts-tree-view-scoping]].
- **No TUI integration.** `tui/` is a stub; it consumes this
  surface when it ships, not vice-versa.
- **No `ai/` consumer changes.** `ai/` is a stub; same as TUI.
- **No `--meta` on `list -q`.** `-q` ignores projection
  uniformly (Q1 above).

## 11. Implementation Outline

This spec is the contract; the parent task
[[t0050-programmatic-cli-access-for-frontmatter]] decomposes the
implementation into developer / author sub-tasks. The file-level
changes below are normative — every file listed here must be
touched to satisfy the spec.

### 11.1 `src/artifacts_os/core/discover.py` (extend)

Add `parent()` and `children()` per §6.2. Both functions reuse
existing private helpers (`_meta_from_file`, `_kind_dir`) and the
public `resolve` for cross-kind ref expansion. No new imports
beyond what the module already pulls in.

Wikilink unwrap helper (private):

```python
_WIKILINK_RE = re.compile(r"^\[\[(.+?)\]\]$")

def _unwrap_wikilink(value: str) -> str:
    """Return the inner ref of `[[ref]]`, or value unchanged."""
    m = _WIKILINK_RE.match(value.strip())
    return m.group(1) if m else value.strip()
```

### 11.2 `src/artifacts_os/core/__init__.py` (extend)

Add `parent` and `children` to imports and `__all__`. Re-export
behind the same public surface as `list_artifacts` / `resolve`.

### 11.3 `src/artifacts_os/cli/commands/show.py` (extend)

Wire `--parent` and `--meta`:

```python
def register(subparsers) -> None:
    p = subparsers.add_parser("show", help="show an artifact")
    p.add_argument("ref", help="artifact reference (name, id, or partial)")
    p.add_argument("--kind", "-k", help="narrow to a specific kind")
    p.add_argument("--parent", action="store_true",
                   help="show the parent of <ref> instead of <ref>")
    p.add_argument("--meta", action="store_true",
                   help="frontmatter only (no body)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-j", "--json", action="store_true", dest="json_out")
    mode.add_argument("-e", "--editor", action="store_true")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    artifact = get(registry, args.ref, kind=args.kind or None)

    if args.parent:
        from artifacts_os.core import parent as _parent
        parent_meta = _parent(registry, artifact)
        if parent_meta is None:
            raise NotFoundError(f"artifact '{args.ref}' has no parent")
        # Re-read body so editor and rich-text rendering work uniformly.
        artifact = get(registry, parent_meta.path.stem)

    if args.meta:
        return _render_meta(args, artifact)

    # ... existing render path unchanged
```

`_render_meta` mirrors the existing default render path but
(a) renders only frontmatter as a one-row table or single
`json.dumps(artifact.frontmatter, default=str)`, and (b)
suppresses the body print.

Reject `show --view`, `show --status`, `show --children` —
either by not adding the flags to the parser at all (preferred;
argparse will surface "unrecognized arguments") or by wiring
explicit `ValidationError` raises.

### 11.4 `src/artifacts_os/cli/commands/list.py` (extend)

Add `--children` and `--meta`:

```python
def register(subparsers) -> None:
    p = subparsers.add_parser("list", help="list artifacts")
    p.add_argument("--kind", "-k", help="filter by kind")
    p.add_argument("--status", "-s", help="filter by status")
    p.add_argument("--children", help="direct children of <ref>")
    p.add_argument("--view", "-V", help="named view from artifacts.yaml")

    proj = p.add_mutually_exclusive_group()
    proj.add_argument("--fields", "-f",
                      help="field spec string (e.g. 'id,name,status')")
    proj.add_argument("--meta", action="store_true",
                      help="full frontmatter (overrides --fields/view.columns)")

    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-q", "--quiet", action="store_true")
    mode.add_argument("-j", "--json", action="store_true", dest="json_out")

    p.set_defaults(func=run)
```

In `run()`:

1. If `args.children` is set, resolve it via `discover.resolve`
   (no `kind` arg → cross-kind). If resolution fails, surface
   the existing `NotFoundError` (exit 3).
2. Apply view (existing s0012 path).
3. Run `list_artifacts` (existing).
4. Apply the children predicate as a post-discovery filter
   using `core.children(registry, ref)` — or, equivalently,
   filter `items` by `_unwrap_wikilink(m.frontmatter.get("parent","")) → ref`.
   Use whichever helper yields cleaner code; the contract is
   that the result is identical to `core.children(...)`
   intersected with the view/`--kind`/`--status` filters.
5. Apply `_apply_extra_filters` (existing).
6. Apply `_apply_sort` (existing).
7. If `args.quiet`: print stems (`--meta` ignored — Q1 above).
8. If `args.json_out`: print `json.dumps([m.frontmatter for m in items], default=str)`.
9. Else (table): if `args.meta`, build a column list of
   **all union frontmatter keys across `items`** (deterministic
   order: `id`, `kind`, `name`, `status`, `created`, then
   remaining keys sorted) and pass to `views.render_table`.
   Otherwise resolve columns via `_resolve_columns` (existing).

Reject `list <ref>` (positional) — no positional argument is
defined; argparse rejects it with "unrecognized arguments". No
extra wiring needed.

### 11.5 Tests — required coverage

Three new test modules. Each row in §5.3 must correspond to
at least one assertion across these files.

#### `tests/core/test_graph.py` (new)

1. `parent(meta_with_parent)` → resolved `ArtifactMeta`.
2. `parent(meta_with_no_parent_field)` → `None`.
3. `parent(meta_with_broken_wikilink)` → raises `NotFoundError`
   with the dangling ref in the message.
4. `parent(meta_with_cross_kind_parent)` → resolves across
   kinds (task → spec).
5. `parent(meta_with_bare_ref_no_brackets)` → still resolves
   (stored value `"t0036-foo"` without `[[…]]`).
6. `children(parent_meta)` → list of children, sorted by
   `path.stem`.
7. `children(leaf_meta)` → `[]` (no error).
8. `children(parent_meta, kind="task")` → narrows to one
   kind.
9. `children(parent_meta, status="ready")` → narrows to one
   status.
10. `children(parent_meta)` correctly identifies children
    even when their `parent` field uses different ref forms
    (`t36`, `t0036`, `t0036-name`, `[[t0036-name]]`).

#### `tests/cli/test_show_meta.py` (new)

1. `show t0046 --meta` → table with frontmatter keys, no
   body printed.
2. `show t0046 --meta -j` → JSON object, no `body` key,
   parses cleanly.
3. `show t0046 --meta -j` body is a `dict`, never an array.
4. `show t0046 --meta -e` opens editor on artifact (TTY
   gated; assert `os.execvp` invoked with artifact path).
5. `show <unknown> --meta` → exit 3.

#### `tests/cli/test_show_parent.py` (new)

1. `show t0046 --parent` → renders parent's table+body.
2. `show t0046 --parent --meta` → parent's frontmatter table.
3. `show t0046 --parent --meta -j` → parent's frontmatter as
   JSON object; `id` matches the parent's `id`.
4. `show <root-with-no-parent> --parent` → exit 3, stderr
   matches `"has no parent"`.
5. `show <ref-with-broken-parent> --parent` → exit 3, stderr
   names the dangling wikilink.
6. `show <task-with-spec-parent> --parent` → resolves
   cross-kind successfully.
7. `show t0046 --view active` → exit 2, stderr matches
   "not valid on 'show'".

#### `tests/cli/test_list_meta.py` (new)

1. `list --meta` table → columns include all frontmatter
   keys union.
2. `list --meta -j` → array of frontmatter dicts.
3. `list --kind task --meta -j` → array filtered by kind.
4. `list --view active --meta -j` → filters and sort applied,
   columns ignored.
5. `list --view active --meta` (table) → projection wins over
   view.columns.
6. `list --fields id,name --meta` → exit 2 (mutually
   exclusive).
7. `list --meta -q` → names only (`--meta` silently ignored).
8. `list --meta -j` shape stable across two calls (regression
   guard).

#### `tests/cli/test_list_children.py` (new)

1. `list --children t0041` → flat table of children.
2. `list --children t0041 -j` → JSON array.
3. `list --children t0041 --meta -j` → JSON array of full
   frontmatter dicts.
4. `list --children t0041 -q` → child stems only.
5. `list --children t0041 --status ready` → intersected
   correctly.
6. `list --children t0041 --kind task --view active` →
   composes with view filters and selection filters.
7. `list --children <leaf>` → exit 0, empty table (and `[]`
   under `-j`).
8. `list --children <unknown>` → exit 3.
9. `list --children s0012` (cross-kind: spec's children) →
   resolves any-kind children.
10. `list --parent t0041` → exit 2 (argparse unrecognized).

### 11.6 Documentation updates (developer + author scope)

- `src/artifacts_os/cli/README.md` — add a "Programmatic
  access" subsection documenting `--meta`, `--children`,
  `--parent`, the JSON contract from §8, and at least one
  worked pipeline example from n0003 Use case 5.
- `docs/cli.md` — extend the existing reference to mention
  the new flags and link to this spec.
- `s0003-artifacts-os-cli-module.md` — update the `show`
  and `list` synopses in §"Command Set" to include the new
  flags; add cross-link to this spec.
- `.openstation/skills/artifacts-os/` (if such a skill
  exists) — note the JSON contract so AI consumers learn
  the shape.
- `CLAUDE.md` — no change expected; the new flags are
  visible from the module READMEs.

### 11.7 Slash-command pattern (optional, recommended)

Author may ship one slash-command example that demonstrates
the agent-friendly use case:

`.openstation/commands/artifacts.children.md`:

```bash
artifacts list --children "$1" --meta -j | jq '[.[] | {id, name, status}]'
```

Pattern is identical to s0012 §12. Not normative for v1; can
be added in the documentation sub-task.

## 12. Verification (inherited by t0051)

Re-listed here so the verifying user can run them against this
spec without flipping back to the task file:

- [x] Spec lands at `artifacts/specs/s0013-programmatic-cli-access.md`
      with `status: draft`. **(Done by this commit.)**
- [x] Cross-links to n0003, n0002, s0012, s0007, s0003. **(§1.)**
- [x] Composition matrix is exhaustive — every cell answerable
      from the layered-model rules. **(§5.3 + §5.2.)**
- [x] All eight open questions from n0003 resolved with recorded
      rationale. **(§9.)**
- [x] Implementation outline names every file the developer must
      touch. **(§11.1–§11.6.)**
- [x] v1 scope exclusions are explicit and listed. **(§10.)**
- [ ] Reviewed and approved by user before parent task t0050
      moves to `ready`. **(Owner action — pending.)**

## 13. Decision Log

| Marker | Items |
|--------|-------|
| **Decided** | Identity-vs-predicate principle (§4). `--meta`/`--children`/`--parent` placement per cardinality (§3, §4.1). Graph traversal lives in `core/discover.py` (§6.1). JSON shapes: `show --meta -j` = object; `list --meta -j` = array (§8). `-q` wins over `--meta` (§9 Q1). `--fields` and `--meta` mutually exclusive (§9 Q2). `show --parent -e` legal (§9 Q3). Missing parent is exit 3 (§7). v1 source field is `parent` only (§6.3 / §9 Q6). |
| **Recommended** | Reserve `-m` / `-c` / `-p` short slots; ship the long-form flags only (§3.1). Wire show-side rejections by not adding flags to the parser (§11.3). Implement `list --children` via the public `core.children()` rather than inlining the predicate (§11.4 step 4). |
| **Deferred** | Transitive traversal flags (§10). Generic field-filter flags (§10). `--meta-fields KEY,KEY` projection (§9 Q2). Native non-string JSON types (§8.4). Caching / index files for `children()` (§6.4). Generator for slash-command shims (§11.7 — same status as s0012 §12). |
