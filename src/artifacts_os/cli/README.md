# `artifacts` — CLI Reference

## What It Does

`artifacts` is a command-line tool for managing structured notes, tasks,
and agent specs stored as plain markdown files. Each file is an **artifact**:
a markdown document with a YAML frontmatter header that captures metadata
(status, kind, owner, and any custom fields) alongside freeform body text.
The CLI lets you create, browse, filter, inspect, and move artifacts through
their lifecycle — all without leaving the terminal.

---

## Install

```bash
pip install artifacts-os
artifacts --help
```

---

## Getting Started

Navigate to any directory inside your project and run:

```bash
# See all artifacts in the project
artifacts list

# Create your first task
artifacts create "Fix the login bug"
# → t0001-fix-the-login-bug

# Inspect it
artifacts show t0001
```

That's it. No configuration file is needed.

---

## Project Detection

`artifacts` finds your project automatically. Starting from the current
directory, it walks up the directory tree until it finds a directory
containing `artifacts/artifacts.yaml`. You can run the command from
anywhere inside the project — root, a subdirectory, or a nested
worktree — and it will always find the right place.

---

## Referencing Artifacts

Most commands take a `<ref>` argument to identify an artifact. Three forms
are accepted:

| Form | Example | Resolves to |
|------|---------|-------------|
| Full name | `t0042-fix-login-bug` | Exact match |
| Numeric ID | `t0042` | The artifact with that ID |
| Partial slug | `fix-login` | Any artifact whose name contains the slug |

If the partial slug matches more than one artifact, the command exits with
an error and lists the candidates. Add `--kind` to narrow the search:

```bash
artifacts show fix-login --kind task
```

---

## Commands

### `list` — Browse and filter artifacts

```
artifacts list [--kind KIND] [--status STATUS] [--fields FIELDS] [-q | -j]
```

Lists all artifacts as a table. Use filters to narrow the results.

| Flag | Description |
|------|-------------|
| `--kind KIND`, `-k` | Show only artifacts of this kind (e.g. `task`, `agent`) |
| `--status STATUS`, `-s` | Show only artifacts with this status |
| `--fields FIELDS`, `-f` | Choose which columns to display (comma-separated) |
| `-q`, `--quiet` | One artifact name per line — good for scripts |
| `-j`, `--json` | JSON array — good for pipelines |

**Examples:**

```bash
# All tasks
artifacts list --kind task

# Only tasks that are ready to work on
artifacts list --kind task --status ready

# Pick specific columns
artifacts list --fields id,name,status,created

# Quiet list for scripting
artifacts list --kind task -q
```

---

### `show` — Inspect a single artifact

```
artifacts show <ref> [--kind KIND] [-j | -e]
```

Displays the artifact's metadata and body. Use `<ref>` as a full name,
numeric ID, or partial slug.

| Flag | Description |
|------|-------------|
| `--kind KIND`, `-k` | Narrow resolution when the ref is ambiguous |
| `-j`, `--json` | JSON object with all fields plus the body |
| `-e`, `--editor` | Open the file in `$EDITOR` |

**Examples:**

```bash
# By full name
artifacts show t0042-fix-login-bug

# By short ID
artifacts show t0042

# By partial slug
artifacts show fix-login --kind task

# As JSON (pipe-friendly)
artifacts show t0042 -j

# Open in your editor
artifacts show t0042 -e
```

---

### `create` — Add a new artifact

```
artifacts create <title> [--kind KIND] [--body BODY] [--fields KEY=VALUE ...]
```

Creates an artifact file and prints its name. Numbered kinds (like `task`)
get an auto-incremented ID. Non-numbered kinds (like `agent`) use the title
as the filename directly.

| Flag | Description |
|------|-------------|
| `title` | Human-readable title; used to derive the filename slug |
| `--kind KIND`, `-k` | Artifact kind (default: `task`) |
| `--body BODY`, `-b` | Initial body text |
| `--fields KEY=VALUE`, `-f` | Set extra frontmatter fields; repeat for multiple |

**Examples:**

```bash
# Create a task (the default kind)
artifacts create "Fix login bug"
# → t0001-fix-login-bug

# Create an agent artifact
artifacts create "my-researcher" --kind agent
# → my-researcher

# Create with initial status and body
artifacts create "Deploy pipeline" \
  --fields status=ready \
  --body "## Steps\n\n- Step 1\n- Step 2"
```

---

### `status` — Move an artifact through its lifecycle

```
artifacts status <ref> <new-status>
```

Updates the `status` field in an artifact's frontmatter and prints
`<name>: <new-status>` to confirm the change.

Each artifact kind defines its own set of allowed status values (e.g. `backlog`,
`ready`, `in-progress`, `review`, `done` for tasks). If the value you provide
is not in that list, the command fails and prints the allowed values:

```
Error: Invalid status 'wip' for kind 'task'. Allowed: ['backlog', 'ready', 'in-progress', 'review', 'done']
```

**Examples:**

```bash
# Pick up a task
artifacts status t0042 in-progress

# Send it for review
artifacts status t0042 review

# Mark it done
artifacts status t0042 done
```

---

### `verify` — Check an artifact's completion checklist

```
artifacts verify [<ref>] [--kind KIND] [--all] [-j]
```

Scans the artifact body for markdown checklist items (`- [ ]` / `- [x]`)
and reports how many are checked. Exits cleanly when all items are checked;
exits with an error when any remain unchecked.

| Flag | Description |
|------|-------------|
| `ref` | Artifact to check (omit to scan all) |
| `--kind KIND`, `-k` | Filter by kind when scanning all |
| `--all` | Explicitly check every artifact |
| `-j`, `--json` | JSON output |

**Examples:**

```bash
# Check a single task
artifacts verify t0042

# Check all tasks at once
artifacts verify --kind task --all

# JSON output for automation
artifacts verify t0042 -j
```

---

### `init` — Bootstrap a new project

```
artifacts init [DIRECTORY] [--name NAME]
```

Creates a new artifacts-os project in *DIRECTORY* (default: current directory).
Writes `artifacts/artifacts.yaml`, per-kind storage directories, per-kind JSON
schemas under `artifacts/kinds/`, and an `openstation → artifacts` symlink for
external tooling compatibility.

| Flag | Description |
|------|-------------|
| `directory` | Target directory (default: `.`) |
| `--name NAME` | Project name (default: directory name) |

**Example:**

```bash
# Bootstrap a project in the current directory
artifacts init

# Bootstrap a named project in a new directory
artifacts init my-project --name "My Project"
```

---

### `validate` — Check artifact frontmatter correctness

```
artifacts validate [<ref>] [--kind KIND] [--fix | --dry-run] [--all] [-j]
```

Validates frontmatter fields against the kind's schema. Reports errors
(required fields missing, invalid status values) and warnings. Exits 0
when no errors are found; exits 2 when any errors are found.

| Flag | Description |
|------|-------------|
| `ref` | Artifact to validate (omit to validate all) |
| `--kind KIND`, `-k` | Filter by kind |
| `--fix` | Auto-correct fixable issues (e.g. missing `status` → first allowed value) |
| `--dry-run` | Preview fixes without writing |
| `--all` | Explicitly validate every artifact |
| `-j`, `--json` | JSON output — only artifacts with issues |

**Examples:**

```bash
# Validate all artifacts
artifacts validate

# Validate only tasks
artifacts validate --kind task

# Preview auto-fix for a single artifact
artifacts validate t0042 --dry-run

# Apply auto-fix
artifacts validate t0042 --fix
```

---

### `kinds` — List registered artifact kinds

```
artifacts kinds [-q | -j]
```

Lists all artifact kinds registered in the active project, including
any vault-defined kinds loaded from `artifacts/kinds/*.json`.

| Flag | Description |
|------|-------------|
| `-q`, `--quiet` | One kind name per line — good for scripts |
| `-j`, `--json` | JSON array with full kind metadata |

**Examples:**

```bash
# Table of all kinds
artifacts kinds

# Just the names
artifacts kinds -q

# JSON (includes dir, prefix, numbered, statuses)
artifacts kinds -j
```

---

## Output Formats

| Mode | Flag | Best for |
|------|------|----------|
| Table | *(default)* | Human reading in the terminal |
| Quiet | `-q` | Shell scripts that iterate over names |
| JSON | `-j` | Pipelines — pipe to `jq`, `python`, etc. |
| Editor | `-e` | Editing a file in place |

**Quick reference:**

```bash
# Count ready tasks with jq
artifacts list --kind task --status ready -j | jq length

# Loop over agent names in a shell script
for agent in $(artifacts list --kind agent -q); do
  echo "Processing $agent"
done
```
