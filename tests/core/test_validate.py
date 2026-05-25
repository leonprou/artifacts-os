"""Unit tests for core/validate.py — validate_one / validate_many.

All tests use ArtifactMeta directly; no file I/O.
"""

from pathlib import Path

import pytest

from artifacts_os.core.models import ArtifactMeta, KindDef, StateMachineDef
from artifacts_os.core.registry import Registry
from artifacts_os.core.validate import validate_one, validate_many, ValidationResult


def _task_status_sm() -> StateMachineDef:
    """The same enum the vault task kind declares (s0033 §5.3)."""
    enum = ("backlog", "ready", "in-progress", "done")
    return StateMachineDef(
        enum=enum,
        initial="backlog",
        transitions={s: enum for s in enum},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _meta(frontmatter: dict, name: str = "t0001-test") -> ArtifactMeta:
    """Build an ArtifactMeta from a raw frontmatter dict."""
    return ArtifactMeta(
        id=frontmatter.get("id", ""),
        kind=frontmatter.get("kind", ""),
        name=name,
        title=frontmatter.get("name", name),
        status=frontmatter.get("status"),
        tags=frontmatter.get("tags", []),
        created=frontmatter.get("created", ""),
        path=Path("/fake/path.md"),
        frontmatter=frontmatter,
    )


def _registry(kinds: list[KindDef] | None = None) -> Registry:
    """Build a Registry from a list of KindDefs (no vault root)."""
    if kinds is None:
        sm = _task_status_sm()
        kinds = [
            KindDef(
                name="task",
                dir="tasks",
                prefix="t",
                numbered=True,
                statuses=list(sm.enum),
                state_machines={"status": sm},
            ),
            KindDef(
                name="agent",
                dir="agents",
                prefix="",
                numbered=False,
                statuses=[],
            ),
        ]
    return Registry(kinds, root=None)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_all_valid():
    """Valid artifact → result.valid == True, issues == []."""
    fm = {"id": "t0001", "kind": "task", "name": "t0001-fix-bug", "created": "2026-01-01", "status": "ready"}
    result = validate_one(_meta(fm), _registry())
    assert result.valid is True
    assert result.issues == []


def test_missing_id():
    """Missing id → error with field='id'."""
    fm = {"kind": "task", "name": "t0001-fix-bug", "created": "2026-01-01", "status": "ready"}
    result = validate_one(_meta(fm, name="t0001-test"), _registry())
    assert any(i.field == "id" and i.severity == "error" for i in result.issues)
    assert result.valid is False


def test_missing_kind():
    """Missing kind → error with field='kind'."""
    fm = {"id": "t0001", "name": "t0001-fix-bug", "created": "2026-01-01", "status": "ready"}
    result = validate_one(_meta(fm), _registry())
    assert any(i.field == "kind" and i.severity == "error" for i in result.issues)
    assert result.valid is False


def test_missing_name():
    """Missing name → error with field='name'."""
    fm = {"id": "t0001", "kind": "task", "created": "2026-01-01", "status": "ready"}
    result = validate_one(_meta(fm), _registry())
    assert any(i.field == "name" and i.severity == "error" for i in result.issues)
    assert result.valid is False


def test_missing_created():
    """Missing created → error with field='created'."""
    fm = {"id": "t0001", "kind": "task", "name": "t0001-fix-bug", "status": "ready"}
    result = validate_one(_meta(fm), _registry())
    assert any(i.field == "created" and i.severity == "error" for i in result.issues)
    assert result.valid is False


def test_unknown_status():
    """Unknown status → error with field='status', fixable=True."""
    fm = {"id": "t0001", "kind": "task", "name": "t0001-fix-bug", "created": "2026-01-01", "status": "wip"}
    result = validate_one(_meta(fm), _registry())
    status_issues = [i for i in result.issues if i.field == "status"]
    assert len(status_issues) == 1
    issue = status_issues[0]
    assert issue.severity == "error"
    assert issue.fixable is True
    assert result.valid is False


def test_unknown_kind():
    """Unknown kind → error; KindDef-dependent rules skipped."""
    fm = {"id": "x0001", "kind": "unknown-kind", "name": "x0001-test", "created": "2026-01-01"}
    result = validate_one(_meta(fm), _registry())
    kind_issues = [i for i in result.issues if i.field == "kind"]
    assert len(kind_issues) == 1
    assert kind_issues[0].severity == "error"
    assert kind_issues[0].fixable is False
    # No id-format errors — rule 4 was skipped
    assert not any(i.field == "id" for i in result.issues)


def test_numbered_id_wrong_format():
    """Numbered ID with wrong format → error, fixable=False."""
    fm = {"id": "t42", "kind": "task", "name": "t0001-fix-bug", "created": "2026-01-01", "status": "ready"}
    result = validate_one(_meta(fm, name="t42-test"), _registry())
    id_issues = [i for i in result.issues if i.field == "id"]
    assert len(id_issues) == 1
    assert id_issues[0].severity == "error"
    assert id_issues[0].fixable is False


def test_non_numbered_id_bad_slug():
    """Non-numbered ID with bad slug → error, fixable=False."""
    fm = {"id": "My Agent!", "kind": "agent", "name": "my-agent", "created": "2026-01-01"}
    result = validate_one(_meta(fm, name="my-agent"), _registry())
    id_issues = [i for i in result.issues if i.field == "id"]
    assert len(id_issues) == 1
    assert id_issues[0].severity == "error"
    assert id_issues[0].fixable is False


def test_schema_violation():
    """Schema constraint violation → error, fixable=False."""
    schema_kind = KindDef(
        name="task",
        dir="tasks",
        prefix="t",
        numbered=True,
        statuses=["backlog", "ready", "in-progress", "done"],
        schema={
            "type": "object",
            "properties": {
                "priority": {"type": "integer"},
            },
        },
    )
    registry = _registry([schema_kind])
    fm = {
        "id": "t0001",
        "kind": "task",
        "name": "t0001-fix-bug",
        "created": "2026-01-01",
        "status": "ready",
        "priority": "high",  # should be integer
    }
    result = validate_one(_meta(fm), registry)
    schema_issues = [i for i in result.issues if i.severity == "error" and not i.fixable and "priority" in i.field]
    assert len(schema_issues) >= 1


def test_unknown_field_warning():
    """Unknown frontmatter field → warning, fixable=False."""
    fm = {
        "id": "t0001",
        "kind": "task",
        "name": "t0001-fix-bug",
        "created": "2026-01-01",
        "status": "ready",
        "assigne": "bob",  # typo
    }
    result = validate_one(_meta(fm), _registry())
    warn_issues = [i for i in result.issues if i.field == "assigne"]
    assert len(warn_issues) == 1
    assert warn_issues[0].severity == "warning"
    assert warn_issues[0].fixable is False


def test_unknown_field_with_additional_properties_false():
    """When schema has additionalProperties: false, unknown fields are NOT double-reported."""
    strict_kind = KindDef(
        name="task",
        dir="tasks",
        prefix="t",
        numbered=True,
        statuses=["backlog", "ready", "in-progress", "done"],
        schema={
            "type": "object",
            "properties": {
                "id": {},
                "kind": {},
                "name": {},
                "created": {},
                "status": {},
            },
            "additionalProperties": False,
        },
    )
    registry = _registry([strict_kind])
    fm = {
        "id": "t0001",
        "kind": "task",
        "name": "t0001-fix",
        "created": "2026-01-01",
        "status": "ready",
        "extra_field": "oops",
    }
    result = validate_one(_meta(fm), registry)
    # extra_field should appear at most once — as a schema error, NOT as a warning
    warning_issues = [i for i in result.issues if i.severity == "warning" and i.field == "extra_field"]
    assert warning_issues == [], "Rule 6 must be skipped when additionalProperties: false"
    # It should be reported as a schema error
    error_issues = [i for i in result.issues if i.severity == "error"]
    assert len(error_issues) >= 1


def test_only_warnings_result_is_valid():
    """Only warnings → result.valid == True; errors/warnings properties separate them."""
    fm = {
        "id": "t0001",
        "kind": "task",
        "name": "t0001-fix-bug",
        "created": "2026-01-01",
        "status": "ready",
        "weirdkey": "value",
    }
    result = validate_one(_meta(fm), _registry())
    assert result.valid is True
    assert len(result.warnings) >= 1
    assert result.errors == []


def test_multiple_violations_accumulated():
    """Multiple violations are all accumulated, not short-circuited."""
    # Missing name AND missing created AND bad status
    fm = {
        "id": "t0001",
        "kind": "task",
        "status": "wip",  # bad status
        # missing name and created
    }
    result = validate_one(_meta(fm), _registry())
    fields_with_issues = {i.field for i in result.issues}
    assert "name" in fields_with_issues
    assert "created" in fields_with_issues
    assert "status" in fields_with_issues
    assert len(result.issues) >= 3


def test_validate_many():
    """validate_many returns one result per artifact."""
    fm1 = {"id": "t0001", "kind": "task", "name": "t0001-a", "created": "2026-01-01", "status": "ready"}
    fm2 = {"id": "t0002", "kind": "task", "name": "t0002-b", "created": "2026-01-01", "status": "ready"}
    metas = [_meta(fm1, "t0001-a"), _meta(fm2, "t0002-b")]
    results = validate_many(metas, _registry())
    assert len(results) == 2
    assert all(isinstance(r, ValidationResult) for r in results)


# ---------------------------------------------------------------------------
# Rule 3 extension — state-machined properties (s0033 D209 §5.3)
# ---------------------------------------------------------------------------


def _registry_with_sm(prop: str, enum: tuple[str, ...]) -> "Registry":
    """Build a registry with a kind that has a state machine on *prop*."""
    from artifacts_os.core.models import StateMachineDef

    sm = StateMachineDef(
        enum=enum,
        initial=enum[0],
        transitions={v: tuple(enum) for v in enum},
    )
    kd = KindDef(
        name="task",
        dir="tasks",
        prefix="t",
        numbered=True,
        statuses=list(enum) if prop == "status" else [],
        state_machines={prop: sm},
    )
    return Registry([kd], root=None)


def test_rule3_state_machine_valid_value() -> None:
    """Valid state-machined property value → no Rule 3 issue."""
    registry = _registry_with_sm("status", ("backlog", "ready"))
    fm = {"id": "t0001", "kind": "task", "name": "t", "created": "2026-01-01", "status": "backlog"}
    result = validate_one(_meta(fm), registry)
    status_issues = [i for i in result.issues if i.field == "status" and i.severity == "error"]
    assert status_issues == []


def test_rule3_state_machine_invalid_value_raises_issue() -> None:
    """Invalid value for a state-machined property → ValidationIssue with field=prop."""
    registry = _registry_with_sm("status", ("backlog", "ready"))
    fm = {"id": "t0001", "kind": "task", "name": "t", "created": "2026-01-01", "status": "wip"}
    result = validate_one(_meta(fm), registry)
    status_issues = [i for i in result.issues if i.field == "status"]
    assert len(status_issues) == 1
    assert status_issues[0].severity == "error"
    assert status_issues[0].fixable is True
    assert "wip" in status_issues[0].message
    assert result.valid is False


def test_rule3_non_status_property_invalid_value() -> None:
    """Rule 3 catches membership violations for non-status state-machined properties."""
    registry = _registry_with_sm("phase", ("scope", "design", "build"))
    fm = {
        "id": "t0001", "kind": "task", "name": "t", "created": "2026-01-01",
        "phase": "ship",  # not in enum
    }
    result = validate_one(_meta(fm), registry)
    # Filter to errors only — Rule 6 may add a warning for unknown field 'phase'
    phase_errors = [i for i in result.issues if i.field == "phase" and i.severity == "error"]
    assert len(phase_errors) == 1
    assert phase_errors[0].fixable is True
    assert "ship" in phase_errors[0].message
    assert "phase" in phase_errors[0].message


def test_rule3_non_status_property_valid_value() -> None:
    """Valid value for a non-status state-machined property → no Rule 3 error."""
    registry = _registry_with_sm("phase", ("scope", "design", "build"))
    fm = {
        "id": "t0001", "kind": "task", "name": "t", "created": "2026-01-01",
        "phase": "design",
    }
    result = validate_one(_meta(fm), registry)
    # No error-level issue for 'phase'; Rule 6 may add an "Unknown field" warning
    phase_errors = [i for i in result.issues if i.field == "phase" and i.severity == "error"]
    assert phase_errors == []


def test_rule3_state_machine_prop_absent_from_fm_no_issue() -> None:
    """State-machined property absent from frontmatter → no Rule 3 issue."""
    registry = _registry_with_sm("phase", ("scope", "design"))
    fm = {"id": "t0001", "kind": "task", "name": "t", "created": "2026-01-01"}
    result = validate_one(_meta(fm), registry)
    phase_issues = [i for i in result.issues if i.field == "phase"]
    assert phase_issues == []


def test_rule3_legacy_statuses_only_no_membership_check() -> None:
    """Kinds with only ``statuses=[…]`` and no state_machines no longer get
    a membership check from Rule 3 (s0033 §5.3 — single authority is
    ``state_machines``). The legacy fallback was removed alongside the
    parallel guard in ``store.update``.
    """
    kd = KindDef(
        name="task",
        dir="tasks",
        prefix="t",
        numbered=True,
        statuses=["backlog", "ready", "in-progress", "done"],
        # No state_machines — schema-less in-memory legacy fixture.
    )
    registry = Registry([kd], root=None)
    fm = {"id": "t0001", "kind": "task", "name": "t", "created": "2026-01-01", "status": "bogus"}
    result = validate_one(_meta(fm), registry)
    status_issues = [i for i in result.issues if i.field == "status" and i.severity == "error"]
    assert status_issues == []


def test_rule3_message_format() -> None:
    """Rule 3 message uses 'Invalid value ... for field ...' format."""
    registry = _registry_with_sm("status", ("backlog", "ready"))
    fm = {"id": "t0001", "kind": "task", "name": "t", "created": "2026-01-01", "status": "oops"}
    result = validate_one(_meta(fm), registry)
    status_issue = next(i for i in result.issues if i.field == "status")
    assert "Invalid value" in status_issue.message
    assert "status" in status_issue.message
    assert "oops" in status_issue.message
