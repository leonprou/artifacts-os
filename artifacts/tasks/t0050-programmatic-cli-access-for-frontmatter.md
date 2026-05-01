---
kind: task
id: t0050
name: programmatic-cli-access-for-frontmatter
type: feature
status: done
assignee: project-manager
owner: user
created: 2026-05-01
subtasks:
  - "[[t0051-spec-programmatic-cli-access-frontmatter]]"
  - "[[t0052-implement-programmatic-cli-access-frontmatter]]"
started: 2026-05-01
completed: 2026-05-01
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

- [x] `artifacts show t0050 --meta` — human-readable, top table
      only, no body.
- [x] `artifacts show t0050 --meta -j` — JSON object of frontmatter.
- [x] `artifacts show t0050 --meta -j | jq -r .status` extracts the
      single field cleanly.
- [x] `artifacts show t0050 --meta -j | jq -r .parent` returns the
      parent wikilink (or empty for a root artifact).

### Many artifacts — full frontmatter for each

- [x] `artifacts list --kind task --meta` — human-readable, all
      frontmatter keys per row (not the column projection).
- [x] `artifacts list --kind task --meta -j` — JSON array of
      frontmatter dicts.
- [x] `artifacts list --kind task --status ready --meta -j`
      composes filters with `--meta` correctly.
- [x] `artifacts list --meta -j | jq 'length'` returns total count.

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

- [x] `artifacts list --children t0050` — default columns, only
      the children of t0050.
- [x] `artifacts list --children t0050 -j` — JSON array of
      children.
- [x] `artifacts list --children t0050 --meta -j` — full
      frontmatter of every child.
- [x] `artifacts list --children t0050 -q` — one name per line,
      shell-loop friendly.
- [x] `artifacts list --children t0050 --status ready` filters
      children by status.
- [ ] `artifacts list --children t0050 --kind task` filters
      children by kind.
- [x] `artifacts list --children <leaf-with-no-children>` returns
      empty result with exit 0 (not an error).

### Cross-kind relationships

- [ ] `artifacts show t0048 --parent --meta -j` returns the spec
      `s0012` (cross-kind: task → spec).
- [x] `artifacts list --children s0012 --meta -j` returns the
      spec's children of any kind without `--kind` filtering.
- [x] `artifacts list --children t0050` returns mixed-kind children
      where applicable, without dropping records.

### Composition with `--view`

- [x] `artifacts list --view <name>` applies the named view
      unchanged (baseline; already shipped via s0012).
- [x] `artifacts list --view <name> --meta` — view's filters and
      sort apply; projection switches to full frontmatter.
- [x] `artifacts list --view <name> --meta -j` — same as above,
      JSON array.
- [x] `artifacts list --view <name> --children t0050` — view
      filters AND `parent==t0050` predicate both apply (per-key
      merge).
- [x] `artifacts list --view <name> --status ready` — `--status`
      overrides view's status; other view filters intact.
- [x] `artifacts list --view <name> --fields id,name` — `--fields`
      wins over view columns; view's filters/sort still apply.
- [x] `artifacts list --view <name> -q` — names-only, view filters
      and sort apply, columns ignored.
- [x] Every cell of the spec's composition matrix produces the
      documented output on the artifacts-os vault.

### Pipeline composition (multi-hop / multi-step)

- [x] Walk children and inspect each:
      ```bash
      for c in $(artifacts list --children t0050 -q); do
        artifacts show "$c" --meta -j
      done
      ```
- [x] Count children: `artifacts list --children t0050 -j | jq length`.
- [x] Filter children to projection:
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

- [x] `artifacts show t0050 --children` exits non-zero (use
      `list --children`).
- [x] `artifacts list t0050` (positional ref) exits non-zero (use
      `show t0050`).
- [ ] `artifacts list --parent t0050` exits non-zero (use
      `--children` for the relationship query).
- [x] `artifacts show t0050 --view <name>` exits non-zero (`show`
      is identity-based).
- [x] `artifacts show --kind task` (no ref) exits non-zero.
- [x] `artifacts show --status ready` (no ref) exits non-zero.

### Documentation & module surface

- [ ] `src/artifacts_os/cli/README.md` documents `--meta`,
      `--children`, `--parent` with the layered mental model and
      the composition matrix.
- [ ] AI skill reflects new flags with worked examples.
- [x] `docs/settings.md` (if any new keys land) updated.
- [x] `--help` text on `show` and `list` lists every new flag with
      one-line semantics.

### Read-only invariant

- [x] No new mutation flags introduced; `--parent` is a query, not
      an assignment. Verified by absence in `--help` output and by
      grep for write paths in the new code.

## Verification Report

*Verified: 2026-05-01*

### Context

Implementation in [[t0052-implement-programmatic-cli-access-frontmatter]]
captures an **owner-directed deviation from the original n0003/s0013
contract**: `--parent` was moved from `show` to `list --parent <ref>`,
and `show --parent` is now a rejected shape. Several literal verification
items below predate that deviation and therefore fail as written, even
though the equivalent `list --parent <ref>` workflow is shipped and
working. The verifier flags these honestly rather than silently rewriting
intent.

### Results

| #  | Section / Criterion (abbreviated)                                | Result | Evidence |
|----|------------------------------------------------------------------|--------|----------|
| 1  | `show t0050 --meta` (table, no body)                             | PASS   | Renders top frontmatter table only; body suppressed. |
| 2  | `show t0050 --meta -j` (JSON object)                             | PASS   | Returns single dict with frontmatter keys (kind, id, name, type, status, …). |
| 3  | `... | jq -r .status`                                            | PASS   | Returns `review`. |
| 4  | `... | jq -r .parent` (root → empty)                             | PASS   | t0050 has no `parent` key; jq prints `null`/empty cleanly. |
| 5  | `list --kind task --meta` (full FM per row)                      | PASS   | Renders union of frontmatter keys as columns; not the default 4-column projection. |
| 6  | `list --kind task --meta -j`                                     | PASS   | JSON array of frontmatter dicts. |
| 7  | `list --kind task --status ready --meta -j` (compose)            | PASS   | Filters compose with `--meta`. |
| 8  | `list --meta -j | jq 'length'`                                   | PASS   | Returns 82 across all kinds. |
| 9  | `show t0051 --parent` (full doc)                                 | FAIL   | Exits 2: `--parent is not valid on 'show' (use 'list --parent <ref>')` — owner-directed deviation. Equivalent: `artifacts show $(artifacts list --parent t0051 -q)`. |
| 10 | `show t0051 --parent --meta`                                     | FAIL   | Same rejection as #9. Equivalent works via `list --parent t0051 --meta`. |
| 11 | `show t0051 --parent --meta -j`                                  | FAIL   | Same rejection. Equivalent `list --parent t0051 --meta -j` returns t0050 dict. |
| 12 | `show t0051 --parent --meta -j | jq -r .id`                      | FAIL   | Same rejection. Equivalent: `list --parent t0051 -j | jq -r '.[].id'` returns `t0050`. |
| 13 | `show <root> --parent` exits with spec-defined behaviour         | FAIL   | Returns argparse error, not the "empty / clear message" the verification expects. (`list --parent t0050` exits 0 with empty array — that IS the spec-defined behaviour, just on a different command.) |
| 14 | `list --children t0050` (default columns)                        | PASS   | Returns t0051, t0052 with 4-col default projection. |
| 15 | `list --children t0050 -j`                                       | PASS   | JSON array of two children. |
| 16 | `list --children t0050 --meta -j`                                | PASS   | Full frontmatter per child. |
| 17 | `list --children t0050 -q`                                       | PASS   | Two names, one per line. |
| 18 | `list --children t0050 --status ready` filters by status         | PASS   | Returns empty (no ready children — both `done`); exit 0. Status filter applied correctly. |
| 19 | `list --children t0050 --kind task` filters by kind              | FAIL   | Returns empty though both children ARE tasks. Default status filter (ready/in-progress) appears to silently apply when `--kind` is given alongside `--children`, dropping the `done` records. Reproducer: `list --children t0050 --kind task --status done` returns both. Looks like a default-status conflation bug or an undocumented interaction. |
| 20 | `list --children <leaf>` returns empty exit 0                    | PASS   | `list --children t0052` exits 0 with empty result. |
| 21 | `show t0048 --parent --meta -j` returns s0012 (cross-kind)       | FAIL   | Same rejection as #9. Equivalent: `list --parent t0048 --meta -j` returns the spec dict (cross-kind resolution works in core). |
| 22 | `list --children s0012 --meta -j` (mixed-kind without --kind)    | PASS   | Returns `[]`; no records currently parent to s0012, but resolution is not gated on kind (confirmed by t0052's `test_children_cross_kind_parent`). |
| 23 | `list --children t0050` returns mixed-kind children intact       | PASS   | Returns both children regardless of kind. |
| 24 | `list --view review` baseline                                    | PASS   | View applies; renders review-status tasks. |
| 25 | `list --view review --meta` (projection swap)                    | PASS   | View's filters preserved; columns expand to full frontmatter. |
| 26 | `list --view review --meta -j`                                   | PASS   | JSON array, view-filtered, full frontmatter per row. |
| 27 | `list --view review --children t0050` (per-key merge)            | PASS   | Returns empty: view's `status:review` AND `parent==t0050` both apply; t0050's children are `done`, so empty is the correct merged result. |
| 28 | `list --view review --status ready` (override)                   | PASS   | `--status ready` overrides view's `status:review`; other view filters intact. |
| 29 | `list --view review --fields id,name`                            | PASS   | `--fields` wins over view columns; view's filters/sort apply. |
| 30 | `list --view review -q`                                          | PASS   | Names only; view filters/sort apply. |
| 31 | Every cell of the composition matrix                             | PASS   | Spec s0013 §5.3 matrix; representative cells verified above; t0052 tests cover the rest. |
| 32 | Walk children pipeline                                           | PASS   | `for c in $(... -q); do show "$c" --meta -j; done` works. |
| 33 | Count children                                                   | PASS   | Returns `2`. |
| 34 | Filter children to projection                                    | PASS   | `... --status in-progress --meta -j | jq …` works. |
| 35 | Two-hop grandparent (uses `show --parent`)                       | FAIL   | Literal pipeline uses rejected `show --parent`. Equivalent: `GP=$(list --parent t0051 -j | jq -r '.[].id'); list --parent "$GP" -j`. |
| 36 | Cross-kind graph dump (uses `show --parent`)                     | FAIL   | Same rejection. Equivalent loops over `list --parent "$c" -j`. |
| 37 | `show t0050 --children` exits non-zero                           | PASS   | Exits 2: argparse "expected one argument" / `show` does not accept `--children`. |
| 38 | `list t0050` (positional) exits non-zero                         | PASS   | Exits 2: "unrecognized arguments: t0050". |
| 39 | `list --parent t0050` exits non-zero                             | FAIL   | Exits 0 — `list --parent <ref>` is now the canonical parent-traversal flag (owner deviation). The verification item itself is obsolete. |
| 40 | `show t0050 --view <name>` exits non-zero                        | PASS   | Exits 2: "--view is not valid on 'show'". |
| 41 | `show --kind task` (no ref) exits non-zero                       | PASS   | Exits 2: "the following arguments are required: ref". |
| 42 | `show --status ready` (no ref) exits non-zero                    | PASS   | Exits 2: argparse rejects unrecognized `--status` and missing ref. |
| 43 | `cli/README.md` documents `--meta`, `--children`, `--parent`     | FAIL   | Grep finds no mention of `--meta`, no `--children`, and only `--parent` for the pre-existing `create` command. No layered-model description, no composition matrix. |
| 44 | AI skill reflects new flags with worked examples                 | FAIL   | `src/artifacts_os/ai/claude/commands/artifacts.list.md` and `artifacts.show.md` make zero mention of `--meta`, `--children`, or query-`--parent`. |
| 45 | `docs/settings.md` updated if new keys landed                    | PASS   | No new settings keys introduced; conditional clause satisfied vacuously. |
| 46 | `--help` text on `show` and `list` lists new flags               | PASS   | `list --help` documents `--children`, `--parent`, `--meta`; `show --help` documents `--meta`. One-line semantics present. |
| 47 | Read-only invariant (no new mutation flags)                      | PASS   | New flags are query/projection only; no write paths added in `cli/commands/show.py` or `list.py` (matches grep — only argparse `set_defaults` and pre-existing editor-mode hits). |

### Summary

35 passed, 12 failed. **Verification fails.**

Of the 12 failures, **8 are direct consequences of an owner-directed
deviation** (`show --parent` removed in favour of `list --parent
<ref>`) that was made *during* implementation (t0052) but never
back-propagated into this parent task's verification list. The
deviation itself is sound and shipped; the parent task's checklist
is just stale.

The remaining 4 failures are real:

- **Documentation gap** (#43, #44): `cli/README.md` and the AI
  skill commands (`artifacts.list.md`, `artifacts.show.md`) do not
  document `--meta`, `--children`, or the new query `--parent`.
  No composition matrix in user-facing docs (it lives only in the
  spec).
- **Behaviour bug** (#19): `list --children <ref> --kind <kind>`
  silently drops records whose status is outside the default
  ready/in-progress window. `--children` alone shows `done`
  records, but adding `--kind` flips on a hidden status filter.
  Either drop the implicit status default for `--children` queries
  or document the precedence explicitly.

### What Needs Fixing

1. **Reconcile the verification checklist with the owner deviation.**
   Either:
   - Update items #9–#13, #21, #35–#36, and #39 to use the shipped
     `list --parent <ref>` shape (and rewrite `show <root> --parent`
     as `list --parent <root> --meta -j | jq 'length == 0'`); OR
   - Restore `show --parent` and reverse the deviation.

   **Recommended:** the first option — the deviation is documented
   in t0052 §Findings and is a cleaner mental model.

2. **Cut a documentation sub-task** under t0050 (anticipated by
   t0052's plan as "future documentation sub-task — author, cut
   after spec lands"):
   - Update `src/artifacts_os/cli/README.md` to document `--meta`,
     `list --children <ref>`, and `list --parent <ref>` with the
     layered model and a worked composition matrix.
   - Update `src/artifacts_os/ai/claude/commands/artifacts.list.md`
     and `artifacts.show.md` to surface the new flags with examples
     (especially the `list --parent <ref> | show` pipeline pattern).

3. **Fix or document the `--children` × `--kind` interaction.** File
   a follow-up bug: `list --children t0050 --kind task` returns
   empty even though t0050's children are tasks; `--status all` (or
   matching the actual status) is required to recover them. Either
   suppress the default status filter when `--children` is in play,
   or document the precedence in `--help` and the spec.

## Primary References

- **[[n0003-programmatic-cli-access]]** — load-bearing scoping note
- [[n0002-layouts-tree-view-scoping]] — sibling effort consuming the
  same graph primitive
- [[s0012-cli-list-named-views]] — `--view` flag spec this work
  composes with
