"""Vault root discovery.

Spec: s2060-artifacts-os-architecture § vault.py
"""

from pathlib import Path


def find_vault_root(
    start: Path | None = None,
    marker_filename: str = "artifacts.yaml",
) -> Path | None:
    """Walk up from start (default: CWD) until a directory containing
    *marker_filename* (default: ``artifacts.yaml``) is found.
    Returns the directory or None.

    The *marker_filename* kwarg lets callers look for a custom-named
    settings file (e.g. ``myapp.yaml``) without altering the
    default discovery behaviour. Spec: s0034 §6.4.
    """
    current = Path(start) if start is not None else Path.cwd()
    current = current.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / marker_filename).is_file():
            return candidate
    return None
