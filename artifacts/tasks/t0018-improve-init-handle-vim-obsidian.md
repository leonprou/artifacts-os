---
kind: task
id: t0018
name: improve-init-handle-vim-obsidian
type: feature
status: ready
assignee: developer
owner: user
created: 2026-04-26
---

# Improve Init - Handle Vim Obsidian Integration

## Context

`artifacts init` currently writes the vault marker (`artifacts.yaml`),
sets up `artifacts/` storage, and creates the `openstation -> artifacts`
compat symlink. It does not configure editor integrations.

Recent friction (t0016) showed that opening the project in Obsidian
without a pre-seeded `.obsidian/` config breaks wikilinks unless the
user manually picks the right vault root. Bare-basename links
(`[[name]]`) work; path-prefixed (`[[artifacts/specs/...]]`) do not
when both `artifacts/` and the `openstation` symlink expose the
same files. A sibling nvim plugin (path TBD) also needs a discovery
contract.

This task extends `artifacts init` and updates **artifacts-os's own**
docs/specs only. The `.openstation/` directory is no longer a vault
marker (t0015) and is out of scope.

## Requirements

### 1. Obsidian config in `init`

`artifacts init` writes a minimal `.obsidian/app.json` at the project
root with wikilink-friendly settings (link resolution = shortest
path / basename). Idempotent — must not clobber an existing
`.obsidian/` directory if the user already configured Obsidian.

Code: `src/artifacts_os/cli/commands/init.py`.

### 2. Compat symlink decision

Decide whether `init` keeps creating the `openstation -> artifacts`
compat symlink:

- Keep it and document a vault-root recommendation, or
- Drop it (and provide a migration note for existing vaults).

Implement the choice in `init.py` with a code comment recording the
rationale.

### 3. Wikilink convention update (artifacts-os files only)

Switch documented examples from `[[artifacts/specs/<name>]]` to bare
`[[<name>]]` in artifacts-os's own files:

- `artifacts/specs/s0002-artifacts-os-architecture.md` (and any
  other artifacts-os spec with wikilink examples)
- `docs/` project docs
- README.md if applicable

Do **not** touch anything under `.openstation/` — that is the
external openstation framework, separately maintained.

### 4. nvim plugin discovery contract

Create `artifacts/specs/sNNNN-editor-integration.md` (architect
or developer can draft inline) covering:

- How an artifacts-os nvim plugin discovers a vault (re-use
  `find_vault_root` walking to `artifacts.yaml`)
- Whether `init` writes any handoff file, or the plugin walks
  the tree itself
- Plugin source code is out of scope for this task

### 5. Tests

- `.obsidian/app.json` is written when absent
- Existing `.obsidian/` not clobbered when present
- Symlink behaviour matches the decision in §2
- Existing pytest suite remains green

## Verification

- [ ] `artifacts init` writes `.obsidian/app.json` with wikilink-friendly settings at project root
- [ ] Existing `.obsidian/` configs are not overwritten (idempotent)
- [ ] Symlink decision implemented in `init.py` with rationale comment
- [ ] artifacts-os specs/docs use bare-basename wikilinks (`[[name]]`)
- [ ] No changes made under `.openstation/` (framework boundary respected)
- [ ] Editor integration spec exists at `artifacts/specs/sNNNN-editor-integration.md`
- [ ] New tests pass; full `pytest` suite stays green
