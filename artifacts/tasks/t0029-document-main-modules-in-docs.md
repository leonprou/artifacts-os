---
kind: task
id: t0029
name: document-main-modules-in-docs
type: documentation
status: rejected
assignee: technical-writer
owner: user
created: 2026-04-28
subtasks:
  - "[[t0030-establish-docs-foundation-readme-index]]"
  - "[[t0031-write-docs-settings-md-cross]]"
  - "[[t0032-audit-and-complete-core-readme]]"
  - "[[t0033-audit-and-complete-views-readme]]"
  - "[[t0034-audit-and-complete-cli-readme]]"
---

# Document Main Modules In Docs Folder (Epic)

## Context

`docs/` currently holds one stale design memo. This epic establishes
`docs/` as the canonical user-facing reference at the **package
level** — cross-cutting overviews and topic guides that link **out**
to per-module `README.md` files for deep API detail. `docs/` does not
duplicate module READMEs.

## Doc Layering

| Layer | Where | Owns |
|---|---|---|
| Package overview, DAG, status, cross-cutting topics | `docs/` | architecture, settings, future cross-cutting facilities |
| Per-module deep API reference | `src/artifacts_os/<module>/README.md` | every public symbol the module exports + worked examples |
| Decision rationale | spec artifacts | "why" the design is what it is |

`docs/` pages link **down** to module READMEs and **across** to specs
by ID.

## Module Status

| Module | Status | README |
|---|---|---|
| `core/` | shipped | yes |
| `views/` | shipped | yes |
| `cli/` | shipped | yes |
| `log/` | empty | — |
| `tui/` | partial | — |
| `ai/` | empty | — |

## Requirements

1. Establish `docs/` as the package-level user-facing reference.
2. Every `docs/` page follows the `technical-writer` document
   conventions (purpose, public API or topic summary, worked example,
   key concepts as needed, cross-references).
3. Per-module README audits ensure each is the canonical,
   comprehensive reference for its module's public API.
4. `docs/` does not duplicate module README content — only summarizes
   and links.
5. Specs linked by ID; doc-to-doc links use relative paths; doc-to-module-README
   links use repo-relative paths
   (e.g. `../src/artifacts_os/core/README.md`).
6. `docs/README.md` is a flat index covering both `docs/` pages and
   per-module READMEs.
7. Decide the fate of `docs/2026-04-20-artifacts-os-design.md` (fold
   into `architecture.md` or move to `docs/archive/`).

## Verification

- [ ] `docs/README.md` exists, indexes both `docs/` pages and per-module READMEs
- [ ] `docs/architecture.md` covers package layout, dependency DAG, module status
- [ ] `docs/settings.md` covers the cross-cutting settings flow with links to `core/README.md` and `views/README.md`
- [ ] `core/README.md`, `views/README.md`, `cli/README.md` are comprehensive per technical-writer conventions
- [ ] No `docs/` page duplicates module README content
- [ ] All five sub-tasks reach `done`

## Subtasks

- Foundation — `docs/README.md` + `docs/architecture.md`
- `docs/settings.md` — cross-cutting page (depends on Foundation)
- Audit `core/README.md`
- Audit `views/README.md`
- Audit `cli/README.md`

## Out of Scope

- Standalone `docs/log.md`, `docs/tui.md`, `docs/ai.md` topic pages —
  defer until those modules ship.
- `log/`, `tui/`, `ai/` README files — empty/stub modules; no README
  to audit yet.
- CLAUDE.md cleanup — covered by `t0028-decouple-claude-md-from-vault`
  (peer prerequisite).
- Source code changes.
