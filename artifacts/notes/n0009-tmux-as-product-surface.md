---
kind: note
id: n0009
name: tmux-as-product-surface
status: active
---

# Tmux As Product Surface

Captures the brainstorm about why tmux is no longer just an
"implementation backend" for openstation runs but a load-bearing
**user surface** — and what that reframing implies for the product.
Triggered by the user prompt "we leverage tmux a lot in multiple
sessions; think about a best tmux config for artifacts-os and
openstation."

## What we have today

### Openstation tmux backend (`docs/tmux-backend.md`)

- **Three modes** configurable via `run.tmux.mode`:
  - `window` (default) — new window inside a shared `os` target session
  - `session` — a brand-new top-level tmux session per run
  - `pane` — horizontal split inside the current target window
- **Naming convention**: `{project.alias}-{task-name}`, e.g.
  `artifacts-0042-fix-bug`. Verify runs prefix `verify-`.
- **Run-complete chain** wires `state.db` updates, hook firing, and
  `remain-on-exit on` for failed runs so the user can post-mortem
  the pane.
- **Session discovery** scans live tmux entities matching the
  `{alias}-` prefix across all three modes.
- **Known edge cases** documented: name conflicts, stale
  `remain-on-exit` panes, ghost runs from crashes,
  `send-keys` truncation.

### How this very repo is configured

```yaml
# .openstation/openstation.yaml
project: { alias: "artifacts" }
run:
  detached_backend: tmux
  tmux: { mode: session }
```

We're using **`session` mode**: every agent run gets its own
top-level tmux session named `artifacts-{id}-{slug}`. With even
two or three concurrent agents this becomes a forest of top-level
sessions to navigate.

### What's missing

- **No project workspace bootstrap.** Opening a project in a
  fresh tmux means hand-building windows for editor, scratch
  shell, "watch agents," etc. There's no `openstation tmux init`
  or equivalent.
- **Window/session names carry no health signal.** A failed run
  with `remain-on-exit on` looks identical to a live one in
  `tmux ls` / status line. The user has to switch into the pane
  or call `openstation sessions` to see status.
- **Mode default is one-size-fits-all.** `session` vs `window` vs
  `pane` is a real workflow trade-off (top-level navigation vs
  grouping vs current-context overlay) and there's no decision
  guidance in docs, no smarter default, and no per-task override
  ergonomics surfaced to the operator.
- **No opinionated tmux config snippets.** Power users who want
  status-line widgets ("3 running, 1 failed"), prefix bindings to
  jump between openstation windows, or a recommended pane layout
  have to invent it.

## Reframing: tmux is the primary monitoring surface

The "backend" framing implies tmux is an interchangeable detail
behind `openstation run -d`. In practice — for any operator using
this tool day-to-day — tmux **is** the monitoring UI. They live
inside it; they jump between agent sessions; they triage failures
visually. Treating it as merely a backend leaves usability
table-stakes on the floor.

This note doesn't argue for shipping a `.tmux.conf`. It argues
that openstation's tmux integration deserves product-level
attention on three concrete fronts:

1. **Workspace bootstrap** — make starting work on a project a
   single command that yields a tmux layout matching how
   operators actually use the tool.
2. **At-a-glance health** — surface run status in
   tmux-discoverable places (window/session names, status line,
   pane titles) so the operator doesn't have to leave tmux to
   know which agents are healthy.
3. **Mode & sessioning UX** — make the choice between `window`
   / `session` / `pane` legible: smarter default, decision
   matrix in docs, easy per-task override.

## Themes (problems → product opportunities)

### A. Project workspace bootstrap is DIY

**Problem.** A user opening artifacts-os for the day:

- Starts a tmux session manually
- Splits or windows for editor / shell / log tail
- Runs `openstation run -d` separately, agents land elsewhere
- No one place to see "what's running for this project right now"

**Opportunity.** `openstation tmux` (or `openstation
workspace`) — a single command that opens a project session
preconfigured with named windows: e.g. `editor`, `shell`,
`agents` (live `openstation sessions --watch` or equivalent).
The exact layout is intent-not-contract; it should be
configurable per-project via `openstation.yaml`.

### B. Run health invisible from `tmux ls`

**Problem.** Window names are `artifacts-0042-slug`. A failed
run with `remain-on-exit on` is named identically to a live one.
Status only surfaces inside the pane (logs) or via
`openstation sessions`. Multiplied across 5+ agents this
becomes the dominant friction point.

**Opportunity.** Augment window/session names with a status
glyph or short suffix the run-complete chain owns:
`artifacts-0042-slug` (running) → `artifacts-0042-slug ✗`
(failed) → `artifacts-0042-slug ✓` (complete; usually closed,
but `--remain-on-exit` users see it). Or update the tmux pane
title; or set the tmux status-left to a live count from
`state.db`. Multiple plausible designs; the architect picks.

### C. Mode default + decision guidance is thin

**Problem.** Three modes (`window`/`session`/`pane`); each fits
a different workflow:

- `session` (current default in artifacts-os): great for
  isolating agents, terrible for navigating many of them
- `window` (engine default): natural grouping, but the shared
  `os` target session can collide across multiple openstation
  projects on one machine
- `pane`: useful for solo focused work, less for parallel runs

There's no decision matrix in docs and no signal-driven
default. New users pick whatever the example shows.

**Opportunity.**

- Document a **decision matrix** in `docs/tmux-backend.md`:
  workflow shape → recommended mode.
- Consider per-project default selection during `openstation
  init` based on a couple of questions ("how many concurrent
  agents do you typically run?" "do you work on multiple
  openstation projects on one machine?").
- Make per-task override more discoverable:
  `openstation run --task 0042 -d --tmux-mode pane` exists; UX
  could surface this in `--help`'s common-flow examples.

### D. Multi-project sessioning is fragile

**Problem.** Default target session is `os` for `window` mode.
Two openstation projects on one machine collide unless one
overrides `run.tmux.target_session`. There's no automatic
namespacing by project alias.

**Opportunity.** Default `target_session` should derive from
`project.alias` (e.g. target `artifacts` for this repo, `myproj`
for another). Backwards compat: keep `os` as fallback if
`alias` is unset.

### E. Power-user `.tmux.conf` snippets

**Problem.** Operators willing to customize tmux have no
reference. Status-line widgets showing live agent counts,
custom keybindings to step through openstation windows, color
conventions for healthy vs failed runs — every operator
reinvents.

**Opportunity.** Ship optional, copy-paste snippets in
`docs/tmux-backend.md` (or a sibling `docs/tmux-recipes.md`).
Not part of `openstation init` (don't touch user dotfiles); a
documentation artifact users opt into.

This is the **lowest-priority** theme — covered last, or not at
all.

## Priorities (impact × effort)

1. **A (workspace bootstrap)** — biggest UX leap; closest to
   "tmux as a product." High value, medium effort. **Filed as
   [[t0097-openstation-tmux-project-workspace-bootstrap]].**
2. **B (status-aware naming)** — concrete daily pain;
   incremental on top of existing `run-complete` chain. High
   value, low-medium effort. **Filed as
   [[t0098-openstation-tmux-surface-run-status]].**
3. **C (mode default + guidance)** — partly a doc task, partly
   a settings change. Medium value, low effort. **Filed as
   [[t0099-openstation-tmux-mode-default-and]].** Theme D
   (multi-project namespacing) folded in; the architect decides
   whether to split.
4. **E (`.tmux.conf` snippets)** — nice-to-have. **Skip for
   now; reconsider once A/B/C are out.**

## Open questions

- **Naming of the new surface.** `openstation tmux init`?
  `openstation workspace`? Generic `openstation start`? The user
  surface should reflect that this isn't strictly a tmux thing —
  it's a project-session bootstrap that *uses* tmux today and
  could use a different multiplexer tomorrow.
- **Where does run-state→window-name coupling live?** Run-complete
  hook? Backend `_set_pane_remain_on_exit` neighbor? Decision
  belongs to the architect.
- **Does workspace bootstrap belong in `openstation` at all?** It
  could be a thin shell wrapper or a tmuxinator template the
  project ships under `bin/` or `.openstation/`. Worth letting
  the architect spec consider before we add CLI surface.
- **Per-project `tmux.workspace` settings shape.** Free-form
  command list? Declarative `windows: [...]` schema mirroring
  tmuxinator? Let the spec settle.

## References

- `.openstation/docs/tmux-backend.md` — current backend
  reference (modes, naming, run-complete, edge cases)
- `.openstation/docs/sessions.md` — run model, `openstation
  sessions`, stale detection
- `.openstation/openstation.yaml` — current `mode: session`
  config in this repo
- [[t0092-allow-openstation-status-to-transition]] — pdm task
  exemplar (user-story-shaped, architect spec sub-task pattern)
- [[t0097-openstation-tmux-project-workspace-bootstrap]] — Theme A
- [[t0098-openstation-tmux-surface-run-status]] — Theme B
- [[t0099-openstation-tmux-mode-default-and]] — Themes C + D
