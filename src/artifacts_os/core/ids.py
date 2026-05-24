"""ID generation and slug utilities.

Spec: s2060-artifacts-os-architecture § ids.py
"""

import re
from pathlib import Path


_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def next_prefixed_id(directory: Path, prefix: str) -> str:
    """Return next prefixed ID in directory. `{prefix}0001` when empty.

    Scans both ``*.md`` files (file-storage kinds) and subdirectories
    (directory-storage kinds) so numbered IDs are unique across both
    storage shapes.
    """
    directory = Path(directory)
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)-")
    max_n = 0
    if directory.is_dir():
        for entry in directory.iterdir():
            if entry.is_file() and entry.suffix == ".md":
                stem = entry.stem
            elif entry.is_dir():
                stem = entry.name
            else:
                continue
            match = pattern.match(stem)
            if match:
                n = int(match.group(1))
                if n > max_n:
                    max_n = n
    return f"{prefix}{max_n + 1:04d}"


def slugify(text: str, max_words: int = 5) -> str:
    """Lowercase, collapse non-[a-z0-9] runs to hyphens, take first max_words."""
    lowered = text.lower()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not collapsed:
        return ""
    parts = collapsed.split("-")
    return "-".join(parts[:max_words])


def validate_slug(slug: str) -> bool:
    """Return True iff slug matches ^[a-z0-9]+(-[a-z0-9]+)*$."""
    return bool(_SLUG_RE.match(slug))
