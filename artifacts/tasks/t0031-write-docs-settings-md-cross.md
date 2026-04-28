---
kind: task
id: t0031
name: write-docs-settings-md-cross
type: documentation
status: rejected
assignee: technical-writer
owner: user
parent: "[[t0029-document-main-modules-in-docs]]"
depends_on:
  - "[[t0030-establish-docs-foundation-readme-index]]"
created: 2026-04-28
---

# Write Docs/Settings.Md Cross-Cutting Page

## Context

Second sub-task of `t0029-document-main-modules-in-docs`. Adds the
cross-cutting `docs/settings.md` page that ties together the settings
facility across `core`, `views`, and consumer modules.

Depends on `t0030-establish-docs-foundation-readme-index` (must land
first so the index can include this page).

## Requirements

1. **Create `docs/settings.md`** following `technical-writer`
   document conventions:
   - **Purpose** (one paragraph) — what `load_settings` does and the
     base-Settings + extension-subclass pattern.
   - **Public API** code block — `core.load_settings`,
     `Settings`, `ProjectConfig`, `UnsupportedSchemaVersion`. Note
     that `ViewConfig` / `ViewsConfig` / `ViewsSettings` live in
     `views`, not `core`.
   - **Worked example** — chained call:

     ```python
     base = load_settings(path)
     settings = ViewsSettings.from_base(base)
     ```

   - **Extension pattern** — how a module (library or consumer)
     defines its own `Settings` subclass with a `from_base` parser.
     Note the `@dataclass(kw_only=True)` requirement.
   - **Schema versioning** — `layout_version: 1`,
     `UnsupportedSchemaVersion` rules.
   - **Cross-references** — links to:
     - `../src/artifacts_os/core/README.md` for the core module's
       full settings API
     - `../src/artifacts_os/views/README.md` for `ViewsSettings`
       deep detail
     - spec `s0010-core-settings-module-spec` for design rationale
2. Do **not** duplicate the module READMEs — summarize and link.
3. Update `docs/README.md` index to include this page.

## Verification

- [ ] `docs/settings.md` exists and follows technical-writer conventions
- [ ] Page covers public API, worked example, extension pattern, schema versioning
- [ ] Cross-references to module READMEs and spec ID present
- [ ] `docs/README.md` index updated to include this page
- [ ] No duplication of `core/README.md` or `views/README.md` content
