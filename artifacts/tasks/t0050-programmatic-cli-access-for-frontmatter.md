---
kind: task
id: t0050
name: programmatic-cli-access-for-frontmatter
type: feature
status: review
assignee: project-manager
owner: user
created: 2026-05-01
subtasks:
  - "[[t0051-spec-programmatic-cli-access-frontmatter]]"
  - "[[t0052-implement-programmatic-cli-access-frontmatter]]"
---

# Programmatic Cli Access For Frontmatter And Relationships

## Context

This task originates from a brainstorm captured in
[[n0003-programmatic-cli-access]] — read it first. n0003 contains
the full mental model (artifacts-as-graph, identity vs predicate,
layered `list` flags), the composition matrix that governs
interaction with `--view`, the rejected flag shapes, worked
use-case examples, and the open questions the spec must resolve.
**All requirements below derive from n0003 and stay at user-story
granularity; the technical contract is the spec sub-task's
deliverable.**

## User Story

As an AI agent or another module consuming artifacts-os, I want to
fetch artifact frontmatter as structured data and navigate the
artifact graph (parent/child) through the CLI, so I can use
artifacts as data without parsing markdown or stripping rendered
bodies.

## Requirements

1. Fetch a single artifact's frontmatter as structured data (no
   body), in both human-readable and JSON form.
2. Fetch full frontmatter for many artifacts at once, replacing the
   default column projection.
3. Navigate from an artifact to its parent in one CLI call.
4. Enumerate an artifact's direct children as a flat result set,
   composable with existing filters.
5. New flags compose cleanly with shipped surface (`--kind`,
   `--status`, `--view`, `--fields`, `-q`, `-j`); composition
   rules are predictable and documented (see n0003 § "Layered mental
   model" + "Composition matrix").
6. Mental model preserved: `show` is identity-based (one record by
   ID); `list` is predicate-based (set by predicate). Flags that
   collapse the distinction are rejected (n0003 § "Rejected flag
   shapes").
7. Cross-kind relationships work without an explicit `--kind` (a
   task's parent may be a spec, a spec's children may span kinds).
8. Read-only — no mutation flags introduced by this work.
9. Documentation, AI skill, and module READMEs reflect the new
   surface.

## Verification

Concrete CLI invocation checks. Each must run successfully against
the artifacts-os vault itself (or fail with the expected error in
the "rejected" group). The implementer must execute every command
and confirm the documented behaviour.

### Single artifact — frontmatter only

- [ ] `artifacts show t0050 --meta` — human-readable, top table
      only, no body.
- [ ] `artifacts show t0050 --meta -j` — JSON object of frontmatter.
- [ ] `artifacts show t0050 --meta -j | jq -r .status` extracts the
      single field cleanly.
- [ ] `artifacts show t0050 --meta -j | jq -r .parent` returns the
      parent wikilink (or empty for a root artifact).

### Many artifacts — full frontmatter for each

- [ ] `artifacts list --kind task --meta` — human-readable, all
      frontmatter keys per row (not the column projection).
- [ ] `artifacts list --kind task --meta -j` — JSON array of
      frontmatter dicts.
- [ ] `artifacts list --kind task --status ready --meta -j`
      composes filters with `--meta` correctly.
- [ ] `artifacts list --meta -j | jq 'length'` returns total count.

### Navigate to parent

- [ ] `artifacts show t0051 --parent` renders the parent artifact
      (default: full document).
- [ ] `artifacts show t0051 --parent --meta` returns parent's
      frontmatter only.
- [ ] `artifacts show t0051 --parent --meta -j` returns parent as
      JSON object.
- [ ] `artifacts show t0051 --parent --meta -j | jq -r .id` returns
      parent's ID cleanly.
- [ ] `show <root> --parent` exits with the spec-defined behaviour
      (empty / clear message — final wording per spec).

### Enumerate children

- [ ] `artifacts list --children t0050` — default columns, only
      the children of t0050.
- [ ] `artifacts list --children t0050 -j` — JSON array of
      children.
- [ ] `artifacts list --children t0050 --meta -j` — full
      frontmatter of every child.
- [ ] `artifacts list --children t0050 -q` — one name per line,
      shell-loop friendly.
- [ ] `artifacts list --children t0050 --status ready` filters
      children by status.
- [ ] `artifacts list --children t0050 --kind task` filters
      children by kind.
- [ ] `artifacts list --children <leaf-with-no-children>` returns
      empty result with exit 0 (not an error).

### Cross-kind relationships

- [ ] `artifacts show t0048 --parent --meta -j` returns the spec
      `s0012` (cross-kind: task → spec).
- [ ] `artifacts list --children s0012 --meta -j` returns the
      spec's children of any kind without `--kind` filtering.
- [ ] `artifacts list --children t0050` returns mixed-kind children
      where applicable, without dropping records.

### Composition with `--view`

- [ ] `artifacts list --view <name>` applies the named view
      unchanged (baseline; already shipped via s0012).
- [ ] `artifacts list --view <name> --meta` — view's filters and
      sort apply; projection switches to full frontmatter.
- [ ] `artifacts list --view <name> --meta -j` — same as above,
      JSON array.
- [ ] `artifacts list --view <name> --children t0050` — view
      filters AND `parent==t0050` predicate both apply (per-key
      merge).
- [ ] `artifacts list --view <name> --status ready` — `--status`
      overrides view's status; other view filters intact.
- [ ] `artifacts list --view <name> --fields id,name` — `--fields`
      wins over view columns; view's filters/sort still apply.
- [ ] `artifacts list --view <name> -q` — names-only, view filters
      and sort apply, columns ignored.
- [ ] Every cell of the spec's composition matrix produces the
      documented output on the artifacts-os vault.

### Pipeline composition (multi-hop / multi-step)

- [ ] Walk children and inspect each:
      ```bash
      for c in $(artifacts list --children t0050 -q); do
        artifacts show "$c" --meta -j
      done
      ```
- [ ] Count children: `artifacts list --children t0050 -j | jq length`.
- [ ] Filter children to projection:
      ```bash
      artifacts list --children t0050 --status in-progress --meta -j \
        | jq '[.[] | {id, owner}]'
      ```
- [ ] Two-hop grandparent traversal:
      ```bash
      GP=$(artifacts show t0051 --parent --meta -j | jq -r .id)
      artifacts show "$GP" --parent --meta -j
      ```
- [ ] Cross-kind graph dump (every parent → child edge for tasks):
      ```bash
      for c in $(artifacts list --kind task -q); do
        P=$(artifacts show "$c" --parent --meta -j 2>/dev/null \
            | jq -r '.id // empty')
        [ -n "$P" ] && echo "$P -> $c"
      done
      ```

### Rejected flag shapes — must fail with clear error

- [ ] `artifacts show t0050 --children` exits non-zero (use
      `list --children`).
- [ ] `artifacts list t0050` (positional ref) exits non-zero (use
      `show t0050`).
- [ ] `artifacts list --parent t0050` exits non-zero (use
      `--children` for the relationship query).
- [ ] `artifacts show t0050 --view <name>` exits non-zero (`show`
      is identity-based).
- [ ] `artifacts show --kind task` (no ref) exits non-zero.
- [ ] `artifacts show --status ready` (no ref) exits non-zero.

### Documentation & module surface

- [ ] `src/artifacts_os/cli/README.md` documents `--meta`,
      `--children`, `--parent` with the layered mental model and
      the composition matrix.
- [ ] AI skill reflects new flags with worked examples.
- [ ] `docs/settings.md` (if any new keys land) updated.
- [ ] `--help` text on `show` and `list` lists every new flag with
      one-line semantics.

### Read-only invariant

- [ ] No new mutation flags introduced; `--parent` is a query, not
      an assignment. Verified by absence in `--help` output and by
      grep for write paths in the new code.

## Primary References

- **[[n0003-programmatic-cli-access]]** — load-bearing scoping note
- [[n0002-layouts-tree-view-scoping]] — sibling effort consuming the
  same graph primitive
- [[s0012-cli-list-named-views]] — `--view` flag spec this work
  composes with
