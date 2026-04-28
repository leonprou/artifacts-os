# Documentation Sprint Design

**Date:** 2026-04-28
**Status:** approved
**Author:** Leon Prouger

---

## Overview

Single documentation sprint that establishes `docs/` as the canonical
package-level reference, cleans up stale content in `CLAUDE.md` and
`README.md`, and audits the `cli` module README. All changes land in
one PR — documentation-only, no source code changes.

---

## Scope

Seven file operations.

### Files modified

| File | What changes |
|---|---|
| `CLAUDE.md` | Remove hardcoded `artifacts/specs/...` paths; update Project Structure block (mark `views`/`cli` as shipped, not stubs); trim Settings section to 2 sentences + link to `docs/settings.md` |
| `README.md` | Fix Project Structure block (views/cli shipped); update Architecture section links to use spec IDs not vault paths |
| `src/artifacts_os/cli/README.md` | Audit against actual shipped CLI — add missing commands/flags, remove stale ones, apply technical-writer conventions |

### Files created

| File | What it contains |
|---|---|
| `docs/README.md` | Flat index: title + one-line summary + link for every page in `docs/` and every per-module README |
| `docs/architecture.md` | Package overview, dependency DAG, module status table, design principles |
| `docs/settings.md` | Cross-cutting settings page: purpose, public API, worked example, extension pattern, schema versioning |

### Files resolved

| File | Disposition |
|---|---|
| `docs/2026-04-20-artifacts-os-design.md` | Move to `docs/archive/` — content already captured; preserved as historical record |

---

## Linking Strategy

`docs/` pages link *down* to module READMEs and *across* to specs by
ID. They do not duplicate module README content — they summarize and
link.

- **Doc-to-doc:** relative paths within `docs/` (e.g. `settings.md`)
- **Doc-to-module README:** repo-relative paths
  (`../src/artifacts_os/<module>/README.md`)
- **Doc-to-spec:** spec ID only (e.g. `s0010-core-settings-module-spec`) — no vault paths

Rationale: module READMEs are the authoritative per-API reference.
Duplicating them in `docs/` creates a maintenance burden with no gain
for contributors navigating the repo.

---

## Document Conventions

Every new `docs/` page follows technical-writer conventions:

1. One-paragraph purpose
2. Public API or topic summary (code block)
3. Worked example
4. Key concepts / patterns (only as needed)
5. Cross-references

`docs/README.md` is a flat index only — no prose, sorted by topic.

---

## Out of Scope

- `log/`, `tui/`, `ai/` module READMEs — stubs; no shipped API to document
- Source code changes
- External-facing content (devrel domain)
- Agent prompts / skills (author domain)
