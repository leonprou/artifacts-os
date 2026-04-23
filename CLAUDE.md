# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Artifacts is an agentic harness for using and organizing artifacts.

## Artifact Storage

Store all project artifacts under `artifacts/`, not `openstation/`.  
Note: code currently writes to `openstation/` — this rename is in progress.

## Project Structure

```
src/artifacts_os/
  __init__.py    # re-exports core public API
  core/          # fully implemented — storage, discovery, registry
  views/         # stub — column layout, rendering (spec: s2062)
  log/           # stub — JSONL operation log (spec: s2063)
  cli/           # stub — argument parsing, command dispatch (spec: s2064)
  tui/           # stub — interactive terminal browser (spec: s2065)
  ai/            # stub — agent context and execution (spec: s2066)
tests/           # mirrors src; uses tmp_path + make_vault fixture, no mocking
docs/            # specs: s2060 (architecture), s2061 (module system), s2062–s2066
```

## Common Commands

```bash
pip install -e ".[dev]"           # install with dev deps
pytest                            # run all tests
pytest tests/core/test_store.py  # run a single test file
```

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
