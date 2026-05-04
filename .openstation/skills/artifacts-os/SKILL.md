---
name: artifacts-os
description: Fetch, search, and update artifacts in an artifacts-os vault using the `artifacts` CLI exclusively (no direct file reads/writes). Use when the user asks to find, list, filter, search, show, inspect, view, create, update, status-change, validate, or verify artifacts (tasks, specs, agents, research notes) — or whenever working in a project that contains an `artifacts/artifacts.yaml` vault marker.
---

# artifacts-os

Use the `artifacts` command-line tool for every read and write to the
artifacts vault. Never read or edit artifact markdown files directly —
the CLI handles ID resolution, frontmatter parsing, validation,
atomic writes, and output formatting.

## Reference Resolution

Most commands take a `<ref>`. Three forms are accepted:

| Form          | Example               | Resolves to                     |
|---------------|-----------------------|---------------------------------|
| Full name     | `t0042-fix-login-bug` | Exact match                     |
| Numeric ID    | `t0042`               | The artifact with that ID       |
| Partial slug  | `fix-login`           | Any artifact whose name matches |

If a partial slug matches more than one artifact, the command fails
and lists candidates. Disambiguate with `--kind`:

```bash
artifacts show fix-login --kind task
```

## Commands

### Search / list — `artifacts list`

```bash
artifacts list [--kind KIND] [--status STATUS] [--fields F1,F2,…] [-q | -j]
```

| Flag             | Purpose                                       |
|------------------|-----------------------------------------------|
| `--kind`, `-k`   | Filter by kind (`task`, `spec`, `agent`, …)   |
| `--status`, `-s` | Filter by status                              |
| `--fields`, `-f` | Comma-separated columns (e.g. `id,name,status`) |
| `-q`             | One name per line — for shell loops           |
| `-j`             | JSON array — for `jq`/scripting               |

Default output is a Rich table. **Always use `-j` or `-q` when piping
or post-processing**; the table format is for humans.

```bash
# All ready tasks
artifacts list --kind task --status ready

# Pick specific columns
artifacts list --kind task --fields id,name,status,assignee

# JSON for jq
artifacts list --kind task -j | jq '.[] | select(.status=="ready") | .id'

# Names for a shell loop
for t in $(artifacts list --kind task --status ready -q); do echo "$t"; done
```

### Fetch one — `artifacts show`

```bash
artifacts show <ref> [--kind KIND] [-j | -e]
```

`-j` returns a JSON object including the body — use it whenever you
need to read the body programmatically. Without `-j` the body is
rendered for human reading.

```bash
artifacts show t0042              # human-readable
artifacts show t0042 -j           # JSON with body
artifacts show fix-login -k task  # by partial slug, narrowed by kind
```

Do **not** open the file with the Read tool to inspect an artifact —
use `artifacts show -j` so frontmatter and body come back parsed.

### Discover kinds — `artifacts kinds`

Before creating an artifact, run `artifacts kinds` to see every
registered kind with its `description` — the L1 selection signal,
encoding both *what* the kind captures and *when* to choose it.
Pick the kind whose description matches your intent.

Then run `artifacts kinds <name>` to read that kind's full
`ARTIFACT.md`: the `## What is a <kind>?` section defines the
kind, and `## How to draft a <kind>` lists required sections,
writing disciplines, and worked-example references. Always read
this before drafting the new artifact's body. Flags: `-j` (JSON
with both `meta` and `body`), `--meta` (prepend metadata above
the body), `-e` (open `ARTIFACT.md` in `$EDITOR`).

### Create — `artifacts create`

```bash
artifacts create "<title>" [--kind KIND]
    [--body TEXT | --body-file PATH]
    [--name SLUG] [--dry-run | -n]
    [--assignee USER] [--owner USER]
    [--parent REF] [--depends-on REF …]
    [--type TYPE]
    [--fields KEY=VALUE …]
```

| Flag                     | Purpose                                                          |
|--------------------------|------------------------------------------------------------------|
| `--kind`, `-k`           | Artifact kind (default: `task`)                                  |
| `--body`, `-b`           | Inline body text                                                 |
| `--body-file PATH`       | Read body from *PATH*; use `'-'` to read from stdin             |
| `--name SLUG`            | Override the auto-derived slug (controls `{id}-{slug}.md`)      |
| `--dry-run`, `-n`        | Print resolved frontmatter + body without writing any file       |
| `--assignee USER`        | Set `assignee` frontmatter field                                 |
| `--owner USER`           | Set `owner` frontmatter field                                    |
| `--parent REF`           | Set `parent` (bare refs like `t0042` are auto-wrapped as `[[t0042]]`) |
| `--depends-on REF`       | Add a dependency; repeat for multiple (auto-wrapped as `[[…]]`) |
| `--type TYPE`            | Set `type` frontmatter field                                     |
| `--fields KEY=VALUE …`   | Extra frontmatter; convenience flags override same-key entries  |

**Kind-aware help** — `--help` is schema-driven. Use `--kind` before
`--help` to see the exact flags for a kind:

```bash
artifacts create --kind task --help   # task flags (e.g. --priority, --status)
artifacts create --kind note --help   # note flags only
```

Convenience flags not declared in the kind's `x-columns` are hidden but
remain accessible via `--fields`. Schema properties without a convenience
flag get their own dedicated flag (e.g. `--priority` for task).

**Wikilink auto-wrap** — `--parent` and `--depends-on` accept bare refs
(`t0042`) or the full `[[t0042]]` form; both are stored correctly.
The same wrapping applies to `parent` and `depends_on` inside `--fields`.

**Comma-list values** — `--fields tags=a,b,c` stores the value as a YAML
list `[a, b, c]`. Wikilink wrapping is applied per-element when the field
is `parent` or `depends_on`.

```bash
# Minimal — numbered kind, auto-assigned ID
artifacts create "Fix login bug"                          # → t0043

# Non-numbered kind — title becomes the slug
artifacts create "researcher" --kind agent               # → researcher.md

# Convenience flags
artifacts create "Deploy pipeline" \
  --kind task \
  --assignee developer \
  --owner user \
  --parent t0010 \
  --depends-on t0001 --depends-on t0002 \
  --type feature

# Body from file
artifacts create "Spec draft" --kind spec --body-file spec-draft.md

# Body from stdin
echo "## Notes" | artifacts create "Scratch note" --body-file -

# Preview without writing (dry run)
artifacts create "Try me" --assignee alice --dry-run

# Override slug
artifacts create "Fix very long title" --name fix-title  # stem: t0044-fix-title

# Comma-list via --fields
artifacts create "Blocked task" --fields depends_on=t0001,t0002
```

### Update status — `artifacts status`

```bash
artifacts status <ref> <new-status>
```

This is the **only CLI command that updates an existing artifact**.
It changes the `status` frontmatter field; the body is preserved
verbatim. The new status must be in the kind's allowed list, otherwise
the command fails and prints the allowed values.

```bash
artifacts status t0042 in-progress
artifacts status t0042 review
artifacts status t0042 done
```

Common task statuses: `backlog`, `ready`, `in-progress`, `review`,
`verified`, `done`, `cancelled`. Run `artifacts status t0042 ?` (any
invalid value) to surface the actual list for a kind.

**Updating non-status fields:** the CLI does not currently expose a
generic field-update command. If the user asks to change a non-status
frontmatter field (e.g. `assignee`, `priority`), say so and ask whether
to (a) wait for that command, (b) recreate the artifact, or (c)
proceed with a direct file edit as a one-off. Do not silently fall
back to direct edits.

### Validate — `artifacts validate`

```bash
artifacts validate [<ref>] [--kind KIND] [--fix | --dry-run] [--all] [-j]
```

Checks frontmatter against the kind's schema. `--fix` applies
auto-correctable changes; `--dry-run` previews them.

```bash
artifacts validate                        # all artifacts
artifacts validate t0042                  # one artifact
artifacts validate --kind task --dry-run  # preview fixes
artifacts validate --all --fix            # apply fixes
```

### Verify checklist — `artifacts verify`

```bash
artifacts verify [<ref>] [--kind KIND] [--all] [-j]
```

Counts `- [ ]` / `- [x]` items in the body. Exits non-zero if any are
unchecked. Use this to confirm a task's completion checklist is
satisfied before `status … done`.

## Output Mode Selection

| Mode    | Flag        | Use when                                    |
|---------|-------------|---------------------------------------------|
| Table   | (default)   | Reporting back to the user                  |
| Quiet   | `-q`        | Iterating in a shell loop                   |
| JSON    | `-j`        | Parsing in a script or piping to `jq`       |
| Editor  | `-e` (show) | User explicitly wants to edit interactively |

When extracting fields for further processing, prefer `-j | jq …`
over parsing the table.

## Common Patterns

```bash
# Count ready tasks
artifacts list --kind task --status ready -j | jq length

# Find every task assigned to "developer"
artifacts list --kind task -j | jq '.[] | select(.assignee=="developer") | .id'

# Bulk transition: move all "review" tasks to "verified"
for id in $(artifacts list --kind task --status review -j | jq -r '.[].id'); do
  artifacts status "$id" verified
done

# Show body only (drop frontmatter)
artifacts show t0042 -j | jq -r .body
```

## Rules

1. **CLI only.** Read artifacts via `artifacts show -j`, never via
   the Read tool. Update status via `artifacts status`, never by
   editing markdown directly. Create via `artifacts create`, never
   by writing files.
2. **Resolve before mutating.** When the user gives a partial ref,
   run `artifacts show <ref> -k <kind>` first to confirm the match,
   especially before `status` changes.
3. **Use `-j` whenever piping.** Table output is not stable for
   parsing.
4. **Honor allowed statuses.** Don't invent status values; use
   exactly what the kind defines.
5. **Body is immutable through the CLI.** `status` only updates
   frontmatter. If the body needs to change, surface that to the
   user — there is no CLI command for it today.
