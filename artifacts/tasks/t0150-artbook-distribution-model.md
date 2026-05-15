---
assignee: ''
created: 2026-05-15
id: t0150
kind: task
name: artbook-distribution-model
owner: user
status: done
type: feature
subtasks:
  - "[[t0151-spec-the-artbook-model]]"
  - "[[t0152-itemmeta-base-class-render-table]]"
  - "[[t0153-artbook-module-manifest-fetch-placement]]"
  - "[[t0154-artifacts-book-cli-command-list]]"
  - "[[t0155-publish-artifacts-os-as-its]]"
completed: 2026-05-15
---

# Artbook Distribution Model

## User story

> **As a** consumer of artifacts-os **I want** to pull artifacts-os's agent defaults from a remote distro repo with one command **so that** I don't have to copy-paste agent files into my project.

## Why

- Parallel copies of agents across `.claude/`, `.openstation/`, `artifacts/`, and `src/.../templates/` drift silently — inventory in [[n0011-distributable-harness-layers-inventory]] and [[n0012-distributable-harness-layers-to-merge]].
- Earlier framing in [[t0144-distributable-opinionated-harness-for-artifacts]] proposed a heavier "catalogue + manifest" model. MVP proves a thinner user-facing primitive (`distro` / `book` / `artbook` module) on one book type before expanding.

## Supersedes

[[t0144-distributable-opinionated-harness-for-artifacts]] in scope. t0144 covered the broader system; this task is narrower and focused on proving the model end-to-end with one book. Its sub-tasks (t0145 spec, t0146 research) stay as historical reference.

## Directions (intent, not contract)

1. **Distro** = a git repo with an `artbook.toml` manifest at its root listing books.
2. **Book** = entry in `artbook.toml`. Typed, named, points at a file or folder.
3. **`artbook` module** lives inside artifacts-os; reads the manifest, fetches content, writes files into the consumer's project.
4. **CLI surface (MVP)**:
   - `artifacts book list`
   - `artifacts book show <name>`
   - `artifacts book pull <name>`
5. **MVP ships one book type**: `agents`. Proves the model end-to-end; kinds / skills / others follow once it works.
6. **MVP pull semantics**: fetch from a configured distro URL on every read, no cache; on `pull`, write files to the type's expected path, overwriting whatever's there. No prompts, no merge logic.

## Out of scope (deferred)

- Book types beyond `agents` (kinds, skills, commands, hooks)
- `update` / `diff` / `remove` CLI verbs
- Multi-distro per project
- Override layer for project-specific items
- Dogfood migration of this repo's existing copies
- Private-distro auth, lock files, version pinning, caching, offline support

## Open questions (architect's call — bias to the simplest option)

- `artbook.toml` minimum required fields per book
- Pull fetch strategy — full clone vs. archive download vs. sparse checkout
- How the consumer configures which distro to pull from (a key in `artifacts.yaml`, or a CLI flag, etc.)

## Sub-tasks

- [[t0151-spec-the-artbook-model]] — architect spec for the MVP
  (verified; produced [[s0029-artbook-mvp-distribution-model]]).
- [[t0152-itemmeta-base-class-render-table]] — precursor refactor:
  generalise `views.render_table` via a new `core.models.ItemMeta`
  base class so the new CLI verbs can reuse the table machinery
  (D22). Independent track; can run in parallel with t0153.
- [[t0153-artbook-module-manifest-fetch-placement]] — pure-logic
  `artbook` module (manifest, fetch, placement, pull, settings,
  errors). Independent track; can run in parallel with t0152.
- [[t0154-artifacts-book-cli-command-list]] — `artifacts book list /
  show / pull` CLI verbs wiring t0152 + t0153 into the user-facing
  loop. Blocked on t0152 and t0153.
- [[t0155-publish-artifacts-os-as-its]] — distro-side: add
  `artbook.yaml` at the repo root so artifacts-os doubles as its own
  artbook distro (Layout B). Independent track; gives t0154's
  end-to-end verification a real URL to pull from.

## Verification

- [ ] Architect spec produced and approved
- [ ] `artifacts book list` lists books from a configured distro
- [ ] `artifacts book show agents` shows the agents inside the agents book
- [ ] `artifacts book pull agents` fetches agent files from the distro and writes them to the consumer's project at the correct path
- [ ] A test repo with no existing agent files runs `artifacts book pull agents` and ends up with working agents

## References

- [[n0011-distributable-harness-layers-inventory]]
- [[n0012-distributable-harness-layers-to-merge]]
- [[t0144-distributable-opinionated-harness-for-artifacts]] (superseded scope)
- [[s0028-distributable-harness-sync-model]] (earlier spec draft, reference only)