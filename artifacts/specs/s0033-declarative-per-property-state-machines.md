---
kind: spec
id: s0033
name: declarative-per-property-state-machines
status: draft
task: "[[t0186-add-declarative-per-property-state]]"
created: 2026-05-24
agent: architect
---

# Declarative Per-Property State Machines in `kind.json`

Locks the technical contract for the parent feature
[[t0186-add-declarative-per-property-state]]. Settles the schema
shape, validator placement, `KindDef` surface, and edge cases so
that implementation is a mechanical translation of this document,
not a series of in-review judgement calls.

The mechanism is generic over property and kind: any enum-typed
property in any `kind.json` may declare a state machine, and the
substrate enforces legal-value membership and legal `(from, to)`
transitions at every write. Relational rules (subtask blocking,
`depends_on`, ownership) remain higher-layer concerns expressed via
hooks; see § 12.

---

## 1. Locked Decisions

Numbered `D201…` to avoid collision with neighbouring specs
(s0029, s0031, s0032's `D101…`).

| ID    | Decision | Rationale |
|-------|----------|-----------|
| D201  | The state machine declaration uses **three sibling keywords** inside the property definition: `enum:`, `initial:`, `transitions:`. No nested `state_machine:` wrapper. | Matches the rest of the kind schema (`statuses`, `prefix`, `numbered`, `x-dir` are all bare keys per t0142). `enum` is already JSON-Schema-native; keeping it at the property root means JSON Schema tooling continues to read it without a custom keyword. |
| D202  | The new keywords are **bare** (`initial`, `transitions`), not vendor-namespaced (`x-initial`, `x-transitions`). | Consistency with the bare `statuses`/`prefix`/`numbered`/`x-dir` mix that already exists. The `x-` prefix is reserved for *kind-level* metadata read by `Registry` directly off the root object; *property-level* keywords stay bare. The JSON Schema spec permits unknown keywords inside property definitions — Draft 7 validators ignore them silently. |
| D203  | `initial` is **strict**: at create time the value, if set, **must equal `initial`**; if omitted, the system defaults it to `initial`. Setting any other value at create fails with a `ValidationError`. | The looser reading ("any enum value is fine at create") makes `initial` meaningless and turns the state machine into a `(from, to)` table that admits illegal starting states. The strict reading matches openstation's current behaviour (every task is created `backlog` or `ready`, never `done`) and is what an "initial state" of a state machine actually means. |
| D204  | The wildcard `*` is a **source key only**, never a destination value. Its semantics: "from any state currently in `enum`, the transitions listed under `*` are additionally legal." | A wildcard destination would be semantically void — every transition's RHS would degenerate to `enum`. The source-only form gives the emergency-abort idiom (`"*": ["rejected"]`) without ambiguity. Load-time validation rejects `*` appearing inside any RHS list. |
| D205  | The wildcard `*` is **not reachable from creation**. The initial state is `initial`; wildcard targets only become reachable on the first `update`. | If wildcards applied at create time, `initial` would be one of many legal starting values and lose its meaning. The state machine's invariant is "first state is `initial`; everything else is governed by `transitions[current] ∪ transitions["*"]`". |
| D206  | A property with `enum:` but **without `transitions:`** is unchanged: any enum value is a legal starting value, and any enum value is a legal target on update. `initial` may still be set; if it is, D203 still applies (strict creation), but absence of `transitions:` means update accepts any enum value. | Backward compatibility for every existing kind shipped in the vault. Operators opt into transition enforcement by adding `transitions:`; nothing else moves. |
| D207  | A property may declare `"transitions": {}` (empty object). Semantics: **the field is locked at `initial` and may never change**. Updates that attempt to change it fail with the same transition error message. | Useful for immutable-after-creation fields (a hypothetical `kind`, `id`, `created` modelled this way; the property type only needs `enum` to fit). Rejecting empty would require a separate "locked: true" flag for the same idea; admitting empty subsumes it. |
| D208  | Cross-checks run at **kind registration time** (`Registry._load_vault_kinds`), not lazily. Failure raises `ValidationError`, which propagates out of `Registry.__init__` and aborts vault load. | Today's registry already raises on `x-storage`, `x-manifest-name` template tokens, description anti-patterns. State-machine drift is the same shape of error and deserves the same fail-fast treatment. A typo in `transitions` should not wait until the first `update` to surface. |
| D209  | Write-time enforcement lives in **`core/store.py`** for both `create` and `update`. `core/validate.py` Rule 3 (status-membership) is **extended** so that `validate_one` reports the same transition rejection as a `ValidationIssue` when given a frontmatter dict that was edited by hand (the `cli verify` path). | Today the membership check is duplicated by design: `store.update` enforces at write time; `validate.py` Rule 3 catches drift in already-written files. The same dual placement applies here. The two surfaces share a single helper module (`core/transitions.py`, D210) so the logic is written once. |
| D210  | A new module **`src/artifacts_os/core/transitions.py`** holds the shared logic: parsing the state-machine declaration out of `KindDef.schema`, computing the legal target set for `(property, current)`, and producing the `ValidationError` / `ValidationIssue` message. Both `store.py` and `validate.py` import from it. | Single source of truth for the validation rule and the error message. The module has no dependency on `events` or `hooks`; `store.py` keeps its existing position in the DAG. |
| D211  | `KindDef` grows **one new field**: `state_machines: dict[str, StateMachineDef]`, keyed by property name. `StateMachineDef` is a new dataclass with `enum: list[str]`, `initial: str \| None`, `transitions: dict[str, list[str]] \| None`. The field is populated at registry load time and is `{}` for kinds with no state machines declared. | Public consumers of `Registry.get(kind)` get a typed surface, not a raw-JSON dive. The existing `KindDef.statuses` field is kept as a convenience alias — it remains a flat `list[str]` mirroring `state_machines["status"].enum` when present, else `schema.properties.status.enum` (current behaviour). No breaking change for callers that read `kd.statuses`. |
| D212  | Write-time error message format: `"Illegal transition for field '<prop>': '<current>' → '<target>' (allowed targets: <list>; allowed from any state: <wildcard-list>)"`. The wildcard clause is **omitted when empty**. | Names every variable the operator needs to act on. Matches the family of today's `"Invalid status 'foo' for kind 'task'. Allowed: […]"` — concrete value first, then the legal set. |
| D213  | Create-time strict-`initial` error message: `"Illegal initial value for field '<prop>': '<value>' (must be '<initial>')"`. | Same family as D212; names the property, the offender, and the only legal value. |
| D214  | Load-time cross-check error messages name the kind, the offending key path, and the universe (`enum`). Three concrete forms: (a) `"Kind '<kind>': field '<prop>' declares 'transitions' without 'enum'"`, (b) `"Kind '<kind>': field '<prop>' transitions key '<key>' is not in enum [<enum>]"`, (c) `"Kind '<kind>': field '<prop>' transitions['<key>'] target '<target>' is not in enum [<enum>]"`, (d) `"Kind '<kind>': field '<prop>' initial '<value>' is not in enum [<enum>]"`. | Consistent with the existing `Registry` error family ("Kind '<name>': …"). The path is named (`prop`, `key`, RHS index) so the operator can find the offender without grepping the schema. |
| D215  | `*` may also appear as a `transitions:` key (source semantics, D204). Load-time check (D214b) **skips the `*` key when validating "key ∈ enum"** but still validates the RHS list against `enum`. | The wildcard is the documented exception to D214b; nothing else is. |
| D216  | **Scope: enum-typed properties only.** Properties with `type: integer`, `type: boolean`, or any other JSON Schema type that *could* in principle carry a transition table do not get one in v1. The load-time check rejects `transitions:` on any property without `enum:` (D214a covers it). | Numeric ladders (`1: [2, 0]`) and boolean toggles add edge cases (closed-vs-open enum, equality vs comparison) that don't earn their keep until a real consumer asks. Door is not closed: future work may extend `StateMachineDef` to discriminate on JSON Schema `type`. |
| D217  | **No new events.** `artifact.updated` (already carries `changed`/`before`/`after`) and `artifact.status_changed` (already fires for `status` specifically) cover the substrate's observable transitions. The catalogue stays closed per s0025 §C2. Confirmed by [[artifacts/research/r0006-property-change-event-design]] (Option C — subscriber-side filtering): all five surveyed consumer scenarios are fully addressable with the existing two events plus a `property:` hook-matcher key (a matcher-schema change, *not* a catalogue change). | A transition rejection is a `ValidationError` raised by `store.update`, which already short-circuits dispatch (the pre-phase never fires for a write that failed validation). Subscribers can already read every per-property delta from `artifact.updated.changed/before/after`; the closed catalogue is preserved at zero cost. The follow-up `property:` matcher key is captured as a downstream item against s0025 / s0032, not against this spec. |
| D218  | `task/kind.json` ships with a **permissive `transitions:` table on `status`** as part of the implementation — every current state can move to every other current state, exercising the contract end-to-end without changing observable behaviour for openstation tasks. Adding a *restrictive* table (e.g. forbidding `done → backlog`) is explicitly out of scope and is itself a follow-up task. | Without an in-vault example, the implementation has no end-to-end exercise and the docs have nothing to reference. Permissive (today's behaviour) is the safe migration; restrictive is a behaviour change that needs its own discussion (openstation's `_STATUS_RANK` and bulk-import flows depend on today's permissive read). |
| D219  | Documentation deltas in the same commit as the implementation: `docs/adding-a-kind.md` (new "Property-Level State Machines" subsection), `src/artifacts_os/core/README.md` (KindDef table + a short "Per-Property State Machines" subsection + import line for `StateMachineDef`). The audit follow-up note in `r0001-openstation-integration-audit` §3.1 / §6 is a separate task (D224). | Co-located doc updates are the project's existing rule ("Doc updates accompany API changes" — `CLAUDE.md`). The audit edit involves another agent's wording and is left as a sibling task. |
| D220  | Out of scope, named explicitly so scope creep can be rejected by reference: (i) cross-property guards (`"can't move status while priority: critical"`); (ii) relational rules (subtask blocking, `depends_on` blocking, ownership/role checks, checklist parsing); (iii) auto-recording timestamps on transition (`started`, `completed`); (iv) numeric and boolean state machines (D216); (v) a `from: *` matching `to: *` "default everywhere" form. | All of these are real needs but live above this layer (hooks / openstation / future scope). Pulling them into v1 turns a focused spec into a workflow engine. |
| D221  | **Sub-task decomposition.** The implementation parent task ([[t0186-add-declarative-per-property-state]]) is sized for 3 sub-tasks: (1) schema parsing into `KindDef.state_machines` + load-time cross-check, (2) write-time enforcement in `store.py` + `validate.py` extension + the shared `transitions.py` helper, (3) docs + the permissive `task/kind.json` migration (D218). Order matters: each builds on the previous; tests for each phase live with the phase. | The work spans the registry, the write path, and docs — three of the file-count heuristics from `docs/decomposition.md`. Splitting at the read/write/docs boundary keeps each PR's blast radius small and each test suite focused. |
| D222  | **Behaviour of `current ∉ transitions` keys** (i.e. a state declared in `enum` but with no row in `transitions`). Interpreted as **terminal**: the only legal targets are `transitions["*"]`. If `transitions["*"]` is also absent, the field is locked at `current` and cannot change. | Coherent with D207 (empty `transitions: {}` locks the field) and D204 (wildcard is additive). A "implicit-permissive" reading (no row → any enum value) would silently bypass the contract whenever the operator forgets a row; explicit-terminal forces them to write the wildcard if they want a global escape. The error message (D212) explains "allowed targets" so the operator sees the row is empty. |
| D223  | **`initial` defaulting on create** (D203 strict): if the property is **omitted** from `fields=`, `core.store.create` injects `state_machines[prop].initial` into the new frontmatter dict before the `_validate_schema` call. If the property is **set** to anything other than `initial`, the create fails. | Symmetric with the strict reading: `initial` is the *only* legal starting value, set explicitly or defaulted. The default-on-omit branch keeps existing `artifacts create <kind> "title"` calls working without forcing every caller to pass `--fields status=backlog`. |
| D224  | Sibling follow-up task (not blocking the implementation): a one-paragraph edit to [[r0001-openstation-integration-audit]] §3.1 and §6 noting the substrate↔harness boundary now distinguishes *declared* legality (substrate) from *relational* legality (harness). Documentation-only; no code. | The audit's current text says "all lifecycle logic on the openstation side" — once D201–D223 land, the substrate owns a slice of that, and the audit should reflect it. Not a blocker for shipping. |

---

## 2. Schema Shape

### 2.1 Worked example — `task/kind.json` post-D218

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

This is intentionally **fully permissive** — D218. It exercises
every code path (load-time cross-check, write-time membership-and-
transition lookup, the shared helper, the error format) without
changing what an openstation user can do today. Tightening the
table to encode openstation's real lifecycle (e.g. `done` is
terminal except `done → cancelled`) is a follow-up.

### 2.2 Worked example — restrictive state machine

```jsonc
"phase": {
  "enum": ["scope", "design", "build", "ship", "retired"],
  "initial": "scope",
  "transitions": {
    "scope":   ["design"],
    "design":  ["scope", "build"],
    "build":   ["design", "ship"],
    "ship":    ["build", "retired"],
    "retired": [],
    "*":       ["retired"]
  }
}
```

- `scope` may only forward to `design`.
- `design` may rewind to `scope` or forward to `build`.
- `retired` has no outgoing edges (terminal — D222 applies).
- Any state may emergency-jump to `retired` via the wildcard
  (`"*": ["retired"]`).
- Per D205, the first write to a new artifact must land on
  `scope`; `retired` is only reachable after at least one update.

### 2.3 Worked example — locked field

```jsonc
"category": {
  "enum": ["external", "internal"],
  "initial": "external",
  "transitions": {}
}
```

Per D207 + D222: `category` is fixed at `external` for every
artifact of this kind. An `update` that tries to change it fails
with `"Illegal transition for field 'category': 'external' → 'internal' (allowed targets: )"`.
(Operators who find this message ugly should fix the source of
the update, not the message — the empty target list is the
intentional signal.)

---

## 3. `KindDef` Surface

### 3.1 New dataclass — `StateMachineDef`

Lives in `src/artifacts_os/core/models.py`.

```python
@dataclass(frozen=True)
class StateMachineDef:
    """Property-level state machine declared in kind.json.

    Built by Registry at load time from the `enum` + `initial` +
    `transitions` keywords inside a property definition. Consumed
    by core.transitions.{check_create, check_transition} and by
    core.validate.validate_one (Rule 3 extension).
    """
    enum: tuple[str, ...]                          # allowed universe
    initial: str | None                            # initial state; None when undeclared
    transitions: dict[str, tuple[str, ...]] | None # None ↔ unrestricted (D206); {} ↔ locked (D207)
```

`tuple` (not `list`) for both `enum` and each RHS — the
dataclass is frozen and consumers should treat the state machine
as immutable runtime data. Mutability would create a footgun
where a per-call edit to `kd.state_machines[prop].transitions`
silently rewrote validation rules.

### 3.2 New `KindDef` field

```python
@dataclass
class KindDef:
    # ...existing fields...
    state_machines: dict[str, StateMachineDef] = field(default_factory=dict)
```

- Keyed by property name (`"status"`, `"phase"`, …).
- Empty dict for kinds with no state machines declared (no
  property has `transitions:` *or* `initial:`).
- `kd.statuses` continues to exist and mirrors
  `kd.state_machines["status"].enum` when present, else the raw
  `properties.status.enum` from `schema` (current behaviour). No
  caller change required.

### 3.3 Public API impact

`src/artifacts_os/core/__init__.py` re-exports `StateMachineDef`
alongside the existing `KindDef`, `Artifact`, etc. Listed in the
`### Models` table in `core/README.md` (D219).

This is a **non-breaking, additive** API change. `KindDef`
instances constructed by callers without the new field get
`state_machines={}` from the dataclass default; nothing breaks.
The version bump is **minor** (semver-ish), not major.

---

## 4. Load-Time Cross-Check (Registry)

### 4.1 Trigger point

`Registry._load_vault_kinds` already walks each `kind.json` and
builds a `KindDef`. After the existing parse (storage, manifest
template, required fields, description), it calls a new helper
`_parse_state_machines(schema, kind_name) -> dict[str, StateMachineDef]`
which raises `ValidationError` on any of the four failure modes
in D214. The exception propagates out of `Registry.__init__`,
aborting vault load — exactly like today's `x-storage` and
`x-manifest-name` failures.

### 4.2 Parsing rules

For each entry in `schema.get("properties", {})`:

1. Read the property dict. Let `enum = prop.get("enum")`,
   `initial = prop.get("initial")`, `transitions = prop.get("transitions")`.
2. If `transitions is None` **and** `initial is None`: no state
   machine declared; continue.
3. If `transitions is not None` **and** `enum is None`: raise
   `ValidationError` (D214a).
4. If `initial is not None` **and** `enum is None`: raise
   `ValidationError` ("Kind '<kind>': field '<prop>' declares 'initial' without 'enum'").
5. If `initial is not None` **and** `initial not in enum`: raise
   `ValidationError` (D214d).
6. If `transitions is not None`:
   - For each key `k` in `transitions`: if `k != "*"` and `k not in enum`,
     raise `ValidationError` (D214b).
   - For each target `t` in `transitions[k]`: if `t == "*"`, raise
     `ValidationError` (D204 — `*` may not appear as a destination);
     if `t not in enum`, raise `ValidationError` (D214c).
7. Build a `StateMachineDef` with the parsed values
   (`transitions=None` when omitted, `{}` when declared empty).

### 4.3 Step ordering inside `_load_vault_kinds`

State-machine parsing happens **after** `x-storage` / `x-manifest-name`
checks and **before** the `out.append(KindDef(...))` call. The
parse is pure-functional over `schema` and never touches the
filesystem.

---

## 5. Write-Time Enforcement

### 5.1 `core/transitions.py` — shared helper

```python
# src/artifacts_os/core/transitions.py
from __future__ import annotations
from artifacts_os.core.errors import ValidationError
from artifacts_os.core.models import KindDef, StateMachineDef


def check_create(kd: KindDef, fields: dict) -> dict:
    """Validate and default the `initial` value for every state-machined
    property at create time (D203 + D223). Returns a *possibly augmented*
    fields dict with `initial` defaults injected.

    Raises ValidationError if any property is set to a value other than
    its declared `initial`."""
    out = dict(fields)
    for prop, sm in kd.state_machines.items():
        if sm.initial is None:
            continue  # property has transitions but no initial — D206-like; skip
        if prop in out:
            if out[prop] != sm.initial:
                raise ValidationError(
                    f"Illegal initial value for field {prop!r}: "
                    f"{out[prop]!r} (must be {sm.initial!r})"
                )
        else:
            out[prop] = sm.initial
    return out


def check_transition(kd: KindDef, prop: str, current, target) -> None:
    """Validate one update edge against the property's state machine
    (D209 + D212). No-op when the property has no state machine,
    or when current == target (D-implicit).

    Raises ValidationError on rejection."""
    sm = kd.state_machines.get(prop)
    if sm is None:
        return
    if current == target:
        return
    transitions = sm.transitions
    if transitions is None:
        # enum-only declaration (D206): membership is enforced elsewhere
        return
    explicit = list(transitions.get(current, ()))
    wildcard = list(transitions.get("*", ()))
    allowed = explicit + [w for w in wildcard if w not in explicit]
    if target not in allowed:
        msg = (
            f"Illegal transition for field {prop!r}: "
            f"{current!r} → {target!r} (allowed targets: {explicit})"
        )
        if wildcard:
            msg += f" (allowed from any state: {wildcard})"
        raise ValidationError(msg)
```

Pure module. No I/O, no events. `store.py` and `validate.py`
both import from it.

### 5.2 `core/store.py` integration

**`create` path** — augment fields immediately after `kd = registry.get(kind)`:

```python
from artifacts_os.core.transitions import check_create

kd = registry.get(kind)
fields = check_create(kd, fields)  # NEW: D203 + D223
# ... existing slug / id allocation ...
fm_dict: dict = {"kind": kind, "id": aid, "name": slug, **fields}
_validate_schema(kd, fm_dict)
```

**`update` path** — replace the existing single-property
status check at line 254 with a generic loop over all state-
machined properties:

```python
from artifacts_os.core.transitions import check_transition

# ... existing meta / kd resolution ...

# Build the prospective new frontmatter the same way as today.
new_meta: dict = {**meta, **fields}
if status is not None:
    new_meta["status"] = status

# NEW: check every state-machined property whose value would change.
for prop in kd.state_machines:
    if meta.get(prop) != new_meta.get(prop):
        check_transition(kd, prop, meta.get(prop), new_meta.get(prop))

# (The legacy `status not in kd.statuses` check at line 254 is REMOVED.
#  `check_transition` covers `target ∈ enum` implicitly because the
#  legal-target set is built from the transition table, whose entries
#  are guaranteed `⊆ enum` by the load-time check. For properties with
#  enum-only declarations (D206), JSON Schema validation via
#  `_validate_schema` still enforces `target ∈ enum`.)

_validate_schema(kd, new_meta)
```

The `_validate_schema` call still runs after `check_transition`,
so the union of (transition table + JSON Schema enum) governs
the legal set. The legacy single-purpose status check is
removed — `check_transition` subsumes it for `status` and
generalises to every property.

### 5.3 `core/validate.py` Rule 3 extension

Today's Rule 3 (line 110) checks `status ∈ kd.statuses` for a
single property. It is extended to iterate every state-machined
property and use `check_transition`-equivalent logic, with one
key difference: `validate_one` works on a **static frontmatter
dict**, not a `(from, to)` pair. There is no "before" value to
compare against.

Resolution: `validate_one` checks only the **membership** half
of the contract — the value in `fm[prop]` must be in
`sm.enum`. The transition half is **not** checkable here
(`validate_one` does not know what the previous value was) and
is left to `store.update`. The Rule 3 message is updated to
mention the property name explicitly, in the same family as
D212:

```
"Invalid value 'foo' for field 'status' — valid: backlog, ready, …"
```

(replacing the current `"Unknown status 'foo' — valid: …"` for
`status` and extending the same check to every state-machined
property).

This is the documented limit of `validate_one`'s reach: it
catches drift in stored files (someone hand-edited the file to
an invalid value), not illegal-transition history.

### 5.4 Event invariants (D217)

- `artifact.updated` payload: unchanged. `changed` / `before` /
  `after` already carry the diff for every property; consumers
  that want to react to a `status: in-progress → review`
  transition read it from the payload.
- `artifact.status_changed`: unchanged. Continues to fire for
  `status` specifically. Per s0025 §C2 the catalogue is closed;
  no `field.transitioned` event is added.
- Pre-phase: no new hook surface. A transition rejection raises
  `ValidationError` from `store.update` before `_dispatch_pre`
  fires, so blocking pre-hooks see only writes that have passed
  the substrate's transition check.

### 5.5 Confirmed by research

The decision in §5.4 was opened as a default position pending
[[t0188-research-property-change-event-design]]. That research
evaluated three candidate event-structures (a parameterised
`artifact.field_changed`, an implicit-tiering `artifact.transitioned`
derived from the presence of `transitions:`, and subscriber-side
filtering only) against five concrete consumer scenarios.

**Outcome:** [[artifacts/research/r0006-property-change-event-design]]
recommends **Option C — subscriber-side filtering, no new event
types.** D217 is confirmed unchanged: `artifact.updated` and
`artifact.status_changed` cover every surveyed consumer scenario,
and the closed catalogue (s0025 §C2) is preserved at zero cost.

The single landing artefact from the research is a `property:`
hook-matcher key — a *matcher-schema* change captured against
s0025 / s0032, **not** against this spec. The implementer of
t0186 ships the event invariants described in §5.4 verbatim and
does not touch the event catalogue.

If a future architect later judges that the `status`-only
asymmetry is unacceptable as per-property state machines
proliferate, Option B (`artifact.transitioned`, derived cleanly
from the `transitions:` keyword introduced by this spec) is the
smallest viable catalogue addition. The research artifact
contains the catalogue diff and migration story; no work is
required for it at this time.

---

## 6. Error Shape

All three error families share the same `"<noun> for field '<prop>': …"`
preamble so log-grepping operators can pivot on one substring.

| Family | Surface | Format |
|--------|---------|--------|
| Load-time, missing enum | `Registry._load_vault_kinds` | `"Kind '<kind>': field '<prop>' declares 'transitions' without 'enum'"` |
| Load-time, key not in enum | `Registry._load_vault_kinds` | `"Kind '<kind>': field '<prop>' transitions key '<key>' is not in enum [a, b, c]"` |
| Load-time, RHS not in enum | `Registry._load_vault_kinds` | `"Kind '<kind>': field '<prop>' transitions['<key>'] target '<target>' is not in enum [a, b, c]"` |
| Load-time, initial not in enum | `Registry._load_vault_kinds` | `"Kind '<kind>': field '<prop>' initial '<value>' is not in enum [a, b, c]"` |
| Load-time, wildcard as destination | `Registry._load_vault_kinds` | `"Kind '<kind>': field '<prop>' transitions['<key>'] target '*' is not allowed (wildcard is source-only)"` |
| Create-time, wrong initial | `store.create` via `check_create` | `"Illegal initial value for field '<prop>': '<value>' (must be '<initial>')"` |
| Update-time, illegal transition | `store.update` via `check_transition` | `"Illegal transition for field '<prop>': '<current>' → '<target>' (allowed targets: [a, b]) (allowed from any state: [c])"` |
| Validate-time, value not in enum | `validate.validate_one` Rule 3 | `"Invalid value '<value>' for field '<prop>' — valid: a, b, c"` |

All raise `ValidationError` (or surface as `ValidationIssue`
with `severity="error"` in the `validate_one` case). All map to
CLI exit code 2.

---

## 7. Edge Cases

### 7.1 Property declared but absent from artifact

State machine on `priority`; an existing artifact has no
`priority:` field. Update sets `priority=high`.

- Membership: `high ∈ enum` — passes via `_validate_schema`.
- Transition: `current = None`, `target = "high"`. Today's
  semantic: `transitions.get(None, ())` returns `()` →
  `check_transition` would reject.

**Decision (added under D222):** when `current is None` (the
property was not in the old frontmatter), treat the write as a
**create-for-that-property** rather than an update. `check_transition`
returns early if `current is None` **and** the property's
`initial` is `None` (no opinion on first set). If `initial` is
declared and the new value differs from `initial`, the write
fails with the D213 create-time error (`"Illegal initial value for field '<prop>': '<target>' (must be '<initial>')"`).

This makes the contract symmetric: the first set of any property
is governed by `initial` (if any); subsequent sets are governed
by `transitions` (if any).

### 7.2 `update` that unsets a property

If `update` is asked to set a property to `None` (e.g.
explicit `fields={"phase": None}`) and the property has a
state machine, `check_transition` is invoked with `target=None`.
This is rejected: `None ∉ enum`, and `None ∉ transitions[*]`.

Spec position: **deletion of a state-machined property is not
supported by `update`**. Operators who need to clear a field
must do so by direct file edit (as they would today to satisfy
any other schema constraint). A future task may add a
"`deletable: true`" property keyword, but that is out of scope
here (D220).

### 7.3 Multiple state-machined properties in one update

`update(... fields={"status": "review", "phase": "build"})`.
`store.update` iterates `kd.state_machines` in dict-insertion
order. Each property's transition is checked independently.
The first rejection raises; later properties are not checked.

Spec position: **fail-fast on the first violation**. The
operator fixes one error at a time; the alternative
(collect-all-then-report) is appropriate for `validate_one`
but not for a write path where the goal is "either the write
goes through, or nothing changes".

### 7.4 Updating to the same value

`update(... status="in-progress")` when the artifact is already
`in-progress`. `check_transition` short-circuits when
`current == target` (no-op). The write proceeds, the file is
re-written (idempotent), and `artifact.updated` fires with
`changed=[]`.

This matches today's behaviour and avoids a class of false-
positive rejection error ("you can't transition to yourself"
which is technically true but operationally useless).

### 7.5 Property with `initial` but no `transitions`

```jsonc
"workflow": {
  "enum": ["new", "active", "archived"],
  "initial": "new"
}
```

By D206 + D203: `initial` strictness applies at create time;
update accepts any enum value. The contract carves out
"opt into initial-strictness without opting into transition
enforcement" as a meaningful intermediate. The shared helper
treats this via `sm.transitions is None → no transition
check` while still defaulting/enforcing `initial`.

---

## 8. Decomposition Plan

Per D221, the parent task ([[t0186-add-declarative-per-property-state]])
should be decomposed into three sequential implementation
sub-tasks. The recommended split:

| # | Sub-task | Scope |
|---|----------|-------|
| 1 | "Parse `enum + initial + transitions` into `KindDef.state_machines`" | New `StateMachineDef` dataclass in `models.py`; `KindDef.state_machines` field; `_parse_state_machines` helper inside `registry.py`; load-time cross-check (D208 + §4); tests for each of the five failure modes (D214 + D204 destination-wildcard). No write-path changes. |
| 2 | "Enforce per-property transitions at write time" | New `core/transitions.py` (`check_create`, `check_transition`); `store.create` invokes `check_create`; `store.update` replaces the legacy single-property status check with the generic transition loop; `validate.py` Rule 3 extended to every state-machined property (D209 + §5). Tests for D203 create-strictness, D205 wildcard-not-from-creation, D207 empty-transitions-locks, D222 missing-row-is-terminal, §7.1 first-set-of-absent-property. |
| 3 | "Migrate `task/kind.json` + docs" | Ship the permissive `task/kind.json` table (D218 + §2.1); update `docs/adding-a-kind.md` (new subsection); update `src/artifacts_os/core/README.md` (KindDef + StateMachineDef + import line); add a smoke test that exercises the end-to-end loop on the new `task` schema (create `task` → update `status` → verify it works). |

Each sub-task is owned by `developer`, parents back to
[[t0186-add-declarative-per-property-state]], and ships its own
tests. The audit edit (D224) is a separate sibling task.

---

## 9. Documentation Deltas (D219)

The implementer ships the following doc changes **in the same
commit** as the code:

### 9.1 `docs/adding-a-kind.md`

New subsection under `## kind.json — Schema Reference`, titled
**"Property-Level State Machines"**. Contains:

- One-line statement of the contract (D201).
- The three keywords (`enum`, `initial`, `transitions`) and what
  each does.
- The wildcard rule (D204 + D205).
- The strict-`initial` rule (D203).
- The "no `transitions:` ↔ unrestricted" rule (D206).
- The empty-`transitions: {}` rule (D207).
- One worked example matching §2.2 above (or a smaller variant).
- A reference to `core/README.md` for the `StateMachineDef`
  dataclass.

The existing trailing line in §"Optional Follow-Up" — *"Lifecycle
transitions (who may move an artifact from one status to another)
are the concern of the host application"* — is rewritten to
distinguish *declared* transitions (substrate, this spec) from
*relational* transitions (harness, still openstation): see D220.

### 9.2 `src/artifacts_os/core/README.md`

- The `## Public API` import block gains `StateMachineDef`.
- The `### Models` table gains a `StateMachineDef` row.
- A new subsection under `### Models`, titled **"Per-Property
  State Machines"**, summarises the contract and references
  `docs/adding-a-kind.md` for the schema syntax.

### 9.3 Out of this commit

- `r0001-openstation-integration-audit` §3.1 / §6: D224 sibling task.
- Any openstation-side adoption of the substrate enforcement
  (e.g. retiring openstation's `TRANSITIONS` table once
  `task/kind.json` ships a restrictive table): not landed by this
  spec; future task.

---

## 10. Verification Mapping (back to t0186's checklist)

| t0186 verification item | Where this spec settles it |
|--------------------------|----------------------------|
| New kind with `enum + initial + transitions` loads cleanly via `Registry` | §4 + D211 |
| `transitions:` referencing value not in `enum` fails at schema load with a clear error | §4 + §6 (D214b/D214c rows) |
| `artifacts create … --fields foo=<illegal-initial>` fails with named field + legal value | §5.2 (create) + §6 (D213 row) + D203 |
| `artifacts update <ref> --status <illegal-target>` fails with named field, current value, legal targets | §5.2 (update) + §6 (transition row) + D212 |
| Update from `A` to `B` where `B ∈ transitions["*"]` succeeds even though `B ∉ transitions[A]` | §5.1 (`allowed = explicit + wildcard`) + D204 |
| Property without `transitions:` still accepts any enum value | D206 + §5.1 (`transitions is None → no transition check`) |
| `artifact.updated` and `artifact.status_changed` fire as today; no new event types | D217 + §5.4 |
| `docs/adding-a-kind.md` + `core/README.md` document the shape with a worked example | §9 + D219 |

Every verification item from t0186 has a concrete answer above.
No "TBD" entries.

---

## 11. Open-Question Disposition

t0186 §"Open questions" → spec resolution:

| t0186 open question | Spec resolution |
|---------------------|-----------------|
| Initial state semantics (default-on-omit vs. strict) | **Strict + default-on-omit** (D203 + D223). |
| Wildcard interaction with `initial` | **`*` not reachable from creation** (D205). |
| Property type scope for v1 | **Enum-only** (D216); door not closed. |
| Empty `transitions: {}` semantics | **Legal; locks field at `initial`** (D207 + D222 terminal-state). |
| Schema vendor keyword | **Bare** (`initial`, `transitions`) — D202. |
| Validator surface (`validate` vs `store` vs both) | **Both**, via shared `core/transitions.py` (D209 + D210). |
| `KindDef` shape | **New `state_machines: dict[str, StateMachineDef]` field** (D211). |
| Schema-shape preference (three siblings vs nested object) | **Three siblings** (D201). |
| `StateMachineDef` dataclass public shape | **Frozen dataclass with `enum`, `initial`, `transitions`** (§3.1). |
| Migration of `task/kind.json` (ship permissive vs. ship empty) | **Ship permissive in the same task** (D218). |

---

## 12. Out of Scope (D220)

Re-stated so future scope creep can be rejected by reference:

1. **Cross-property guards.** Rules like "cannot move `status` to
   `done` while `priority: critical`" are relational and stay in
   the hooks layer (openstation expresses them as `host: openstation`
   pre-phase blocking hooks).
2. **Relational rules.** Subtask blocking, `depends_on`,
   ownership/role checks, checklist parsing — all higher-layer
   concerns. The substrate provides the event payload (D217)
   that lets these rules live in hooks.
3. **Auto-recording timestamps on transition.** `started` /
   `completed` writes on entry to `in-progress` / `done` are
   harness policy, not substrate behaviour.
4. **Numeric and boolean state machines.** D216 — defer until a
   real consumer asks.
5. **A `from: *` matching everywhere as a default.** The wildcard
   is source-only and additive (D204). A "default from any state"
   form would be redundant with the existing per-state rows and
   adds an ordering question (does the per-state row override?).

---

## 13. References

- Parent task: [[t0186-add-declarative-per-property-state]]
- Spec sub-task (this artifact): [[t0187-spec-declarative-per-property-state]]
- Event-design pressure-test: [[t0188-research-property-change-event-design]] →
  [[artifacts/research/r0006-property-change-event-design]] (confirms D217)
- Audit informing the carve-out: [[r0001-openstation-integration-audit]] §3.1, §6
- Event catalogue invariants: [[s0025-artifact-events]] §C2
- Kind-folder schema reference: `docs/adding-a-kind.md`
- Core public API: `src/artifacts_os/core/README.md`
- Existing membership check (today's behaviour being generalised):
  `src/artifacts_os/core/store.py:254` and
  `src/artifacts_os/core/validate.py:110`
