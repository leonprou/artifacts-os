---
kind: spec
name: artifacts-os-cli-module
status: draft
created: 2026-04-20
task: "[[0001-migrate-docs-specs-to-openstation]]"
agent: manual
id: s0003
---

# artifacts-os: cli Module

High-level spec for `artifacts_os.cli`.

## Purpose

Expose `artifacts-os` core capabilities as a command-line tool. Handles
argument parsing and command dispatch; delegates storage to core and
rendering to `views`. Contains no lifecycle logic.

## Dependencies

- `artifacts_os` (core)
- `artifacts_os.views`
- `rich>=13` (via views)

## Entry Point

```toml
[project.scripts]
artifacts = "artifacts_os.cli:main"
```

```python
# artifacts_os/cli/__init__.py
def main() -> None: ...
```

## Command Set

| Command | Synopsis | Core calls |
|---------|----------|-----------|
| `list` | `list [--kind KIND] [--status S] [--fields F] [--view V] [-q\|-j]` | `list_artifacts` + `views.render_table` |
| `show` | `show <ref> [--kind KIND] [-j\|-e]` | `get` |
| `create` | `create <title> [--kind KIND] [--body B\|--body-file P] [--name SLUG] [--assignee U] [--owner U] [--parent REF] [--depends-on REF …] [--type T] [--fields F] [--dry-run]` | `create` |
| `status` | `status <ref> <new-status>` | `update(status=...)` |
| `verify` | `verify [<ref>] [--kind KIND] [--all] [-j]` | `list_artifacts` + frontmatter checks |
| `agents` | `agents [list\|-show <name>] [-q\|-j\|-e]` | `list_artifacts(kind="agent")` / `get` |

### `create` flags

| Flag | Description |
|------|-------------|
| `--body BODY`, `-b` | Initial body text |
| `--body-file PATH` | Read body from PATH; `'-'` reads from stdin |
| `--name SLUG` | Override the auto-derived slug; controls the name portion of the filename |
| `--assignee USER` | Set `assignee` in frontmatter |
| `--owner USER` | Set `owner` in frontmatter |
| `--parent REF` | Set `parent`; bare refs auto-wrapped as `[[REF]]` |
| `--depends-on REF` | Add a dependency (repeatable); bare refs auto-wrapped |
| `--type TYPE` | Set `type` in frontmatter |
| `--fields KEY=VALUE`, `-f` | Extra frontmatter; comma values produce lists; wikilink wrapping applies to `parent` and `depends_on` |
| `--dry-run`, `-n` | Print resolved frontmatter + body without writing |

**Wikilink convention** — `parent` and `depends_on` fields store
Obsidian-style wikilinks (`[[ref]]`). The CLI auto-wraps bare refs and
leaves already-wrapped values unchanged.

### Output modes

`-q` / `--quiet` — one name per line  
`-j` / `--json` — JSON array / object  
`-e` / `--editor` — open in `$EDITOR`

Output flags are mutually exclusive. Default is rich table via `views`.

### `--fields` and `--view`

`--fields` accepts a field spec string (`id,name,status:date as Date`),
passed directly to `views.parse_field_specs`.

`--view` loads a named `ViewConfig` from the project settings file via
`views.load_views`. Explicit flags override view defaults.

## Argument Parsing

Uses stdlib `argparse`. No `click` or `typer` dependency.

Sub-commands are registered as `argparse` subparsers. Each command lives
in its own module under `artifacts_os/cli/commands/`.

## Error Handling

| Exception | Exit code | Output |
|-----------|-----------|--------|
| `NotFoundError` | 3 | `error: <message>` to stderr |
| `AmbiguousError` | 4 | `error: <message>` + candidate list to stderr |
| `ValidationError` | 2 | `error: <message>` to stderr |
| `ValueError` (bad args) | 1 | argparse usage message |

## Project Discovery

`cli` calls `find_vault_root()` at startup. If no root is found, exits
with code 2 and message `"error: not in an artifacts-os project"`.

`Registry` is constructed once per invocation and passed to command
handlers. Kind definitions and `meta` config (column layout, etc.) are
the caller application's responsibility — `cli` exposes a
`register_kinds(kinds: list[KindDef])` hook called before `main()`
dispatches.

## Scope Boundary

- **In:** argument parsing, command dispatch, exit codes, output formatting
- **Out:** lifecycle transition rules, hook execution, session tracking,
  agent execution (`ai` module handles that)

## Deferred

| Item | Notes |
|------|-------|
| `register_kinds` hook API | How host apps inject their KindDefs into the CLI |
| `run` command | Depends on `ai` module spec |
| `logs` / `sessions` commands | Depends on `log` module spec |
