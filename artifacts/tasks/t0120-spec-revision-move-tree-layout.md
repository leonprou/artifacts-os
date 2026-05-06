---
kind: task
id: t0120
name: spec-revision-move-tree-layout
type: spec
status: done
assignee: architect
owner: user
parent: "[[t0114-feat-tree-layout-for-art]]"
created: 2026-05-06
started: 2026-05-06
artifacts:
  - "[[openstation/specs/s0022-tree-layout]]"
completed: 2026-05-06
---

# Spec-Revision: Move Tree Layout Config Out Of Kind Files Into Artifacts.Yaml

## User story

As an artifacts-os user managing layout configuration, I want
all layout settings to live in `artifacts.yaml` (alongside my
other views) — not on individual kind JSON files. Kinds describe
data shape; presentation is mine to configure.

## Origin

User pivot, 2026-05-06, after live review of the as-shipped
tree layout. Captured in [[n0002-layouts-tree-view-scoping]]
§ "Update — 2026-05-06".

> "Layout shouldn't live in the kind file. It should be defined
> in `artifacts.yaml` views — as a default view for task."

This task **revises** [[s0022-tree-layout]]. It is not a new
spec — it's a delta against the approved one, plus the migration
plan for already-shipped work.

## Scope

The user-facing outcome is unchanged:

- `art ls --kind task` shows hierarchy by default on this vault.
- `--layout table` opts out.
- `-q` / `-j` carve out unchanged.

What changes is **where the configuration lives** and **what the
resolution chain looks like**.

## Requirements

The architect must revise s0022 (or supersede with a new spec)
to answer:

1. **Remove the kind-file layer.** `x-layouts` on kind JSON is
   no longer the home for layout config. Decide: delete the
   block entirely, or keep a narrower form (e.g. just the
   `parent_field` declaration) for data-shape reasons. Justify.
2. **Define the `artifacts.yaml` mechanism.** The user's framing
   was *"a default view for task"*. Resolve:
   - Does `views.default_layouts: { task: tree }` become
     authoritative (current settings layer wins, kind layer
     deleted)?
   - Or does a saved view earn a "default per kind" marker
     (e.g. `views.tasks-default: { kind: task, layout: tree,
     default: true }`)?
   - Or is there a third design? Pick one with rationale.
3. **Re-derive the resolution chain.** With the kind slot
   removed, what's the new precedence? The current chain is
   `flag > view > settings.default_layouts > kind > implicit`.
   At minimum the `kind` link disappears. Confirm the rest.
4. **Where does `parent_field` live?** Today the kind file
   declares both *whether the kind is a tree* and *which field
   carries the upward pointer*. If `x-layouts` is removed, the
   `parent_field` must move somewhere — either into the
   `artifacts.yaml` view config (less natural — it's a data
   property, not a presentation choice) or stays on the kind
   under a different key (e.g. `x-hierarchy`). Pick.
5. **Migration plan for shipped work.** Specify what each of
   t0115, t0117 must change. Decide whether they get edited
   in place or reverted and re-cut. The PM uses this section
   verbatim to queue the next round of implementation tasks.
6. **Backward-compatibility statement.** No artifacts-os user
   has the `x-layouts` block on a custom kind yet (this shipped
   today), so we have a free hand — but state explicitly that
   the change is breaking and document the migration any
   downstream user would need.
7. **Docs-task respec.** t0118 was rejected because it
   documented the pre-pivot design. Specify the new doc surface:
   which files, which examples, where users land when they ask
   "how do I configure layout?".

## Verification

- [x] Spec revision lands at
      `artifacts/specs/s0022-tree-layout.md` (in-place update,
      with a "Revision History" section) **or** at a new
      `s00NN-...md` that supersedes s0022 (with s0022 marked
      `superseded`). Architect picks the form.
- [x] Kind-file layer decision recorded with rationale (delete
      `x-layouts` entirely vs. keep a narrower form).
- [x] `artifacts.yaml` mechanism specified — exact YAML shape,
      single worked example.
- [x] Resolution chain re-derived; new precedence documented.
- [x] `parent_field` placement decided.
- [x] Migration plan section names every shipped artifact that
      changes (t0115's `task.json`, t0117's `resolve_layout`
      and reserved-flag list, etc.) and what each needs.
- [x] Backward-compat statement included.
- [x] Docs surface re-scoped — file list and per-file scope
      sufficient for a docs sub-task to be cut from it.

## Verification Report

*Verified: 2026-05-06 (owner: user — approval relayed via PM)*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec revision form | PASS | In-place revision of s0022 (kept ID); §0 Revision Notice + §16 Decision Log row added. |
| 2 | Kind-file layer decision | PASS | §11 — `x-layouts` deleted entirely; rationale §11.3 (kind-side slot for layout-coupled datum reintroduces the coupling the user removed). |
| 3 | `artifacts.yaml` mechanism | PASS | §3, §10 — `default_layouts: dict[str, LayoutConfig]`; string-shorthand + object-form (object required when `layout: tree`); symmetric to `default_views`. |
| 4 | Resolution chain re-derived | PASS | §8.2 — 4 rungs: `--layout` > `view.layout` > `default_layouts[<kind>].layout` > implicit `"table"`; parallel chain for `parent_field`. |
| 5 | `parent_field` placement | PASS | §3.3 — on layout config object (`default_layouts[<kind>].parent_field` / `view.parent_field`), not on the kind. |
| 6 | Migration plan | PASS | §13 lists 7 sub-tasks (13.1–13.7) with file-level diffs for t0115/t0116/t0117 reverts and re-cut docs/verify. |
| 7 | Backward-compat statement | PASS | §15 row 1 — breaking change documented; no external users have `x-layouts` (shipped today); migration narrative included. |
| 8 | Docs surface re-scoped | PASS | §13.6 lists files and per-file scope (settings.md, adding-a-kind.md, views/README.md, cli/README.md, artifacts-os skill). |

### Summary

8 passed, 0 failed. Migration plan (§13) is the verbatim handle
the PM uses to cut the next round of tasks.

## Notes for the architect

- This is the user's call, not a debate. Don't relitigate the
  "kind file vs. settings" trade-off; the user has chosen
  `artifacts.yaml`. Your job is to make the design clean given
  that choice.
- The renderer (t0116) is layout-mechanism-agnostic and should
  not need changes. Confirm this.
- The shipped behaviour (`art ls --kind task` → tree) must
  survive the migration. The verification target on this vault
  (§6.5 of the original spec) is the contract; the way we get
  there is what changes.

## Progress

### 2026-05-06 — architect
> time: 23:00

Revised s0022 in place: §0 Revision Notice, rewrote §3 (artifacts.yaml mechanism), §4.3, §5.5, §8.2-§8.5, §10, §11, §13, §15 row 1, §16. Decisions: x-layouts deleted entirely (no x-hierarchy retained); default_layouts becomes dict[str, LayoutConfig] with string-form shorthand; resolution chain shrinks to 4 rungs; parent_field lives on the layout config object; property-existence check moves to CLI-resolve; render_tree.parent_field becomes required. Migration plan in §13 names 7 sub-tasks (13.1-13.7) with explicit file-level diffs for t0115/t0116/t0117 reverts and re-cut docs/verification.

## Findings

Revised [[openstation/specs/s0022-tree-layout]] **in place** (kept
the spec ID; added §0 "Revision Notice — 2026-05-06" and a new
"Decided (revision 2026-05-06)" row in §16; rewrote §3, §4.3, §5.5,
§8.2–§8.5, §10, §11, §13, §15 row 1; left §1, §2, §4 (excl. 4.3),
§5 (excl. 5.5), §6, §7, §9, §12, §14 untouched). Cross-refs from
t0114, t0115, t0116, t0117, t0118 stay valid; that's why I picked
in-place over a supersede.

### Decisions

1. **Kind-file `x-layouts` deleted entirely** — not narrowed to
   `x-hierarchy.parent_field`. Rationale §11.3: a kind-side slot
   for a layout-coupled datum reintroduces the coupling the user
   removed. `parent_field` is read by exactly one layout (tree),
   which is the literal definition of layout config.
2. **`artifacts.yaml` mechanism — `default_layouts` as
   `dict[str, LayoutConfig]`** with string-form shorthand for
   layouts that take no config. Object form required when
   `layout: tree` (must carry `parent_field`). Picked over (a)
   string-only `default_layouts` (can't carry `parent_field`)
   and (b) "default-marker on a saved view" (forces a view name
   on users who don't want one). Symmetric to existing
   `default_views: dict[str, str]`; one new sibling top-level key.
3. **Resolution chain — 4 rungs**: explicit `--layout` > `view.layout`
   > `default_layouts[<kind>].layout` > implicit `"table"`.
   Plus a parallel sibling chain for `parent_field` (view >
   `default_layouts[<kind>]`) so `--layout tree` ad-hoc still
   works against a vault-configured kind. Failure surface is
   ValidationError exit 2, never silent fall-through.
4. **`parent_field` placement — on the layout config object**
   (`default_layouts[<kind>].parent_field` or `view.parent_field`),
   not on the kind. Rationale §3.3.
5. **Property-existence check moves from registry-load to
   CLI-resolve** (§3.6). Renderer and registry both stay
   presentation-agnostic; the CLI is the only caller that has
   both schema and layout choice in hand.
6. **`render_tree(parent_field=...)` becomes required** (no
   kind_def fallback). Renderer is mechanism-agnostic — it
   accepts the resolved parent-field name from the CLI.
7. **In-place revision form** chosen over supersede; Revision
   History captured in §0 + a separate row in §16's Decision Log.

### Migration plan (verbatim handle for the PM)

§13 of the spec lists seven sub-tasks the PM cuts next:

| § | Title | Type | Depends |
|---|-------|------|---------|
| 13.1 | `revert-x-layouts-from-kind-schema` | implementation | — |
| 13.2 | `make-render-tree-parent-field-required` | implementation | — |
| 13.3 | `extend-views-models-for-layout-config` | implementation | — |
| 13.4 | `rewire-cli-resolve-layout-for-settings-only` (bundles 13.5) | implementation | 13.1, 13.2, 13.3 |
| 13.5 | vault-config migration — adds `default_layouts.task` to `artifacts.yaml` | (folded into 13.4) | — |
| 13.6 | `document-tree-layout-revised` (re-cut t0118) | documentation | 13.4 |
| 13.7 | `verify-tree-layout-revised` (re-run t0119) | feature/verification | 13.6 |

13.1, 13.2, 13.3 are independent and parallel-startable. 13.4 joins
them. 13.5 must ship in 13.4's diff (otherwise tree disappears on
this vault between 13.1 and 13.4). 13.6 follows 13.4. 13.7 closes
out the parent t0114.

### What did not change

- Renderer algorithm (§4–§7, §9), `compute_tree`, `TreeNote`, the
  `LAYOUTS` registry, `Registry.exists_stem`, `unwrap_wikilink`.
- `-q` / `-j` carve-outs (§8.4), `--fields` interaction (§9),
  cycle policy (§6.3), filtered-slice promotion (§7).
- `x-columns` (§11.2). Only `x-layouts` is removed kind-side.
- The user-facing outcome (§2, §6.5).

### Files modified

- `openstation/specs/s0022-tree-layout.md` — in-place revision
  per above. Frontmatter gains `revised: 2026-05-06`.
- `openstation/tasks/t0120-spec-revision-move-tree-layout.md` —
  this file (artifacts list + Findings + Progress).

No source code touched in this task — implementation deltas land
in the §13 sub-tasks.

## Downstream

- The PM should cut the seven §13 sub-tasks under parent t0114.
  Suggested titles and dependency shape are above; type and
  assignee are listed in each §13.x sub-section.
- t0118 should be **left rejected**; do not reopen it. The
  re-cut documentation task per §13.6 has a different scope
  (removes content t0118 added rather than revising it).
- t0114's verification list still passes once 13.7 lands; no
  changes to t0114's checklist are required by this revision.
- A future `--parent-field` CLI flag is mentioned in §8.2 as a
  possible future enhancement (rung 0 of the parent-field
  sibling chain). Not in scope for the migration; flag if user
  research surfaces ad-hoc tree-on-arbitrary-kind workflows.
