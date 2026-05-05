"""Install machinery for artifacts-os AI commands and skills.

Installs *.md slash-command files from the package into a vault's
.claude/commands/ (or .opencode/commands/) directory, and SKILL.md
files into a vault's .claude/skills/artifacts-os/ directory.
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
_SKILL_NS_PREFIX = "artifacts-"
# Exact skill directory names that do not carry the artifacts- prefix
# but are still owned and managed by this package.
_SKILL_NS_EXACT: frozenset[str] = frozenset({"release-changelog"})


def _is_namespaced(filename: str) -> bool:
    """True if filename belongs to our commands namespace."""
    return filename.startswith(_COMMAND_PREFIX)


def _is_skill_namespace(dirname: str) -> bool:
    """True if a skills sub-directory belongs to our namespace."""
    return dirname.startswith(_SKILL_NS_PREFIX) or dirname in _SKILL_NS_EXACT


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


def _source_skill_files(tool: str) -> list[tuple[str, Path]]:
    """Return (namespace_dir, skill_md_path) for each SKILL.md in the package.

    Enumerates ``artifacts_os.ai.{tool}.skills`` sub-directories; every
    immediate sub-directory whose name starts with ``artifacts-`` is treated
    as one installable unit.  Only the ``SKILL.md`` file inside it is
    returned.
    """
    import importlib.resources as ir

    pkg_name = f"artifacts_os.ai.{tool}.skills"
    try:
        pkg = ir.files(pkg_name)
    except (ModuleNotFoundError, AttributeError):
        return []

    results = []
    for subdir in pkg.iterdir():
        ns = getattr(subdir, "name", None)
        if ns and _is_skill_namespace(ns):
            skill_file = subdir / "SKILL.md"
            try:
                p = Path(str(skill_file))
                if p.exists():
                    results.append((ns, p))
            except Exception:
                pass
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
    asset_kind: Literal["command", "skill"] = "command",
) -> AssetAction:
    """Determine what action to take for a single file.

    ``asset_kind`` controls the namespace check:
    - ``"command"``: filename must start with ``artifacts.``
    - ``"skill"``: parent directory name must start with ``artifacts-``
    """
    # Case: file doesn't exist yet
    if not target.exists() and not target.is_symlink():
        action: ActionKind = "install-link" if mode == "link" else "install-copy"
        return AssetAction(source=source, target=target, action=action, reason="new file")

    # Case: not in our namespace — never touch
    if asset_kind == "command" and not _is_namespaced(target.name):
        return AssetAction(
            source=source, target=target, action="keep-foreign",
            reason="not in artifacts-os namespace",
        )
    if asset_kind == "skill" and not _is_skill_namespace(target.parent.name):
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
    target_dir = action.target.parent
    target_dir.mkdir(parents=True, exist_ok=True)

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
    """Install AI command files and skill files into target vault's tool directory.

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
        # Commands
        commands_dir = tool_dir / "commands"
        for filename, source_path in _source_files(tool_name):
            target_path = commands_dir / filename
            action = _plan_action(source_path, target_path, mode, force, asset_kind="command")
            report.actions.append(action)
            if not dry_run:
                _execute_action(action)

        # Skills
        for skill_ns, source_path in _source_skill_files(tool_name):
            target_path = tool_dir / "skills" / skill_ns / "SKILL.md"
            action = _plan_action(source_path, target_path, mode, force, asset_kind="skill")
            report.actions.append(action)
            if not dry_run:
                _execute_action(action)

        # Orphan pruning — remove broken owned-skill symlinks whose package source
        # was deleted (e.g. artifacts-release → release-changelog migration).
        skills_root = tool_dir / "skills"
        if skills_root.exists():
            for ns_dir in sorted(skills_root.iterdir()):
                if not _is_skill_namespace(ns_dir.name):
                    continue
                skill_file = ns_dir / "SKILL.md"
                if skill_file.is_symlink() and not skill_file.exists():
                    orphan_action = AssetAction(
                        source=skill_file,
                        target=skill_file,
                        action="remove",
                        reason="orphaned skill symlink (source removed from package)",
                    )
                    report.actions.append(orphan_action)
                    if not dry_run:
                        _execute_action(orphan_action)
                        try:
                            ns_dir.rmdir()
                        except OSError:
                            pass  # non-empty dir — leave it

    return report


def uninstall(
    target: Path,
    *,
    tool: str = "claude",
    dry_run: bool = False,
) -> InstallReport:
    """Remove artifacts-os commands and skills from target vault's tool directory.

    Only removes namespaced files (prefix ``artifacts.`` for commands,
    dir prefix ``artifacts-`` for skills).  Foreign files are never touched.
    The ``artifacts-os/`` skills directory is pruned when left empty.

    Args:
        target: Vault root.
        tool: Tool directory to clean ("claude" or "opencode").
        dry_run: Plan without writing anything.

    Returns:
        InstallReport describing all planned/executed actions.
    """
    report = InstallReport()

    # --- Commands ---
    commands_dir = target / f".{tool}" / "commands"
    if commands_dir.exists():
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

    # --- Skills ---
    skills_root = target / f".{tool}" / "skills"
    if skills_root.exists():
        for ns_dir in sorted(skills_root.iterdir()):
            if not _is_skill_namespace(ns_dir.name):
                continue
            skill_file = ns_dir / "SKILL.md"
            if not (skill_file.exists() or skill_file.is_symlink()):
                continue

            source = skill_file.resolve() if skill_file.is_symlink() else skill_file
            action = AssetAction(
                source=source, target=skill_file, action="remove",
                reason="owned by artifacts-os",
            )
            report.actions.append(action)
            if not dry_run:
                _execute_action(action)
                # Prune empty namespace dir
                try:
                    ns_dir.rmdir()
                except OSError:
                    pass  # non-empty (foreign files present) — leave it

    return report


def list_installed(target: Path, *, tool: str = "claude") -> list[InstalledAsset]:
    """Return InstalledAsset for each installed artifacts-os command or skill.

    Args:
        target: Vault root.
        tool: Tool directory to inspect ("claude" or "opencode").

    Returns:
        Sorted list of InstalledAsset objects (empty if none installed).
    """
    assets: list[InstalledAsset] = []

    # --- Commands ---
    commands_dir = target / f".{tool}" / "commands"
    if commands_dir.exists():
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

    # --- Skills ---
    skills_root = target / f".{tool}" / "skills"
    if skills_root.exists():
        for ns_dir in sorted(skills_root.iterdir()):
            if not _is_skill_namespace(ns_dir.name):
                continue
            skill_file = ns_dir / "SKILL.md"
            if not (skill_file.exists() or skill_file.is_symlink()):
                continue

            if skill_file.is_symlink():
                s_mode: Literal["link", "copy"] = "link"
                s_source = Path(os.readlink(skill_file))
                if not s_source.is_absolute():
                    s_source = (skill_file.parent / s_source).resolve()
                else:
                    s_source = s_source.resolve()
            else:
                s_mode = "copy"
                s_source = skill_file.resolve()

            assets.append(InstalledAsset(
                path=skill_file.resolve(), mode=s_mode, source=s_source,
            ))

    return assets
