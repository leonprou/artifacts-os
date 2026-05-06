---
kind: task
id: t0109
name: provide-artifacts-init-flow-with
type: feature
status: done
assignee: project-manager
owner: user
created: 2026-05-06
subtasks:
  - "[[t0110-implement-artifacts-init-flow-per]]"
started: 2026-05-06
completed: 2026-05-06
---

# Provide Artifacts Init Flow With Tiered Templates

## User Story

As a developer onboarding to artifacts-os, I want a single `artifacts init` command that walks me through choosing a settings tier, the artifact kinds I need, and the agents I want, so I get a working vault scaffold without copy-pasting from another project or reading schema docs.

## Why

- Today there is no real init flow — `find_vault_root` requires a hand-authored `artifacts/artifacts.yaml`, and the existing stub `init` command emits a hard-coded four-kind dump with no tier choice and no agents.
- Operators bootstrap by copying yaml from another project, which drifts from canonical patterns and is invisible to upgrade tooling.
- Bundled templates (settings tiers + kinds + agents) shipped inside the wheel give every install a consistent starting point and let new features ride along automatically with releases.

## Outcome

- `artifacts init` is the single supported way to scaffold a new vault.
- Three independent selection steps (tier / kinds / agents) — each skippable via flag.
- Skip-by-default, `--force` to overwrite, fail-loud non-TTY without `-y`.
- All templates ship with the wheel (no install cache).

## Scope

- `artifacts init` CLI surface (subcommand, flags, prompts).
- Bundled settings templates: basic, standard, advanced.
- Bundled kind templates: task, note, spec, research, agent.
- Bundled agent templates: architect, developer, author, researcher, technical-writer.
- Spec doc landing the technical contract.

## Out of scope

- Template versioning / migration.
- Remote template fetch.
- Interactive editing of templates after install.
- AI command install (no `.claude/` symlink trees).

## Related

- [[t0108-spec-artifacts-init-flow-with]] — spec sub-task (DONE → produced [[s0021-artifacts-init-flow]]).
- Implementation sub-task linked below.

## Verification

- [ ] [[s0021-artifacts-init-flow]] exists with status `approved` (DONE via t0108).
- [ ] Implementation sub-task ships with all §18 tests passing.
- [ ] Bundled templates verified in built wheel via `python -m build && unzip -l dist/*.whl | grep templates/`.
- [ ] README and docs updated to point at `artifacts init` as the canonical bootstrap.
