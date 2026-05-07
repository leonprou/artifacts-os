---
kind: task
id: t0130
name: spec-for-artifact-events-with
type: spec
status: review
assignee: architect
owner: user
created: 2026-05-07
started: 2026-05-07
artifacts:
  - "[[openstation/specs/s0025-artifact-events]]"
---

# Spec For Artifact Events With Subscriber/Hook Config

## Requirements

The architect should produce a spec under `artifacts/specs/` covering an **artifact event system** for `artifacts-os`, with the following user-facing intent:

1. **Events fire on significant artifact operations** so that agents, users, and external apps can react to changes in a vault — without polluting the core CRUD path or blocking it on subscriber failures.

2. **A documented event catalog** — at minimum: artifact created, artifact updated, and any other operations the architect deems significant (e.g. delete if/when it exists, validation outcomes). The spec defines the catalog and per-event payload fields. *(intent, not contract — exact set is a design call)*

3. **Subscriber configuration model similar to OpenStation hooks** — declarative, per-vault config (likely under `artifacts/artifacts.yaml` or a sibling file) that lets users register reactions to events. Concepts to mirror from `.openstation/docs/hooks.md`:
   - matchers (event type + optional filters such as `kind`, status, etc.)
   - command-style subscribers (shell command with env vars carrying event payload)
   - pre vs post phases where it makes sense, or an explicit decision to keep it post-only
   - failure semantics (warn vs block), spelled out per phase

4. **Local notification surface** — beyond shell commands, the spec must consider how a subscriber expresses 'notify me locally' (e.g. desktop notification, terminal bell, file drop). The architect picks a baseline mechanism and documents extensions.

5. **Subscribable by agents, users, and apps** — the spec must show one concrete worked example per audience (agent reacting to an event, user-defined CLI hook, external app tailing the event log).

6. **Relationship to the `log/` stub and `s2063`** — the spec must explicitly reconcile this work with the existing `log/` module (`src/artifacts_os/log/__init__.py`) and the referenced spec `s2063-artifacts-os-log-module`. Either fold subscribers into `log/` or justify a separate module and place it correctly in the dependency DAG (`core → log → ai`).

7. **Always-on telemetry layer vs opt-in subscribers** — clearly separate the two concerns (parallel to OpenStation's events-vs-hooks split): an always-on event stream that records what happened, and an opt-in subscriber layer that reacts. The spec must articulate both, and how they relate.

8. **Non-blocking by default** — emitting an event must never break a CRUD operation. Subscriber failures must default to warnings, not aborts. Any 'blocking' behaviour (analogous to pre-hooks) is opt-in and called out explicitly.

9. **Trade-off section** — the spec should compare at least two design alternatives for subscriber configuration (e.g. yaml-only vs yaml + Python entry points) and pick one with reasoning.

10. **Out of scope, made explicit** — the spec lists what it deliberately does *not* cover (e.g. remote/webhook delivery, durable queues, retry semantics) so a follow-up implementation task has a clean boundary.

## Verification

- [ ] Spec file exists at `artifacts/specs/sNNNN-artifact-events.md` with appropriate frontmatter (`kind: spec`, `name`, `id`).
- [ ] Event catalog is enumerated with payload schemas for each event type.
- [ ] Subscriber configuration format is fully specified (file location, schema, example entries).
- [ ] Worked examples cover all three audiences: agent, user, app.
- [ ] Always-on event stream and opt-in subscriber layer are documented as separate concerns with their relationship explained.
- [ ] Failure semantics (blocking vs non-blocking, warning vs abort) are explicit per phase.
- [ ] Relationship to the existing `log/` stub and `s2063` is reconciled — either integration plan or justification for a sibling module, with module placement in the dependency DAG.
- [ ] At least one trade-off comparison with a justified pick is present.
- [ ] Out-of-scope section is included.
- [ ] Spec references and aligns with prior art in `.openstation/docs/events.md` and `.openstation/docs/hooks.md` where relevant.

## Progress

- 2026-05-07: Authored `s0025-artifact-events` (905 lines) covering
  always-on event stream + opt-in subscriber layer. Folded into
  `log/` per DD-1; `core` dispatches via registered emitters in a
  new `core/events.py` to respect the DAG. YAML-only subscribers
  (DD-2), opt-in pre-phase blocking (DD-3), closed event catalog
  (DD-4). Three worked examples cover agent, user, and external-app
  audiences. Reconciled with `s0004` (extends, not replaces) and
  out-of-scope section drawn for follow-up implementation task.

## Findings

Produced `s0025-artifact-events` — a 905-line feature spec
covering a two-layer reactive surface for `artifacts-os`:

- **Always-on event stream** — JSONL daily files at
  `artifacts/logs/events/YYYY-MM-DD.jsonl`, written by every
  `store.create` / `store.update` call.
- **Opt-in subscriber layer** — declarative reactions
  configured in `artifacts.yaml` under a top-level
  `subscribers:` key.

### Key Design Decisions

- **DD-1 — Fold into `log/`** rather than introducing a sibling
  module. Three new files (`stream.py`, `subscribers.py`,
  `actions.py`) plus a settings extension live under
  `src/artifacts_os/log/` alongside the existing `Logger` /
  `LogReader` API from `s0004`. Trade-off table compares fold
  vs sibling vs `core/` placement.
- **DD-2 — YAML-only subscribers**. Compared against
  YAML + Python entry points; YAML wins on audit, sandbox, and
  install simplicity. Power users compose via shell.
- **DD-3 — Pre-phase blocking is opt-in**. Library invariant
  (emit must not break CRUD) preserved by default; explicit
  `blocking: true` opts into the gate-keeping use case.
- **DD-4 — Closed event catalog**. Adding event types requires
  spec revision; gives external apps a stable wire contract.

### DAG Reconciliation

`core` cannot import `log` (DAG violation). The dispatch goes
*outward* via a registration callable in a new
`core/events.py`: `register_emitter(fn)` + `_dispatch(event,
**payload)` that swallows every emitter exception. `log/`
registers `stream.append` and `subscribers.notify` on import.
`core` adds zero new dependencies and works fine without
`log/` imported.

### Event Catalog (closed in v1)

`artifact.created`, `artifact.updated`, `artifact.validated`,
`subscriber.fired`, `subscriber.failed`. Each has a documented
JSON schema with universal `ts` + `event` fields plus
event-specific payload. Deliberately omits `artifact.deleted`
(no delete operation exists yet).

### Subscriber Action Types

`shell` (subprocess), `notify` (cross-platform desktop with
terminal-bell fallback), `file-drop` (write payload to
templated path). Action registry is structured for in-tree
extension; third-party plugins are out of scope for v1.

### Worked Examples

Three end-to-end examples — architect agent self-assigning
spec-typed tasks; user receiving desktop notifications + bells
on review-ready tasks; external dashboard tailing the JSONL
stream with `tail -F | jq` or `artifacts events tail --follow`.

### Relationship to `s0004` and the `log/` stub

This spec extends `s0004-artifacts-os-log-module` rather than
replacing it. `Logger` / `LogReader` API is unchanged. The
implementing task should bump `s0004` to `version: 2`, mark
`status: final`, and add a "Superseded sections" pointer for
the event-type table. `log/__init__.py` docstring updates the
`Implementation spec` reference to point to `s0025` for the
event/subscriber surface and keeps the writer/reader pointer
to `s0004`. The old `s2063` reference in the docstring
resolves to `s0004` post-migration.

### Out of Scope (made explicit)

Remote / webhook delivery, durable retry, async subscribers,
cross-vault federation, third-party action plugins, daily-file
rotation, emit-time payload validation, dry-run mode. Each is
listed with rationale so a follow-up task has a clean
boundary.

### Build Sequence

Nine independently-testable steps from C2 dispatcher → C7 core
integration → C3 stream → C8 CLI → C6 settings → C5 actions →
C4 subscriber loader → audit-trail events → end-to-end
verification harness.

## Downstream

- **Implementation task** — pick up the build sequence in
  `s0025` § "Build Sequence". Likely a feature-typed parent
  task with sub-tasks per build step.
- **`s0004` revision** — bump to `version: 2`, mark `final`,
  add cross-reference pointer to `s0025` for the event-type
  schemas. Could be folded into the implementation task or
  done first as a docs-typed task.
- **`log/__init__.py` docstring update** — update spec
  references (`s2061` → `s0005`, `s2063` → `s0004`, plus add
  `s0025`). Small docs follow-up.
- **`docs/architecture.md`** — once implemented, the `log`
  row in the Module Map needs to mention "event stream and
  subscribers" alongside "JSONL operation log".
- **`docs/settings.md`** — needs an `events:` /
  `subscribers:` section once `LogSettings.from_base` ships.
- **`artifact.deleted` event type** — add to the catalog when
  delete operation lands in `core/store.py`.
