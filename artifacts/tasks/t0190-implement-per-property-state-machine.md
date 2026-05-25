---
assignee: developer
created: 2026-05-25
id: t0190
kind: task
name: implement-per-property-state-machine
owner: user
parent: '[[t0186-add-declarative-per-property-state]]'
status: done
type: feature
completed: 2026-05-25
---

# Implement Per-Property State-Machine Substrate

# Implement per-property state-machine substrate

## User story

> **As an implementer of [[t0186-add-declarative-per-property-state]], I want the full substrate for declarative per-property state machines — schema parsing, load-time cross-check, write-time enforcement — to land in one cohesive change, so that authors who add `transitions:` to a `kind.json` immediately see both validation and enforcement working end-to-end.**

## Why

Spec [[s0033-declarative-per-property-state-machines]] locks every decision needed to implement this substrate (D201–D224). The original decomposition (D221) proposed three phases, but Phase 1 (parse + load-time check) and Phase 2 (write-time enforcement) ship as a single cohesive unit:

- Phase 1 alone populates `KindDef.state_machines` but nothing reads it — authors see no behavioural change beyond load-time error messages.
- The `transitions.py` helper is the only consumer of the parsed structure; splitting them artificially separates a producer from its sole consumer.
- No architectural decisions live at the Phase 1/2 boundary — the spec locks `StateMachineDef`'s shape (D211), the helper's location (D210), and the error format (D212).

This task delivers the substrate end-to-end. The `task/kind.json` migration and docs are tracked separately.

## Directions

Intent — every detail is locked in [[s0033-declarative-per-property-state-machines]]; cross-reference by D-row.

### Schema parsing (spec §2, §3)

- Add `StateMachineDef` frozen dataclass to `src/artifacts_os/core/models.py`. Shape per D211: `enum: list[str]`, `initial: str | None`, `transitions: dict[str, list[str]] | None`.
- Add `state_machines: dict[str, StateMachineDef]` field to `KindDef`. Empty dict when no property declares a state machine.
- Re-export `StateMachineDef` from `core/__init__.py`.
- Populate `KindDef.state_machines` in `Registry._load_vault_kinds` by scanning each property's JSON Schema for `enum` + `initial` + `transitions` keys (D201, D202 — bare keywords, no `x-` prefix).
- Keep `KindDef.statuses` as the convenience alias per D211.

### Load-time cross-check (spec §4, D208, D214, D215)

- New helper module `src/artifacts_os/core/transitions.py` owns the parse + validation logic.
- At kind registration, raise `ValidationError` (which propagates out of `Registry.__init__`) for the four drift conditions:
  - (a) `transitions:` declared without `enum:` → D214a
  - (b) a `transitions:` key (other than `*`) not in `enum` → D214b (skip `*` per D215)
  - (c) a `transitions:` RHS value not in `enum` → D214c
  - (d) `initial` not in `enum` → D214d
- Also raise (e) when `*` appears in any RHS list (D204 — wildcard is source-only).
- Error messages match D214's exact format: `"Kind '<kind>': field '<prop>' …"`.

### Write-time enforcement (spec §5, D203, D205, D207, D209, D222, D223)

- `core/transitions.py` exposes two functions consumed by `store.py`:
  - `check_create(kind_def, fields) -> dict` — for each state-machined property, enforce D203 strict-`initial`: if the property is set, it must equal `initial`; if omitted, inject `initial` (D223). Raises `ValidationError` per D213.
  - `check_transition(kind_def, current_fm, new_fm) -> None` — for each state-machined property where the value is changing, enforce `new ∈ enum ∧ new ∈ (transitions[current] ∪ transitions["*"])`. Wildcard is additive (D205). Terminal-state semantics per D222 (state in `enum` but missing from `transitions` keys → only `transitions["*"]` is reachable; if `*` also absent → field locked). Empty `transitions: {}` locks the field at `initial` (D207). Raises `ValidationError` per D212.
- Wire `check_create` into `core/store.py` `create()` before the existing schema validation.
- Wire `check_transition` into `core/store.py` `update()` — **replaces** the existing single-purpose status-membership check at `store.py:254`. The new helper covers status as a degenerate case of any state-machined property.

### Validate.py extension (D209)

- Extend Rule 3 in `src/artifacts_os/core/validate.py` (currently checks only `status ∈ kd.statuses` at line 110) so it iterates every state-machined property and reports membership violations as `ValidationIssue`s.
- `validate_one` cannot check transitions (no "before" value); membership-only is correct here.
- Reuse the same error message helpers from `core/transitions.py` so wording stays consistent across `store` and `validate`.

### Error messages (D212, D213, D214)

Exact strings locked by the spec. Surface them from a single helper in `core/transitions.py` so `store.py` and `validate.py` share the wording.

- D212 (write-time transition rejection): `"Illegal transition for field '<prop>': '<current>' → '<target>' (allowed targets: <list>; allowed from any state: <wildcard-list>)"` — omit the wildcard clause when empty.
- D213 (create-time strict-`initial` rejection): `"Illegal initial value for field '<prop>': '<value>' (must be '<initial>')"`.
- D214a–d (load-time): see spec §4 for the four exact templates.

### Tests

Mirror module structure under `tests/`. No mocking — use `tmp_path` and the `make_vault` fixture per `CLAUDE.md`.

- `tests/core/test_transitions.py` (new):
  - Load-time: each of the five drift conditions raises with the spec-mandated message.
  - `check_create`: strict `initial` enforced; omission defaults; non-state-machined property accepts any enum value (D206); empty `transitions: {}` only accepts `initial` at create.
  - `check_transition`: legal target accepted; illegal target rejected with D212 message; `*` wildcard additive; terminal state (D222); locked field (D207); property with `enum` but no `transitions:` accepts any enum value (D206); status as degenerate case.
- `tests/core/test_store.py` (extend): integration through `create` and `update` — fixtures using a test kind with a small state machine.
- `tests/core/test_validate.py` (extend): Rule 3 reports membership violations for arbitrary state-machined properties, not just `status`.
- `tests/core/test_registry.py` (extend): registry load fails with spec-mandated messages on each of the five drift conditions.

### Module placement summary

| Symbol | File |
|---|---|
| `StateMachineDef` (dataclass) | `src/artifacts_os/core/models.py` |
| `KindDef.state_machines` (field) | `src/artifacts_os/core/models.py` |
| `check_create`, `check_transition`, message helpers | `src/artifacts_os/core/transitions.py` (new) |
| Load-time parsing + cross-check | called from `src/artifacts_os/core/registry.py` |
| Write-time enforcement wires | `src/artifacts_os/core/store.py` (`create`, `update`) |
| Validate.py Rule 3 extension | `src/artifacts_os/core/validate.py` |
| Public re-export | `src/artifacts_os/core/__init__.py` |

### Out of scope (deferred)

- `task/kind.json` migration with permissive `transitions:` table — covered in the sibling docs/migration task (D218).
- `docs/adding-a-kind.md` and `src/artifacts_os/core/README.md` updates — covered in the sibling docs/migration task (D219).
- Numeric/boolean state machines (D216 — enum-only for v1).
- Cross-property guards, relational rules, auto-timestamps (D220).
- Property deletion via `update(fields={prop: None})` — rejected by spec §7.2.
- New event types (D217 — no catalogue change; existing `artifact.updated` and `artifact.status_changed` cover the observable surface).

## Open questions

None. Spec [[s0033-declarative-per-property-state-machines]] settles every contract. If the implementer hits an unresolved edge, bounce back to the spec — it's a spec bug, not an implementation judgement call.

## Sub-tasks

None proposed. The work is bounded (one new dataclass, one new module, three existing-file edits, four test files). Expected diff ~400–600 LoC including tests. If it exceeds ~700 LoC the developer may decompose at their discretion, but the natural split (read/write) was already evaluated and rejected during decomposition.

## Verification

Maps to spec §10 verification table.

- [x] A new kind declaring `enum + initial + transitions` on any property (not just `status`) loads cleanly via `Registry`.
- [x] A `transitions:` table referencing a value not in `enum` fails registry load with the D214 message naming the kind, property, and offending key/value.
- [x] A `transitions:` declared without `enum:` fails with the D214a message.
- [x] A `transitions:` RHS containing `*` fails registry load (D204 — wildcard is source-only).
- [x] `core.store.create(kind, fields={prop: <not-initial>})` on a state-machined property fails with the D213 message.
- [x] `core.store.create(kind, fields={})` on a state-machined property succeeds and the new artifact has `prop == initial` (D223 default injection).
- [x] `core.store.update(ref, fields={prop: <illegal-target>})` fails with the D212 message naming the property, current, target, and legal targets.
- [x] `core.store.update(ref, fields={prop: <wildcard-target>})` succeeds where the target is in `transitions["*"]` but not in `transitions[current]`.
- [x] A property declaring `enum` but no `transitions:` accepts any enum value on `create` and `update` (D206 — backward compat).
- [x] `core.validate.validate_one` reports a membership violation for every state-machined property, not only `status`.
- [x] `core.store.update` no longer contains the single-purpose `status not in kd.statuses` check — replaced by the unified `check_transition` call.
- [x] `from artifacts_os.core import StateMachineDef` imports without error.
- [x] `artifact.updated` and `artifact.status_changed` events fire as today; no new event types added (D217).
- [x] Existing tests pass — no regressions in `task`, `agent`, `note`, `research`, `spec`, `hook` kinds.
- [x] Full test coverage for the new helper module per the Tests section above.

## Verification Report

*Verified: 2026-05-25 (re-verification + targeted fix at user request)*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | New kind with `enum + initial + transitions` loads cleanly via `Registry` | PASS | `tests/core/test_registry.py::test_registry_state_machine_loads_cleanly` and `::test_registry_non_status_property_state_machine` pass; `Registry._load_vault_kinds` calls `parse_state_machines` (`registry.py:224`); vault task kind loads with `state_machines["status"].initial == "backlog"`. |
| 2 | `transitions` value not in `enum` → D214c message | PASS | `test_registry_transition_target_not_in_enum_fails`; message at `transitions.py:138-141` includes kind, prop, offending target. |
| 3 | `transitions` without `enum` → D214a message | PASS | `test_registry_transitions_without_enum_fails`; message at `transitions.py:84-87`. |
| 4 | `*` in `transitions` RHS rejected at load (D204) | PASS | `test_registry_wildcard_as_destination_fails`; check at `transitions.py:129-134` with "wildcard is source-only" wording. |
| 5 | `create` with non-initial → D213 message | PASS | `test_create_rejects_non_initial_state_machine` + `test_check_create_rejects_non_initial`; message at `transitions.py:22-26`. |
| 6 | `create(fields={})` injects `initial` (D223) | PASS | `test_create_injects_initial_state_machine` shows new widget gets `status == "new"`; injection at `transitions.py:182-183`. |
| 7 | `update` illegal target → D212 message | PASS | `test_update_illegal_transition_raises_d212` + `test_check_transition_illegal_target_raises_d212`; message at `transitions.py:40-46` names prop, current, target, allowed list. |
| 8 | `update` wildcard target succeeds (D205) | PASS | `test_update_wildcard_target_accepted` (active → cancelled via `transitions["*"]`); `test_check_transition_wildcard_additive`. Logic at `transitions.py:226-228`. |
| 9 | Enum-only prop accepts any enum value (D206) | PASS | `test_check_create_enum_only_no_transitions` + `test_check_transition_enum_only_no_transitions_d206`; `check_transition` returns early when `sm.transitions is None` (`transitions.py:222-224`). |
| 10 | `validate_one` reports membership for every state-machined property, not only `status` | PASS | `test_rule3_non_status_property_invalid_value` (phase="ship" outside enum); Rule 3 iterates `kind_def.state_machines` at `validate.py:114-123`. |
| 11 | `store.update` no longer contains the single-purpose `status not in kd.statuses` check | PASS (fixed) | The legacy backward-compat block was removed from `store.update` and the parallel one from `validate.validate_one`. `grep -r "status not in.*statuses"` across `src/` returns zero hits. Test fixtures (`tests/core/conftest.py::_default_kinds`, `tests/core/test_validate.py::_registry`, `tests/cli/conftest.py::_KINDS["task"]`) updated to declare `state_machines["status"]`. The validate `--fix` path now writes `state_machines["status"].initial` (recovery target) instead of `statuses[0]`. A new `§7.5 (recovery)` semantics was added to `check_transition` so a corrupt current value gets mapped to `initial` — mirrors §7.1 first-set logic. New tests: `test_check_transition_corrupt_current_recovers_to_initial`, `test_check_transition_corrupt_current_no_initial_is_noop`. |
| 12 | `from artifacts_os.core import StateMachineDef` imports cleanly | PASS | Re-exported from `core/__init__.py` (in `__all__`) and now also from the top-level `artifacts_os/__init__.py`. |
| 13 | `artifact.updated` and `artifact.status_changed` fire; no new event types (D217) | PASS | Both `_events._dispatch("artifact.updated", …)` and `_events._dispatch("artifact.status_changed", …)` remain in `store.py`. Grep for new event types returns zero hits. |
| 14 | Existing tests pass — no regressions in `task`, `agent`, `note`, `research`, `spec`, `hook` kinds | PASS | Full suite: `1296 passed, 1 skipped` in 23.84s (was 1294 before; +2 new tests for §7.5). |
| 15 | Full test coverage for the new helper module | PASS | `tests/core/test_transitions.py` — 35 tests covering parse (5 drift conditions + D215 + edge cases), `check_create` (7 scenarios), `check_transition` (16 scenarios including legal/illegal, wildcard additive + clause/no-clause in message, terminal D222, locked D207, idempotent, enum-only D206, no-state-machine, first-set §7.1 with/without initial, corrupt-current recovery §7.5 with/without initial, status-as-degenerate-case). |

### Summary

15 passed, 0 failed. The legacy `status not in kd.statuses` fallback has been removed from both `store.update` and `validate.validate_one`. `check_transition` is now the single authority for status (and every other state-machined property) at write time. A small §7.5 (recovery) extension lets `validate --fix` repair corrupt status values cleanly.

## Depends on

- [[t0186-add-declarative-per-property-state]] — parent feature
- [[s0033-declarative-per-property-state-machines]] — settled spec (verified via [[t0187-spec-declarative-per-property-state]])