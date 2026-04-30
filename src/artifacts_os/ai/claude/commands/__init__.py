"""Markdown command prompts for Claude Code's `/artifacts.*` surface.

Each `*.md` file in this package is a slash-command prompt that gets
installed into a vault's `.claude/commands/` directory. Files are
discovered as package data via
`importlib.resources.files("artifacts_os.ai.claude.commands")`.
"""

__all__: list[str] = []
