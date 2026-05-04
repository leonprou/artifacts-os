"""Body loader for /artifacts.create slash command.

Spec: s0018-artifact-md-body-loader-for

Implements the skeleton extraction and placeholder-substitution algorithm
described in s0018 § 4.4 and § 5.1.  This module is the Python-callable
body-loading procedure invoked (or described) by the slash command.

Layer boundary (s0018 D6 / D7):
- This module reads exactly ONE ARTIFACT.md body per call (the chosen kind's).
- It NEVER reads kind.json bodies, playbooks, or other kinds' ARTIFACT.md files.
- The CLI stays body-agnostic; this module's output is piped via --body-file -.
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import NamedTuple

import yaml

# Regex for recognised placeholders: {{UPPERCASE_IDENTIFIER}}
_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")


class LoadResult(NamedTuple):
    """Result of :func:`load_body`."""

    body: str
    """Resolved skeleton body with {{TITLE}} substituted.  Empty string when
    the kind has no ARTIFACT.md or the skeleton section is absent."""

    info: str | None
    """Agent-visible note when the kind has no ARTIFACT.md, or None."""


def _read_frontmatter(path: Path) -> dict:
    """Read only the YAML frontmatter block from *path*.

    Returns an empty dict when the file does not start with ``---``.
    Raises no exceptions on YAML parse errors (returns empty dict with a
    warning), matching the body-loader's "treat-as-missing" contract.
    """
    lines: list[str] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            first = fh.readline()
            if first.strip() != "---":
                return {}
            for line in fh:
                if line.rstrip("\n") == "---":
                    break
                lines.append(line)
        return yaml.safe_load("".join(lines)) or {}
    except Exception as exc:  # noqa: BLE001
        warnings.warn(
            f"body_loader: could not parse frontmatter of {path}: {exc}",
            stacklevel=3,
        )
        return {}


def _read_body_lines(path: Path) -> list[str]:
    """Return the body lines of an ARTIFACT.md (everything after frontmatter).

    Returns an empty list on any I/O error.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    lines = text.splitlines(keepends=True)
    # Skip YAML frontmatter block (---...\n---\n)
    if not lines or lines[0].strip() != "---":
        return lines
    for i, line in enumerate(lines[1:], 1):
        if line.rstrip("\n") == "---":
            return lines[i + 1 :]
    return []  # unclosed frontmatter


def _extract_section(body_lines: list[str], heading: str) -> str | None:
    """Extract the content of an H2 section from body_lines.

    Finds the line equal to *heading*, then collects lines until the next
    file-level H2 heading (i.e., a line starting with ``## `` that is NOT
    inside a code fence).  Returns None when the heading is not found.

    The collected block is returned as a string with code-fence delimiters
    stripped (per s0018 § 5.2): if the section opens with a ``\`\`\`markdown``
    (or bare ``\`\`\``\`) fence and closes with ``\`\`\``\`, the fence lines
    are removed and the inner content is returned.  If there is no fence the
    section content is returned verbatim.
    """
    # Locate the target heading (case-insensitive comparison on the name part
    # for Variants/<name> as per s0018 § 5.1).
    section_start: int | None = None
    for i, line in enumerate(body_lines):
        if line.rstrip("\n\r") == heading:
            section_start = i + 1
            break
        # Case-insensitive match for Variants headings
        if (
            heading.startswith("## Variants/")
            and line.rstrip("\n\r").lower() == heading.lower()
        ):
            section_start = i + 1
            break

    if section_start is None:
        return None

    # Collect lines until next file-level H2 (outside code fences)
    section_lines: list[str] = []
    in_fence = False
    for line in body_lines[section_start:]:
        stripped = line.rstrip("\n\r")
        # Toggle fence state on opening/closing fence markers
        if stripped.startswith("```"):
            in_fence = not in_fence
        # Stop at file-level H2 heading (not inside a fence)
        if not in_fence and stripped.startswith("## "):
            break
        section_lines.append(line)

    return _strip_code_fence("".join(section_lines))


def _strip_code_fence(text: str) -> str:
    """Strip surrounding \\`\\`\\`markdown ... \\`\\`\\` or \\`\\`\\` ... \\`\\`\\` fences.

    Per s0018 § 5.2: the opening fence (\\`\\`\\`markdown or bare \\`\\`\\`) and its
    matching closing \\`\\`\\` are removed; the inner content is returned as plain
    markdown.  If no fence is found the text is returned verbatim.
    """
    lines = text.splitlines(keepends=True)
    # Find opening fence
    open_idx: int | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            open_idx = i
            break
        # Skip blank lines before fence
        if stripped:
            break  # non-blank, non-fence content → no fence

    if open_idx is None:
        return text

    # Find closing fence (last ``` line)
    close_idx: int | None = None
    for i in range(len(lines) - 1, open_idx, -1):
        if lines[i].strip() == "```":
            close_idx = i
            break

    if close_idx is None or close_idx <= open_idx:
        return text  # unclosed fence — return verbatim

    inner = lines[open_idx + 1 : close_idx]
    return "".join(inner)


def _list_variant_names(body_lines: list[str]) -> list[str]:
    """Return the names of all ``## Variants/<name>`` sections in *body_lines*."""
    names: list[str] = []
    in_fence = False
    for line in body_lines:
        stripped = line.rstrip("\n\r")
        if stripped.startswith("```"):
            in_fence = not in_fence
        if not in_fence and stripped.startswith("## Variants/"):
            name = stripped[len("## Variants/") :]
            if name:
                names.append(name)
    return names


def read_skeleton_block(
    path: Path,
    variant: str | None = None,
    type_token: str | None = None,
) -> tuple[str | None, str | None]:
    """Extract and return the skeleton block from *path*.

    Implements s0018 § 5.1 variant-selection precedence:
    1. Explicit *variant* name (highest priority).
    2. *type_token* when the ARTIFACT.md frontmatter declares ``variant_field: type``.
    3. Default ``## Skeleton``.

    Returns a tuple ``(block, error_message)``:
    - On success: ``(plain_markdown_string, None)``
    - When an explicit variant name does not match: ``(None, error_message)``
    - When the skeleton section is absent: ``(None, None)``
    """
    fm = _read_frontmatter(path)
    body_lines = _read_body_lines(path)
    declared_variants = _list_variant_names(body_lines)

    # Determine which heading to use (s0018 § 5.1)
    if variant is not None:
        # Case-insensitive match as per spec
        match = next(
            (v for v in declared_variants if v.lower() == variant.lower()), None
        )
        if match is None:
            listed = ", ".join(repr(v) for v in declared_variants) or "(none)"
            return None, (
                f"error: variant {variant!r} not found; declared variants: {listed}"
            )
        heading = f"## Variants/{match}"
    elif type_token is not None and fm.get("variant_field") == "type":
        # type token selects a variant only when variant_field: type is declared
        match = next(
            (v for v in declared_variants if v.lower() == type_token.lower()), None
        )
        if match is None:
            listed = ", ".join(repr(v) for v in declared_variants) or "(none)"
            return None, (
                f"error: variant {type_token!r} (from type token) not found; "
                f"declared variants: {listed}"
            )
        heading = f"## Variants/{match}"
    else:
        heading = "## Skeleton"

    block = _extract_section(body_lines, heading)
    return block, None


def load_body(
    artifact_md_path: Path | None,
    title: str,
    variant: str | None = None,
    type_token: str | None = None,
) -> LoadResult:
    """Load, substitute, and return the body for a new artifact.

    Implements s0018 § 4.4 substitution algorithm:

    1. When *artifact_md_path* is None (``has_template=False``): return empty
       body + agent-visible info note (s0018 § 6).
    2. Read the skeleton block via :func:`read_skeleton_block`.
    3. Substitute ``{{TITLE}}`` with *title* (s0018 § 4.2).
    4. Return the resolved body.

    Only ``{{TITLE}}`` is substituted in v1; all other ``{{TOKEN}}``
    placeholders are left literal for the agent to fill in (s0018 D1/D3).
    """
    if artifact_md_path is None:
        # Caller already determined has_template=False; note which kind is
        # unavailable via the path being None (caller logs the kind name).
        return LoadResult(body="", info=None)

    # Check that the path refers to a readable file; treat missing/unreadable
    # as if has_template=False (s0018 § 11.2).
    if not artifact_md_path.is_file():
        kind_name = artifact_md_path.parent.name
        return LoadResult(
            body="",
            info=f"info: kind '{kind_name}' has no ARTIFACT.md; created with empty body.",
        )

    block, error = read_skeleton_block(
        artifact_md_path, variant=variant, type_token=type_token
    )

    if error is not None:
        # Variant mismatch — propagate the error to the caller
        return LoadResult(body="", info=error)

    if block is None:
        # Section absent — fall back to empty body
        kind_name = artifact_md_path.parent.name
        return LoadResult(
            body="",
            info=f"info: kind '{kind_name}' has no ARTIFACT.md; created with empty body.",
        )

    # Substitute {{TITLE}} only (s0018 § 4.2, D1)
    body = block.replace("{{TITLE}}", title)
    return LoadResult(body=body, info=None)


def body_for_kind(
    kind_name: str,
    artifact_md_path: Path | None,
    title: str,
    variant: str | None = None,
    type_token: str | None = None,
) -> LoadResult:
    """High-level helper: load body for *kind_name* and emit info note if needed.

    Wraps :func:`load_body` and fills in the ``info`` note when ``has_template``
    is False (s0018 § 6).

    This is the primary entry point for the slash command's body-loading step.
    """
    if artifact_md_path is None:
        return LoadResult(
            body="",
            info=f"info: kind '{kind_name}' has no ARTIFACT.md; created with empty body.",
        )
    return load_body(artifact_md_path, title, variant=variant, type_token=type_token)
