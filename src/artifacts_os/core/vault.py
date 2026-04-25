"""Vault root discovery.

Spec: s2060-artifacts-os-architecture § vault.py
"""

from pathlib import Path


def find_vault_root(start: Path | None = None) -> Path | None:
    """Walk up from start (default: CWD) until a directory containing
    `artifacts/artifacts.yaml` is found. Returns the directory or None."""
    current = Path(start) if start is not None else Path.cwd()
    current = current.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "artifacts" / "artifacts.yaml").is_file():
            return candidate
    return None
