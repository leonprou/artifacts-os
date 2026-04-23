---
kind: task
id: t0002
name: write-readme-md-for-artifacts
type: documentation
status: done
assignee: author
owner: user
created: 2026-04-22
started: 2026-04-22
completed: 2026-04-23
---

# Write Readme.Md For Artifacts-Os

## Requirements

Write a `README.md` for the `artifacts-os` Python package at the repo root.

### Source material

- `CLAUDE.md` — project overview, structure, commands, constraints
- `artifacts/specs/s0002-artifacts-os-architecture.md` — authoritative architecture reference
- `artifacts/specs/s0005-artifacts-os-module-system.md` — module system design
- `pyproject.toml` — package name, version, dependencies, entry points

### Content outline

1. **Title + one-line description** — what artifacts-os is
2. **Install** — `pip install artifacts-os` (or editable: `pip install -e ".[dev]"`)
3. **Quick start** — minimal usage example showing core API
4. **Project structure** — directory tree matching CLAUDE.md § Project Structure
5. **Development** — how to run tests (`pytest`), coding conventions
6. **Architecture** — brief pointer to `artifacts/specs/` for deep dives

### Constraints

- No marketing language — factual and concise
- Match the tone of `CLAUDE.md`
- Keep it under ~100 lines; link to specs for depth

## Verification

- [ ] `README.md` exists at repo root
- [ ] Covers install, quick start, structure, and development sections
- [ ] No content contradicts `CLAUDE.md` or the architecture spec
- [ ] Renders correctly as Markdown (no broken links or malformed headings)

## Progress

### 2026-04-22 — author
> time: 22:24

Wrote README.md (~90 lines) covering install, quick start, CLI, project structure, development, and architecture sections. All source material cross-checked.

## Findings

Wrote `README.md` at repo root (~90 lines). Covers all required sections:

- **Install** — standard and editable installs; lists optional extras from `pyproject.toml`
- **Quick start** — end-to-end example using `find_vault_root`, `Registry`, `KindDef`, `create`, `get`, `list_artifacts`
- **CLI** — four representative `artifacts` commands
- **Project structure** — directory tree aligned with `CLAUDE.md` § Project Structure and actual `src/` layout
- **Development** — install command, pytest invocations, coding conventions (type annotations, dataclasses, atomic writes, no mocking)
- **Architecture** — links to `s0002` and `s0005` in `artifacts/specs/`

Source cross-checked against `pyproject.toml` (entry point, extras), `s0002` (public API, module contracts), `s0005` (module inventory, dependency DAG), and `CLAUDE.md` (structure, commands, constraints). No contradictions found.
