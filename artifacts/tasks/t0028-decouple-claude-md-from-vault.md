---
kind: task
id: t0028
name: decouple-claude-md-from-vault
type: documentation
status: ready
assignee: technical-writer
owner: user
created: 2026-04-28
---

# Decouple Claude.Md From Vault Layout And Add Docs/Settings.Md

# Decouple CLAUDE.md From Vault Layout, Add docs/settings.md

## Context

`CLAUDE.md` currently hardcodes vault folder names (`artifacts/`,
`openstation/`) and a spec path (`artifacts/specs/s0010-...`). This
leaks vault layout into agent instructions and breaks if the vault
folder is renamed (as already happened during t0014/t0023). It also
mixes "what the package does" with "where files live in this
specific repo."

The fix: keep `CLAUDE.md` semantic (no path coordinates beyond the
package's own layout under `src/`); move detailed how-to content
into `docs/`, which is path-stable. `docs/` references specs in the
vault when readers want full rationale.

Reference: `docs/2026-04-20-artifacts-os-design.md` shows the
existing top-level docs style.

## Requirements

1. **Create `docs/settings.md`** as the canonical user-facing
   reference for the settings facility. Cover:
   - Purpose: load `artifacts.yaml`, return a typed `Settings`.
   - Public API: `core.load_settings`, `Settings`, `ProjectConfig`,
     `UnsupportedSchemaVersion`.
   - Extension pattern: `Settings` is a base; modules subclass it
     with `from_base`. Show `views.ViewsSettings.from_base(base)`
     as the worked example.
   - Implementation note: `@dataclass(kw_only=True)` is required
     for subclasses adding required fields.
   - Note that the write API is deferred (link to s0010 § Future
     Work).
   - Link to `openstation/specs/s0010-core-settings-module-spec.md`
     for the full design rationale.

2. **Update `CLAUDE.md`:**
   - **`## Artifact Storage`** — remove the literal `artifacts/`
     folder reference. Describe the vault marker abstractly
     (`artifacts.yaml` at the project root walked up by
     `find_vault_root`); point at `docs/` for storage details.
   - **`## Settings`** — trim to ~2 sentences that name the
     pattern (base `Settings` + module subclass via `from_base`)
     and link to `docs/settings.md`. Drop the `artifacts/specs/...`
     path.
   - Sweep for any other hardcoded vault paths and replace with
     `docs/`-relative references or stable abstractions.
   - Keep package-internal paths (`src/artifacts_os/...`,
     `tests/`, `pyproject.toml`) — those are part of the package
     layout, not the vault.

3. **Out of scope:**
   - Renaming `openstation/` ↔ `artifacts/` (separate question;
     don't touch the vault layout in this task).
   - Updating `openstation/docs/*.md` (those are harness docs;
     scope here is only the package's `docs/` and `CLAUDE.md`).
   - Editing the s0010 spec (authoritative).

## Verification

- [ ] `docs/settings.md` exists and covers public API + extension
      pattern + the `kw_only=True` note
- [ ] `docs/settings.md` links to `openstation/specs/s0010-core-settings-module-spec.md`
- [ ] `CLAUDE.md` `## Artifact Storage` section does not name a
      specific vault folder
- [ ] `CLAUDE.md` `## Settings` section is ≤3 sentences and points
      at `docs/settings.md`
- [ ] `grep -n "artifacts/specs\|openstation/specs\|artifacts/tasks" CLAUDE.md`
      returns no matches
