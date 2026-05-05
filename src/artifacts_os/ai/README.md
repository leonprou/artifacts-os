# artifacts-os AI module

Install and manage AI slash-command prompts and skills for Claude Code and OpenCode.

## Package layout

```
artifacts_os.ai
├── install.py               — install/uninstall/list_installed
├── claude/
│   ├── commands/            — *.md prompt files for Claude Code
│   └── skills/
│       └── artifacts-os/    — SKILL.md for Claude Code
└── opencode/
    └── commands/            — *.md prompt files for OpenCode (future)
```

## Python API

```python
from pathlib import Path
from artifacts_os.ai import install, uninstall, list_installed

vault = Path("/path/to/vault")

# Install commands and skills as symlinks (default)
report = install(vault)

# Install as copies
report = install(vault, mode="copy")

# Force overwrite of modified files
report = install(vault, mode="copy", force=True)

# Preview without writing
report = install(vault, dry_run=True)

# List what is installed (commands and skills)
assets = list_installed(vault)

# Remove
report = uninstall(vault)
```

## CLI surface

```
artifacts ai install [--target DIR] [--copy|--link] [--tool claude|opencode] [--force] [--dry-run]
artifacts ai uninstall [--target DIR] [--tool ...] [--dry-run]
artifacts ai list [--target DIR] [--tool ...]
```

## Source resolution

Command files are resolved via `importlib.resources.files("artifacts_os.ai.claude.commands")`.
Skill files are resolved via `importlib.resources.files("artifacts_os.ai.claude.skills")`.

- **Editable install** (`pip install -e .`): symlinks resolve into the source tree.
- **Wheel install**: symlinks resolve into `site-packages/artifacts_os/ai/claude/`.

Hatchling's `packages = ["src/artifacts_os"]` setting includes all files in the
package directory tree (not just `*.py`), so `*.md` files are shipped in the wheel
by default — no additional `include` rules are needed.

## Asset kinds

Two kinds of assets are managed:

| Kind | Namespace | Install path |
|---|---|---|
| Command | filename prefix `artifacts.` | `<tool_dir>/commands/artifacts.*.md` |
| Skill | directory prefix `artifacts-` | `<tool_dir>/skills/artifacts-os/SKILL.md` |

## Conflict policy

| Existing target | Mode | Action |
|---|---|---|
| Symlink → our package | any | Skip (idempotent) |
| Same content | copy | Skip (idempotent) |
| Different content, namespace match | link | Replace |
| Regular file in namespace | link | Refuse unless `--force` |
| Different content, namespace match | copy | Refuse unless `--force` |
| Outside namespace | any | Never touch |

Skills namespace check: parent directory name must start with `artifacts-`.
Commands namespace check: filename must start with `artifacts.`.

## Uninstall pruning

`uninstall()` removes namespaced skill files and prunes the now-empty
`<tool_dir>/skills/artifacts-os/` directory. If the directory contains
foreign files, it is kept.

## Module DAG

`ai` imports only `core`. Never imports `cli`, `views`, or `tui`.
