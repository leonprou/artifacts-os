"""Hook action runners: shell, notify, file-drop.

Each action is a frozen dataclass with a ``run(payload, env)`` method.
Actions are registered in a module-level registry keyed by type name.

Spec: s0025-artifact-events § C5
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import Any


# ---------------------------------------------------------------------------
# Action registry
# ---------------------------------------------------------------------------

_ACTION_REGISTRY: dict[str, type["BaseAction"]] = {}


def register(name: str, cls: type["BaseAction"]) -> None:
    """Register an action class under *name*.

    The ``type`` key in the hooks YAML maps to this name.
    """
    _ACTION_REGISTRY[name] = cls


def from_config(cfg: dict[str, Any]) -> "BaseAction":
    """Build an action instance from a YAML action dict.

    Raises ``ValueError`` for unknown or missing ``type``.
    """
    action_type = cfg.get("type")
    if not action_type:
        raise ValueError("action missing 'type' field")
    cls = _ACTION_REGISTRY.get(action_type)
    if cls is None:
        raise ValueError(f"unknown action type: {action_type!r}")
    return cls.from_config(cfg)


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class BaseAction:
    """Protocol for action runners."""

    def run(self, payload: dict[str, Any], env: dict[str, str]) -> None:
        """Execute the action.  Raises on failure."""
        raise NotImplementedError

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "BaseAction":
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Shell action
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShellAction(BaseAction):
    """Run a shell command via ``/bin/sh -c``."""

    command: str
    timeout: int = 30

    def run(self, payload: dict[str, Any], env: dict[str, str]) -> None:
        full_env = {**os.environ, **env}
        result = subprocess.run(
            ["/bin/sh", "-c", self.command],
            env=full_env,
            timeout=self.timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(f"exit {result.returncode}: shell hook failed")

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "ShellAction":
        cmd = cfg.get("command", "")
        if not cmd:
            raise ValueError("shell action missing 'command'")
        return cls(command=cmd, timeout=int(cfg.get("timeout", 30)))

    def to_dict(self) -> dict[str, Any]:
        return {"type": "shell", "command": self.command, "timeout": self.timeout}


register("shell", ShellAction)


# ---------------------------------------------------------------------------
# Notify action
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NotifyAction(BaseAction):
    """Send a desktop notification, falling back to terminal bell."""

    title: str = ""
    body: str = ""
    sound: bool = False
    mechanism: str = "auto"  # "auto" | "bell" | "desktop" | "osc9" | "file"

    def run(self, payload: dict[str, Any], env: dict[str, str]) -> None:
        title = _expand(self.title, env)
        body = _expand(self.body, env)

        if self.mechanism == "bell":
            _bell()
            return

        plat = platform.system()
        sent = False
        if self.mechanism in ("auto", "desktop"):
            if plat == "Darwin":
                sent = _macos_notify(title, body)
            elif plat == "Linux":
                sent = _linux_notify(title, body)
            elif plat == "Windows":
                sent = _windows_notify(title, body)

        if not sent:
            _bell()

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "NotifyAction":
        return cls(
            title=cfg.get("title", ""),
            body=cfg.get("body", ""),
            sound=bool(cfg.get("sound", False)),
            mechanism=cfg.get("mechanism", "auto"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "notify",
            "title": self.title,
            "body": self.body,
            "sound": self.sound,
            "mechanism": self.mechanism,
        }


def _expand(text: str, env: dict[str, str]) -> str:
    """Expand ``$VAR`` references using *env*."""
    try:
        return Template(text).safe_substitute(env)
    except Exception:
        return text


def _bell() -> None:
    sys.stderr.write("\a")
    sys.stderr.flush()


def _macos_notify(title: str, body: str) -> bool:
    if not shutil.which("osascript"):
        return False
    script = f'display notification {json.dumps(body)} with title {json.dumps(title)}'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception:
        return False


def _linux_notify(title: str, body: str) -> bool:
    if not shutil.which("notify-send"):
        return False
    try:
        subprocess.run(
            ["notify-send", title, body],
            check=True,
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception:
        return False


def _windows_notify(title: str, body: str) -> bool:
    if not shutil.which("powershell"):
        return False
    script = (
        f"New-BurntToastNotification -Text '{title}', '{body}'"
    )
    try:
        subprocess.run(
            ["powershell", "-Command", script],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return True
    except Exception:
        return False


register("notify", NotifyAction)


# ---------------------------------------------------------------------------
# File-drop action
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileDropAction(BaseAction):
    """Write the event payload to a file.

    ``path`` may contain ``{event}``, ``{ts}``, ``{kind}``, ``{id}``
    substitutions.  ``payload_mode`` is ``"full"`` (default) or
    ``"summary"``.
    """

    path: str
    payload_mode: str = "full"  # "full" | "summary"

    def run(self, payload: dict[str, Any], env: dict[str, str]) -> None:
        # Resolve path template substitutions.
        ts = env.get("ART_TS", "")
        event_str = env.get("ART_EVENT", "")
        kind = env.get("ART_KIND", "")
        art_id = env.get("ART_ID", "")
        resolved = self.path.format(
            event=event_str,
            ts=ts,
            kind=kind,
            id=art_id,
        )
        dest = Path(resolved)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if self.payload_mode == "summary":
            record = {
                "event": event_str,
                "kind": kind,
                "id": art_id,
                "ts": ts,
            }
        else:
            record = {"ts": ts, "event": event_str, **payload}

        dest.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "FileDropAction":
        path = cfg.get("path", "")
        if not path:
            raise ValueError("file-drop action missing 'path'")
        return cls(path=path, payload_mode=cfg.get("payload", "full"))

    def to_dict(self) -> dict[str, Any]:
        return {"type": "file-drop", "path": self.path, "payload": self.payload_mode}


register("file-drop", FileDropAction)
