---
kind: task
id: t0064
name: cli-list-defined-views-command
type: feature
status: done
assignee: project-manager
owner: user
created: 2026-05-02
subtasks:
  - "[[t0065-spec-cli-list-defined-views]]"
  - "[[t0067-implement-cli-list-defined-views]]"
  - "[[t0069-spec-cli-views-detail-by]]"
  - "[[t0072-implement-cli-views-detail-mode]]"
artifacts:
  - "[[artifacts/specs/s0016-cli-list-defined-views]]"
started: 2026-05-02
completed: 2026-05-02
---

# CLI: `artifacts views` Command

The umbrella feature for the `artifacts views` discoverability
command. Delivered in iterations:

- **Iteration 1 — list mode** (shipped, t0067): `artifacts views`
  lists every defined view in a table, with `-q` and `-j`
  variants. Spec: [[artifacts/specs/s0016-cli-list-defined-views]].
- **Iteration 2 — detail mode** (in progress, t0069):
  `artifacts views <name>` shows the full definition of a single
  view (filters, columns, sort, default-for) without the table-
  level truncation.

## User Story (Iteration 1 — list)

**As a** vault user who has named views defined in
`artifacts/artifacts.yaml`,
**I want** a CLI command that lists every defined view (and which
views are bound as defaults per kind),
**so that** I can discover available presets without opening the
YAML file by hand and decide which to invoke via
`artifacts list --view <name>`.

## User Story (Iteration 2 — detail)

**As a** vault user who has discovered a view via
`artifacts views`,
**I want** to invoke `artifacts views <view_name>` to see that
view's full definition (untruncated columns, full filters dict,
sort, default-for binding),
**so that** I can inspect a single preset before invoking it via
`artifacts list --view <name>` or before editing it in
`artifacts.yaml`.

## Why

Views were introduced by [[t0047-cli-list-named-views]] and ship as
a discoverability feature — but right now they are only discoverable
by reading `artifacts/artifacts.yaml` directly. The CLI already
exposes its sibling concept (kinds) via `artifacts kinds`
([[t0021-add-artifacts-kinds-subcommand-to]]); views deserve a
parallel surface so operators, slash-command authors, and new
contributors can explore what's available. Iteration 1 covered
list-style discovery; iteration 2 closes the gap that the
list-mode table intentionally leaves (truncated `columns`, no
`filters` column) for single-record inspection — a gap explicitly
deferred in spec [[artifacts/specs/s0016-cli-list-defined-views]]
§11 until a user asked.

## Sub-tasks

### Iteration 1 — list mode (shipped)

- [[t0065-spec-cli-list-defined-views]] — architect produced the
  spec ([[artifacts/specs/s0016-cli-list-defined-views]]); status:
  `done`.
- [[t0067-implement-cli-list-defined-views]] — developer
  implemented the spec end-to-end; status: `done`.

### Iteration 2 — detail mode (in progress)

- [[t0069-spec-cli-views-detail-by]] — architect produced the
  spec as a §15 addendum to
  [[artifacts/specs/s0016-cli-list-defined-views]]; status:
  `done`.
- [[t0072-implement-cli-views-detail-mode]] — developer
  implements §15 end-to-end; status: `ready`.

## Tech Requirements — Iteration 1 (list mode, finalized)

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

## Tech Requirements — Iteration 2 (detail mode, finalized)

Authoritative spec: [[artifacts/specs/s0016-cli-list-defined-views]]
**§15** (addendum). Requirements below are normative; refer to
the addendum for rationale, decision tables, and worked
examples.

1. **CLI surface** — extend the existing `artifacts views`
   subparser with a single optional positional `view_name`
   (`nargs="?"`). Positional supplied → detail mode; positional
   absent → unchanged list mode (§§3–10). See spec §15.2.
2. **Single-name only** — `nargs="?"`, not `nargs="+"`. No
   multi-name support. See §15.2.2.
3. **Default detail output** — two-column key/value Rich table
   (`field` / `value`) with six rows in spec order: `name`,
   `kind` (lifted from `filters.kind`, or `(any)`), `columns`
   (**untruncated**), `filters` (multi-line indented JSON, or
   `(none)`), `sort` (or `(none)`), `default-for` (comma-
   separated bound kinds, or `(none)`). See §15.3.
4. **`filters` rendering** — `json.dumps(filters, indent=2,
   sort_keys=True, default=str)`; `kind` key is **kept** in the
   filters cell even though it is also lifted to row 2. See
   §15.3.3.
5. **`-q` (quiet) with positional** — print **only**
   `view.columns` on one line. Deliberate divergence from
   list-mode `-q` (which prints view names). Composes with
   `art list --fields "$(art views ready -q)"`. See §15.4.
6. **`-j` (JSON) with positional** — single JSON object equal
   to one element of list-mode's `views[]` array
   (`{name, columns, filters, sort, default_for}`, schema
   per §6.1). **Not** wrapped in `{"views": [...]}`. **No**
   top-level `default_views` map. See §15.5.
7. **Unknown view name** — exit `2`, stderr
   `error: unknown view '<name>'`. Append `Did you mean: …`
   line via `difflib.get_close_matches(name, names, n=3,
   cutoff=0.6)` when candidates exist. Same exit/message in
   `-q` and `-j` modes. See §15.6.
8. **Mutex `-q` / `-j` with positional** — argparse mutex
   group rejects unchanged. See §15.7.
9. **Malformed view entry + positional** — `ValueError`
   re-raise propagates before dispatch (exit 1, list-mode error
   path). See §15.8.
10. **Empty / missing `views:` + positional** — collapses into
    the unknown-view error (exit 2, no "no views defined"
    hint). List-mode empty-vault behaviour (§8) is unchanged
    when no positional is supplied. See §15.9.
11. **Dispatch** — `if args.name is None:` branch in
    `views.py:run`, with private `_run_list` / `_run_detail`
    helpers in the same file. Loader call and `default_views`
    reverse-index happen **once** before dispatch; both paths
    consume them. See §15.9.
12. **No-op zones** — no changes required to
    `cli/__init__.py`, `views/models.py`, or the registration
    mutex group (§15.11). Reuse only.
13. **Docs** — `cli/README.md` views section gains a
    "Detail mode" subsection;
    `artifacts/specs/s0003-artifacts-os-cli-module.md` Command
    Set row updated to `views [<view_name>] [-q|-j]`. No
    changes to `docs/settings.md`, `s0007`, or `s0012`. See
    §15.10.

## Verification — Iteration 1 (list mode)

- [x] Spec sub-task merged and approved before implementation
      starts (see [[t0065-spec-cli-list-defined-views]]; spec
      [[artifacts/specs/s0016-cli-list-defined-views]] exists).
- [x] `artifacts views` lists every view defined in
      `artifacts/artifacts.yaml` (one row per view, sorted by
      name).
- [x] Default table shows `name`, `kind`, `columns`, `sort`,
      `default-for` columns; empty cells render `(any)` /
      `(none)` per spec §4.
- [x] Long `columns` strings (>60 chars) truncate to 57 + `…`
      in the table; full value preserved in `-j`.
- [x] `artifacts views -q` emits one view name per line,
      alphabetically sorted, no binding info.
- [x] `artifacts views -j` emits the spec §6 object shape:
      `{"views": [...], "default_views": {...}}` with per-view
      `default_for` arrays.
- [x] `-q` and `-j` are mutually exclusive (argparse exits 2).
- [x] No `views:` section / empty `views:` map → stderr hint,
      exit 0, no table; `-q` produces no stdout; `-j` emits a
      well-formed empty payload.
- [x] Malformed view entry surfaces the parser error (exit 1,
      stderr `error: view entry missing required 'columns'
      field`).
- [x] `tests/cli/test_views_cmd.py` covers all 13 cases listed
      in spec §12.3; full `pytest` suite passes.
- [x] `src/artifacts_os/cli/README.md`, `docs/settings.md`, and
      `artifacts/specs/s0003-artifacts-os-cli-module.md` updated
      per spec §12.4.
- [x] `artifacts views` appears in `artifacts --help`.

## Verification — Iteration 2 (detail mode)

- [x] Iteration-2 spec merged and approved (see
      [[t0069-spec-cli-views-detail-by]]; addendum lives at
      [[artifacts/specs/s0016-cli-list-defined-views]] §15).
- [ ] `artifacts views <view_name>` prints the §15.3.1
      two-column key/value table with all six rows in the
      specified order.
- [ ] `kind` row lifts the kind filter or renders `(any)`;
      `filters` row stays authoritative (still includes `kind`).
- [ ] `columns` row is **untruncated** for >60-char strings
      (the principal value-add over list mode; case 20).
- [ ] `filters` cell renders multi-line indented JSON
      (`indent=2, sort_keys=True`); empty filters render
      `(none)` (§15.3.3, cases 16, 21).
- [ ] `sort` and `default-for` rows render correctly
      (verbatim / `(none)`; comma-separated alphabetised bound
      kinds; cases 17–19).
- [ ] `artifacts views <name> -q` prints **only**
      `view.columns` on one line (§15.4, case 22).
- [ ] `artifacts views <name> -j` emits a single JSON object
      with `{name, columns, filters, sort, default_for}`; not
      array-wrapped; no top-level `default_views` (§15.5,
      cases 23–26).
- [ ] Unknown view → exit 2, stderr
      `error: unknown view '<name>'`; `Did you mean: …`
      appears when `difflib` returns matches (§15.6,
      cases 27–30).
- [ ] Empty / missing `views:` + positional → unknown-view
      error (no "no views defined" hint; §15.9, cases 31, 32).
- [ ] `-q` + `-j` mutex still rejects with positional present
      (case 33). Malformed view + positional → exit 1 via
      `ValueError` re-raise (case 34).
- [ ] List mode unchanged — running `artifacts views` with no
      positional still produces the §4 list-mode table; all 13
      list-mode tests from §12.3 still pass (case 35).
- [ ] `tests/cli/test_views_cmd.py` covers all 22 detail-mode
      cases listed in §15.12 (cases 14–35); full `pytest` suite
      passes.
- [ ] `src/artifacts_os/cli/README.md` gains a "Detail mode"
      subsection per §15.10.
- [ ] `artifacts/specs/s0003-artifacts-os-cli-module.md`
      Command Set row updated to `views [<view_name>] [-q|-j]`
      per §15.10.
- [ ] `artifacts views --help` reflects the new positional and
      help text.
