---
kind: task
id: t0135
name: implement-artifact-events-and-hooks
type: implementation
status: done
assignee: developer
owner: user
parent: "[[t0136-artifact-event-and-hook-system]]"
created: 2026-05-10
started: 2026-05-10
completed: 2026-05-10
---

# Implement Artifact Events And Hooks Per S0025

# Implement: Artifact Events + Hooks

Implement the two-layer reactive surface defined in
[[s0025-artifact-events]] (v2). Read the spec end-to-end first;
this task is its build-sequence follow-through.

## Summary

Two new sibling modules under `core/` plus a small dispatch shim:

| Path | Owns |
|------|------|
| `src/artifacts_os/core/events.py` | Registration table + non-throwing `_dispatch` / `_dispatch_pre` (DAG glue) |
| `src/artifacts_os/core/errors.py` (modified) | New exception `BlockedByPreHook(ArtifactError)` |
| `src/artifacts_os/events/` | Event catalog (payload dataclasses, type constants), JSONL audit stream writer, settings extension |
| `src/artifacts_os/hooks/` | Hook loader, matcher engine, action runners (`shell`, `notify`, `file-drop`), settings extension |
| `src/artifacts_os/cli/commands/events.py` | `artifacts events tail [--since DATE] [--event TYPE] [--follow]` |

`src/artifacts_os/log/` is **untouched** by this work — `s0004`'s
`Logger` / `LogReader` API is unchanged. Only a `version: 2` bump
+ "Superseded sections" cross-reference pointer to the event-type
table in `s0025`.

## Build Sequence

Each step is independently testable. Land each as its own commit
(or sub-task) in this order — the spec's § "Build Sequence"
section is the canonical source.

- [ ] **Step 1 — C2 dispatcher.** `core/events.py` with
      `register_emitter`, `unregister_emitter`, `_dispatch`,
      `_dispatch_pre`. Add `BlockedByPreHook` to `core/errors.py`.
- [ ] **Step 2 — C7 core integration.** Wire `_dispatch` calls
      into `store.create` and `store.update`. Add the
      `artifact.status_changed` derivative dispatch when
      `status` is in `changed`. Tests must pass with no
      registered emitters (zero behaviour change).
- [ ] **Step 3 — C1 catalog + C3 stream.** `events/catalog.py`
      (payload dataclasses + type constants) and
      `events/stream.py` (JSONL writer). Auto-register
      `stream.append` from `events/__init__.py`. Verify the
      daily JSONL file is created on first event.
- [ ] **Step 4 — C8 CLI tail.** `cli/commands/events.py`
      implementing `artifacts events tail` with `--since`,
      `--event`, `--follow` flags. Confirms the stream is
      reachable end-to-end.
- [ ] **Step 5 — C6 settings extensions.** `EventsSettings`
      (`events:` yaml key) and `HooksSettings` (`hooks:` yaml
      key), each with `from_base` per the established extension
      pattern in `docs/settings.md`.
- [ ] **Step 6 — C5 actions.** `hooks/actions.py` implementing
      `shell`, `notify`, `file-drop`. Each must have
      platform-fallback tests (notify falls back to terminal
      bell when no notification daemon present).
- [ ] **Step 7 — C4 hook loader.** `hooks/loader.py` parsing,
      matching, dispatch. Auto-register `notify` from
      `hooks/__init__.py` via `core.events.register_emitter`.
- [ ] **Step 8 — Audit-trail events.** Emit `hook.fired` /
      `hook.failed` from C4 after each hook execution.
- [ ] **Step 9 — Verification harness.** Four end-to-end tests
      covering the worked-example audiences in `s0025`:
      agent self-assigning, user CLI hook, external app tailing
      the stream, and external async runtime via catch-all hook.

## Constraints

- **DAG.** `core` imports nothing from `events/`, `hooks/`, or
  `log/`. The dispatch shim in `core/events.py` is the only
  thing `core/store.py` calls; it knows zero specific event
  types. Verified by `ast`-walking `core/*.py` (V3 in spec).
- **Non-blocking by default.** A failed emitter never propagates
  out of `_dispatch` (I1). Only `_dispatch_pre` re-raises
  `BlockedByPreHook`, and that exception is only raised when a
  hook explicitly opts in via `blocking: true` (I4).
- **Stdlib only** in `events/stream.py` and `core/events.py`.
  Hooks may use `subprocess` for `shell` / `notify` actions.
- **Closed event catalog.** `_dispatch` accepts any event string,
  but only the six events in `s0025` § C1 are documented and
  tested. Adding a new event type requires a spec revision.
- **`artifact.status_changed` invariant (I6).** Fires only as a
  derivative of `artifact.updated` when `status` is in
  `changed`. Must never fire alone.

## Verification

The full criteria table is in `s0025` § Verification (V1–V16).
Key acceptance signals:

- [x] V3 — `core` does not import outward (ast-walk test).
- [x] V10 — `store.create` / `store.update` succeed with no
      hooks configured, with zero overhead beyond no-op
      `_dispatch` calls.
- [x] V11 — Pre-phase hook with `blocking: true` exiting
      non-zero aborts the CRUD operation and leaves the file
      unchanged.
- [x] V12 — Pre-phase hook with `blocking: false` exiting
      non-zero prints a warning, fires `hook.failed`, and the
      CRUD operation still completes.
- [x] V13 — Post-phase hook exiting non-zero never affects the
      CRUD outcome.
- [x] V14 — `artifact.status_changed` dispatched immediately
      after `artifact.updated` whenever `status` is in
      `changed`, and never otherwise (I6).
- [x] V16 — All four worked examples (agent, user, app, async
      runtime) run end-to-end against a test vault.

## Verification Report

*Verified: 2026-05-10*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | V3 — `core` does not import outward | PASS | `tests/events/test_dispatcher.py::test_core_does_not_import_outward` AST-walks `src/artifacts_os/core/*.py` against `artifacts_os.{events,hooks,log}` prefixes; passes. `core/store.py` only imports `from artifacts_os.core import events as _events`. |
| 2 | V10 — CRUD succeeds with no emitters / no hooks configured | PASS | `tests/events/test_store_integration.py::test_create_succeeds_no_emitters` and `test_update_succeeds_no_emitters` pass; `core/events.py::_dispatch` returns immediately when `_emitters` is empty (`for fn in list(_emitters)` over empty list). |
| 3 | V11 — `blocking: true` pre-hook aborts CRUD, file unchanged | PASS | `tests/events/test_store_integration.py::test_pre_blocking_hook_aborts_create` confirms no file is left in tasks dir; `test_pre_blocking_hook_aborts_update` confirms status remains `backlog`. `core/store.py:152-155` cleans up reserved fd + `path.unlink(missing_ok=True)` on `BlockedByPreHook`. `tests/hooks/test_loader.py::test_hook_failed_blocking_pre_raises` exercises the blocking-pre hook path through the loader. |
| 4 | V12 — non-blocking pre-hook warns + fires `hook.failed` + CRUD completes | PASS | `tests/events/test_store_integration.py::test_pre_non_blocking_hook_warns_and_crud_completes` confirms CRUD succeeds and stderr `warning` is written. `tests/hooks/test_loader.py::test_hook_failed_event_emitted_non_blocking` confirms `hook.failed` is dispatched when a non-blocking hook action raises. `hooks/loader.py:328-347` fires `hook.failed` then warns instead of raising when `phase != "pre"` or `blocking` is False. |
| 5 | V13 — post-phase hook failure does not affect CRUD | PASS | `tests/events/test_store_integration.py::test_post_hook_failure_does_not_affect_crud` passes (`a.id == "t0001"` despite emitter raising). `core/events.py::_dispatch` swallows all exceptions per invariant I1. |
| 6 | V14 — `artifact.status_changed` fires only after `artifact.updated` when status changed | PASS | `tests/events/test_store_integration.py::test_update_dispatches_status_changed_when_status_in_changed` asserts ordering (`idx_changed > idx_updated`); `test_update_does_not_dispatch_status_changed_when_status_not_changed` asserts the event is absent when `status` is not in `changed`. `core/store.py:271-282` dispatches the event only inside the `if "status" in changed_keys` branch, immediately after the `artifact.updated` dispatch. |
| 7 | V16 — four worked-example audiences run end-to-end | PASS | `tests/events/test_e2e.py` covers Audience 1 (agent self-assign via file-drop hook), Audience 2 (user CLI hook on `artifact.status_changed`), Audience 3 (external app tails JSONL stream — verifies `artifact.created`/`updated`/`status_changed` records with `ts` + `event` keys), and Audience 4 (catch-all `event: "*"` hook receives ≥3 artifact events). All tests pass. |

### Summary

7 passed, 0 failed. All verification criteria are backed by passing
tests in `tests/events/` and `tests/hooks/` (81 tests, all green).
The full test suite excluding the pre-existing release-changelog
skill failure (unrelated to this work) is green: 225 passed, 1
skipped across `tests/events`, `tests/hooks`, and `tests/core`.

## Documentation Follow-Through

- [ ] Bump `s0004-artifacts-os-log-module` to `version: 2`,
      mark `status: final`, add "Superseded sections"
      cross-reference pointer to `s0025` § C1 for the
      event-type table only. Logger/LogReader API untouched.
- [ ] Update `docs/architecture.md` Module Map: add `events`
      ("event catalog + always-on audit stream") and `hooks`
      ("opt-in declarative reactions") rows. The `log` row
      stays as-is.
- [ ] Update `docs/settings.md` with `events:` and `hooks:`
      sections matching `EventsSettings` / `HooksSettings`.
- [ ] Update `log/__init__.py` docstring spec references
      (`s2061` → `s0005`, `s2063` → `s0004`). Note that
      `s0025` is **not** a `log/` reference — events live in
      `events/`.

## Out of Scope

Per `s0025` § Out of Scope — explicitly **not** included in this
task:

- In-tree async / queued execution (delegated via catch-all
  hook to external runtime per DD-5).
- Remote / webhook delivery.
- Durable retry semantics.
- Threaded hooks.
- Cross-vault event federation.
- Third-party action plugins (registry is structured for them
  but loading model is not specified).
- Event stream rotation / compaction.
- Hook dry-run / test mode.
- The `artifact.deleted` event (no delete operation exists yet
  in `core/store.py`).

## References

- [[s0025-artifact-events]] — design spec (v2).
- [[s0004-artifacts-os-log-module]] — Logger/LogReader API,
  unchanged by this work; gets `version: 2` cross-ref bump.
- [[s0005-artifacts-os-module-system]] — module DAG, into
  which this work adds `events/` and `hooks/`.
- [[s0010-core-settings-module-spec]] — `Settings` extension
  pattern used by `EventsSettings` / `HooksSettings`.
- [[s0023-multi-value-filters]] — list-as-OR matcher semantics.
- [[t0130-spec-for-artifact-events-with]] — parent (architect
  spec task that produced `s0025`).
