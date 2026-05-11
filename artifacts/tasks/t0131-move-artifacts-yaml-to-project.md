---
kind: task
id: t0131
name: move-artifacts-yaml-to-project
type: feature
status: done
assignee: 
owner: user
created: 2026-05-09
subtasks:
  - "[[t0132-spec-for-vault-marker-at]]"
  - "[[t0137-implement-vault-marker-relocation-per]]"
  - "[[t0138-docs-sweep-for-vault-marker]]"
completed: 2026-05-11
---

# Move Artifacts.Yaml To Project Root

# Move artifacts.yaml to project root

## User story

> **As an operator working in an artifacts-os project, I want the
> vault marker (`artifacts.yaml`) to live at the project root —
> next to `pyproject.toml`, `CLAUDE.md`, and other project metadata —
> rather than buried inside `artifacts/`. That way the file that
> *identifies* the project is visible at a glance, while
> `artifacts/` holds only artifact data.**

Today the marker is `artifacts/artifacts.yaml`. The directory and
its config file share the same name, which is awkward. Pulling the
marker up one level matches how every other project-level config
behaves (`pyproject.toml`, `package.json`, `Cargo.toml` are all at
the repo root) and cleans up the visual hierarchy.

## Intent (not contract)

The architect spec sub-task owns the precise contract. Captured
here as user-level intent only:

1. **Marker lives at project root** as `./artifacts.yaml`. The
   `artifacts/` directory continues to hold artifact data
   (`tasks/`, `specs/`, `agents/`, etc.) but no longer contains
   the marker.
2. **`find_vault_root` discovers the new location** by walking up
   from CWD looking for `./artifacts.yaml` (sibling of
   `artifacts/`), not the current `artifacts/artifacts.yaml`.
3. **`artifacts init` writes the marker to the new location** and
   creates the `artifacts/` data directory alongside it.
4. **One-time migration path** — existing vaults with the old
   layout should be migrate-able with a single command or doc'd
   manual step. Architect picks the approach (migration helper
   vs. doc-only).
5. **Backward compatibility decision is explicit** — the spec
   states whether the old location is still recognised (with a
   warning) or removed cleanly. Pre-1.0, hard cutover is fine if
   justified.
6. **Documentation tracks the change** — `CLAUDE.md`,
   `docs/settings.md`, `README.md`, and per-module READMEs that
   reference the old path are updated in the same commit as the
   code change.
7. **This vault migrates to the new layout** — once the change
   ships, this repo's own `artifacts/artifacts.yaml` moves to
   `./artifacts.yaml` as part of the implementation task.

## Verification

_(Placeholder — finalise this list after the spec is approved.)_

- [ ] Architect spec sub-task is approved and merged.
- [ ] `find_vault_root` discovers `./artifacts.yaml` at project
      root and no longer probes `artifacts/artifacts.yaml`
      (per spec).
- [ ] `artifacts init` produces the new layout in a fresh
      directory.
- [ ] Migration path (helper or documented steps) works for an
      existing vault.
- [ ] Documentation (`CLAUDE.md`, `docs/`, READMEs) reflects the
      new layout — no stale references to
      `artifacts/artifacts.yaml`.
- [ ] This repo's own vault has been migrated and `pytest`
      passes.

## Subtasks

### Spec (HIGH — gates the rest)

1. **[[t0132-spec-for-vault-marker-at]]** — architect spec
   defining the contract. Produced
   [[artifacts/specs/s0026-vault-marker-at-root]].

### Implementation (in order)

2. **[[t0137-implement-vault-marker-relocation-per]]** —
   developer task executing PR1 of s0026 §13.1: code +
   fixtures + this repo's `git mv`. Single atomic PR.
3. **[[t0138-docs-sweep-for-vault-marker]]** —
   technical-writer task executing PR2 of s0026 §13.2:
   pure-prose sweep of every `artifacts/artifacts.yaml`
   reference in docs and READMEs. Depends on t0137.
