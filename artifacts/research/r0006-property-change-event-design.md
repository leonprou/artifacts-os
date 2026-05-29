---
kind: research
id: r0006
name: property-change-event-design
agent: researcher
task: "[[t0188-research-property-change-event-design]]"
created: 2026-05-24
---

# Property-Change Event Design for Per-Property State Machines

Research commissioned by [[t0188-research-property-change-event-design]] to
pressure-test the provisional decision D217 in
[[openstation/specs/s0033-declarative-per-property-state-machines]]:
"no new event types needed." The question is how property-change
events should be structured once any property can carry a state
machine, without requiring authors to annotate every property's
"eventfulness" in `kind.json`.

---

## Conclusion First

**Recommendation: Option C (subscriber-side filtering) plus a
`property:` matcher field.**

No new event types. The closed catalogue (s0025 §C2) is preserved
at zero cost. Adding a `property:` matcher key to the hook-matcher
schema is the only artefact of this research that needs landing
— and the task already flags that as a downstream design item. The
current `artifact.status_changed` event is retained unchanged as the
canonical affordance for the single universal lifecycle property.
D217's default position ("no new events") is confirmed.

If the architect later judges that the `status`-only asymmetry is
unacceptable as per-property state machines proliferate, Option B
(`artifact.transitioned`) is the smallest viable catalogue addition.
See §5 for the full catalogue diff and migration story.

---

## 1. Schema Signals Available (No New Declarations Needed)

Before evaluating options, it is worth stating precisely what signals
the substrate already has at dispatch time:

| Signal | Source | Available at? |
|--------|--------|---------------|
| `transitions:` present on property | `KindDef.state_machines` (D211) | Kind-load time; available in `store.update` |
| `enum:` present without `transitions:` | `KindDef.schema` | Kind-load time |
| Property's JSON type (`string`, `integer`, …) | `KindDef.schema` | Kind-load time |
| `initial` declared | `KindDef.state_machines[prop].initial` | Kind-load time |
| `changed` array | computed diff in `store.update` | Dispatch time |

The `transitions:` keyword (added by t0186) is the one signal that
distinguishes "this property carries state-machine semantics" from
"this is a free field." No new author-facing annotation is required;
the schema already has the information.

---

## 2. Candidate Options

### Option A — One New Parameterised Event: `artifact.field_changed`

Add a single generic event to the catalogue. Example payload:

```json
{
  "ts": "...",
  "event": "artifact.field_changed",
  "property": "assignee",
  "kind": "task",
  "id": "t0042",
  "stem": "t0042-fix-the-bug",
  "before": "alice",
  "after": "bob",
  "fields": { "...full frontmatter..." }
}
```

One entry is emitted **per changed property** per `update()` call.
Subscribers match on `event: artifact.field_changed, property: assignee`.

`artifact.status_changed` may be kept as-is (backward compat) or
deprecated in favour of `event: artifact.field_changed, property:
status`.

**Catalogue diff:** one addition (`artifact.field_changed`); optionally
one deprecation (`artifact.status_changed`).

---

### Option B — Implicit Tiering: `artifact.transitioned`

Derive the tier from the schema signal. Properties that declare
`transitions:` emit a dedicated event; everything else stays in
`artifact.updated`.

Example payload:

```json
{
  "ts": "...",
  "event": "artifact.transitioned",
  "property": "status",
  "kind": "task",
  "id": "t0042",
  "stem": "t0042-fix-the-bug",
  "before": "ready",
  "after": "in-progress",
  "fields": { "...full frontmatter..." }
}
```

`artifact.updated` continues to fire for every mutation (including
state-machine properties — it is the catch-all). `artifact.transitioned`
fires additionally after `artifact.updated` whenever a changed property
has `transitions:` in its kind schema. One `artifact.transitioned`
emission per changed transitioned property.

`artifact.status_changed` aligns to `artifact.transitioned` with
`property: status`. Migration options are (i) keep both (dual-fire,
cheapest) or (ii) deprecate `artifact.status_changed` with a grace
period.

**Catalogue diff:** one addition (`artifact.transitioned`); `status_changed`
kept or deprecated.

---

### Option C — Subscriber-Side Filtering Only

No catalogue change. Add a `property:` matcher field to the hook
matcher schema (already flagged as a downstream design item in t0188).

Hook authors write:
```yaml
matcher:
  event: artifact.updated
  property: assignee     # new matcher key: "changed array includes this"
```

Today's `artifact.updated` payload already carries `changed`,
`before.<key>`, `after.<key>` — the information is there. The
`property:` matcher is syntactic sugar over `changed: [assignee]`.
For state-machine transitions, subscribers may additionally filter on
`before.<prop>` and `after.<prop>` fields already in the matcher
schema (§ Matcher Schema in s0025).

`artifact.status_changed` is unchanged: the canonical shortcut for
the universal lifecycle property.

**Catalogue diff:** none. The matcher-schema gains one field (`property:`).

---

## 3. Consumer Scenario Walkthrough

Five scenarios from the task spec, evaluated against each option.

### S1 — Notify Slack when `assignee` changes (no `transitions:` on `assignee`)

| Option | Hook configuration | Notes |
|--------|-------------------|-------|
| A | `event: artifact.field_changed, property: assignee` | Clean. Fires N times if N properties change in one call. |
| B | `event: artifact.updated, property: assignee` or `changed: [assignee]` | B provides no `artifact.transitioned` here (`assignee` has no `transitions:`). Falls back to the same shape as C. |
| C | `event: artifact.updated, property: assignee` | Requires the `property:` matcher. Equivalent ergonomics to A. |

**Summary:** A is marginally cleaner for this case; B provides no
advantage. C with the `property:` matcher is equally expressive.

---

### S2 — Block transition to `verified` until subtasks `done` (relational, observes `status` change)

| Option | Hook configuration | Notes |
|--------|-------------------|-------|
| A | `event: artifact.field_changed, property: status, after.status: verified` — or, if `status_changed` kept: `event: artifact.status_changed, after: verified` | Relational check lives in the hook action regardless. |
| B | `event: artifact.transitioned, property: status, after: verified` | Matches the semantic intent precisely. `after` is scalar. |
| C | `event: artifact.status_changed, after: verified` | Already works today, no change needed. |

**Summary:** C's `artifact.status_changed` is already the right primitive.
A and B add equivalent expressiveness for non-`status` transitioned
properties. For `status` specifically, C is the winner (zero work).

---

### S3 — Index-rebuild on `tags` change (free-form, not a state machine)

| Option | Hook configuration | Notes |
|--------|-------------------|-------|
| A | `event: artifact.field_changed, property: tags` (if A fires for all property changes) | Only if A covers non-transitioned properties; this would be a catch-all parameterised event, not tied to `transitions:`. |
| B | `event: artifact.updated, changed: [tags]` | `tags` has no `transitions:`. B's `artifact.transitioned` does not fire here. Falls back to `artifact.updated`. |
| C | `event: artifact.updated, property: tags` | Same ergonomics. |

**Summary:** B provides no advantage for free-form fields. A requires
deciding whether `artifact.field_changed` fires for *all* property
changes (open catalogue by stealth) or only for transitioned ones (still
falls back to `artifact.updated` for `tags`). C works uniformly.

This scenario reveals a hidden fork in Option A: if `artifact.field_changed`
fires only for properties with `transitions:`, scenarios S1 and S3 are
*not* covered by A (because `assignee` and `tags` have no `transitions:`).
If it fires for all property changes, A is a richer but noisier replacement
for `artifact.updated` — effectively opening the catalogue via proliferation.
Neither fork is clearly desirable.

---

### S4 — CI bot wants every status transition for every kind

| Option | Hook configuration | Notes |
|--------|-------------------|-------|
| A | `event: artifact.field_changed, property: status` or `artifact.status_changed` | Works with either. |
| B | `event: artifact.transitioned, property: status` | Clean; or `artifact.status_changed` retained. |
| C | `event: artifact.status_changed` | Already works. Zero change. |

**Summary:** All options serve this scenario. C requires zero work.

---

### S5 — Existing `artifact.status_changed` subscribers (migration cost)

| Option | Migration required | Cost |
|--------|-------------------|------|
| A | Keep `artifact.status_changed` alongside `artifact.field_changed` (dual-fire on `status`). Optional: deprecate with a grace period. | Low if kept. Medium if deprecated — all existing hooks must update. |
| B | Keep `artifact.status_changed` and fire `artifact.transitioned` additionally for every property with `transitions:`. Optional: deprecate `artifact.status_changed`. | Low if kept. Medium if deprecated. |
| C | No change. | Zero. |

**Summary:** Keeping `artifact.status_changed` in A and B costs nothing
and avoids breaking consumers. Deprecating it costs every existing hook
author a rewrite.

---

## 4. Prior Art

Three comparisons, chosen for relevance over breadth.

### 4.1 Git Hook Tiers

Git's `pre-commit` / `post-commit` / `post-receive` split is a
**tier-by-operation** model: hooks are named after the operation, not
the changed objects. Subscribers that care about specific files grep
`git diff --name-only` inside their hook body. This is Option C
applied to VCS: the transport is coarse, discrimination is subscriber-
side. Git explicitly does not add `post-file-changed` hooks for each
file type. The analogous principle: `artifact.updated` is the coarse
event; filtering on `changed: [assignee]` is the subscriber-side
discrimination.

### 4.2 Event Sourcing — Domain Events vs Internal Events

Domain-Driven Design event sourcing literature distinguishes **domain
events** (cross a bounded context; worth a specific type name) from
**internal events** (implementation detail; aggregate-internal). The
`transitions:` keyword is exactly the signal that a property is
"domain-event-worthy" — it has declared legal states and legal moves
between them. This is the architectural basis for Option B:
`artifact.transitioned` is the domain-event type; `artifact.updated`
is the internal-event catch-all.

However, this distinction is only valuable if *consumers* are
architected at the bounded-context level. In a single-vault
`artifacts-os` setup, most consumers are the same team and can treat
the `artifact.updated` + `changed` array as sufficient. The domain-
event argument strengthens as the system scales; in a single-project
vault today it is over-engineering.

### 4.3 Redux Action-Type Granularity

Redux's ecosystem evolved two directions: (i) specific named action
types per field (`USER_EMAIL_UPDATED`, `USER_ROLE_CHANGED`) for
discoverability and dev-tools, and (ii) the "entity adapter" pattern
with a generic `update(entity, changes)` action for brevity. The
generic form dominated because the per-field proliferation was hard to
maintain and offered no practical benefit for reducers that still had to
`switch` on both type and subfield. This maps directly to the argument
against Option A: `artifact.field_changed` with a `property` argument
is the Redux "generic update" form, and adding it alongside
`artifact.updated` creates two overlapping channels for the same
information — without the actual discoverability win (the hook YAML
still needs the `property:` field either way).

---

## 5. Catalogue-Diff Summary for Each Option

| Option | Events added | Events deprecated | Matcher changes |
|--------|-------------|-------------------|-----------------|
| A | `artifact.field_changed` | `artifact.status_changed` (optional) | `property:` matcher key added |
| B | `artifact.transitioned` | `artifact.status_changed` (optional) | `property:` matcher key added |
| C | *none* | *none* | `property:` matcher key added |

### C2-compliance note

s0025 §C2 states: "The catalog is closed. New event types require a
spec revision and a `version` bump in this spec's frontmatter."

- Options A and B each require one spec revision to s0025.
- Option C requires no spec revision. The `property:` matcher key is
  a matcher-schema change (not an event-catalogue change) and is
  covered by the hook configuration section of s0025, not §C2.

---

## 6. Migration Story for `artifact.status_changed`

**Confirmed recommendation: Keep `artifact.status_changed` as-is,
regardless of which option is chosen.**

The event was introduced because `status` is the single universal
lifecycle property. Its ergonomic advantage (scalar `before`/`after`
values; short matcher syntax `after: review`) is real and is not
duplicated by any other mechanism today.

**If Option B is adopted:**

- `artifact.transitioned` fires for every property with `transitions:`,
  including `status`.
- `artifact.status_changed` continues to fire in parallel as today
  (dual-fire, same as its current relationship to `artifact.updated`).
- The relationship becomes: `artifact.status_changed` is an alias for
  `artifact.transitioned` where `property = status`, kept for
  backward compatibility.
- If the architect wishes to consolidate: deprecate `artifact.status_changed`
  in s0025 v3, with a migration note: "replace `event: artifact.status_changed`
  with `event: artifact.transitioned, property: status`." A grace period
  of at least one minor release is recommended.
- Do **not** rename `status_changed` to embed the property in the event
  name (i.e., do not ship `artifact.status_changed` alongside
  `artifact.assignee_changed` — that path opens the catalogue per kind
  property, which conflicts with §C2).

**If Option C is adopted** (recommended):

- `artifact.status_changed` is unchanged. No migration. No deprecation.

---

## 7. Open Questions Closed

### OQ1 — Is `artifact.status_changed` itself the right model to generalise, or the wrong one?

It is the wrong model to generalise as a named-per-property event
(i.e., do not ship `artifact.assignee_changed`). It is a specifically-
named event for the specifically-named property that every kind shares.
Generalising it as `artifact.field_changed` (Option A) or
`artifact.transitioned` (Option B) is correct; spawning per-property
variants is not.

### OQ2 — What about properties with `enum:` but without `transitions:`?

Their changes belong in `artifact.updated`. The absence of `transitions:`
settles it: no state-machine semantics, no state-machine event. Free
movement means the property is a tag, label, or category — not a lifecycle
stage. Inserting it into a new event tier would require either an author-
side declaration (explicitly out of scope) or an implicit rule that
"any `enum` property gets a special event" (which would cover nearly
every categorical field in every kind schema, over-broadening the signal).

### OQ3 — One event per changed property, or one event per `update()` call?

`artifact.updated` is one-per-call with a `changed` array. This is the
correct model. If Option A or B is adopted, the derived event should
fire **once per changed transitioned property** (N emissions for N
changed properties with `transitions:`). This matches the existing
`artifact.status_changed` behaviour (one derived emission per `update`
when `status` is in `changed`). The dedup burden on subscribers is
minimal for the expected case of one property changing per call; for
bulk writes, subscribers handle N events the same way they would a
`changed` array with N entries.

### OQ4 — Hook matcher schema impact (flagged, not designed here)

If the `property:` matcher key is added, s0032-hooks-via-artbook-
distribution and the matcher validation in `hooks/loader.py` need to
be updated. The matcher engine currently rejects unknown keys with
`ValidationError` at config load time. Adding `property:` means:
- Matcher engine: `property:` is a membership check against
  `payload["changed"]` for `artifact.updated`, or against
  `payload["property"]` for `artifact.transitioned` / `artifact.field_changed`.
- YAML schema: `property:` accepts a string or list (consistent with
  the multi-value OR semantics of existing matcher keys per s0023).
- This is out of scope to design here but is the primary downstream
  consequence of any option in this recommendation.

---

## 8. Confidence Levels

| Claim | Confidence | Basis |
|-------|------------|-------|
| Option C is sufficient for all five consumer scenarios | High | Walked through each; `artifact.updated` + `changed` array + `property:` matcher covers all of them |
| Adding `property:` matcher key is the minimum required change | High | Every option requires it; it is not a catalogue change |
| `artifact.status_changed` should not be deprecated | High | Zero benefit to removing it; breaking change for existing subscribers |
| Option B is the right choice if the architect wants a new event type | Medium | Rests on the "domain-event" framing which becomes more valuable at scale; may be over-engineering for a single-project vault |
| Option A should be avoided | Medium | The "fires for which properties?" fork is unresolved and either outcome has downsides; the dual-channel with `artifact.updated` is redundant |

---

## 9. Recommendation for D217

D217 in s0033 should be **confirmed** — no new event types needed. The
provisional "conditional on t0188" note may be resolved as follows:

> **D217 (confirmed):** No new event types. `artifact.updated` (already
> carries `changed`/`before`/`after`) and `artifact.status_changed`
> (already fires for `status` specifically) cover the substrate's
> observable transitions for all consumer scenarios evaluated in
> [[r0006-property-change-event-design]]. The catalogue stays closed
> per s0025 §C2. The sole downstream action is adding a `property:`
> matcher key to the hook matcher schema (a matcher change, not a
> catalogue change), deferred to a separate spec revision of s0025
> § "Matcher Schema."

If the architect later revisits this — motivated by real consumers
expressing that `artifact.updated` filtering is insufficient — Option B
(`artifact.transitioned`, deriving from `transitions:` presence) is
the recommended next step. It is clean, schema-derived, and requires
exactly one spec revision to s0025.

---

## Tags

#research #events #state-machines #hooks #per-property #t0188 #t0187 #s0025 #s0033
