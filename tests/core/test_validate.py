"""Unit tests for core/validate.py — validate_one / validate_many.

All tests use ArtifactMeta directly; no file I/O.
"""

from pathlib import Path

import pytest

from artifacts_os.core.models import ArtifactMeta, KindDef
from artifacts_os.core.registry import Registry
from artifacts_os.core.validate import validate_one, validate_many, ValidationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _meta(frontmatter: dict, name: str = "t0001-test") -> ArtifactMeta:
    """Build an ArtifactMeta from a raw frontmatter dict."""
    return ArtifactMeta(
        id=frontmatter.get("id", ""),
        kind=frontmatter.get("kind", ""),
        name=name,
        title=frontmatter.get("title", ""),
        status=frontmatter.get("status"),
        tags=frontmatter.get("tags", []),
        created=frontmatter.get("created", ""),
        path=Path("/fake/path.md"),
        frontmatter=frontmatter,
    )


def _registry(kinds: list[KindDef] | None = None) -> Registry:
    """Build a Registry from a list of KindDefs (no vault root)."""
    if kinds is None:
        kinds = [
            KindDef(
                name="task",
                dir="tasks",
                prefix="t",
                numbered=True,
                statuses=["backlog", "ready", "in-progress", "done"],
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
    fm = {"id": "t0001", "kind": "task", "title": "Fix bug", "created": "2026-01-01", "status": "ready"}
    result = validate_one(_meta(fm), _registry())
    assert result.valid is True
    assert result.issues == []


def test_missing_id():
    """Missing id → error with field='id'."""
    fm = {"kind": "task", "title": "Fix bug", "created": "2026-01-01", "status": "ready"}
    result = validate_one(_meta(fm, name="t0001-test"), _registry())
    assert any(i.field == "id" and i.severity == "error" for i in result.issues)
    assert result.valid is False


def test_missing_kind():
    """Missing kind → error with field='kind'."""
    fm = {"id": "t0001", "title": "Fix bug", "created": "2026-01-01", "status": "ready"}
    result = validate_one(_meta(fm), _registry())
    assert any(i.field == "kind" and i.severity == "error" for i in result.issues)
    assert result.valid is False


def test_missing_title():
    """Missing title → error with field='title'."""
    fm = {"id": "t0001", "kind": "task", "created": "2026-01-01", "status": "ready"}
    result = validate_one(_meta(fm), _registry())
    assert any(i.field == "title" and i.severity == "error" for i in result.issues)
    assert result.valid is False


def test_missing_created():
    """Missing created → error with field='created'."""
    fm = {"id": "t0001", "kind": "task", "title": "Fix bug", "status": "ready"}
    result = validate_one(_meta(fm), _registry())
    assert any(i.field == "created" and i.severity == "error" for i in result.issues)
    assert result.valid is False


def test_unknown_status():
    """Unknown status → error with field='status', fixable=True."""
    fm = {"id": "t0001", "kind": "task", "title": "Fix bug", "created": "2026-01-01", "status": "wip"}
    result = validate_one(_meta(fm), _registry())
    status_issues = [i for i in result.issues if i.field == "status"]
    assert len(status_issues) == 1
    issue = status_issues[0]
    assert issue.severity == "error"
    assert issue.fixable is True
    assert result.valid is False


def test_unknown_kind():
    """Unknown kind → error; KindDef-dependent rules skipped."""
    fm = {"id": "x0001", "kind": "unknown-kind", "title": "Test", "created": "2026-01-01"}
    result = validate_one(_meta(fm), _registry())
    kind_issues = [i for i in result.issues if i.field == "kind"]
    assert len(kind_issues) == 1
    assert kind_issues[0].severity == "error"
    assert kind_issues[0].fixable is False
    # No id-format errors — rule 4 was skipped
    assert not any(i.field == "id" for i in result.issues)


def test_numbered_id_wrong_format():
    """Numbered ID with wrong format → error, fixable=False."""
    fm = {"id": "t42", "kind": "task", "title": "Fix bug", "created": "2026-01-01", "status": "ready"}
    result = validate_one(_meta(fm, name="t42-test"), _registry())
    id_issues = [i for i in result.issues if i.field == "id"]
    assert len(id_issues) == 1
    assert id_issues[0].severity == "error"
    assert id_issues[0].fixable is False


def test_non_numbered_id_bad_slug():
    """Non-numbered ID with bad slug → error, fixable=False."""
    fm = {"id": "My Agent!", "kind": "agent", "title": "Agent", "created": "2026-01-01"}
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
        "title": "Fix bug",
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
        "title": "Fix bug",
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
                "title": {},
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
        "title": "Fix",
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
        "title": "Fix bug",
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
    # Missing title AND missing created AND bad status
    fm = {
        "id": "t0001",
        "kind": "task",
        "status": "wip",  # bad status
        # missing title and created
    }
    result = validate_one(_meta(fm), _registry())
    fields_with_issues = {i.field for i in result.issues}
    assert "title" in fields_with_issues
    assert "created" in fields_with_issues
    assert "status" in fields_with_issues
    assert len(result.issues) >= 3


def test_validate_many():
    """validate_many returns one result per artifact."""
    fm1 = {"id": "t0001", "kind": "task", "title": "A", "created": "2026-01-01", "status": "ready"}
    fm2 = {"id": "t0002", "kind": "task", "title": "B", "created": "2026-01-01", "status": "ready"}
    metas = [_meta(fm1, "t0001-a"), _meta(fm2, "t0002-b")]
    results = validate_many(metas, _registry())
    assert len(results) == 2
    assert all(isinstance(r, ValidationResult) for r in results)
