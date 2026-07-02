---
assignee: developer
created: 2026-06-04
id: t0201
kind: task
name: ship-show-editor-default-in
owner: user
started: 2026-06-05
status: cancelled
type: implementation
---

# Ship `cli.defaults.show.editor: true` in the init settings templates

## Why

The canonical artifacts-os vault sets `cli.defaults.show.editor: true`
under `artifacts.yaml`'s `cli:` section so that `artifacts show <ref>`
opens the file in `$EDITOR` for interactive humans. New vaults created
by `artifacts init` (either tier) inherit no `cli:` section at all, so
they get the bare-default `show` behaviour and every user has to
hand-edit `artifacts.yaml` to match.

t0192 already guards the default against agent/non-interactive
contexts, so flipping it on by default is now safe — CI and agent
invocations won't hang on `$EDITOR`. This task ships the default in
the templates so new vaults match the canonical experience.

## Source of truth

- **`artifacts.yaml`** (this vault, the canonical example) — lines
  146–151 declare:
  ```yaml
  cli:
    defaults:
      show:
        editor: true
  ```
- **t0192 — guard `show.editor` default in agent/non-interactive
  contexts** — the prerequisite that made `editor: true` safe as a
  default. `artifacts show -e` is silently downgraded to text output
  when stdout is not a TTY.
- **`src/artifacts_os/cli/README.md` § "Project Configuration"** —
  documents `cli.defaults.show.editor` and the explicit-flag override
  precedence.

## Files to touch

| Path | Edit |
|---|---|
| `src/artifacts_os/templates/settings/minimal.yaml` | Append a `cli:` section with `defaults.show.editor: true`. |
| `src/artifacts_os/templates/settings/standard.yaml` | Same. |

## Constraints

- **`-j` precedence preserved.** Per the README, passing `-j` to
  `show` must still print JSON regardless of the `editor` default.
  This is already covered by the runtime; the template change must
  not introduce any new contract.
- **Comment the line.** Mirror the inline comment from the canonical
  `artifacts.yaml`: `# behave as if -e were always passed to show`
  so users skim-reading the file understand what the line does.
- **No `create.kind: note` default.** The canonical vault also sets
  `cli.defaults.create.kind: note`, but that is a project-specific
  choice for the artifacts-os repo itself; do **not** propagate it
  to the templates. New users should get the bare `task` default.

## Out of scope

- Adding any other `cli.defaults` or `cli.aliases` entries.
- Renaming or restructuring existing template sections.
- Updating `docs/settings.md` examples — the documented snippet
  already shows this exact pattern, so no doc change is needed.

## Requirements

1. **`minimal.yaml` ships a `cli:` section.** After init with
   `--template minimal`, `artifacts.yaml` contains:
   ```yaml
   cli:
     defaults:
       show:
         editor: true   # behave as if -e were always passed to show
   ```
2. **`standard.yaml` ships the same `cli:` section.** Identical
   content; same trailing comment.
3. **No other template values changed.** `project:`, `views:`, and
   `default_views:` sections are untouched.
4. **Init still parses both templates.** Running
   `artifacts init --template minimal --dry-run` and
   `artifacts init --template standard --dry-run` exit 0 and print
   the new section in the rendered output.
5. **No CLI / core / docs change.**

## Verification

- [ ] `src/artifacts_os/templates/settings/minimal.yaml` ends with a `cli:` block containing `defaults.show.editor: true` and the trailing inline comment.
- [ ] `src/artifacts_os/templates/settings/standard.yaml` ends with the same `cli:` block.
- [ ] No other lines in either template changed (verified by `git diff --stat`).
- [ ] `artifacts init --template minimal --dry-run` and `artifacts init --template standard --dry-run` both exit 0 and show the new `cli:` section in their planned output.
- [ ] A fresh `artifacts init -y` in a scratch directory produces an `artifacts.yaml` whose `cli.defaults.show.editor` is `true`.
- [ ] `pytest -q` passes (template-snapshot tests, if any, regenerated as needed).
- [ ] Reviewed and approved by user.