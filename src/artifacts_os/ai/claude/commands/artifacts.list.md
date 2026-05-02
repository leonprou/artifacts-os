---
name: artifacts.list
description: List artifacts in the active vault. Supports filters via $ARGUMENTS (e.g., kind:<value>, status:<value>) and output modes (quiet, json). Use when the user asks "what artifacts exist", "show artifacts of kind X", or wants to enumerate the vault.
---

# List Artifacts

Display artifacts from the active vault as a readable table.

## Input

`$ARGUMENTS` — optional space-separated filters and output flags in
`key:value` form. All filters are optional; with no arguments the
command lists every artifact using the default columns.

| Token | Effect |
|---|---|
| `kind:<value>` | Restrict to one registered kind |
| `status:<value>` | Restrict to one status (allowed values come from the kind's schema) |
| `fields:<a,b,c>` | Choose which columns to render (comma-separated keys) |
| `quiet` | One artifact name per line — script-friendly |
| `json` | JSON array — pipeline-friendly |

If the user has not specified a kind, run `artifacts kinds` first to
discover what is registered before guessing.

## Procedure

Run `artifacts list` with the flags translated from `$ARGUMENTS`:

```bash
# No filters — full table
artifacts list

# Restrict to one kind
artifacts list --kind <KIND>

# Restrict to one status
artifacts list --status <STATUS>

# Combine filters
artifacts list --kind <KIND> --status <STATUS>

# Pick specific columns
artifacts list --fields id,name,status,created

# Script-friendly output (one name per line)
artifacts list --kind <KIND> -q

# JSON output (array of objects)
artifacts list --kind <KIND> -j
```

**IMPORTANT: Run the command exactly as shown above. Do not modify
the command in any way. Do not add `2>&1`, `2>/dev/null`,
`|| echo`, or any other shell operators.**

| Filter / mode | CLI flag |
|---|---|
| `kind:<value>` | `--kind <value>` (alias `-k`) |
| `status:<value>` | `--status <value>` (alias `-s`) |
| `fields:<a,b,c>` | `--fields <a,b,c>` (alias `-f`) |
| `quiet` | `-q` / `--quiet` |
| `json` | `-j` / `--json` |

Display the CLI output directly — it produces an aligned table sorted
by ID. After the table, surface a one-line summary with the row count
so the user can scan results quickly.

## Worked example

User asks: "show me everything of kind `<KIND>`."

```bash
artifacts list --kind <KIND>
```

The CLI prints a row per matching artifact. Hand the output to the user
verbatim. To inspect a single row, follow up with
`/artifacts.show <ref>` using the name or ID from the table.

For a scripted count via `jq`:

```bash
artifacts list --kind <KIND> -j | jq length
```

## Edge cases

| Situation | Handling |
|---|---|
| Empty vault | The CLI prints an empty table or "No artifacts found." Surface that result as-is — do not retry. |
| Unknown kind | The CLI exits non-zero with a message naming the rejected kind. Run `artifacts kinds` to enumerate registered kinds and re-run with a valid one. |
| Unknown status | The CLI rejects the value if it is not in the kind's schema. Run `artifacts kinds -j` and inspect the kind's `statuses` array (or omit `--status` to see every artifact). |
| Ambiguous `fields:` keys | `--fields` only accepts column keys present in the kind's schema. Run `/artifacts.show <ref>` on one artifact to see available frontmatter keys, then re-run with valid names. |
| `-q` and `-j` both passed | Mutually exclusive — pick one. Default to `-j` if the user wants structured output. |

## Cross-references

- `/artifacts.show <ref>` — inspect a single artifact returned by this listing.
- `artifacts kinds` — discover what kinds are registered before passing `--kind`.
