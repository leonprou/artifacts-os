---
kind: spec
id: s0027
name: align-events-cli-with-list
status: draft
task: "[[t0139-align-events-cli-with-list]]"
created: 2026-05-10
---

# Align `artifacts events` With `artifacts list`

Replace the nested `artifacts events tail` subcommand with a flat
`artifacts events` verb that mirrors `artifacts list` in shape,
output, and flag conventions. Add a shared `--tail [N]` flag to both
commands so "show me the last N rows" is the same primitive across
the CLI.

Producing task: [[t0139-align-events-cli-with-list]].
Sibling spec touched: [[s0025-artifact-events]] § C8 — its CLI
contract is restated here and the older form documented as a
deprecated alias.

## Problem

`artifacts events` was implemented as a nested subcommand
(`artifacts events tail`) that took a `git log`-style shape:
implicit `--limit 50`, plain-text output, optional `--follow`. Every
other command in the CLI is a flat verb (`list`, `show`, `create`,
`status`, `verify`, `validate`, `kinds`, `views`), so `events tail`
is the only command in the surface that requires a subcommand.

Two concrete consequences:

1. **Inconsistent mental model.** `artifacts list --kind task` and
   `artifacts events tail --event artifact.created` look like they
   come from two different tools. Users have to remember which verbs
   take a subcommand and which don't. The streaming/paging behaviour
   belongs as flags on a flat verb, not as a separate noun.
2. **Inconsistent default behaviour.** `artifacts list` shows
   everything by default and lets the user narrow with filters.
   `artifacts events tail` silently caps at 50 lines via `--limit`,
   which leaks an arbitrary policy into the default and contradicts
   the rest of the CLI. Showing the "last N" is a Unix `--tail`
   primitive — opt-in, not opt-out.

`--limit` was added in commit `1eda407` (same session as t0139); no
external users depend on it yet. The cost of removing it is zero.

## Architecture

Flat verb with all flags top-level; render through the same Rich
table layer `artifacts list` already uses. `events tail` survives
as a hidden alias that maps to the same handler so existing
muscle memory and documentation links keep working.

### CLI Surface (after)

```
artifacts events                              # all events, old→new, Rich table
artifacts events --tail                       # last 50, Rich table
artifacts events --tail 20                    # last 20
artifacts events --follow                     # all + live stream
artifacts events --tail --follow              # last 50 snapshot, then stream
artifacts events --tail 20 --follow           # last 20 snapshot, then stream
artifacts events --since 2026-05-01           # filter by date
artifacts events --event artifact.status_changed  # filter by event type
artifacts events --json                       # raw JSONL
artifacts events tail [...]                   # hidden alias — same flags, same handler

artifacts list --tail 10                      # last 10 results (post-filter, post-sort)
```

### Flow

```
argv ─ ["events", ...]
  └─ events parser (top-level flags) ─┐
                                       │
argv ─ ["events", "tail", ...]         │
  └─ hidden tail subparser ───────────┤   (same handler)
                                       ▼
                          _run_events(args, registry)
                              │
              ┌───────────────┼─────────────────┐
              ▼               ▼                 ▼
          _events_dir    collect snapshot   --json? raw JSONL
                              │                 │
                              ▼                 ▼
                     apply --tail [N] slice    print
                              │
                              ▼
                  --json? print JSONL : render Rich table
                              │
                              ▼
                  --follow? stream new lines (no cap)
```

### Invariants

| # | Invariant |
|---|-----------|
| I1 | The flat verb and the `tail` alias dispatch to the same handler with the same flag set — they are interchangeable. |
| I2 | Without `--tail`, no implicit truncation. All matching events are shown. |
| I3 | Default order is chronological (old → new), matching daily-file order and `artifacts list`'s `id`-ascending default. |
| I4 | `--tail [N]` slices **after** all filters are applied (`--since`, `--event`); `--tail` without a value defaults to 50. |
| I5 | `--follow` after a `--tail` snapshot streams without a cap — `--tail` controls the snapshot only. |
| I6 | `--limit` / `-n` is **removed**, not aliased. The flag never appears in argparse and is not silently mapped to `--tail`. |
| I7 | The Rich table for `events` uses the same column-construction pattern as `list` (`views.render_table`-shaped) so styling stays uniform. |

### Module Layout

No new modules. Two files change:

- `src/artifacts_os/cli/commands/events.py` — registration and runner
  rewritten; rendering helper added in-file.
- `src/artifacts_os/cli/commands/list.py` — `--tail [N]` flag added to
  the `list` parser; tail slice applied after sort, before render.

Tests are split: `tests/cli/test_events_tail.py` is renamed to
`tests/cli/test_events.py` (new layout) and a small
`tests/cli/test_list_tail.py` is added.

## Components

| # | Component | Location | Purpose |
|---|-----------|----------|---------|
| C1 | Flat `events` parser | `src/artifacts_os/cli/commands/events.py` | Register `events` with all flags top-level + hidden `tail` alias |
| C2 | Events runner | `src/artifacts_os/cli/commands/events.py` | Collect → filter → tail-slice → render; follow loop |
| C3 | Events Rich renderer | `src/artifacts_os/cli/commands/events.py` | Build a `rich.Table` with `ts`, `event`, `kind`, `artifact` columns |
| C4 | `list --tail [N]` | `src/artifacts_os/cli/commands/list.py` | Same flag shape; slice applied after sort |
| C5 | Tests | `tests/cli/test_events.py`, `tests/cli/test_list_tail.py` | Cover all verification items below |

### C1 — Flat `events` parser + hidden `tail` alias

Replace the current nested `add_subparsers` block with a flat
`events` parser that owns every flag. Then register a `tail`
subparser whose flag set is identical and whose handler is the same
function — the alias is invisible to `--help` (`add_help=False` plus
omission from the help text).

```python
def register(subparsers) -> None:
    p = subparsers.add_parser(
        "events",
        help="inspect the artifact event stream",
    )
    _add_event_flags(p)
    p.set_defaults(func=_run_events)

    # Hidden backward-compat alias: `artifacts events tail [...]`.
    # Same flags, same handler. Not advertised in --help.
    sub = p.add_subparsers(dest="events_command", metavar="")
    tail_alias = sub.add_parser("tail", help=argparse.SUPPRESS)
    _add_event_flags(tail_alias)
    tail_alias.set_defaults(func=_run_events)
```

`_add_event_flags(parser)` is the single source of truth for the
flag set. It registers (in order):

| Flag | Type | Default | Purpose |
|------|------|---------|---------|
| `--since DATE` | `str` (parsed via `_parse_since`) | `None` | filter from this date forward |
| `--event TYPE` (`-e`, repeatable) | append-list | `None` | filter by event type |
| `--follow` (`-f`) | `store_true` | `False` | live-tail new entries |
| `--json` (`-j`) | `store_true` (`dest="json_out"`) | `False` | raw JSONL output |
| `--tail [N]` | `int`, `nargs="?"` | `_TAIL_UNSET` (sentinel) | last-N slice; bare `--tail` ⇒ 50 |

Implementation note for `--tail`:

```python
_TAIL_UNSET = object()  # module-level sentinel
_TAIL_DEFAULT_WHEN_BARE = 50

parser.add_argument(
    "--tail",
    nargs="?",
    type=int,
    const=_TAIL_DEFAULT_WHEN_BARE,  # bare `--tail` → 50
    default=_TAIL_UNSET,             # absent → no slicing
    metavar="N",
    help="show the last N events (default 50 when N is omitted)",
)
```

The sentinel pattern is required because argparse cannot
distinguish "flag absent" from "flag present with default value"
when `nargs="?"` and `default` is anything other than the same
object as `const`. Using a unique sentinel keeps the runner's
branching unambiguous.

### C2 — Events runner

```python
def _run_events(args, registry) -> int:
    # 1. Resolve events_dir (existing helper, unchanged)
    # 2. Parse --since (existing helper, unchanged)
    # 3. Build snapshot: collect all matching records old→new
    # 4. If args.tail is not _TAIL_UNSET: snapshot = snapshot[-args.tail:]
    # 5. Render snapshot (json or Rich table)
    # 6. If --follow: stream new lines without a cap
```

Snapshot collection reuses the existing `_collect_file` and
`_daily_files` helpers. The chronological order is already
guaranteed by `sorted(events_dir.glob("*.jsonl"))` plus per-file
linear read.

The follow loop is unchanged from the current implementation
(existing `time.sleep(0.25)` + per-file `tell()` tracking). Cap
removal is implicit because `--tail` only controls the snapshot.

When the resolved tail value is `0`, the snapshot is truncated to
zero entries (consistent with the slice `lst[-0:]` being all
elements is a Python gotcha — handle explicitly: `if n == 0:
snapshot = []`). This preserves the behaviour of `--limit 0` no
longer being a "show everything" escape hatch — that role is
served by simply omitting `--tail`.

### C3 — Events Rich renderer

A small helper builds a `rich.Table` directly from the JSONL records
without going through `views.render_table` (which is keyed off
`ArtifactMeta` + `FieldSpec`). Events are not artifacts; reusing
`render_table` would require a synthetic `ArtifactMeta`, which
muddies the abstraction. A purpose-built table that follows the
same visual style is simpler and lower-risk.

```python
from rich.console import Console
from rich.table import Table

_EVENT_COLUMNS: tuple[str, ...] = ("ts", "event", "kind", "artifact")

def _render_table(records: list[dict]) -> None:
    table = Table()
    for col in _EVENT_COLUMNS:
        table.add_column(col)
    for rec in records:
        ts = rec.get("ts", "")
        event = rec.get("event", "")
        kind = rec.get("kind", "")
        artifact = rec.get("stem") or rec.get("id") or rec.get("hook") or ""
        table.add_row(ts, event, kind, artifact)
    Console().print(table)
```

The `artifact` column resolves in this order: `stem`, then `id`
(for events that lack `stem` such as some validate outcomes), then
`hook` (for `hook.fired` / `hook.failed` records), then empty. This
mirrors the order already used by `_format_record` in plain-text
output today, so the column has a meaningful value for every event
type in the C1 catalog of [[s0025-artifact-events]].

### C4 — `list --tail [N]`

Add the same flag to the `list` parser, with the same sentinel
semantics as C1:

```python
p.add_argument(
    "--tail",
    nargs="?",
    type=int,
    const=50,
    default=_TAIL_UNSET,
    metavar="N",
    help="show the last N results after filters and sort",
)
```

Application point: in `cli/commands/list.py::run`, after sorting
and after any tree/table layout has computed its row order, slice
the items list `items = items[-n:]` if `args.tail is not
_TAIL_UNSET`. For `quiet` and `json` modes the slice is applied to
the sorted flat list before output. For `tree` layout, slicing the
input set before tree composition is the correct semantic — the
tree is a presentation of the (possibly tail-sliced) result set,
not a separate data axis.

When `n == 0`: empty result set (consistent with C2). When `n >=
len(items)`: returns the full list (Python slice semantics handle
this naturally). No interaction with `--children`, `--parent`, or
`--prune` beyond ordering — the slice happens last.

### C5 — Tests

Two test files cover the new surface end to end. The existing
`tests/cli/test_events_tail.py` is renamed to
`tests/cli/test_events.py` and its assertions updated. New
test names:

| Test | Asserts |
|------|---------|
| `test_events_flat_no_subcommand` | `_run(["events"])` returns 0 with all events shown |
| `test_events_tail_alias_works` | `_run(["events", "tail"])` returns 0 and produces same output as `["events"]` (V: backward compat) |
| `test_events_default_is_rich_table` | Output contains the Rich table border characters or column headers (`ts`, `event`, `kind`, `artifact`) |
| `test_events_chronological_order` | When events span two daily files, output rows appear earliest-first |
| `test_events_tail_default_50` | With 80 records, `["events", "--tail"]` shows 50 |
| `test_events_tail_explicit` | `["events", "--tail", "20"]` shows 20 |
| `test_events_tail_zero` | `["events", "--tail", "0"]` shows 0 rows |
| `test_events_no_tail_shows_all` | With 80 records, `["events"]` shows 80 (no implicit cap) |
| `test_events_json_passthrough` | `["events", "--json"]` produces valid JSONL, one record per line |
| `test_events_since_filter` | `--since` filters by date as before |
| `test_events_event_type_filter` | `--event` (repeatable) filters as before |
| `test_events_no_limit_flag` | argparse rejects `--limit` / `-n` (`SystemExit`, exit 2) |
| `test_list_tail_default_50` | `artifacts list` with 80+ tasks: `["list", "--tail"]` returns 50 |
| `test_list_tail_explicit` | `["list", "--tail", "10"]` returns 10 |
| `test_list_tail_after_filter` | `["list", "--kind", "task", "--tail", "5"]` slices the filtered set |
| `test_list_no_tail_unchanged` | Existing list tests still pass (no behaviour change when flag absent) |

Each test reuses the existing `vault` fixture from
`tests/cli/conftest.py` and the in-file `vault_with_events`
pattern from `test_events_tail.py`.

## Verification

| # | Component | Criterion |
|---|-----------|-----------|
| V1 | C1 | `artifacts events` parses without a subcommand; all flags work top-level |
| V2 | C1 | `artifacts events tail [...]` parses with the same flag set and dispatches to the same handler |
| V3 | C1 | `--limit` / `-n` are not registered; passing them errors with argparse exit 2 |
| V4 | C2 | Without `--tail`, output contains every matching event (no cap) |
| V5 | C2 | Output is chronologically ordered earliest-first across multiple daily files |
| V6 | C2 | `--tail` (bare) shows the last 50 of a larger set; `--tail 20` shows the last 20; `--tail 0` shows zero rows |
| V7 | C2 | `--follow` after `--tail` snapshot streams new lines without re-applying the cap |
| V8 | C3 | Default (non-`--json`) output is a Rich table with columns `ts`, `event`, `kind`, `artifact` |
| V9 | C3 | The `artifact` column shows `stem` ‖ `id` ‖ `hook` (first non-empty) for every catalog event |
| V10 | C4 | `artifacts list --tail [N]` slices the post-filter, post-sort result set; bare `--tail` defaults to 50 |
| V11 | C4 | `--tail` interacts cleanly with `-q` / `-j` / tree layout (slice applied in all modes) |
| V12 | C5 | All new tests pass; renamed `test_events.py` covers backward-compat for `events tail` |
| V13 | Docs | `s0025-artifact-events` § C8 is updated to reflect the new flat surface (alias mentioned, `--limit` removed) |

## Build Sequence

Each step compiles and is independently testable.

1. **C1 + C2 (renderer-less)** — flat `events` parser + handler that
   prints plain text. Hidden `tail` alias wired. `--limit` removed.
   Existing tests in `test_events_tail.py` updated to call `events`
   directly; the alias has its own test.
2. **C3** — Rich table renderer added; default output switches from
   plain text to Rich table. `--json` path unchanged.
3. **C4** — `--tail [N]` added to `list` parser; slice applied in
   `run()` after sort, before render. New `test_list_tail.py`.
4. **C5** — rename `test_events_tail.py` to `test_events.py`;
   add the new test cases above. Confirm the full test suite is
   green (`pytest`).
5. **Docs** — update `s0025-artifact-events` § C8 to point at
   the flat surface; mention the hidden alias and the removal of
   `--limit`. Update any `CHANGELOG` entry that references the old
   shape.

## Design Decisions

### DD-1: Flat verb with hidden `tail` alias (vs deprecation warning)

**Choice:** Keep `artifacts events tail` as a hidden alias that
shares the handler — silent, no deprecation warning, no advertised
removal date.

**Alternatives considered:**

| Option | Pros | Cons |
|--------|------|------|
| **A. Hidden alias, no warning (chosen)** | Existing scripts and muscle memory keep working with zero noise. Single handler, single source of truth. | A user typing `events tail --help` sees the same help twice (alias and parent). |
| B. Hard cutover (remove `tail`) | Smallest surface; matches the rest of the CLI exactly. | Breaks any agent or doc that already wired `events tail`; the cost of t0139's "no external users yet" claim is repaid only if the change happens before any docs land — it has not. |
| C. Deprecation warning on `tail` | Signals the migration path. | Adds a stderr noise channel for a transitional period nobody asked for. Pre-1.0 we are free to break, but only when the break has a reason; here the reason is symmetry, which is preserved cheaply by the alias. |

**Trade-off:** The hidden alias trades an extra five lines of code
for full backward compatibility. Pre-1.0 we're allowed to break;
we just don't gain anything by breaking here.

### DD-2: `--tail [N]` with `nargs="?"` + sentinel default

**Choice:** Use `argparse.nargs="?"` with `const=50`, `default=<unique sentinel>`.

**Alternatives considered:**

| Option | Pros | Cons |
|--------|------|------|
| **A. `nargs="?"` + sentinel (chosen)** | One flag covers `--tail` (bare) and `--tail N`; runner can distinguish "flag absent" from "flag present" without ambiguity. | Sentinel pattern is non-obvious to readers; needs a short comment. |
| B. Two flags (`--tail` boolean + `--tail-n N`) | Each flag is unambiguous on its own. | API doubles for no reason; users would still type `--tail 20` and be confused. |
| C. `default=0`, treat 0 as "absent" | No sentinel needed. | Clashes with the legitimate "show 0 rows" semantic of `--tail 0`; we want both reachable. |
| D. Custom action class | Most explicit. | Overkill for a one-flag concern. |

**Trade-off:** A is a five-line trick (sentinel object, `const`,
`default`, comment, runner branch) that buys exactly the surface
the task spec asks for. The alternatives all sacrifice either
clarity at the call site or a bit of behaviour we want to keep.

### DD-3: Purpose-built renderer (vs `views.render_table`)

**Choice:** Build the events Rich table inline in `events.py`
rather than going through `views.render_table`.

**Alternatives considered:**

| Option | Pros | Cons |
|--------|------|------|
| **A. Inline renderer (chosen)** | Events are not `ArtifactMeta`; no synthetic adaptation needed. ~15 lines. The CLI already imports `rich.Console` and `rich.Table`. | Two table-building code paths in CLI (one in `views`, one here). |
| B. Use `views.render_table` with a synthetic `ArtifactMeta` | Single rendering path. | Forces every event JSONL record to be wrapped in an `ArtifactMeta` shaped fake; couples the events command to internal `views` types it has no semantic relationship to. |
| C. Add an "events table" layout to `views.layouts` | Real architectural fit. | Out of scope for t0139; would need its own spec and larger surface. |

**Trade-off:** Two table builders is mild duplication. The
alternative (synthetic `ArtifactMeta` for every event) is a worse
abstraction violation than the duplication. If a future task
generalizes `views` to render arbitrary records, both call sites
collapse to one — until then, inline is the right size.

### DD-4: `--tail` slice applied last (vs early)

**Choice:** Apply the `--tail [N]` slice **after** all filters and
sorts, immediately before render.

**Alternatives considered:**

| Option | Pros | Cons |
|--------|------|------|
| **A. Slice last (chosen)** | The user's mental model is "filter, sort, then take the last N" — same as `tail` after a pipeline. | Loads more records into memory than strictly necessary. |
| B. Slice while reading (events) | Reads only the last N from disk. | Breaks composition with `--since` and `--event` filters; "last 20 of kind=task" requires reading more than 20. |

**Trade-off:** A keeps the filter/sort/slice mental model
consistent with `artifacts list`. Memory cost is bounded by the
event-stream size, which is already small (one JSON object per CRUD
call). If volume ever forces optimisation, a streaming variant can
replace the in-memory list without changing the user-facing
contract.

## Migration

Pre-1.0 hard cutover for `--limit` / `-n`. The flag was added in
commit `1eda407` and is not referenced by any agent spec, doc, or
script in the tree (verified via `grep -r 'events.*--limit'`,
`grep -r 'events.*\-n '`). Removing it is a no-op in practice;
this section exists only to make the choice explicit.

`events tail` is preserved as a hidden alias indefinitely. If a
future task removes it, that task should add a one-cycle
deprecation warning first — but the cost of the alias today is
five lines and zero runtime overhead.

## Cross-References

- [[t0139-align-events-cli-with-list]] — producing task
- [[s0025-artifact-events]] § C8 — the original CLI contract; this
  spec supersedes the surface but not the catalog or stream design
- [[s0003-artifacts-os-cli-module]] — CLI module conventions
- [[s0023-multi-value-filters]] — `--event` repeatable / multi-value
  precedent
- `src/artifacts_os/cli/commands/events.py` — primary edit target
- `src/artifacts_os/cli/commands/list.py` — secondary edit target
- `tests/cli/test_events_tail.py` → `tests/cli/test_events.py` —
  rename and expand
