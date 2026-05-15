"""Fetch helpers — shallow git clone for the artbook module.

Spec: s0029-artbook-mvp-distribution-model §6
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Tuple

from artifacts_os.artbook.errors import FetchError
from artifacts_os.artbook.manifest import Manifest, load_manifest


def clone(distro_url: str, clone_into: Path) -> None:
    """Shallow-clone *distro_url* (main branch) into *clone_into*.

    Raises FetchError if git exits non-zero (D4, D13).
    """
    result = subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            "main",
            "--single-branch",
            distro_url,
            str(clone_into),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise FetchError(
            f"git clone failed (exit {result.returncode})",
            returncode=result.returncode,
            stderr=result.stderr,
        )


def get_short_sha(clone_root: Path) -> str:
    """Return the short HEAD SHA of the cloned repo.

    Returns an empty string on any git failure (non-fatal — used for reporting only).
    """
    result = subprocess.run(
        ["git", "-C", str(clone_root), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return ""


def read_manifest(distro_url: str, clone_into: Path | None = None) -> Tuple[Manifest, Path]:
    """Shallow-clone *distro_url* and return (Manifest, clone_root).

    If *clone_into* is provided the clone is placed there (caller owns teardown).
    If *clone_into* is None a temporary directory is created; the caller is
    responsible for removing it when done.

    Raises FetchError on git failure or ManifestError on invalid artbook.yaml.
    """
    if clone_into is None:
        import tempfile

        tmpdir = tempfile.mkdtemp(prefix="artbook-")
        clone_root = Path(tmpdir)
    else:
        clone_root = clone_into

    clone(distro_url, clone_root)
    manifest = load_manifest(clone_root)
    return manifest, clone_root
