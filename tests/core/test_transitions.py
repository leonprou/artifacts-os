"""Tests for core/transitions.py — per-property state-machine enforcement.

Covers:
- parse_state_machines: five load-time failure conditions (D214a–d + D204)
- check_create: D203 strict-initial, D223 default injection, D206 enum-only
- check_transition: legal/illegal targets, wildcard (D205), terminal state
  (D222), locked field (D207), enum-only (D206), first-set-of-absent (§7.1)

No mocking — pure unit tests on helpers directly.

Spec: s0033-declarative-per-property-state-machines
"""

import pytest

from artifacts_os.core.errors import ValidationError
from artifacts_os.core.models import KindDef, StateMachineDef
from artifacts_os.core.transitions import (
    check_create,
    check_transition,
    membership_error_msg,
    parse_state_machines,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kd(state_machines: dict[str, StateMachineDef] | None = None) -> KindDef:
    return KindDef(
        name="widget",
        dir="widgets",
        prefix="w",
        numbered=True,
        state_machines=state_machines or {},
    )


def _sm(
    enum: tuple[str, ...],
    initial: str | None,
    transitions: dict[str, tuple[str, ...]] | None,
) -> StateMachineDef:
    return StateMachineDef(enum=enum, initial=initial, transitions=transitions)


# ---------------------------------------------------------------------------
# parse_state_machines — load-time cross-check
# ---------------------------------------------------------------------------


def test_parse_clean_state_machine() -> None:
    """Well-formed schema with enum + initial + transitions parses cleanly."""
    schema = {
        "properties": {
            "status": {
                "enum": ["a", "b", "c"],
                "initial": "a",
                "transitions": {
                    "a": ["b"],
                    "b": ["a", "c"],
                    "c": [],
                    "*": ["a"],
                },
            }
        }
    }
    result = parse_state_machines(schema, "mykind")
    assert "status" in result
    sm = result["status"]
    assert sm.enum == ("a", "b", "c")
    assert sm.initial == "a"
    assert sm.transitions is not None
    assert sm.transitions["a"] == ("b",)
    assert sm.transitions["*"] == ("a",)


def test_parse_enum_only_no_state_machine() -> None:
    """Property with enum but no initial/transitions → no state machine built."""
    schema = {
        "properties": {
            "priority": {"enum": ["low", "high"]},
        }
    }
    result = parse_state_machines(schema, "mykind")
    assert result == {}


def test_parse_no_properties() -> None:
    """Schema with no properties section → empty dict."""
    result = parse_state_machines({}, "mykind")
    assert result == {}


# D214a — transitions without enum
def test_parse_transitions_without_enum_raises() -> None:
    """D214a: transitions declared without enum → ValidationError."""
    schema = {
        "properties": {
            "status": {
                "transitions": {"a": ["b"]},
            }
        }
    }
    with pytest.raises(ValidationError) as exc_info:
        parse_state_machines(schema, "mykind")
    msg = str(exc_info.value)
    assert "mykind" in msg
    assert "status" in msg
    assert "transitions" in msg
    assert "enum" in msg


# D214b — transition key not in enum
def test_parse_transition_key_not_in_enum_raises() -> None:
    """D214b: transitions key not in enum → ValidationError."""
    schema = {
        "properties": {
            "status": {
                "enum": ["a", "b"],
                "transitions": {
                    "a": ["b"],
                    "bogus": ["a"],  # not in enum
                },
            }
        }
    }
    with pytest.raises(ValidationError) as exc_info:
        parse_state_machines(schema, "mykind")
    msg = str(exc_info.value)
    assert "mykind" in msg
    assert "status" in msg
    assert "bogus" in msg
    assert "enum" in msg


# D214c — transition RHS target not in enum
def test_parse_transition_target_not_in_enum_raises() -> None:
    """D214c: transitions target not in enum → ValidationError."""
    schema = {
        "properties": {
            "status": {
                "enum": ["a", "b"],
                "transitions": {
                    "a": ["b", "zzz"],  # zzz not in enum
                },
            }
        }
    }
    with pytest.raises(ValidationError) as exc_info:
        parse_state_machines(schema, "mykind")
    msg = str(exc_info.value)
    assert "mykind" in msg
    assert "status" in msg
    assert "zzz" in msg
    assert "enum" in msg


# D214d — initial not in enum
def test_parse_initial_not_in_enum_raises() -> None:
    """D214d: initial value not in enum → ValidationError."""
    schema = {
        "properties": {
            "status": {
                "enum": ["a", "b"],
                "initial": "zzz",  # not in enum
                "transitions": {"a": ["b"]},
            }
        }
    }
    with pytest.raises(ValidationError) as exc_info:
        parse_state_machines(schema, "mykind")
    msg = str(exc_info.value)
    assert "mykind" in msg
    assert "status" in msg
    assert "zzz" in msg
    assert "enum" in msg


# D204 — wildcard as destination
def test_parse_wildcard_as_destination_raises() -> None:
    """D204: '*' in transitions RHS → ValidationError (wildcard is source-only)."""
    schema = {
        "properties": {
            "status": {
                "enum": ["a", "b"],
                "transitions": {
                    "a": ["*"],  # invalid
                },
            }
        }
    }
    with pytest.raises(ValidationError) as exc_info:
        parse_state_machines(schema, "mykind")
    msg = str(exc_info.value)
    assert "mykind" in msg
    assert "status" in msg
    assert "wildcard is source-only" in msg


# D215 — wildcard may appear as a source key
def test_parse_wildcard_source_key_is_valid() -> None:
    """D215: '*' as a transitions key is valid (source-only semantics)."""
    schema = {
        "properties": {
            "status": {
                "enum": ["a", "b", "cancelled"],
                "initial": "a",
                "transitions": {
                    "a": ["b"],
                    "*": ["cancelled"],
                },
            }
        }
    }
    result = parse_state_machines(schema, "mykind")
    assert result["status"].transitions["*"] == ("cancelled",)


def test_parse_initial_only_no_transitions() -> None:
    """Property with initial but no transitions → state machine built (D206 + D203)."""
    schema = {
        "properties": {
            "workflow": {
                "enum": ["new", "active", "archived"],
                "initial": "new",
            }
        }
    }
    result = parse_state_machines(schema, "mykind")
    assert "workflow" in result
    sm = result["workflow"]
    assert sm.initial == "new"
    assert sm.transitions is None  # unrestricted updates (D206)


def test_parse_empty_transitions_dict() -> None:
    """Empty transitions dict is valid (D207 — locks field at initial)."""
    schema = {
        "properties": {
            "category": {
                "enum": ["x", "y"],
                "initial": "x",
                "transitions": {},
            }
        }
    }
    result = parse_state_machines(schema, "mykind")
    assert result["category"].transitions == {}


# ---------------------------------------------------------------------------
# check_create — D203 + D223
# ---------------------------------------------------------------------------


def _sm_full() -> StateMachineDef:
    """A state machine with initial='a' and permissive transitions."""
    return _sm(
        enum=("a", "b", "c"),
        initial="a",
        transitions={"a": ("b", "c"), "b": ("a", "c"), "c": ("a", "b")},
    )


def test_check_create_injects_initial() -> None:
    """D223: omitted state-machined property gets initial injected."""
    kd = _kd({"status": _sm_full()})
    out = check_create(kd, {})
    assert out["status"] == "a"


def test_check_create_accepts_initial_value() -> None:
    """Setting status=initial at create is legal."""
    kd = _kd({"status": _sm_full()})
    out = check_create(kd, {"status": "a"})
    assert out["status"] == "a"


def test_check_create_rejects_non_initial() -> None:
    """D203: setting status to a non-initial value at create raises ValidationError."""
    kd = _kd({"status": _sm_full()})
    with pytest.raises(ValidationError) as exc_info:
        check_create(kd, {"status": "b"})
    msg = str(exc_info.value)
    assert "Illegal initial value" in msg
    assert "status" in msg
    assert "'b'" in msg
    assert "'a'" in msg


def test_check_create_enum_only_no_initial() -> None:
    """D206: property with enum but no initial → check_create imposes no restriction."""
    sm = _sm(enum=("x", "y", "z"), initial=None, transitions={"x": ("y",)})
    kd = _kd({"phase": sm})
    # Any value is OK and no injection happens
    out = check_create(kd, {"phase": "z"})
    assert out["phase"] == "z"


def test_check_create_enum_only_no_transitions() -> None:
    """D206: enum-only (no transitions) property accepts any value at create."""
    sm = _sm(enum=("new", "active", "archived"), initial=None, transitions=None)
    kd = _kd({"workflow": sm})
    out = check_create(kd, {"workflow": "archived"})
    assert out["workflow"] == "archived"


def test_check_create_empty_transitions_locks_at_initial() -> None:
    """D207: empty transitions — create must use initial."""
    sm = _sm(enum=("x", "y"), initial="x", transitions={})
    kd = _kd({"category": sm})
    # Setting to initial is OK
    out = check_create(kd, {"category": "x"})
    assert out["category"] == "x"
    # Setting to anything else fails
    with pytest.raises(ValidationError):
        check_create(kd, {"category": "y"})


def test_check_create_no_state_machines_passthrough() -> None:
    """Kind with no state machines: check_create is a no-op."""
    kd = _kd({})
    fields = {"status": "any-value", "priority": "high"}
    out = check_create(kd, fields)
    assert out == fields


def test_check_create_preserves_other_fields() -> None:
    """Non-state-machined fields are passed through unchanged."""
    kd = _kd({"status": _sm_full()})
    out = check_create(kd, {"title": "my task", "assignee": "alice"})
    assert out["title"] == "my task"
    assert out["assignee"] == "alice"
    assert out["status"] == "a"  # injected


# ---------------------------------------------------------------------------
# check_transition — D209 + D212 + §7.1 + D205 + D222 + D207
# ---------------------------------------------------------------------------


def _kd_with_sm(sm: StateMachineDef, prop: str = "status") -> KindDef:
    return _kd({prop: sm})


def _sm_restrictive() -> StateMachineDef:
    """scope → design → build → ship; retired is terminal; any → retired via *."""
    return _sm(
        enum=("scope", "design", "build", "ship", "retired"),
        initial="scope",
        transitions={
            "scope": ("design",),
            "design": ("scope", "build"),
            "build": ("design", "ship"),
            "ship": ("build", "retired"),
            "retired": (),
            "*": ("retired",),
        },
    )


def test_check_transition_legal_target_accepted() -> None:
    """Legal transition: scope → design does not raise."""
    kd = _kd_with_sm(_sm_restrictive())
    check_transition(kd, "status", "scope", "design")  # should not raise


def test_check_transition_illegal_target_raises_d212() -> None:
    """D212: illegal transition raises ValidationError with correct message."""
    kd = _kd_with_sm(_sm_restrictive())
    with pytest.raises(ValidationError) as exc_info:
        check_transition(kd, "status", "scope", "ship")
    msg = str(exc_info.value)
    assert "Illegal transition" in msg
    assert "status" in msg
    assert "scope" in msg
    assert "ship" in msg


def test_check_transition_wildcard_additive() -> None:
    """D205/D204: target in transitions['*'] is accepted even if not in transitions[current]."""
    kd = _kd_with_sm(_sm_restrictive())
    # "scope" → "retired" is only legal via wildcard, not via transitions["scope"]
    check_transition(kd, "status", "scope", "retired")  # must not raise


def test_check_transition_wildcard_clause_in_message() -> None:
    """D212: wildcard clause appears in error message when non-empty."""
    kd = _kd_with_sm(_sm_restrictive())
    with pytest.raises(ValidationError) as exc_info:
        check_transition(kd, "status", "scope", "build")
    msg = str(exc_info.value)
    assert "allowed from any state" in msg


def test_check_transition_no_wildcard_clause_when_empty() -> None:
    """D212: wildcard clause omitted from error message when empty."""
    sm = _sm(
        enum=("a", "b", "c"),
        initial="a",
        transitions={"a": ("b",), "b": ("a",)},
    )
    kd = _kd_with_sm(sm)
    with pytest.raises(ValidationError) as exc_info:
        check_transition(kd, "status", "a", "c")
    msg = str(exc_info.value)
    assert "allowed from any state" not in msg


def test_check_transition_terminal_state_d222() -> None:
    """D222: state with no row in transitions → only wildcard targets reachable."""
    kd = _kd_with_sm(_sm_restrictive())
    # "retired" has an empty tuple in transitions, so no explicit exits.
    # Wildcard target "retired" is the only allowed target, but current==target → no-op.
    # An attempt to go anywhere else from "retired" fails.
    with pytest.raises(ValidationError):
        check_transition(kd, "status", "retired", "scope")


def test_check_transition_locked_field_d207() -> None:
    """D207: empty transitions dict locks field at initial; any change fails."""
    sm = _sm(enum=("x", "y"), initial="x", transitions={})
    kd = _kd_with_sm(sm, "category")
    with pytest.raises(ValidationError) as exc_info:
        check_transition(kd, "category", "x", "y")
    msg = str(exc_info.value)
    assert "Illegal transition" in msg
    assert "category" in msg


def test_check_transition_same_value_is_noop() -> None:
    """§7.4: transition to same value does not raise (idempotent)."""
    sm = _sm(enum=("a", "b"), initial="a", transitions={"a": ("b",)})
    kd = _kd_with_sm(sm)
    check_transition(kd, "status", "a", "a")  # must not raise


def test_check_transition_enum_only_no_transitions_d206() -> None:
    """D206: enum-only property (no transitions) accepts any enum value on update."""
    sm = _sm(enum=("new", "active", "archived"), initial=None, transitions=None)
    kd = _kd_with_sm(sm, "workflow")
    # Any transition is fine
    check_transition(kd, "workflow", "new", "archived")  # must not raise
    check_transition(kd, "workflow", "archived", "new")  # must not raise


def test_check_transition_no_state_machine_for_prop_noop() -> None:
    """Property with no state machine → check_transition is a no-op."""
    kd = _kd({})
    check_transition(kd, "anything", "old", "new")  # must not raise


def test_check_transition_first_set_absent_prop_with_initial() -> None:
    """§7.1: current=None + initial declared → only initial is legal first value."""
    sm = _sm(enum=("a", "b"), initial="a", transitions={"a": ("b",)})
    kd = _kd_with_sm(sm)
    # Setting to initial is OK
    check_transition(kd, "status", None, "a")  # must not raise
    # Setting to non-initial fails
    with pytest.raises(ValidationError) as exc_info:
        check_transition(kd, "status", None, "b")
    msg = str(exc_info.value)
    assert "Illegal initial value" in msg
    assert "status" in msg


def test_check_transition_first_set_absent_prop_no_initial() -> None:
    """§7.1: current=None + no initial → any value accepted (no opinion on first set)."""
    sm = _sm(enum=("x", "y"), initial=None, transitions={"x": ("y",)})
    kd = _kd_with_sm(sm)
    check_transition(kd, "status", None, "y")  # must not raise


def test_check_transition_status_as_degenerate_case() -> None:
    """Status state machine works like any other property via check_transition."""
    sm = _sm(
        enum=("backlog", "done"),
        initial="backlog",
        transitions={"backlog": ("done",)},
    )
    kd = _kd({"status": sm})
    check_transition(kd, "status", "backlog", "done")  # legal
    with pytest.raises(ValidationError):
        check_transition(kd, "status", "done", "backlog")  # no reverse edge


# ---------------------------------------------------------------------------
# membership_error_msg helper
# ---------------------------------------------------------------------------


def test_membership_error_msg_format() -> None:
    msg = membership_error_msg("status", "wip", ("backlog", "ready"))
    assert "status" in msg
    assert "wip" in msg
    assert "backlog" in msg
    assert "ready" in msg
