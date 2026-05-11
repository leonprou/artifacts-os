---
kind: task
id: t0134
name: spec-relocate-vault-marker-to
type: spec
status: rejected
assignee: architect
owner: user
parent: "[[t0133-feat-relocate-artifacts-yaml-to]]"
created: 2026-05-09
---

# Spec: Relocate Vault Marker To Project Root

## Requirements

The architect should produce a spec under `artifacts/specs/`
(stem `sNNNN-relocate-vault-marker-to-root`) that defines the
contract for moving the vault-marker file out of `artifacts/`
and up to the project root, as described in the parent task
[[t0133-feat-relocate-artifacts-yaml-to]].

User-level intent the spec must serve:

1. **New marker location** — the canonical vault marker is
   `artifacts.yaml` at the project root. Define how
   `find_vault_root` walks the parents and what it returns
   (the project root, the vault root, and the relationship
   between the two). Explicitly state which directory is "the
   vault" after the move.

2. **Storage layout decision** — decide whether `artifacts/`
   continues to host artifact files (tasks, specs, agents,
   logs) or whether the vault flattens to the project root.
   Justify the pick with trade-offs (clarity vs. clutter at
   repo root, default-kind path resolution, existing
   `default_kinds` paths, test-fixture impact).

3. **Settings loader contract** — define how `load_settings`
   resolves the marker file path, what keys move (if any),
   and what stays. Cover both `core.Settings` and any
   extension subclasses (`from_base`).

4. **Default-kind path resolution** — spell out how artifact
   directories (tasks, specs, agents, etc.) are resolved
   relative to the new marker. Are paths still
   `artifacts/<kind>/`, are they `<kind>/`, or configurable?
   This must reconcile with the `default_kinds` config.

5. **Discovery & CWD semantics** — confirm `find_vault_root`
   still resolves correctly from any subdirectory inside the
   project, including from inside `artifacts/`, `src/`,
   `tests/`, and worktrees.

6. **Backward compatibility & migration** — define behaviour
   when a project still has the old `artifacts/artifacts.yaml`
   layout. Options to evaluate: hard cutover, dual-discovery
   window, automatic migration on `artifacts init`, manual
   migration step. Pick one and justify.

7. **Test-fixture impact** — `make_vault` and the broader
   `tests/` suite assume the current marker location. The
   spec must describe how the fixture changes and what test
   updates are required (count files, not enumerate).

8. **Documentation impact** — list every doc that references
   the old marker location (`CLAUDE.md`, `docs/`,
   `README.md`, module READMEs, `.openstation/docs/`,
   skill files). The implementation task will use this list;
   the spec must guarantee it is exhaustive.

9. **Trade-off section** — at minimum: dual-marker-window vs
   hard-cutover migration; flat-vault vs `artifacts/`-nested
   storage. Pick one of each with reasoning.

10. **Out of scope, made explicit** — the spec lists what it
    deliberately does *not* cover, so the implementation task
    has a clean boundary.

## Verification

- [ ] Spec file exists at
      `artifacts/specs/sNNNN-relocate-vault-marker-to-root.md`
      with frontmatter (`kind: spec`, `name`, `id`, `task`).
- [ ] Vault-discovery contract is fully specified
      (`find_vault_root` behaviour, return value, project-root
      vs vault-root semantics).
- [ ] Storage-layout decision is documented with trade-offs
      and explicit pick.
- [ ] Settings-loader contract covers `core.Settings` and
      extension subclasses.
- [ ] Default-kind path-resolution rule is unambiguous.
- [ ] Migration plan is chosen with reasoning; backward-compat
      behaviour is explicit.
- [ ] Test-fixture impact is described.
- [ ] Documentation impact list is exhaustive (every file
      referencing the old marker is enumerated).
- [ ] At least two trade-off comparisons with picks are
      present.
- [ ] Out-of-scope section is included.
