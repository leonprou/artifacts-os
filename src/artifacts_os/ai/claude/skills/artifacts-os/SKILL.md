---
name: artifacts-os
description: Fetch, search, and update artifacts in an artifacts-os vault using the `artifacts` CLI exclusively (no direct file reads/writes). Use when the user asks to find, list, filter, search, show, inspect, view, create, update, status-change, validate, or verify artifacts (tasks, specs, agents, research notes) — or whenever working in a project that contains an `artifacts.yaml` vault marker.
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

**Tree layout.** Tree layout for tasks is configured in
`artifacts.yaml`'s `default_layouts` (kinds no longer declare
layouts themselves). Override per-invocation with `--layout table`.
`-q` / `-j` are unaffected. Full design: `s0022-tree-layout`.

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

### Create — `artifacts create`

```bash
artifacts create "<title>" [--kind KIND] [--body TEXT] [--fields KEY=VALUE …]
```

- Default kind is `task`.
- For numbered kinds (e.g. `task`, `spec`) the ID is auto-assigned.
- For non-numbered kinds (e.g. `agent`) the title becomes the slug.
- `--fields` accepts multiple `KEY=VALUE` pairs after a single flag.

```bash
artifacts create "Fix login bug"                                  # → t0043
artifacts create "researcher" --kind agent                        # → researcher
artifacts create "Deploy pipeline" \
  --kind task \
  --fields status=ready assignee=developer \
  --body "## Steps\n- Step 1\n- Step 2"
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
