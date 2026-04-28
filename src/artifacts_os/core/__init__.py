"""artifacts-os core — storage, discovery, registry.

Spec: s2060-artifacts-os-architecture, s2061-artifacts-os-module-system
"""

from artifacts_os.core.vault import find_vault_root
from artifacts_os.core.registry import Registry
from artifacts_os.core.store import create, get, update
from artifacts_os.core.discover import list_artifacts, resolve, search
from artifacts_os.core.models import Artifact, ArtifactMeta, KindDef, Settings, ProjectConfig
from artifacts_os.core.settings import load_settings, UnsupportedSchemaVersion
from artifacts_os.core.errors import (
    ArtifactError,
    NotFoundError,
    AmbiguousError,
    ValidationError,
)
from artifacts_os.core.validate import validate_one, validate_many, ValidationIssue, ValidationResult

__all__ = [
    "find_vault_root",
    "Registry",
    "create",
    "get",
    "update",
    "list_artifacts",
    "resolve",
    "search",
    "Artifact",
    "ArtifactMeta",
    "KindDef",
    "ArtifactError",
    "NotFoundError",
    "AmbiguousError",
    "ValidationError",
    "validate_one",
    "validate_many",
    "ValidationIssue",
    "ValidationResult",
    "load_settings",
    "UnsupportedSchemaVersion",
    "Settings",
    "ProjectConfig",
]
