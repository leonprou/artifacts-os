---
kind: task
id: t0003
name: write-readme-for-core-module
type: documentation
status: done
assignee: author
owner: user
created: 2026-04-22
started: 2026-04-22
completed: 2026-04-23
---

# Write Readme For Core Module

## Requirements

Write `src/artifacts_os/core/README.md` documenting the `core` module.

### Source material

- `artifacts/specs/s0002-artifacts-os-architecture.md` — authoritative implementation reference
- `artifacts/specs/s0005-artifacts-os-module-system.md` — module system and dependency rules
- `src/artifacts_os/core/` — fully implemented source code

### Content outline

1. **Purpose** — storage, discovery, and registry; foundational layer for all other modules
2. **Public API** — key classes and functions exported via `__init__.py` (`KindDef`, `ArtifactMeta`, `Artifact`, and main operations)
3. **Sub-components** — brief description of each file/submodule (store, discovery, registry)
4. **Usage examples** — minimal code snippets showing create, read, update, discover
5. **Constraints** — atomic write rules (`O_CREAT | O_EXCL`, `os.replace`), no peer imports

### Constraints

- Derive content from actual source code and specs — do not invent API surface
- Concise; link to architecture spec for deep dives

## Verification

- [ ] `src/artifacts_os/core/README.md` exists
- [ ] Public API section matches actual exports in `__init__.py`
- [ ] Usage examples are runnable (no fictional method names)
- [ ] Constraints section mentions atomic write rules

## Progress

### 2026-04-22 — author
> time: 22:27

Wrote src/artifacts_os/core/README.md — all sections from actual source: purpose, public API tables, sub-component descriptions, runnable usage examples, atomic-write constraints. Transitioning to review.

## Findings

Wrote `src/artifacts_os/core/README.md` derived entirely from the
actual source code (no invented API). The README covers:

- **Purpose** — storage, discovery, registry; foundational layer
- **Public API** — tables for models, CRUD functions, discovery
  functions, Registry methods, vault helper, and error hierarchy;
  all entries match the `__init__.py` `__all__` list exactly
- **Usage examples** — end-to-end snippet: Registry setup, create,
  get, update, list_artifacts (all real function/class names)
- **Constraints** — `O_CREAT | O_EXCL` for create, `os.replace`
  for update; no peer imports rule; update is frontmatter-only
