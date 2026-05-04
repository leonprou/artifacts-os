---
kind: task
id: t0088
name: fix-shell-expansion-footgun-in
type: feature
status: backlog
assignee: ""
owner: user
created: 2026-05-03
---

# Fix shell-expansion footgun in `artifacts create --body`

## Context

While comparing two research artifacts created today (r0004 vs r0005),
the corrupted state of r0004 was traced to **shell command substitution
on the `--body` argument**. The body string contained ordinary Markdown
code spans (backtick-quoted), and the user's shell expanded them
*before* the CLI ever saw the argument.

### Reproduction (from the actual r0004 trace)

The agent ran:

```
artifacts create "computer-use-cli-vs-mcp-for-agents" \
  --kind research --fields status=draft \
  --body "## Question … `rm -rf`, `git reset --hard`, `db drop` … `.env` files, SSH keys … `tools/list` endpoint …"
```

zsh emitted these errors during the call:

```
cat: logs: No such file or directory
(eval):1: command not found: db
(eval):1: command not found: .env
```

Resulting corruption in `artifacts/research/r0004-computer-use-cli-vs-mcp.md`:

| Intended body fragment | Stored body fragment |
|---|---|
| `` `rm -rf`, `git reset --hard`, `db drop` are one misfire away. `` | `, HEAD is now at 8332c17 docs(t0078): update adding-a-kind guide for folder form and ARTIFACT.md contract,  are one misfire away.` |
| `` agent can read `.env` files, SSH keys, … `` | `agent can read , SSH keys, …` |
| `` Unix pipes: `ls \| grep X \| wc -l`. `` | `Unix pipes: .` |
| `` **Discoverability** \| `tools/list` endpoint … `` | `**Discoverability** \| endpoint lets agents …` |

Two consequences:

1. **Body content is silently mutated.** Any backtick / `$(...)` / unquoted
   metacharacter inside the body becomes a shell command. The artifact
   on disk no longer matches what the agent (or human) intended to
   write.
2. **Real side-effects on the working tree.** In r0004's case
   `` `git reset --hard` `` actually executed and printed
   `HEAD is now at 8332c17 …` into the body. That is the only reason the
   commit hash appears verbatim in a research note. A different code
   span (`` `rm -rf .` ``, `` `git push --force` ``) could destroy
   work.

The CLI already provides safe alternatives — `--body-file PATH` and
`--body -` (stdin) — but the unsafe `--body "..."` form is still the
first one shown in `--help` examples and is the natural shape an agent
reaches for when authoring multi-line content.

## Requirements

- **R1.** Decide whether `--body` should keep accepting raw strings at
  all. Options: (a) keep but warn, (b) restrict to single-line content
  (reject input containing `\n`), (c) deprecate and remove. Document
  the chosen policy in `docs/`.
- **R2.** Update `--help` output for `artifacts create` (and
  `openstation create` if it forwards): the **first** example shown
  must be `--body-file` or stdin. The quoted `--body "..."` example
  should either be removed or carry an explicit hazard note.
- **R3.** Add a section to `docs/` (likely `docs/cli.md` or wherever
  the create command is documented) describing the shell-expansion
  hazard with a minimal repro and the safe alternatives.
- **R4.** Update authoring guidance for skills / commands that drive
  `artifacts create` so the recommended path is `--body-file` (write
  to tempfile then pass) or `--body -` (pipe via stdin), never quoted
  multi-line content. Specifically check the create-related skills /
  commands shipped under `.openstation/` and `artifacts/agents/`.
- **R5.** Optional but recommended: emit a runtime warning to stderr
  when `--body` content contains newlines, pointing the caller at
  `--body-file` / stdin.
- **R6.** Add a regression test demonstrating that body content with
  backticks, `$(...)`, and other shell metacharacters round-trips
  unchanged when supplied via `--body-file` and via `--body -`.

## Verification

- [ ] `artifacts create --help` no longer leads with a quoted
      multi-line `--body "..."` example.
- [ ] `docs/` contains a documented hazard note + safe-pattern example.
- [ ] At least one test in `tests/cli/` writes a body containing
      backticks and `$(...)` via `--body-file` and asserts the file on
      disk matches byte-for-byte.
- [ ] Any skill or command in `.openstation/` or `artifacts/agents/`
      that previously instructed agents to call `artifacts create
      --body "..."` is updated to use `--body-file` or stdin.
- [ ] Decision on R1 (keep / restrict / remove) is recorded in the
      task progress log with rationale before implementation lands.

## Notes

- The underlying expansion happens in the user's shell, not in the
  CLI — the CLI cannot fully prevent it for the `--body` form. The
  goal is to make the safe path the default and the unsafe path
  visibly hazardous.
- This task may warrant a tiny spec first (R1 decision needs
  agreement); if so, split into a spec task + implementation task
  rather than expanding scope here.
