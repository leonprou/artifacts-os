---
kind: task
id: t0133
name: feat-relocate-artifacts-yaml-to
type: feature
status: rejected
assignee: 
owner: user
created: 2026-05-09
subtasks:
  - "[[t0134-spec-relocate-vault-marker-to]]"
---

# Feat: Relocate Artifacts.Yaml To Project Root

## User story

As a vault user, I want `artifacts.yaml` to live at the **project
root** (e.g. alongside `pyproject.toml` / `package.json`), instead
of being buried inside `artifacts/`.

A top-level config file makes it immediately obvious that the
repo *is* an artifacts vault — the same way `pyproject.toml`
declares a Python project. It also normalizes the marker with
the rest of the project's top-level config, simplifies tooling
that scans repo roots, and reduces the conceptual nesting between
"the project" and "the vault".

## Intent (what / why) — not contract

These are user-level expectations. Exact mechanics are deferred
to the architect spec sub-task.

- The vault-marker file is `artifacts.yaml` at the project root,
  not `artifacts/artifacts.yaml`.
- `find_vault_root` discovery still works from any subdirectory
  inside the project — no regression in CWD-relative resolution.
- `artifacts/` continues to be where artifact files live (tasks,
  specs, agents, etc.). *Intent, not contract — the architect
  decides whether that storage layout stays or changes.*
- Existing vaults can migrate without losing data. *Intent — the
  architect designs the migration path.*
- Documentation (`CLAUDE.md`, `docs/`, `README.md`) and test
  fixtures stay coherent with the new layout.

## Out of scope (until spec lands)

- Concrete file moves, rename rules, backward-compat windows,
  default-kind path resolution changes, settings-loader API
  surface — all decided by the architect.

## Verification

*Placeholder — finalized after the architect spec is approved
and this parent task is promoted to `ready`.*

## Subtasks

- [[tNNNN-spec-relocate-vault-marker-to-root]] — architect
  produces the design contract.
