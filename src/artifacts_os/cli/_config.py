"""Config-ref resolution for the ``--config`` CLI flag.

Spec: s0034-artifacts-cli-config-flag §6.1–6.3.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from artifacts_os.core import find_vault_root


@dataclass(frozen=True)
class SettingsRef:
    """Resolved settings location: vault root directory + settings file path."""

    root: Path
    settings_path: Path


class ConfigRefError(ValueError):
    """Raised when ``--config <ref>`` cannot be resolved."""

    def __init__(self, ref: str, reason: str) -> None:
        self.ref = ref
        self.reason = reason
        super().__init__(f"--config: {ref}: {reason}")


def _classify_ref(ref: str) -> str:
    """Return ``"path"`` if *ref* looks like a path, ``"basename"`` otherwise.

    A ref is a path iff it is absolute or contains any path separator.
    Falls back to ``"basename"`` for bare filenames.

    Spec: s0034 §6.1.
    """
    if os.path.isabs(ref):
        return "path"
    if os.sep in ref or "/" in ref:
        return "path"
    return "basename"


def _resolve_settings_path(
    *,
    config_ref: str | None,
    cwd: Path,
) -> SettingsRef | None:
    """Apply ``--config`` disambiguation and return a :class:`SettingsRef`.

    Returns ``None`` when no settings file was found and no ``--config`` was
    given (default vault discovery returned nothing). The caller emits the
    "not in a vault" error.

    Raises :class:`ConfigRefError` when ``--config`` was given but the ref
    cannot be resolved. The caller catches and emits an exit-2 error.

    Spec: s0034 §6.2.
    """
    if config_ref is None:
        root = find_vault_root(start=cwd)
        if root is None:
            return None
        return SettingsRef(root=root, settings_path=root / "artifacts.yaml")

    mode = _classify_ref(config_ref)

    if mode == "path":
        path = Path(config_ref).expanduser().resolve()
        if not path.is_file():
            raise ConfigRefError(config_ref, "file not found")
        return SettingsRef(root=path.parent, settings_path=path)

    # basename mode — walk up from CWD looking for that filename.
    root = find_vault_root(start=cwd, marker_filename=config_ref)
    if root is None:
        raise ConfigRefError(
            config_ref,
            f"no file with that name found walking up from {cwd}",
        )
    return SettingsRef(root=root, settings_path=root / config_ref)
