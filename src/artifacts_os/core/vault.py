"""Vault root discovery.

Spec: s2060-artifacts-os-architecture § vault.py
"""

from pathlib import Path


def find_vault_root(start: Path | None = None) -> Path | None:
    """Walk up from start (default: CWD) until a directory containing
    `.openstation/` is found. Returns the directory or None."""
    current = Path(start) if start is not None else Path.cwd()
    current = current.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".openstation").is_dir():
            return candidate
    return None
