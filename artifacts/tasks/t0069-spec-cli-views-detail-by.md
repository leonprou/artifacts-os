---
kind: task
id: t0069
name: spec-cli-views-detail-by
type: spec
status: done
assignee: architect
owner: user
parent: "[[t0064-cli-list-defined-views-command]]"
created: 2026-05-02
started: 2026-05-02
artifacts:
  - "[[artifacts/specs/s0016-cli-list-defined-views]]"
completed: 2026-05-02
---

# Spec: `artifacts views <name>` — Detail Mode

## Goal

Produce a sub-spec (or addendum to
[[artifacts/specs/s0016-cli-list-defined-views]]) for a positional
detail mode on the existing `artifacts views` command:

```text
artifacts views <view_name> [-q | -j]
```

This addresses the deferred follow-up called out in **s0016 §11**
("`artifacts views show <name>` — detail view of a single
view"). The user has now requested it, framed as a positional
argument on the existing subcommand rather than a nested
`show` sub-subcommand. The architect should pick the actual
shape and justify it.

Parent: [[t0064-cli-list-defined-views-command]] — the
list-mode command this extends.

## Inputs / References

- Shipped list-mode command:
  `src/artifacts_os/cli/commands/views.py`
  ([[t0067-implement-cli-list-defined-views]]).
- Authoritative existing spec:
  [[artifacts/specs/s0016-cli-list-defined-views]] —
  particularly §3 (CLI surface), §6 (JSON shape), §10 (errors),
  §11 (deferred items).
- Data model: `ViewConfig` in
  `src/artifacts_os/views/models.py`.
- Settings loader: `_load_views_settings(root)` in
  `src/artifacts_os/cli/__init__.py` (already re-raises
  `ValueError` after t0067).
- Vault example: `artifacts/artifacts.yaml`.

## Decisions to Settle

The spec must answer all of the following:

1. **CLI surface shape.** Positional `artifacts views <name>`
   vs. subcommand `artifacts views show <name>`. User asked for
   the former; pick whichever is cleanest given argparse
   ergonomics, list/detail-mode coexistence, and consistency
   with `artifacts kinds` (which has no detail mode today).
2. **Multi-name handling.** Accept one name only, or `nargs="+"`
   for `artifacts views a b c`? If multi-name, decide table-mode
   vs. multiple detail blocks vs. JSON array.
3. **Default detail output.** Format for a single view's
   definition. Candidates: multi-line key-value block, a
   two-column rich `Table` (key/value), a panel. Decide what to
   include: `name`, `columns` (full, untruncated), `filters`
   (full dict — pretty-printed how?), `sort`, `default-for`.
4. **`-q` (quiet) with positional.** Is quiet meaningful for
   detail mode? If so, define the shape (e.g. just the
   columns string? a tab-separated row?). If not, document
   that `-q` is ignored or rejected.
5. **`-j` (JSON) with positional.** Confirm: emit a single
   object equal to the per-view element of the list-mode
   `views[]` array (`{name, columns, filters, sort,
   default_for}`). Or emit a list of one for symmetry?
6. **Unknown name.** Exit code, stderr message
   (e.g. `error: unknown view '<name>'`), and whether to
   suggest close matches via `difflib.get_close_matches`.
7. **Interaction with mutually-exclusive `-q` / `-j`.** Reuse
   the existing argparse group; confirm positional + `-q -j`
   still rejects.
8. **List/detail dispatch.** `views.py:run` currently treats
   any positional arg as an error (none defined). Decide
   whether the dispatch is a simple `if args.name:` branch or
   a refactor into two functions.
9. **Empty / missing-views interaction.** When `views:` is
   empty/missing **and** a positional is supplied, what
   happens? (Likely the same "unknown view" error — confirm.)
10. **Doc touchpoints.** `cli/README.md` views section gets a
    new "detail mode" subsection; `s0016` may need a §15
    addendum or a sibling spec `s00NN-cli-views-detail.md`.
    Pick one.

## Out of Scope

- New flags beyond `-q` / `-j` (no `--filters-only`,
  `--columns-only`, etc. unless the architect strongly
  motivates).
- Editing or validating views from the CLI (still
  `validate`'s job).
- Glob / pattern matching on view names (`art views note-*`).

## Deliverable

Either:

- A short standalone spec at
  `artifacts/specs/s00NN-cli-views-detail.md`, **or**
- A §15 addendum appended to
  [[artifacts/specs/s0016-cli-list-defined-views]].

Architect picks which based on cohesion (likely an addendum,
since the contract heavily references s0016 §6 / §10). Link
the chosen artifact in this task's `artifacts:` frontmatter.

## Findings

Delivered as a **§15 addendum to
[[artifacts/specs/s0016-cli-list-defined-views]]** (chosen over a
sibling spec because the contract heavily references s0016 §6
JSON shape and §10 errors, reuses the loader / mutex group, and
inherits the empty-state semantics — keeping it colocated avoids
duplication and stale cross-links). §11's deferred bullet was
updated to point at §15.

### Decisions Settled (1–10)

| # | Question | Decision |
|---|----------|----------|
| 1 | CLI shape | **Positional** `artifacts views <view_name>` (user's ask). Rejected `views show <name>`: longer to type, doubles help-tree depth, no symmetry payoff. Documented `nargs="?"` so list mode is unchanged. |
| 2 | Multi-name | **Single name only** (`nargs="?"`). Rejected `nargs="+"`: introduces output-shape ambiguity, error-path ambiguity, and no real ergonomic gap (`jq` covers multi-view JSON from list mode). |
| 3 | Default output | **Two-column Rich Table** (`field` / `value`) with 6 fixed rows: `name`, `kind` (lifted from filters), `columns` (untruncated — the principal value-add), `filters` (rendered as `json.dumps(..., indent=2, sort_keys=True)`), `sort`, `default-for`. Rejected: text block (inconsistent aesthetic), Panel (heavy), one-row-per-filter (variable layout). |
| 4 | `-q` semantic | **Print `view.columns` on one line.** Deliberate divergence from list-mode `-q` (which prints names): in detail mode the user has already typed the name; the next-most-script-useful single-line value is `columns`, which composes with `art list --fields "$(art views ready -q)"`. Rejected: echo name (redundant), no-op (footgun), reject `-q` (loses scripting mode). |
| 5 | `-j` shape | **Single JSON object** equal to one element of list-mode `views[]` (§6.1). Rejected single-element array (extra `jq -s` for symmetry). Rejected including top-level `default_views` map (per-view `default_for` already covers the binding direction; full map is list-mode's job). |
| 6 | Unknown name | **Exit 2**, stderr `error: unknown view '<name>'`. Append `Did you mean: a, b, c?` line when `difflib.get_close_matches(name, names, n=3, cutoff=0.6)` is non-empty. Exit 2 matches `--view foo not found` from s0012. |
| 7 | `-q -j` mutex | **Reuse existing argparse group.** Positional and the flag-group are independent; argparse's native rejection still fires. No custom validation. |
| 8 | Dispatch | **`if args.name is None:` branch in `run`** with private `_run_list` / `_run_detail` helpers in the same file. Loader call and reverse-index of `default_views` happen once before dispatch (both paths consume them). Rejected splitting into a sibling module (would force shared helpers into a third module). |
| 9 | Empty + positional | **Collapse into the unknown-view error.** When `views:` is empty/missing **and** a positional is supplied, emit `error: unknown view '<name>'` (exit 2) — not list-mode's "no views defined" hint. The `Did you mean` line is naturally empty. List mode's empty-vault behaviour (§8) is unchanged. |
| 10 | Doc touchpoints | **§15 addendum** to s0016 (this task). Implementation sub-task to update `cli/README.md` (new Detail mode subsection under `views`) and `s0003` Command Set row (`views [<view_name>] [-q\|-j]`). No changes to `docs/settings.md`, `s0007`, or `s0012`. |

### Worked CLI examples (full content in §15.3 / §15.4 / §15.5)

```text
$ artifacts views ready                      # default — 6-row k/v table
$ artifacts views ready -q                   # → id,name,assignee,created:date
$ artifacts views ready -j                   # → single per-view JSON object
$ artifacts views redy                       # error: unknown view 'redy'
                                             # Did you mean: ready, recent?
                                             # exit 2
```

### Test-case list

22 new cases (§15.12, numbered 14–35) covering: default-mode
rendering of every row variant (14–21), `-q`/`-j` machine modes
including emptiness semantics (22–26), the unknown-view error
matrix across all three output modes plus close-match
suggestions (27–32), and flag interactions / list-mode
backwards-compatibility (33–35).

### Implementation outline (for the follow-up sub-task)

Single-file edit to `src/artifacts_os/cli/commands/views.py`:
add a `name` positional with `nargs="?"`, factor `run` into
`_run_list` / `_run_detail`, share the loader call and
reverse-index. No changes required to `cli/__init__.py`,
`views/models.py`, or the existing argparse mutex group.

## Downstream

- **Implementation sub-task** under
  [[t0064-cli-list-defined-views-command]] — code + tests +
  README/`s0003` doc updates per §15.10–15.12. Not yet created;
  parent task PM should spawn it once this addendum is
  approved.
- **Parent task `t0064`** — when the implementation sub-task
  lands, the parent's user story for Iteration 2 is satisfied
  and t0064 can move toward `review`.
- **Future ergonomic risk** flagged in §15.2.1: if a future
  feature ever needs `artifacts views <verb>`, the positional
  shadows verb dispatch. Mitigation already documented (express
  as a flag, not a verb). No action required now.

## Progress

- 2026-05-02 — architect: appended §15 detail-mode addendum to
  `artifacts/specs/s0016-cli-list-defined-views.md` covering all
  ten decisions, two worked default-mode tables, `-q` / `-j`
  contracts, unknown-name error matrix with close-match
  suggestions, list/detail dispatch outline, doc touchpoints,
  and 22 test cases (numbered 14–35) for the implementation
  sub-task. Updated §11 to point at §15. Task → review.

## Verification

- [ ] Spec artifact created (or s0016 amended) and linked in
      `artifacts:` frontmatter
- [ ] All ten "Decisions to Settle" answered with a concrete
      contract
- [ ] CLI surface specified with worked examples for default,
      `-q`, `-j` modes
- [ ] Unknown-name error exit code + stderr message specified
- [ ] List/detail dispatch logic specified at the
      `views.py:run` level
- [ ] Test-case list enumerates the cases the implementation
      sub-task must cover
- [ ] Doc touchpoints listed
