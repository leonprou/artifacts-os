---
kind: task
id: t0034
name: audit-and-complete-cli-readme
type: documentation
status: rejected
assignee: technical-writer
owner: user
parent: "[[t0029-document-main-modules-in-docs]]"
created: 2026-04-28
---

# Audit And Complete Cli Readme

## Context

Fifth sub-task of `t0029-document-main-modules-in-docs`. Audits and
completes `src/artifacts_os/cli/README.md` so it is the canonical,
comprehensive reference for the `openstation` CLI commands shipped
today.

`cli/` is shipped — `commands/` directory contains command
implementations; the `openstation` binary is on `$PATH` during agent
sessions.

## Requirements

1. Read `src/artifacts_os/cli/commands/*.py` (and any other
   command-relevant files) — confirm every shipped command and flag
   is documented in the README.
2. Apply `technical-writer` document conventions:
   - **Purpose** (one paragraph) — what the `openstation` CLI is and
     when to reach for it.
   - **Command reference** — for each command, document:
     - usage line
     - description
     - flags
     - one short example
   - **Worked example** — a typical end-to-end flow
     (`init` → `create` → `list` → `status`).
   - **Cross-references** — link to spec
     `s0003-artifacts-os-cli-module` and to relevant `docs/` pages.
3. Identify any shipped command or flag missing documentation;
   add it.
4. Identify any documented command/flag that no longer exists; remove
   it.
5. Do not introduce content that belongs in `docs/` — module-scoped
   only.

## Verification

- [ ] Every shipped CLI command is documented in `cli/README.md` with usage, flags, and an example
- [ ] README follows technical-writer conventions
- [ ] Worked end-to-end flow example present
- [ ] No documented command or flag that no longer exists
- [ ] Cross-references use spec IDs and relative paths
