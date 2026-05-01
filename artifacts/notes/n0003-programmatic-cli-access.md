---
id: n0003
name: programmatic-cli-access
kind: note
type: planning
created: 2026-05-01
---

# Programmatic CLI Access: Frontmatter & Relationships

> PM scoping note from a brainstorm session. Captures the requirements
> and CLI shape for two related capabilities — frontmatter-only output
> and parent/child navigation — at a level a spec writer can consume.
> No architectural decisions; those land in the spec.

## Origin

Two adjacent requests surfaced together:

1. A way to fetch only the **frontmatter** of an artifact (no body),
   for AI agents and inter-module CLI use.
2. A way to fetch the **parent** or **children** of a specific
   artifact.

Both serve the same underlying need: **structured CLI access to
artifacts as data**, not as rendered docs. They share a primitive
(graph + metadata projection) and should be specced together.

A third related thread — visual rendering of hierarchy (`└─` tree
view) — already has its own scoping note (`n0002`). That work
**consumes** the data primitive defined here but adds rendering
concerns that belong in `views/`. Keep n0002 separate.

## User-facing outcome

- AI agents and other modules can fetch any artifact's frontmatter as
  a structured dict — directly, without parsing markdown or stripping
  bodies.
- The same agents can **traverse the artifact graph** through both
  CLI entry points: `show` (one record by ID, with `--parent` to
  hop one edge) and `list` (a set defined by predicate, including
  `--children <ref>` as a relationship predicate).
- All of this is read-only and orthogonal to how things are
  *displayed*.

## Mental model — artifacts form a graph

The unifying frame: **artifacts form a graph**, and `list` / `show`
are both **traversal entry points** into it. They differ in how they
enter and in cardinality, not in purpose.

| | `show` | `list` |
|---|---|---|
| Entry point | A specific ID | A predicate (filters / view / `--children`) |
| Yields | Exactly one node | A set of nodes |
| Default content | The full document (frontmatter + body) | A projection of frontmatter (columns) |
| Traversal flags | `--parent` (edge hop → one node) | `--children <ref>` (predicate using an edge) |
| Projection switches | `--meta` | `--meta`, `--fields` |
| Filters / ordering / view | **N/A** by definition | `--kind`, `--status`, `--children`, `--view` |

Three rules fall out cleanly:

1. **`show` is identity-based.** Filters, ordering, and views are
   conceptually meaningless on a single named record and are
   **explicitly rejected** (`show --view`, `show --status`,
   `show --kind` etc. are not legal flags).
2. **`list` is predicate-based.** Anything that scopes a *set* lives
   here, including the relationship-as-predicate `--children`.
3. **Projection is orthogonal to the entry point.** `--meta` is
   shared between both commands; it switches the default (full
   document for `show`, column projection for `list`) to a
   frontmatter dict.

`--view` is unambiguously a **`list`-only macro** — it bundles
filtering, ordering, and columns, none of which apply once a record
has been named by ID. This eliminates one source of confusion
identified in the brainstorm: `show --view` is not a thing.

## Layered mental model for `list` flags

Once `--meta`, `--children`, and `--parent` land alongside the
already-spec'd `--view` (s0012), `artifacts list` carries flags at
four conceptual layers. Without a model the surface looks like a
flat soup; with the model, composition is mechanical.

| Layer | Controls | Flags |
|---|---|---|
| 1. Selection | Which artifacts come back | `--kind`, `--status`, `--children` |
| 2. Ordering | What order they're in | (view-only: `sort`) |
| 3. Projection | What fields/columns per record | `--fields`, `--meta` |
| 4. Format | How the projection is rendered | default table, `-q`, `-j` |
| 5. Preset | Bundles 1+2+3 from YAML | `--view`, `default_views[kind]` |

`--view` is a **macro** — not a peer flag. It expands into layers
1+2+3 from `artifacts.yaml`. The new `--meta`, `--children`,
`--parent` flags must compose with it under three rules:

1. **Within a layer, explicit flags win and merge per-key.**
   `--status ready` overrides `view.filters.status`; other view
   filters still apply. `--children t0041` adds a `parent==t0041`
   predicate alongside view filters.
2. **Across layers, projection is independent of selection.**
   `--meta` wins over `view.columns` the same way `-j` already does
   — opted-in projection takes precedence over view-supplied
   columns. Filters and sort still apply.
3. **Format flags ignore projection.** `-q` and `-j` already
   short-circuit columns. `--meta` composes with `-j`
   (array/object of frontmatter dicts) and is ignored by `-q`
   (names only, per existing semantics).

### Composition matrix the spec must ship

| Invocation | Filters | Sort | Projection | Format |
|---|---|---|---|---|
| `list --view active` | view's | view's | view.columns | table |
| `list --view active --status ready` | merged (ready wins) | view's | view.columns | table |
| `list --view active --meta` | view's | view's | full frontmatter | table |
| `list --view active --meta -j` | view's | view's | full frontmatter | JSON array |
| `list --view active --children t0041` | merged | view's | view.columns | table |
| `list --view active --fields id,name` | view's | view's | `--fields` | table |
| `list --view active -q` | view's | view's | (ignored) | names |

If a user can predict every cell from the three rules, the surface
is learnable.

## Term overload — `--view` is not the rendering layer

The word "view" in artifacts-os carries three meanings:

| "View" | Meaning |
|---|---|
| `views/` module | The rendering layer (table → tree → board…) |
| `--view <name>` | A saved query bundle in `artifacts.yaml` |
| n0002 "tree view" | A future layout (rendering concern) |

This is a real friction point that the user **will** trip over.
Possible mitigations, in increasing cost order:

1. **Document the layered model** in the CLI README. Zero divergence
   from openstation. Recommended for v1.
2. **Rename `--view`** to `--preset` / `--saved` / `--query`. Removes
   the overload at the cost of openstation divergence. Worth a
   discussion but not a v1 blocker.
3. **Rename the `views/` module.** Higher cost; cross-cuts s0007 and
   the layout work in n0002. Out of scope here.

The architect spec must at minimum (a) document the layered model
and (b) ship the composition matrix above. Renaming is deferred.

## Principle — identity vs predicate

Adding several flags to `show` and `list` risks blurring the line
between them. The spec must lock the distinction as a principle, not
just describe current behaviour.

> **CLI shape principle.** `show` is **identity-based** and returns
> exactly one record (JSON object). `list` is **predicate-based**
> and returns zero or more records (JSON array). All future flags
> must fit one of these shapes; flags that collapse the distinction
> are rejected.

| Axis | `show` | `list` |
|---|---|---|
| Input | A reference (or relationship derived from a ref) | A predicate (zero or more filters) |
| Output cardinality | Exactly 1 | 0..N |
| JSON shape | Object `{}` | Array `[…]` |
| Default content | Full body | Metadata only |
| Failure mode | Unknown ref → error | Empty match → empty result |

Test for any future flag:

1. Does it take a ref and return one record? → `show` flag.
2. Does it take a predicate and return a set? → `list` flag.
3. Does it shift projection on either? → may apply to both
   (e.g. `--meta`, `-j`).

### Rejected flag shapes (kept on file as guardrails)

| Tempting but wrong | Why it's wrong |
|---|---|
| `show <ref> --children` (expand inline) | Collapses 1↔N. Use `list --children <ref>`. |
| `list <ref>` (positional ref) | Conflates predicate with identity. Use `show <ref>`. |
| `list --parent <ref>` (filter on field) | "Parent" is already used as relationship-of on `show`. Reserve the vocabulary. |
| `show --kind task` (no ref, first match) | Predicate disguised as identity. Use `list --kind task -j \| jq '.[0]'`. |
| `show <ref> --view <name>` | `show` is identity-based; views bundle filter+sort+columns which are meaningless on one record. |
| `show <ref> --status <s>` | Same reason. `show` resolves by ID alone; status is a filter, not a property of identity. |

## Naming convention (settled in brainstorm)

Flags name **relationships**, not field equality. Asymmetry between
`--parent` (on `show`) and `--children` (on `list`) is a deliberate
reflection of cardinality.

| Direction | Command | Cardinality |
|---|---|---|
| Get children of `<ref>` | `list --children <ref>` | many |
| Get parent of `<ref>` | `show <ref> --parent` | one |
| Frontmatter only | `--meta` (on both `show` and `list`) | n/a |

Field-equality filters (e.g. a generic `--field owner=alice`) get a
separate, distinct surface; they do not pollute the relationship
vocabulary.

## CLI surface — worked examples

### Use case 1 — single artifact frontmatter

```bash
artifacts show t0041 --meta              # human-readable, table only
artifacts show t0041 --meta -j           # JSON dict of frontmatter
artifacts show t0041 --meta -j | jq -r '.status'
```

### Use case 2 — full frontmatter for many artifacts

`list -j` today returns a column projection. `--meta` widens to all
frontmatter keys per row.

```bash
artifacts list --kind task --meta -j
artifacts list --kind task --status ready --meta -j
artifacts list --kind task --meta            # human-readable
```

### Use case 3 — children of a specific artifact

```bash
artifacts list --children t0041                      # default columns
artifacts list --children t0041 -j                   # JSON array
artifacts list --children t0041 --meta -j            # full frontmatter
artifacts list --children t0041 -q                   # names only
artifacts list --children t0041 --kind task --status in-progress
```

### Use case 4 — parent of a specific artifact

```bash
artifacts show t0046 --parent                  # render parent (default)
artifacts show t0046 --parent --meta           # parent's frontmatter
artifacts show t0046 --parent --meta -j        # parent as JSON
artifacts show t0046 --parent --meta -j | jq -r '.id'
```

### Use case 5 — pipeline composition

```bash
# Walk children and inspect each
for c in $(artifacts list --children t0041 -q); do
  artifacts show "$c" --meta -j
done

# Count children
artifacts list --children t0041 -j | jq length

# In-progress children projected to (id, owner)
artifacts list --children t0041 --status in-progress --meta -j \
  | jq '[.[] | {id, owner}]'

# Two-hop: grandparent of t0046
GP=$(artifacts show t0046 --parent --meta -j | jq -r '.id')
artifacts show "$GP" --parent --meta -j
```

### Use case 6 — cross-kind relationships

Cross-kind parents already exist in practice (e.g. a task pointing at
a spec). The query must not collapse on `--kind`.

```bash
artifacts show t0048 --parent --meta -j        # task → spec parent
artifacts list --children s0012 --meta -j      # spec's children, any kind
```

## Development areas touched

| Area              | What changes                                              | Risk |
|-------------------|-----------------------------------------------------------|------|
| Spec / design     | Contract for `--meta`, `--children`, `--parent` flags      | Low; blocks the rest |
| Core              | Possibly expose a graph-traversal primitive (parent/child) | Self-contained |
| Views             | New JSON shape for `list --meta`; `show --meta` formatter  | Self-contained |
| CLI               | Flag wiring on `show` and `list`; flag-composition rules  | Touches shipped flags |
| Docs              | CLI README, settings guide, AI/skill                       | Follows behaviour |
| Tests             | New flag coverage + no-regression on flat list/show       | Standard |

`tui/` and `ai/` are out of scope here — they are downstream consumers
once the surface lands.

## Work breakdown (provisional, sequenced)

1. **Spec** — *architect, owner: user.* Defines the contract for
   `--meta` and the relationship flags, including JSON shape, flag
   composition rules, edge cases, and where graph traversal lives in
   the module DAG. v1 scope: **`--meta`, `list --children`,
   `show --parent` only** — no transitive traversal, no field-filter
   generalization.
2. **Core graph primitive** — *developer.* If the spec calls for a
   shared traversal helper, land it first so both CLI commands and
   future tree-view rendering (n0002) can reuse it.
3. **`--meta` wiring on `show` + `list`** — *developer.* Includes
   JSON-shape contract, `--fields` interaction, `-q`/`-e` carve-outs.
4. **Relationship flags on `show` + `list`** — *developer.* Wires
   `show --parent` and `list --children`, composes with existing
   filters and `--meta`.
5. **Documentation** — *author.* CLI README, AI/skill, settings doc
   if any new keys land.
6. **Verification pass** — *user.* Run all six use-case examples on
   the artifacts-os vault itself.

Dependency shape: `1 → 2 → {3, 4} → 5 → 6`. Tasks 3 and 4 can run in
parallel once graph primitive is in.

## Requirements

Functional:

- `show <ref> --meta` returns frontmatter only (no body) in human and
  JSON forms.
- `list --meta` returns full frontmatter per row (not just the
  default column projection) in human and JSON forms.
- `list --children <ref>` returns the direct children of `<ref>` as a
  flat list, composable with all existing filters and with `--meta`.
- `show <ref> --parent` returns the parent artifact of `<ref>`,
  composable with `--meta` and `-j`.
- Cross-kind relationships work without explicit `--kind`.
- Read-only: none of these flags mutate any artifact.

Non-functional:

- New flags compose cleanly with shipped flags (`--kind`, `--status`,
  `--fields`, `-q`, `-j`, `-e`). The spec must enumerate every
  combination's behaviour or its rejection.
- The JSON shape is documented and stable: `show` flavour returns an
  object; `list` flavour returns an array of objects.
- Module DAG preserved: graph traversal lives in `core`; CLI in
  `cli`; rendering stays in `views`.
- The data primitive established here is reusable by n0002's
  tree-view layout work without further abstraction.

## Out of scope

- **Tree rendering.** Visual hierarchy with `└─` characters is n0002.
- **Transitive traversal** (`--subtree`, `--ancestors`). Pipelines
  cover the multi-hop case for v1 (see Use case 5, last example).
  Re-evaluate after v1 lands.
- **Generic field-filter flags** (`--owner alice`, `--field k=v`).
  Separate concern; mentioned only to justify reserving the
  relationship vocabulary.
- **Mutation flags.** `--parent` here is a query, never an
  assignment.
- **TUI integration.**
- **`ai/` consumers.** Downstream — they consume this surface once it
  ships.

## Open questions for the spec

1. **`-q` + `--meta` interaction.** `-q` is the script-friendly
   cardinality reducer (one name per line). When combined with
   `--meta`, does `-q` win (names only) or is the combination
   rejected? Lean: `-q` wins; `--meta` is silently ignored.
2. **`--fields` + `--meta` interaction.** Mutually exclusive, or does
   `--fields` filter the meta dict? Lean: mutually exclusive — they
   answer different questions.
3. **`show --parent -e`.** Open-in-editor on a parent — legal, or
   rejected because `--parent` is a query rather than a target?
4. **Missing-relationship behaviour.**
   - `show <root> --parent` → empty exit, error, or explicit message?
   - `list --children <leaf>` → empty result with clean exit (not an
     error). This one is settled.
   - `show --parent` on an artifact whose `parent` wikilink is broken
     → error with the dangling reference named.
5. **Where does graph traversal live?** A standalone helper in
   `core`, exposed as a public API? Or inlined in CLI command
   modules? The spec must decide so n0002 can reuse it.
6. **Resolution of relationship source.** v1 = `parent` frontmatter
   wikilink only. Confirmed scope; mirrors n0002.
7. **`--view` × `--meta` precedence on `list`.** Spec must declare
   that `--meta` overrides `view.columns` (parallel to `-j`/`-q`'s
   existing behaviour). Filters and sort still apply.
8. **`--view` × `--children` composition.** `--children <ref>` adds
   a `parent==ref` predicate at the selection layer. It composes
   with view filters per the per-key merge rule. Spec must show this
   in the composition matrix.

## Risks

1. **JSON contract change on `list`.** Today's `list -j` is a column
   projection. Adding `--meta -j` introduces a *second* JSON shape
   from the same command. Consumers must read flag state to know
   what they got. Document loudly or risk silent breakage downstream.
2. **Flag-composition matrix grows.** `--meta`, `--children`,
   `--parent`, `--fields`, `-q`, `-j`, `-e`, `--kind`, `--status` —
   that is a lot of pairwise combinations. The spec needs to list
   each interaction, not leave it to implementer judgement.
3. **Premature abstraction of graph traversal.** A "graph layer" can
   easily over-design before n0002 is ready to consume it. Hold the
   line at *just enough* primitive for v1 use cases; revisit when
   tree view actually lands.
4. **Cross-kind resolution edge cases.** A task pointing at a spec
   parent works only if `find` / resolution doesn't pre-filter by
   kind. Test cross-kind explicitly in the verification pass.

## Recommended next move

Cut the **spec task first**, assigned to the architect with
`owner: user`. Implementation tasks (2–6) stay in the backlog or in
this note until that lands.

## Reference material

- `n0002-layouts-tree-view-scoping.md` — sibling effort that consumes
  this data primitive.
- `s0012-cli-list-named-views.md` — the `--view` flag spec that this
  effort must compose with. Composition rules and matrix above.
- `src/artifacts_os/cli/commands/show.py` — current `show` dispatch.
- `src/artifacts_os/cli/commands/list.py` — current `list` dispatch.
- `src/artifacts_os/core/` — `ArtifactMeta`, store, registry; likely
  home for any graph helper.
- `~/workspace/open-station/` — prior art for graph traversal and
  metadata projection in the parent project.
