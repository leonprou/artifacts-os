---
assignee: ''
created: 2026-05-05
id: t0095
kind: task
name: ship-artifacts-os-skill-via
owner: user
parent: '[[t0041-ai-claude-commands-support]]'
status: backlog
type: feature
---

## User story

> **As an artifacts-os user, after running \`pip install artifacts-os\` and \`artifacts init\` in a fresh repo, I want the \`artifacts-os\` Claude skill to be present at \`<vault>/.claude/skills/artifacts-os/SKILL.md\` — so my Claude Code agent uses the \`artifacts\` CLI correctly without me manually copying any file.**

## Why this exists

\`t0044\` shipped the install machinery and three slash commands
(\`/artifacts.list\`, \`/artifacts.show\`, \`/artifacts.create\`), but the
SKILL.md that teaches an agent the CLI contract is still authored
**out-of-tree** at \`~/.claude/skills/artifacts-os/SKILL.md\` — it does
not ride the wheel and \`init\` does nothing about skills today.

The user has chosen to omit any pip-postinstall hook. Distribution
flows entirely through \`artifacts init\` (with \`--no-ai\` opt-out),
matching how commands already work.

## Scope (intent, not contract — spec to be authored)

- Ship one skill: the existing \`artifacts-os\` skill content, no edits to behaviour.
- Install target: \`<vault>/.claude/skills/artifacts-os/SKILL.md\` (vault-local; \`.opencode/\` parity follows the same pattern as commands).
- Default mode: symlink (matches commands); \`--copy\` opt-in.
- Namespace ownership: anything under \`artifacts-os/\` directory in the skills tree is ours; everything else is untouched.
- Repo dogfood: this repo's \`.claude/skills/\` should expose the skill the same way \`.claude/commands/\` exposes \`artifacts.*\`.

## Out of scope

- The other six unfinished commands from \`t0041\` (\`artifacts.kinds\`,
  \`artifacts.kinds.create\`, \`artifacts.kinds.edit\`,
  \`artifacts.validate\`, \`artifacts.verify\`, \`artifacts.init\`).
- User-global install (\`~/.claude/skills/\`).
- pip postinstall hooks (explicitly rejected — \`init\` is the only entry point).
- Changes to existing command install behaviour.

## Decomposition

1. **Spec the contract** — \`architect\` — see the architect sub-task spawned with this parent. Locks: symlink-file vs symlink-dir, namespace predicate, \`list_installed\` reporting, \`uninstall\` semantics, package layout for \`ai/claude/skills/\`.
2. **Author SKILL.md in the package** — \`author\` — port the existing \`~/.claude/skills/artifacts-os/SKILL.md\` content to \`src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md\`. *(spawned after spec approves.)*
3. **Extend \`install.py\`** — \`developer\` — generalise \`_source_files\`, \`_plan_action\`, \`uninstall\`, \`list_installed\` to handle the skills sub-tree per spec; add tests under \`tests/ai/\`. *(spawned after spec approves.)*
4. **Repo dogfood update** — \`developer\` — once 2 + 3 land, point \`.claude/skills/\` at the package source so the repo eats its own dog food. *(spawned with task 3.)*

## Verification (placeholder — finalise after spec approves)

- [ ] Spec sub-task reaches \`approved\`.
- [ ] All decomposition sub-tasks reach \`done\`.
- [ ] \`pip install -e .\` followed by \`artifacts init\` in a fresh dir produces a working \`<vault>/.claude/skills/artifacts-os/SKILL.md\`.
- [ ] \`artifacts ai install --dry-run\` previews the skill action; \`artifacts ai uninstall\` removes only the namespaced skill.
- [ ] \`--no-ai\` still skips both commands and the skill.
- [ ] Repo's own \`.claude/skills/\` shows \`artifacts-os/\` after the dogfood update.
- [ ] Test suite green; no new cross-module imports.