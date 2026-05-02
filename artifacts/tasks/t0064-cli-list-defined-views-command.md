---
kind: task
id: t0064
name: cli-list-defined-views-command
type: feature
status: review
assignee: project-manager
owner: user
created: 2026-05-02
subtasks:
  - "[[t0065-spec-cli-list-defined-views]]"
---

# CLI: List Defined Views

## User Story

**As a** vault user who has named views defined in
`artifacts/artifacts.yaml`,
**I want** a CLI command that lists every defined view (and which
views are bound as defaults per kind),
**so that** I can discover available presets without opening the
YAML file by hand and decide which to invoke via
`artifacts list --view <name>`.

## Why

Views were introduced by [[t0047-cli-list-named-views]] and ship as
a discoverability feature — but right now they are only discoverable
by reading `artifacts/artifacts.yaml` directly. The CLI already
exposes its sibling concept (kinds) via `artifacts kinds` ([[t0021-add-artifacts-kinds-subcommand-to]]);
views deserve a parallel surface so operators, slash-command
authors, and new contributors can explore what's available.

## Directions

> Final tech requirements will be set by the spec sub-task. The
> bullets below are intent, not contract.

- The command should consume the existing `ViewsSettings`
  (s0007 / s0010) — the data is already parsed; this is a
  read-only presentation surface.
- Show each view's name and the most useful at-a-glance metadata
  (kind filter, columns, sort) — exact columns are the spec's
  call.
- Surface `default_views` mappings somehow so users can see which
  view fires automatically per kind.
- Match the look-and-feel of `artifacts kinds`: rich table by
  default, with `-q` (quiet, machine-readable) and `-j` (JSON)
  variants, mutually exclusive.
- Behave gracefully when no views are defined.
- Reference: `src/artifacts_os/cli/commands/kinds.py` is the
  closest sibling and a good shape to mirror.

## Sub-tasks

- [[t0065-spec-cli-list-defined-views]] — architect to produce
  the spec (CLI surface, output columns, JSON shape, error
  handling, default-views rendering).
- *Implementation sub-task* — to be created after spec is
  approved.

## Tech Requirements

*To be finalized after [[t0065-spec-cli-list-defined-views]] is
approved.*

## Verification

*Final checklist will be set after the spec is approved. Provisional
acceptance:*

- [ ] A CLI command lists all views defined in
      `artifacts/artifacts.yaml`
- [ ] Default-views bindings (per-kind) are visible from the
      output
- [ ] Quiet (`-q`) and JSON (`-j`) variants exist and are
      machine-readable
- [ ] Behaves gracefully when no views are defined
- [ ] Documentation updated (`cli/README.md` and/or
      `docs/settings.md` cross-link)
