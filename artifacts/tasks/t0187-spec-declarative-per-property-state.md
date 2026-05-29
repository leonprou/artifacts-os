---
kind: task
id: t0187
name: spec-declarative-per-property-state
type: spec
status: done
assignee: architect
owner: user
parent: "[[t0186-add-declarative-per-property-state]]"
created: 2026-05-24
started: 2026-05-24
artifacts:
  - "[[openstation/specs/s0033-declarative-per-property-state-machines]]"
completed: 2026-05-29
---

# Spec Declarative Per-Property State Machines In Kind.Json

# Spec declarative per-property state machines in `kind.json`

## User story

> **As the implementer who will land `[[t0186-add-declarative-per-property-state]]`, I want a written spec that settles the schema shape, validator semantics, `KindDef` surface, and edge cases for property-level state machines, so that implementation is a mechanical translation of a contract — not a series of judgement calls.**

## Why

`[[t0186-add-declarative-per-property-state]]` is locked at user-story granularity. The contract has known unsettled edges: initial-state strictness, wildcard interaction with `initial`, validator placement, `KindDef` surface change, vendor-keyword namespacing. These are architectural decisions, not implementation details, and they have downstream consequences:

- `KindDef` shape is part of the public library API per `core/README.md`. Changing it is a versioning event.
- The validator semantics interact with `core.validate.validate_one` / `validate_many` (consumed by `cli verify`) **and** `core.store.update` (consumed by every write path). The two surfaces need to agree.
- The schema choice (`enum` + `initial` + `transitions` siblings vs. nested under a single `state_machine:` object) affects how openstation, third-party consumers, and JSON Schema tooling read kind definitions.

Without a spec, the implementer will make these calls inline and we'll re-litigate them at review.

## Directions

Intent, not contract — the architect owns the final shape. Topics the spec must settle:

- **Schema shape.** Final JSON layout for declaring a property-level state machine inside `kind.json`. The working assumption from `t0186` is three sibling keywords (`enum`, `initial`, `transitions`); confirm or revise. Address whether to namespace as `x-transitions` / `x-initial` (JSON Schema vendor-keyword convention) or keep bare keys (consistent with existing `statuses`, `prefix`, `numbered` in current kind schemas).

- **Load-time cross-check.** Define the failure mode and error message format when (a) `transitions:` is declared without `enum:`, (b) a `transitions:` key is not in `enum`, (c) a `transitions:` RHS value is not in `enum`, (d) `initial` is not in `enum`. Where does this run — `Registry.register` time? First-touch lazy validation? Confirm placement.

- **Write-time validation.**
  - On `create`: define whether `initial` is "default if omitted" or "the only legal value at create". Recommendation from `t0186` is the strict reading; spec must confirm.
  - On `update`: define the check as `new ∈ enum ∧ new ∈ (transitions[current] ∪ transitions["*"])`. Specify behaviour when `current` is not in the `transitions:` map (terminal state) — recommend: only `transitions["*"]` is reachable.
  - Specify what happens for properties that declare `enum` but no `transitions:` — must be backward-compatible (any enum value transitions to any other).

- **Wildcard `*`.** Confirm syntax, semantics, and the constraint that `*` is reachable only *after* the first update (not from creation). Address whether `*` may appear as a *destination* (recommend: no — only as a source key).

- **Validator placement.** Today the status-membership check lives in **both** `src/artifacts_os/core/validate.py:110` (Rule 3, used by `cli verify` and inspection paths) **and** `src/artifacts_os/core/store.py:254` (used by `update`). The transition check has the same dual audience. Spec must decide: same dual placement, or a single shared helper?

- **`KindDef` surface.** Decide whether `KindDef` grows a new field (e.g. `state_machines: dict[str, StateMachineDef]` keyed by property name), or whether validation is performed against the raw JSON-schema dict stashed in `KindDef.schema`. This is a public-API decision — name it explicitly in the spec.

- **Error shape.** Define the exact `ValidationError` message format for transition rejection, in the same family as today's `"Invalid status 'foo' for kind 'task'. Allowed: [...]"`. The new message must name (a) the property, (b) the current value, (c) the attempted target, (d) the legal targets (including `*` reachable targets if any).

- **Empty `transitions: {}`.** Confirm whether legal and what it means. `t0186` proposed: legal, means the field is locked at `initial` and may never change. Spec must confirm or reject — affects use cases like immutable `kind`, `id`, `created`.

- **Type scope for v1.** Confirm enum-only. Address whether the spec leaves room for future numeric/boolean transition tables or closes the door.

- **Event semantics (no new events expected).** Confirm explicitly that no event-catalogue change is required — `artifact.updated` already carries the delta, `artifact.status_changed` continues to fire for `status` specifically, and the catalogue stays closed per `[[s0025-artifact-events]]` §C2.

- **Documentation deltas.** Name the files whose docs must change in the same commit as the implementation: at minimum `docs/adding-a-kind.md`, `src/artifacts_os/core/README.md`. The spec should not write the doc copy — just list the surfaces.

- **Out of scope (state explicitly).** Cross-property guards, relational rules (subtask blocking, depends_on, ownership, checklist parse) — all remain higher-layer concerns, expressed via hooks. Spec should state this explicitly so future scope creep can be rejected by reference.

## Open questions

- **Schema-shape preference.** Three siblings (`enum`, `initial`, `transitions`) is the working assumption. The alternative is a single nested object (`state_machine: { values: [...], initial: ..., transitions: {...} }`) which is more discoverable but breaks the "enum is JSON-Schema-native" property. Architect's call.
- **`StateMachineDef` dataclass.** If `KindDef` grows a typed sub-object, what's its public shape? Consumers of `Registry.get(kind)` rely on this.
- **Migration of existing kinds.** Should `task/kind.json` ship `transitions:` for `status` as part of this work (proving the contract end-to-end), or land empty (no behavioural change for `task`) and let openstation/consumers opt in later? Recommend: ship `task/kind.json` with a permissive `transitions:` matching today's "any enum value" semantics, so the contract is exercised end-to-end without changing observable behaviour.

## Sub-tasks

None. The spec produces a `s00NN-...` artifact (numbering by `artifacts create --kind spec --task 0186`). Implementation is a follow-up task that the spec may recommend decomposing into phases (schema parse → load-time check → write-time check → docs).

## Verification

- [x] A spec artifact `s00NN-declarative-per-property-state-machines` (or similar) exists under `artifacts/specs/`, owned by `architect`, parented to `[[t0186-add-declarative-per-property-state]]`.
- [x] The spec answers every "topic the spec must settle" item in §Directions with a concrete decision (not a "TBD" or a "to be revisited").
- [x] Every open question from `t0186` is either answered or explicitly deferred with a stated reason.
- [x] The spec is reachable from `t0186` via the `artifacts:` frontmatter (added on completion).
- [x] A skim by a fresh reader can answer "what does `core.store.update` do when a `transitions:` table rejects the new value?" without reading source.

## Verification Report

*Verified: 2026-05-25*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec artifact exists under `artifacts/specs/`, owned by `architect`, parented to `[[t0186-add-declarative-per-property-state]]` | PASS | File `artifacts/specs/s0033-declarative-per-property-state-machines.md` exists; frontmatter has `agent: architect` and `task: "[[t0186-add-declarative-per-property-state]]"` |
| 2 | Spec answers every "topic the spec must settle" with a concrete decision | PASS | §1 lists 24 locked decisions D201–D224 covering schema shape (D201, D202), load-time cross-check (D208, D214), write-time validation (D203, D209, D210, D222, D223), wildcard (D204, D205, D215), validator placement (D209, D210), `KindDef` surface (D211), error shape (D212–D214), empty `transitions: {}` (D207), type scope (D216), event semantics (D217), documentation deltas (D219), and out-of-scope (D220). No "TBD" entries. |
| 3 | Every open question from `t0186` is answered or explicitly deferred | PASS | §11 "Open-Question Disposition" provides a table mapping each t0186 open question to a concrete spec resolution (schema-shape preference → D201; `StateMachineDef` shape → §3.1; migration of `task/kind.json` → D218). |
| 4 | Spec is reachable from `t0186` via `artifacts:` frontmatter | PASS | `t0186` frontmatter `artifacts:` list contains `"[[openstation/specs/s0033-declarative-per-property-state-machines]]"` |
| 5 | Fresh reader can answer "what does `core.store.update` do when a `transitions:` table rejects the new value?" without reading source | PASS | §5.2 documents the update path: `check_transition` raises `ValidationError` before the write occurs; §6 gives the exact message format `"Illegal transition for field '<prop>': '<current>' → '<target>' (allowed targets: [...]) (allowed from any state: [...])"`; §7.x edge cases cover same-value, deletion, multi-property, and absent-property scenarios. |

### Summary

5 passed, 0 failed. All verification criteria satisfied — the spec is complete, every D-row is settled, the parent task links the artifact, and the runtime behaviour of `core.store.update` is fully readable from the spec without source inspection.

## Progress

### 2026-05-24 — architect
> time: 21:57
> log: [[artifacts/logs/t0187-spec-declarative-per-property-state]]

Authored spec [[openstation/specs/s0033-declarative-per-property-state-machines]] with 24 locked decisions (D201–D224) covering schema shape, KindDef surface, validator placement, error messages, edge cases, and decomposition plan. Added Findings + Downstream sections to task body; linked spec via artifacts: frontmatter on both t0187 and t0186.

### 2026-05-24 — architect
> time: 22:05
> log: [[artifacts/logs/t0187-spec-declarative-per-property-state]]

Observed that sub-task [[t0188-research-property-change-event-design]] was added to this task's `subtasks:` after I started work, pressure-testing the event-semantics assumption (D217). Lifecycle correctly blocks transition to `review` until t0188 reaches `done`. Updated spec D217 and added §5.5 to mark the event decision as **provisional pending t0188's research artifact**; the rest of the spec (schema shape, validator placement, error format, decomposition, docs) is independent of the event outcome and may be implemented in parallel. Leaving this task `in-progress` so the spec is reachable while the research runs; once t0188 reports back, either re-confirm D217 (no catalogue change) or bump the spec version with the recommended diff, then promote t0187 to `review`.

### 2026-05-25 — architect
> time: 14:17
> log: [[artifacts/logs/t0187-spec-declarative-per-property-state]]

Research sub-task [[t0188-research-property-change-event-design]] reported back with [[artifacts/research/r0006-property-change-event-design]] (status `review`). Recommendation: **Option C — subscriber-side filtering, no new event types.** All five surveyed consumer scenarios (assignee-change Slack notify, block-on-verified relational hook, tags index-rebuild, CI status bot, existing `artifact.status_changed` subscribers) are fully addressable with the existing two events; the sole landing artefact is a `property:` hook-matcher key (a matcher-schema change against s0025 / s0032, not a catalogue change). D217 confirmed unchanged. Spec updates: dropped the *(provisional)* qualifier on D217 and rewrote its rationale to cite r0006; rewrote §5.5 from "Deferred — pressure-test against research" to "Confirmed by research" with the Option C outcome and Option B "later" pointer inline; added the t0188 → r0006 link to §13 References. The follow-up `property:` matcher key is tracked in r0006's downstream against s0025 / s0032 — explicitly *not* against this spec.

Spec content is now complete: every D-row settled, every t0186 open question resolved, every "topic the spec must settle" item answered with a concrete decision. Attempted transition to `review` returned exit code 6 — lifecycle correctly blocks because t0188 is still `review` (owner = `user`, awaiting human verification). Task remains `in-progress` per the same correct blocker noted in the 22:05 entry; the user verifying [[t0188-research-property-change-event-design]] (and its artifact r0006) will unblock this transition. No further architect work required on t0187 itself — the spec faithfully reflects the research outcome.

### 2026-05-25 — architect
> time: 15:52
> log: [[artifacts/logs/t0187-spec-declarative-per-property-state]]

Sub-task [[t0188-research-property-change-event-design]] reached `done` since the prior session, unblocking the lifecycle gate. Transitioned t0187 in-progress → review. Spec content unchanged from the 14:17 entry — every D-row settled, every t0186 open question resolved, Findings + Downstream sections present, artifact link in frontmatter. Ready for owner (user) verification against the §Verification checklist.

## Findings

Produced spec [[openstation/specs/s0033-declarative-per-property-state-machines]] (24 locked decisions, D201–D224). Every "topic the spec must settle" item in §Directions has a concrete decision; every open question from t0186 has an explicit resolution row (§11 of the spec).

**Headline decisions:**

- **Schema shape (D201–D202):** three bare sibling keywords (`enum`, `initial`, `transitions`) directly on the property definition. No nested `state_machine:` wrapper, no `x-` vendor-namespacing. Consistent with how `enum` is JSON-Schema-native and how the rest of the kind schema already uses bare keys.
- **`KindDef` surface (D211):** new field `state_machines: dict[str, StateMachineDef]` keyed by property name. `StateMachineDef` is a new frozen dataclass exported from `core` alongside `KindDef`. Non-breaking additive change. `kd.statuses` continues to exist as a convenience alias.
- **Validator placement (D209–D210):** shared helper in a new module `src/artifacts_os/core/transitions.py`. `store.create` calls `check_create`; `store.update` calls `check_transition` (replacing today's single-purpose status check at `store.py:254`); `validate.py` Rule 3 is extended to every state-machined property for the membership half of the contract (`validate_one` cannot check transitions because it has no "before" value).
- **Initial-state strictness (D203 + D223):** strict — at create the property's value, if set, must equal `initial`; if omitted, the system defaults to `initial`. Setting any other value at create fails.
- **Wildcard `*` (D204 + D205):** source-key only (never a destination); not reachable from creation (only after first update). `*` is additive on top of explicit `transitions[current]`.
- **No `transitions:` (D206):** the property keeps today's "any enum value is fine" semantics — full backward compatibility for every existing kind.
- **Empty `transitions: {}` (D207):** legal; locks the field at `initial`. Subsumes the "immutable-after-creation" use case without needing a separate `locked:` flag.
- **Terminal states (D222):** a state present in `enum` but absent as a key in `transitions` is terminal — only `transitions["*"]` is reachable, and if `*` is also absent the field is locked at the current value.
- **Type scope (D216):** enum-only for v1; door not closed for numeric/boolean state machines.
- **Events (D217):** zero new event types. `artifact.updated` and `artifact.status_changed` already cover the observable surface; catalogue stays closed per s0025 §C2. Confirmed by [[artifacts/research/r0006-property-change-event-design]] (Option C — subscriber-side filtering) against five consumer scenarios; the only landing artefact (a `property:` hook-matcher key) is tracked as downstream against s0025 / s0032, not this spec.
- **Migration of `task/kind.json` (D218):** ship with a permissive transitions table on `status` so the contract is exercised end-to-end without changing observable behaviour. Tightening to a restrictive table is a follow-up.
- **Decomposition (D221 + spec §8):** parent task t0186 should be split into 3 sequential sub-tasks: (1) parse + load-time check, (2) write-time enforcement, (3) `task/kind.json` migration + docs.
- **Out of scope (D220 + §12):** cross-property guards, relational rules, auto-timestamps, numeric/boolean state machines, `from: *` default-everywhere form. All listed by reference for future scope-creep rejection.

The error-shape table (§6) gives the implementer exact message strings for all eight failure surfaces; the verification mapping table (§10) cross-references each verification bullet from t0186 to the spec section that settles it.

## Downstream

- **Audit edit (D224 — sibling task suggested):** `[[r0001-openstation-integration-audit]]` §3.1 and §6 currently say "all lifecycle logic on the openstation side". After t0186 lands, the substrate owns *declared* legality (membership + transitions); openstation retains *relational* legality. A one-paragraph audit edit should reflect the new boundary. Documentation-only; not blocking t0186.
- **Openstation harness consolidation (future task):** once `task/kind.json` ships a restrictive `transitions:` table that matches openstation's intent (e.g. `done` is terminal except for `cancelled`), openstation's `TRANSITIONS` / `VALID_TRANSITIONS` / `_STATUS_RANK` tables in `src/openstation/core/lifecycle.py` become candidates for retirement. Out of scope for t0186 because it requires a separate behavioural review of every openstation transition path.
- **`task/kind.json` tightening (future task):** the permissive table shipped by t0186 sub-task #3 (D218) is intentionally a no-op behaviourally. A follow-up should encode the real openstation lifecycle (e.g. `done` terminal, `verified → done` only, `rejected` reachable from anywhere via `"*"`). Needs alignment with openstation's existing transition rules — separate review.
- **Deletable-property keyword (out of scope per spec §7.2):** the spec rejects deletion of a state-machined property via `update(fields={prop: None})`. If a real consumer needs this, a future keyword `deletable: true` could be added to `StateMachineDef`; tracked here so it does not get reinvented inline.
