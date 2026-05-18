"""State file read/write for artbook promotion tracking.

Tracks previously-promoted targets per book for idempotent re-pull and
stale-target cleanup.

State file location: ``artifacts/.artbook/state.json`` (vault-relative).

Spec: s0031-artbook-post-pull-artifact-promotion D32
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

_STATE_DIR = Path("artifacts") / ".artbook"
_STATE_FILE = _STATE_DIR / "state.json"

_EMPTY_STATE: dict[str, Any] = {"version": 1, "promotions": {}}


def _state_path(vault_root: Path) -> Path:
    return vault_root / _STATE_FILE


def read_state(vault_root: Path) -> dict[str, Any]:
    """Read ``artifacts/.artbook/state.json``; absent file returns empty state.

    The state schema:
    - ``version``: int (always 1)
    - ``promotions``: dict mapping book name → promotion record dict

    Each promotion record has:
    - ``mode``: str ('symlink' or 'copy')
    - ``target_root``: str (vault-relative promotion target directory)
    - ``files``: list of string (symlink mode) or {path, hash} dicts (copy mode)
    """
    path = _state_path(vault_root)
    if not path.is_file():
        return {"version": 1, "promotions": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "promotions": {}}
    if not isinstance(data, dict):
        return {"version": 1, "promotions": {}}
    if "promotions" not in data or not isinstance(data["promotions"], dict):
        data["promotions"] = {}
    if "version" not in data:
        data["version"] = 1
    return data


def write_state(vault_root: Path, state: dict[str, Any]) -> None:
    """Atomically write *state* to ``artifacts/.artbook/state.json``.

    Creates parent directories as needed. Uses write-to-tmp + os.replace
    for atomicity (D32).
    """
    path = _state_path(vault_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def file_hash(path: Path) -> str:
    """Return the sha256 hex digest of *path*'s content, prefixed ``sha256:``."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return f"sha256:{h.hexdigest()}"


def file_hash_bytes(data: bytes) -> str:
    """Return the sha256 hex digest of *data*, prefixed ``sha256:``."""
    h = hashlib.sha256()
    h.update(data)
    return f"sha256:{h.hexdigest()}"


# ---------------------------------------------------------------------------
# State-entry helpers (D32 schema)
# ---------------------------------------------------------------------------


def make_symlink_entry(vault_rel_path: str) -> str:
    """Return a string-form state entry for a symlink-mode promotion."""
    return vault_rel_path


def make_copy_entry(vault_rel_path: str, content_hash: str) -> dict[str, str]:
    """Return an object-form state entry for a copy-mode promotion."""
    return {"path": vault_rel_path, "hash": content_hash}


def entry_path(entry: Any) -> str | None:
    """Extract the vault-relative path string from a state entry (either form)."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return entry.get("path")
    return None


def entry_hash(entry: Any) -> str | None:
    """Extract the content hash from a copy-mode state entry; None for symlink entries."""
    if isinstance(entry, dict):
        return entry.get("hash")
    return None
