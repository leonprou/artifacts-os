# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Artifacts is an agentic harness for using and organizing artifacts.

## Artifact Storage

Store all project artifacts under `artifacts/`. The vault marker is
`artifacts.yaml` (at the project root) — `find_vault_root` walks up from
CWD until it finds this file.

## Project Structure

```
src/artifacts_os/
  __init__.py    # re-exports core public API
  core/          # fully implemented — storage, discovery, registry
  views/         # shipped — formatting layer, Rich rendering (spec: s2062)
  log/           # stub — JSONL operation log (spec: s2063)
  cli/           # shipped — argument parsing, command dispatch (spec: s2064)
  tui/           # stub — interactive terminal browser (spec: s2065)
  ai/            # stub — agent context and execution (spec: s2066)
tests/           # mirrors src; uses tmp_path + make_vault fixture, no mocking
docs/            # architecture overview, settings guide, per-module references
```

## Documentation First

Read `docs/` and module `README.md` files before answering questions or starting tasks.

## Common Commands

```bash
pip install -e ".[dev]"           # install with dev deps
pytest                            # run all tests
pytest tests/core/test_store.py  # run a single test file
```

## Release

The `release-changelog` skill reads this section to draft a new
release entry. Edit the tables and checklist when modules or
release flow change.

### Domain Categories

Listed most-impactful first. The skill emits an H3 subsection per
category that has entries in the release range. Empty categories
are omitted.

- **Architecture** — cross-cutting structural changes
- **Core** — `src/artifacts_os/core/`
- **Views** — `src/artifacts_os/views/`
- **CLI** — `src/artifacts_os/cli/`
- **TUI** — `src/artifacts_os/tui/`
- **AI** — `src/artifacts_os/ai/`
- **Log** — `src/artifacts_os/log/`
- **Install** — packaging and installer changes
- **Fix** — any commit with a `fix:` conventional prefix

### File Path Mapping

Longest-prefix match wins. A commit's category is determined by
its most-changed file's prefix; the `fix:` commit prefix overrides
the path mapping and routes to `Fix`.

| Path prefix | Category |
|-------------|----------|
| `src/artifacts_os/core/` | Core |
| `src/artifacts_os/views/` | Views |
| `src/artifacts_os/cli/` | CLI |
| `src/artifacts_os/tui/` | TUI |
| `src/artifacts_os/ai/` | AI |
| `src/artifacts_os/log/` | Log |
| `pyproject.toml` | Install |
| `setup.py` | Install |
| `install.sh` | Install |

### Checklist

The skill renders Step 8 from this list. `<VERSION>` is
substituted at draft time.

1. Update `version` in `pyproject.toml` to `<VERSION>`.
2. Write the CHANGELOG entry (the skill does this in Step 7).
3. Commit with subject `chore: release v<VERSION>`.
4. Push to `main` — CI handles the tag, GitHub Release, and
   PyPI publish.

### Exclusions

- subject: `^Merge `
- path: `.editorconfig`
- path: `.github/dependabot.yml`

## Settings

Settings are parsed from `artifacts.yaml` using a base-class +
extension-subclass pattern: `core` owns `Settings` and `load_settings`;
other modules extend via a `from_base` classmethod without coupling to
the library's release cycle. See [`docs/settings.md`](docs/settings.md)
for the full API, worked example, and extension rules.

## Coding Style

- Full type annotations on all public functions
- Dataclasses for models (`KindDef`, `ArtifactMeta`, `Artifact`)
- Atomic writes: `O_CREAT | O_EXCL` for create, `os.replace` for update

## Naming Conventions

- Numbered artifacts: filename `{prefix}{NNNN}-{slug}.md` (e.g.
  `t0042-fix-bug.md`); frontmatter `id: t0042`, `name: fix-bug`
- Non-numbered artifacts: filename `{slug}.md` (e.g. `researcher.md`);
  frontmatter `id: researcher`, `name: researcher`
- Slugs: lowercase, hyphenated, max 5 words
- Spec docs: `s{NNNN}-{topic}.md`
- The frontmatter `name` field stores the **slug only** — no `id`
  prefix. The full file stem (`{id}-{name}` for numbered kinds) is
  the canonical reference for resolution and wikilinks; derive it
  from `path.stem` rather than concatenating manually.

## Constraints

- `update` is frontmatter-only — body always preserved verbatim
- Module dependency DAG must be respected (no peer imports outside declared deps):
  `core` → `views` → `cli`, `tui`; `core` → `log` → `ai`
- No lifecycle logic in `cli` (status transitions stay in OpenStation)
- Doc updates accompany API changes — when a public API, re-export surface,
  or vault behaviour changes, update the corresponding doc in the same commit

## CLI Conventions

New `artifacts` commands and flag changes must match the established surface
shape. The reference commands are `list`, `show`, `create`, `status`,
`verify`, and `events`.

- **Flat verbs** — one-word top-level verb, no nested subcommands. Streaming,
  paging, and mode variants belong as flags on the verb, not as sub-verbs.
- **Default Rich table output** — same column/style language as
  `artifacts list`. `--json` / `-j` switches to raw JSON/JSONL for scripting.
- **`--tail [N]` is the universal "last N" primitive** — `nargs="?"` with a
  sensible `const` default (e.g. 50) and a sentinel `default` so the runner
  can distinguish absent / present-no-value / present-with-value. Slice is
  applied **after** filters and sorts. Do not introduce `--limit`-style
  opt-out caps.
- **Filter flags at the top level** — `--since`, `--event`, `--kind`,
  `--status`, etc. live directly on the verb's parser, never behind a
  subcommand.
