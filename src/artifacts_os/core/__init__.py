"""artifacts-os core — storage, discovery, registry.

Spec: s2060-artifacts-os-architecture, s2061-artifacts-os-module-system
"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("artifacts-os")
except PackageNotFoundError:  # pragma: no cover — only hit in non-installed checkouts
    __version__ = "0.0.0+unknown"

from artifacts_os.core.vault import find_vault_root
from artifacts_os.core.registry import Registry
from artifacts_os.core.store import create, get, update, get_prop, set_prop
from artifacts_os.core.discover import list_artifacts, resolve, search, parent, children, unwrap_wikilink
from artifacts_os.core.models import Artifact, ArtifactMeta, ItemMeta, KindDef, StateMachineDef, TransitionView, Settings, ProjectConfig
from artifacts_os.core.transitions import transitions_for
from artifacts_os.core.settings import load_settings, UnsupportedSchemaVersion
from artifacts_os.core.errors import (
    ArtifactError,
    NotFoundError,
    AmbiguousError,
    ValidationError,
    BlockedByPreHook,
)
from artifacts_os.core.validate import validate_one, validate_many, ValidationIssue, ValidationResult
from artifacts_os.core.kinds_catalog import KindCatalog, KindCatalogEntry

__all__ = [
    "__version__",
    "find_vault_root",
    "Registry",
    "create",
    "get",
    "update",
    "get_prop",
    "set_prop",
    "transitions_for",
    "list_artifacts",
    "resolve",
    "search",
    "parent",
    "children",
    "unwrap_wikilink",
    "Artifact",
    "ArtifactMeta",
    "ItemMeta",
    "KindDef",
    "StateMachineDef",
    "TransitionView",
    "ArtifactError",
    "NotFoundError",
    "AmbiguousError",
    "ValidationError",
    "BlockedByPreHook",
    "validate_one",
    "validate_many",
    "ValidationIssue",
    "ValidationResult",
    "load_settings",
    "UnsupportedSchemaVersion",
    "Settings",
    "ProjectConfig",
    "KindCatalog",
    "KindCatalogEntry",
]
