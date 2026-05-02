---
kind: task
id: t0065
name: spec-cli-list-defined-views
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

# Spec: CLI Command to List Defined Views

## Goal

Produce a spec (`artifacts/specs/s00NN-cli-list-defined-views.md`)
for a CLI command that lists every named view defined in
`artifacts/artifacts.yaml`, parallel to `artifacts kinds`.

Parent: [[t0064-cli-list-defined-views-command]] — read its
**User Story** and **Directions** for intent.

## Inputs / References

- Existing parser and data model:
  `src/artifacts_os/views/models.py` — `ViewConfig`, `ViewsConfig`,
  `ViewsSettings`.
- Settings loading helper used by `--view`:
  `_load_views_settings(root)` in `src/artifacts_os/cli/__init__.py`.
- Closest sibling command (use as the shape to mirror):
  `src/artifacts_os/cli/commands/kinds.py`.
- Original view feature spec: [[artifacts/specs/s0012-cli-list-named-views]].
- Vault example data: `artifacts/artifacts.yaml`
  (`views:` and `default_views:` sections).

## Decisions to Settle

The spec must answer all of the following — these are the open
design questions the parent task deliberately did not pin down:

1. **Command surface.** Subcommand name and shape — e.g.
   `artifacts views`. Confirm there is no collision with the
   existing `--view` flag on `artifacts list`.
2. **Default output (rich table).** Which columns to show, in
   what order. Candidates: `name`, `kind` (filter), `columns`,
   `sort`, `default-for` (which kind, if any, binds this view via
   `default_views`). Decide how to render long values (truncate
   filters? show columns as comma-separated list?).
3. **`-q` (quiet) format.** One view name per line, sorted
   alphabetically — confirm and align with `artifacts kinds -q`.
4. **`-j` (JSON) shape.** Exact object schema per view; whether
   to emit a flat array or an object that also carries
   `default_views`. Decide field names and types.
5. **`default_views` rendering.** Inline column on each row vs.
   a separate footer/section vs. a separate flag (e.g.
   `artifacts views --defaults`). Pick one and justify.
6. **Empty / missing config behavior.** What happens when
   `artifacts.yaml` has no `views:` section, an empty `views:`
   map, or no settings file at all. Exit code, stderr message,
   and whether the table is printed empty or suppressed.
7. **Mutually exclusive flags.** `-q` and `-j` reject combination
   (mirror `artifacts kinds`).
8. **Sorting.** Default sort order for table rows. Whether to
   expose a `--sort` flag (likely no — keep minimal).
9. **Errors.** Exit codes for malformed views section
   (delegate to `ViewsSettings` parse errors? raise from the
   command?). Document the user-visible message.
10. **Docs touchpoints.** Which docs to update — at minimum
    `src/artifacts_os/cli/README.md` and `docs/settings.md`'s
    Views section. Confirm and list.

## Out of Scope

- Editing or creating views from the CLI.
- Validating view definitions (that's `validate`'s job; spec may
  note this boundary).
- Showing a single view in detail (`artifacts views show <name>`)
  — call out as a possible follow-up but do not specify here.

## Deliverable

A spec document at `artifacts/specs/s00NN-cli-list-defined-views.md`
with the standard sections (overview, CLI surface, output formats,
algorithm, error table, test cases, doc touchpoints). Link it from
the task's `artifacts:` frontmatter.

## Verification

- [x] Spec created at `artifacts/specs/s00NN-cli-list-defined-views.md`
      and linked in `artifacts:` frontmatter
- [x] Every "Decisions to Settle" item (1–10) is answered with a
      concrete contract
- [x] CLI surface specified with full flag table
- [x] Default / `-q` / `-j` output formats each have a worked
      example
- [x] `default_views` rendering decision is documented with
      rationale
- [x] Empty / missing-config behavior fully specified (exit code,
      stderr, output)
- [x] Test-case list enumerates the cases the implementation
      sub-task must cover
- [x] Docs touchpoints listed (files + sections)

## Verification Report

*Verified: 2026-05-02*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec created and linked in `artifacts:` frontmatter | PASS | `artifacts/specs/s0016-cli-list-defined-views.md` exists; task frontmatter lists `[[artifacts/specs/s0016-cli-list-defined-views]]` |
| 2 | All "Decisions to Settle" items (1–10) answered | PASS | §3 (cmd surface), §4 (default table), §5 (-q), §6 (-j), §7 (default_views rendering), §8 (empty/missing), §9 (mutex flags), §4.2 (sort), §10 (errors), §12.4 (docs) — each gives a concrete contract |
| 3 | CLI surface specified with full flag table | PASS | §3 includes synopsis `artifacts views [-q \| -j]` and a flag table covering `-q`/`--quiet` and `-j`/`--json` with mutex semantics |
| 4 | Default / `-q` / `-j` output formats each have a worked example | PASS | §4.3 worked rich-table sample, §5 sample `-q` output, §6 worked JSON object sample |
| 5 | `default_views` rendering decision documented with rationale | PASS | §7 picks "inline `default-for` column" and includes a four-row alternatives-considered table with rationale |
| 6 | Empty / missing-config behavior fully specified | PASS | §8 enumerates three states (no `artifacts.yaml`, no `views:` section, empty `views:` map) with exit codes, stderr messages, and per-mode output; §10 cross-references |
| 7 | Test-case list enumerates implementation cases | PASS | §12.3 lists 13 numbered test cases covering populated/empty paths, mutex flags, malformed entries, truncation, and multi-kind bindings |
| 8 | Docs touchpoints listed (files + sections) | PASS | §12.4 names `src/artifacts_os/cli/README.md` (new `views` section + `list#Views` cross-link), `docs/settings.md` ("Views Section" paragraph), and `s0003-artifacts-os-cli-module.md` (Command Set entry) |

### Summary

8 passed, 0 failed. Spec is implementation-ready and the task is ready to be marked verified.

## Progress

### 2026-05-02 — architect
> time: 07:50

Drafted [[artifacts/specs/s0016-cli-list-defined-views]] covering
all 10 "Decisions to Settle" with concrete contracts, worked
examples for default/`-q`/`-j` outputs, error-handling table,
13-case test matrix, and documentation diff list. Linked from
task `artifacts:` frontmatter. Transitioning to review.

## Findings

Produced [[artifacts/specs/s0016-cli-list-defined-views]] — a
~440-line spec that pins down every "Decisions to Settle" item
from this task (1–10) with a concrete contract.

**Key decisions:**

- **Subcommand name:** `views` (plural), no positional arg, no
  `--sort` / `--defaults` flag. Mirrors `artifacts kinds`.
- **Default table:** five fixed columns — `name`, `kind`,
  `columns`, `sort`, `default-for`. `filters` is **not** a
  column; `kind` lifts the most common filter axis.
  Long `columns` strings truncate at 60 chars (full value
  always available via `-j`).
- **`-q` format:** view name per line, alphabetically sorted.
  No binding info — quiet mode is for shell pipelines.
- **`-j` format:** object shape `{"views": [...],
  "default_views": {...}}`. Each view object includes a
  `default_for: [<kinds>]` array. Symmetric with the YAML
  input; `jq '.views[]'` gives the flat-array variant.
- **`default_views` rendering:** inline `default-for` column on
  each row (in `-j`, both per-view `default_for` **and**
  top-level `default_views` for round-trip symmetry).
- **Empty / missing-views:** exit 0, stderr hint
  `no views defined in artifacts.yaml`, suppress the table.
  `-j` still emits a well-formed empty payload.
- **Mutually exclusive `-q -j`:** native argparse group, exit 2.
- **Malformed entries:** delegated to existing
  `ViewsSettings` parser; surfaces as exit 1 via the
  `_run` ValueError cascade.
- **Docs touchpoints:** `cli/README.md` (new `views` section
  after `kinds` + cross-link from existing `list#Views`),
  `docs/settings.md` (one paragraph appended to "Views
  Section"), `s0003-artifacts-os-cli-module.md` (one-line
  Command Set entry).

**Trade-offs called out:**

- Object JSON shape vs. flat array — chose object for
  symmetry with YAML input and clearer kind→view querying.
- Exit 0 (not 2) for empty/missing config — consistent with
  `artifacts list` returning 0 for empty result sets.
- Malformed YAML treated as "no views defined" rather than
  surfaced — keeps the error surface narrow; `validate` is
  the right place to fail loudly.

**Deferred (called out in §11):** `artifacts views show <name>`
detail subcommand, `--validate` flag (belongs under `validate`),
`--kind` filter (use `jq`), CLI alias.

The spec is implementation-ready: §12 specifies the new file
path (`src/artifacts_os/cli/commands/views.py`), reuses the
existing `_load_views_settings` helper, lists 13 required test
cases, and enumerates documentation diffs.

## Downstream

- **Implementation sub-task** under
  [[t0064-cli-list-defined-views-command]] — to be created next
  by the project-manager. The spec at
  [[artifacts/specs/s0016-cli-list-defined-views]] is its
  contract; verification checklist in §13 maps 1:1 onto the
  parent task's provisional acceptance criteria.
