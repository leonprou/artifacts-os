---
kind: task
id: t0130
name: spec-for-artifact-events-with
type: spec
status: done
assignee: architect
owner: user
parent: "[[t0136-artifact-event-and-hook-system]]"
created: 2026-05-07
started: 2026-05-07
artifacts:
  - "[[openstation/specs/s0025-artifact-events]]"
completed: 2026-05-10
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

- [x] Spec file exists at `artifacts/specs/sNNNN-artifact-events.md` with appropriate frontmatter (`kind: spec`, `name`, `id`).
- [x] Event catalog is enumerated with payload schemas for each event type.
- [x] Subscriber configuration format is fully specified (file location, schema, example entries).
- [x] Worked examples cover all three audiences: agent, user, app.
- [x] Always-on event stream and opt-in subscriber layer are documented as separate concerns with their relationship explained.
- [x] Failure semantics (blocking vs non-blocking, warning vs abort) are explicit per phase.
- [x] Relationship to the existing `log/` stub and `s2063` is reconciled — either integration plan or justification for a sibling module, with module placement in the dependency DAG.
- [x] At least one trade-off comparison with a justified pick is present.
- [x] Out-of-scope section is included.
- [x] Spec references and aligns with prior art in `.openstation/docs/events.md` and `.openstation/docs/hooks.md` where relevant.

## Verification Report

*Verified: 2026-05-10*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec file exists at `artifacts/specs/sNNNN-artifact-events.md` with appropriate frontmatter | PASS | `artifacts/specs/s0025-artifact-events.md` (1089 lines); frontmatter has `kind: spec`, `id: s0025`, `name: artifact-events`, `version: 2` |
| 2 | Event catalog enumerated with payload schemas for each event type | PASS | C1 (lines 205–350) defines 6 events: `artifact.created`, `artifact.updated`, `artifact.status_changed`, `artifact.validated`, `hook.fired`, `hook.failed`. Each has a JSON schema with `ts`, `event`, and event-specific fields. |
| 3 | Subscriber configuration format is fully specified (file location, schema, example entries) | PASS | C6 (lines 530–589) specifies file `artifacts.yaml`, top-level `events:` and `hooks:` keys, full YAML schema with worked example. Matcher schema in lines 592–614. |
| 4 | Worked examples cover all three audiences: agent, user, app | PASS | "Worked Examples" section covers Audience 1 (agent self-assigning, lines 693–716), Audience 2 (user CLI hook, lines 718–749), Audience 3 (external app tailing JSONL, lines 751–772), plus Audience 4 (async runtime). |
| 5 | Always-on event stream and opt-in subscriber layer documented as separate concerns with relationship explained | PASS | "Layer Separation" table (lines 116–124) compares both layers across 7 axes; lines 126–129 explain the relationship ("event stream is the source of truth; hooks are a filter-and-react view"). |
| 6 | Failure semantics (blocking vs non-blocking, warning vs abort) are explicit per phase | PASS | "Phases" table (lines 618–622), invariants I1/I2/I4 (lines 184–190), DD-3 (lines 882–898) on opt-in blocking. Pre/post failure defaults explicitly tabulated. |
| 7 | Relationship to existing `log/` stub and `s2063` reconciled with DAG placement | PASS | Dedicated section "Relationship to `log/` and `s0004`" (lines 992–1024); DD-1 (lines 828–856) compares 4 module options, picks three siblings. DAG diagram on lines 137–141: `core ─┬─ events ─┬─ hooks ─── ai` with `log/` left untouched. |
| 8 | At least one trade-off comparison with a justified pick is present | PASS | Five Design Decisions (DD-1 through DD-5) each present alternatives in a table with chosen option + justification (lines 826–937). |
| 9 | Out-of-scope section included | PASS | "Out of Scope" section (lines 1026–1069) enumerates 9 deliberate exclusions: in-tree async, webhooks, durable retry, federation, threaded hooks, third-party plugins, rotation, emit-time validation, dry-run. |
| 10 | Spec references and aligns with prior art in `.openstation/docs/events.md` and `.openstation/docs/hooks.md` | PASS | Both docs exist (`.openstation/docs/events.md` 6051B, `hooks.md` 11366B) and are listed in Cross-References (lines 1085–1088). Problem section (lines 42–46) explicitly cites the OpenStation events/hooks split as prior art; C4 (line 437) mirrors OpenStation's hook loader; `ART_` env namespace parallels `OS_`. |

### Summary

10 passed, 0 failed. All verification criteria satisfied — the spec
is comprehensive, internally consistent with v2 design decisions,
and aligned with both the OpenStation prior art and the existing
`s0004`/`log/` boundary.

## Progress

- 2026-05-07: Authored `s0025-artifact-events` (905 lines) covering
  always-on event stream + opt-in subscriber layer. Folded into
  `log/` per DD-1; `core` dispatches via registered emitters in a
  new `core/events.py` to respect the DAG. YAML-only subscribers
  (DD-2), opt-in pre-phase blocking (DD-3), closed event catalog
  (DD-4). Three worked examples cover agent, user, and external-app
  audiences. Reconciled with `s0004` (extends, not replaces) and
  out-of-scope section drawn for follow-up implementation task.
- 2026-05-10: Bumped `s0025` to `version: 2` after design review.
  Five revisions: (1) **module split inverted** — DD-1 now picks
  three sibling modules (`events/`, `hooks/`, `log/` unchanged
  from `s0004`) over the v1 fold-into-log decision; (2)
  **renamed throughout** — "subscribers" → "hooks" matching
  OpenStation vocabulary, yaml key `subscribers:` → `hooks:`,
  audit events `subscriber.fired/failed` → `hook.fired/failed`,
  exception `BlockedByPreSubscriber` → `BlockedByPreHook`; (3)
  **new derived event** `artifact.status_changed` fires alongside
  `artifact.updated` whenever `status` is in `changed` (I6),
  giving hook authors a simpler matcher form; (4) **async
  delegated** — new DD-5 makes async execution explicitly
  out-of-tree, integrated via a catch-all hook to an external
  runtime (Audience 4 worked example added); (5) **Out of Scope
  rewritten** to spell out the async-via-hook delegation pattern.
  `s0004`'s `log/` scope is now untouched by this work.

## Findings

Produced `s0025-artifact-events` (v2) — a feature spec covering a
two-layer reactive surface for `artifacts-os`:

- **Always-on event stream** — JSONL daily files at
  `artifacts/logs/events/YYYY-MM-DD.jsonl`, written by every
  `store.create` / `store.update` call. Owned by a new
  `events/` module.
- **Opt-in hook layer** — declarative reactions configured in
  `artifacts.yaml` under a top-level `hooks:` key. Owned by a
  new `hooks/` module.

### Key Design Decisions

- **DD-1 — Three sibling modules** (`events/`, `hooks/`,
  `log/` unchanged from `s0004`). Each module owns one concept;
  audit-stream tail commands point at `events/`, hook authoring
  docs point at `hooks/`, and `s0004`'s Logger/LogReader scope
  stays exactly as specified. (v1 had folded both into `log/`;
  v2 inverted that choice — see DD-1 trade-off table.)
- **DD-2 — YAML-only hooks**. Compared against
  YAML + Python entry points; YAML wins on audit, sandbox, and
  install simplicity. Power users compose via shell.
- **DD-3 — Pre-phase blocking is opt-in**. Library invariant
  (emit must not break CRUD) preserved by default; explicit
  `blocking: true` opts into the gate-keeping use case.
- **DD-4 — Closed event catalog**. Adding event types requires
  spec revision; gives external apps a stable wire contract.
- **DD-5 — Async execution delegated to external modules**.
  `artifacts-os` ships only synchronous, in-process hooks; async
  fan-out (queues, retries, DLQ, worker pools) integrates via a
  catch-all hook to an external runtime that owns its own
  substrate.

### DAG Reconciliation

`core` cannot import outward (DAG violation). The dispatch goes
*outward* via a registration callable in a new
`core/events.py`: `register_emitter(fn)` + `_dispatch(event,
**payload)` that swallows every emitter exception. `events/`
registers `stream.append` and `hooks/` registers `notify` on
import. `core` adds zero new dependencies and works fine
without `events/` or `hooks/` imported.

DAG: `core → {events, log} → hooks → ai`; `log/` is left
exactly as `s0004` specifies (its scope is preserved verbatim
by v2).

### Event Catalog (closed in v2)

`artifact.created`, `artifact.updated`,
`artifact.status_changed` (derived from `artifact.updated`
when `status` is in `changed`), `artifact.validated`,
`hook.fired`, `hook.failed`. Each has a documented JSON schema
with universal `ts` + `event` fields plus event-specific
payload. Deliberately omits `artifact.deleted` (no delete
operation exists yet).

### Hook Action Types

`shell` (subprocess), `notify` (cross-platform desktop with
terminal-bell fallback), `file-drop` (write payload to
templated path). Action registry is structured for in-tree
extension; third-party plugins are out of scope for v1.

### Worked Examples

Four end-to-end examples — architect agent self-assigning
spec-typed tasks; user receiving desktop notifications + bells
on review-ready tasks (using the simpler
`artifact.status_changed` matcher); external dashboard tailing
the JSONL stream with `tail -F | jq` or
`artifacts events tail --follow`; and a catch-all hook
handing every event to an external async runtime that owns its
own queue and worker pool.

### Relationship to `s0004` and the `log/` stub

This spec **does not modify** `s0004`'s `log/` scope.
`Logger` / `LogReader` API and the operational log surface
remain exactly as specified. The events surface lives in a
separate new `events/` module; the reactive layer lives in
`hooks/`. (v1 had extended `s0004` by growing `log/`; v2
leaves `log/` alone.) The implementing task should bump `s0004`
to `version: 2`, mark `status: final`, and add a "Superseded
sections" cross-reference pointer to the event-type table only.

### Out of Scope (made explicit)

In-tree async / queued execution (delegated via catch-all hook
to external runtime per DD-5), remote / webhook delivery,
durable retry, threaded hooks, cross-vault federation,
third-party action plugins, daily-file rotation, emit-time
payload validation, dry-run mode. Each is listed with rationale
so a follow-up task has a clean boundary.

### Build Sequence

Nine independently-testable steps from C2 dispatcher → C7 core
integration → C1+C3 catalog/stream → C8 CLI → C6 settings → C5
actions → C4 hook loader → audit-trail events → end-to-end
verification harness (now covering all four worked-example
audiences).

## Downstream

- **Implementation task** — pick up the build sequence in
  `s0025` § "Build Sequence". Likely a feature-typed parent
  task with sub-tasks per build step. Adds two new module
  dirs (`src/artifacts_os/events/`,
  `src/artifacts_os/hooks/`) and leaves `src/artifacts_os/log/`
  untouched.
- **`s0004` revision** — bump to `version: 2`, mark `final`,
  add cross-reference pointer to `s0025` for the event-type
  schemas only (Logger/LogReader API is unchanged). Could be
  folded into the implementation task or done first as a
  docs-typed task.
- **`log/__init__.py` docstring update** — update spec
  references (`s2061` → `s0005`, `s2063` → `s0004`). Note
  that `s0025` is *not* a `log/` reference under v2 — the
  events surface lives in a separate `events/` module. Small
  docs follow-up.
- **`docs/architecture.md`** — once implemented, add two new
  rows to the Module Map: `events` ("event catalog + always-on
  audit stream") and `hooks` ("opt-in declarative reactions").
  The `log` row stays as-is.
- **`docs/settings.md`** — needs an `events:` section once
  `EventsSettings.from_base` ships, and a `hooks:` section
  once `HooksSettings.from_base` ships.
- **`artifact.deleted` event type** — add to the catalog when
  delete operation lands in `core/store.py`.
