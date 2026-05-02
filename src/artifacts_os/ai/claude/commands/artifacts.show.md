---
name: artifacts.show
description: Show full details of a single artifact (frontmatter + body). $ARGUMENTS is a ref — full name, numeric ID, or partial slug — plus optional kind/json/editor flags. Use when the user says "show <ref>", "view artifact", or wants to inspect a specific artifact.
---

# Show Artifact

Display the full contents (frontmatter + body) of a single artifact.

## Input

`$ARGUMENTS` — a ref identifying the artifact, plus optional flags.

Three ref forms are accepted:

| Form | Example | Resolves to |
|---|---|---|
| Full name | `t0042-fix-login-bug` | Exact filename stem match |
| Numeric ID | `t0042` | The artifact carrying that ID |
| Partial slug | `fix-login` | Any artifact whose name contains the slug |

Optional tokens inside `$ARGUMENTS`:

| Token | Effect |
|---|---|
| `kind:<value>` | Disambiguate when a partial slug matches multiple artifacts |
| `json` | Print a JSON object (frontmatter + body) instead of a table |
| `editor` | Open the file in `$EDITOR` instead of printing |

## Procedure

Run `artifacts show` with the ref and any translated flags:

```bash
# Default — frontmatter as a table, body as markdown
artifacts show <ref>

# Disambiguate a partial slug by kind
artifacts show <slug> --kind <KIND>

# JSON output (frontmatter + body)
artifacts show <ref> -j

# Open in $EDITOR
artifacts show <ref> -e
```

**IMPORTANT: Run the command exactly as shown above. Do not modify
the command in any way. Do not add `2>&1`, `2>/dev/null`,
`|| echo`, or any other shell operators.**

| Flag | Effect |
|---|---|
| `--kind <value>` (alias `-k`) | Narrows partial-slug resolution to one registered kind |
| `-j` / `--json` | Prints a JSON object with all frontmatter fields plus the body |
| `-e` / `--editor` | Opens the file in `$EDITOR`; mutually exclusive with `-j` |

Display the CLI output directly. After the table/body, surface the
canonical file path printed by the CLI so the user can open or quote
it without an extra round-trip.

## Worked examples

User asks: "show me `t0042`."

```bash
artifacts show t0042
```

The CLI resolves the numeric ID, prints frontmatter as an aligned
table, the body verbatim, and the file path.

User asks: "show me the artifact about `fix-login`."

```bash
artifacts show fix-login --kind <KIND>
```

`--kind` narrows the search when the partial slug would otherwise be
ambiguous. Use `artifacts kinds` to discover available kind names if
the user did not specify one.

User asks for machine-readable output:

```bash
artifacts show <ref> -j
```

The CLI emits one JSON object combining frontmatter and body — pipe it
into `jq` or another consumer.

## Resolution edge cases

| Situation | Handling |
|---|---|
| Ref matches no artifact | The CLI exits non-zero with a "not found" message. Use `/artifacts.list` to discover existing refs and re-run with a real one. |
| Partial slug matches multiple artifacts | The CLI lists candidates and exits non-zero. Re-run with `--kind <KIND>`, the artifact's numeric ID, or the full filename stem to disambiguate. |
| Ref wrapped in `[[…]]` | Most call sites accept either form — strip the brackets if the CLI rejects the wrapped value. |
| `-e` requested but `$EDITOR` unset | The CLI fails with a clear message. Suggest exporting `EDITOR` (e.g., `export EDITOR=vim`) and retry, or fall back to the default table output. |
| Both `-j` and `-e` passed | Mutually exclusive — pick one based on intent (JSON for piping, editor for inline edits). |

## Cross-references

- `/artifacts.list` — discover refs by kind, status, or other filters before showing one.
- `artifacts kinds` — see what kinds the registry knows about, before passing `--kind` for disambiguation.
