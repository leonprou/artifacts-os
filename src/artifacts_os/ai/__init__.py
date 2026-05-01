"""artifacts-os ai module — install, list, and remove AI command assets.

Provides install machinery for copying or linking slash-command prompt
files (``*.md``) into a vault's ``.claude/commands/`` directory.

Depends on ``core`` only. No imports from ``cli``, ``views``, or ``tui``.

Spec: s2066-artifacts-os-ai-module
"""

from artifacts_os.ai.install import (
    install,
    uninstall,
    list_installed,
    InstallReport,
    InstalledAsset,
    AssetAction,
)

__all__ = [
    "install",
    "uninstall",
    "list_installed",
    "InstallReport",
    "InstalledAsset",
    "AssetAction",
]
