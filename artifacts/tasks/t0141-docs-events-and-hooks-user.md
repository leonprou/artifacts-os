---
kind: task
id: t0141
name: docs-events-and-hooks-user
type: documentation
status: done
assignee: author
owner: user
depends_on:
  - "[[t0140-implement-s0027-align-events-cli]]"
  - "[[t0135-implement-artifact-events-and-hooks]]"
created: 2026-05-10
---

# Docs: Events And Hooks User Guide + Cli Reference

## User story

> **As a user, agent, or external integrator, I want a single
> doc that explains what events and hooks are, what events the
> vault emits, how to subscribe, and how to drive the events
> stream from the CLI — so I can wire up reactions or
> integrations without reading the spec.**

The events + hooks feature shipped in t0135, and the CLI surface
was finalized in t0140 (`s0027`). Configuration reference exists
in `docs/settings.md`, but there is no narrative doc that:

- introduces the two-layer model (always-on stream vs opt-in
  reactions),
- enumerates the event catalog,
- shows the four worked-example audiences end-to-end,
- documents the `artifacts events` CLI surface.

This task closes that gap and unblocks the documentation
checkbox on parent feature [[t0136-artifact-event-and-hook-system]].

## Intent (not contract)

Author owns the narrative shape. Directional bullets only:

1. **Two files** — the event catalog and CLI reference live in
   `docs/events.md`; the hooks reactive layer lives in
   `docs/hooks.md`. Each opens with a two-sentence two-layer
   model summary and cross-links the other. The split avoids
   duplicating the event catalog and serves distinct audiences
   (stream readers vs hook configurers) without a 400-line page.
2. **Audience-first overview** — open with *why* the feature
   exists and the always-on-stream vs opt-in-reactions split.
   Keep it readable to someone who has never read `s0025`.
3. **Event catalog** — list the events the vault emits today
   (created, updated, status-changed, validated, plus any
   others present). For each: when it fires and what payload
   fields the hook env contract exposes. Cross-link
   `docs/settings.md` for the env-var table rather than
   duplicating it.
4. **Four worked examples** — one per audience listed in
   t0136's verification:
   - agent self-assigning on a matching event,
   - user wiring a CLI/notify hook via `artifacts.yaml`,
   - external app tailing the JSONL stream,
   - external async runtime via a catch-all hook.
   Each example should be runnable on a real vault.
5. **CLI section** — document `artifacts events`: default
   table output, `--json`/`-j`, `--tail [N]` (including
   `--tail 0` and bare-flag default), `--follow`/`-f`,
   `--since`, `--event`/`-e`, the hidden `tail` alias, and
   the removal of `--limit`. Mirror the conventions in
   `CLAUDE.md` § "CLI Conventions".
6. **Cross-links** — point to `s0025` for design rationale and
   `docs/settings.md` for full config reference. Add an entry
   to `docs/architecture.md`'s navigation if there is one.
7. **Don't duplicate** — settings keys already documented in
   `docs/settings.md` should be linked, not copy-pasted.

Implementation details (file structure, exact heading order,
prose voice) are the author's call.

## Verification

- [x] `docs/events.md` and `docs/hooks.md` exist and each reads
      coherently end-to-end without requiring `s0025`.
- [x] Two-layer model (always-on stream vs opt-in reactions)
      is explained in the overview.
- [x] Event catalog is present and matches what `events/`
      emits in `src/artifacts_os/`.
- [x] All four worked examples are present and verified
      runnable against a test vault.
- [x] CLI section covers `artifacts events` flags from t0140
      (`--tail [N]`, `--follow`, `--since`, `--event`, `--json`,
      hidden `tail` alias, no `--limit`).
- [x] Cross-links to `s0025` and `docs/settings.md` are in
      place; no duplicated settings reference.
- [ ] Parent task [[t0136-artifact-event-and-hook-system]]
      documentation checkbox can be marked complete.

## Notes

- Source material:
  - `s0025-artifact-events` — full design + event catalog
  - `s0027-align-events-cli-with-list` — final CLI surface
  - `docs/settings.md` §§ Events / Hooks — config reference
  - `src/artifacts_os/core/events.py`,
    `src/artifacts_os/cli/commands/events.py` — emitted
    events and CLI behaviour
- Prior art: `.openstation/docs/events.md` and
  `.openstation/docs/hooks.md` show the shape OpenStation uses;
  borrow structure where it fits.
