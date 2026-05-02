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

- **Detail mode for a single view** — full filters dict, parsed
  columns, formatted sort. **Status: spec'd in §15** as a
  positional `artifacts views <view_name>` (not a `show`
  sub-subcommand) per user request. Delivered by
  [[t0069-spec-cli-views-detail-by]] and a follow-up
  implementation sub-task.
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
| **Decided** | Subcommand name `views`. Five-column table (`name`, `kind`, `columns`, `sort`, `default-for`). `-q` is name-only; `-j` is `{views: [...], default_views: {...}}`. Empty / missing-views state is exit 0 with stderr hint. Malformed view entries exit 1 via the `ValueError` cascade. Sort: alphabetical by `name`. No `--sort` / `--defaults` / positional flags in list mode. |
| **Recommended** | Reuse the existing `_load_views_settings(root)` helper rather than introducing a new loader. Place the new command file at `src/artifacts_os/cli/commands/views.py` and the test file at `tests/cli/test_views_cmd.py`. |
| **Deferred** | `--validate` flag (belongs under `validate`). `--kind` filter (use `jq`). Sort-by-`default-for`. CLI-level alias (per-vault choice, not library default). |
| **Iteration 2** | Detail mode added in §15: positional `artifacts views <view_name>` for full single-view inspection (untruncated `columns`, full `filters` dict). |

---

## 15. Detail Mode — Iteration 2 Addendum

> **Provenance.** This section was added under
> [[t0069-spec-cli-views-detail-by]] to spec the detail-mode
> follow-up that §11 originally deferred. The list-mode contract
> in §§1–13 is unchanged.

### 15.1 Goal

Extend `artifacts views` so a vault user who has already
discovered a view (via `artifacts views`) can inspect that view's
**full** definition — including the `filters` dict (which the
list-mode table omits entirely) and the **untruncated** `columns`
field-spec (which the table truncates at 60 chars per §4.1).

The detail surface lives on the **same** subcommand and reuses
the same loader, the same mutually-exclusive `-q` / `-j` group,
the same registry path, and the same per-view JSON object schema
defined in §6.1. It adds one positional argument and one new
error path (unknown view name).

### 15.2 CLI Surface

```text
artifacts views [<view_name>] [-q | -j]
```

| Position | Type   | Description |
|----------|--------|-------------|
| `view_name` | str (optional, `nargs="?"`) | Name of a single defined view. When supplied, switches to **detail mode**. When absent, the command behaves exactly as specified in §§3–10 (list mode). |

#### 15.2.1 Decision — positional vs. `show` sub-subcommand

**Decided: positional `artifacts views <view_name>`** (the user's
ask). Rejected alternative: `artifacts views show <view_name>`.

Rationale:

| Axis | Positional | `show` sub-subcommand |
|------|------------|------------------------|
| Typing length | Shorter (`art views ready`) | Longer (`art views show ready`) |
| User's stated preference | ✅ asked for this shape | ✗ not asked |
| Argparse ergonomics | `nargs="?"` on the existing parser; no new sub-subparser | Requires nested `add_subparsers` on the views parser, doubling the help-tree depth |
| Symmetry with `artifacts kinds` | `kinds` has no detail mode today; either choice is unprecedented | same |
| Symmetry with `artifacts show <ref>` | Mismatched (`show` is a top-level command, not a verb on `views`) | Mismatched in a different direction (would imply `kinds show <name>` for parity, which we don't want) |
| Future ergonomic cost | If we later add `artifacts views <verb>` (e.g. `validate`), the positional shadows verb dispatch — but we have explicitly deferred such verbs (§11), and adding one would be a breaking change either way | None |

The shadowing risk in the last row is real but distant.
`artifacts views --validate` is already deferred to the `validate`
command per §11, so the `views` subparser is unlikely to grow
verbs. If a future feature genuinely needs a verb namespace, the
clean migration is to introduce it as a flag (`artifacts views
<name> --action`) rather than break the positional contract.

#### 15.2.2 Decision — `nargs="?"`, single name only

**Decided: single optional name** (`nargs="?"`).

Rejected: `nargs="+"` (multi-name detail mode). Multi-name
introduces three problems without solving any:

1. **Output-shape ambiguity.** Three plausible default-mode
   shapes (one detail block per name; a multi-row table; a
   panel grid) all add complexity. `-j` would have to choose
   between an array and a dict, neither of which matches §6.1.
2. **Error-path ambiguity.** If `art views a b c` and `b` is
   unknown, do we abort, skip, or partial-succeed? Each answer
   is defensible; none is obvious.
3. **No real ergonomic gap.** Users wanting multi-view JSON can
   already run `artifacts views -j | jq '.views[] | select(...)'`
   from the list-mode payload. Users wanting human-readable
   detail typically inspect one view at a time.

A user explicitly asking for multi-name later can be served by
adding `nargs` widening; the inverse migration is harder.

### 15.3 Default Output (Rich Table — Two Columns)

When `<view_name>` is supplied and neither `-q` nor `-j` is
passed, render a **two-column key/value Rich table** with one row
per field. Column 1 is the field key (label); column 2 is the
field's rendered value.

#### 15.3.1 Row order and contents

| # | Field        | Value source                                  | Rendering |
|---|--------------|-----------------------------------------------|-----------|
| 1 | `name`       | the positional argument (verbatim)            | bold style; the view's identifier. |
| 2 | `kind`       | `view.filters.get("kind")` if present         | the kind name (e.g. `task`); `[dim](any)[/dim]` when the view has no `kind` filter (cross-kind). |
| 3 | `columns`    | `view.columns` (untruncated)                  | verbatim field-spec string. **No truncation** — this is the detail mode's principal value-add over §4.1's 60-char list-mode truncation. |
| 4 | `filters`    | `view.filters`                                | rendered as **JSON with indent=2** so nested keys remain legible inside the cell; `[dim](none)[/dim]` when filters is empty (`{}`). The `kind` key is **kept** in this rendering even though it is also lifted into row 2 — the row-2 lift is a convenience; row 4 remains the authoritative full dict. |
| 5 | `sort`       | `view.sort`                                   | verbatim; `[dim](none)[/dim]` when `None`. |
| 6 | `default-for`| reverse of `default_views` for this view      | comma-separated list of kinds bound to this view via `default_views`, alphabetically sorted (e.g. `note, task`); `[dim](none)[/dim]` when not bound. Same rendering rule as list-mode §4 column 5. |

The two-column table style is consistent with the visual language
of the list-mode table (also Rich, also `show_header=True`,
`header_style="bold"`). Header labels for the two columns:
`field` and `value`.

#### 15.3.2 Decision — table vs. multi-line block vs. panel

**Decided: two-column Rich Table.**

Rejected:

| Option | Reason rejected |
|--------|-----------------|
| Multi-line key-value text block (e.g. `name: ready\\ncolumns: …`) | Cleaner code but inconsistent with the list-mode table aesthetic; users get one visual style across `kinds`, `views` (list), and `views` (detail). |
| Rich `Panel` (boxed, multi-line) | Heavier than warranted for ≤6 fields; panels are better for prose, not key/value. |
| Two side-by-side panels (one per column group) | Over-engineered. |

#### 15.3.3 Decision — render `filters` as indented JSON

**Decided: `json.dumps(filters, indent=2, sort_keys=True,
default=str)`** for the filters cell, with `[dim](none)[/dim]`
when empty.

Rejected alternatives:

- **YAML dump.** Would require importing `yaml` (currently not
  used by `views.py`). JSON is already imported and is
  unambiguous for the dict structure.
- **One row per filter key.** Splitting filters across multiple
  table rows would conflict with the fixed 6-row layout above
  (the row count would become data-dependent, and the
  list/detail dispatch would need a different table shape per
  view). Single-cell rendering keeps the table shape stable.
- **Single-line JSON (no indent).** Long nested dicts become
  hard to scan. `indent=2` keeps each key on its own line in
  the cell.

`sort_keys=True` keeps the filters cell deterministic across
runs, matching the discoverability goal of §1.

#### 15.3.4 Worked example — default mode

Given the `ready` view from this repo's `artifacts/artifacts.yaml`:

```yaml
views:
  ready:
    columns: id,name,assignee,created:date
    filters:
      kind: task
      status: ready
    sort: created
default_views:
  task: ready
```

```text
$ artifacts views ready
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ field       ┃ value                                       ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ name        │ ready                                       │
│ kind        │ task                                        │
│ columns     │ id,name,assignee,created:date               │
│ filters     │ {                                           │
│             │   "kind": "task",                           │
│             │   "status": "ready"                         │
│             │ }                                           │
│ sort        │ created                                     │
│ default-for │ task                                        │
└─────────────┴─────────────────────────────────────────────┘
```

(Box-drawing characters illustrative; actual width adapts.)

For a cross-kind view with no sort and no binding:

```text
$ artifacts views recent
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ field       ┃ value                                       ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ name        │ recent                                      │
│ kind        │ (any)                                       │
│ columns     │ id,kind,name,status,created:date            │
│ filters     │ (none)                                      │
│ sort        │ -created                                    │
│ default-for │ (none)                                      │
└─────────────┴─────────────────────────────────────────────┘
```

### 15.4 `-q` (Quiet) With Positional

**Decided: `-q` prints `view.columns` on a single line.**

```text
$ artifacts views ready -q
id,name,assignee,created:date
```

#### 15.4.1 Rationale — divergence from list-mode `-q`

List-mode `-q` (§5) prints view **names** because the name is the
per-row identifier. In detail mode the user has *already supplied*
the name as the positional argument; echoing it back is
redundant. The next-most-script-useful single-line value is the
`columns` field-spec string, which composes directly with
`artifacts list --fields`:

```bash
art list --fields "$(art views ready -q)"
```

This makes detail-mode `-q` **deliberately divergent** from
list-mode `-q`: in both modes `-q` returns "the most useful
single string for shell substitution", but the *content* differs
because the inputs differ. Document this divergence explicitly in
the README per §15.10.

Rejected alternatives:

| Option | Reason rejected |
|--------|-----------------|
| Echo `name` (the positional) | Redundant — the user just typed it. |
| Print nothing | A flag that does nothing is a footgun. |
| Print `name<TAB>columns` | Tab-separated breaks the "one identifier per line" convention. |
| Reject `-q` with positional (argparse error) | Custom validation logic for marginal benefit; loses a useful scripting mode. |

### 15.5 `-j` (JSON) With Positional

**Decided: emit a single JSON object equal to the per-view
element of list-mode's `views[]` array (§6.1).**

```json
{
  "name": "ready",
  "columns": "id,name,assignee,created:date",
  "filters": {"kind": "task", "status": "ready"},
  "sort": "created",
  "default_for": ["task"]
}
```

The five keys, types, and emptiness semantics are **identical to
§6.1** (verbatim `columns`; `filters: {}` when empty; `sort:
null` when absent; `default_for: []` when not bound, alphabetised
when populated). This ensures:

```bash
diff \
  <(art views ready -j) \
  <(art views -j | jq '.views[] | select(.name == "ready")')
# (modulo whitespace formatting)
```

#### 15.5.1 Decision — single object, not list-of-one

**Decided: a single JSON object.** Rejected: a single-element
JSON array `[{...}]` for symmetry with list-mode's `views[]`.

Rationale: a positional argument signals "I want this one thing";
a JSON object matches that intent. Consumers who genuinely need
array-shaped output can wrap with `jq -s` (slurp) or use list
mode + filter. The cost of array-of-one is more `jq` indirection
on every consumer for hypothetical symmetry.

#### 15.5.2 Decision — exclude `default_views` top-level object

The list-mode `-j` payload (§6) wraps results in
`{"views": [...], "default_views": {...}}`. **Detail-mode `-j`
emits only the per-view object.** It does *not* include a
`default_views` map.

Rationale: the kind→view direction is a vault-wide concern. A
detail query is per-view; including the full `default_views` map
would inflate the payload and tempt consumers to use detail mode
as a discovery surface (which is list mode's job). The
view-specific binding direction is preserved as `default_for`
on the per-view object, exactly as in §6.1.

### 15.6 Unknown View Name

When `<view_name>` resolves to no entry in `views_map` (whether
because `views:` is empty/missing, malformed-and-swallowed, or
the user typed a name that simply isn't defined):

| Mode    | Stdout | Stderr | Exit |
|---------|--------|--------|------|
| default | (none) | `error: unknown view '<name>'`<br>(plus optional close-match line — see §15.6.2) | `2` |
| `-q`    | (none) | same as default | `2` |
| `-j`    | (none) | same as default | `2` |

#### 15.6.1 Decision — exit code `2`

**Decided: exit `2`** (matches "argument or usage error" in this
CLI's convention).

Rationale: aligns with `artifacts list --view foo` when `foo` is
not defined (already exit 2 per
[[s0012-cli-list-named-views]]'s error table, which also returns
2 for "view not found"). Reusing 2 keeps the "view name not in
vault" semantics consistent across the CLI. Exit `1` was
considered (since `_run` maps `ValueError` to 1) but is reserved
for parser/validation errors, not lookup misses.

#### 15.6.2 Decision — close-match suggestions via `difflib`

**Decided: append a "Did you mean: …" line when at least one
candidate has a similarity ratio ≥ 0.6.**

Use `difflib.get_close_matches(name, list(views_map.keys()),
n=3, cutoff=0.6)`. When the result is non-empty, append a
second stderr line:

```text
error: unknown view 'redy'
Did you mean: ready, recent?
```

When the result is empty (or `views_map` is empty), emit only
the first line:

```text
error: unknown view 'redy'
```

Rationale: cheap (`difflib` is std-lib, no dependency), bounded
(top 3, ratio ≥ 0.6), high signal in practice (typos and
near-misses are the dominant unknown-name case). Symmetric with
`argparse`'s built-in close-match behaviour for unknown
subcommands.

#### 15.6.3 Decision — empty/missing `views:` + positional

**Decided: collapse the empty-vault state into the unknown-view
error path.** When the user supplies a positional and no views
are defined, emit `error: unknown view '<name>'` (exit 2). Do
**not** emit list-mode's "no views defined in artifacts.yaml"
hint when a positional is present.

Rationale: with a positional, the user has stated they expect a
specific view; the error they need is "that view doesn't exist
in this vault", not "this vault has no views". Suppressing the
list-mode hint avoids two stderr lines that say the same thing.
The `Did you mean` line is naturally also empty (no candidates
to match against).

The list-mode behaviour (§8: stderr hint, exit 0 when `views:`
is empty/missing **and** no positional) is unchanged.

### 15.7 Mutually Exclusive `-q` / `-j` (with positional)

**Decided: reuse the existing argparse mutually-exclusive group
unchanged.** The positional and the flag-group are independent in
argparse; passing both `-q` and `-j` (with or without a
positional) hits the existing argparse rejection (exit 2,
argparse-generated stderr). No custom validation required.

### 15.8 Malformed View Entry With Positional

When `_load_views_settings` re-raises `ValueError` (e.g. a view
entry is missing the required `columns` field), the existing
`_run` cascade in `cli/__init__.py:_run` maps it to exit 1 with
stderr `error: view entry missing required 'columns' field`.

This applies to detail mode the same as list mode (§10).

| Condition (detail mode) | Exit | Stderr |
|--------------------------|------|--------|
| Outside an `artifacts-os` project | `2` | `error: not in an artifacts-os project` |
| `artifacts.yaml` malformed YAML / load fails (`_load_views_settings` returns `None`) | `2` | `error: unknown view '<name>'` (no candidates → no "Did you mean") |
| `views:` entry missing required `columns` | `1` | `error: view entry missing required 'columns' field` |
| `<view_name>` resolves, command succeeds | `0` | (none) |
| `<view_name>` not in `views_map` | `2` | `error: unknown view '<name>'` (+ close-match line if any) |
| `-q` and `-j` both passed | `2` | argparse: `argument -j: not allowed with argument -q` |

### 15.9 List/Detail Dispatch — `views.py:run`

**Decided: simple `if args.name:` branch in `run`, with two
private helpers `_run_list(...)` and `_run_detail(...)` for
readability.** Keep both in the same `commands/views.py` file —
the module is small and the two paths share argument parsing,
the loader call, and the empty-vault detection.

Pseudocode (normative for the implementation sub-task):

```python
def register(subparsers) -> None:
    p = subparsers.add_parser("views", help="list defined views", ...)
    p.add_argument("name", nargs="?", default=None,
                   help="show details for this single view (detail mode)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-q", "--quiet",   action="store_true", ...)
    mode.add_argument("-j", "--json",    action="store_true",
                      dest="json_out", ...)
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    from artifacts_os.cli import _load_views_settings
    settings = _load_views_settings(registry.root)

    views_cfg = settings.views if settings is not None else None
    views_map = views_cfg.views if views_cfg is not None else {}
    defaults  = views_cfg.default_views if views_cfg is not None else {}

    # Reverse-index default_views once; both paths consume it.
    reverse: dict[str, list[str]] = {}
    for kind, view_name in defaults.items():
        reverse.setdefault(view_name, []).append(kind)
    for kinds_list in reverse.values():
        kinds_list.sort()

    if args.name is None:
        return _run_list(args, views_map, defaults, reverse)
    return _run_detail(args, views_map, reverse)
```

Decisions encoded above:

- **`name` is the positional kwarg name on `args`.** Not
  `view_name` — single-word `args.name` matches argparse
  convention and is shorter at call sites.
- **Reverse-indexing happens once**, before dispatch. Both
  paths need `default_for`; deduplication is cheap and avoids
  divergence.
- **Loader call happens once**, before dispatch. `ValueError`
  from `_load_views_settings` propagates to the `_run` cascade
  exactly as in list mode.

#### 15.9.1 Decision — single file, two helpers

Rejected: split detail mode into a sibling module
`commands/views_detail.py`. The two paths share:

- the loader call (`_load_views_settings`),
- argument parsing (one parser, one mutex group),
- the reverse-index of `default_views`,
- the empty-vault detection logic,
- the `default_for` rendering rule (list-of-kinds, sorted,
  `(none)` when empty).

Splitting would force shared helpers into a third module or
duplicate them. One file at ~150 lines is well within the project's
existing module-size norm (`commands/list.py` is larger).

### 15.10 Doc Touchpoints

#### `src/artifacts_os/cli/README.md`

Add a **`#### Detail mode`** subsection inside the existing
`### views — List defined views` section, after the existing
`Examples` block. Mirror the list-mode subsection's structure:
synopsis, behaviour summary, three examples (default, `-q`,
`-j`), and a one-line note on the unknown-name error path.

Concretely (illustrative copy):

```markdown
#### Detail mode

```
artifacts views <view_name> [-q | -j]
```

Pass a positional view name to inspect a single view's full
definition — including the **untruncated** `columns` string
and the **complete** `filters` dict (which the table form omits).

| Mode    | Output |
|---------|--------|
| default | Two-column rich table: `field` / `value` rows for `name`, `kind`, `columns`, `filters`, `sort`, `default-for`. |
| `-q`    | Just the `columns` field-spec string on one line — designed for shell substitution into `artifacts list --fields`. |
| `-j`    | A single JSON object equal to one element of the list-mode `views[]` array (§6.1 of `s0016`). |

**Examples:**

```bash
# Inspect a single view (full filters dict, untruncated columns)
artifacts views ready

# Reuse a view's columns directly in a list query
artifacts list --fields "$(artifacts views ready -q)"

# Single-view JSON for piping
artifacts views ready -j | jq '.filters'
```

If `<view_name>` is not defined, the command exits 2 with
`error: unknown view '<name>'` and offers close-match
suggestions when available.
```

Also add a one-line cross-link from the list-mode `Examples`
block: "Pass a view name as a positional argument to inspect a
single view in detail — see *Detail mode* below."

#### `s0003-artifacts-os-cli-module.md`

Append a one-line note in the Command Set row for `views`:

```diff
-| `views` | `views [-q\|-j]` | `_load_views_settings`; see [[s0016-cli-list-defined-views]] |
+| `views` | `views [<view_name>] [-q\|-j]` | `_load_views_settings`; see [[s0016-cli-list-defined-views]] (list mode + detail mode) |
```

#### `docs/settings.md`

No change required. The Views Section paragraph already
cross-links to `artifacts views`; the detail mode is a sub-mode
of the same command and does not introduce new settings keys.

#### `s0007-artifacts-os-views-module.md`, `s0012-cli-list-named-views.md`

No change. Data model and `--view` resolver contract are both
untouched.

### 15.11 Implementation Outline

The implementation sub-task is **out of scope for this spec
task** ([[t0069-spec-cli-views-detail-by]]). The umbrella feature
[[t0064-cli-list-defined-views-command]] will spawn a sibling
implementation task once this addendum is approved. That task
must:

1. Edit `src/artifacts_os/cli/commands/views.py` per §15.9.
2. Add the test cases enumerated in §15.12.
3. Update `src/artifacts_os/cli/README.md` per §15.10.
4. Update `s0003-artifacts-os-cli-module.md` Command Set row
   per §15.10.

No changes are required to:

- `src/artifacts_os/cli/__init__.py` (the loader
  `_load_views_settings` is already shipped and re-raises
  `ValueError` correctly per t0067).
- `src/artifacts_os/views/models.py` (data model unchanged).
- The argparse mutex group in `register(...)` (reused).

### 15.12 Test Cases — Implementation Sub-Task Must Cover

Add these to `tests/cli/test_views_cmd.py` in addition to the 13
list-mode cases already covered (§12.3). Use the existing
`vault` fixture and `_write_artifacts_yaml` helper.

| # | Case | Asserts |
|---|------|---------|
| 14 | **Detail default — fully populated view.** A view with `kind` filter, multi-key `filters`, `columns`, `sort`, and a `default_views` binding. | Output contains rows for `name`, `kind` (with the lifted kind value), `columns` (untruncated), `filters` (multi-line JSON with each filter key visible), `sort`, `default-for` (with the bound kind name). Exit `0`. |
| 15 | **Detail default — view with no kind filter.** | `kind` row renders `(any)`. |
| 16 | **Detail default — view with empty filters dict.** | `filters` row renders `(none)`. |
| 17 | **Detail default — view with no sort.** | `sort` row renders `(none)`. |
| 18 | **Detail default — view with no binding.** | `default-for` row renders `(none)`. |
| 19 | **Detail default — view bound to multiple kinds.** `default_views: {note: v, task: v}`. | `default-for` row renders `note, task` (alphabetised, comma-separated). |
| 20 | **Detail default — long `columns` is NOT truncated.** A `columns` string of >60 chars (which would truncate in list mode per §4.1). | Full string appears verbatim in the detail table. |
| 21 | **Detail default — nested `filters`.** Filters dict contains a nested object value. | `filters` cell renders multi-line indented JSON; nested keys remain visible (one per line). |
| 22 | **Detail `-q` quiet.** | Stdout is exactly `<columns>\n` (the `columns` field-spec string, single line). No view name, no other fields. Exit `0`. |
| 23 | **Detail `-j` JSON, populated view.** | Stdout parses to a single JSON object with keys `name, columns, filters, sort, default_for`. `default_for` is alphabetised. Object is **not** wrapped in `{"views": [...]}`. Exit `0`. |
| 24 | **Detail `-j` JSON, `filters` empty.** | Output JSON has `"filters": {}`. |
| 25 | **Detail `-j` JSON, `sort` absent.** | Output JSON has `"sort": null`. |
| 26 | **Detail `-j` JSON, view not bound.** | Output JSON has `"default_for": []`. |
| 27 | **Unknown view, no close matches.** Vault has `views: {alpha: ...}` and user runs `views zzzzzzz`. | Stderr is exactly `error: unknown view 'zzzzzzz'\n`. No `Did you mean`. Exit `2`. |
| 28 | **Unknown view, with close match.** Vault has `views: {ready: ..., recent: ...}` and user runs `views redy`. | Stderr first line is `error: unknown view 'redy'`. Stderr second line begins `Did you mean:` and contains `ready` (and possibly `recent`). Exit `2`. |
| 29 | **Unknown view in `-j` mode.** | No JSON on stdout (the parsed payload would not be a single view object). Stderr matches the unknown-view error. Exit `2`. |
| 30 | **Unknown view in `-q` mode.** | No stdout. Stderr matches. Exit `2`. |
| 31 | **Empty `views:` + positional.** Vault YAML has no `views:` section; user runs `views ready`. | Stderr `error: unknown view 'ready'`, no "no views defined" hint, no "Did you mean" line (no candidates). Exit `2`. |
| 32 | **Empty `views:` map + positional.** Vault YAML has `views: {}`. | Same as case 31. |
| 33 | **`-q` + `-j` + positional.** Three flags together. | Argparse rejects with exit `2` and its standard "not allowed with argument" stderr. (Already covered for list mode in case 10; case 33 confirms the rejection still fires when a positional is present.) |
| 34 | **Malformed entry + positional.** A view in `views:` is missing required `columns` field; user runs `views <any-name>`. | Stderr `error: view entry missing required 'columns' field`. Exit `1`. (The `ValueError` re-raise propagates before dispatch, so the unknown-view path is not reached.) |
| 35 | **Detail mode does not affect list mode.** Sanity check: `views` (no positional) in the same vault still produces the list-mode table per §4. | At least one expected list-mode row appears; argparse does not require a positional. |

Ordering rationale: cases 14–21 cover default rendering (one
row, one decision per case); 22–26 cover machine-readable
modes; 27–32 cover the unknown-view error matrix; 33–35 cover
flag interactions and a backwards-compatibility sanity check.

### 15.13 Verification (Spec-Level)

This addendum is verified when the architect's
[[t0069-spec-cli-views-detail-by]] task passes its checklist.
The downstream implementation sub-task inherits the test-case
list from §15.12 directly.
