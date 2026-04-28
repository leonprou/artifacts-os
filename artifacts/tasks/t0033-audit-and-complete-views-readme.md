---
kind: task
id: t0033
name: audit-and-complete-views-readme
type: documentation
status: rejected
assignee: technical-writer
owner: user
parent: "[[t0029-document-main-modules-in-docs]]"
created: 2026-04-28
---

# Audit And Complete Views Readme

## Context

Fourth sub-task of `t0029-document-main-modules-in-docs`. Audits and
completes `src/artifacts_os/views/README.md` so it is the canonical,
comprehensive reference for the `views` module's public API.

`views/` ships `FieldSpec`, `parse_field_specs`, `format_field`,
`render_table`, `default_columns`, plus `ViewConfig`, `ViewsConfig`,
and `ViewsSettings` (after `t0026`).

## Requirements

1. Read `src/artifacts_os/views/*.py` — every module file (`_views.py`,
   `models.py`, `__init__.py`) — and confirm the README documents every
   public symbol exported via `views/__init__.py`.
2. Apply `technical-writer` document conventions:
   - **Purpose** (one paragraph) — what `views` is and who imports it.
   - **Public API** code block listing imports.
   - **Worked example** — render a table from a list of artifacts.
   - **Key concepts**: `FieldSpec` syntax (`field[:format] [as Label]`),
     `KindDef.meta` keys (`columns`, `status_colors`),
     `ViewsSettings.from_base` chained-call.
   - **Cross-references** — link to spec `s0007-artifacts-os-views-module`
     and to `docs/settings.md` for the cross-cutting settings flow.
3. Identify any public symbol missing documentation; add it.
4. Identify any documentation that contradicts current code; fix it.
5. Do not introduce content that belongs in `docs/` — module-scoped
   only.

## Verification

- [ ] Every public symbol exported from `views/__init__.py` is documented in `views/README.md`
- [ ] README follows technical-writer conventions
- [ ] `FieldSpec` syntax and `KindDef.meta` keys covered
- [ ] `ViewsSettings.from_base` worked example present
- [ ] Cross-references use spec IDs and relative paths
- [ ] No contradictions with current `views/*.py` source
