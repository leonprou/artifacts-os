---
kind: task
id: t0188
name: research-property-change-event-design
type: research
status: done
assignee: researcher
owner: user
parent: "[[t0186-add-declarative-per-property-state]]"
created: 2026-05-24
started: 2026-05-24
artifacts:
  - "[[artifacts/research/r0006-property-change-event-design]]"
completed: 2026-05-29
---

# Research Property-Change Event Design For Per-Property State Machines

# Research property-change event design for per-property state machines

## User story

> **As the architect settling `[[t0187-spec-declarative-per-property-state]]`'s "Event semantics" section, I want a researched recommendation on how property-change events should be structured so that consumers can subscribe to the changes they care about without the schema asking authors to annotate every property's "weight" or "eventfulness".**

## Why

`[[t0186-add-declarative-per-property-state]]` ships per-property state machines. The spec sub-task `[[t0187]]` currently assumes "no event-catalogue change is required — `artifact.updated` already carries the delta, `artifact.status_changed` continues to fire for `status` specifically". That assumption is worth pressure-testing because:

- **Property changes carry different signal in practice.** A `status: ready → in-progress` move is a workflow event; an `updated:` timestamp bump is bookkeeping; an `assignee:` change matters to notification consumers but not to CI bots. Subscribers (hooks, CI integrations, search indexers, dashboards) care about different fields. Today's catalogue already reflects this inconsistently — `artifact.updated` fires for any mutation, `artifact.status_changed` fires for *one* specific high-signal transition. There's no principled middle.
- **`[[s0025-artifact-events]]` §C2 closes the catalogue.** Adding new event types is a spec revision, not a free choice. Getting the catalogue shape right at t0186 time is cheaper than churning the catalogue once consumers exist.
- **Per-property state machines generalize the `status` case.** Once any property can carry a state machine, the asymmetry between `status_changed` (one event) and "everything else changed" (lumped into `updated`) needs justification or repair.

Annotating weight in `kind.json` (e.g., `eventful: true`) is **explicitly out of scope** for this research: asking authors to label every property's weight is a bad solution — it pushes a substrate concern into the schema and creates drift between what's declared and what subscribers actually filter for. The research must find a recommendation that derives the right behaviour from schema signals that already exist, or pushes discrimination to subscribers entirely.

## Directions

Intent, not contract — researcher owns the final shape and produces a research artifact.

- **Survey the candidate event-structure options.** At minimum:
  - **(A) One new parameterized event** — `artifact.field_changed` with `property` argument. One catalogue addition, generic over property. Subscribers (and hook bundles) match on `event: artifact.field_changed + property: <name>`. `artifact.status_changed` may stay for backward compat or be deprecated in favour of the parameterized form.
  - **(B) Implicit tiering from existing schema signals** — presence of `transitions:` on a property is itself the signal that "this property carries state-machine semantics". Substrate emits a dedicated `artifact.transitioned` event for those changes (parameterized by property name), keeps `artifact.updated` as the catch-all for everything else, and either retires or aligns `artifact.status_changed`. No new author-facing declaration; the schema's existing `transitions:` keyword does double duty.
  - **(C) Subscriber-side filtering only** — leave the catalogue exactly as-is. Subscribers filter `artifact.updated`'s `changed` array for the property names they care about. Hook bundles grow a `property:` matcher field. No catalogue change.
  - **(D) Anything else the researcher surfaces** — prior art may suggest a hybrid or a different decomposition.

- **Evaluate against concrete consumer scenarios.** For each option, walk through:
  - Hook bundle for "notify Slack when `assignee` changes" (no `transitions:` on `assignee`)
  - Hook bundle for "block transition to `verified` until subtasks `done`" (relational, but observes `status` change)
  - Index-rebuild on `tags` change (free-form, not state-machine)
  - CI bot that wants every status transition for every kind (generic over kinds)
  - openstation's existing `artifact.status_changed` subscribers (migration cost)

- **Identify which schema signals are already available.** At minimum: presence of `transitions:`, presence of `enum:`, presence/absence of the property in the kind schema, the property's JSON type. The recommendation should rest on these — not on a new author-facing declaration.

- **Prior art to survey.** Event sourcing weight tiers, observable / reactive frameworks (RxJS, Svelte stores) and how they categorize updates, frontend state libraries (Redux action-type granularity), Git's `pre-commit` / `post-commit` / `post-receive` hook split as a tier analogue, Kubernetes event types (`Normal` vs `Warning` vs custom). Aim for two or three relevant comparisons; this is not a literature review.

- **Closed-catalogue implications.** Whatever the recommendation, name the catalogue diff explicitly — which event types are added, kept, deprecated. The output should let the `[[s0025]]` revision (if any) be drafted by the architect from the research alone.

- **Migration story for `artifact.status_changed`.** Today's subscribers depend on this. Recommend explicitly: keep it as canonical for `status` and add a parallel mechanism for other properties? Promote it to a general transition event with a `property:` argument and deprecate the implicit `_status_` in the name? Leave it untouched and never expand the catalogue?

## Open questions

For the researcher to surface (or close):

- **Is `artifact.status_changed` itself the right model to generalize, or the wrong one?** It's a specifically-named event for a specifically-named property. Generalizing it might produce `artifact.<property>_changed` for every property with `transitions:` — which effectively opens the catalogue. That conflicts with §C2.
- **What about properties without `transitions:` but with `enum:`?** Do their changes deserve a tier between "transition" and "any update"? Or does the absence of `transitions:` settle it ("free movement = no special signal")?
- **Does the substrate fire one event per changed property, or one event per `update()` call with a list of changed properties?** Today's `artifact.updated` is one-per-call with a `changed` array. If we add `artifact.field_changed`, do we fire it N times or once with N entries? Affects subscriber dedup logic.
- **Hook matcher schema impact.** Per `[[s0032-hooks-via-artbook-distribution]]`, hook bundles match on event name. If the recommendation introduces a `property:` argument, the matcher schema needs a `property:` field too. Out of scope to design here — just flag it.

## Sub-tasks

None. Output is a research artifact (`r00NN-...`) under `artifacts/research/`.

## Verification

- A research artifact (e.g. `r00NN-property-change-event-design`) exists under `artifacts/research/`, owned by `researcher`, parented to `[[t0188]]` (this task).
- The artifact presents the candidate options (at minimum the three sketched above), walks each through the consumer scenarios named in §Directions, and ends with a concrete recommendation.
- The recommendation names the catalogue diff explicitly (events added / kept / deprecated).
- The recommendation does **not** rely on a new author-facing declaration in `kind.json` (no `eventful:`, no weight annotation) — it must derive from schema signals that already exist or from subscriber-side filtering.
- The migration story for existing `artifact.status_changed` subscribers is named in the artifact.
- `[[t0187-spec-declarative-per-property-state]]` cites this research artifact in its §"Event semantics" section when settled.

## Progress

### 2026-05-24 — researcher
> time: 22:04

Produced r0006-property-change-event-design. Recommendation: Option C (subscriber-side filtering, no new events). D217 confirmed — catalogue stays closed. All five consumer scenarios satisfied by existing events + a property: matcher key addition. artifact.status_changed retained unchanged.

## Findings

Produced [[artifacts/research/r0006-property-change-event-design]].

**Recommendation: Option C — subscriber-side filtering, no new event types.**

D217 in s0033 (provisional "no catalogue change") is **confirmed**. All five
consumer scenarios (assignee-change Slack notify, block-on-verified relational
hook, tags index-rebuild, CI status bot, existing status_changed subscribers)
are fully addressable with `artifact.updated` + `artifact.status_changed` today.
The sole landing item is a `property:` matcher key in the hook matcher schema
(a matcher-schema change, not an event-catalogue change, therefore not subject
to s0025 §C2).

**Key findings:**

- Option A (`artifact.field_changed`) has an unresolved fork: fire for all
  property changes (noisy, redundant with `artifact.updated`) or only for
  transitioned ones (still misses free-field scenarios like `assignee` and
  `tags`). Neither outcome is clearly better than Option C.
- Option B (`artifact.transitioned`) is the correct *next step* if the architect
  later decides the `status`-only asymmetry is unacceptable as per-property state
  machines proliferate. Derived cleanly from `transitions:` presence — no new
  author-side declaration needed.
- `artifact.status_changed` should not be deprecated under any option; it is a
  named ergonomic affordance for the universal lifecycle property with zero
  migration benefit for removal.
- Open question OQ3 closed: derived events should fire once per changed transitioned
  property (N emissions for N such properties), matching `artifact.status_changed`'s
  existing behaviour.
- Open question OQ4 flagged for s0025 / s0032 owners: `property:` matcher key
  requires an update to the matcher validation in `hooks/loader.py` and the matcher-
  schema docs.

## Downstream

- **s0025 revision for `property:` matcher key.** Whichever option lands (or even
  just Option C), the hook matcher schema in s0025 § "Matcher Schema" needs a
  `property:` key entry. Currently unknown matcher keys raise `ValidationError` at
  config load time. A separate s0025 revision should add `property:` as a supported
  matcher key with multi-value OR semantics (matching membership in `payload["changed"]`).
- **s0032 matcher docs.** The artbook hook-bundle format references the same
  matcher schema; needs the same addition once s0025 revision lands.
- **D217 confirmation in s0033.** The architect should update the §5.5 provisional
  note and D217 row in s0033 to cite this artifact and drop the "conditional on
  t0188" qualifier.
