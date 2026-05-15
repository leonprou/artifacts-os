"""Exception hierarchy for the artbook module.

Spec: s0029-artbook-mvp-distribution-model §4.6
"""


class ArtbookError(Exception):
    """Base class for all artbook errors."""


class ManifestError(ArtbookError):
    """YAML parse failure, missing required field, version mismatch, or validation error."""


class FetchError(ArtbookError):
    """git clone failure.

    Attributes:
        returncode: The process exit code from git.
        stderr: The captured stderr text from git.
    """

    def __init__(self, message: str, returncode: int = -1, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class UnknownBookError(ArtbookError):
    """Raised by find_book when the requested name is not in the manifest."""


class DistroNotConfiguredError(ArtbookError):
    """artbook.distro_url is missing or empty in artifacts.yaml."""
