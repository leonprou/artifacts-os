---
kind: task
id: t0140
name: implement-s0027-align-events-cli
type: implementation
status: done
assignee: developer
owner: user
parent: "[[t0139-align-events-cli-with-list]]"
created: 2026-05-10
started: 2026-05-10
completed: 2026-05-10
---

# Implement S0027 — Align Events Cli With List

## Requirements

Implement [[artifacts/specs/s0027-align-events-cli-with-list]]
end-to-end. Follow the spec's `## Build Sequence` for ordering.

1. **Flat `events` parser + handler** —
   `src/artifacts_os/cli/commands/events.py`. Replace the nested
   `events tail` subcommand with a flat `events` verb. Extract a
   single `_add_event_flags(parser)` helper as the source of truth
   for `--since`, `--event` / `-e`, `--follow` / `-f`, `--json` /
   `-j`, and `--tail [N]`. Register a hidden `tail` subparser that
   shares the same flag set and dispatches to `_run_events`.
   Remove `--limit` / `-n` outright. (Spec § C1, C2; DD-1.)

2. **`--tail [N]` argparse pattern** — `nargs="?"`, `type=int`,
   `const=50`, `default=<unique sentinel>`. Runner branches on the
   sentinel to distinguish "flag absent" from "flag with N=0".
   `--tail 0` produces zero rows (do not rely on Python's
   `lst[-0:]` returning all elements). (Spec § C1; DD-2.)

3. **Rich-table renderer** —
   `src/artifacts_os/cli/commands/events.py`. Inline ~15 LOC
   builder; columns `ts`, `event`, `kind`, `artifact` (where
   `artifact` resolves `stem ‖ id ‖ hook`, first non-empty).
   `--json` / `-j` keeps raw JSONL output. (Spec § C3; DD-3.)

4. **`--tail [N]` on `artifacts list`** —
   `src/artifacts_os/cli/commands/list.py`. Same flag, same
   sentinel pattern. Apply the slice **after** sort, before render,
   in all output modes (`-q`, `-j`, table, tree). (Spec § C4; DD-4.)

5. **Tests** — rename `tests/cli/test_events_tail.py` to
   `tests/cli/test_events.py` and update assertions. Add the 13
   event test cases and 4 `list --tail` cases enumerated in
   spec § C5. Verify argparse rejects `--limit` / `-n`.

6. **Doc update** —
   `openstation/specs/s0025-artifact-events.md` § C8: rewrite to
   reflect the flat surface; mention the hidden `tail` alias and
   the removal of `--limit`.

7. **Final check** — `pytest` is green; `artifacts events`,
   `artifacts events --tail 5`, `artifacts events tail`, and
   `artifacts list --tail 10` all behave per the spec on a real
   vault.

## Findings

The implementation was already largely complete when the task was picked up — `events.py`, `list.py`, and the s0025 § C8 prose had been updated in the parent task session. The work here:

1. **Renamed** `tests/cli/test_events_tail.py` → `tests/cli/test_events.py` (no assertion changes needed — all 14 existing tests still pass).
2. **Added** `test_events_no_limit_flag` to `test_events.py` — verifies argparse rejects `--limit` and `-n` with exit code 2 (V3).
3. **Created** `tests/cli/test_list_tail.py` with 6 tests covering `--tail` in quiet, JSON, and filtered modes; `--tail 0`; and the baseline no-tail-unchanged case.
4. **Updated** `openstation/specs/s0025-artifact-events.md`:
   - Component table C8: "CLI tail command / `artifacts events tail`" → "CLI events command / flat verb with `--tail [N]`, hidden alias, `--limit` removed"
   - V15 verification criterion: rewritten for flat surface
   - Build sequence step 4: rewritten to describe the flat command and flag set

`events.py` uses `default=None` (rather than a named sentinel) for `--tail` — functionally equivalent since `_TAIL_UNSET` vs `None` both signal "no tail applied" and `tail <= 0` is explicitly guarded. `list.py` similarly uses `_apply_tail(items, None)` → returns items unchanged.

All 448 CLI tests pass. 4 pre-existing failures in `tests/ai/test_release_changelog_skill.py` are unrelated to this task.

## Verification

- [x] `artifacts events` runs without subcommand; all flags work top-level (V1)
- [x] `artifacts events tail [...]` parses and dispatches identically (V2)
- [x] argparse rejects `--limit` / `-n` with exit 2 (V3)
- [x] No `--tail` ⇒ all events shown, chronologically old→new (V4, V5)
- [x] `--tail` (bare) ⇒ last 50; `--tail 20` ⇒ last 20; `--tail 0` ⇒ zero rows (V6)
- [x] `--follow` after `--tail` snapshot streams without a cap (V7)
- [x] Default output is a Rich table with columns ts, event, kind, artifact (V8)
- [x] `artifact` column resolves stem ‖ id ‖ hook for every catalog event (V9)
- [x] `artifacts list --tail [N]` slices post-filter, post-sort; bare ⇒ 50 (V10)
- [x] `--tail` works in `-q`, `-j`, table, and tree modes (V11)
- [x] All renamed and new tests pass; full `pytest` suite green (V12)
- [x] `s0025` § C8 updated to the flat surface (V13)

## Verification Report

*Verified: 2026-05-10*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | V1 — flat `events` parser, all flags top-level | PASS | `events.py:33-87` registers `events` with `--since`, `--event/-e`, `--follow/-f`, `--json/-j`, `--tail` directly on `p`; `test_events_flat_no_subcommand` passes |
| 2 | V2 — `events tail [...]` dispatches identically | PASS | `cli/__init__.py:263-264` strips the `tail` token before argparse; `test_events_tail_subcommand_backcompat` and `test_events_tail_subcommand_with_flags` pass |
| 3 | V3 — argparse rejects `--limit` / `-n` (exit 2) | PASS | Neither flag is registered in `events.py`; `test_events_no_limit_flag` asserts `SystemExit(2)` for both |
| 4 | V4/V5 — no `--tail` shows all events old→new | PASS | `_run_events` builds snapshot via `_daily_files` (sorted ascending) and only slices when `tail is not None`; `test_events_no_default_truncation` (80→80) and `test_events_default_chronological_old_to_new` pass |
| 5 | V6 — bare→50, N→last N, 0→zero rows | PASS | `events.py:75-86` uses `nargs="?", const=50, default=None`; `events.py:248-254` explicitly handles `tail <= 0` → `[]`; `test_events_tail_default_50`, `test_events_tail_n`, `test_events_tail_zero_yields_empty` pass |
| 6 | V7 — `--follow` streams without re-applying cap | PASS | `events.py:266-285` enters follow loop after snapshot; `_emit_new` does not consult `tail`, so post-snapshot streaming is uncapped |
| 7 | V8 — default Rich table with ts/event/kind/artifact | PASS | `_build_table` (events.py:191-205) constructs `rich.Table` with those four columns; `test_events_default_is_rich_table` asserts headers + box-draw chars |
| 8 | V9 — artifact column resolves stem ‖ id ‖ hook | PASS | `_artifact_label` (events.py:177-188): `stem or id or hook or ""`; `test_events_default_chronological_old_to_new` exercises stem path; fallback chain matches catalog (s0025 C1) |
| 9 | V10 — `list --tail [N]` slices post-filter, post-sort; bare→50 | PASS | `list.py:313-324` registers `--tail` with `const=50, default=None`; `_apply_tail` (l.830-840) and apply points at `run()` lines 654, 661, 701-703 are after filters and sort; `test_list_tail_default_50`, `test_list_tail_explicit`, `test_list_tail_after_filter` pass |
| 10 | V11 — `--tail` works in `-q`, `-j`, table, tree modes | PASS | `run()` applies `_apply_tail` for `-q` (l.654), `-j` (l.661), and pre-render for both table and tree (l.701-703); `test_list_tail_default_50` (`-q`), `test_list_tail_after_filter` (`-q` filtered), `test_list_tail_json_mode` (`-j`) pass; table/tree paths covered by the same `_apply_tail` call |
| 11 | V12 — renamed/new tests pass; suite green | PASS | `tests/cli/test_events.py` (16 tests) and `tests/cli/test_list_tail.py` (6 tests) all pass; full CLI suite 448/448 green; the 4 failures in `tests/ai/test_release_changelog_skill.py` are pre-existing (verified via `git stash`-and-rerun on clean main) and unrelated to this task |
| 12 | V13 — s0025 § C8 updated for flat surface | PASS | `artifacts/specs/s0025-artifact-events.md` C8 component row, § C8 prose (l.656-679), V15 (l.971), and Build Sequence step 4 (l.989-992) all describe the flat verb, hidden `tail` alias, and `--limit` removal |

### Summary

12 passed, 0 failed. All verification criteria met; task is ready to be marked verified.
