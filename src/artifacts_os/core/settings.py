"""Settings loader for artifacts-os.

Spec: s0010-core-settings-module-spec
"""

from pathlib import Path

import yaml

from artifacts_os.core.models import ProjectConfig, Settings


class UnsupportedSchemaVersion(ValueError):
    """Raised when layout_version is missing or not in the supported set."""


_SUPPORTED_VERSIONS = {1}


def load_settings(path: Path) -> Settings:
    """Read and parse the settings file at *path*, returning a ``Settings``.

    Raises:
        UnsupportedSchemaVersion: if ``layout_version`` is absent or unsupported.
        KeyError: if the ``project`` section is absent.
    """
    raw: dict = yaml.safe_load(path.read_text()) or {}

    # Validate layout_version
    if "layout_version" not in raw:
        raise UnsupportedSchemaVersion("missing layout_version")
    version = raw["layout_version"]
    if version not in _SUPPORTED_VERSIONS:
        raise UnsupportedSchemaVersion(f"unsupported version {version}")

    # Build ProjectConfig from required project section
    project_data: dict = raw["project"]  # KeyError if absent
    project = ProjectConfig(
        name=project_data["name"],
        alias=project_data.get("alias"),
    )

    return Settings(
        layout_version=version,
        project=project,
        raw=raw,
    )
