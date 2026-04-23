"""Data models for artifacts-os.

Spec: s2060-artifacts-os-architecture § models.py
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class KindDef:
    name: str
    dir: str
    prefix: str
    numbered: bool
    statuses: list[str] = field(default_factory=list)
    schema: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)


@dataclass
class ArtifactMeta:
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


@dataclass
class Artifact(ArtifactMeta):
    """Full artifact including body text."""

    body: str = ""
