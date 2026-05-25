"""artifacts-os — public API re-export shim.

All symbols are defined in artifacts_os.core. This module re-exports
them so callers can import directly from `artifacts_os` (unchanged from s2060).

Spec: s2060-artifacts-os-architecture, s2061-artifacts-os-module-system
"""

from artifacts_os.core import (  # noqa: F401
    __version__,
    find_vault_root,
    Registry,
    create,
    get,
    update,
    list_artifacts,
    resolve,
    search,
    Artifact,
    ArtifactMeta,
    KindDef,
    StateMachineDef,
    ArtifactError,
    NotFoundError,
    AmbiguousError,
    ValidationError,
)

__all__ = [
    "__version__",
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
    "StateMachineDef",
    "ArtifactError",
    "NotFoundError",
    "AmbiguousError",
    "ValidationError",
]
