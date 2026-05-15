---
assignee: project-manager
created: 2026-04-30
id: t0041
kind: task
name: ai-claude-commands-support
owner: user
status: backlog
subtasks:
  - '[[t0043-author-browse-and-inspect-claude]]'
  - "[[t0044-cli-ai-install-module]]"
  - "[[t0045-review-docs-for-t0041-changes]]"
  - "[[t0046-author-artifacts-create-command]]"
type: feature
---

## Goal

Ship a native `/artifacts.*` Claude Code surface for `artifacts-os` — distinct from openstation's lifecycle-driven `/openstation.*` commands — and the supporting install machinery so that `pip install artifacts-os` followed by `artifacts init` produces a working set of slash commands and skills inside `<vault>/.claude/`.

## Context

- Audit `r0001-openstation-integration-audit` already plans for "10 planned `/artifacts.*`" commands as a separate surface from `/openstation.*` (see §4 coverage matrix: "Both stay; different surfaces").
- The artifacts-os boundary is **storage / discovery / validation** — no lifecycle. Lifecycle commands (`ready`, `progress`, `done`, etc.) stay openstation-side (`CLAUDE.md`: "No lifecycle logic in `cli`").
- artifacts-os kinds are user-defined via `artifacts/kinds/*.json`, so per-kind subcommands (`/artifacts.create.note`, `/artifacts.create.spec`, …) would leak openstation assumptions. The surface is **kind-aware via the registry** rather than per-kind.
- The `ai/` module (spec `s2066`) is currently a stub. This work makes it concrete; its scope narrows to "AI tool integration assets" (commands, skills, future hooks).

## Command surface (9 commands across 5 categories)

### 1. Browse & Inspect

| Command | Maps to | Purpose |
|---|---|---|
| `/artifacts.list` | `artifacts list` | List/filter artifacts |
| `/artifacts.show` | `artifacts show` | Inspect a single artifact |
| `/artifacts.kinds` | `artifacts kinds` | List registered kinds in this vault |

### 2. Author artifacts

| Command | Maps to | Purpose |
|---|---|---|
| `/artifacts.create` | `artifacts create --kind <K>` | Single kind-aware creator. Reads the registry; prompts for the kind, slug, frontmatter, body. Works for any user-defined kind. |

### 3. Define kinds *(new category — replaces per-kind sub-commands)*

| Command | Writes to | Purpose |
|---|---|---|
| `/artifacts.kinds.create` | `artifacts/kinds/<name>.json` | Scaffold a new kind: prompts for `kind`, `prefix`, `numbered`, `dir`, `statuses`, required fields, columns. Generates a JSON-Schema kind definition with `x-` extensions. |
| `/artifacts.kinds.edit` | `artifacts/kinds/<name>.json` | Modify an existing kind (add/remove status, add a required field, change columns). |

### 4. Validate & Verify

| Command | Maps to | Purpose |
|---|---|---|
| `/artifacts.validate` | `artifacts validate` | Frontmatter vs. kind schema (`--fix`, `--dry-run`) |
| `/artifacts.verify` | `artifacts verify` | Body checklist completion |

### 5. Project Setup

| Command | Maps to | Purpose |
|---|---|---|
| `/artifacts.init` | `artifacts init` | Bootstrap a new vault |

### Explicitly out of scope (stays in `/openstation.*`)

- State transitions: `ready`, `progress`, `done`, `suspend`, `fail`, `reject`, `update`
- Execution: `run`, `check`
- Workflow scaffolds: `list.backlog` (assumes lifecycle semantics)
- Connector-driven kinds: `create.alert`

## Package layout

```
src/artifacts_os/ai/
  __init__.py            # public API
  install.py             # install/uninstall/list logic
  README.md
  claude/
    commands/            # → installed to <vault>/.claude/commands/
      artifacts.list.md
      artifacts.show.md
      artifacts.create.md
      artifacts.kinds.md
      artifacts.kinds.create.md
      artifacts.kinds.edit.md
      artifacts.validate.md
      artifacts.verify.md
      artifacts.init.md
    skills/              # → installed to <vault>/.claude/skills/
      artifacts-os/
        SKILL.md
  # opencode/            # future, mirrors `claude/`
```

Files ship via the existing Hatchling wheel target (`packages = ["src/artifacts_os"]`) — no `pyproject.toml` changes needed beyond verifying `*.md` inclusion. Runtime access uses `importlib.resources.files("artifacts_os.ai.claude")`.

## Public install API (`src/artifacts_os/ai/__init__.py`)

```python
def install(
    target: Path,
    *,
    mode: Literal["link", "copy"] = "link",
    tool: Literal["claude", "opencode"] = "claude",
    force: bool = False,
    dry_run: bool = False,
) -> InstallReport: ...

def uninstall(target: Path, *, tool: str = "claude", dry_run: bool = False) -> ...
def list_installed(target: Path) -> list[InstalledAsset]: ...
```

`artifacts init` and `artifacts ai install` both go through this API; the CLI is a thin shell.

## CLI surface

| Command | Purpose |
|---|---|
| `artifacts init` | Bootstrap a vault — internally calls `ai install` with defaults (opt-out via `--no-ai`) |
| `artifacts ai install` | (Re-)install commands + skills into `.claude/` |
| `artifacts ai install --copy` | Standalone copies (editable) |
| `artifacts ai install --link` | Symlinks (default) |
| `artifacts ai install --target DIR` | Override target |
| `artifacts ai install --tool claude\|opencode` | Pick toolchain (default: detect from `.claude/` / `.opencode/`) |
| `artifacts ai install --dry-run` | Preview |
| `artifacts ai install --force` | Overwrite user-edited copies |
| `artifacts ai uninstall` | Remove all artifacts-namespaced assets |
| `artifacts ai list` | Show what's currently installed |

## Install mode policy

| Mode | Behaviour | When |
|---|---|---|
| **Symlink** *(default)* | `<vault>/.claude/commands/artifacts.list.md` → `<site-packages>/artifacts_os/ai/claude/commands/artifacts.list.md` | Most users — `pip upgrade artifacts-os` delivers updates instantly. |
| **Copy** *(opt-in)* | Plain file copy from package into the vault | Users who want to fork/edit commands without having edits shadowed by upgrades. |

## Conflict policy

Every file artifacts-os installs is **namespace-prefixed**:

- Commands: `artifacts.*.md`
- Skills: `artifacts-os/`

Anything matching the namespace is owned by artifacts-os; anything else is the user's or another tool's and is never touched.

| Existing file | Mode | Action |
|---|---|---|
| Same content as package | any | Skip (idempotent) |
| Symlink already pointing into our package | any | Skip |
| Different content, owned by us | symlink | Replace |
| Different content, owned by us | copy | Refuse unless `--force` |
| Outside our namespace | any | Never touch |

## Repo dogfood plan

This repo's `.claude/commands/` is currently a symlink to `.openstation/commands`. To dogfood `/artifacts.*` while still serving the existing `/openstation.*` surface:

1. Convert `.claude/commands/` from symlink to a real directory.
2. Inside, create file-level symlinks:
   - `openstation.*.md` → `../../.openstation/commands/openstation.*.md` (existing source preserved).
   - `artifacts.*.md` → `../../src/artifacts_os/ai/claude/commands/*.md` (new source).
3. Same pattern applies to `.claude/skills/`.

## Edge cases to design for

| Case | Handling |
|---|---|
| Vault not initialised | `artifacts ai install` errors with "run `artifacts init` first." |
| `.claude/` missing | Created automatically. |
| User has hand-authored `.claude/commands/artifacts.list.md` | Refused in copy mode without `--force`; replaced in symlink mode. |
| `pip uninstall artifacts-os` while symlinks exist | Symlinks become dangling; `artifacts ai uninstall` should be run first (documented, not enforced). |
| Editable install (`pip install -e .`) | Symlinks resolve to the source tree — ideal for development. |
| Worktrees | `find_vault_root` walks up correctly; install targets the worktree's `.claude/`, not the main checkout. |

## Multi-tool extension point

Adding a new AI tool (e.g., OpenCode) requires only a new sibling sub-tree under `ai/`, mirroring `claude/`'s layout. No code changes — `install()` takes a `tool` parameter that selects the source sub-tree and the target dir. Auto-detection rule:

- `<vault>/.claude/` exists → install Claude assets.
- `<vault>/.opencode/` exists → install OpenCode assets.
- Both → install both (configurable).

## Spec `s2066` revision

Narrow the `ai/` module's charter from the original "agent context and execution" stub to **"AI tool integration assets"** — Claude/OpenCode commands, skills, and future hook scripts. Agent execution itself stays openstation-side per audit `r0001` §3.2.

## Decomposition plan

This epic is a **container parent** without execution work of its own. The planned decomposition is:

1. **Spec the design** — `architect` — write `s00XX-artifacts-claude-commands.md` and revise `s2066`. *(not yet created)*
2. **Implement the install module + CLI** — `developer` — `ai/install.py`, `ai/__init__.py`, `cli ai install/uninstall/list` subcommands, `init` integration, dogfood update, tests. *(not yet created)*
3. **Author the 9 commands + skill** — `author` — markdown content under `ai/claude/commands/` and `ai/claude/skills/artifacts-os/SKILL.md`. *(being broken out per-category)*
4. **Document the AI module** — `technical-writer` — `docs/ai.md`, `ai/README.md`, root `README.md` and `CLAUDE.md` updates. *(not yet created)*

Sequencing: 1 → (2 ∥ 3) → 4.

## Subtasks

- [[t0043-author-browse-and-inspect-claude]] — author the 3 Browse & Inspect commands (`/artifacts.list`, `/artifacts.show`, `/artifacts.kinds`).
- [[t0044-cli-ai-install-module]] — implement `ai/install.py`, the `artifacts ai install/uninstall/list` CLI, `artifacts init` integration, and the repo dogfood (decomposition step 2).
- [[t0046-author-artifacts-create-command]] — author the single `/artifacts.create` command (Category 2 — Author artifacts).

## Requirements

1. The 9-command surface above is implemented as markdown command files under `src/artifacts_os/ai/claude/commands/` and ships with the wheel.
2. A public `artifacts_os.ai` install API (`install`, `uninstall`, `list_installed`) supports symlink (default) and copy (opt-in) modes, namespace-aware conflict policy, `--force`, `--dry-run`, and a `tool` parameter for future multi-tool support.
3. CLI surface `artifacts ai install/uninstall/list` is wired in; `artifacts init` invokes `install()` by default with `--no-ai` opt-out.
4. An `artifacts-os` skill ships at `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`.
5. Repo dogfood: `.claude/commands/` becomes a real directory with file-level symlinks to both `.openstation/commands/openstation.*.md` and `src/artifacts_os/ai/claude/commands/artifacts.*.md`.
6. Spec `s2066` is revised to formalise the narrowed `ai/` module charter.
7. Documentation updates: `docs/ai.md`, `src/artifacts_os/ai/README.md`, root `README.md`, `CLAUDE.md` "Project Structure".
8. No openstation lifecycle logic leaks into `/artifacts.*` commands; no per-kind subcommands hardcode kinds outside the user's registry.
9. Module DAG remains intact (`core → log → ai`); no peer imports introduced.

## Verification

- [ ] All 4 planned subtasks reach `done`.
- [ ] `pip install -e .` followed by `artifacts init` in a fresh dir produces a working `.claude/commands/artifacts.*.md` set and `.claude/skills/artifacts-os/`.
- [ ] `artifacts ai install --copy` produces standalone files; `--link` (default) produces symlinks resolving into `site-packages`.
- [ ] `artifacts ai install --dry-run` previews actions without writing.
- [ ] `artifacts ai uninstall` removes only artifacts-namespaced files; user files are untouched.
- [ ] Repo's own `.claude/commands/` lists both `openstation.*` and `artifacts.*` after the dogfood update.
- [ ] `s2066` reflects the narrowed scope.
- [ ] Test suite green; no new cross-module imports.
- [ ] Combined result reviewed by `user` before this epic is closed.