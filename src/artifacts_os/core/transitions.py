"""Per-property state-machine enforcement for artifacts-os.

Shared helper consumed by ``core/store.py`` (write-time enforcement)
and ``core/validate.py`` (Rule 3 membership check).  Also contains
the load-time parsing helper called from ``core/registry.py``.

Spec: s0033-declarative-per-property-state-machines § 4–6
"""

from __future__ import annotations

from artifacts_os.core.errors import ValidationError
from artifacts_os.core.models import KindDef, StateMachineDef


# ---------------------------------------------------------------------------
# Error message helpers (D212, D213, D214)
# ---------------------------------------------------------------------------


def _msg_create_initial(prop: str, val: object, initial: str) -> str:
    """D213 — create-time strict-initial rejection."""
    return (
        f"Illegal initial value for field {prop!r}: "
        f"{val!r} (must be {initial!r})"
    )


def _msg_transition(
    prop: str,
    current: object,
    target: object,
    explicit: list[str],
    wildcard: list[str],
) -> str:
    """D212 — write-time transition rejection.

    Wildcard clause is omitted when *wildcard* is empty.
    """
    msg = (
        f"Illegal transition for field {prop!r}: "
        f"{current!r} \u2192 {target!r} (allowed targets: {explicit})"
    )
    if wildcard:
        msg += f" (allowed from any state: {wildcard})"
    return msg


def membership_error_msg(prop: str, val: object, enum: tuple[str, ...]) -> str:
    """Validate-time membership message (Rule 3 in validate.py)."""
    return f"Invalid value {val!r} for field {prop!r} \u2014 valid: {', '.join(enum)}"


# ---------------------------------------------------------------------------
# Load-time parsing (called from registry.py)
# ---------------------------------------------------------------------------


def parse_state_machines(schema: dict, kind_name: str) -> dict[str, StateMachineDef]:
    """Parse per-property state machines from a kind's JSON schema.

    Raises ``ValidationError`` with a D214-family message on any of the five
    load-time failure conditions (D214a–d + D204 destination-wildcard).

    Spec: s0033 § 4.2
    """
    props: dict = schema.get("properties", {})
    result: dict[str, StateMachineDef] = {}

    for prop_name, prop_def in props.items():
        if not isinstance(prop_def, dict):
            continue

        raw_enum = prop_def.get("enum")
        raw_initial = prop_def.get("initial")
        raw_transitions = prop_def.get("transitions")

        # If neither initial nor transitions is declared, no state machine.
        if raw_transitions is None and raw_initial is None:
            continue

        # D214a — transitions declared without enum.
        if raw_transitions is not None and raw_enum is None:
            raise ValidationError(
                f"Kind '{kind_name}': field '{prop_name}' "
                f"declares 'transitions' without 'enum'"
            )

        # Guard: initial declared without enum.
        if raw_initial is not None and raw_enum is None:
            raise ValidationError(
                f"Kind '{kind_name}': field '{prop_name}' "
                f"declares 'initial' without 'enum'"
            )

        enum: tuple[str, ...] = tuple(raw_enum) if raw_enum is not None else ()

        # D214d — initial not in enum.
        if raw_initial is not None and raw_initial not in enum:
            raise ValidationError(
                f"Kind '{kind_name}': field '{prop_name}' "
                f"initial '{raw_initial}' is not in enum [{', '.join(enum)}]"
            )

        # Validate transitions table.
        parsed_transitions: dict[str, tuple[str, ...]] | None = None
        if raw_transitions is not None:
            if not isinstance(raw_transitions, dict):
                raise ValidationError(
                    f"Kind '{kind_name}': field '{prop_name}' "
                    f"'transitions' must be an object"
                )
            parsed_transitions = {}
            for key, targets in raw_transitions.items():
                # D214b — transition key (other than '*') not in enum.
                if key != "*" and key not in enum:
                    raise ValidationError(
                        f"Kind '{kind_name}': field '{prop_name}' "
                        f"transitions key '{key}' is not in enum [{', '.join(enum)}]"
                    )
                if not isinstance(targets, list):
                    raise ValidationError(
                        f"Kind '{kind_name}': field '{prop_name}' "
                        f"transitions['{key}'] must be an array"
                    )
                validated_targets: list[str] = []
                for target in targets:
                    # D204 — wildcard may not appear as a destination.
                    if target == "*":
                        raise ValidationError(
                            f"Kind '{kind_name}': field '{prop_name}' "
                            f"transitions['{key}'] target '*' is not allowed "
                            f"(wildcard is source-only)"
                        )
                    # D214c — target not in enum.
                    if target not in enum:
                        raise ValidationError(
                            f"Kind '{kind_name}': field '{prop_name}' "
                            f"transitions['{key}'] target '{target}' "
                            f"is not in enum [{', '.join(enum)}]"
                        )
                    validated_targets.append(target)
                parsed_transitions[key] = tuple(validated_targets)

        result[prop_name] = StateMachineDef(
            enum=enum,
            initial=raw_initial if isinstance(raw_initial, str) else None,
            transitions=parsed_transitions,
        )

    return result


# ---------------------------------------------------------------------------
# Write-time helpers
# ---------------------------------------------------------------------------


def check_create(kd: KindDef, fields: dict) -> dict:
    """Validate and default the ``initial`` value for every state-machined
    property at create time (D203 + D223).

    Returns a *possibly augmented* ``fields`` dict with ``initial`` defaults
    injected for properties that were omitted from the caller's fields dict.

    Raises ``ValidationError`` (D213) if any property is explicitly set to a
    value other than its declared ``initial``.

    Spec: s0033 § 5.1 (check_create)
    """
    out = dict(fields)
    for prop, sm in kd.state_machines.items():
        if sm.initial is None:
            # Property has enum (+ maybe transitions) but no initial — D206-like.
            # No create-time restriction imposed.
            continue
        if prop in out:
            if out[prop] != sm.initial:
                raise ValidationError(
                    _msg_create_initial(prop, out[prop], sm.initial)
                )
        else:
            out[prop] = sm.initial
    return out


def check_transition(
    kd: KindDef,
    prop: str,
    current: object,
    target: object,
) -> None:
    """Validate one update edge against the property's state machine (D209 + D212).

    No-op when the property has no state machine, or when current == target.

    Edge case §7.1 — ``current is None`` (property absent from old frontmatter):
    treated as a first-set operation governed by ``initial`` (if declared).

    Raises ``ValidationError`` on rejection.

    Spec: s0033 § 5.1 (check_transition), § 7.1
    """
    sm = kd.state_machines.get(prop)
    if sm is None:
        return  # no state machine for this property

    # §7.1 — first set of a previously absent property.
    # §7.5 (recovery) — also treat a corrupt current value (not in enum) like
    # a first-set: the artifact is already broken; the only sane target is
    # ``initial``. Mirrors §7.1 so validate --fix can repair corrupt status
    # without going through a transition row that doesn't exist.
    if current is None or current not in sm.enum:
        if sm.initial is None:
            return  # no opinion on first set
        if target != sm.initial:
            raise ValidationError(
                _msg_create_initial(prop, target, sm.initial)
            )
        return  # target == initial — OK

    if current == target:
        return  # §7.4 — idempotent write

    transitions = sm.transitions
    if transitions is None:
        # Enum-only declaration (D206): membership enforced by JSON Schema.
        return

    explicit = list(transitions.get(current, ()))  # type: ignore[arg-type]
    wildcard = list(transitions.get("*", ()))
    allowed = explicit + [w for w in wildcard if w not in explicit]

    if target not in allowed:
        raise ValidationError(
            _msg_transition(prop, current, target, explicit, wildcard)
        )
