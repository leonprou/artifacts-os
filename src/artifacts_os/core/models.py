"""Data models for artifacts-os.

Spec: s2060-artifacts-os-architecture § models.py
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StateMachineDef:
    """Property-level state machine declared in kind.json.

    Built by Registry at load time from the ``enum`` + ``initial`` +
    ``transitions`` keywords inside a property definition.  Consumed by
    ``core.transitions.{check_create, check_transition}`` and by
    ``core.validate.validate_one`` (Rule 3 extension).

    Spec: s0033-declarative-per-property-state-machines § 3.1
    """

    enum: tuple[str, ...]                           # allowed universe
    initial: str | None                             # initial state; None when undeclared
    transitions: dict[str, tuple[str, ...]] | None  # None → unrestricted (D206); {} → locked (D207)


@dataclass
class ItemMeta:
    """Base class for items renderable in a Rich table.

    Subclasses override ``cell`` to read from their own data source.
    The default implementation reads named attributes via ``getattr``.
    """

    def cell(self, key: str, default: Any = "") -> Any:
        """Return the display value for *key*, falling back to *default*.

        Default: reads ``getattr(self, key, default)``.
        """
        return getattr(self, key, default)


@dataclass
class KindDef:
    name: str
    dir: str
    prefix: str
    numbered: bool
    statuses: list[str] = field(default_factory=list)
    schema: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    # Per-kind required frontmatter fields; None means use the global default.
    required_fields: list[str] | None = None
    # L1 catalogue fields populated from ARTIFACT.md frontmatter.
    description: str | None = None
    has_template: bool = False
    # Directory-storage primitive (s0032 §2.1).
    storage: str = "file"          # "file" | "directory"
    manifest_name: str = "{slug}.md"
    # Per-property state machines (s0033).  Keyed by property name.
    # Empty dict for kinds with no state machines declared.
    state_machines: dict[str, StateMachineDef] = field(default_factory=dict)

    @property
    def schema_properties(self) -> set[str]:
        """Names of properties defined in the kind's JSON schema."""
        return set(self.schema.get("properties", {}).keys())


@dataclass
class ArtifactMeta(ItemMeta):
    """Lightweight view populated from frontmatter only (no body read)."""

    id: str
    kind: str
    name: str
    title: str
    status: str | None
    tags: list[str]
    created: str
    path: Path
    frontmatter: dict

    def cell(self, key: str, default: Any = "") -> Any:
        """Return *key* from frontmatter, falling back to *default*."""
        return self.frontmatter.get(key, default)


@dataclass
class Artifact(ArtifactMeta):
    """Full artifact including body text."""

    body: str = ""


@dataclass
class ProjectConfig:
    """Project identity section of artifacts.yaml."""

    name: str
    alias: str | None = None


@dataclass(frozen=True)
class TransitionView:
    """Snapshot of legal next-values for one state-machined property.

    Spec: t0189 — Add Property API Get/Set Transitions CLI Verbs
    """

    property: str
    current: Any                       # current value; None when property absent
    allowed_next: tuple[Any, ...]      # transitions[current] (excludes wildcard for clarity)
    wildcard_targets: tuple[Any, ...]  # transitions["*"]
    locked: bool                       # True iff transitions == {} (s0033 D207)


@dataclass(kw_only=True)
class Settings:
    """Base settings dataclass parsed from artifacts.yaml.

    Other modules extend this class to add their own typed fields,
    reading their section from ``raw``.
    """

    layout_version: int
    project: ProjectConfig
    raw: dict[str, Any] = field(default_factory=dict)
