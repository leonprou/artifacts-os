"""L1 kinds catalogue — name, description, has_template per registered kind.

Spec: s0017-artifact-kinds-discovery-mechanism § 5, § 8.1

Layer-isolation invariant (s0017 § 4): L1 MUST NOT read ARTIFACT.md body
content or any playbook file. Only kind.json and the ARTIFACT.md frontmatter
are touched. This module honours that invariant by delegating all I/O to
Registry._load_vault_kinds (which reads frontmatter only) and storing the
results on KindDef.description / KindDef.has_template.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from artifacts_os.core.registry import Registry


@dataclass(frozen=True)
class KindCatalogEntry:
    """L1 representation of one registered artifact kind.

    ``name``              — kind name (e.g. "task").
    ``description``       — one-line description from ARTIFACT.md frontmatter;
                            None when ARTIFACT.md is absent or description is empty.
    ``has_template``      — True iff artifacts/kinds/<name>/ARTIFACT.md exists.
    ``artifact_md_path``  — resolved path to ARTIFACT.md when has_template=True,
                            else None.
    """

    name: str
    description: str | None
    has_template: bool
    artifact_md_path: Path | None = None


class KindCatalog:
    """L1 discovery surface over a Registry.

    Layers L2/L3 will extend this class in a follow-up spec (s0017 § 11.1,
    § 11.2).  Consumers depending on L1 today will not need to switch surfaces
    when L2 lands.

    Parameters
    ----------
    registry:
        The active :class:`~artifacts_os.core.registry.Registry`.
    root:
        Vault root path.  Accepted for API parity with the forthcoming L2
        extension; L1 uses only data already stored on the registry's kinds.
    """

    def __init__(self, registry: Registry, root: Path) -> None:
        self._registry = registry
        self._root = Path(root)

    def list_kinds(self) -> list[KindCatalogEntry]:
        """Return one :class:`KindCatalogEntry` per registered kind, sorted by name."""
        return [
            KindCatalogEntry(
                name=kd.name,
                description=kd.description,
                has_template=kd.has_template,
                artifact_md_path=(
                    self._root / "artifacts" / "kinds" / kd.name / "ARTIFACT.md"
                    if kd.has_template else None
                ),
            )
            for kd in sorted(self._registry.all(), key=lambda k: k.name)
        ]
