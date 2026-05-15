---
kind: note
id: n0013
name: artbook-book-command-user-manual
status: active
task: "[[t0151-spec-the-artbook-model]]"
agent: architect
created: 2026-05-15
---

# Artbook Book Command — User Manual

A practical guide to using `artifacts book list / show / pull`,
the MVP of the artbook distribution model. Design reference:
[[s0029-artbook-mvp-distribution-model]].

> **MVP note.** The current version ships one book type
> (`agents`), always pulls from `main`, never caches, and writes
> to a single destination per book type. Update / diff / remove /
> multi-distro / version pinning are deferred to later releases.

---

## 1. Concepts in 30 seconds

- A **distro** is a git repository with an `artbook.yaml` manifest
  at its root.
- The manifest lists **books** — named, typed bundles that point
  at a file or folder *anywhere* in the repo.
- The CLI exposes three verbs: `list` (what does this distro
  ship?), `show` (what's inside one book?), `pull` (install it
  into my project).
- Every command fetches fresh from the distro's `main` branch —
  there is no cache.

---

## 2. One-time setup

Before any `book` command works, the project needs (a) an
initialised artifacts-os vault and (b) a configured distro URL.

```console
$ cd my-project

$ artifacts init
✓ Wrote artifacts.yaml (tier: standard)
✓ Wrote CLAUDE.md
✓ Created artifacts/ vault tree
```

Open `artifacts.yaml` and add the `artbook:` block:

```yaml
# artifacts.yaml (excerpt — only the new block shown)
artbook:
  distro_url: https://github.com/leonprou/artifacts-os-defaults
```

That's it. The CLI looks for `artbook.distro_url` on every
invocation; no global config, no environment variables.

---

## 3. `artifacts book list` — what does this distro ship?

Fetches the manifest from the configured distro and prints one
row per book.

```console
$ artifacts book list
Distro: artifacts-os-defaults — Default agents for artifacts-os consumers.
URL:    https://github.com/leonprou/artifacts-os-defaults @ a1b2c3d

Name    Type    Path                  Description
agents  agents  openstation/agents/   Default agent specs.

1 book.
```

The `@ a1b2c3d` is the short SHA of `main`'s tip at the time of
the call — useful for reporting issues and pinning future pull
expectations.

Add `--json` for scripting:

```console
$ artifacts book list --json | jq '.books[].name'
"agents"
```

---

## 4. `artifacts book show <name>` — what's inside a book?

Renders the book's details and (for `type: agents`) the list of
files the consumer would receive on `pull`.

```console
$ artifacts book show agents
Book:        agents
Type:        agents
Path:        openstation/agents/
Description: Default agent specs.

Distro:      artifacts-os-defaults
URL:         https://github.com/leonprou/artifacts-os-defaults @ a1b2c3d

Destination: .claude/agents/

Contents (9 files, by directory walk):
  architect.md
  author.md
  developer.md
  devrel.md
  product-manager.md
  project-manager.md
  researcher.md
  security-engineer.md
  technical-writer.md
```

The `Contents (...)` line distinguishes the two ways a book can
declare its content:

- **`by directory walk`** — the manifest has no `files:` field,
  so the handler walks `book.path/` and applies the convention
  filter (include `*.md`, exclude `README.md` and dotfiles).
- **`from files allowlist`** — the manifest pinned exactly which
  filenames to ship.

```
Contents (3 files, from `files` allowlist):
  architect.md
  developer.md
  researcher.md
```

`--json` returns a structured payload:

```console
$ artifacts book show agents --json | jq '.contents'
[
  "architect.md",
  "author.md",
  …
]
```

---

## 5. `artifacts book pull <name>` — install the files

Copies the book's content into the consumer's project. For
`type: agents`, the destination is `<project>/.claude/agents/`.

### 5.1 First-time pull (fresh project)

```console
$ artifacts book pull agents
Pulling book 'agents' from artifacts-os-defaults @ a1b2c3d…

Action  Destination
write   .claude/agents/architect.md
write   .claude/agents/author.md
write   .claude/agents/developer.md
write   .claude/agents/devrel.md
write   .claude/agents/product-manager.md
write   .claude/agents/project-manager.md
write   .claude/agents/researcher.md
write   .claude/agents/security-engineer.md
write   .claude/agents/technical-writer.md

Summary: 9 written (0 overwritten, 9 new).
```

Open the project in Claude Code — the agents are immediately
usable.

### 5.2 Re-pull after distro updates

```console
$ artifacts book pull agents
Pulling book 'agents' from artifacts-os-defaults @ e7f8g9h…

Action      Destination
overwrite   .claude/agents/architect.md
overwrite   .claude/agents/author.md
…
overwrite   .claude/agents/technical-writer.md

Summary: 9 written (9 overwritten, 0 new).
```

Every file is rewritten on every pull. The MVP does not compare
content — re-running with no upstream changes still overwrites
all 9 files (byte-identical result, but the writes happen).
This is intentional — content-compare and partial-update are a
future spec.

### 5.3 Preview before writing (`--dry-run`)

```console
$ artifacts book pull agents --dry-run
Pulling book 'agents' from artifacts-os-defaults @ a1b2c3d… [dry-run]

Action          Destination
[would] write   .claude/agents/architect.md
[would] write   .claude/agents/author.md
…
[would] write   .claude/agents/technical-writer.md

Summary [dry-run]: would write 9 (would overwrite 0, would create 9).
```

No files are touched; the tmpdir clone still happens.

### 5.4 Pull over a symlink layout

If a destination path is a symlink (broken or live), pull
**unlinks the symlink first** and writes a regular file in its
place. The symlink's target is never modified.

```console
$ ls -la .claude/agents/architect.md
lrwxr-xr-x  …  .claude/agents/architect.md -> ../../openstation/agents/architect.md

$ artifacts book pull agents
…
Action                  Destination
overwrite (was symlink) .claude/agents/architect.md
…

$ ls -la .claude/agents/architect.md
-rw-r--r--  …  .claude/agents/architect.md
```

If you maintain a symlink farm and want to preserve it, set up
the symlinks **after** the pull, or write a small script that
re-creates them post-pull.

### 5.5 Machine-readable output (`--json`)

`pull --json` emits one JSON object per file on stdout (JSONL),
followed by a final summary object:

```console
$ artifacts book pull agents --json
{"action": "write", "destination": ".claude/agents/architect.md", "overwritten": false, "was_symlink": false}
{"action": "write", "destination": ".claude/agents/author.md", "overwritten": false, "was_symlink": false}
…
{"summary": {"written": 9, "overwritten": 0, "new": 9}, "distro": {"url": "https://github.com/leonprou/artifacts-os-defaults", "sha": "a1b2c3d"}, "book": "agents"}
```

---

## 6. Authoring a distro

If you maintain agents for your team and want to expose them via
`artifacts book pull`, your repo needs **one file**: an
`artbook.yaml` at the root.

### 6.1 Layout A — dedicated distro repo

Keep agents in a top-level `agents/` directory:

```
artbook-defaults/
├── artbook.yaml
└── agents/
    ├── architect.md
    ├── developer.md
    └── …
```

`artbook.yaml`:

```yaml
version: 1

distro:
  name: artifacts-os-defaults
  description: Default agents for artifacts-os consumers.

books:
  - name: agents
    type: agents
    path: agents/
    description: Default agent specs.
```

### 6.2 Layout B — project repo doubling as its own distro

Most repos don't want a dedicated layout. Point the manifest at
wherever the agents already live:

```
my-project/
├── artbook.yaml             # adds 10 lines, ships the project's existing files
├── pyproject.toml
├── src/...
└── openstation/
    └── agents/              # the book's content — already used by the project
        ├── architect.md
        ├── developer.md
        └── …
```

`artbook.yaml`:

```yaml
version: 1

distro:
  name: my-project-agents

books:
  - name: agents
    type: agents
    path: openstation/agents/
```

The same files serve the project's own use *and* downstream
consumers — no duplication, no reorganisation.

### 6.3 Pinning the file list (`files:`)

By default, the agents handler walks `book.path/` and ships
every `*.md` file (except `README.md` and dotfiles). To lock the
exact contents you ship, add a `files:` allowlist:

```yaml
version: 1

distro:
  name: artifacts-os-defaults

books:
  - name: agents
    type: agents
    path: openstation/agents/
    files:
      - architect.md
      - developer.md
      - researcher.md
```

When `files:` is set, **only** those files are shipped — and a
missing entry causes a hard error (`error: book 'agents' files
entry 'missing.md' not found at openstation/agents/missing.md`).

Choose the mode that fits:

| Style | Use when |
|-------|----------|
| Directory walk (omit `files:`) | "The directory *is* the book — ship everything in it." |
| Allowlist (`files: [...]`) | "I want to control exactly which files consumers receive." |

### 6.4 Manifest schema reference

```yaml
version: 1                          # required, must be 1

distro:
  name: <string>                    # required
  description: <string>             # optional

books:
  - name: <string>                  # required, unique
    type: agents                    # required (only `agents` in MVP)
    path: <distro-relative-path>    # required
    description: <string>           # optional
    files:                          # optional allowlist
      - <filename>
      - …
```

Sub-paths in `files:` (anything with `/`) are rejected — the MVP
is non-recursive; books are flat.

---

## 7. Error reference

| Exit | Cause | Fix |
|------|-------|-----|
| 0 | Success. | — |
| 1 | Runtime error (clone failed, manifest parse failed, unknown book, unknown type, version mismatch, missing allowlisted file). | Read the printed `error:` line; remediation hint follows it. |
| 2 | Usage error (bad flag, missing positional, `--dry-run` on a non-`pull` verb). | `artifacts book --help` or `artifacts book <verb> --help`. |
| 3 | Vault not initialised. | Run `artifacts init` in the project root. |
| 4 | `artbook.distro_url` missing or empty in `artifacts.yaml`. | Add `artbook.distro_url: <git-url>` to `artifacts.yaml`. |

Common one-liners:

```
error: artbook.distro_url not configured in artifacts.yaml
       Add `artbook.distro_url: <git-url>` to artifacts.yaml.

error: git clone failed (exit 128)
       URL: https://github.com/example/typo
       stderr: fatal: repository '...' not found

error: artbook.yaml not found at distro root
       URL: https://github.com/some-random/repo
       Is this URL pointing at a distro repo?

error: this artifacts-os version speaks artbook manifest v1; distro declares v2
       Upgrade artifacts-os to a version that supports manifest v2.

error: book 'kinds' not found in distro 'artifacts-os-defaults'
       Available books: agents.

error: unknown book type 'kinds' for book 'kinds'
       This artifacts-os version supports: agents.

error: book 'agents' files entry 'missing.md' not found at openstation/agents/missing.md

error: destination .claude/agents/architect.md is a directory; refusing to overwrite
       Resolve the structural mismatch and re-run `artifacts book pull agents`.
```

---

## 8. FAQ

**Q. Can I pull from a private repo?**
Not in v1. The MVP relies on plain `git clone` working against
the URL with no credential dance. Use a public repo or a host
configured for ambient auth (SSH agent, gh CLI). Private-repo
auth is a deferred spec.

**Q. Can I pin to a tag or commit?**
Not in v1. Always `main`. Version pinning is deferred.

**Q. Can I have multiple distros for one project?**
Not in v1. One `artbook.distro_url` per project. Multi-distro is
deferred.

**Q. What happens to files I added to `.claude/agents/` that
aren't in the book?**
Left alone. `book pull` writes only the files the book ships; it
never deletes extras. (A future `book remove` / `book sync`
verb handles cleanup.)

**Q. Why is everything rewritten on every pull, even unchanged
files?**
The MVP doesn't content-compare — it overwrites all files in
the book unconditionally. Cost is one re-write per file; result
is byte-identical to the prior pull when the distro hasn't
moved. Smarter behaviour belongs to `book update`, deferred.

**Q. Why is the destination `.claude/agents/` and not
`openstation/agents/` or both?**
The MVP writes to **one** destination per book type, and
`.claude/agents/` is what every Claude Code project reads from.
The MVP explicitly does not solve file replication — if you
also want agents at `.openstation/agents/`, wire it yourself
(symlink, copy, etc.) or wait for the multi-destination spec.

**Q. The distro repo has agents in `openstation/agents/` *and*
`.claude/agents/`. Which does the manifest point at?**
Pick one in `artbook.yaml :: books[].path`. Whichever you name
is the canonical source; the others are ignored by consumers.
The MVP doesn't try to solve internal replication on the distro
side either.

**Q. Where can I see the design spec?**
[[s0029-artbook-mvp-distribution-model]] in this vault. The
parent feature task is [[t0150-artbook-distribution-model]].

---

## 9. Quick-reference cheat sheet

```
# one-time setup
artifacts init
# then edit artifacts.yaml to add: artbook.distro_url: <git-url>

# everyday use
artifacts book list                       # what does this distro ship?
artifacts book show agents                # what's in the agents book?
artifacts book pull agents                # install it
artifacts book pull agents --dry-run      # preview without writing

# scripting
artifacts book list --json | jq '.books[].name'
artifacts book pull agents --json         # JSONL writes + final summary

# troubleshooting
artifacts book list                       # exit 4 → fix artbook.distro_url
                                          # exit 3 → run `artifacts init`
                                          # exit 1 → read stderr; common: bad URL, missing artbook.yaml, version mismatch
```
