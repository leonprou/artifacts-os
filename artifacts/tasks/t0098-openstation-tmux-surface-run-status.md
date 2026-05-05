---
kind: task
id: t0098
name: openstation-tmux-surface-run-status
type: feature
status: backlog
assignee: 
owner: user
created: 2026-05-05
---

# Openstation Tmux: Surface Run Status In Window Names

## User Story

**As an** operator running multiple openstation agents
concurrently in tmux,
**I want** each run's tmux window/session/pane name to reflect its
live status (running, complete, failed),
**so that** I can scan `tmux ls` (or my status line) and know
which agents need my attention without diving into every pane.

## Why

- **Today's names are status-blind.** The tmux backend names
  windows `{alias}-{task-name}` (see
  `.openstation/docs/tmux-backend.md` § Naming Convention). A
  failed run with `remain-on-exit on` is named identically to a
  live one — the operator must enter the pane to know.
- **`remain-on-exit` panes accumulate.** Per the same doc § Stale
  `remain-on-exit` Panes, failed runs persist by design so the
  operator can post-mortem. Without a status signal in the name,
  the post-mortem queue is invisible until the operator asks for
  it.
- **Concrete daily friction.** With `run.tmux.mode: session`
  (this repo's config), the user sees a top-level session per
  run in `tmux ls`. Five live agents and three failed leftovers
  are visually indistinguishable. Captured in
  [[n0009-tmux-as-product-surface]] § B.
- **Hookpoint exists.** `run-complete` already updates
  `state.db` and calls `_set_pane_remain_on_exit` on failure
  (`docs/tmux-backend.md` § Failure / Max-Turns — Pane Stays
  Open). Renaming or annotating the tmux entity is a sibling
  operation in the same chain.

## Directions

*Intent, not contract — the architect refines.*

- The tmux entity (window in `window` mode, session in `session`
  mode, pane title in `pane` mode) should reflect run status at
  a glance. A glyph suffix is one option (e.g. `… ✗` for failed,
  no suffix for running, `… ✓` briefly for complete before
  pane closes); a status-line widget is another; the spec
  decides.
- **Run state must drive the rename**, not the operator. The
  `run-complete` chain owns final state already; that's the
  natural place to update the tmux name on `failed` /
  `complete`. For `running`, the initial name is set at launch
  and stays unchanged.
- **Minimal surgical change.** Don't redesign the naming
  convention; *append* a status signal to the existing scheme.
  Operators with muscle memory for `artifacts-0042-slug`
  shouldn't need to relearn anything.
- **All three modes.** `window`, `session`, and `pane` should
  each have a coherent answer (rename window, rename session,
  set pane title). Acceptable for the implementations to differ
  per-mode as long as the user-observable signal is consistent.
- **Post-mortem ergonomics.** Operators looking at a wall of
  failed-run remnants should be able to identify and clean them
  up easily — possibly via `openstation sessions --kill --failed`
  or similar. That cleanup ergonomics piece can be a follow-up
  task; this one focuses on the visual signal first.

## Open Questions

*Decisions deliberately deferred to the architect spec sub-task.*

- **Visual encoding.** Glyph suffix (`✓` / `✗`)? Color (tmux
  supports `#[fg=red]` in window names but support is patchy
  across themes)? A separate tmux status-line widget driven by
  `state.db`? The spec picks one.
- **Render target.** Window/session name vs pane title vs status
  line — which surface in which mode? Pane titles are the safest
  bet but invisible by default in many configs.
- **`tmux rename-window` vs recreate.** Renaming is cheap; some
  tmux configs treat the name as immutable in scripts. Confirm
  rename is the right primitive.
- **Cross-tmux-version behaviour.** `select-pane -T` and rename
  semantics differ across tmux versions. Minimum version
  supported should be stated.
- **Should running agents *also* show progress?** E.g. turn
  count in the name, or cost-so-far. Probably out of scope for
  v1 — but the spec should explicitly defer or include.
- **Interaction with `--remain-on-exit` flag.** A successful run
  with `--remain-on-exit` keeps the pane around — does it show a
  `✓`? A neutral marker? Stay un-annotated?

## Sub-Tasks

- Spawn an **architect spec sub-task** to settle the visual
  encoding, the render target per-mode, the hookpoint in the
  run-complete chain, and the cross-version compatibility floor.
  Implementation task follows the spec.

## Verification

- A failed run leaves a tmux entity (window/session/pane) whose
  name or title clearly signals `failed` to a user scanning
  `tmux ls` or the tmux status line — confirmed by deliberately
  triggering a failure (e.g. max-turns) and checking the live
  tmux state.
- A live run displays a name without the failed signal — a user
  can distinguish "running" from "failed" without entering the
  pane.
- All three modes (`window`, `session`, `pane`) get a coherent
  status signal — verified in each mode by triggering a failure
  and inspecting the corresponding tmux entity.
- The naming change is **additive**: operators who already
  parse `{alias}-{task-name}` in scripts continue to match it
  (e.g. status signal appended after a separator the spec
  defines, not interpolated mid-name).
- The architect spec sub-task lands first; the implementation
  task references the spec ID.
- `docs/tmux-backend.md` is updated to document the status
  signal, render target per-mode, and supported tmux versions.
