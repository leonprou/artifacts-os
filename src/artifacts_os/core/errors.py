"""Error hierarchy for artifacts-os.

Spec: s2060-artifacts-os-architecture § errors.py
"""


class ArtifactError(Exception):
    """Base exception. CLI maps to exit code 1."""


class NotFoundError(ArtifactError):
    """Artifact not found. CLI maps to exit code 3."""


class AmbiguousError(ArtifactError):
    """Query matched multiple artifacts. CLI maps to exit code 4.

    The message includes the list of candidate paths.
    """


class ValidationError(ArtifactError):
    """Frontmatter failed schema or status validation. CLI maps to exit code 2."""
