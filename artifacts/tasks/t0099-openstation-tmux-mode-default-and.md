---
kind: task
id: t0099
name: openstation-tmux-mode-default-and
type: feature
status: backlog
assignee: 
owner: user
created: 2026-05-05
---

# Openstation Tmux: Mode Default And Decision Guidance

## User Story

**As an** operator picking how to detach openstation runs into
tmux,
**I want** the choice between `window` / `session` / `pane` modes
to be legibly documented and reasonably defaulted —
**so that** I'm not guessing at trade-offs and my project's tmux
sessions don't collide with another openstation project on the
same machine.

## Why

- **Three modes exist; guidance doesn't.** `.openstation/docs/tmux-backend.md`
  § Modes lists `window` / `session` / `pane` and what each
  *does*, but nothing about *when to pick which*. Operators
  default to whatever the example shows.
- **Default `target_session: os` collides across projects.** In
  `mode: window` the shared target session is hard-coded to
  `os`. Two openstation projects on the same machine will both
  funnel agents into the same tmux session unless one operator
  knows to override `run.tmux.target_session`. This is a quiet
  multi-project footgun. Captured in
  [[n0009-tmux-as-product-surface]] § D.
- **This repo runs `mode: session`** (see
  `.openstation/openstation.yaml`) — a defensible choice for a
  small project, but with concurrent runs it produces a forest
  of top-level tmux sessions. Whether that's the right default
  for new openstation projects is currently undocumented.
- **Per-task override exists but is invisible.**
  `--tmux-mode` works (per `docs/tmux-backend.md` § Modes) but
  isn't surfaced in `--help` examples or anywhere a new operator
  would see it.

## Directions

*Intent, not contract — the architect refines.*

- Add a **decision matrix** to `docs/tmux-backend.md`: workflow
  shape (concurrent agent count, single-project vs
  multi-project, attach-and-watch vs fire-and-forget) →
  recommended mode. Short, opinionated.
- Make the **default `target_session` derive from
  `project.alias`** when alias is set (e.g. `artifacts` for
  this repo, `myproj` for another), falling back to `os` when
  alias is unset. Backwards-compatible: existing projects
  with the literal `os` default continue to work; the default
  *resolution* changes, not the static value.
- **Re-evaluate the engine default mode.** The engine default
  today is `window`; this repo opts into `session`. Whether
  `window` is the right new-project default after the
  multi-project fix is a question the spec should address with
  evidence (or explicitly defer).
- **Surface the per-task override in `--help`.** `openstation
  run --help` should mention `--tmux-mode` with a one-line
  explanation, not just list it.
- **Narrow scope.** Don't redesign the backend. Settings change
  + docs + help-text polish.

## Open Questions

*Decisions deliberately deferred to the architect spec sub-task.*

- **Default mode revisit.** With the `target_session`-from-alias
  fix, is `window` the right engine default? The decision matrix
  the spec produces is the input to this question.
- **Migration path.** If the engine default mode changes,
  existing projects with no explicit `run.tmux.mode` flip
  silently. Acceptable, or do we require an explicit choice in
  `openstation init` going forward?
- **Should `openstation init` ask?** A 2-question prompt
  ("concurrent agents typical?" "multi-project on this
  machine?") feeding `run.tmux.mode` and `target_session` is
  ergonomic but adds setup friction. The spec decides.
- **Decision matrix shape.** Table? Flowchart? Just prose? Match
  conventions already used in `docs/tmux-backend.md`.
- **Fold in [[n0009-tmux-as-product-surface]] § D
  (multi-project namespacing) or split it out?** This task
  bundles the fix; if the spec finds it grows, split.

## Sub-Tasks

- Spawn an **architect spec sub-task** to: (a) draft the
  decision matrix, (b) settle the `target_session`-from-alias
  default and migration path, (c) decide whether the engine
  default mode should change, (d) sketch the `--help` polish.
  Implementation task follows the spec — likely small (settings
  default + doc edits + help-text strings).

## Verification

- `docs/tmux-backend.md` contains a decision matrix that lets a
  new operator pick `window` / `session` / `pane` based on
  workflow signals — confirmed by reading the doc cold.
- Default `target_session` for `mode: window` derives from
  `project.alias` when set; verified by configuring two
  scratch projects with different aliases on one machine and
  confirming agents from each land in different tmux sessions
  without explicit `target_session` override.
- Existing projects (no `run.tmux.mode` and no explicit
  `target_session`) continue to function — verified by running
  this repo's existing flows after the change.
- `openstation run --help` surfaces `--tmux-mode` with a brief
  description and at least one example.
- The architect spec sub-task lands first; the implementation
  task references the spec ID.
