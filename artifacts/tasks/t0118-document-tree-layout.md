---
kind: task
id: t0118
name: document-tree-layout
type: documentation
status: rejected
assignee: author
owner: author
parent: "[[t0114-feat-tree-layout-for-art]]"
depends_on:
  - "[[t0117-wire-layout-flag-in-cli]]"
created: 2026-05-06
started: 2026-05-06
---

# Document Tree Layout

## User story

As a user discovering the new tree layout, I want documentation
that tells me (a) it exists, (b) how to opt out, (c) how to
declare it on my own kinds — without reading the spec.

## Context

- Parent: [[t0114-feat-tree-layout-for-art]].
- Depends on the CLI wiring task being `done` so the documented
  behaviour is reality.
- Source of truth: [[s0022-tree-layout]]. Translate, don't
  duplicate.

## Requirements

Update the four user-facing docs that describe behaviour the
tree layout changes. Stay at user-task granularity — point
readers at the spec for design rationale.

1. `docs/settings.md` — document `views.default_layouts` and
   `view.layout` fields per spec §10. Worked example: setting
   the default to `table` for a kind that declares `tree`.
2. `docs/adding-a-kind.md` — document the `x-layouts` block per
   spec §3. Show the minimal opt-in (`default: "tree"`,
   `parent_field: "<field>"`).
3. `src/artifacts_os/views/README.md` — describe layouts as a
   first-class concept, list the two members (`table`,
   `tree`), describe how to register a third. Pull algorithm
   summary from spec §6 — reference §6 for full details.
4. `src/artifacts_os/cli/README.md` — document the `--layout`
   flag and the resolution chain (§8). Include a short
   example showing default-tree and the opt-out.
5. `artifacts-os` skill — add a one-paragraph "Tree layout"
   bullet under whichever section covers `art ls`. The skill
   is the agent-facing contract; keep it short.

Cross-link consistency: every doc that mentions the new
behaviour links to `s0022-tree-layout` once.

## Verification

- [ ] `docs/settings.md` covers `views.default_layouts` and
      `view.layout` with one worked example.
- [ ] `docs/adding-a-kind.md` covers `x-layouts` with the
      minimal opt-in example.
- [ ] `views/README.md` lists `table` and `tree` and explains
      the registry.
- [ ] `cli/README.md` covers `--layout` and the resolution
      chain.
- [ ] `artifacts-os` skill mentions tree layout as a behaviour
      of `art ls`.
- [ ] Each updated doc links to `s0022-tree-layout` exactly
      once.
- [ ] No doc duplicates spec internals (algorithm details,
      cycle policy text) — each defers to §6 / §8 of the spec.

## Findings

Updated all five user-facing docs that describe behaviour
touched by the tree layout. Each defers to
[[s0022-tree-layout]] for design rationale and links to it
exactly once.

**Per-doc summary:**

- `docs/settings.md` — added a "Layout selection —
  `default_layouts` and `view.layout`" subsection inside the
  existing Views Section. Documents both keys, lists validation
  behaviour, and includes a worked example for "vault wants
  flat tasks even though the kind declares `default: tree`".
- `docs/adding-a-kind.md` — added `x-layouts` to the
  `kind.json` reference table and a new "Layouts —
  `x-layouts`" section before the L1 catalogue. Minimal
  opt-in JSON shown verbatim with a key/required/purpose table.
- `src/artifacts_os/views/README.md` — extended the public-API
  block (added `Layout`, `LAYOUTS`, `render_tree`,
  `compute_tree`, `TreeNote`), added a `"layouts"` row to the
  `KindDef.meta` convention table, and added a "Layouts"
  section that names the two registry entries, contrasts
  what `tree` vs. `table` own, and shows how to register a
  third layout. Settings extension subsection updated with the
  new `view.layout` and `default_layouts` fields.
- `src/artifacts_os/cli/README.md` — added `--layout` to the
  list-command flag table, added a new "Layouts — `--layout`"
  subsection inside the `list` command with the resolution
  chain (5-rung table) and a default-tree-and-opt-out worked
  example. Also added `--layout` to the schema-derived
  static-flag collision list.
- `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`
  (the canonical skill — `.openstation/skills/artifacts-os/SKILL.md`
  is a symlink to it) — added a one-paragraph **Tree layout**
  note under `artifacts list` covering opt-out, force-on, and
  `-q` / `-j` carve-out.

**Design discipline:**

- No doc reproduces the traversal algorithm, cycle-break
  policy, four orphan/cycle annotations, or sort-per-level
  details from spec §§ 6, 8. Each just names the layouts and
  defers to the spec.
- The five docs link to `s0022-tree-layout` once each
  (verified by `grep -c`).
- Each link uses the appropriate relative path for its
  location in the tree.

## Downstream

- The `templates/agents/product-manager.md` and
  `agents/product-manager.md` shipped versions appeared in
  `git status` from earlier work and are unrelated to this
  task.
- A future board / timeline / matrix layout would slot in
  via `LAYOUTS["board"] = render_board`; the docs already
  describe that registration shape, but no follow-up task is
  required until such a layout is on the roadmap.

## Progress

- 2026-05-06 — Updated all five user-facing docs
  (`docs/settings.md`, `docs/adding-a-kind.md`,
  `src/artifacts_os/views/README.md`,
  `src/artifacts_os/cli/README.md`,
  `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`)
  to document the tree layout. Each links to
  `s0022-tree-layout` exactly once (verified) and defers spec
  internals to the spec. Transitioned to `review`.
