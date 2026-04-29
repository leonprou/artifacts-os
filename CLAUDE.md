# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Artifacts is an agentic harness for using and organizing artifacts.

## Artifact Storage

Store all project artifacts under `artifacts/`. The vault marker is
`artifacts/artifacts.yaml` — `find_vault_root` walks up from CWD until
it finds this file.

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

## Settings

Settings are parsed from `artifacts/artifacts.yaml` using a base-class +
extension-subclass pattern: `core` owns `Settings` and `load_settings`;
other modules extend via a `from_base` classmethod without coupling to
the library's release cycle. See [`docs/settings.md`](docs/settings.md)
for the full API, worked example, and extension rules.

## Coding Style

- Full type annotations on all public functions
- Dataclasses for models (`KindDef`, `ArtifactMeta`, `Artifact`)
- Atomic writes: `O_CREAT | O_EXCL` for create, `os.replace` for update

## Naming Conventions

- Numbered artifacts: `{prefix}{NNNN}-{slug}.md` (e.g. `t0042-fix-bug.md`)
- Non-numbered artifacts: `{slug}.md` (e.g. `researcher.md`)
- Slugs: lowercase, hyphenated, max 5 words
- Spec docs: `s{NNNN}-{topic}.md`

## Constraints

- `update` is frontmatter-only — body always preserved verbatim
- Module dependency DAG must be respected (no peer imports outside declared deps):
  `core` → `views` → `cli`, `tui`; `core` → `log` → `ai`
- No lifecycle logic in `cli` (status transitions stay in OpenStation)
- Doc updates accompany API changes — when a public API, re-export surface,
  or vault behaviour changes, update the corresponding doc in the same commit
