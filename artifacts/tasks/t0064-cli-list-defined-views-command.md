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
  - "[[t0067-implement-cli-list-defined-views]]"
artifacts:
  - "[[artifacts/specs/s0016-cli-list-defined-views]]"
started: 2026-05-02
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
exposes its sibling concept (kinds) via `artifacts kinds`
([[t0021-add-artifacts-kinds-subcommand-to]]); views deserve a
parallel surface so operators, slash-command authors, and new
contributors can explore what's available.

## Sub-tasks

- [[t0065-spec-cli-list-defined-views]] — architect produced the
  spec ([[artifacts/specs/s0016-cli-list-defined-views]]); status:
  `done`.
- [[t0067-implement-cli-list-defined-views]] — developer
  implements the spec end-to-end; status: `ready`.

## Tech Requirements (finalized)

Authoritative spec: [[artifacts/specs/s0016-cli-list-defined-views]].
Requirements below are normative; refer to the spec for rationale,
diagrams, and worked examples.

1. **CLI surface** — new top-level subcommand `artifacts views`
   with mutually exclusive `-q` / `--quiet` and `-j` / `--json`
   flags. No positional arg, no `--sort`, no `--defaults`. See
   spec §3.
2. **Default output** — rich table with five fixed columns in
   order: `name`, `kind`, `columns`, `sort`, `default-for`.
   `filters` is intentionally not a column. Sorted alphabetically
   by `name`. See spec §4.
3. **Long-value rendering** — `columns` cells longer than 60
   characters truncate to 57 + `…`; full value preserved in `-j`.
   `default-for` is comma-separated, no truncation. See spec §4.1.
4. **`-q` (quiet)** — one view name per line, alphabetically
   sorted, no binding info. See spec §5.
5. **`-j` (JSON)** — single object with two keys:
   `{"views": [...], "default_views": {...}}`. Each view object
   has `name`, `columns`, `filters`, `sort`, `default_for`
   (kinds bound to it, sorted). See spec §6.
6. **`default_views` rendering** — inline `default-for` column
   on each row in the table; in `-j`, both per-view `default_for`
   array **and** the top-level `default_views` object for
   round-trip symmetry with YAML input. See spec §7.
7. **Empty / missing config** — exit `0` with stderr hint
   `no views defined in artifacts.yaml`; suppress the table
   (don't render an empty header-only table). `-q` produces no
   stdout; `-j` still emits `{"views": [], "default_views": {…}}`.
   See spec §8.
8. **Errors** — `-q` and `-j` together → argparse exit 2 (native
   message). Malformed view entry (missing `columns`) → exit 1
   via the existing `ViewsSettings` `ValueError` cascade with
   stderr `error: view entry missing required 'columns' field`.
   Non-loadable YAML treated as empty (exit 0). See spec §10.
9. **Reuse** — consume the existing `_load_views_settings(root)`
   helper from `cli/__init__.py`; do not introduce a new loader.
   No changes to `ViewsSettings` / `ViewConfig` data model.
   See spec §1, §12.
10. **Files** — new
    `src/artifacts_os/cli/commands/views.py` (mirrors
    `commands/kinds.py` shape); register in
    `src/artifacts_os/cli/__init__.py` adjacent to
    `_kinds_cmd.register(...)`; new tests at
    `tests/cli/test_views_cmd.py`. See spec §12.
11. **Docs** — update `src/artifacts_os/cli/README.md` (new
    `views` section after `kinds` + cross-link from `list#Views`),
    `docs/settings.md` (paragraph at end of "Views Section"),
    `artifacts/specs/s0003-artifacts-os-cli-module.md` (Command
    Set entry). See spec §12.4.

## Verification

- [x] Spec sub-task merged and approved before implementation
      starts (see [[t0065-spec-cli-list-defined-views]]; spec
      [[artifacts/specs/s0016-cli-list-defined-views]] exists).
- [ ] `artifacts views` lists every view defined in
      `artifacts/artifacts.yaml` (one row per view, sorted by
      name).
- [ ] Default table shows `name`, `kind`, `columns`, `sort`,
      `default-for` columns; empty cells render `(any)` /
      `(none)` per spec §4.
- [ ] Long `columns` strings (>60 chars) truncate to 57 + `…`
      in the table; full value preserved in `-j`.
- [ ] `artifacts views -q` emits one view name per line,
      alphabetically sorted, no binding info.
- [ ] `artifacts views -j` emits the spec §6 object shape:
      `{"views": [...], "default_views": {...}}` with per-view
      `default_for` arrays.
- [ ] `-q` and `-j` are mutually exclusive (argparse exits 2).
- [ ] No `views:` section / empty `views:` map → stderr hint,
      exit 0, no table; `-q` produces no stdout; `-j` emits a
      well-formed empty payload.
- [ ] Malformed view entry surfaces the parser error (exit 1,
      stderr `error: view entry missing required 'columns'
      field`).
- [ ] `tests/cli/test_views_cmd.py` covers all 13 cases listed
      in spec §12.3; full `pytest` suite passes.
- [ ] `src/artifacts_os/cli/README.md`, `docs/settings.md`, and
      `artifacts/specs/s0003-artifacts-os-cli-module.md` updated
      per spec §12.4.
- [ ] `artifacts views` appears in `artifacts --help`.
