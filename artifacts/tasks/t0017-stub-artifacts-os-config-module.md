---
kind: task
id: t0017
name: stub-artifacts-os-config-module
type: implementation
status: rejected
assignee: developer
owner: user
depends_on:
  - "[[t0016-re-scope-s0007-views-spec]]"
created: 2026-04-26
---

# Stub Artifacts_Os.Config Module

## Context

t0016 re-scopes the `views` module and introduces a new
`artifacts_os.config` module that owns settings-file loading
(`artifacts.yaml` / `openstation.yaml`). This task creates the empty
module skeleton, parallel to the existing stubs (`views`, `log`, `cli`,
`tui`, `ai`).

This is a stub — no loading logic. The implementation lands in a
follow-up task once the spec from t0016 is in place.

## Requirements

1. Create `src/artifacts_os/config/__init__.py` with module docstring
   and reference to the spec produced by t0016.
2. Create `src/artifacts_os/config/README.md` describing module purpose,
   spec reference, and a "Not Yet Implemented" section listing the
   public API sketched in the spec. Match the shape of the other
   module READMEs.
3. Create `tests/config/__init__.py` (empty package init).
4. Update `CLAUDE.md` Project Structure section:
   - Add `config/` to the `src/artifacts_os/` tree with its spec ID.
   - Update the module dependency DAG comment to reflect the new
     module's position (per the spec produced by t0016).

## Constraints

- Stub must import cleanly: `from artifacts_os import config` works.
- `pytest tests/config/` passes (no tests yet, just discovery).
- No loading logic — `load_settings` and any dataclasses come in a
  follow-up implementation task.

## Source material

- The spec produced by t0016 (`artifacts/specs/sNNNN-artifacts-os-config-module.md`)
- `src/artifacts_os/views/__init__.py` — reference for module docstring shape
- `src/artifacts_os/log/__init__.py`, `cli/__init__.py`, etc. — other stubs
- `CLAUDE.md` — project structure and DAG

## Verification

- [ ] `src/artifacts_os/config/__init__.py` exists with module docstring
      and spec reference
- [ ] `src/artifacts_os/config/README.md` exists with purpose section,
      spec reference, and "Not Yet Implemented" content
- [ ] `tests/config/__init__.py` exists; `pytest tests/config/` passes
- [ ] `CLAUDE.md` Project Structure tree lists `config/` with spec ID
- [ ] `CLAUDE.md` module dependency DAG comment reflects the new module
- [ ] `from artifacts_os import config` succeeds
