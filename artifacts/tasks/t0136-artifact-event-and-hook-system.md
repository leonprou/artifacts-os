---
kind: task
id: t0136
name: artifact-event-and-hook-system
type: feature
status: done
assignee: 
owner: user
created: 2026-05-10
started: 2026-05-07
subtasks:
  - "[[t0130-spec-for-artifact-events-with]]"
  - "[[t0135-implement-artifact-events-and-hooks]]"
completed: 2026-05-11
---

# Artifact Event + Hook System

## User story

> **As an agent, user, or external application, I want to react to
> significant changes in an artifacts-os vault — without polluting
> the core CRUD path or blocking it on my reactions — so that I can
> automate workflows, get notified locally, or integrate vault
> activity into other tools.**

Today vault operations (create, update, status transitions) are
silent: nothing observes them and nothing can react. This feature
adds a two-layer reactive surface so the vault becomes
*subscribable* by all three audiences.

## Intent (not contract)

Precise design and module placement is owned by the architect spec
sub-task ([[t0130-spec-for-artifact-events-with]] →
[[s0025-artifact-events]]). User-level intent only:

1. **Significant artifact operations emit events** — at minimum:
   created, updated, status-changed, validated. Events are
   observable by anything outside the core CRUD path.
2. **Always-on telemetry vs opt-in reactions** are clearly separate
   concerns: a stream that records *what happened*, and a hook
   layer that *reacts*.
3. **Subscribers are configurable per vault** — declarative config
   lets users register reactions (run a command, notify locally,
   drop a file) without writing Python.
4. **Three audiences must work end-to-end**: an agent reacting
   programmatically, a user wiring up a CLI hook, and an external
   app tailing the event stream.
5. **Non-blocking by default** — emitting an event must never break
   a CRUD operation. Any blocking behaviour is opt-in and
   explicit.
6. **Local notification surface** — beyond shell commands,
   subscribers can express "notify me locally" (desktop bell, file
   drop, etc.) without external dependencies.

## Sub-tasks

- [[t0130-spec-for-artifact-events-with]] — architect spec
  (`s0025-artifact-events` v2). **Status: verified.**
- [[t0135-implement-artifact-events-and-hooks]] — implementation
  per `s0025` build sequence. **Status: review.**

## Verification

High-level acceptance signals — detailed criteria live in
`s0025` § Verification (V1–V16) and are tracked on t0135.

- [ ] Spec produced and verified ([[t0130]]).
- [ ] Implementation merged and full test suite green ([[t0135]]).
- [ ] Documentation updated: `docs/architecture.md` Module Map
      shows `events/` and `hooks/`; `docs/settings.md` documents
      the `events:` and `hooks:` YAML sections.
- [ ] All four worked-example audiences runnable against a test
      vault: agent self-assigning, user CLI hook, external app
      tailing the JSONL stream, external async runtime via
      catch-all hook.
- [ ] `s0004-artifacts-os-log-module` bumped to `version: 2` with
      cross-reference pointer to `s0025` for the event-type table.
      `log/` API itself is unchanged.

## Out of Scope

Per `s0025` § Out of Scope — deliberate exclusions for follow-up
features, not this one:

- In-tree async / queued execution (delegated to external
  runtimes via catch-all hook per DD-5).
- Remote / webhook delivery, durable retry, threaded hooks.
- Cross-vault event federation.
- Third-party action plugins (registry shape only; loading model
  unspecified).
- Event stream rotation / compaction.
- Hook dry-run / test mode.
- The `artifact.deleted` event (no delete operation in
  `core/store.py` yet — adds when delete lands).

## References

- [[s0025-artifact-events]] — design spec (v2).
- [[s0004-artifacts-os-log-module]] — Logger/LogReader API
  (untouched by this work; gets a `version: 2` cross-ref bump).
- [[t0130-spec-for-artifact-events-with]] — architect spec
  sub-task.
- [[t0135-implement-artifact-events-and-hooks]] — implementation
  sub-task.
