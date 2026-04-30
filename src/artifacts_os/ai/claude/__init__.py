"""Claude Code integration assets for artifacts-os.

Ships markdown command files and skill prompts that get installed into
a vault's `.claude/` directory by `artifacts ai install`.

This package is consumed at runtime via
`importlib.resources.files("artifacts_os.ai.claude")`. Sub-packages
(`commands/`, future `skills/`) hold the actual prompt assets.
"""

__all__: list[str] = []
