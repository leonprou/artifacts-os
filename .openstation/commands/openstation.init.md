---
name: openstation.init
description: Initialize or update an Open Station project. Runs CLI init for structural setup, then uses LLM understanding to merge upstream template changes into customized agent files without losing local customizations.
---

# Init / Update Open Station

Run structural init via the CLI, then intelligently merge
upstream template additions into locally customized agent files.

## Input

`$ARGUMENTS` — optional flags passed through to `openstation init`
(e.g., `--agents researcher,author`, `--no-agents`, `--dry-run`).

## Procedure

### Phase 1 — CLI Init (structural setup)

1. Run `openstation init $ARGUMENTS` and capture its output.
   This handles directories, symlinks, docs, skills, commands,
   and new agent files. It **skips** existing agent files to
   avoid clobbering customizations.

2. Parse the CLI output. Collect:
   - **Created files** — lines with `✓` (newly installed)
   - **Skipped files** — lines with `⊘` (existing, not
     overwritten)

3. Report the CLI results to the user.

   If `--no-agents` was passed or no agent files were skipped,
   stop here — Phase 2 is not needed.

### Phase 2 — LLM Template Merge (agent files only)

For each **skipped** agent file from Phase 1:

4. Determine the install cache directory. The CLI uses
   `~/.local/share/openstation/` by default (or `$OPENSTATION_DIR`
   if set). The upstream template lives at:
   ```
   <cache>/.openstation/templates/agents/<name>.md
   ```

5. Read both files:
   - **Upstream template**: the file from the install cache
   - **Local agent file**: `.openstation/artifacts/agents/<name>.md`

6. Compare the two files and identify **additions only** —
   content present in the upstream template but missing from
   the local file. Look for:

   - **New frontmatter fields** — fields in the upstream YAML
     that do not exist in the local file (e.g., a new `skills`
     entry, a new `allowed-tools` pattern)
   - **Startup instruction** — the `**On startup**...` line.
     If upstream has it and local does not, add it at the top
     of the body (before the H1 title)
   - **New body sections** — H1/H2/H3 sections present in the
     upstream but absent from the local file
   - **New tool entries** — items in the upstream `allowed-tools`
     or `tools` lists that are missing from the local lists

7. Apply the merge rules:

   | Element | Merge rule |
   |---------|-----------|
   | Frontmatter field (new) | Add the field with the upstream value |
   | Frontmatter field (exists locally) | **Keep local value** — never overwrite |
   | `allowed-tools` list items | Append missing upstream entries after local entries |
   | `tools` field entries | Append missing upstream entries |
   | `skills` list items | Append missing upstream entries |
   | Startup instruction line | Add before H1 if missing |
   | Body section (new) | Insert at the position matching the upstream template order |
   | Body section (exists locally) | **Keep local content** — never overwrite |
   | Local-only content | **Always preserve** — never remove anything |

   **Cardinal rule**: never remove or overwrite local
   customizations. This is additive-only merging.

8. Before writing, show the user a diff-style summary of
   proposed changes for each file:

   ```
   ## <agent-name>.md
   - Add frontmatter field: `skills: [openstation-execute]`
   - Add allowed-tools entry: `Bash(openstation *)`
   - Add startup instruction line
   - No changes to existing sections
   ```

   Ask: **"Apply these merges? (yes/no/select)"**

   - **yes** — apply all proposed merges
   - **no** — skip all merges
   - **select** — let the user pick which files to merge

9. Apply approved merges using the Edit tool (minimal diffs,
   not full rewrites). For each merged file, report:
   ```
   ✓ <name>.md — merged (<N> additions)
   ```

10. After all files are processed, show a final summary:

    ```
    ## Init Summary

    **CLI phase**: <N> created, <M> updated, <K> skipped
    **Merge phase**: <X> files merged, <Y> already up to date, <Z> skipped by user

    Files merged:
    - researcher.md — 3 additions (skills, allowed-tools, startup line)
    - author.md — already up to date

    No local customizations were removed.
    ```

## Edge Cases

- **Template adaptation**: the CLI applies `_adapt_template()`
  which replaces "the project" with the project name. When
  comparing upstream vs local, account for this substitution —
  do not flag adapted text as "missing" from the local file.
- **Identical files**: if upstream and local are identical after
  adaptation, report "already up to date" and skip.
- **Install cache missing**: if `~/.local/share/openstation/`
  does not exist, report an error and stop. The user needs to
  run the installer first.
- **No skipped agents**: if no agent files were skipped (all
  were newly created or `--no-agents` was used), skip Phase 2
  entirely and report success from Phase 1.
