"""Install machinery for artifacts-os AI commands and skills.

Installs *.md slash-command files from the package into a vault's
.claude/commands/ (or .opencode/commands/) directory.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

ActionKind = Literal[
    "install-link", "install-copy", "replace-link",
    "skip", "refuse", "keep-foreign", "remove",
]


@dataclass
class AssetAction:
    source: Path
    target: Path
    action: ActionKind
    reason: str


@dataclass
class InstallReport:
    actions: list[AssetAction] = field(default_factory=list)

    @property
    def installed(self) -> int:
        return sum(
            1 for a in self.actions
            if a.action in ("install-link", "install-copy", "replace-link")
        )

    @property
    def skipped(self) -> int:
        return sum(1 for a in self.actions if a.action == "skip")

    @property
    def refused(self) -> int:
        return sum(1 for a in self.actions if a.action == "refuse")

    @property
    def removed(self) -> int:
        return sum(1 for a in self.actions if a.action == "remove")


@dataclass
class InstalledAsset:
    path: Path
    mode: Literal["link", "copy"]
    source: Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_COMMAND_PREFIX = "artifacts."


def _is_namespaced(filename: str) -> bool:
    return filename.startswith(_COMMAND_PREFIX)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _same_content(a: Path, b: Path) -> bool:
    try:
        return _sha256(a) == _sha256(b)
    except OSError:
        return False


def _source_files(tool: str) -> list[tuple[str, Path]]:
    """Return (filename, resolved_path) for each *.md command in the package."""
    import importlib.resources as ir

    pkg_name = f"artifacts_os.ai.{tool}.commands"
    try:
        pkg = ir.files(pkg_name)
    except (ModuleNotFoundError, AttributeError):
        return []

    results = []
    for item in pkg.iterdir():
        name = getattr(item, "name", None)
        if name and name.endswith(".md") and name.startswith(_COMMAND_PREFIX):
            results.append((name, Path(str(item))))
    return sorted(results)


def _detect_tool_dirs(target: Path) -> list[tuple[str, Path]]:
    """Return [(tool_name, tool_dir)] based on what exists in target."""
    result = []
    for tool in ("claude", "opencode"):
        d = target / f".{tool}"
        if d.exists():
            result.append((tool, d))
    if not result:
        # Default: claude
        result.append(("claude", target / ".claude"))
    return result


def _plan_action(
    source: Path,
    target: Path,
    mode: Literal["link", "copy"],
    force: bool,
) -> AssetAction:
    """Determine what action to take for a single file."""
    # Case: file doesn't exist yet
    if not target.exists() and not target.is_symlink():
        action: ActionKind = "install-link" if mode == "link" else "install-copy"
        return AssetAction(source=source, target=target, action=action, reason="new file")

    # Case: not in our namespace — never touch
    if not _is_namespaced(target.name):
        return AssetAction(
            source=source, target=target, action="keep-foreign",
            reason="not in artifacts-os namespace",
        )

    # File is owned by us
    if target.is_symlink():
        try:
            resolved = target.resolve()
            if resolved == source.resolve():
                # Symlink already points into our package
                return AssetAction(
                    source=source, target=target, action="skip",
                    reason="symlink already points to package",
                )
        except OSError:
            pass
        # Stale or different symlink
        if mode == "link":
            return AssetAction(
                source=source, target=target, action="replace-link",
                reason="replace stale symlink",
            )
        else:
            if force:
                return AssetAction(
                    source=source, target=target, action="install-copy",
                    reason="forced copy replaces symlink",
                )
            return AssetAction(
                source=source, target=target, action="refuse",
                reason="owned symlink differs; use --force to overwrite",
            )
    else:
        # Regular file (previously copied)
        if mode == "copy":
            if _same_content(target, source):
                return AssetAction(
                    source=source, target=target, action="skip",
                    reason="same content",
                )
            if force:
                return AssetAction(
                    source=source, target=target, action="install-copy",
                    reason="forced overwrite",
                )
            return AssetAction(
                source=source, target=target, action="refuse",
                reason="file content differs from package; use --force to overwrite",
            )
        else:
            # link mode: copy-to-link upgrade is a write
            if force:
                return AssetAction(
                    source=source, target=target, action="replace-link",
                    reason="forced copy-to-link upgrade",
                )
            return AssetAction(
                source=source, target=target, action="refuse",
                reason="copy-to-link upgrade requires --force",
            )


def _execute_action(action: AssetAction) -> None:
    """Write action to disk (called only when dry_run=False)."""
    if action.action in ("skip", "keep-foreign", "refuse"):
        return

    if action.action == "remove":
        if action.target.exists() or action.target.is_symlink():
            action.target.unlink()
        return

    # install-link / install-copy / replace-link
    commands_dir = action.target.parent
    commands_dir.mkdir(parents=True, exist_ok=True)

    # Remove existing file
    if action.target.exists() or action.target.is_symlink():
        action.target.unlink()

    if action.action in ("install-link", "replace-link"):
        os.symlink(action.source.resolve(), action.target)
    else:
        shutil.copy2(str(action.source), str(action.target))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def install(
    target: Path,
    *,
    mode: Literal["link", "copy"] = "link",
    tool: Literal["claude", "opencode"] | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> InstallReport:
    """Install AI command files into target vault's tool directory.

    Args:
        target: Vault root (must contain artifacts/artifacts.yaml).
        mode: "link" creates symlinks; "copy" copies files.
        tool: Target tool. If None, auto-detects from existing dirs.
        force: Overwrite files that differ from package version.
        dry_run: Plan without writing anything.

    Returns:
        InstallReport describing all planned/executed actions.

    Raises:
        ValueError: If target is not an initialised vault.
    """
    if not (target / "artifacts" / "artifacts.yaml").is_file():
        raise ValueError(
            f"Not an artifacts-os vault: {target}. Run `artifacts init` first."
        )

    report = InstallReport()

    if tool is not None:
        tool_dirs: list[tuple[str, Path]] = [(tool, target / f".{tool}")]
    else:
        tool_dirs = _detect_tool_dirs(target)

    for tool_name, tool_dir in tool_dirs:
        commands_dir = tool_dir / "commands"
        for filename, source_path in _source_files(tool_name):
            target_path = commands_dir / filename
            action = _plan_action(source_path, target_path, mode, force)
            report.actions.append(action)
            if not dry_run:
                _execute_action(action)

    return report


def uninstall(
    target: Path,
    *,
    tool: str = "claude",
    dry_run: bool = False,
) -> InstallReport:
    """Remove artifacts-os commands from target vault's tool directory.

    Only removes namespaced files (prefix `artifacts.`). Foreign files
    are never touched.

    Args:
        target: Vault root.
        tool: Tool directory to clean ("claude" or "opencode").
        dry_run: Plan without writing anything.

    Returns:
        InstallReport describing all planned/executed actions.
    """
    report = InstallReport()
    commands_dir = target / f".{tool}" / "commands"

    if not commands_dir.exists():
        return report

    for path in sorted(commands_dir.iterdir()):
        if not (path.name.startswith(_COMMAND_PREFIX) and path.name.endswith(".md")):
            report.actions.append(AssetAction(
                source=path, target=path, action="keep-foreign",
                reason="not in artifacts-os namespace",
            ))
            continue

        source = path.resolve() if path.is_symlink() else path
        action = AssetAction(
            source=source, target=path, action="remove",
            reason="owned by artifacts-os",
        )
        report.actions.append(action)
        if not dry_run:
            _execute_action(action)

    return report


def list_installed(target: Path, *, tool: str = "claude") -> list[InstalledAsset]:
    """Return InstalledAsset for each installed artifacts-os command.

    Args:
        target: Vault root.
        tool: Tool directory to inspect ("claude" or "opencode").

    Returns:
        Sorted list of InstalledAsset objects (empty if none installed).
    """
    commands_dir = target / f".{tool}" / "commands"

    if not commands_dir.exists():
        return []

    assets = []
    for path in sorted(commands_dir.iterdir()):
        if not (path.name.startswith(_COMMAND_PREFIX) and path.name.endswith(".md")):
            continue

        if path.is_symlink():
            mode: Literal["link", "copy"] = "link"
            source = Path(os.readlink(path))
            if not source.is_absolute():
                source = (path.parent / source).resolve()
            else:
                source = source.resolve()
        else:
            mode = "copy"
            source = path.resolve()

        assets.append(InstalledAsset(path=path.resolve(), mode=mode, source=source))

    return assets
