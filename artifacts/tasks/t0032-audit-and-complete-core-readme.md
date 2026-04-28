---
kind: task
id: t0032
name: audit-and-complete-core-readme
type: documentation
status: rejected
assignee: technical-writer
owner: user
parent: "[[t0029-document-main-modules-in-docs]]"
created: 2026-04-28
---

# Audit And Complete Core Readme

## Context

Third sub-task of `t0029-document-main-modules-in-docs`. Audits and
completes `src/artifacts_os/core/README.md` so it is the canonical,
comprehensive reference for the `core` module's public API.

`core/` is the most fully-shipped module today: storage, discovery,
kinds registry, frontmatter, ID generation, vault detection, validate,
and (after `t0025`) settings.

## Requirements

1. Read `src/artifacts_os/core/*.py` — every module file
   (`store.py`, `discover.py`, `registry.py`, `frontmatter.py`,
   `ids.py`, `vault.py`, `validate.py`, `settings.py`, `models.py`,
   `errors.py`) — and confirm the README documents every public
   symbol exported via `core/__init__.py`.
2. Apply `technical-writer` document conventions to the README:
   - **Purpose** (one paragraph) — what `core` is and who imports it.
   - **Public API** code block listing imports.
   - **Worked example** for the typical caller flow (init vault →
     load settings → list/get artifacts).
   - **Key concepts**: vault root, kinds, atomic writes, frontmatter
     model. Keep narrow — link to specs for "why."
   - **Cross-references** — link to specs by ID and to `docs/` pages
     by relative path.
3. Identify any public symbol missing documentation; add it.
4. Identify any documentation that contradicts current code or
   recently shipped changes; fix it.
5. Do not introduce content that belongs in `docs/` (cross-cutting
   topics) — that is `t0031`'s scope. This audit is module-scoped.

## Verification

- [ ] Every public symbol exported from `core/__init__.py` is documented in `core/README.md`
- [ ] README follows technical-writer conventions (purpose, public API, worked example, key concepts, cross-references)
- [ ] No contradictions with current `core/*.py` source
- [ ] Cross-references use spec IDs and relative paths
- [ ] No duplication of cross-cutting `docs/` page content
