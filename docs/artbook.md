# Artbook — Publishing and Consuming Distros

An **artbook distro** is a git repository that publishes named
collections of files — called **books** — that consumers pull into
their own projects with `artifacts book pull`. Typical books ship
Claude agent specs, slash commands, skills, or artifact kind
definitions.

This document covers the **author side** (how to create a distro).
For the consumer CLI (`book list`, `book show`, `book pull`) see
[`src/artifacts_os/cli/README.md`](../src/artifacts_os/cli/README.md#book).

---

## Anatomy of `artbook.yaml`

Place `artbook.yaml` at the root of the distro repository.

```yaml
version: 1

distro:
  name: my-org-defaults
  description: Shared agents and skills for my-org projects.

books:
  - name: agents
    src: artifacts/agents/
    dest: .claude/agents/
    description: Standard agent specs.

  - name: skills
    src: src/ai/skills/
    dest: .claude/skills/
    description: Claude skills.
    recurse: true

  - name: kinds
    src: artifacts/kinds/
    dest: artifacts/kinds/
    description: Standard artifact kinds.
    recurse: true
```

### Top-level fields

| Field | Required | Description |
|-------|----------|-------------|
| `version` | yes | Must be `1`. Version gate — clients reject unknown versions. |
| `distro.name` | yes | Short identifier for the distro (shown in CLI output). |
| `distro.description` | no | One-line description shown in `book list`. |
| `books` | yes | Non-empty list of book entries (see below). |

### Book entry fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Unique book identifier. Used in `book pull <name>`. |
| `src` | yes | Directory path relative to the distro root. Must not be absolute or contain `..`. |
| `dest` | yes | Directory path relative to the consumer's vault root where files are written. Must not be absolute or contain `..`. |
| `description` | no | One-line description shown in `book list` / `book show`. |
| `recurse` | no | `true` to use folder-of-folders mode (see below). Default: `false`. |
| `files` | no | Explicit allowlist of filenames (see below). Mutually exclusive with `recurse`. |

---

## Walker modes

### Flat walker (default)

When `recurse` is omitted or `false` and `files` is omitted, the
walker scans the top level of `src/` and ships every `*.md` file
except `README.md` and dotfiles. Subdirectories are ignored.

```
src/agents/
  architect.md    ← shipped as .claude/agents/architect.md
  developer.md    ← shipped
  README.md       ← excluded (always)
  .draft.md       ← excluded (dotfile)
  archive/        ← excluded (subdirectory)
```

Use flat walker for simple directories of markdown files —
agent specs, slash commands.

### Recurse walker (`recurse: true`)

Each **direct subdirectory** of `src/` is treated as a unit. The
walker descends each unit's full subtree and ships every file
except dotfiles, `__pycache__/`, and `.pyc`/`.pyo` files. Loose
files directly under `src/` (not inside a unit folder) are
silently ignored.

```
src/skills/
  artifacts-os/
    SKILL.md      ← shipped as .claude/skills/artifacts-os/SKILL.md
    __init__.py   ← shipped (Python infra — see note below)
  release-changelog/
    SKILL.md      ← shipped as .claude/skills/release-changelog/SKILL.md
  README.md       ← ignored (loose file at src/ root)
```

> **Note on Python files:** `__init__.py` is not excluded by the
> recurse walker. If your skill folders are Python packages and you
> don't want to ship `__init__.py` to consumers, move the skill
> content to a non-package directory or use an explicit `files:`
> allowlist per unit.

Use recurse walker for folder-of-folders layouts — skills, kinds,
or any collection where each unit is a directory.

### Allowlist (`files:`)

When `files:` is set, only the listed filenames are shipped. Files
must exist directly under `src/` (no path separators allowed).

```yaml
- name: core-agents
  src: artifacts/agents/
  dest: .claude/agents/
  files:
    - architect.md
    - developer.md
```

Use allowlist when you want to curate exactly which files ship from
a larger source directory.

---

## Destination patterns

`dest` is always relative to the consumer's vault root (the
directory containing `artifacts.yaml`).

| Book content | Typical `dest` | Lands in |
|---|---|---|
| Claude agent specs | `.claude/agents/` | Claude Code sub-agent list |
| Claude slash commands | `.claude/commands/` | Claude Code slash commands |
| Claude skills | `.claude/skills/` | Claude Code skills |
| Artifact kinds | `artifacts/kinds/` | Vault kind definitions |

`dest` is not restricted to `.claude/` — the vault-escape guard
only prevents writing outside the vault root.

---

## Publishing a distro

A distro is any git repository with `artbook.yaml` at its root.
No special hosting is required — any URL `git clone` can reach
works.

The distro repository can be:
- **A dedicated defaults repo** — `artbook.yaml` + source
  directories, nothing else.
- **A project repo doubling as its own distro** — `artbook.yaml`
  at the root of an existing repo (this is how `artifacts-os`
  itself is published).

Consumers point `artbook.distro_url` at your repo's clone URL:

```yaml
# consumer's artifacts.yaml
artbook:
  distro_url: https://github.com/my-org/artbook-defaults
```

The CLI clones the repo at HEAD on every `book pull`, so consumers
always get the latest committed content. There is no pinning or
lock-file mechanism in the MVP.

---

## Local development

`book list` and `book show` have a local-manifest auto-detect:
when `artbook.yaml` is present at the vault root, they read it
directly without cloning. This lets you author and inspect a
distro from inside the same repository.

```bash
# works without distro_url configured
artifacts book list
artifacts book show agents
```

`book pull` always requires a remote clone and will fail if
`artbook.distro_url` is not configured. To test a pull locally,
set `distro_url` to the repo's own remote URL.

---

## Item selection (consumer pull)

`artifacts book pull <name>` pulls every item in a book by default.
Pass one or more `ITEM` names after the book name to pull only a
matching subset — no manifest change or new book entry required.

```bash
# Pull the whole book (default behaviour — unchanged)
artifacts book pull agents

# Pull only architect.md and developer.md from a flat book
artifacts book pull agents architect developer

# Extension-qualified form also works
artifacts book pull agents architect.md developer.md

# Pull only the artifacts-os unit from a recurse book
artifacts book pull skills artifacts-os

# Pull two units from a kinds book
artifacts book pull kinds task note
```

### Matching rules

| Walker mode | Item matches |
|-------------|-------------|
| Flat (D20) or allowlist (D18) | Filename **stem** (`architect`) or full filename (`architect.md`). Case-sensitive. |
| Recurse (D26) | **Unit folder name** — the direct subdirectory of `src/` whose subtree should be included (`artifacts-os`, `task`). All files within the unit are included. |

### Error handling

If any supplied item name is not found in the book, the command
exits 1 **before writing any files** and lists the available items:

```
error: items not found in book 'agents': ghost
       Available items: architect, developer
       Run `artifacts book show agents` to see all items.
```

This guarantee means a partially-misspelled item list never leaves
the destination in a half-updated state.

`--dry-run` and `--json` both honour the item filter, so you can
preview or script filtered pulls the same way as full pulls.

---

## Example — artifacts-os distro

`artifacts-os` publishes itself as a distro at the repo root.
The current `artbook.yaml`:

```yaml
version: 1

distro:
  name: artifacts-os
  description: Default agents shipped by artifacts-os for consumers of the library.

books:
  - name: agents
    src: artifacts/agents/
    dest: .claude/agents/
    description: Default agent specs (architect, developer, researcher, etc.).

  - name: commands
    src: src/artifacts_os/ai/claude/commands/
    dest: .claude/commands/
    description: Slash commands for artifacts CLI.

  - name: skills
    src: src/artifacts_os/ai/claude/skills/
    dest: .claude/skills/
    description: Skills that teach Claude how to use artifacts-os.
    recurse: true

  - name: kinds
    src: artifacts/kinds/
    dest: artifacts/kinds/
    description: Standard artifact kinds (task, note, spec, research, agent).
    recurse: true
```

A consumer pulling all four books gets a fully wired Claude Code
setup (`.claude/agents/`, `.claude/commands/`, `.claude/skills/`)
plus the standard artifact kind definitions (`artifacts/kinds/`).
