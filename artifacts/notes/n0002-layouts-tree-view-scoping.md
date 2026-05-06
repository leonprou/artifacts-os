---
created: 2026-05-01
id: n0002
kind: note
name: layouts-tree-view-scoping
type: planning
---

# Layouts: Tree View Scoping

> PM scoping note from a brainstorm session. Captures requirements, work
> breakdown, and risks at a level a spec writer can consume. No
> architectural decisions — those land in the spec.

## Origin

Openstation now ships a tree view in `os ls --kind task` (parents and
children rendered together using `└─` characters). artifacts-os does not
— `art ls --kind task` emits a flat table even though `parent`
wikilinks already exist on tasks (see `t0042`–`t0046`).

Initial framing was "patch `render_table` to draw `└─`". The brainstorm
reframed it: tree is not a table feature, it is a sibling **layout**.
The `views/` module today only knows one layout (table). Adding tree
forces a small abstraction — and that abstraction is what unlocks
future layouts (board, timeline, etc.) without another retrofit.

## User-facing outcome

`art ls` shows hierarchy when the underlying data has it. That is the
only thing a user sees. Everything else is internal scaffolding.

## Development areas touched

| Area              | What changes                                                | Risk profile                                       |
|-------------------|-------------------------------------------------------------|----------------------------------------------------|
| Spec / design     | New abstraction for "how a kind is rendered"                | Low risk; blocks everything else                   |
| Data (kinds)      | Kind files declare supported layouts and their default      | Touches every existing `kinds/*.json` — migration  |
| Views (rendering) | Add tree renderer alongside the existing table renderer     | Self-contained, well-scoped                       |
| CLI               | Layout selection, resolution chain, opt-out flag           | Touches `art ls`; interacts with shipped `--fields` |
| Docs              | Settings guide, CLI README, views README, skill            | Follows behaviour                                  |
| Tests             | New layout coverage + no-regression on flat output         | Standard                                           |

`tui/` is touched in theory but is a stub today — out of scope unless
the architect flags a forced design choice.

## Work breakdown

Six pieces, sequenced. Parent task ties them together.

1. **Spec** — *architect, owner: user.* Defines the layout abstraction
   (what a layout is, how kinds opt in, CLI surface, interaction with
   `ViewConfig` saved-queries, `x-columns` migration story). v1 scope:
   **table + tree only** — no speculation about board/timeline. Output
   is a contract for the next four tasks.
2. **Kind schema + migration** — *developer.* Apply the spec's schema
   shape to existing `kinds/*.json`. Decide and execute the
   `x-columns` compatibility path.
3. **Tree renderer in views** — *developer.* Implement the renderer
   from the spec, no CLI knowledge. Ships with its own tests.
4. **CLI wiring** — *developer.* Layout resolution chain, flag
   surface, `-q`/`-j` carve-outs. Depends on (3). Tests cover real
   `art ls` output.
5. **Documentation** — *author / technical-writer.* Settings doc, CLI
   README, views README, `artifacts-os` skill. Single agent, single
   task.
6. **Verification pass** — *user.* End-to-end on the artifacts-os
   vault itself: `art ls --kind task` shows `t0042` under `t0036` and
   `t0043`–`t0046` under `t0041`.

Dependency shape: `1 → {2, 3} → 4 → 5 → 6`. Tasks 2 and 3 can run in
parallel once the spec lands.

## Requirements

Functional:

- Hierarchy is visible by default for any kind whose artifacts use a
  parent-style relationship.
- `-q` and `-j` output unchanged. Existing `--fields` workflows for
  non-hierarchical kinds keep working.
- Opt-out exists for users who want flat output on a hierarchical
  kind.
- Behaviour is driven by kind definitions, not hardcoded to `task`.

Non-functional:

- The new abstraction must accommodate at least one *imagined* second
  layout without redesign — proof that we are not just renaming
  `render_table`.
- Renderer stays in `views/`; data lives in `kinds/`; selection lives
  in `cli/`. The module DAG is preserved.
- The settings layer (`ViewConfig` / `ViewsConfig` saved-queries) is
  not broken by the change.

## Update — 2026-05-06: design pivot post-shipping

After t0115/t0116/t0117 shipped, the user reviewed the live
behaviour (`art ls --kind task`) and pushed back on a load-bearing
choice in s0022:

> "Layout shouldn't live in the kind file. It should be defined
> in `artifacts.yaml` views — as a default view for task."

User-level intent (no implementation prescribed):

- **Kind files stay layout-agnostic.** The `x-layouts` block on
  `task.json` should not exist; kinds describe data shape, not
  presentation.
- **`artifacts.yaml` is the single home for layout config.** The
  user expects to manage layout in their settings file alongside
  saved views, not by editing kind JSON.
- **"Default view for task"** is the framing the user used.
  Whether that means (a) `views.default_layouts` becomes the
  authoritative kind-default mechanism, or (b) a saved view per
  kind earns a "default" marker, is the architect's call. The
  intent is that one of the two (or a unified design) replaces
  the kind-side declaration.
- **Resolution chain shrinks.** With the kind layer removed, the
  current chain `flag > view > settings > kind > implicit` loses
  the `kind` slot. The architect should re-derive the precedence
  with that constraint.

What this implies for already-shipped work (architect to confirm,
not PM):

- t0115 (`x-layouts` on `task.json`) is reverted — partly or
  fully — depending on whether registry validation still has a
  role.
- t0117 (CLI resolution chain) drops the kind layer.
- t0118 (docs) is rejected — re-cut after the spec revision.
- t0119 (vault verification) target shape is unchanged from the
  user's POV; only the configuration mechanism that produced it
  shifts.

This pivot is filed as a spec-revision task assigned to the
architect; tasks follow once the revised contract lands.

## Open questions for the spec

> Intent, not contract. These belong to the architect to resolve in
> the spec — listed here so they don't get lost and so the spec scope
> is unambiguous before the task is cut.

Tree traversal is the dominant unknown. A "generic tree layout" only
earns its name if the renderer is not hardcoded to `parent`. The
spec needs to answer, at minimum:

- **Where is the hierarchy declared?** Today only `task` has a
  `parent` wikilink. Other kinds may use a different field name, or
  none. The kind definition is the natural place to declare "this
  kind forms a tree, here is the field that points up" — but the
  spec decides the exact shape and whether multiple traversal
  sources (e.g. parent + depends_on) are allowed in v1. Per the
  earlier scoping decision: **parent-style only for v1**, but the
  declaration must not preclude a second source later.
- **What does a root look like?** Artifacts with no parent? Parent
  pointing outside the current `--kind` slice? Parent pointing to a
  missing/unresolved artifact? Each case has a different user
  expectation (top-level vs. orphan vs. broken link) and the spec
  must spell out the rendering contract.
- **What sibling order does the user see?** Insertion order, sort
  by id, sort by the active `--sort` flag, or whatever the kind
  declares as default? Whichever it is, the answer must be
  deterministic and not surprise users who today rely on flat
  list ordering.
- **Cycles and orphans.** A vault is user-edited markdown — cycles
  and dangling parents will happen. The spec must decide whether
  the renderer detects and breaks them visibly (so the user can
  fix the data) or silently flattens them. Failing loudly is
  preferred but is the architect's call.
- **Where does traversal live?** Pure renderer concern in `views/`
  (renderer takes a flat list and infers structure), or a data-side
  concern in `core/` (a tree-shaped query result that views just
  draws)? The module DAG (`core → views → cli`) constrains this and
  the answer ripples into `--fields`, `-q`, and `-j` semantics.
- **Filtered slices.** When `art ls --kind task --status ready`
  hides a parent but keeps a child, what does the user see? Promote
  the child to a root? Render a placeholder? Skip the layout and
  fall back to flat? Pick one and document it.

The spec doesn't have to answer these in depth — but it must answer
them clearly enough that the kind-schema task (#2) and the renderer
task (#3) can proceed in parallel without re-litigating contract.

## Out of scope

- TUI integration.
- A second concrete layout beyond tree (board, timeline, card, etc.).
- Hierarchical `art show` (rendering an artifact with its subtree
  underneath). Separate concern.
- Layouts driven by `depends_on`. Tree-of-parents only for now.

## Risks

1. **Migration blast radius.** If the spec changes the kind-file
   shape, all existing kind files change — and any vault that has
   already extended kinds in the wild does too. Watch for whether the
   spec preserves a compatibility shim or breaks cleanly.
2. **`--fields` collision.** `--fields` was just shipped for the
   table case (t0036 family). Under a multi-layout world its meaning
   narrows. Worth flagging so the developer does not break working
   flows.
3. **Scope creep into "let's design four layouts."** The cheapest
   way to fail this is to over-design the abstraction. Hold the line
   at tree-as-first-concrete-renderer; the abstraction earns its keep
   with one user, not four hypothetical ones.
4. **Spec-to-impl handoff sequencing.** Tasks 2 and 3 want to start in
   parallel — that only works if the spec is unambiguous on the
   kind-schema shape and the renderer signature. Budget one round of
   spec revision after the first implementer reads it.

## Recommended next move

When ready to leave brainstorm mode, the first task to cut is the
**spec**, assigned to the architect with `owner: user`. Tasks 2–6 stay
in the backlog (or in this note) until that lands. Writing them now
would prematurely commit to architectural decisions that are not ours
to make.

## Reference material

- `~/workspace/open-station/src/openstation/tasks.py` —
  `group_tasks_for_display`, `_indent_prefix` (algorithmic prior art).
- `~/workspace/open-station/src/openstation/ui.py` —
  `rich_task_table`, `_rich_task_table_custom` (tree-prefix
  application).
- `src/artifacts_os/views/_views.py` — current `render_table`.
- `src/artifacts_os/views/models.py` — existing `ViewConfig` /
  `ViewsConfig` (saved-query layer; vocabulary collision risk).
- `src/artifacts_os/cli/commands/list.py` — current list dispatch.
- `artifacts/kinds/task.json` — current `x-columns` shape; affected
  by the migration.