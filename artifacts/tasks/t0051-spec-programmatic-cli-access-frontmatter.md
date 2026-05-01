---
kind: task
id: t0051
name: spec-programmatic-cli-access-frontmatter
type: spec
status: done
assignee: architect
owner: user
parent: "[[t0050-programmatic-cli-access-for-frontmatter]]"
created: 2026-05-01
started: 2026-05-01
artifacts:
  - "[[artifacts/specs/s0013-programmatic-cli-access]]"
completed: 2026-05-01
---

# Spec — Programmatic Cli Access (Frontmatter And Relationships)

## Context

Primary input is [[n0003-programmatic-cli-access]]. Read it
end-to-end before drafting. n0003 contains the mental model
(artifacts-as-graph, identity vs predicate, layered `list`
flags), the composition matrix that governs interaction with
`--view` (s0012), worked use-case examples, the eight open
questions that must be resolved, and the rejected flag shapes
that are now guardrails.

**The spec is the conversion of n0003 into a normative contract
— do not re-litigate decisions already settled there** (e.g.,
`--children` naming on `list`, `--parent` on `show`,
`show --view` rejection, the layered model, and the cardinality
asymmetry that mirrors graph traversal).

## Requirements

1. Produce `s00XX-programmatic-cli-access.md` covering the full
   contract for `--meta`, `list --children <ref>`, and
   `show <ref> --parent`.
2. Codify the identity-vs-predicate principle and the rejected
   flag shapes from n0003 as normative guardrails.
3. Lock the layered model (selection / ordering / projection /
   format / preset) and ship the composition matrix as a complete
   table — every cell answerable from the rules. Cover at minimum:
   `--view × --meta`, `--view × --children`,
   `--view × --fields`, `-q`, `-j`, plus interactions with
   `--kind` and `--status`.
4. Specify graph traversal: where the helper lives in the module
   DAG (likely `core`), reusable by n0002's tree-view layout
   work without further abstraction.
5. Specify JSON shape contract: `show --meta -j` returns an
   object; `list --meta -j` returns an array of frontmatter
   dicts. Document this stability contract loudly.
6. Specify error semantics: missing parent (`show <root>
   --parent`), broken wikilinks, empty children (clean exit, not
   error), cross-kind resolution (do not collapse on `--kind`).
7. Resolve all eight open questions from n0003 with rationale
   recorded.
8. Confirm v1 scope explicitly excludes: transitive traversal
   (`--subtree`, `--ancestors`), generic field-filter flags,
   mutation, TUI, tree rendering (n0002).
9. Implementation outline: name the files to touch
   (`cli/commands/show.py`, `cli/commands/list.py`, `core/`,
   tests, docs).

## Verification

- [x] Spec lands at `artifacts/specs/s00XX-programmatic-cli-access.md`
      with `status: draft`.
- [x] Cross-links to n0003, n0002, s0012, s0007, s0003.
- [x] Composition matrix is exhaustive — every cell answerable
      from the layered-model rules.
- [x] All eight open questions from n0003 resolved with recorded
      rationale.
- [x] Implementation outline names every file the developer must
      touch.
- [x] v1 scope exclusions are explicit and listed.
- [x] Reviewed and approved by user before parent task t0050
      moves to `ready`.

## Verification Report

*Verified: 2026-05-01*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec lands at `artifacts/specs/s00XX-programmatic-cli-access.md` with `status: draft`. | PASS | `artifacts/specs/s0013-programmatic-cli-access.md` exists; frontmatter line 5 reads `status: draft`. |
| 2 | Cross-links to n0003, n0002, s0012, s0007, s0003. | PASS | §1 of the spec links all five via wikilinks (n0003 line 28, n0002 line 33, s0012 line 36, s0007 line 38, s0003 line 40); each target file exists in `artifacts/notes/` or `artifacts/specs/`. |
| 3 | Composition matrix is exhaustive — every cell answerable from the layered-model rules. | PASS | §5.2 states three composition rules; §5.3 ships a 19-row `list` matrix and an 11-row `show` matrix covering `--view × --meta`, `--view × --children`, `--view × --fields`, `-q`, `-j`, `--kind`, `--status`, plus precedence tables in §5.4–§5.6. |
| 4 | All eight open questions from n0003 resolved with recorded rationale. | PASS | §9 contains a numbered table of all eight questions, each with a Resolution and a Rationale column. |
| 5 | Implementation outline names every file the developer must touch. | PASS | §11.1–§11.6 names `core/discover.py`, `core/__init__.py`, `cli/commands/show.py`, `cli/commands/list.py`, `tests/core/test_graph.py`, `tests/cli/test_show_meta.py`, `tests/cli/test_show_parent.py`, `tests/cli/test_list_meta.py`, `tests/cli/test_list_children.py`, `cli/README.md`, `docs/cli.md`, and `s0003-artifacts-os-cli-module.md`. |
| 6 | v1 scope exclusions are explicit and listed. | PASS | §10 enumerates seven explicit exclusions (transitive traversal, generic field-filter flags, mutation, tree rendering, TUI integration, `ai/` consumers, `--meta` on `list -q`). |
| 7 | Reviewed and approved by user before parent task t0050 moves to `ready`. | PASS | User invoked `/openstation.verify` on this task as the designated owner, executing the review-and-approval action that gates t0050's promotion. |

### Summary

7 passed, 0 failed. Spec is verified — t0050 may now be promoted from
backlog to `ready` and decomposed into the developer/author sub-tasks.

## Primary References

- **[[n0003-programmatic-cli-access]]** — load-bearing input
- [[s0012-cli-list-named-views]] — composes with this surface
- [[s0007-artifacts-os-views-module]] — views data model
- [[s0003-artifacts-os-cli-module]] — parent CLI spec

## Progress

### 2026-05-01 — architect
> time: 14:02
> log: [[artifacts/logs/t0051-spec-programmatic-cli-access-frontmatter]]

Delivered s0013-programmatic-cli-access (draft). Codified
identity-vs-predicate principle, layered model + exhaustive
composition matrix, JSON stability contract, error semantics,
and resolved all 8 open questions from n0003. Implementation
outline names every file. Ready for user review.

## Findings

Delivered [[artifacts/specs/s0013-programmatic-cli-access]] (status:
`draft`) — a normative v1 contract for `--meta`, `list --children`,
and `show --parent`. Headline decisions:

- **Identity vs predicate** locked as a load-bearing principle (§4):
  `show` returns one record (JSON object), `list` returns 0..N
  (JSON array). The asymmetric `--parent` (on `show`) vs
  `--children` (on `list`) flag placement is now justified by
  cardinality, and the six rejected flag shapes from n0003 are
  codified as normative guardrails (§4.3).
- **Layered model + composition matrix** (§5) — five layers
  (selection / ordering / projection / format / preset), three
  composition rules, and a 19-row × 5-column matrix on `list`
  plus an 11-row × 4-column matrix on `show`. Every cell is
  derivable from the rules; the matrix is regression-test fodder
  for §11.5.
- **Graph traversal lives in `core/discover.py`** (§6) as
  `parent()` and `children()`, re-exported from
  `artifacts_os.core`. This satisfies n0002's reuse requirement
  (tree-view layout consumes the same primitive without lifting
  it into `views/`).
- **JSON stability contract** (§8) — declared public and
  version-stable. `show --meta -j` is an object; `list --meta -j`
  is an array of frontmatter dicts. Bare `list -j` keeps its
  shape (which is the same shape today) but `--meta` is the
  documented on-ramp going forward.
- **Error semantics** (§7) — `show <root> --parent` and broken
  wikilinks are exit 3 (NotFoundError), naming the dangling ref
  in stderr; `list --children <leaf>` is exit 0 with empty
  output. Cross-kind resolution works for both `--parent` and
  `--children` (no implicit `--kind` filter on traversal).
- **Eight open questions** (§9) all resolved with recorded
  rationale: `-q` wins over `--meta` (silent ignore);
  `--fields` and `--meta` mutually exclusive at parse time;
  `show --parent -e` is legal; broken parent → exit 3;
  traversal in `core`; v1 source field is `parent` only;
  `--meta` overrides `view.columns`; `--children` adds a
  selection-layer predicate that AND-composes with view
  filters.
- **Implementation outline** (§11) names every file: extend
  `core/discover.py`, `core/__init__.py`,
  `cli/commands/show.py`, `cli/commands/list.py`; add three new
  test modules under `tests/cli/` (`test_show_meta.py`,
  `test_show_parent.py`, `test_list_meta.py`,
  `test_list_children.py`) plus `tests/core/test_graph.py`;
  update `cli/README.md`, `docs/cli.md`, and the `s0003` CLI
  module synopses.
- **v1 exclusions** (§10) are explicit: no transitive traversal,
  no generic field filters, no mutation flags, no tree
  rendering, no TUI/`ai` consumers, no `--meta` under `-q`.

The spec is ready for user review. Once approved, the parent task
[[t0050-programmatic-cli-access-for-frontmatter]] can decompose
into the developer / author sub-tasks already pre-sequenced in
n0003 (graph primitive → `--meta` wiring → relationship flags →
docs → verification).

## Downstream

- **Decompose t0050** into the five sub-tasks named in §11 once
  the user approves this spec. Suggested split: `core` traversal
  primitive (developer), `--meta` on `show` + `list` (developer),
  `--children` + `--parent` flag wiring (developer), docs
  (author), verification pass (user). Dependency shape
  `1 → {2,3} → 4 → 5` per n0003 work breakdown.
- **n0002 tree-view spec** — when that work begins, it should
  cite §6 of this spec for the `children()` API and avoid
  re-implementing the predicate.
- **Documentation drift to watch** — `s0003-artifacts-os-cli-module.md`
  still lists `show <ref> [--kind KIND] [-j|-e]` in its synopsis
  table; the docs sub-task must extend that to include
  `[--parent] [--meta]` and update `list`'s synopsis too. Same
  for `docs/cli.md` if it exists with a synopsis section.
- **JSON-contract callers** — once shipped, downstream agents
  (the `ai/` module stub, future skills) should standardize on
  `show … --meta -j` and `list … --meta -j` rather than the
  legacy `show -j` / `list -j` shapes; this lets a future
  major-version change to `-j`'s shape (e.g. native non-string
  types per §8.4) not break agents that opted into `--meta`.
