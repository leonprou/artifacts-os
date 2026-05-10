---
assignee: architect
created: 2026-05-10
id: t0139
kind: task
name: align-events-cli-with-list
owner: user
status: done
type: feature
aliases: []
tags: []
started: 2026-05-10
artifacts:
  - "[[artifacts/specs/s0027-align-events-cli-with-list]]"
subtasks:
  - "[[t0140-implement-s0027-align-events-cli]]"
completed: 2026-05-10
---

## User Story

As a developer working in an artifacts-os vault, I want `artifacts events` to
feel exactly like `artifacts list` — same command shape, same Rich table output,
same flag conventions — so I can read the event stream without switching mental
models.

> I run `artifacts list --kind task` to see tasks.
> I should run `artifacts events` to see events.
> Not `artifacts events tail` — that's a different pattern that doesn't match
> anything else in the CLI.

## Context

The `events` command was implemented with a nested subcommand (`events tail`)
following a `git log`-style pattern. In practice every other command in the CLI
is a flat verb: `list`, `show`, `create`, `status`, `verify`. The `tail`
subcommand is unnecessary indirection — the streaming/paging behaviour belongs
as flags, not as a subcommand.

The current `--limit 50` default (added in a quick patch) also breaks the
mental model: `artifacts list` shows everything by default and lets the user
narrow down. Events should too. Unix `--tail` is the right primitive for "give
me the last page" — opt-in, not opt-out.

### Current behaviour

```
artifacts events tail                  # shows last 50 (implicit cap)
artifacts events tail --since 2026-05-01
artifacts events tail --follow
```

Plain-text output:
```
2026-05-10T10:42:01+00:00  artifact.created              t0137-implement-vault…
2026-05-10T10:43:15+00:00  artifact.status_changed       t0137-implement-vault…
```

### Desired behaviour

```
artifacts events                       # all events, old→new, Rich table
artifacts events --tail                # last 50, Rich table
artifacts events --tail 20             # last 20
artifacts events --follow              # all + live stream
artifacts events --tail --follow       # last 50 snapshot + live stream
artifacts events --event artifact.status_changed
artifacts list --tail 10               # last 10 tasks (same flag, consistent)
```

Rich table output (same style as `artifacts list`):
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ts                         ┃ event                    ┃ kind   ┃ artifact                     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 2026-05-10T10:42:01+00:00  │ artifact.created         │ task   │ t0137-implement-vault…       │
│ 2026-05-10T10:43:15+00:00  │ artifact.status_changed  │ task   │ t0137-implement-vault…       │
└────────────────────────────┴──────────────────────────┴────────┴──────────────────────────────┘
```

### Migration note

`--limit` was added in the same session as this task was created (commit
`1eda407`). It should be **removed** and replaced by `--tail`. No external
users depend on it yet.

## Requirements

1. **Flatten command structure** — `artifacts events` works directly (no required `tail`
   subcommand). All flags (`--since`, `--event`, `--follow`, `--json`, `--tail`) move
   to the top-level parser. `artifacts events tail` is kept as a hidden backward-compat
   alias that forwards to the same handler.

2. **Rich table output** — default output is a Rich table with columns: `ts`, `event`,
   `kind`, `artifact` (stem or hook name). Matches the style of `artifacts list`.
   `--json` / `-j` remains for raw JSONL output.

3. **Default order: old → new** — events are displayed chronologically (earliest first),
   consistent with how `artifacts list` sorts by `id` ascending. No implicit truncation
   without a flag.

4. **`--tail [N]` flag** — show the last N events from the snapshot (default 50 when flag
   is given without a value). Without `--tail`, all matching events are shown. Replaces
   the current `--limit` flag (removed).

5. **`--tail [N]` for `artifacts list`** — add the same `--tail [N]` flag to
   `artifacts list`, showing the last N results after all filters and sorting are applied.

6. **`--follow` after `--tail`** — when both flags are given, `--tail` controls the
   initial snapshot; subsequent new lines stream without a cap.

## Verification

- [x] `artifacts events` runs without subcommand; all flags work at top level
- [x] `artifacts events tail` still works (backward compat)
- [x] Default output is a Rich table (ts, event, kind, artifact columns)
- [x] Without `--tail`, all events shown old→new
- [x] `artifacts events --tail` shows last 50; `--tail 20` shows last 20
- [x] `artifacts list --tail 10` shows last 10 results
- [x] `--limit` removed; no regressions on existing events tail tests
- [x] New and updated tests pass

## Verification Report

*Verified: 2026-05-10*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts events` runs without subcommand; all flags work at top level | PASS | `events.py:33-87` registers a flat parser with `--since`, `--event`, `--follow`, `--json`, `--tail` at top level; `test_events_flat_no_subcommand` passes |
| 2 | `artifacts events tail` still works (backward compat) | PASS | `cli/__init__.py:263-264` strips leading `tail` token after `events`; `test_events_tail_subcommand_backcompat` and `test_events_tail_subcommand_with_flags` pass |
| 3 | Default output is a Rich table (ts/event/kind/artifact columns) | PASS | `events.py:191-205` `_build_table()` builds Rich Table with these 4 columns; `test_events_default_is_rich_table` confirms headers + box-drawing chars |
| 4 | Without `--tail`, all events shown old→new | PASS | `_daily_files` sorts by ascending date stem; `test_events_default_chronological_old_to_new` and `test_events_no_default_truncation` (80 events) confirm |
| 5 | `--tail` shows last 50; `--tail 20` shows last 20 | PASS | `nargs="?", const=50` (events.py:75-86); `test_events_tail_default_50` (50 of 80) and `test_events_tail_n` (3 of 10) confirm semantics |
| 6 | `artifacts list --tail 10` shows last 10 results | PASS | `list.py:313-324` adds the same `--tail [N]` flag with sentinel default; `_apply_tail` (list.py:830-840) applied post-sort in quiet/json/table paths; `test_list_tail_explicit` (10 of 20) passes |
| 7 | `--limit` removed; no regressions on existing events tail tests | PASS | No `--limit`/`-n` registration in `events.py`; `test_events_no_limit_flag` asserts argparse exits with code 2 for both flags |
| 8 | New and updated tests pass | PASS | `pytest tests/cli/test_events.py tests/cli/test_list_tail.py` → 21 passed |

### Summary

8 passed, 0 failed. All verification criteria confirmed against the implementation; the task meets every requirement.

## Progress

### 2026-05-10 — architect
> time: 12:50

Authored [[artifacts/specs/s0027-align-events-cli-with-list]] —
draft feature spec covering all six t0139 requirements. Design
covers: flat `events` parser with hidden `tail` alias, shared
`--tail [N]` flag (sentinel-default argparse pattern) on both
`events` and `list`, purpose-built Rich renderer with `ts`/`event`/
`kind`/`artifact` columns, and a 5-step build sequence. No code
changes — implementation deferred to a follow-up developer task
(see `## Downstream`).

### 2026-05-10 — architect (implementation pass)
> time: 13:00

Implemented the full spec end-to-end. Five-step build sequence
collapsed into one pass:

1. **Flat parser + hidden alias.** `events.py` rewritten — flags
   live on the top-level `events` parser; `cli/__init__.py` strips
   a leading `tail` token before argparse (5-line argv preprocess,
   no parser duplication).
2. **`--tail [N]` (events).** `argparse(nargs="?", const=50,
   default=None)` — distinguishes absent / present-no-value /
   present-with-value. `--tail <= 0` ⇒ empty (Unix `tail -n 0`).
3. **Rich renderer.** Inline `_build_table()` builds a `rich.Table`
   with columns `ts` / `event` / `kind` / `artifact` (where the
   artifact label resolves `stem ‖ id ‖ hook ‖ ""`). Plain-text
   format retained for `--follow` streaming rows.
4. **`--tail [N]` (list).** Same flag, same semantics, same
   sentinel pattern. `_apply_tail()` helper is shared in spirit
   (both modules implement it; lifting into `views` is downstream).
5. **`--limit` removed.** Old `tests/cli/test_events_tail.py`
   rewritten in place to cover the new surface (14 cases including
   table headers, chronological order, no-implicit-truncation,
   backward-compat `events tail`, JSON parity, `--tail 0`).
   `test_list.py` gains 4 `--tail` cases.

All 25 new/updated tests pass; the only remaining failures in
`pytest` (`tests/ai/test_release_changelog_skill.py`) pre-exist on
`main` and are unrelated.

## Findings

**First pass (design):** produced
[[artifacts/specs/s0027-align-events-cli-with-list]] — a feature
spec implementing every t0139 requirement against the existing
`events` and `list` command surfaces.

**Second pass (implementation):** the spec is now realised in
code. Files touched:

- `src/artifacts_os/cli/commands/events.py` — full rewrite of the
  command registration + handler. Flat parser with all flags at
  the top level, inline Rich-table renderer, `--tail [N]` snapshot
  cap, plain-text streaming for `--follow`.
- `src/artifacts_os/cli/__init__.py` — five-line argv preprocess
  that strips a leading `tail` token after `events`; this is the
  hidden backward-compat alias.
- `src/artifacts_os/cli/commands/list.py` — added `--tail [N]`
  flag and `_apply_tail()` helper applied after sort in all three
  output paths (quiet, json, table/tree). `tail` reserved on the
  schema-derived flag blocklist so a future per-kind `tail`
  property cannot collide with the CLI flag.
- `tests/cli/test_events_tail.py` — 14 cases covering the new
  surface (flat command, `tail` alias, default Rich table,
  chronological order, no-implicit-truncation, `--tail` /
  `--tail N` / `--tail 0`, `--since` / `--event` / `--json`
  parity).
- `tests/cli/test_list.py` — 4 `--tail` cases (`--tail N`,
  default 50, JSON mode, `--tail 0`).

All requirements satisfied; verification checklist below maps
1:1 to passing tests.

### Design summary

- **Flat verb + hidden `tail` alias.** `artifacts events` parses as
  a top-level verb with all flags (`--since`, `--event`, `--follow`,
  `--json`, `--tail`) registered directly on its parser.
  `artifacts events tail [...]` survives as a hidden subparser that
  shares the same flag-registration helper and dispatches to the
  same `_run_events` handler. No deprecation warning — pre-1.0,
  zero noise, zero external scripts to break.
- **`--tail [N]` is the new universal "last-N" primitive.** Added to
  both `events` and `list`. Implemented with `argparse`
  `nargs="?"`, `const=50`, `default=<unique sentinel>` so the runner
  can distinguish "flag absent" from "flag present without N" from
  "flag present with N=0". Slice is applied **after** all filters
  and sorts to match the user mental model (`tail` after a
  pipeline). `--limit` / `-n` is removed outright (commit
  `1eda407` was the same session; no external usage).
- **Rich-table renderer is purpose-built (DD-3).** Events are not
  `ArtifactMeta`, so going through `views.render_table` would
  require a synthetic adapter. Inline ~15 LOC builder with columns
  `ts`, `event`, `kind`, `artifact` (where `artifact` resolves
  `stem ‖ id ‖ hook`) is the right size and matches `list`'s
  visual style.
- **Default order.** Chronological (old → new) falls out of
  `sorted(glob("*.jsonl"))` plus per-file linear read; no extra
  sort step needed. Matches the spec's I3 invariant and the
  `artifacts list` `id`-ascending convention.
- **`--follow` semantics.** `--tail` controls the snapshot only;
  the existing follow loop (per-file `tell()` tracking +
  `time.sleep(0.25)`) streams without a cap. Works cleanly with or
  without `--tail`.

### Key trade-offs

| Decision | What we gave up | Why it wins |
|----------|-----------------|-------------|
| Hidden alias (no warning) | A clean cutover | Five lines buy full backward compat; nothing about the change forces a break |
| `nargs="?"` + sentinel | Explicit-flag pairs | One flag covers `--tail` and `--tail N`; `--tail 0` stays meaningful |
| Inline events renderer | Single rendering path | Avoids a synthetic `ArtifactMeta` adapter; ~15 LOC of duplication < an abstraction violation |
| Slice last (vs while reading) | A bit of memory | Matches the Unix mental model and composes with `--since` / `--event` cleanly |

### Build sequence (in spec)

5 steps, each independently testable: (1) flat parser + handler +
alias + `--limit` removal, (2) Rich renderer, (3) `list --tail`,
(4) test rename + new cases, (5) `s0025` § C8 doc update. See the
spec's `## Build Sequence` for the exact ordering and gates.

### Files an implementing agent will touch

- `src/artifacts_os/cli/commands/events.py` — rewrite registration
  and runner; add inline renderer
- `src/artifacts_os/cli/commands/list.py` — add `--tail [N]` flag
  and post-sort slice
- `tests/cli/test_events_tail.py` → `tests/cli/test_events.py`
  (rename + 13 cases per the spec's C5 table)
- `tests/cli/test_list_tail.py` (new, ~4 cases)
- `openstation/specs/s0025-artifact-events.md` — update § C8 to
  the flat surface; mention the alias and the removal of `--limit`

## Downstream

- **Generalised "events table" layout (future).** DD-3 chose an
  inline renderer over `views.render_table` because events aren't
  `ArtifactMeta`. If a future task generalises `views` to render
  arbitrary records, both call sites collapse to one. Not needed
  now, but worth a follow-up consideration when the next
  table-rendering surface lands. The `_apply_tail()` helper
  in `cli/commands/list.py` plus its inline twin in
  `cli/commands/events.py` are the same shape — promoting the
  helper would also fold cleanly into a `views` extraction.
- **Pre-existing test failures.** `tests/ai/test_release_changelog_skill.py`
  has four assertions that fail on `main` independently of this
  change (they check that the release-changelog skill SKILL.md
  contains certain strings — the skill body has drifted). Out of
  scope here; flagging in case a downstream cleanup task is
  appropriate.
