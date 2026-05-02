---
kind: spec
id: s0016
name: cli-list-defined-views
status: draft
created: 2026-05-02
agent: architect
task: "[[t0065-spec-cli-list-defined-views]]"
---

# CLI: List Defined Views

Sub-spec of [[s0003-artifacts-os-cli-module]]. Specifies the
contract for `artifacts views`, a discoverability surface for the
named views already modelled in [[s0007-artifacts-os-views-module]]
and consumed by [[s0012-cli-list-named-views]].

The data model is shipped (`ViewConfig`, `ViewsConfig`,
`ViewsSettings`); the CLI currently exposes views only through
`artifacts list --view <name>`. This spec adds a parallel **read-
only** command that lists every defined view (and the per-kind
`default_views` bindings) so users can discover what is available
without opening `artifacts.yaml`.

## 1. Background and Cross-References

- **Closest sibling** —
  `src/artifacts_os/cli/commands/kinds.py` ([[s0003-artifacts-os-cli-module]]).
  This spec mirrors its argument shape, output formats, and
  exit-code conventions verbatim.
- **Data model** — [[s0007-artifacts-os-views-module]]
  (`ViewConfig`, `ViewsConfig`, `ViewsSettings.from_base`). This
  spec adds no new fields and no new validation rules.
- **Existing consumer** — [[s0012-cli-list-named-views]]; the
  `artifacts list --view` precedence model. The `views` command
  is **read-only** and never invokes that resolver.
- **Settings loader** — `_load_views_settings(root)` in
  `src/artifacts_os/cli/__init__.py`. The `views` command reuses
  it directly; no new loader helper is required.
- **Vault example** — `artifacts/artifacts.yaml`
  (`views:` and `default_views:` sections in this repository).

## 2. Goals and Non-Goals

**Goals:**

- Add `artifacts views` — a single subcommand that lists every
  view defined in `artifacts.yaml`.
- Surface `default_views[kind] = view` bindings inline so users
  can see at a glance which view fires automatically per kind.
- Match `artifacts kinds` for argument shape (`-q`, `-j`, mutually
  exclusive), exit codes, and table style.
- Behave gracefully when no views are defined.

**Non-goals:**

- Editing or creating views from the CLI (out of scope; views are
  authored by hand in `artifacts.yaml`).
- Validating view definitions — that is `validate`'s job. The
  `views` command surfaces the parser's existing errors but does
  not add new validation.
- A detail subcommand (`artifacts views show <name>`). Called out
  as a possible follow-up in §11; not specified here.
- New `--view` semantics on `artifacts list`. That contract is
  fully owned by [[s0012-cli-list-named-views]] and is unchanged
  by this spec.

## 3. CLI Surface

```text
artifacts views [-q | -j]
```

| Flag | Type | Description |
|------|------|-------------|
| `-q`, `--quiet`     | bool | One view name per line. Mutually exclusive with `-j`. |
| `-j`, `--json`      | bool | JSON output. Mutually exclusive with `-q`. |

**Decision — subcommand name:** `views` (plural). Rationale:
mirrors `artifacts kinds` exactly. Discoverability via
`artifacts --help` is the primary user benefit; a singular form
(`view`) would create confusion with `artifacts list --view`.

**Decision — no positional arg, no `--sort`, no `--defaults`
filter flag.** The output is small (typically <30 entries even
in a large vault). Adding flags adds surface area without solving
a real ergonomic problem; `grep`, `jq`, and `awk` already cover
filtering and reformatting needs against `-q`/`-j` output.

**Decision — collision check with `artifacts list --view`:**
None. `--view` is a flag on `list`; `views` is a top-level
subcommand. They live in disjoint argparse namespaces.

**Decision — alias.** None added by this spec. The default `cli.aliases`
section in `artifacts/artifacts.yaml` may pick a short alias
(e.g. `vw: views`) once the command ships; that is a per-vault
choice, not a library default.

## 4. Default Output (Rich Table)

Five columns, in this fixed order:

| # | Column | Source | Notes |
|---|--------|--------|-------|
| 1 | `name`        | dict key in `views:`                | Bold style; the view's identifier as passed to `--view`. |
| 2 | `kind`        | `view.filters.get("kind")`          | The kind filter, when set. Empty cell otherwise (the view is cross-kind). Renders `[dim](any)[/dim]` for empty. |
| 3 | `columns`     | `view.columns`                      | Field-spec string, **truncated** to fit (see §4.1). |
| 4 | `sort`        | `view.sort`                         | Empty cell when `None`; renders `[dim](none)[/dim]`. |
| 5 | `default-for` | reverse of `default_views`          | Comma-separated list of kinds where this view is bound as the default. Empty when the view is not bound; renders `[dim](none)[/dim]`. |

`filters` is intentionally **not** a column. Filter dicts can be
arbitrarily deep and dominate the table width; users who need to
inspect filters reach for `-j`. The `kind` column lifts the most
common filter key into the table because cross-kind vs.
kind-specific is the primary mental axis users sort on.

### 4.1 Long-value rendering

- `columns` (column 3): If the field-spec string is longer than
  60 characters, truncate to 57 characters and append `…`. The
  full value is always available via `-j`.
- `default-for` (column 5): Comma-separated kind names (e.g.
  `task, note`). No truncation — the cardinality of `default_views`
  is bounded by registered kinds, which is small.

### 4.2 Sort order

Rows are sorted **alphabetically by `name`** (ascending,
case-sensitive ASCII order). Same convention as
`artifacts kinds`. No `--sort` flag — see §3.

### 4.3 Worked example

Given the views section in this repository's
`artifacts/artifacts.yaml`:

```text
$ artifacts views
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ name                   ┃ kind  ┃ columns                                 ┃ sort       ┃ default-for┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ active                 │ task  │ id,name,assignee,status                 │ -started   │ (none)     │
│ agents                 │ agent │ name,description                        │ name       │ agent      │
│ architect-queue        │ task  │ id,name,status,created:date             │ status     │ (none)     │
│ author-queue           │ task  │ id,name,status,created:date             │ status     │ (none)     │
│ backlog                │ task  │ id,name,assignee,type                   │ created    │ (none)     │
│ developer-queue        │ task  │ id,name,status,created:date             │ status     │ (none)     │
│ done                   │ task  │ id,name,assignee,completed:date         │ -completed │ (none)     │
│ features               │ task  │ id,name,status,assignee                 │ -created   │ (none)     │
│ implementations        │ task  │ id,name,status,assignee                 │ -created   │ (none)     │
│ note                   │ note  │ id,name,type,created:date               │ -created   │ note       │
│ note-planning          │ note  │ id,name,created:date                    │ -created   │ (none)     │
│ ready                  │ task  │ id,name,assignee,created:date           │ created    │ task       │
│ recent                 │ (any) │ id,kind,name,status,created:date        │ -created   │ (none)     │
│ rejected               │ task  │ id,name,assignee,owner                  │ -created   │ (none)     │
│ research               │ research │ id,name,status,created:date          │ -created   │ research   │
│ review                 │ task  │ id,name,assignee,owner                  │ -created   │ (none)     │
│ spec                   │ spec  │ id,name,status,created:date             │ -created   │ spec       │
│ specs-approved         │ spec  │ id,name,agent,created:date              │ -created   │ (none)     │
│ specs-draft            │ spec  │ id,name,agent,created:date              │ -created   │ (none)     │
│ task-docs              │ task  │ id,name,status,assignee                 │ -created   │ (none)     │
│ task-specs             │ task  │ id,name,status,assignee                 │ -created   │ (none)     │
│ technical-writer-queue │ task  │ id,name,status,created:date             │ status     │ (none)     │
└────────────────────────┴───────┴─────────────────────────────────────────┴────────────┴────────────┘
```

(Box-drawing characters are illustrative; actual width adapts to
the terminal as `rich` decides.)

## 5. `-q` (Quiet) Format

One view name per line, sorted alphabetically. Identical
mechanically to `artifacts kinds -q`:

```text
$ artifacts views -q
active
agents
architect-queue
author-queue
backlog
…
technical-writer-queue
```

`default_views` bindings are **not** emitted in `-q` mode. Quiet
mode is for shell scripting (`for v in $(artifacts views -q); do
…`); injecting binding metadata would break that contract.
Consumers who need bindings use `-j`.

## 6. `-j` (JSON) Format

A single JSON **object** with two keys:

```json
{
  "views": [
    {
      "name": "active",
      "columns": "id,name,assignee,status",
      "filters": { "kind": "task", "status": "in-progress" },
      "sort": "-started",
      "default_for": []
    },
    {
      "name": "ready",
      "columns": "id,name,assignee,created:date",
      "filters": { "kind": "task", "status": "ready" },
      "sort": "created",
      "default_for": ["task"]
    }
  ],
  "default_views": {
    "agent": "agents",
    "note": "note",
    "research": "research",
    "spec": "spec",
    "task": "ready"
  }
}
```

### 6.1 `views` array

- One element per defined view. Sorted alphabetically by `name`.
- Object schema:
  | Key           | Type            | Notes |
  |---------------|-----------------|-------|
  | `name`        | string          | View identifier (the `views:` dict key). |
  | `columns`     | string          | Verbatim `ViewConfig.columns`. Field-spec syntax, not parsed. |
  | `filters`     | object          | Verbatim `ViewConfig.filters`. Empty `{}` when none. |
  | `sort`        | string \| null  | Verbatim `ViewConfig.sort`. `null` when absent. |
  | `default_for` | array of string | Kinds that bind this view via `default_views`. Sorted alphabetically. Empty `[]` when no bindings. |

### 6.2 `default_views` object

Verbatim copy of `ViewsConfig.default_views`: an object mapping
kind name → view name. Empty `{}` when no bindings. Included
even though the same data is also available reversed in each
view's `default_for` field, because:

1. Some consumers (slash-command authors) want the kind→view
   direction to render "what fires when I pass `--kind X`".
2. The JSON shape is then symmetric with the input YAML, which
   makes round-tripping trivial.

### 6.3 Decision — object shape vs. flat array

**Decided: object with `views` and `default_views` keys.**

Alternative considered: emit a flat array of view objects,
relying on each row's `default_for` field to convey bindings.
Rejected because:

- The kind→view direction (`default_views`) is the natural query
  for "what happens when I run `artifacts list --kind task`".
- Symmetry with the YAML input is valuable — copy-pasting from
  the JSON output back into a settings file is one fewer
  transformation for users.
- The cost is one extra wrapping object; for downstream `jq`
  consumers, `jq '.views[]'` is equivalent to the flat-array
  form.

## 7. `default_views` Rendering — Rationale

**Decided: inline `default-for` column on each row.** The same
information appears in `-j` as the per-view `default_for` list
**and** the top-level `default_views` object.

Alternatives considered:

| Option | Decision | Reason |
|--------|----------|--------|
| Inline column on each view row | **Chosen** | Single-pass scan; the binding axis is per-view, so it belongs on the view's row. |
| Footer / separate section under the table | Rejected | Splits attention; users would hunt the footer for the binding of a specific view. |
| Separate flag `artifacts views --defaults` | Rejected | Adds surface area for a feature already cheap to inline. |
| Separate column `kind-bound` (boolean) | Rejected | Discards the kind name; users still need to look at YAML to know which kind. |

The inline column is empty (`(none)`) for the majority of views
(only ~5 of ~22 views in the example are defaults), which keeps
the table visually quiet for non-bound rows.

## 8. Empty / Missing Configuration

Three distinct states. All three exit `0` (the command succeeded;
the absence of views is data, not an error).

| State | Detection | Default output | `-q` | `-j` |
|-------|-----------|----------------|------|------|
| **No `artifacts.yaml`** (vault missing entirely) | `find_vault_root()` returns `None` | falls through existing `cli/__init__.py` handling: stderr `error: not in an artifacts-os project`, exit `2`. | same | same |
| **`artifacts.yaml` present, no `views:` and no `default_views:`** | `ViewsSettings.from_base(...).views is None` | stderr: `no views defined in artifacts.yaml`. **No table.** Exit `0`. | no stdout; exit `0`. | `{"views": [], "default_views": {}}`; exit `0`. |
| **`views:` empty map, or only `default_views:` set** | `ViewsSettings.views is not None` and `len(views.views) == 0` | stderr: `no views defined in artifacts.yaml`. **No table.** Exit `0`. *If `default_views` is non-empty, the stderr line still fires; the binding has no effect without a defined view, and a follow-up `validate` task can flag dangling bindings.* | no stdout; exit `0`. | `{"views": [], "default_views": {…}}`; exit `0`. |

**Decision — empty body suppression in default mode.** Print the
stderr hint and **suppress** the table (don't render an empty
table with just headers). Rationale: an empty rich table is
visually noisy and looks like a bug. The stderr line gives the
user a clear next step (open `artifacts.yaml`).

**Decision — exit code 0, not 2, for empty / missing-views
state.** This is consistent with `artifacts list` returning 0 for
an empty match set. The command is read-only discovery; "nothing
to show" is a valid result.

**Decision — no error from a non-loadable `artifacts.yaml`.**
`_load_views_settings` already swallows load errors and returns
`None` (existing convention; see `cli/__init__.py` line 39–52).
The `views` command treats `None` exactly like the
"no `views:` section" case: stderr hint, exit 0. Rationale:
keeping the error surface narrow — `validate` is the command
that should surface YAML-syntax errors with a non-zero exit,
not `views`.

## 9. Mutually Exclusive Flags

`-q` and `-j` are members of an `argparse` mutually exclusive
group, exactly like `artifacts kinds`. Argparse handles the
conflict natively (exit 2, stderr message generated by argparse).
No custom validation logic.

## 10. Error Handling Summary

| Condition | Exit | Stderr message | Source |
|-----------|------|----------------|--------|
| Outside an `artifacts-os` project | `2` | `error: not in an artifacts-os project` | existing `cli/__init__.py` |
| `artifacts.yaml` malformed YAML / load fails | `0` | `no views defined in artifacts.yaml` | `_load_views_settings` returns `None`; we treat as empty |
| `views:` entry missing required `columns` field | `1` (re-raised `ValueError`) | `error: view entry missing required 'columns' field` | `ViewConfig._parse_view`; surfaced by the existing `except ValueError` cascade in `cli/__init__.py:_run` |
| `-q` and `-j` both passed | `2` | argparse: `argument -j: not allowed with argument -q` | argparse mutually exclusive group |
| `views:` section absent or empty | `0` | `no views defined in artifacts.yaml` | this spec, §8 |
| `views:` populated, command succeeds | `0` | (none) | normal path |

The deliberate divergence is **malformed YAML → exit 0**: see §8
and the rationale "validate is the place to fail loudly". For
parser errors (a view entry missing `columns`), we let
`ViewsSettings.from_base` raise `ValueError`, which the existing
`_run` cascade maps to exit 1. This matches the behaviour
`artifacts list --view foo` exhibits today when `foo`'s entry is
malformed.

## 11. Out of Scope (Follow-Up Candidates)

These are noted explicitly so the implementation sub-task does
not accidentally pick them up:

- **`artifacts views show <name>`** — detail view of a single
  view (full filters dict, parsed columns, formatted sort).
  Useful, but a separate UX problem (single-record rendering).
  Defer until a user asks.
- **`artifacts views --validate`** — flag dangling bindings
  (`default_views[k] = "v"` where `v ∉ views`), warn on unused
  views, etc. Belongs under `validate`, not `views`.
- **`artifacts views --kind <k>`** — filter the list to views
  whose `filters.kind == <k>`. Trivially expressible as
  `artifacts views -j | jq '.views[] | select(.filters.kind == "k")'`;
  add only if grep-on-table proves insufficient.
- **Sort by `default-for` first** — surfaces "the view that fires
  for kind X" at the top. Defer; alphabetical-by-name is the
  predictable contract.

## 12. Implementation Outline

This spec is delivered by [[t0064-cli-list-defined-views-command]]
via a follow-up implementation sub-task. The following
file-level changes are normative.

### 12.1 New file — `src/artifacts_os/cli/commands/views.py`

Mirror the shape of `commands/kinds.py` (~60 lines).

```python
"""cli views command — list named views defined in artifacts.yaml."""

import json
import sys

from rich.console import Console
from rich.table import Table

from artifacts_os.core import Registry


def register(subparsers) -> None:
    p = subparsers.add_parser(
        "views",
        help="list defined views",
        description=(
            "List all named views defined in artifacts/artifacts.yaml, "
            "including the per-kind default_views bindings."
        ),
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-q", "--quiet", action="store_true",
                      help="one view name per line")
    mode.add_argument("-j", "--json", action="store_true", dest="json_out",
                      help="JSON output")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    # Reuse the existing loader; it returns None on any error.
    from artifacts_os.cli import _load_views_settings
    settings = _load_views_settings(registry.root)

    views_cfg = settings.views if settings is not None else None
    views_map = views_cfg.views if views_cfg is not None else {}
    defaults  = views_cfg.default_views if views_cfg is not None else {}

    # Empty path
    if not views_map:
        if args.json_out:
            print(json.dumps({"views": [], "default_views": dict(defaults)},
                             default=str))
            return 0
        if args.quiet:
            return 0
        print("no views defined in artifacts.yaml", file=sys.stderr)
        return 0

    # Reverse-index default_views: kind → view  →  view → [kinds]
    reverse: dict[str, list[str]] = {}
    for kind, view_name in defaults.items():
        reverse.setdefault(view_name, []).append(kind)
    for kinds_list in reverse.values():
        kinds_list.sort()

    names = sorted(views_map.keys())

    if args.quiet:
        for name in names:
            print(name)
        return 0

    if args.json_out:
        payload = {
            "views": [
                {
                    "name": name,
                    "columns": views_map[name].columns,
                    "filters": dict(views_map[name].filters),
                    "sort": views_map[name].sort,
                    "default_for": reverse.get(name, []),
                }
                for name in names
            ],
            "default_views": dict(defaults),
        }
        print(json.dumps(payload, default=str))
        return 0

    # Default — rich table
    table = Table(show_header=True, header_style="bold")
    table.add_column("name")
    table.add_column("kind")
    table.add_column("columns")
    table.add_column("sort")
    table.add_column("default-for")

    for name in names:
        v = views_map[name]
        kind = v.filters.get("kind") if v.filters else None
        kind_cell = str(kind) if kind else "[dim](any)[/dim]"
        cols = v.columns
        if len(cols) > 60:
            cols = cols[:57] + "…"
        sort_cell = v.sort if v.sort else "[dim](none)[/dim]"
        bound = reverse.get(name, [])
        bound_cell = ", ".join(bound) if bound else "[dim](none)[/dim]"
        table.add_row(name, kind_cell, cols, sort_cell, bound_cell)

    Console().print(table)
    return 0
```

### 12.2 Edit — `src/artifacts_os/cli/__init__.py`

Add the import and register the subparser. Two single-line
diffs:

```python
from artifacts_os.cli.commands import views as _views_cmd       # new
# ...
_views_cmd.register(subparsers)                                  # new
```

Place the registration adjacent to `_kinds_cmd.register(...)`
to preserve the kinship.

### 12.3 Tests — `tests/cli/test_views_cmd.py` (new)

Required cases (the implementation sub-task must cover all of these):

1. **Default table — populated.** `views:` and `default_views:`
   set. Assert table contains one row per view, includes the
   bound view's `default-for` cell, and is sorted by name.
2. **Default table — view with no kind filter.** Renders
   `(any)` in the kind column.
3. **Default table — view with no sort.** Renders `(none)` in
   the sort column.
4. **`-q` quiet.** One name per line, alphabetically sorted, no
   binding info, exit 0.
5. **`-j` JSON, populated.** Object with `views` (sorted array)
   and `default_views` (verbatim dict). `default_for` populated
   correctly for bound views, `[]` otherwise.
6. **`-j` JSON, `filters` empty.** `"filters": {}` in JSON.
7. **`-j` JSON, `sort` absent.** `"sort": null` in JSON.
8. **No `views:` section.** Default mode prints
   `no views defined in artifacts.yaml` to stderr, suppresses
   table, exits 0. `-q` produces no stdout, exits 0. `-j`
   produces `{"views": [], "default_views": {}}`, exits 0.
9. **`views:` empty map, `default_views:` set.** Same as case 8
   but `-j` includes the `default_views` object verbatim.
10. **Mutually exclusive `-q -j`.** argparse exits 2.
11. **Malformed view entry (missing `columns`).** Exit 1, stderr
    contains `error: view entry missing required 'columns'
    field`.
12. **Long `columns` string truncation.** A `columns` value
    longer than 60 chars is truncated to 57 + `…` in the table;
    the full value still appears in `-j`.
13. **Multiple kinds bound to one view.** `default_views: {task:
    v, note: v}` produces `default_for: ["note", "task"]`
    (sorted) in JSON and `note, task` in the table.

Use the existing `vault` and `make_artifacts_yaml` test
helpers from `tests/cli/conftest.py`.

### 12.4 Documentation updates

- **`src/artifacts_os/cli/README.md`** — add a `views` section
  under "Commands", positioned immediately after `kinds`. Mirror
  the `kinds` section's structure (synopsis, flags table, three
  examples). Add a short cross-link from the existing
  `list#Views` subsection ("To see what views are defined,
  run `artifacts views`.").
- **`docs/settings.md`** — append one paragraph at the end of
  the "Views Section" cross-linking to `artifacts views` for
  discoverability ("Run `artifacts views` to list every defined
  view from the command line; see
  [`cli/README.md`](../src/artifacts_os/cli/README.md) for the
  full reference.").
- **`s0003-artifacts-os-cli-module.md`** — add `views` to the
  "Command Set" enumeration (one line, pointing at this spec).

No changes to `s0007-artifacts-os-views-module.md` (data model
is untouched) or to `s0012-cli-list-named-views.md` (resolver
contract is untouched).

## 13. Verification

The parent task [[t0064-cli-list-defined-views-command]] inherits
these checks. The implementation sub-task checklist must
include at least:

- [ ] `artifacts views` lists every view defined in
      `artifacts/artifacts.yaml` (one row per view, sorted by
      name).
- [ ] The `default-for` column shows the kind(s) for which a
      view is bound via `default_views`; empty cell renders
      `(none)`.
- [ ] `artifacts views -q` emits one view name per line,
      alphabetically sorted.
- [ ] `artifacts views -j` emits the object shape from §6
      (`{"views": [...], "default_views": {...}}`).
- [ ] `-q` and `-j` are mutually exclusive (argparse exits 2).
- [ ] No `views:` section / empty `views:` map → stderr hint,
      exit 0, no table; `-j` still emits a well-formed empty
      payload.
- [ ] Malformed view entry (`columns` missing) surfaces the
      `ViewsSettings` parser error (exit 1, stderr `error:
      view entry missing required 'columns' field`).
- [ ] `tests/cli/test_views_cmd.py` covers all 13 cases in §12.3.
- [ ] `src/artifacts_os/cli/README.md` and `docs/settings.md`
      updated per §12.4.
- [ ] `s0003-artifacts-os-cli-module.md` Command Set
      enumeration updated.

## 14. Decision Log

| Marker | Items |
|--------|-------|
| **Decided** | Subcommand name `views`. Five-column table (`name`, `kind`, `columns`, `sort`, `default-for`). `-q` is name-only; `-j` is `{views: [...], default_views: {...}}`. Empty / missing-views state is exit 0 with stderr hint. Malformed view entries exit 1 via the `ValueError` cascade. Sort: alphabetical by `name`. No `--sort` / `--defaults` / positional flags. |
| **Recommended** | Reuse the existing `_load_views_settings(root)` helper rather than introducing a new loader. Place the new command file at `src/artifacts_os/cli/commands/views.py` and the test file at `tests/cli/test_views_cmd.py`. |
| **Deferred** | `artifacts views show <name>` (detail view). `--validate` flag (belongs under `validate`). `--kind` filter (use `jq`). Sort-by-`default-for`. CLI-level alias (per-vault choice, not library default). |
