"""CLI settings extension for artifacts-os.

Reads the ``cli`` top-level key from artifacts.yaml and exposes
per-command defaults and command aliases.

Spec: s0003-artifacts-os-cli-module
"""

from dataclasses import dataclass, field

from artifacts_os.core.models import Settings


@dataclass(kw_only=True)
class CliSettings(Settings):
    """Settings subclass that adds typed access to the ``cli`` section.

    Construct via ``CliSettings.from_base(base)`` where *base* is the
    result of ``core.load_settings``.

    Attributes:
        defaults: Per-command default flag values.
                  e.g. ``{"show": {"editor": True}}``
        aliases:  Command name remappings applied before argparse.
                  e.g. ``{"ls": "list", "t": "status"}``
    """

    defaults: dict[str, dict] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_base(cls, base: Settings) -> "CliSettings":
        """Parse the ``cli`` section from *base.raw*.

        Returns a ``CliSettings`` with empty ``defaults`` and ``aliases``
        when the ``cli`` section is absent from the settings document.
        """
        cli_section: dict = base.raw.get("cli") or {}

        defaults: dict[str, dict] = {}
        for cmd, cmd_defaults in (cli_section.get("defaults") or {}).items():
            defaults[cmd] = dict(cmd_defaults or {})

        aliases: dict[str, str] = dict(cli_section.get("aliases") or {})

        return cls(
            layout_version=base.layout_version,
            project=base.project,
            raw=base.raw,
            defaults=defaults,
            aliases=aliases,
        )
