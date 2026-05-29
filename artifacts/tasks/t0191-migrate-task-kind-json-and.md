---
assignee: developer
created: 2026-05-25
depends_on:
- '[[t0190-implement-per-property-state-machine]]'
id: t0191
kind: task
name: migrate-task-kind-json-and
owner: user
parent: '[[t0186-add-declarative-per-property-state]]'
started: 2026-05-26
status: done
type: feature
completed: 2026-05-29
---

# Migrate Task/Kind.Json And Document Property State Machines

# Migrate `task/kind.json` and document property state machines

## User story

> **As a kind author opening `docs/adding-a-kind.md` after [[t0186-add-declarative-per-property-state]] ships, I want a worked example of a property state machine in the canonical `task` kind and a documented "Property-Level State Machines" subsection, so that I can add `transitions:` to my own kind without reading the spec.**

## Why

The substrate task ships the machinery; this task exercises and documents it. Per spec [[s0033-declarative-per-property-state-machines]] D218 / D219:

- Without an in-vault example, the contract has no end-to-end exercise and the docs have nothing concrete to reference.
- `task/kind.json` is the canonical, most-referenced kind — adding a permissive `transitions:` table there proves the substrate end-to-end without changing observable behaviour for openstation tasks.
- Co-located doc updates are the project's existing rule per `CLAUDE.md` ("Doc updates accompany API changes").

A *restrictive* transitions table for `task/kind.json` (e.g. `done` terminal, `verified → done` only) is explicitly out of scope — it requires alignment with openstation's existing `_STATUS_RANK` / `VALID_TRANSITIONS` and a separate behavioural review. Tracked as a future follow-up.

## Directions

Intent — every shape locked in spec §2 and §9.

### `task/kind.json` migration (D218, spec §2.1)

Add `initial:` and `transitions:` to the `status` property. The transitions table is **fully permissive** — every current status can transition to every other current status, including itself. Exact shape per spec §2.1:

```jsonc
"status": {
  "enum": ["backlog", "ready", "in-progress", "review", "verified", "done", "cancelled", "rejected"],
  "initial": "backlog",
  "transitions": {
    "backlog":     ["backlog", "ready", "in-progress", "review", "verified", "done", "cancelled", "rejected"],
    "ready":       ["backlog", "ready", "in-progress", "review", "verified", "done", "cancelled", "rejected"],
    "in-progress": ["backlog", "ready", "in-progress", "review", "verified", "done", "cancelled", "rejected"],
    "review":      ["backlog", "ready", "in-progress", "review", "verified", "done", "cancelled", "rejected"],
    "verified":    ["backlog", "ready", "in-progress", "review", "verified", "done", "cancelled", "rejected"],
    "done":        ["backlog", "ready", "in-progress", "review", "verified", "done", "cancelled", "rejected"],
    "cancelled":   ["backlog", "ready", "in-progress", "review", "verified", "done", "cancelled", "rejected"],
    "rejected":    ["backlog", "ready", "in-progress", "review", "verified", "done", "cancelled", "rejected"]
  },
  "description": "Task lifecycle stage."
}
```

This is intentionally a no-op behaviourally — any current movement openstation makes on a task remains legal. The point is to exercise the substrate code paths and give docs something to point at.

### `docs/adding-a-kind.md` update (D219)

New top-level subsection "Property-Level State Machines" covering:

1. **What it is** — one paragraph: any enum-typed property may declare a state machine via `enum + initial + transitions` siblings inside the property definition.
2. **Minimal example** — a small fictional kind (e.g. `ticket` with a `priority` property) showing the three keywords, an `initial`, two explicit transitions, and a `*` wildcard.
3. **The wildcard `*`** — source-only, additive, not reachable from creation. One-sentence each.
4. **Backward compatibility** — properties with `enum` but no `transitions:` keep today's "any enum value transitions to any other" semantics (D206).
5. **Empty `transitions: {}`** — locks the field at `initial` (D207). Useful for immutable-after-creation properties.
6. **Worked example pointer** — link to `task/kind.json` as the in-vault reference.

Do not duplicate the spec — the doc is a tutorial, the spec is the contract. If a reader needs decisions, they go to s0033.

### `src/artifacts_os/core/README.md` update (D219)

- **Models table** — add `StateMachineDef` row alongside `Artifact`, `ArtifactMeta`, `KindDef`. One-line description.
- **KindDef table** — add `state_machines: dict[str, StateMachineDef]` field with a one-line description.
- **New subsection "Per-Property State Machines"** — short (≤ 20 lines):
  - One paragraph on what `state_machines` contains.
  - Pointer to `docs/adding-a-kind.md` for authoring.
  - Pointer to `s0033-declarative-per-property-state-machines` for the contract.
  - Import line: `from artifacts_os.core import StateMachineDef`.

### Tests

- `tests/core/test_kind_resolution.py` (or wherever the canonical `task` kind is exercised): assert `kd.state_machines["status"].initial == "backlog"` and `kd.state_machines["status"].transitions` is non-empty.
- Smoke test: `artifacts create --kind task "test"` defaults `status` to `backlog`; an existing openstation lifecycle move (e.g. `backlog → ready`) still succeeds end-to-end.

### Files touched

| File | Change |
|---|---|
| `src/artifacts_os/core/kinds/task/kind.json` | Add `initial:` + permissive `transitions:` to `status` property. |
| `docs/adding-a-kind.md` | New "Property-Level State Machines" subsection. |
| `src/artifacts_os/core/README.md` | Models table + KindDef table + new short subsection. |
| `tests/core/test_kind_resolution.py` (or peer) | Assertions on `task` kind's `state_machines`. |

### Out of scope

- A *restrictive* `task/kind.json` transitions table — separate follow-up (see Downstream).
- Migrating other kinds (`note`, `research`, `spec`, `hook`, `agent`) — they keep today's no-state-machine behaviour per D206.
- The `r0001-openstation-integration-audit` §3.1 / §6 boundary-line edit (D224) — tracked separately under [[t0185-refresh-r0001-openstation-integration-audit]] or a new task.

## Open questions

None. Doc copy is the author's call; the structure is locked.

## Sub-tasks

None.

## Verification

- [x] `src/artifacts_os/core/kinds/task/kind.json` contains the permissive `transitions:` table matching spec §2.1 exactly.
- [x] `artifacts create --kind task "smoke"` succeeds and the new task has `status: backlog`.
- [x] Every existing openstation status transition (`backlog → ready`, `ready → in-progress`, `in-progress → review`, `review → verified`, `verified → done`, `* → cancelled`, `* → rejected`) succeeds against the new `task/kind.json` — no behavioural regression.
- [x] `docs/adding-a-kind.md` has a "Property-Level State Machines" subsection covering the six points listed in §Directions.
- [x] `src/artifacts_os/core/README.md` lists `StateMachineDef` in the Models table, `state_machines` in the KindDef table, and has a short "Per-Property State Machines" subsection.
- [x] An operator can copy-paste the doc example into a new kind and have it work without reading s0033.
- [x] `from artifacts_os.core import StateMachineDef` import appears in the docs and resolves at runtime.

## Verification Report

*Verified: 2026-05-29*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `task/kind.json` permissive `transitions:` matches spec §2.1 exactly | PASS | `artifacts/kinds/task/kind.json` lines 47–61 — eight enum values + `initial: "backlog"` + 8×8 transitions table byte-identical to spec §2.1 (lines 66–82 of `s0033-declarative-per-property-state-machines.md`). |
| 2 | `artifacts create --kind task "smoke"` defaults to `status: backlog` | PASS | `tests/core/test_registry.py::test_task_kind_create_defaults_to_backlog` exercises `core.create` against the vault task kind and asserts `frontmatter["status"] == "backlog"` — passes. |
| 3 | All openstation transitions succeed against the new `task/kind.json` | PASS | `tests/core/test_registry.py::test_task_kind_lifecycle_transitions_succeed` walks the full forward chain `backlog → ready → in-progress → review → verified → done` plus `* → cancelled` and `* → rejected` — passes. |
| 4 | `docs/adding-a-kind.md` has "Property-Level State Machines" subsection covering all six points | PASS | `docs/adding-a-kind.md` line 310 onwards — covers (1) what it is, (2) `ticket/priority` minimal example with `*` wildcard, (3) wildcard source-only/additive semantics, (4) D206 backward compatibility, (5) D207 empty-transitions lock, (6) pointer to `artifacts/kinds/task/kind.json`. |
| 5 | `core/README.md` lists `StateMachineDef` in Models table + documents `state_machines` field + has Per-Property State Machines subsection | PASS | `src/artifacts_os/core/README.md` line 40 (Models table row for `StateMachineDef`), line 39 (`KindDef` row mentions per-property state machines), lines 46–78 (Per-Property State Machines subsection documenting `KindDef.state_machines: dict[str, StateMachineDef]` and the dataclass shape). |
| 6 | Doc example is copy-paste-runnable without reading s0033 | PASS | `docs/adding-a-kind.md` lines 323–334 provide a self-contained `ticket.priority` JSON block; surrounding prose explains `initial`, `transitions`, wildcard, backward compat and locked-field semantics inline. No cross-spec lookup required. |
| 7 | `from artifacts_os.core import StateMachineDef` appears in docs and resolves at runtime | PASS | Import line at `src/artifacts_os/core/README.md` line 27 (`Artifact, ArtifactMeta, KindDef, StateMachineDef`); runtime check `python -c "from artifacts_os.core import StateMachineDef"` resolves to `<class 'artifacts_os.core.models.StateMachineDef'>`. |

### Summary

7 passed, 0 failed. All verification criteria satisfied; transitioning to `verified`.

## Findings

`task/kind.json` was already migrated by the substrate task (t0190) — it
already carried `initial: "backlog"` and the fully permissive
`transitions:` table matching spec §2.1 exactly, so no changes were needed
there.

Added to `tests/core/test_registry.py`:
- `test_task_kind_status_state_machine` — parses the vault's `task/kind.json`
  via `parse_state_machines` and asserts `initial == "backlog"` + eight fully
  permissive transition rows.
- `test_task_kind_create_defaults_to_backlog` — smoke: `core.create` with the
  vault task kind injects `status: "backlog"`.
- `test_task_kind_lifecycle_transitions_succeed` — smoke: the full openstation
  forward chain (backlog → ready → … → done) plus `* → cancelled` and
  `* → rejected` all succeed.

Added `## Property-Level State Machines` as a new top-level section in
`docs/adding-a-kind.md` (after the `## kind.json — Schema Reference`
reference section). Covers all six required points: what it is, a
`ticket/priority` minimal example with wildcard, wildcard semantics,
backward compat (D206), empty-transitions lock (D207), and a pointer to
`artifacts/kinds/task/kind.json`.

`src/artifacts_os/core/README.md` was already complete (StateMachineDef in
Models table, `state_machines` documented in the subsection, import line
present). No changes required.

1299 tests pass, 1 skipped.

## Downstream (future follow-ups, not in scope)

- **Restrictive `task/kind.json` table.** Encode openstation's real lifecycle (e.g. `done` terminal except for `cancelled`, `verified → done` only, `rejected` reachable via `*`). Requires behavioural alignment with `src/openstation/core/lifecycle.py` — separate task.
- **openstation harness consolidation.** Once `task/kind.json` ships a restrictive table, openstation's `TRANSITIONS` / `VALID_TRANSITIONS` / `_STATUS_RANK` become candidates for retirement.
- **`property:` hook-matcher key** — flagged in r0006's downstream against s0025 / s0032. Separate task.

## Depends on

- The substrate task — `task/kind.json` permissive table is meaningless until `Registry` parses it and `store` enforces it.
- [[t0186-add-declarative-per-property-state]] — parent feature.
- [[s0033-declarative-per-property-state-machines]] — settled spec.