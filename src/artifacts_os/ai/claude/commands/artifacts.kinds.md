---
name: artifacts.kinds
description: List artifact kinds registered in the active vault — built-ins plus any vault-defined kinds from artifacts/kinds/*.json. Supports quiet and JSON output via $ARGUMENTS. Use when the user asks "what kinds are registered", "show kinds", or wants to inventory the registry.
---

# List Registered Kinds

Display every artifact kind known to the active vault — built-ins plus
anything declared in `artifacts/kinds/*.json`.

## Input

`$ARGUMENTS` — optional output flags:

| Token | Effect |
|---|---|
| `quiet` | One kind name per line — script-friendly |
| `json` | JSON array with full per-kind metadata (`prefix`, `numbered`, `dir`, `statuses`, columns, schema) |

If no arguments are provided, the command prints an aligned table
summarising every registered kind.

## Procedure

Run `artifacts kinds`:

```bash
# Aligned table — readable summary
artifacts kinds

# One name per line
artifacts kinds -q

# Full per-kind metadata as JSON
artifacts kinds -j
```

**IMPORTANT: Run the command exactly as shown above. Do not modify
the command in any way. Do not add `2>&1`, `2>/dev/null`,
`|| echo`, or any other shell operators.**

| Mode | Flag | Best for |
|---|---|---|
| Table | *(default)* | Human reading |
| Quiet | `-q` / `--quiet` | Iterating in shell scripts |
| JSON | `-j` / `--json` | Pipelines (`jq`, scripted introspection) |

Display the CLI output directly.

## Worked examples

User asks: "what kinds can I create here?"

```bash
artifacts kinds
```

The CLI prints a table whose rows are the registered kinds and whose
columns include the per-kind storage directory, prefix, and allowed
status values. To enumerate artifacts of a specific kind, follow up
with `/artifacts.list --kind <KIND>` (or `artifacts list --kind <K>`)
using a kind name from the table.

For scripted introspection — e.g., listing every kind that uses
auto-incremented IDs:

```bash
artifacts kinds -j | jq -r '.[] | select(.numbered) | .name'
```

## Edge cases

| Situation | Handling |
|---|---|
| No vault-defined kinds | The table shows only built-ins. Pass that result through — there is nothing to fix. |
| `artifacts/kinds/*.json` invalid | The CLI surfaces a validation error naming the bad schema file. Report it to the user — this command does not auto-repair kind definitions. |
| `-q` and `-j` both passed | Mutually exclusive — pick one based on intent. |

## Adding a new kind

This command is read-only — it lists what is already registered. To
register a new kind, use `/artifacts.kinds.create` (once that command
ships) which writes a JSON-Schema file under
`artifacts/kinds/<name>.json` and reloads the registry.

## Cross-references

- `/artifacts.list --kind <KIND>` — list artifacts of a single registered kind.
- `/artifacts.show <ref>` — inspect one artifact of any kind.
