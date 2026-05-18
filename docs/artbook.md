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
    # dest omitted — canonical default = artifacts/agents/
    promote: .claude/agents/
    description: Standard agent specs.

  - name: skills
    src: src/ai/skills/
    dest: artifacts/skills/   # explicit — src basename differs from default
    promote: .claude/skills/
    description: Claude skills.
    recurse: true

  - name: kinds
    src: artifacts/kinds/
    # dest omitted — canonical default = artifacts/kinds/
    # promote omitted — kinds have no tool-specific consumer
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
| `dest` | no | Canonical landing directory, relative to the consumer's vault root. **Must resolve under `artifacts/`** — paths outside `artifacts/` raise `ManifestError`. When omitted, defaults to `artifacts/<basename(src)>/`. |
| `promote` | no | Tool-shaped path where canonical files are also surfaced. String shorthand (`".claude/agents/"`) or object form (`{target: …, mode: symlink|copy}`). See [§ Promotion](#promotion). |
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

`dest` is always relative to the consumer's vault root and
**must resolve under `artifacts/`** — it is the canonical
landing for book content. Using a path outside `artifacts/`
(e.g., `dest: .claude/agents/`) raises `ManifestError`:

```
book 'agents' dest: '.claude/agents/' is not under 'artifacts/'.
dest: is canonical-only — move tool-specific paths to promote:
```

To also surface book content in tool-specific locations, use
`promote:` alongside `dest:` (or omit `dest:` and use the
canonical default). See [§ Promotion](#promotion).

| Book content | Canonical `dest` | Tool view via `promote` |
|---|---|---|
| Claude agent specs | `artifacts/agents/` (or omit for default) | `.claude/agents/` |
| Claude slash commands | `artifacts/commands/` | `.claude/commands/` |
| Claude skills | `artifacts/skills/` | `.claude/skills/` |
| Artifact kinds | `artifacts/kinds/` (or omit for default) | *(none — canonical-only)* |

When `dest:` is omitted, the default is computed as
`artifacts/<basename(src)>/` — the canonical mirror of `src:`
under the vault's `artifacts/` tree:

| `src` | Default `dest` |
|---|---|
| `artifacts/agents/` | `artifacts/agents/` |
| `src/artifacts_os/ai/claude/skills/` | `artifacts/skills/` |
| `kinds/` | `artifacts/kinds/` |

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
The current `artbook.yaml` (post-promotion migration; see
[§ Migration](#migration) for the before/after diff):

```yaml
version: 1

distro:
  name: artifacts-os
  description: Default agents shipped by artifacts-os for consumers of the library.

books:
  - name: agents
    src: artifacts/agents/
    # dest omitted — canonical default = artifacts/agents/
    promote: .claude/agents/
    description: Default agent specs (architect, developer, researcher, etc.).

  - name: commands
    src: src/artifacts_os/ai/claude/commands/
    dest: artifacts/commands/
    promote: .claude/commands/
    description: Slash commands for artifacts CLI.

  - name: skills
    src: src/artifacts_os/ai/claude/skills/
    dest: artifacts/skills/
    promote: .claude/skills/
    description: Skills that teach Claude how to use artifacts-os.
    recurse: true

  - name: kinds
    src: artifacts/kinds/
    # dest omitted — canonical default = artifacts/kinds/
    # promote omitted — kinds have no tool-specific consumer
    description: Standard artifact kinds (task, note, spec, research, agent).
    recurse: true
```

A consumer pulling all four books gets canonical content under
`artifacts/` (visible to `artifacts list`) **and** a fully wired
Claude Code setup (`.claude/agents/`, `.claude/commands/`,
`.claude/skills/`) via promotion symlinks. Both views stay in
sync — edits to files under `artifacts/` are immediately visible
to Claude through the symlinks.

---

## Consumer Quickstart — `artifacts init --distro`

The fastest way to bootstrap a new project and pull books from a
distro in one step is `artifacts init --distro <url>`.

### Non-interactive — pull everything

```bash
# Initialise with defaults and pull all books, all items
artifacts init --distro https://github.com/my-org/artbook-defaults -y
```

`-y` accepts all default selections (settings tier) and pulls
**every book and every item** from the distro without prompting.

### Non-interactive — pull specific books

```bash
# Pull only the 'agents' book
artifacts init --distro https://github.com/my-org/artbook-defaults \
    --book agents -y

# Pull agents (full) and skills (filtered to artifacts-os only)
artifacts init --distro https://github.com/my-org/artbook-defaults \
    --book agents --book skills:artifacts-os -y
```

`--book` is repeatable. `NAME` pulls the whole book; `NAME:item,item`
pulls a subset of items from that book.

### Interactive

Without `-y`, `init` walks two stages:

```bash
artifacts init --distro https://github.com/my-org/artbook-defaults
# Stage 1: pick settings tier
# Stage 2..N: one multi-select prompt per book in the distro manifest
```

```
Settings tier (1 of N):
  1) minimal      — header + lifecycle views (active / ready / done)
  2) standard     — adds per-type slices, default_views, cross-kind 'recent'

Choice [2]: ⏎

Selected:
  template : standard
  distro   : https://github.com/my-org/artbook-defaults

Writing files...
  ✓ artifacts.yaml

Fetching distro manifest…

Book 'agents' (9 items) — comma-separated numbers, '*' for all, '-' for none:
  1) architect        [default]
  ...

Choice [*]: 1,3 ⏎
  ✓ agents: 2 files written
```

### What gets written

1. `artifacts.yaml` — with `artbook.distro_url` set to `<url>`
2. Book content written to canonical `artifacts/…` locations
3. Promotion symlinks (or copies) created at each book's `promote:` target

The `artifacts.yaml` is written **before** the distro clone so that
`pull_book` destination resolution is always valid. Pass
`--no-promote` to skip step 3 for this invocation (see
[§ Consumer behaviour](#consumer-behaviour)).

### No-distro fallback

When neither `--distro` nor `$ARTIFACTS_DISTRO_URL` is set, `init`
writes `artifacts.yaml` and installs the bundled `artifacts-os`
skill — writing it to `artifacts/skills/artifacts-os/SKILL.md`
(canonical) and promoting a symlink to
`.claude/skills/artifacts-os/SKILL.md`:

```bash
# Fresh project, no distro — just the skill bootstrap
artifacts init -y
```

### Dry-run

```bash
artifacts init --distro https://github.com/my-org/artbook-defaults -y --dry-run
```

Prints what vault files would be written and reports the planned
distro pull **without** cloning or writing anything.

### Default distro from the environment

If most of your projects pull from the same distro, export
`ARTIFACTS_DISTRO_URL` once and drop the `--distro` flag from your
`init` invocations:

```bash
export ARTIFACTS_DISTRO_URL=https://github.com/my-org/artbook-defaults

# Picks up the env var automatically
artifacts init -y

# With book filter
artifacts init --book agents -y
```

Rules:

- An explicit `--distro <url>` on the CLI **always** overrides the env var.
- An empty or whitespace-only `ARTIFACTS_DISTRO_URL` is treated as unset
  (book loop is skipped; D2 fallback runs).
- When init resolves the URL from the env var, the `Selected:` summary
  annotates the line — for example `distro   : <url> (from
  ARTIFACTS_DISTRO_URL)` — so the source is always visible.
- Only `artifacts init` reads the env var. Once `artbook.distro_url`
  is written into `artifacts.yaml`, downstream `book list` / `book show`
  / `book pull` commands use that file as the source of truth.

---

## Promotion

The promotion mechanism surfaces canonical book content at
tool-specific paths declared by the distro author. A `book pull`
writes files to their canonical `artifacts/…` location **and then**
runs a post-step that creates symlinks (or copies) at the `promote:`
target. Both views stay in sync from the first pull; the operator
runs no manual link step.

### `promote:` field

Add `promote:` to any book entry in `artbook.yaml`. The field
accepts two forms:

**String shorthand** (path only; mode uses the per-vault default,
which is `symlink`):

```yaml
- name: agents
  src: artifacts/agents/
  promote: .claude/agents/
```

**Object form** (explicit per-book mode override):

```yaml
- name: skills
  src: src/ai/skills/
  dest: artifacts/skills/
  promote:
    target: .claude/skills/
    mode: copy      # 'symlink' (default) or 'copy'
```

| Promote field | Required | Description |
|---|---|---|
| `target` | yes (object form) | Vault-relative path. Same escape guard as `dest:` — no `..`, no absolute paths. |
| `mode` | no | `symlink` (default) or `copy`. Any other value raises `ManifestError`. |

When `promote:` is absent the book is **canonical-only** — no
tool-shaped view is created.

### Default mode: symlink with automatic copy fallback

The default promotion mode is **`symlink`**. Each promoted file
becomes a relative symlink pointing at the canonical path under
`artifacts/`:

```
.claude/agents/architect.md → ../../artifacts/agents/architect.md
```

Relative links survive vault relocation (directory rename);
absolute links do not.

If the filesystem raises `OSError` on `os.symlink` (Windows
without developer mode, some Docker volumes), the CLI falls back
to copying for that file and logs once per book pull:

```
book 'agents' promotion: symlinks not supported on this
filesystem; using copy mode. Set artbook.promote_mode: copy
in artifacts.yaml to silence this notice.
```

### When to set `mode: copy`

Use `mode: copy` explicitly when:

- The consuming tool reads inode metadata that changes the
  behaviour for symlinks vs real files.
- The promotion target is on a separate filesystem that does
  not support symlinks.
- You want the distro to always copy regardless of the
  consumer's per-vault setting.

### Worked example

Distro `artbook.yaml`:

```yaml
version: 1
distro:
  name: my-org-defaults
  description: Shared agents for my-org projects.
books:
  - name: agents
    src: artifacts/agents/
    promote: .claude/agents/
    description: Standard agent specs.
```

After `artifacts book pull agents`:

```
<vault>/
├── artifacts.yaml
├── artifacts/
│   ├── .artbook/
│   │   └── state.json          ← tracks promoted files
│   └── agents/
│       ├── architect.md        ← canonical
│       └── developer.md        ← canonical
└── .claude/
    └── agents/
        ├── architect.md → ../../artifacts/agents/architect.md
        └── developer.md → ../../artifacts/agents/developer.md
```

Both `artifacts list --kind agent` and Claude Code now see the
same content. Editing `artifacts/agents/architect.md` is
immediately visible through the symlink.

### State tracking

Promotion state is recorded in `artifacts/.artbook/state.json`.
This file tracks which files were promoted per book so that a
re-pull can clean up stale targets (e.g., an agent the distro
removed) without touching user-authored files in the same
directory. The state file is managed automatically; you do not
need to edit it.

---

## Consumer behaviour

### `--no-promote` flag

Pass `--no-promote` to `book pull` or `init` to skip the
promotion step for that invocation. The canonical write under
`artifacts/…` still happens; only the post-step is disabled.

```bash
# Canonical-only pull — useful for debugging what the distro ships
artifacts book pull agents --no-promote

# Init without promotion
artifacts init --distro https://github.com/my-org/defaults -y --no-promote
```

### `artbook.promotion` setting

Set `artbook.promotion: disabled` in `artifacts.yaml` for a
**persistent** opt-out — every `book pull` and `init` book step
will skip promotion until the setting is removed or changed.

```yaml
artbook:
  distro_url: https://github.com/my-org/artbook-defaults
  promotion: disabled
```

| Value | Effect |
|---|---|
| `enabled` (default) | Promotion runs after every pull. |
| `disabled` | Promotion is skipped; only canonical writes occur. |

Invalid values raise `SettingsError` at load time.

### `artbook.promote_mode` setting

Override the default promotion mode for all books in this vault:

```yaml
artbook:
  distro_url: https://github.com/my-org/artbook-defaults
  promote_mode: copy
```

| Value | Effect |
|---|---|
| absent (default) | Per-promotion `mode` or `symlink` default. |
| `symlink` | Force symlink mode for all books (with automatic copy fallback). |
| `copy` | Force copy mode; no symlinks created, no fallback warning. |

Invalid values raise `SettingsError` at load time.

### Precedence rule

When determining the effective mode for a specific file, the
first matching rule wins:

1. **Per-promotion `promote.mode`** in the manifest (distro author).
2. **`artbook.promote_mode`** in `artifacts.yaml` (consumer override).
3. **Default `symlink`** (with automatic copy fallback).

`--no-promote` is a separate override that disables the entire
promotion step regardless of mode settings.

### `artifacts book promote` verb

Re-runs the promotion step against the current canonical content —
useful after restoring a vault from backup, changing the
`promote_mode` setting, or manually deleting a promotion target.

```bash
# Re-promote all books that have a promote: field
artifacts book promote

# Re-promote a specific book
artifacts book promote agents

# Rebuild state from scratch (ignores recorded stale-target info)
artifacts book promote agents --clean

# Preview what would be written/cleaned without making changes
artifacts book promote --dry-run

# Emit PromotionReport as JSON
artifacts book promote agents --json
```

`book promote` never clones the distro — it only operates on
canonical content already present under `artifacts/`.

---

## Migration

### Converting a pre-spec v1 manifest

The v1 schema is unchanged — no `version:` bump. The semantics
are tightened: `dest:` is now **canonical-only** (must resolve
under `artifacts/`) and the old pattern of pointing `dest:` at a
tool-specific path (e.g., `dest: .claude/agents/`) now raises
`ManifestError`.

To migrate, move the tool-specific path from `dest:` to `promote:`
and either omit `dest:` (taking the canonical default) or set it
explicitly under `artifacts/`.

### Worked example — artifacts-os distro

**Before** (pre-spec v1 with non-canonical `dest:`):

```yaml
version: 1
distro:
  name: artifacts-os
books:
  - name: agents
    src: artifacts/agents/
    dest: .claude/agents/           # ← non-canonical — now ManifestError
    description: Default agent specs.

  - name: commands
    src: src/artifacts_os/ai/claude/commands/
    dest: .claude/commands/         # ← non-canonical — now ManifestError
    description: Slash commands for artifacts CLI.

  - name: skills
    src: src/artifacts_os/ai/claude/skills/
    dest: .claude/skills/           # ← non-canonical — now ManifestError
    description: Skills.
    recurse: true

  - name: kinds
    src: artifacts/kinds/
    dest: artifacts/kinds/          # ← already canonical
    description: Standard artifact kinds.
    recurse: true
```

**After** (canonical landing + promote):

```yaml
version: 1
distro:
  name: artifacts-os
books:
  - name: agents
    src: artifacts/agents/
    # dest omitted — canonical default = artifacts/agents/
    promote: .claude/agents/
    description: Default agent specs.

  - name: commands
    src: src/artifacts_os/ai/claude/commands/
    dest: artifacts/commands/       # explicit canonical
    promote: .claude/commands/
    description: Slash commands for artifacts CLI.

  - name: skills
    src: src/artifacts_os/ai/claude/skills/
    dest: artifacts/skills/         # explicit canonical
    promote: .claude/skills/
    description: Skills.
    recurse: true

  - name: kinds
    src: artifacts/kinds/
    # dest omitted — canonical default = artifacts/kinds/
    # promote omitted — kinds have no tool-specific consumer
    description: Standard artifact kinds.
    recurse: true
```

**Migration steps per book:**

| Book | Change |
|---|---|
| `agents` | Remove `dest: .claude/agents/` (the canonical default `artifacts/agents/` takes over). Add `promote: .claude/agents/`. |
| `commands` | Change `dest: .claude/commands/` → `dest: artifacts/commands/` (explicit canonical). Add `promote: .claude/commands/`. |
| `skills` | Change `dest: .claude/skills/` → `dest: artifacts/skills/` (explicit canonical — `src` basename is `skills`). Add `promote: .claude/skills/`. |
| `kinds` | `dest: artifacts/kinds/` was already canonical; remove it (default suffices). No `promote:` needed — kinds have no tool-specific consumer. |

### Schema note

The manifest `version:` stays `1`. There is no back-compat shim.
Any third-party manifest with non-canonical `dest:` values must
be updated before it will parse. No deprecation warning is emitted —
the error message is actionable:

```
book 'agents' dest: '.claude/agents/' is not under 'artifacts/'.
dest: is canonical-only — move tool-specific paths to promote:
```

See spec `s0031-artbook-post-pull-artifact-promotion` for the full
design rationale (§§ 2–3).
