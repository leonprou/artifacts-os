---
kind: task
id: t0068
name: cli-views-detail-by-name
type: feature
status: rejected
assignee: project-manager
owner: user
created: 2026-05-02
subtasks:
  - "[[t0069-spec-cli-views-detail-by]]"
---

# CLI: `artifacts views <name>` — Detail Mode

## User Story

**As a** vault user who has discovered a view via `artifacts views`,
**I want** to invoke `artifacts views <view_name>` to see that
view's full definition (filters, columns, sort, default-for
binding) without scanning a wide table or piping through `jq`,
**so that** I can quickly inspect a single preset before invoking
it via `artifacts list --view <name>` or before editing it in
`artifacts.yaml`.

## Why

Spec [[artifacts/specs/s0016-cli-list-defined-views]] §11
deliberately deferred this until a user asked. The user has now
asked. The list-mode command (`artifacts views`) ships in
[[t0064-cli-list-defined-views-command]] and intentionally
truncates `columns` strings and omits `filters` from the table —
detail mode closes that gap for single-record inspection.

This is also the natural ergonomic follow-up to the
discoverability story: list → pick → inspect → use.

## Directions

> Final tech requirements will be set by the spec sub-task. The
> bullets below are intent, not contract.

- Positional argument: `artifacts views <view_name>`. The list
  mode (no positional) keeps its current behaviour; the
  positional triggers detail mode.
- Show the **full** view definition — at minimum: `name`,
  `columns` (untruncated), `filters` (full dict), `sort`,
  `default-for` binding. Format choice is the spec's call (a
  multi-line key-value block is the obvious starting point).
- Honor the existing `-q` / `-j` flags consistently with the
  list mode — `-j` should emit the single view's JSON object
  (a clean subset of the list-mode `views[]` element).
- Unknown view name should fail with a clear error and a
  non-zero exit code; consider suggesting close matches if
  cheap.
- No design overlap with `artifacts list --view <name>` — that
  applies the view to filter artifacts; this *describes* the
  view itself.
- Reuse `_load_views_settings` and the existing `ViewConfig`
  data model; do not introduce new parsing.
- Reference: [[artifacts/specs/s0016-cli-list-defined-views]]
  §11 (deferred follow-up rationale) and the existing
  `src/artifacts_os/cli/commands/views.py` shipped by
  [[t0067-implement-cli-list-defined-views]].

## Sub-tasks

- [[t0069-spec-cli-views-detail-by]] — architect to produce the
  spec (positional vs subcommand, output format, `-q` / `-j`
  contract, unknown-name error, multi-name handling).
- *Implementation sub-task* — to be created after spec is
  approved.

## Tech Requirements

*To be finalized after [[t0069-spec-cli-views-detail-by]] is
approved.*

## Verification

*Final checklist will be set after the spec is approved.
Provisional acceptance:*

- [ ] `artifacts views <view_name>` prints the full definition
      of a single view (filters, columns, sort, default-for).
- [ ] `-j` mode emits a JSON object for the single view that is
      consistent with the list-mode shape.
- [ ] Unknown view name fails with a clear error and a
      non-zero exit code.
- [ ] List mode (`artifacts views` with no positional) is
      unchanged.
- [ ] Documentation updated (`cli/README.md` views section).
