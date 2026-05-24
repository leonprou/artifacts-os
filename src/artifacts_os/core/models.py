"""Data models for artifacts-os.

Spec: s2060-artifacts-os-architecture § models.py
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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


@dataclass(kw_only=True)
class Settings:
    """Base settings dataclass parsed from artifacts.yaml.

    Other modules extend this class to add their own typed fields,
    reading their section from ``raw``.
    """

    layout_version: int
    project: ProjectConfig
    raw: dict[str, Any] = field(default_factory=dict)
