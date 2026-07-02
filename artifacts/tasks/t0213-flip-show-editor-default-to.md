---
assignee: developer
created: 2026-06-14
id: t0213
kind: task
name: flip-show-editor-default-to
owner: user
status: done
type: implementation
---

# Flip the built-in default for `artifacts show` to open in an editor

## Why

When a human runs `artifacts show <ref>`, the expected behaviour is
for the file to open in their editor. Today the runtime default is
`false`, so editor mode only kicks in when `cli.defaults.show.editor:
true` is set in `artifacts.yaml`. Flip the default in code so every
vault — new and existing — gets editor-by-default with no config.

Supersedes t0201 (template-only approach) and t0211/t0212 (over-scoped
spec path).

## What

In the CLI module, change the built-in default for the `show.editor`
resolution from `false` to `true`. Existing precedence stays as-is:

| Source                                       | Wins over default? |
|---|---|
| `-j` on the invocation                      | yes (forces JSON)  |
| `-e` on the invocation                      | yes (forces editor) |
| explicit opt-out flag, if one exists today   | yes                 |
| `cli.defaults.show.editor` in artifacts.yaml | yes (true or false) |
| t0192 non-TTY / agent guard                  | yes (downgrades to text) |
| built-in runtime default                     | now `true`         |

If no explicit per-invocation opt-out flag currently exists, **do not
add one in this task** — it's a separate concern. The config-level
opt-out (`cli.defaults.show.editor: false`) is the documented escape
hatch.

## Out of scope

- Adding/renaming any `show` flags.
- Changing other `cli.defaults.*` defaults.
- Init template changes (no `cli:` block needed — that was t0201).
- TUI behaviour.

## Verification

- [ ] In a fresh vault with no `cli:` section in `artifacts.yaml`, running `artifacts show <ref>` from an interactive TTY opens the file in `$EDITOR`.
- [ ] In the same vault, `artifacts show <ref> -j` still prints JSON.
- [ ] In the same vault, piping `artifacts show <ref>` to a non-TTY (e.g. `| cat`) still prints text (t0192 guard intact).
- [ ] In a vault that sets `cli.defaults.show.editor: false` explicitly, `artifacts show <ref>` from a TTY prints text (config override still honoured).
- [ ] `docs/settings.md` and `src/artifacts_os/cli/README.md` updated to reflect the new built-in default and that the config key is now an opt-out rather than an opt-in.
- [ ] Tests added/updated for the new default and each precedence case above.
- [ ] `pytest -q` passes.
- [ ] Reviewed and approved by user.