---
kind: task
id: t0097
name: openstation-tmux-project-workspace-bootstrap
type: feature
status: backlog
assignee: 
owner: user
created: 2026-05-05
---

# Openstation Tmux: Project Workspace Bootstrap Command

## User Story

**As an** operator starting a working session on an
openstation-managed project,
**I want** a single command that opens a tmux workspace pre-built
for that project — editor, scratch shell, and a live agents view —
**so that** I'm not hand-rolling the same tmux layout every morning
and my agent runs land in a session I'm already inside.

## Why

- **Tmux is already the primary monitoring surface.** The existing
  tmux backend (`.openstation/docs/tmux-backend.md`) creates per-run
  windows or sessions, but there's no entry-point that bootstraps
  the *project-level* layout. Operators DIY this every time.
- **Concrete signal in this repo.** This repo runs with
  `run.tmux.mode: session` (see `.openstation/openstation.yaml`),
  so every agent run becomes a top-level tmux session — making it
  even more important that the operator has a project session
  *they live in* to pivot from. Today there is none.
- **User prompt that triggered this.** "We leverage tmux a lot in
  multiple sessions" — captured in
  [[n0009-tmux-as-product-surface]] § A. Workspace bootstrap is
  the highest-priority theme that came out of that brainstorm.
- **Adjacent precedent.** `openstation init` already configures
  the project; a workspace-bootstrap command is the natural
  daily-use companion to the one-time `init`.

## Directions

*Intent, not contract — the architect refines.*

- A single command (working name: `openstation tmux`,
  `openstation workspace`, or `openstation start` — bikeshed in
  the spec) opens a project tmux session named after the project
  (e.g. derived from `project.alias`).
- The session should land with a small, opinionated default
  layout: at minimum **editor** window, **shell** window, and
  **agents** window (the latter showing live `openstation
  sessions` activity — could be `openstation sessions --watch` or
  similar).
- Layout should be **per-project configurable** via
  `openstation.yaml` (e.g. `workspace.windows: [...]`). Operators
  who want a different shape get it without forking the command.
- Idempotent: running it twice should attach to the existing
  session, not create a duplicate.
- Plays nicely with the existing tmux backend — agent runs
  triggered from inside the workspace continue to land where the
  current `run.tmux.mode` directs them.

## Open Questions

*Decisions deliberately deferred to the architect spec sub-task.*

- **Command name.** `tmux init` couples to the multiplexer;
  `workspace` is generic; `start` is short. The spec picks. The
  pdm preference is something multiplexer-agnostic since this
  layout could plausibly target Zellij, screen, or wezterm panes
  later — but that's a soft preference.
- **Where does the layout config live?** Inline under
  `workspace:` in `openstation.yaml`? Separate
  `.openstation/workspace.yaml`? A tmuxinator-style YAML file the
  command shells out to?
- **Should the "agents" window auto-populate?** I.e. does the
  command itself launch `openstation sessions --watch` (or
  equivalent) into the agents pane, or is that a hint the
  operator wires up themselves?
- **Reattach semantics.** If the project session already exists,
  do we attach silently, or print a hint and require an
  `--attach` flag? Probably the former; surface the choice in the
  spec.
- **Multi-project on one machine.** Two projects open at once →
  two separate tmux sessions named after each `project.alias`.
  Confirm this is the model and that it doesn't conflict with the
  tmux backend's `target_session` for `mode: window`.
- **Default-on or opt-in.** Should `openstation init` write a
  starter `workspace:` block into `openstation.yaml`, or do
  operators opt in by adding it themselves?

## Sub-Tasks

- Spawn an **architect spec sub-task** to settle the command
  name, the workspace config schema, the default layout,
  reattach semantics, and the integration boundary with the
  existing tmux backend. Implementation task follows the spec.

## Verification

- A single openstation command opens a tmux session whose name
  derives from the project (e.g. `artifacts` for this repo)
  containing the configured windows — confirmed live by running
  it in a fresh shell and inspecting `tmux ls`.
- Re-running the command from outside the session attaches to
  the existing one rather than creating a duplicate (no name
  collision, no error).
- Per-project layout configured in `openstation.yaml` is
  honored: changing the windows list and re-running produces the
  new layout (after killing the prior session).
- Agent runs launched from inside the workspace land where the
  current `run.tmux.mode` directs them; the workspace command
  doesn't break the existing tmux backend behaviour.
- `--help` documents the workspace command alongside `init` and
  `run`.
- The architect spec sub-task lands first; the implementation
  task references the spec ID.
