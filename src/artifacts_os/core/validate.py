"""Frontmatter validation for artifacts-os.

Spec: s0008-artifact-validate-command
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from artifacts_os.core.models import ArtifactMeta
    from artifacts_os.core.registry import Registry

from artifacts_os.core.ids import validate_slug

Severity = Literal["error", "warning"]

# Required frontmatter keys for every artifact.
_REQUIRED_KEYS = ("id", "kind", "title", "created")

# Built-in metadata fields recognised regardless of kind schema.
_BUILTIN_FIELDS = frozenset({
    "id", "kind", "name", "title", "status", "tags", "created", "started",
    "updated", "agent", "task", "parent", "subtasks", "artifacts", "owner",
    "assignee", "type",
})


@dataclass
class ValidationIssue:
    field: str               # frontmatter key involved, or "" for artifact-level
    message: str             # human-readable description
    fixable: bool            # True ↔ --fix can auto-correct this issue
    severity: Severity = "error"   # "error" fails validation; "warning" does not


@dataclass
class ValidationResult:
    name: str                           # artifact name (stem)
    kind: str                           # kind string
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def valid(self) -> bool:
        """True when no *errors* — warnings alone don't invalidate."""
        return not self.errors


def validate_one(
    meta: "ArtifactMeta",
    registry: "Registry",
) -> ValidationResult:
    """Validate frontmatter of a single artifact. Pure function; no I/O."""
    fm = meta.frontmatter
    issues: list[ValidationIssue] = []
    kind_str = fm.get("kind", "")

    # Rule 1: Required keys
    for key in _REQUIRED_KEYS:
        if key not in fm:
            issues.append(ValidationIssue(
                field=key,
                message=f"Required field '{key}' is missing",
                fixable=False,
                severity="error",
            ))

    # Rule 2: kind resolves (only when kind key was present)
    kind_def = None
    if "kind" not in fm:
        # Already reported as missing; skip KindDef-dependent rules
        return ValidationResult(name=meta.name, kind=kind_str, issues=issues)
    try:
        kind_def = registry.get(kind_str)
    except Exception:
        issues.append(ValidationIssue(
            field="kind",
            message=f"Unknown kind '{kind_str}'",
            fixable=False,
            severity="error",
        ))
        # Skip KindDef-dependent rules
        return ValidationResult(name=meta.name, kind=kind_str, issues=issues)

    # Rule 3: status legality
    if kind_def.statuses:
        status_val = fm.get("status")
        if status_val not in kind_def.statuses:
            issues.append(ValidationIssue(
                field="status",
                message=(
                    f"Unknown status '{status_val}' — "
                    f"valid: {', '.join(kind_def.statuses)}"
                ),
                fixable=True,
                severity="error",
            ))

    # Rule 4: id format
    id_val = fm.get("id", "")
    if id_val:  # only check if id is present (rule 1 handles absence)
        if kind_def.numbered:
            prefix = kind_def.prefix
            pattern = re.compile(rf"^{re.escape(prefix)}\d{{4}}$")
            if not pattern.match(id_val):
                issues.append(ValidationIssue(
                    field="id",
                    message=f"ID '{id_val}' does not match expected format '{prefix}NNNN'",
                    fixable=False,
                    severity="error",
                ))
        else:
            if not validate_slug(id_val):
                issues.append(ValidationIssue(
                    field="id",
                    message=f"ID '{id_val}' is not a valid slug",
                    fixable=False,
                    severity="error",
                ))

    # Rule 5: KindDef.schema constraints
    # Skip status field from schema errors when rule 3 already handles it
    # (avoids double-reporting fixable status issues as both rule-3 and rule-5 errors).
    _rule3_handled_status = bool(kind_def.statuses)
    if kind_def.schema:
        try:
            import jsonschema
            validator = jsonschema.Draft7Validator(kind_def.schema)
            for exc in validator.iter_errors(fm):
                field_path = ".".join(str(p) for p in exc.absolute_path) if exc.absolute_path else ""
                # Skip status schema errors when rule 3 is responsible for status validation
                if field_path == "status" and _rule3_handled_status:
                    continue
                issues.append(ValidationIssue(
                    field=field_path,
                    message=exc.message,
                    fixable=False,
                    severity="error",
                ))
        except ImportError:
            pass  # jsonschema not installed; skip schema validation

    # Rule 6: Unknown fields (skip when schema has additionalProperties: false)
    schema = kind_def.schema or {}
    if schema.get("additionalProperties") is not False:
        schema_props = set(schema.get("properties", {}).keys())
        schema_required = set(schema.get("required", []))
        recognised = _BUILTIN_FIELDS | schema_props | schema_required
        for key in fm:
            if key not in recognised:
                issues.append(ValidationIssue(
                    field=key,
                    message=f"Unknown field '{key}'",
                    fixable=False,
                    severity="warning",
                ))

    return ValidationResult(name=meta.name, kind=kind_str, issues=issues)


def validate_many(
    metas: list["ArtifactMeta"],
    registry: "Registry",
) -> list[ValidationResult]:
    """Validate a list of artifacts. Returns one result per artifact."""
    return [validate_one(meta, registry) for meta in metas]
