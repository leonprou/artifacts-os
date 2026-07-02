---
assignee: developer
created: 2026-06-14
id: t0211
kind: task
name: make-show-editor-the-built
owner: user
status: cancelled
subtasks:
- '[[t0212-spec-runtime-show-editor-default]]'
type: implementation
---

# Make `show` open in an editor by default at the runtime level

## Why

When a human runs `artifacts show <ref>`, the expected behaviour is for
the file to open in their editor. Today this only happens if their
`artifacts.yaml` sets `cli.defaults.show.editor: true` — i.e. every
vault has to opt in via config. The default should be flipped at the
CLI runtime level so it works out of the box for **all** vaults, new
and existing, with no `artifacts.yaml` change required.

## User story

> As a user, when I run `artifacts show t0042` in any vault, I get
> the artifact opened in my editor without having to configure
> anything. Scripts and agents that pipe `show` continue to work
> unchanged.

## Intent (not contract — pending architect spec)

- Editor-by-default applies only in interactive TTY contexts. The
  existing non-TTY/agent guard (t0192) must keep working — agents
  and CI still get text output.
- `-j` continues to win unconditionally (machine-readable output).
- A user can still opt out per-invocation (some form of
  `--no-editor` or equivalent) and via `artifacts.yaml`
  (`cli.defaults.show.editor: false`).
- No `cli:` block needs to appear in `artifacts.yaml` templates —
  the default lives in the code.
- Supersedes t0201, which shipped the same default via init
  templates and is now redundant.

## Out of scope

- Changing any other `cli.defaults.*` behaviour.
- TUI / non-CLI surfaces.
- Editor-discovery logic (`$EDITOR` resolution, fallbacks).

## Verification

_Placeholder — finalize once the architect spec lands._

- [ ] Architect spec approved (see sub-task).
- [ ] Precedence rules from the spec are implemented and tested.
- [ ] Reviewed and approved by user.