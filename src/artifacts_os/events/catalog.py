"""Closed event-type catalog for artifacts-os.

Defines the six documented event-type constants and payload dataclasses.
Adding a new event type requires a spec revision and a ``version`` bump in
``s0025-artifact-events``.

Spec: s0025-artifact-events § C1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Event-type constants
# ---------------------------------------------------------------------------

ARTIFACT_CREATED = "artifact.created"
ARTIFACT_UPDATED = "artifact.updated"
ARTIFACT_STATUS_CHANGED = "artifact.status_changed"
ARTIFACT_VALIDATED = "artifact.validated"
HOOK_FIRED = "hook.fired"
HOOK_FAILED = "hook.failed"

ALL_EVENT_TYPES: frozenset[str] = frozenset(
    [
        ARTIFACT_CREATED,
        ARTIFACT_UPDATED,
        ARTIFACT_STATUS_CHANGED,
        ARTIFACT_VALIDATED,
        HOOK_FIRED,
        HOOK_FAILED,
    ]
)

# ---------------------------------------------------------------------------
# Payload dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ArtifactCreatedPayload:
    """Payload for ``artifact.created``."""

    kind: str
    id: str
    name: str
    stem: str
    path: str
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArtifactUpdatedPayload:
    """Payload for ``artifact.updated``."""

    kind: str
    id: str
    name: str
    stem: str
    path: str
    changed: list[str] = field(default_factory=list)
    before: dict[str, Any] = field(default_factory=dict)
    after: dict[str, Any] = field(default_factory=dict)
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArtifactStatusChangedPayload:
    """Payload for ``artifact.status_changed``."""

    kind: str
    id: str
    name: str
    stem: str
    path: str
    before: str = ""
    after: str = ""
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArtifactValidatedPayload:
    """Payload for ``artifact.validated``."""

    kind: str
    id: str
    stem: str
    path: str
    result: str = "pass"  # "pass" | "fail"
    issues: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class HookFiredPayload:
    """Payload for ``hook.fired``."""

    hook: str
    matcher: dict[str, Any] = field(default_factory=dict)
    action: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    phase: str = "post"


@dataclass
class HookFailedPayload:
    """Payload for ``hook.failed``."""

    hook: str
    matcher: dict[str, Any] = field(default_factory=dict)
    action: dict[str, Any] = field(default_factory=dict)
    phase: str = "post"
    blocking: bool = False
    error: str = ""
    duration_ms: int = 0
