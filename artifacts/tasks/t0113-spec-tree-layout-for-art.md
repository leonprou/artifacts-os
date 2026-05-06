---
kind: task
id: t0113
name: spec-tree-layout-for-art
type: spec
status: done
assignee: architect
owner: user
created: 2026-05-06
started: 2026-05-06
artifacts:
  - "[[artifacts/specs/s0022-tree-layout]]"
completed: 2026-05-06
---

# Spec: Tree Layout For `art ls`

## User story

As an artifacts-os user listing a hierarchical kind
(`art ls --kind task`), I want to see parent/child relationships
rendered as a tree so the structure already encoded in my data is
visible without me passing flags or memorising field names.

The verification target on the artifacts-os vault itself is:
`art ls --kind task` shows `t0042` under `t0036` and `t0043`–`t0046`
under `t0041`.

## Context

Read `artifacts/notes/n0002-layouts-tree-view-scoping.md` first —
it captures origin, work breakdown, requirements, risks, and the
**Open questions for the spec** that this task must resolve. This
spec is item #1 of the breakdown and unblocks items #2–#6.

Reference prior art (read, don't copy):

- `~/workspace/open-station/src/openstation/tasks.py` —
  `group_tasks_for_display`, `_indent_prefix`.
- `~/workspace/open-station/src/openstation/ui.py` —
  `rich_task_table`, `_rich_task_table_custom`.
- `src/artifacts_os/views/_views.py` — current `render_table`.
- `src/artifacts_os/views/models.py` — `ViewConfig` /
  `ViewsConfig` (vocabulary collision risk).
- `src/artifacts_os/cli/commands/list.py` — current list dispatch.
- `artifacts/kinds/task.json` — current `x-columns` shape.

## Requirements

The spec must answer each of the following. The note's Open
Questions section is the input checklist; this list is the
contract for "spec complete".

1. **Layout abstraction** — Define what a "layout" is in the
   `views/` module: how table and tree coexist, what each owns,
   and how a kind selects its default. The abstraction must
   accommodate at least one *imagined* second layout (board,
   timeline, etc.) without redesign — but no second layout is
   designed in v1.
2. **Kind-level declaration** — Specify how a kind declares (a)
   that it forms a tree and (b) which field carries the upward
   pointer. v1 supports parent-style only; the declaration shape
   must not preclude future multi-source traversal.
3. **Root and orphan rendering** — Specify what the user sees for
   artifacts with no parent, parents outside the current
   `--kind` slice, and parents pointing to a missing/unresolved
   artifact. Each case has a distinct user expectation.
4. **Sibling order** — Specify the deterministic sibling order
   and how it interacts with the active `--sort` flag.
5. **Cycle and dangling-parent handling** — Specify whether the
   renderer fails loudly, breaks visibly, or silently flattens.
   Pick one and document it.
6. **Module placement** — Decide whether traversal is a pure
   renderer concern in `views/` or a data-side concern in
   `core/`. Justify against the module DAG
   (`core → views → cli`) and against `--fields`, `-q`, `-j`
   semantics.
7. **Filtered slices** — Specify what happens when a filter
   (`--status`, etc.) hides a parent but keeps a child. Pick
   one of: promote child to root, render placeholder, fall back
   to flat. Document.
8. **CLI surface** — Specify the layout-selection flag
   (opt-out for users who want flat output on a hierarchical
   kind) and the resolution chain (kind default → settings →
   flag). `-q` and `-j` output must be unchanged.
9. **`--fields` interaction** — Spell out what `--fields` means
   under tree layout. The `--fields` workflow shipped for the
   table case (t0036 family) must keep working for
   non-hierarchical kinds.
10. **Settings layer compatibility** — Specify how `ViewConfig` /
    `ViewsConfig` saved-queries interact with layouts. The note
    flags this as a vocabulary-collision risk.
11. **`x-columns` migration** — Decide and document the
    compatibility path for existing `kinds/*.json` `x-columns`
    declarations. Preserve a shim or break cleanly — pick one,
    state the rationale.
12. **Out-of-scope confirmations** — Carry forward from the note:
    TUI integration, second concrete layout beyond tree,
    hierarchical `art show`, and `depends_on`-driven layouts are
    explicitly excluded from v1.

## Verification

- [x] Spec doc lands at `artifacts/specs/sNNNN-tree-layout.md`,
      status `approved`.
- [x] Layout abstraction defined; coexistence of table and tree
      explained; second-layout extensibility argued without
      designing one.
- [x] Kind-level tree declaration specified with field-name
      contract and forward-compat statement.
- [x] Root, orphan, and missing-parent rendering each specified
      with a worked example.
- [x] Sibling order rule specified; interaction with `--sort`
      stated.
- [x] Cycle and dangling-parent policy specified; loud-fail vs
      visible-break vs silent-flatten chosen with rationale.
- [x] Traversal module placement decided; module DAG argument
      written.
- [x] Filtered-slice behaviour specified with worked example.
- [x] CLI surface specified — opt-out flag, resolution chain,
      `-q`/`-j` unchanged.
- [x] `--fields` semantics under tree layout specified;
      non-hierarchical-kind compatibility confirmed.
- [x] `ViewConfig` / `ViewsConfig` interaction specified.
- [x] `x-columns` migration path specified.
- [x] Out-of-scope items listed verbatim from n0002.

## Verification Report

*Verified: 2026-05-06 (owner: user — approval relayed via PM)*

| #  | Criterion | Result | Evidence |
|----|-----------|--------|----------|
| 1  | Spec doc at approved status | PASS | `artifacts/specs/s0022-tree-layout.md`; frontmatter `status: approved`, `task: [[t0113-...]]`. |
| 2  | Layout abstraction defined | PASS | §4 defines `Layout = Callable[(items, columns, kind_def), Renderable]` and `views.LAYOUTS` registry; §5.4 argues second-layout extensibility without designing one. |
| 3  | Kind-level tree declaration | PASS | §3 specifies additive `x-layouts` block with `parent_field` contract; v2 multi-source extension reserved. |
| 4  | Root, orphan, missing-parent rendering | PASS | §6.4 worked examples for each case; §6.5 vault-target example. |
| 5  | Sibling order rule | PASS | §6.2 rule + §8 `--sort` interaction. |
| 6  | Cycle / dangling-parent policy | PASS | §6.3 chooses visible-break with `↻ cycle` + stderr warning; rationale includes loud-fail and silent-flatten rejections. |
| 7  | Traversal module placement | PASS | §5.1 places traversal in `views/`; module-DAG argument written. |
| 8  | Filtered-slice behaviour | PASS | §7 promotes child to root with `↑[parent: <ref>]`; worked example included. |
| 9  | CLI surface | PASS | §8 `--layout` flag, resolution chain explicit > view > settings > kind > implicit; `-q`/`-j` carve-out documented. |
| 10 | `--fields` semantics | PASS | §9 spells out tree layout `--fields` interaction; non-hierarchical kinds unchanged. |
| 11 | `ViewConfig` / `ViewsConfig` interaction | PASS | §10 adds `ViewConfig.layout` and `ViewsConfig.default_layouts`; collision risk addressed. |
| 12 | `x-columns` migration path | PASS | §11 keeps `x-columns` unchanged; only `task.json` touched in task #2. |
| 13 | Out-of-scope items | PASS | §12 lists TUI, second concrete layout, hierarchical `art show`, `depends_on` — verbatim from n0002. |

### Summary

13 passed, 0 failed. Spec is sufficient for parallel-start of
implementation tasks #2 (kind schema) and #3 (tree renderer);
§3, §5, and §8 are the documented interlocks.

## Notes for the architect

- v1 scope is **table + tree only**. Resist designing a third
  layout to "validate the abstraction" — the abstraction earns
  its keep with one new user, not four hypothetical ones (n0002
  Risk #3).
- The downstream implementation tasks (#2 kind schema, #3
  renderer, #4 CLI wiring) are designed to run #2 and #3 in
  parallel after this spec lands. Budget for unambiguity on the
  kind-schema shape and the renderer signature so that parallel
  start is real, not aspirational (n0002 Risk #4).
- `tui/` is a stub; out of scope unless a forced design choice
  forces a flag.

## Progress

### 2026-05-06 — architect
> time: 12:40

Drafted spec `s0022-tree-layout` under `artifacts/specs/`.
Resolves all 12 task requirements + the 6 n0002 Open Questions
(mapping in §15). Key load-bearing decisions:

- Layout = `Callable[(items, columns, kind_def), Renderable]`
  registered in `views.LAYOUTS`.
- Tree returns `rich.Table` (glyph prefix on first column);
  not `rich.Tree` — preserves status colors and column model.
- Traversal lives in `views/`. Module-DAG argument: `-q`/`-j`
  consume flat lists; `--fields` is a `views/` concept.
- `x-layouts` is **additive** on the kind schema; `x-columns`
  preserved unchanged. Only `task.json` is touched in task #2.
- Cycles → visible-break with `↻ cycle` + one stderr warning.
- Filtered-out parent → child promoted to root with
  `↑[parent: <ref>]` Case B annotation.
- `--layout` long-form flag, no short form. Resolution chain:
  explicit > view > settings.default_layouts >
  kind.x-layouts.default > implicit "table".
- `-q`/`-j` carve out: layout selection skipped; sort still
  applies on flat data.
- `ViewConfig.layout: str | None` and
  `ViewsConfig.default_layouts: dict[str, str]` added —
  vocabulary-collision risk addressed by namespace separation.

Findings + Downstream sections appended below. Spec set to
`status: approved` per the task verification rubric. Task
moved to `review` for owner verification.

## Findings

Spec landed at `artifacts/specs/s0022-tree-layout.md` with
`status: approved`. All 12 requirements answered; the n0002
Open Questions are mapped 1:1 in §15.

**Key decisions (load-bearing for downstream tasks):**

- **Layout = `Callable[(items, columns, kind_def), Renderable]`**
  registered in `views.LAYOUTS`. Two members in v1: `table`,
  `tree`. A future third slots into the registry without
  schema or CLI changes (§4, §5.4).
- **Kind declaration is additive `x-layouts`** —
  `{ default: "tree", tree: { parent_field: "parent" } }`. v1
  is parent-style only; the block name is reserved for a v2
  multi-source extension (§3). `x-columns` is **preserved
  unchanged** — no kind file other than `task.json` is
  touched in task #2 (§11).
- **Tree returns `rich.Table` (not `rich.Tree`).** The prefix
  is glyph-on-first-column, identical to open-station's prior
  art. This preserves status coloring, format strings, and
  the existing column model (§4.1, §9.2).
- **Traversal lives in `views/`.** Module-DAG argument: core
  stays a flat-discovery layer; `-q`/`-j` consume flat lists
  directly without touching `views/`; `--fields` is a `views/`
  concept already (§5.1).
- **Cycles → visible-break with `↻ cycle` annotation +
  one stderr warning.** Loud-fail rejected (blocks unrelated
  listing); silent-flatten rejected (hides corruption) (§6.3).
- **Filtered-slice behaviour: promote child to root with
  `↑[parent: <ref>]` annotation.** Honours the filter without
  leaking the hidden parent into the result (§7).
- **CLI: `--layout` long-form flag, no short form.**
  Resolution chain: explicit > view > settings.default_layouts
  > kind.x-layouts.default > implicit "table". `-q` and `-j`
  carve out — sort still applies, layout is skipped (§8).
- **Settings: `ViewConfig.layout: str | None` and
  `ViewsConfig.default_layouts: dict[str, str]`** are added,
  both optional. Vocabulary-collision risk addressed: `views`
  is the namespace, `layout` is a field within a view (§10).

**Parallel-start interlocks for tasks #2 and #3 (n0002 Risk #4):**

- Task #2 reads §3.1, §3.3, §3.4 for the kind-schema contract.
- Task #3 reads §5 (renderer signatures), §6 (algorithm), §9
  (prefix on first column).
- Their join is task #4 (CLI wiring), which reads §8 and §13.4.

**Worked examples include the verification target:** §6.5
shows the exact `t0036`/`t0042` and `t0041`/`t0043`–`t0046`
shape that task #6 verifies on the artifacts-os vault itself.

## Downstream

- **Task #2 (kind schema + migration)** — adds `x-layouts`
  block to `task.json`, validates at registry load, populates
  `meta["layouts"]`. Tests in §13.
- **Task #3 (tree renderer in `views/`)** — implements
  `compute_tree`, `render_tree`, `TreeNote`, `LAYOUTS`
  registry. Promotes `_unwrap_wikilink` to public and adds
  `Registry.exists_stem`. Tests in §13.
- **Task #4 (CLI wiring)** — adds `--layout` flag,
  `resolve_layout` helper, threads `sort_key` into
  `compute_tree`. Reserves `--layout` against
  `_RESERVED_FILTER_FLAG_NAMES`. Tests in §13.
- **Task #5 (documentation)** — updates `docs/settings.md`,
  `docs/adding-a-kind.md`, `views/README.md`, `cli/README.md`.
- **Task #6 (verification on artifacts-os vault)** — owner is
  user; runs `art ls --kind task` on this very vault and
  confirms §6.5's tree shape.

Tasks #2 and #3 can run in parallel; #4 depends on both.
