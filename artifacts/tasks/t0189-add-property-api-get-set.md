---
assignee: developer
created: 2026-05-25
depends_on:
- '[[t0186-add-declarative-per-property-state]]'
id: t0189
kind: task
name: add-property-api-get-set
owner: user
status: done
type: feature
---

# Add Property Api Get Set Transitions Cli Verbs

# Add property API: `artifacts get`, `set`, `transitions` CLI verbs

## User story

> **As an agent or operator working with state-machined artifacts, I want flat `get`, `set`, and `transitions` CLI verbs (plus their Python equivalents) so that I can read a single property, write a single property with transition validation, and discover what transitions are legal from the current value — without parsing `kind.json` or running `update` for one-field writes.**

## Why

[[t0186-add-declarative-per-property-state]] (settled by [[openstation/specs/s0033-declarative-per-property-state-machines]]) gives the substrate transition validation on every write through `store.update`. The Python and CLI surface for *querying* a property, *reading* the legal next set, and *writing* a single property with transition-aware error messages is currently a gap:

- `artifacts show` returns the whole frontmatter + body; there's no single-property read.
- `artifacts update --status review` works but is multi-field-shaped; the error family reads as "validation" rather than the more specific "transition".
- There's no way to ask the CLI "what can `status` move to from here?" — agents have to read `kind.json` and the spec to know.
- Python consumers (openstation, dashboards, future agents) re-implement the same query against `KindDef.state_machines` rather than calling a single helper.

Option A from the architect's design exploration (chat log, 2026-05-25): three new flat verbs (`get`, `set`, `transitions`) plus the Python equivalents, exposing the data already present on `KindDef.state_machines` and the helper logic already in `core/transitions.py` (per s0033 §5.1).

`set` writes through `store.update` and therefore inherits the full write-time validation pipeline — schema rules from `core/validate.py` plus the transition check introduced by t0186. There is no "fast path" that skips checks; `set` is a single-property convenience surface, not a validation bypass.

## Directions

Intent, not contract. The substrate is already settled; this task is the UX layer.

### CLI surface

Three new flat top-level verbs. Match the conventions in `CLAUDE.md` § "CLI Conventions" (flat verbs, filter flags at top level, default Rich table + `--json/-j` for scripting):

- `artifacts get <ref> <property>` → prints the value. `--json` returns `{"property": ..., "value": ...}`.
- `artifacts get <ref>` (no property) → prints all frontmatter as a key-value table (no body, unlike `show`).
- `artifacts set <ref> <property> <value>` → writes the single property. Validates per s0033 §5.2: transition check for state-machined props, schema check for all. Free-form properties are allowed (no strict restriction to state-machined ones in v1 — see open question 1).
- `artifacts transitions <ref>` → all state-machined properties, table form: `property | current | allowed_next | wildcard_targets | locked?`. `--json` returns the structured map.
- `artifacts transitions <ref> <property>` → just one property, same columns. `--json` returns `{"current": ..., "allowed_next": [...], "wildcard_targets": [...], "locked": bool}`.

Error families (`ValidationError` → exit 2 unchanged):

- `set` on a state-machined property with illegal target → use the existing s0033 D212 message (`"Illegal transition for field 'status': 'in-progress' → 'verified' (allowed targets: ['review']) (allowed from any state: ['rejected'])"`).
- `set` on a free-form property → falls through to JSON Schema validation; existing error message.
- `get` / `transitions` on an unknown property name → exit 2 with `"Unknown property '<name>' for kind '<kind>' — known: [...]"`.

### Python surface

`core/__init__.py` re-exports three new public functions:

```python
def get_prop(registry: Registry, ref: str, property: str) -> Any:
    """Resolve ref, return frontmatter[property].
    Raises NotFoundError, ValueError on unknown property."""

def set_prop(registry: Registry, ref: str, property: str, value: Any) -> Artifact:
    """Write a single property. Goes through store.update;
    transition + schema validation per s0033 §5."""

def transitions_for(
    registry: Registry, ref: str, property: str | None = None
) -> dict[str, TransitionView] | TransitionView:
    """Query legal-next-set for one or all state-machined properties.
    Returns TransitionView (single) or dict[property → TransitionView] (all)."""
```

New dataclass `TransitionView` in `core/models.py`:

```python
@dataclass(frozen=True)
class TransitionView:
    property: str
    current: Any                          # current value; None when property absent
    allowed_next: tuple[Any, ...]         # transitions[current] (excludes wildcard for clarity)
    wildcard_targets: tuple[Any, ...]     # transitions["*"]
    locked: bool                          # True iff transitions == {} (s0033 D207)
```

Re-exported from `core` alongside `Artifact`, `ArtifactMeta`, `KindDef`, `StateMachineDef`.

### Module placement

- `get_prop`, `set_prop`: in `src/artifacts_os/core/store.py` (sit alongside `get` and `update`; thin wrappers).
- `transitions_for`, `TransitionView`: `TransitionView` in `core/models.py`; `transitions_for` is a new function in `core/transitions.py` (the module lands as part of t0186 phase 2 per s0033 §5.1).
- CLI verbs: each in its own file in `cli/` mirroring the existing one-verb-one-file pattern.

### Tests

- `tests/core/test_store.py`: round-trip `get_prop` → `set_prop` → verify on the canonical `task` kind.
- `tests/core/test_transitions.py` (extend, or add to t0186 phase 2's): `transitions_for` returns correct view for each state in a state-machined property; correct empty for free-form properties; raises on unknown property.
- `tests/cli/test_get.py`, `test_set.py`, `test_transitions.py`: each verb's happy path, error path, JSON mode, unknown property error, unknown ref error.

### Docs

- `src/artifacts_os/cli/README.md`: new "Property and Transition Verbs" subsection covering all three verbs with worked examples on `task`.
- `src/artifacts_os/core/README.md`: extend the CRUD table with `get_prop`, `set_prop`, `transitions_for`; add `TransitionView` to the Models table.
- No new top-level doc file — these are CLI additions, not new concepts.

## Open questions

1. **Strict `set`?** Should `set` refuse to write properties that have no state machine (i.e., free-form properties)? *Recommendation: non-strict in v1.* Restricting is more surprising than useful — `artifacts set t0187 assignee alice` is an obvious use case. The state-machine path is the value-add; free-form just works through schema validation.
2. **`get` shadowing `show`?** `artifacts show <ref>` already prints everything; `artifacts get <ref>` printing all frontmatter is a near-duplicate. *Recommendation: keep `get <ref>` as a frontmatter-only view (no body); `show` continues to include the body. They differ in scope, not redundantly.*
3. **`transitions` on a non-state-machined property?** What should `artifacts transitions t0187 title` return — error (no state machine on `title`) or a degenerate view (`locked=False`, `allowed_next=()`, meaning "any value")? *Recommendation: error.* The verb name implies state-machine semantics; absence is a user error worth flagging.
4. **CLI verb collision check.** Verify that `get`, `set`, `transitions` don't already exist as flags or subcommands elsewhere in `cli/`. *Quick `grep` confirms no collision today, but developer to re-verify at implementation time.*
5. **Retarget `validate --fix` onto `set_prop`? (follow-on.)** Today `cli/commands/validate.py:60` calls `update(registry, name, fields={"status": ...})` to repair an illegal status. Once `set_prop` lands, the natural implementation is a single `set_prop` call — transition-aware error, one canonical "single-property write" path, no behavioural change. *Recommendation: defer to a small follow-on task after t0186 + t0189 both ship.* Not in scope here; recording so it doesn't get lost.

## Sub-tasks

None proposed at architect time. The work spans CLI (3 verbs) + Python helpers (3 fns + 1 dataclass) + tests + docs — borderline for the 4+ files / 6+ requirements heuristic. The developer may decide to split, e.g.:

- Phase 1: Python `get_prop`, `set_prop`, `TransitionView`, `transitions_for`.
- Phase 2: CLI verbs.
- Phase 3: Docs.

Or land as a single PR — both shapes are defensible. Decompose if the diff exceeds ~400 LoC or if review surface becomes unwieldy.

## Progress

### 2026-05-29 21:15:48 — Incomplete run (r0208)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$1.73, turns=51

## Verification

- `artifacts get t0187 status` prints the current status; `--json` returns `{"property": "status", "value": "in-progress"}`.
- `artifacts get t0187` (no property) prints the frontmatter only (no body), as a Rich key-value table.
- `artifacts set t0187 status review` succeeds when the transition is legal; rejects with the s0033 D212 message when illegal.
- `artifacts set t0187 assignee alice` succeeds for a free-form property (non-strict per OQ 1).
- `artifacts transitions t0187` prints a Rich table listing every state-machined property in the artifact's kind with current value, allowed-next, wildcard targets, and locked flag.
- `artifacts transitions t0187 status` prints just the `status` row; `--json` returns the structured `TransitionView` JSON.
- `artifacts transitions t0187 title` exits with code 2 and `"no state machine declared for field 'title' in kind 'task'"` (OQ 3).
- Python: `from artifacts_os.core import get_prop, set_prop, transitions_for, TransitionView` imports without error; each function is documented in `core/README.md`.
- Doc files (`cli/README.md`, `core/README.md`) include worked examples an operator can copy-paste against the `task` kind.

## Depends on

- [[t0186-add-declarative-per-property-state]] must reach `done` first. The substrate validation and `KindDef.state_machines` field are prerequisites; `core/transitions.py` (delivered by t0186 phase 2 per s0033 §5.1) is the helper this work extends.