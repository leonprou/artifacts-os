---
kind: task
id: t0030
name: establish-docs-foundation-readme-index
type: documentation
status: rejected
assignee: technical-writer
owner: user
parent: "[[t0029-document-main-modules-in-docs]]"
created: 2026-04-28
---

# Establish Docs Foundation - Readme Index And Architecture Page

## Context

First sub-task of `t0029-document-main-modules-in-docs`. Establishes
the `docs/` directory convention with two foundational pages: a flat
index (`docs/README.md`) and a package-level overview
(`docs/architecture.md`). Subsequent sub-tasks build on this.

## Requirements

1. **Create `docs/README.md`** — flat index. For each current page in
   `docs/` and each per-module README, list:
   - title
   - one-line summary
   - link (relative path within `docs/`; repo-relative path
     `../src/artifacts_os/<module>/README.md` for module READMEs)
   - sorted by topic, not chronology
2. **Create `docs/architecture.md`** covering:
   - package overview (one paragraph)
   - dependency DAG (the `core → views → cli, tui` and
     `core → log → ai` graph from `CLAUDE.md`)
   - module status table (shipped/partial/empty per module, with
     a link to the module README where applicable)
   - design principles: vault discovery via `find_vault_root`,
     kinds-driven schema, atomic writes, base `Settings` extension
     pattern
   - cross-references to specs by ID (e.g. `s0010-core-settings-module-spec`)
3. **Resolve `docs/2026-04-20-artifacts-os-design.md`:**
   - either fold its still-relevant content into `architecture.md`
     and delete the dated memo, or
   - move it to `docs/archive/` to preserve as a historical record
   - decision and rationale recorded in this task's `## Findings`
4. Follow `technical-writer` document conventions on both pages.
5. Do not duplicate content from module READMEs in `architecture.md`
   — link instead.

## Verification

- [ ] `docs/README.md` exists and indexes every current page in `docs/` and every per-module README (`core`, `views`, `cli`)
- [ ] `docs/architecture.md` covers package overview, DAG, module status table, design principles
- [ ] `docs/2026-04-20-artifacts-os-design.md` is either folded into `architecture.md` (and removed) or moved to `docs/archive/`
- [ ] All cross-references to specs use spec IDs, not vault paths
- [ ] All cross-references to module READMEs use `../src/artifacts_os/<module>/README.md`
