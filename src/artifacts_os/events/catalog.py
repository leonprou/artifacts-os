"""Closed event-type catalog for artifacts-os.

Defines event-type constants and payload dataclasses.
Adding a new event type requires a spec revision and a ``version`` bump in
``s0025-artifact-events``.

Spec: s0025-artifact-events § C1; hooks-via-artbook s0032 §7
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
HOOK_SKIPPED = "hook.skipped"
HOOK_PROMOTED = "hook.promoted"
HOOK_DEMOTED = "hook.demoted"
HOOK_PULLED = "hook.pulled"

ALL_EVENT_TYPES: frozenset[str] = frozenset(
    [
        ARTIFACT_CREATED,
        ARTIFACT_UPDATED,
        ARTIFACT_STATUS_CHANGED,
        ARTIFACT_VALIDATED,
        HOOK_FIRED,
        HOOK_FAILED,
        HOOK_SKIPPED,
        HOOK_PROMOTED,
        HOOK_DEMOTED,
        HOOK_PULLED,
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
    source: str | None = None  # "yaml" | "bundle" | None


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
    source: str | None = None  # "yaml" | "bundle" | None


@dataclass
class HookSkippedPayload:
    """Payload for ``hook.skipped``."""

    hook: str
    reason: str = ""  # "missing-target" | "parse-error" | "escape-attempt"
    path: str = ""


@dataclass
class HookPromotedPayload:
    """Payload for ``hook.promoted``."""

    hook: str
    target: str = ""


@dataclass
class HookDemotedPayload:
    """Payload for ``hook.demoted``."""

    hook: str
    reason: str = ""  # "" | "prune"


@dataclass
class HookPulledPayload:
    """Payload for ``hook.pulled`` (s0032 §5).

    Emitted once per ``kind: hook`` book pull.
    ``book`` is the book name.
    ``written`` / ``overwritten`` / ``removed`` are slug lists.
    """

    book: str
    written: list[str] = field(default_factory=list)
    overwritten: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
