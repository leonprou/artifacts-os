---
kind: task
id: t0125
name: document-tree-layout-revised
type: documentation
status: review
assignee: author
owner: author
parent: "[[t0114-feat-tree-layout-for-art]]"
depends_on:
  - "[[t0124-rewire-cli-resolve-layout-for]]"
created: 2026-05-06
started: 2026-05-07
---

# Document-Tree-Layout-Revised

## User story

Document the revised tree layout configuration — `artifacts.yaml`
is the single home for layout config, `parent_field` lives on
the layout config object, and the resolution chain is 4 rungs.
Replaces the rejected t0118.

## Context

- Parent: [[t0114-feat-tree-layout-for-art]].
- Depends on: t0124 (CLI wiring landed; behaviour matches docs).
- Spec contract: [[s0022-tree-layout]] §13.6 (file-level
  per-doc scope).
- Replaces rejected [[t0118-document-tree-layout]]. Original
  preserved in git history (`r0136`).

## Requirements

Apply spec §13.6 exactly. Per-file scope:

1. **`docs/settings.md`** — new "Layout selection" subsection.
   Document `default_layouts` (string-form and object-form,
   parent_field requirement when `layout: tree`),
   `view.layout` + `view.parent_field`. Worked examples:
   - vault wants flat tasks: `default_layouts.task: table`
   - vault wants tree tasks: `default_layouts.task:
     { layout: tree, parent_field: parent }`
   Resolution-chain summary (4 rungs per §8.2) including the
   parent-field sibling chain. Link to `s0022-tree-layout`
   once.
2. **`docs/adding-a-kind.md`** — **remove** the `x-layouts`
   section that t0118 added. Replace with a one-paragraph
   note: "Layout configuration lives in `artifacts.yaml`,
   not `kind.json`. See [docs/settings.md](settings.md#layout-selection)."
   Remove `x-layouts` from the kind.json reference table.
3. **`src/artifacts_os/views/README.md`** — keep the
   `Layout`, `LAYOUTS`, `render_tree`, `compute_tree`,
   `TreeNote` API descriptions. **Remove** the `"layouts"`
   row from the `KindDef.meta` convention table (it no
   longer exists). Update the settings-extension subsection:
   `view.layout`, `view.parent_field`, `default_layouts:
   dict[str, LayoutConfig]`. Link to `s0022-tree-layout` once.
4. **`src/artifacts_os/cli/README.md`** — keep `--layout` in
   the flag table. Rewrite the resolution-chain section
   (4 rungs, not 5). Add the parent-field sibling chain.
   Worked example: pivot the "default tree on tasks" source
   from `x-layouts` to `default_layouts.task` in
   `artifacts.yaml`. Remove every reference to kind-side
   layout config.
5. **`src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`**
   — one-paragraph adjustment: "Tree layout for tasks is
   configured in `artifacts.yaml`'s `default_layouts`.
   Override per-invocation with `--layout table`. `-q` / `-j`
   are unaffected."

Cross-link consistency: every doc that mentions the new
behaviour links to `s0022-tree-layout` exactly once. Spec
internals (algorithm, cycle policy) defer to §6 / §8.

## Verification

- [ ] `docs/settings.md` covers `default_layouts` and
      `view.layout` + `view.parent_field` with both worked
      examples; resolution-chain summary present.
- [ ] `docs/adding-a-kind.md` no longer contains `x-layouts`;
      replaced by the redirect paragraph.
- [ ] `views/README.md` no longer has the `"layouts"` row
      in the meta convention table; settings-extension
      subsection updated.
- [ ] `cli/README.md` covers the 4-rung chain and the
      parent-field sibling chain; no kind-side references.
- [ ] `artifacts-os` skill carries the one-paragraph
      adjustment.
- [ ] Each updated doc links to `s0022-tree-layout` exactly
      once.
- [ ] No doc duplicates spec internals (algorithm, cycle
      policy).

## Progress

### 2026-05-07 — author
> time: 18:07

Documented the revised tree-layout configuration across all five
surfaces (settings.md, adding-a-kind.md, views/README.md,
cli/README.md, SKILL.md). Removed every kind-side layout
reference, added the 4-rung resolution chain and parent-field
sibling chain to settings.md and cli/README.md, retyped
`default_layouts` as `dict[str, LayoutConfig]` in
views/README.md, renamed the settings.md heading to "Layout
selection" so the mandated `#layout-selection` anchor resolves.
Each doc links to `s0022-tree-layout` exactly once
(adding-a-kind.md redirects to settings.md instead).

## Findings

Documented the revised tree-layout configuration across all five
required surfaces; `artifacts.yaml` is now the single home for
layout config in every doc.

- **`docs/settings.md`** — replaced the prior `Layout selection
  — default_layouts and view.layout` subsection with a clean
  `Layout selection`. Documents the string-form / object-form
  `default_layouts` entry (with the parent_field requirement
  table), `view.layout` + `view.parent_field`, both worked
  examples (flat tasks via shorthand, tree tasks via object
  form), and the 4-rung resolution chain plus the parent-field
  sibling chain. The single s0022 link sits at the end of the
  section.
- **`docs/adding-a-kind.md`** — dropped the `x-layouts` row from
  the `kind.json` reference table and replaced the entire
  Layouts subsection with the spec-mandated redirect paragraph.
  Anchor target is `settings.md#layout-selection`.
- **`src/artifacts_os/views/README.md`** — removed `"layouts"`
  from the `KindDef.meta` convention table (now two keys), kept
  every `Layout` / `LAYOUTS` / `render_tree` / `compute_tree` /
  `TreeNote` API description, updated the `tree` registry row
  to "the caller (CLI) supplies `parent_field`", added a new
  `LayoutConfig` subsection, expanded `ViewConfig` to cover
  `parent_field`, retyped `default_layouts` as
  `dict[str, LayoutConfig]`, and updated the surrounding prose
  to mention the third top-level key. Single s0022 link in the
  Layouts section preserved.
- **`src/artifacts_os/cli/README.md`** — flag-table help text
  pivoted from "auto-detects from kind" to "falls through to
  `default_layouts` in `artifacts.yaml`". Rewrote the resolution
  chain to 4 rungs, added the parent-field sibling chain, and
  rewrote the worked example so the source of "default tree on
  tasks" is `default_layouts.task` in `artifacts.yaml`. The
  spec-side error block (`exits 2 — layout 'tree' requires
  parent_field`) replaces the old "force tree on a kind that
  declares parent_field" example.
- **`SKILL.md`** — replaced the tree-layout paragraph with the
  exact wording from the requirements. Reference to
  `s0022-tree-layout` retained as a textual citation.

### Heading anchor

Renamed the `docs/settings.md` heading from `Layout selection
— default_layouts and view.layout` to `Layout selection` so the
mandated redirect anchor `#layout-selection` resolves; the only
other consumer of the anchor (`views/README.md`) was updated in
the same pass.

### Cross-link consistency

`grep -c s0022-tree-layout` per touched doc:

| Doc | Count |
|-----|-------|
| `docs/settings.md` | 1 |
| `docs/adding-a-kind.md` | 0 (redirects to settings.md) |
| `src/artifacts_os/views/README.md` | 1 |
| `src/artifacts_os/cli/README.md` | 1 |
| `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` | 1 |

`adding-a-kind.md` is intentionally 0 — the doc no longer
discusses the new behaviour beyond the redirect.

### Algorithm / cycle policy

No doc duplicates spec §6 internals. Each doc that needs to gesture
at "the full algorithm (sibling order, cycle handling, orphan
annotations)" links to `s0022-tree-layout` §§ 6, 8 instead of
restating the contract.
