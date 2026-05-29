---
kind: task
id: t0186
name: add-declarative-per-property-state
type: feature
status: done
assignee: 
owner: user
created: 2026-05-24
subtasks:
  - "[[t0187-spec-declarative-per-property-state]]"
  - "[[t0188-research-property-change-event-design]]"
  - "[[t0190-implement-per-property-state-machine]]"
  - "[[t0191-migrate-task-kind-json-and]]"
artifacts:
  - "[[openstation/specs/s0033-declarative-per-property-state-machines]]"
completed: 2026-05-29
---

# Add Declarative Per-Property State Machines To Kind.Json

# Declarative per-property state machines in `kind.json`

## User story

> **As an artifact kind author, I want to declare a property-level state machine — `enum` + `initial` + `transitions` — in `kind.json` so that the substrate validates legal starting values and legal `(from, to)` transitions at write time, without requiring a higher-layer harness (like openstation) to enforce workflow rules in-house.**

## Why

- **Audit recommendation reversal in scope.** `[[r0001-openstation-integration-audit]]` §3.1 currently keeps **all** lifecycle logic on the openstation side, on the premise that `artifacts-os` is a substrate and `KindDef.statuses` is "just a list — no notion of legal transitions". A targeted carve-out is now warranted: *declarative* legality (membership + transitions) belongs in the substrate because it is generic over both kind and property. *Relational* legality (subtask blocking, `depends_on`, ownership, checklist parsing) still stays in openstation. The CLAUDE.md rule "No lifecycle logic in `cli`" remains literally true — the logic lives in `core/store.py`, not `cli/`.
- **The mechanism is truly generic.** `status` is not special. Any enum-typed property — `priority`, `severity`, `phase`, `owner` — can carry its own independent state machine. Multiple state machines per artifact, validated uniformly.
- **Today's substrate validates value membership but not transitions.** `core.store.update` checks `status ∈ kd.statuses` (`src/artifacts_os/core/store.py:254`) and `core.validate` Rule 3 mirrors it. Neither knows about `(from, to)`. openstation re-implements `TRANSITIONS`, `VALID_TRANSITIONS`, `_STATUS_RANK`, `_MIN_PARENT_STATUS` in `src/openstation/core/lifecycle.py`. Every workflow-shaped consumer would otherwise re-invent the same primitive.
- **Composable with the events + hooks substrate already shipped.** Subscribers can still observe transitions via `artifact.updated` (carries `changed`/`before`/`after`) and `artifact.status_changed`. No new events; the catalogue stays closed per `[[s0025-artifact-events]]` §C2.
- **Backward-compatible.** Properties without `transitions:` keep today's "any enum value is fine" behaviour. No migration required for existing kinds.

## Directions

Intent, not contract — the architect spec sub-task settles the precise schema and validator semantics.

- **Property-level declaration.** `transitions:` and `initial:` are siblings of `enum:` inside the property definition. `enum` is the universe of legal values; `initial` is the legal value at creation; `transitions:` is the edge map. Example (intent only):

  ```json
  "status": {
    "enum": ["backlog", "ready", "in-progress", "review", "verified", "done", "rejected"],
    "initial": "backlog",
    "transitions": {
      "backlog":     ["ready", "rejected"],
      "ready":       ["in-progress", "backlog"],
      "in-progress": ["review", "ready", "failed"],
      "review":      ["in-progress", "verified"],
      "verified":    ["done"],
      "*":           ["rejected"]
    }
  }
  ```

- **`enum` validates `transitions:`.** At schema load (kind registration), the validator cross-checks: every key of `transitions:` except the wildcard `*` must be in `enum`; every value in every right-hand-side list must be in `enum`; `initial` must be in `enum`. Drift is caught at load, not at write.

- **Wildcard `*` for "from any state".** Useful for emergency-abort paths (`rejected`, `cancelled`) without duplicating the destination across every from-state's edge list.

- **Validation at write time.**
  - `create`: when the property is set, its value must equal `initial` (or be `initial` by default if the field is omitted — see open questions).
  - `update`: when the property changes, the new value must be in `enum` (existing rule) **and** in `transitions[current] ∪ transitions["*"]` (new rule). Properties without `transitions:` skip the second check.

- **Error shape.** Reuse `ValidationError`. Message names the property and lists allowed targets: `"Illegal transition 'verified' for field 'status' from 'in-progress' — allowed: review"`.

- **No cross-property guards.** "Can't move `status` while `priority: critical`" is a relational rule and stays out of scope — openstation continues to express that via a `host: openstation` pre-phase blocking hook.

- **Audit follow-up.** Once shipped, `[[r0001-openstation-integration-audit]]` §3.1 and §6 need a one-paragraph update: the substrate-vs-harness boundary moves one notch — *declared* legality lives in core, *relational* legality stays in the harness.

## Open questions

For the architect spec sub-task to settle:

- **Initial state semantics.** Does `initial` mean "default if the field is omitted at create" or "the only legal value at create (must be set explicitly to `initial` or left out)"? Both are coherent; the latter is a stricter state machine, the former is more permissive for callers that bulk-import data. Recommend stricter for v1.

- **Wildcard interaction with `initial`.** Should `transitions["*"]` be reachable *from creation* too, or only after the first update? Recommend "only after first update" — otherwise `initial` is meaningless.

- **Property type scope for v1.** Recommend enum-only. Numeric ladders (`1: [2, 0]`) and booleans are syntactically expressible but add edge cases; defer.

- **Empty `transitions:` semantics.** Is `"transitions": {}` legal? If yes, what does it mean — "no transitions allowed, terminal-at-creation"? Recommend: legal, means the field is locked at `initial` and can never change. Could be useful for immutable-after-creation fields (`kind`, `id`).

- **Schema vendor keyword.** Use bare `transitions:` / `initial:` or namespace as `x-transitions:` / `x-initial:` for JSON Schema cleanliness? Current kind schemas already use bare keys (`statuses`, `prefix`, `numbered`) per `[[t0142-drop-legacy-flat-kind-schema]]`. Recommend: bare, for consistency.

- **Validator surface.** Does this go in `core.validate` (Rule N) or `core.store.update` (alongside the existing `status not in kd.statuses` check) or both? Today's check lives in both `validate.py:110` and `store.py:254` — same pattern likely applies.

- **`KindDef` shape.** Today `KindDef.statuses` is a flat `list[str]`. Does the per-property state machine need a new dataclass on `KindDef` (e.g. `KindDef.state_machines: dict[str, StateMachine]`), or is parsing kept inside `validate`/`store` against the raw JSON schema? Affects the public API surface.

## Sub-tasks

- Spawn an `architect` spec sub-task to settle the schema shape (`enum` / `initial` / `transitions` / wildcard), the validator semantics (load-time cross-check, write-time check), the `KindDef` surface change (if any), and the open questions above. Spec ID and slug TBD by the architect.

## Verification

- A new kind declaring `enum + initial + transitions` on any property (not necessarily `status`) loads cleanly via `Registry`.
- A `transitions:` table that references a value not in `enum` fails at schema load with a clear error pointing at the offending key or RHS value.
- `artifacts create --kind <new-kind> --fields foo=<illegal-initial>` fails with a message naming the field and the legal `initial` value.
- `artifacts update <ref> --status <illegal-target>` (or equivalent for an arbitrary property) fails with a message naming the field, the current value, and the legal targets.
- An update from `A` to `B` where `B ∈ transitions["*"]` succeeds even though `B ∉ transitions[A]`.
- A property without a `transitions:` block still accepts any value in `enum` — no regression for existing `task`, `agent`, `note`, `research`, `spec`, `hook` kinds.
- `artifact.updated` and `artifact.status_changed` events fire as today; no new event types added.
- `docs/adding-a-kind.md` (and the relevant module README under `src/artifacts_os/core/`) document the property shape with a worked example.
