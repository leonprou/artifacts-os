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

## Global flags

These flags sit on the top-level `artifacts` parser and apply to every
subcommand.

| Flag | Purpose |
|------|---------|
| `--version`, `-v` | Print the installed version and exit. |
| `--config <ref>` | Override settings-file discovery for this one invocation. `<ref>` is a **path** (`./custom.yaml`, `/etc/foo.yaml`) used as-is, or a **basename** (`myapp.yaml`) walked up from CWD like the default `artifacts.yaml` marker. Has **no effect on `artifacts init`**. |

```bash
# Drive a vault that uses a custom marker name
artifacts --config myapp.yaml list --kind task
```

Full contract: `docs/settings.md` § "CLI override".

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
artifacts create "<title>" [--kind KIND] [--body TEXT] [--body-file PATH|-] [--fields KEY=VALUE …]
```

- Default kind is `task`.
- For numbered kinds (e.g. `task`, `spec`) the ID is auto-assigned.
- For non-numbered kinds (e.g. `agent`) the title becomes the slug.
- `--fields` accepts multiple `KEY=VALUE` pairs after a single flag.
- **Comma-separated values produce a list** (e.g. `tags=a,b,c`).
- **Wikilink array fields** (`depends_on`, `subtasks`, `artifacts`)
  accept comma-separated refs and are auto-wrapped as `[[…]]`
  (e.g. `depends_on=t0001,t0002` → `["[[t0001]]", "[[t0002]]"]`).
- **Parent backlink:** setting `parent=REF` (via `--parent` or
  `--fields parent=…`) auto-appends the new artifact's wikilink
  to the parent's `subtasks` array. The parent must already
  exist — otherwise the command fails before any write.

```bash
artifacts create "Fix login bug"                                  # → t0043
artifacts create "researcher" --kind agent                        # → researcher
artifacts create "Deploy pipeline" \
  --kind task \
  --fields status=ready assignee=developer depends_on=t0001,t0002 \
  --body "## Steps\n- Step 1\n- Step 2"
artifacts create "Child task" --parent t0043                      # back-links into t0043.subtasks
```

Every `artifacts create` call goes through **two preparation steps**
before the command itself: (1) selecting the kind, (2) drafting the
body from the chosen kind's `ARTIFACT.md`. Both happen at this agent
layer — the CLI itself stays body-agnostic and never reads
`ARTIFACT.md` bodies.

#### Selecting a kind

When the user does not name a kind explicitly, do **not** fall straight
through to the `cli.defaults.create.kind` default (usually `task`).
First consult the registered kinds and pick by the `description:`
signal:

```bash
artifacts kinds -j | jq '.[] | {name, description}'
```

`description:` (≤ 1024 chars, third-person) encodes both the *what*
(what the kind captures) and the *when* (which signals indicate this
kind over alternatives). Read each candidate description and pick the
kind whose *when* clause matches the user's request. Only fall back
to the configured default when nothing matches.

For human-friendly browsing run `artifacts kinds` (table). When
scripting or piping, use `artifacts kinds -j`.

#### Drafting the body from ARTIFACT.md

Every kind ships an `ARTIFACT.md` that pairs the validation contract
(`kind.json`) with an authored body skeleton. The skill's flow is
**read-then-create**: load the skeleton, resolve placeholders, then
pipe the result into `artifacts create` via `--body-file -`.

```bash
# 1. Load the chosen kind's ARTIFACT.md
artifacts kinds <kind>            # full file (frontmatter + body)
# or, for scripting:
artifacts kinds <kind> -j         # {"meta": {...}, "body": "..."}

# 2. Extract the skeleton section (## Skeleton, or ## Variants/<name>)
#    — drop the surrounding ```markdown … ``` fence if present.

# 3. Substitute {{TITLE}} with the user's title. Leave every other
#    {{TOKEN}} placeholder LITERAL — the agent fills those in while
#    drafting after the file is created.

# 4. Pipe the resolved body into the CLI
echo "<RESOLVED-BODY>" | artifacts create "<title>" --kind <kind> --body-file -
```

**Variant-selection precedence** (s0018 § 5.1). When the chosen kind's
`ARTIFACT.md` declares one or more `## Variants/<name>` sub-sections,
pick **exactly one** section to extract. Precedence, highest first:

1. **Explicit user-requested variant.** The user named a variant
   (e.g. "create a `decision` note"). Match it case-insensitively
   against the declared `## Variants/<name>` headings.
2. **`--type` token, only when the `ARTIFACT.md` frontmatter declares
   `variant_field: type`.** A `type:<value>` token in the request
   selects the variant whose name matches `<value>`. If the
   frontmatter does not declare `variant_field: type`, ignore the
   token for variant selection (it is still passed through as a
   normal frontmatter field).
3. **Default `## Skeleton`.** Used when neither 1 nor 2 applies,
   or when the `ARTIFACT.md` declares no variants at all.

Never infer a variant from the title's wording — title inference is
explicitly rejected. If the user names a variant that does not exist,
abort and list the declared variants rather than silently falling back.

**Substitution scope.** `{{TITLE}}` is the **only** placeholder
substituted at create time. Every other `{{TOKEN}}` (e.g.
`{{ONE_PARAGRAPH_SUMMARY}}`, `{{DECISION_RATIONALE}}`) is left
**literal** in the body so the agent fills it in during drafting after
the file lands. Do not invent a substitution table — if a token's
intent is unclear, ask the user.

**Fallback — no ARTIFACT.md or no skeleton.** When the chosen kind has
no `ARTIFACT.md`, or its `ARTIFACT.md` has no `## Skeleton` section
(and no variant applies), skip the body step entirely and run
`artifacts create` with no `--body` / `--body-file`. Surface a
one-line info note to the user:

```
info: kind '<kind>' has no ARTIFACT.md; created with empty body.
```

This matches the `body_loader.py` policy (s0018 § 6): the empty body
is the honest signal that the kind has not authored a skeleton yet —
do not synthesise a generic stub.

#### Worked example — creating a `note`

User asks: "Capture the brainstorm we just had on retry semantics
as a note titled *Retry budget brainstorm*."

```bash
# 1. Confirm the kind from descriptions (the user said "note" — verify
#    description matches: "captures thinking at a point in time").
artifacts kinds -j | jq -r '.[] | select(.name=="note") | .description'

# 2. Load the kind's ARTIFACT.md.
artifacts kinds note

#    The body contains a ## Skeleton section:
#
#        ```markdown
#        # {{TITLE}}
#
#        {{ONE_PARAGRAPH_SUMMARY}}
#
#        ## Origin
#
#        ## References
#        ```

# 3. Substitute {{TITLE}}; leave {{ONE_PARAGRAPH_SUMMARY}} literal.
#    No variant applies (note declares no ## Variants/<name>).

# 4. Pipe the resolved body into create.
cat <<'EOF' | artifacts create "Retry budget brainstorm" \
  --kind note \
  --fields type=brainstorm \
  --body-file -
# Retry budget brainstorm

{{ONE_PARAGRAPH_SUMMARY}}

## Origin

## References
EOF
```

The CLI assigns the next note ID, writes the file, and prints the
canonical stem (e.g. `n0007-retry-budget-brainstorm`). Follow up by
filling in `{{ONE_PARAGRAPH_SUMMARY}}`, the `## Origin` context, and
the `## References` links — those placeholders were intentionally
left literal.

### Update status — `artifacts status`

```bash
artifacts status <ref> <new-status>
```

Changes the `status` frontmatter field; the body is preserved
verbatim. The new status must be in the kind's allowed list, otherwise
the command fails and prints the allowed values. This is the focused,
ergonomic verb for advancing an artifact's lifecycle state — to write
any *other* property, use `artifacts set` (below).

```bash
artifacts status t0042 in-progress
artifacts status t0042 review
artifacts status t0042 done
```

Common task statuses: `backlog`, `ready`, `in-progress`, `review`,
`verified`, `done`, `cancelled`. Run `artifacts status t0042 ?` (any
invalid value) to surface the actual list for a kind.

**Other frontmatter fields:** to change a non-status field (e.g.
`assignee`, `priority`), use `artifacts set <ref> <property> <value>`
(see *Write a property* below). Don't recreate the artifact or edit the
file directly.

### Read a property — `artifacts get`

```bash
artifacts get <ref> [<property>] [-j]
```

Reads one frontmatter property — or, with no property, lists every
frontmatter field as key/value (no body, unlike `show`). Reach for
this instead of `show -j | jq .field` when you only need one value.

- **With `<property>`** — prints the scalar value on one line. `-j`
  returns `{"property": "<name>", "value": <value>}`.
- **Without `<property>`** — prints all frontmatter as a key/value
  table. `-j` returns the full frontmatter object.
- Unknown property exits 2 with
  `Unknown property '<name>' for kind '<kind>' — known: [...]`.

```bash
# Read the status property
artifacts get t0042 status
# → ready

# JSON form — pipe-friendly
artifacts get t0042 status -j
# → {"property": "status", "value": "ready"}

# An arbitrary frontmatter field
artifacts get t0042 assignee
# → alice

# All frontmatter, no body
artifacts get t0042

# Full frontmatter as JSON
artifacts get t0042 -j
```

### Write a property — `artifacts set`

```bash
artifacts set <ref> <property> <value>
```

Writes exactly one frontmatter property; the body is preserved
verbatim. **This is the generic field-update command** — it supersedes
any older guidance that `status` was the only way to mutate an
artifact. Use it for any single-field change.

Every write runs the full validation pipeline:

- **State-machined properties** (e.g. `status`) — the new value must be
  a legal transition from the current one (s0033). An illegal
  transition exits 2:

  ```
  error: Illegal transition for field 'status': 'in-progress' → 'verified' (allowed targets: ['review']) (allowed from any state: ['rejected'])
  ```

- **Free-form properties** (e.g. `assignee`) — written through JSON
  Schema validation only (no transition check).

```bash
# Advance a state-machined property (transition-validated)
artifacts set t0042 status review

# Set a free-form property
artifacts set t0042 assignee alice

# Illegal transition exits 2
artifacts set t0042 status verified
# → error: Illegal transition for field 'status': ...
```

To see which targets are legal before writing, run
`artifacts transitions` (below).

### Inspect transitions — `artifacts transitions`

```bash
artifacts transitions <ref> [<property>] [-j]
```

Shows the state-machine snapshot for one or all state-machined
properties on the artifact's kind — the legal next values before you
call `set`. Columns: `property`, `current`, `allowed_next`,
`wildcard_targets`, `locked?`.

- `allowed_next` — targets reachable from the current value.
- `wildcard_targets` — targets reachable from *any* state.
- `locked` — `yes` when the field is frozen at its initial value.
- Omit `<property>` to list every state-machined property; `-j`
  returns a dict keyed by property name.
- A property with no state machine (e.g. `title`) exits 2 with
  `no state machine declared for field '<name>' in kind '<kind>'`.

```bash
# All state-machined properties on the artifact
artifacts transitions t0042

# Just 'status'
artifacts transitions t0042 status

# JSON for piping
artifacts transitions t0042 status -j
# → {"property": "status", "current": "ready", "allowed_next": ["in-progress"], "wildcard_targets": [], "locked": false}
```

For the full per-property state-machine model — how transition tables,
wildcards, and locks are declared — see `s0033`.

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

### Manage hooks — `artifacts hooks`

Hook bundles live under `artifacts/hooks/<slug>/` (a manifest plus
optional sibling scripts). A bundle must be **promoted** into
`artifacts/hooks/.active/` before the loader will fire it — that
`.active/` symlink is what separates a *defined* hook from a *live*
one. Full model: `docs/hooks.md`.

```bash
artifacts hooks list    [--host HOST] [--active | --inactive] [--source yaml|bundle] [--tail [N]] [-j]
artifacts hooks show    <slug> [-j]
artifacts hooks promote <slug> [--force] [-j]
artifacts hooks demote  <slug> [-j]
```

- **`list`** — every hook (yaml + bundle) as a table; `active` is `yes`
  (symlink resolves), `dangling` (target missing), or `no` (not
  promoted).
- **`show <slug>`** — manifest frontmatter, sibling files, active
  state, and recent `hook.fired` / `hook.failed` events.
- **`promote <slug>`** — create the `.active/<slug>` entry so the hook
  fires; idempotent, `--force` overwrites a divergent entry.
- **`demote <slug>`** — remove the `.active/<slug>` entry (no-op when
  inactive).

```bash
# List hooks (JSON for scripting)
artifacts hooks list -j

# Activate a hook
artifacts hooks promote auto-commit
```

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

1. **CLI only.** Read artifacts via `artifacts show -j` (or
   `artifacts get`), never via the Read tool. Update frontmatter via
   `artifacts set` / `artifacts status`, never by editing markdown
   directly. Create via `artifacts create`, never by writing files.
2. **Resolve before mutating.** When the user gives a partial ref,
   run `artifacts show <ref> -k <kind>` first to confirm the match,
   especially before `status` changes.
3. **Use `-j` whenever piping.** Table output is not stable for
   parsing.
4. **Honor allowed statuses.** Don't invent status values; use
   exactly what the kind defines.
5. **Body is immutable through the CLI.** `set` and `status` update
   frontmatter only; the body is always preserved verbatim. If the
   body needs to change, surface that to the user — there is no CLI
   command for it.
6. **Select kinds by description; draft bodies from `ARTIFACT.md`.**
   For every create: pick the kind by its `description:` field
   (consulted via `artifacts kinds`) before falling back to the
   configured default, then load the chosen kind's `ARTIFACT.md`
   via `artifacts kinds <name>`, extract `## Skeleton` (or the
   matching variant per the precedence above), substitute
   `{{TITLE}}` only, and pipe the resolved body via
   `--body-file -`. Read exactly one `ARTIFACT.md` per create —
   the chosen kind's — and never fall back to direct file reads.
