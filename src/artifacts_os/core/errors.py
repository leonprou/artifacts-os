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


class BlockedByPreHook(ArtifactError):
    """A pre-phase hook with blocking=true rejected the operation.

    CLI maps to exit code 11. The CRUD operation is aborted and the
    artifact file is left unchanged.
    """
