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
containing `artifacts.yaml`. You can run the command from
anywhere inside the project — root, a subdirectory, or a nested
worktree — and it will always find the right place.

---

## Global Flags

These flags are accepted by the top-level `artifacts` parser and apply to
every subcommand. See [docs/settings.md](../../../docs/settings.md) for full
details on settings and the `--config` override.

| Flag | Description |
|------|-------------|
| `--version`, `-v` | Print the installed version and exit. |
| `--config <ref>` | Override settings-file discovery for this invocation. `<ref>` is a path (`./custom.yaml`, `/etc/foo.yaml`) or a basename (`myapp.yaml`) walked up from CWD. Has no effect on `artifacts init`. |

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
artifacts list [REF ...] [--kind KIND] [--status STATUS] [--filter K=V]...
               [--view NAME] [--fields FIELDS] [--layout NAME]
               [--prune {strict|ancestors|subtree}] [-q | -j]
```

Lists all artifacts as a table. Use filters to narrow the results.

| Argument / Flag | Description |
|-----------------|-------------|
| `REF ...` | Optional ref-set: restrict output to these artifacts only (intersection with all other filters) |
| `--kind KIND`, `-k` | Show only artifacts of this kind (e.g. `task`, `agent`) |
| `--status STATUS`, `-s` | Show only artifacts with this status |
| `--filter K=V` | Frontmatter-equality filter (repeatable; last value per key wins) |
| `--fields FIELDS`, `-f` | Choose which columns to display (comma-separated) |
| `--view NAME`, `-V` | Apply a named view from `artifacts.yaml` (filters, columns, sort) |
| `--layout NAME` | Presentation layout (`table`, `tree`); falls through to `default_layouts` in `artifacts.yaml` when omitted |
| `--prune NAME` | Pruning mode for tree layouts (`strict`, `ancestors`, `subtree`); ignored on non-tree layouts |
| `-q`, `--quiet` | One artifact name per line — good for scripts |
| `-j`, `--json` | JSON array — good for pipelines |

**Examples:**

```bash
# All tasks
artifacts list --kind task

# Only tasks that are ready to work on
artifacts list --kind task --status ready

# Filter by any frontmatter key
artifacts list --filter assignee=alice
artifacts list --kind task --filter assignee=alice --filter type=feature

# Pick specific columns
artifacts list --fields id,name,status,created

# Apply a named view (uses its filters, columns, and sort)
artifacts list --view active

# Named view with explicit flag override (--status wins, other view filters kept)
artifacts list --view active --status done

# Quiet list for scripting
artifacts list --kind task -q
```

#### Ref-set filter (positional arguments)

Pass one or more artifact references as positional arguments to restrict output
to exactly those artifacts.  All other filters still apply — the ref-set is an
additional predicate that intersects with `--kind`, `--status`, `--filter`,
`--children`, `--parent`, and `--view`.

**Accepted ref forms** (same as `artifacts show`):

| Form | Example | Resolves to |
|------|---------|-------------|
| Numeric ID | `t1`, `t0042` | Artifact with that ID |
| Full stem | `t0042-fix-login-bug` | Exact stem match |
| Partial slug | `fix-login` | Any artifact containing the slug (must be unambiguous) |
| Wikilink | `[[t0042]]`, `[[t0042-fix-login-bug]]` | Inner ref resolved as above |

**Behaviour:**

- **Intersection semantics** — `artifacts list t1 t4 --status ready` returns
  refs in `{t1, t4}` whose status is `ready`.
- **`--kind` scopes partial-slug resolution** — when `--kind task` is given,
  a partial slug resolves only within the task directory, matching
  `artifacts show --kind task`.
- **Fail-fast on unresolvable refs** — if any ref cannot be resolved, the
  command exits non-zero, emits one `error: …` line per bad ref on stderr,
  and produces no output (even for refs that *did* resolve).
- **Output flags unchanged** — `-j`, `-q`, `--fields`, `--meta`, `--view`
  behave identically; only the row set narrows.

```bash
# Inspect two known tasks in one call
artifacts list t1 t4

# Same two tasks, specific columns
artifacts list t0001 t0042 --fields id,name,status,assignee

# JSON for downstream tooling
artifacts list t1 t4 -j

# Intersection with --status
artifacts list t1 t4 --status ready

# Partial-slug scoped to tasks
artifacts list migrate --kind task

# Wikilink form (handy when pasting from frontmatter)
artifacts list "[[t0001]]" "[[t0042]]"
```

#### Schema-derived filter flags

When `--kind <K>` is supplied, `artifacts list` automatically generates a
typed flag for every property declared in that kind's JSON schema
(`artifacts/kinds/<K>/kind.json`).  Properties with an `enum` array get
`choices=` enforcement at parse time — a typo is an immediate error rather
than a silent empty result.

```bash
# See all filterable axes for a kind
artifacts list --kind task --help
# → lists --status {backlog,ready,...}, --priority {low,...}, --assignee TEXT, etc.

# Enum-validated filter — typo caught before core runs
artifacts list --kind task --status bogus
# → error: argument --status: invalid choice: 'bogus' (choose from ...)

# Combine multiple generated flags
artifacts list --kind task --type feature --assignee alice
```

**Without `--kind`** (cross-kind mode), the same flags are generated from
the union of all vault schemas, but without `choices=` because different
kinds may define different enums for the same property name.  Enum
validation is deferred to core (silent-no-match for unknown values).

```bash
# Cross-kind: --status available but without per-kind choices validation
artifacts list --status review
```

**Multi-value (CSV) input** — every enum-typed flag accepts a
comma-separated list to match the union of those values
(per [`s0023-multi-value-filters`](../../../artifacts/specs/s0023-multi-value-filters.md)).
Single values still work unchanged.

```bash
# Single value
artifacts list --kind task --status ready

# Multi-value — "all in-flight work" in one call
artifacts list --kind task --status ready,in-progress,review

# Cross-kind, multi-value
artifacts list --status ready,review
```

CSV validation:

- Empty elements (`a,,b`, `a,`, `,a`) exit `2` with
  `argument --status: empty value in CSV`.
- In per-kind mode each element is validated against the enum;
  a bogus element exits `2` with
  `argument --status: invalid value '<elem>' (choose from: …)`.
- Cross-kind mode skips per-element enum validation (enums
  diverge by kind); bogus values silent-no-match in core.

**Flag generation rules:**

- One flag per schema `properties` entry; `--` + lowercase hyphenated name.
- `enum` → CSV-aware `type=` callable with per-element enum
  validation in per-kind mode (no `choices=`, since argparse
  `choices=` runs against the raw string and would always
  reject CSV input). `type: string` → free-form `TEXT`;
  `type: integer` → argparse `int`; `type: boolean` →
  `true|false|1|0|yes|no`.
- `type: array` properties are skipped (use `--filter` for list-typed fields).
- Flags that would collide with static flags (`--kind`, `--filter`,
  `--view`, `--fields`, `--layout`, `--meta`, `--quiet`, `--json`,
  `--children`, `--parent`) are silently skipped; those fields
  remain reachable via `--filter k=v`.
- `--status` is the only flag that is **augmented** in per-kind mode
  (keeping its `-s` short form) rather than being skipped.

**Precedence — per-key, last wins:**

| Layer | Example |
|-------|---------|
| View config `filters` (lowest) | `view.filters.assignee = developer` |
| `--kind` / `--status` static flags | `--status ready` |
| Schema-derived generated flags | `--type feature`, `--assignee alice` |
| `--filter k=v` tokens (highest) | `--filter type=spec` overrides `--type feature` |

The `--filter k=v` escape hatch always wins and is the safe fallback for
any field not covered by generated flags.

#### Views

Named views let you pre-configure filters, columns, and sort order in
`artifacts.yaml` and invoke them with a single flag.

**Defining views:**

```yaml
views:
  active:
    columns: id,name,status,assignee
    filters:
      status: ready
    sort: name

  my-tasks:
    columns: id,name,status
    filters:
      status: in-progress
      assignee: alice
    sort: -created
```

**Binding a view to a kind** — `default_views` automatically activates
a view when `--kind` matches, without requiring `--view`:

```yaml
default_views:
  task: active   # `artifacts list --kind task` applies the "active" view
```

**Precedence rules:**

| Setting | Precedence |
|---------|-----------|
| `--view NAME` (explicit) | Beats `default_views` binding |
| `default_views[kind]` | Applied when `--kind` matches and no `--view` given |
| `--status`, `--kind` (explicit flags) | Win over the view's own `filters` for those keys |
| `--fields` | Wins over `view.columns` |

**Filter merging** is per-key: `--status done --view active` uses
`status=done` from the flag but keeps all other `view.filters` entries.

**JSON / quiet contract** — `-j` and `-q` ignore `view.columns` but
still apply `view.filters` and `view.sort`, so machine consumers see
view-filtered, view-sorted data.

**Error handling:**

| Condition | Exit |
|-----------|------|
| `--view foo` and `foo` not found | `2` |
| `--view foo` and no `views:` section | `2` |
| `default_views.k = "v"` and `v` not found | `2` |

To see what views are defined in the active vault, run `artifacts views`.

#### Layouts — `--layout`

`--layout NAME` picks the presentation layout for the result.
The shipped layouts are `table` (flat, the historical default)
and `tree` (parent-child rendering, with each row indented under
its parent and a `└─` prefix on the first column). Layout
configuration lives **only** in `artifacts.yaml` — kinds do not
declare layouts.

```bash
# Default — falls through to default_layouts in artifacts.yaml
# (this vault sets default_layouts.task = { layout: tree, parent_field: parent })
artifacts list --kind task

# Opt out for one call
artifacts list --kind task --layout table

# Force tree on a kind without a configured parent_field — exits 2
artifacts list --kind spec --layout tree
# → error: layout 'tree' requires parent_field; declare it in
#   artifacts.yaml under default_layouts[spec] or a view config
```

`-q` and `-j` short-circuit before layout selection — they
always emit the flat, sort-applied list. Combining `--layout`
with `-q` / `-j` is silently ignored.

**Resolution chain — explicit > view > settings > implicit.**
Four rungs; first rung that resolves wins:

| Rung | Source | Set by |
|------|--------|--------|
| 1 (highest) | `--layout NAME` | the user, per call |
| 2 | `view.layout` | the active view in `artifacts.yaml` |
| 3 | `default_layouts[<kind>]` | the vault's `default_layouts:` map in `artifacts.yaml` |
| 4 (implicit) | `"table"` | nothing declared anywhere |

**Parent-field sibling chain.** When the resolved layout is
`tree`, the renderer needs a `parent_field`. It is resolved
through a parallel chain consulting the same slots:

| Rung | Source |
|------|--------|
| 1 (highest) | `view.parent_field` |
| 2 | `default_layouts[<kind>].parent_field` |
| 3 (implicit) | none — exits 2 with `layout 'tree' requires parent_field` |

There is no `--parent-field` flag in v1; ad-hoc tree on a kind
without a configured `parent_field` requires a one-line
`artifacts.yaml` edit.

**Worked example — default tree from `artifacts.yaml`.** The
artifacts-os vault declares:

```yaml
# artifacts.yaml
default_layouts:
  task:
    layout: tree
    parent_field: parent
```

Then:

```bash
# rung 3 — vault's default_layouts entry resolves layout=tree
artifacts list --kind task
# → tasks render as a tree

# rung 1 — explicit flag beats everything
artifacts list --kind task --layout table
# → tasks render flat

# rung 3 — flip the same map to opt out durably
# artifacts.yaml:
#   default_layouts:
#     task: table          # string-form shorthand
artifacts list --kind task
# → tasks render flat without --layout
```

Unknown layout names exit `2` with `error: unknown layout
'<name>'`. The full algorithm (sibling order, cycle handling,
orphan annotations) lives in
[`s0022-tree-layout`](../../../artifacts/specs/s0022-tree-layout.md)
§§ 6, 8.

#### Prune modes — `--prune`

For tree layouts, `--prune NAME` controls how the tree renders
around a filtered slice. Three modes are defined:

| Mode | Rendered set | Filter honesty |
|------|--------------|----------------|
| `strict` *(implicit default)* | only matched rows; orphan parents promote to root with `↑[parent: …]` | strict — every row matches |
| `ancestors` | matched rows + each match's parent chain up to root, dimmed with `· (context)` | preserved via dim/marked context rows |
| `subtree` | matched rows + each match's full descendant set, regardless of filter | relaxed — user opts into subtree expansion |

```bash
# Default = strict — the orphan annotation tells you a parent is hidden
artifacts list --kind task --status verified
# t0124  ↑[parent: t0114]   verified

# ancestors — pull in the parent chain as context rows
artifacts list --kind task --status verified --prune ancestors
# t0114  · (context)        in-progress
#   └─ t0124                verified

# subtree — full descendant view of every active feature
artifacts list --kind task --view active --prune subtree
```

`--prune` is silently ignored when the resolved layout is not
`tree` (no hierarchy to prune). `-q` and `-j` short-circuit
before pruning runs — their output is byte-for-byte identical
regardless of `--prune`. `--children` and `--parent`
neutralise prune (the user has already shaped an explicit
slice).

**Resolution chain — explicit > view > kind default > implicit.**

| Rung | Source |
|------|--------|
| 1 (highest) | `--prune NAME` |
| 2 | `view.prune` (named view in `artifacts.yaml`) |
| 3 | `default_layouts[<kind>].prune` |
| 4 (implicit) | `"strict"` |

Unknown prune names exit `2` (argparse `choices` enforcement).
The full design lives in
[`s0024-tree-prune-modes`](../../../artifacts/specs/s0024-tree-prune-modes-strict-ancestors.md).

---

### `show` — Inspect a single artifact

```
artifacts show <ref> [--kind KIND] [-j | -e]
```

Displays the artifact's metadata and body. Use `<ref>` as a full name,
numeric ID, or partial slug.

On an interactive TTY, `show` opens the file in `$EDITOR` by default (built-in
default). Use `-j` to get JSON output, or set `cli.defaults.show.editor: false`
in `artifacts.yaml` to restore plain-text rendering vault-wide.

| Flag | Description |
|------|-------------|
| `--kind KIND`, `-k` | Narrow resolution when the ref is ambiguous |
| `-j`, `--json` | JSON object with all fields plus the body |
| `-e`, `--editor` | Open the file in `$EDITOR` (explicit; works even in non-interactive contexts) |

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
artifacts create <title> [--kind KIND]
                         [--body BODY | --body-file PATH]
                         [--name SLUG]
                         [--assignee USER] [--owner USER]
                         [--parent REF] [--depends-on REF ...]
                         [--type TYPE]
                         [--fields KEY=VALUE ...]
                         [--dry-run]
```

Creates an artifact file and prints its name. Numbered kinds (like `task`)
get an auto-incremented ID. Non-numbered kinds (like `agent`) use the title
as the filename directly.

| Flag | Description |
|------|-------------|
| `title` | Human-readable title; used to derive the filename slug |
| `--kind KIND`, `-k` | Artifact kind (default: `task`) |
| `--body BODY`, `-b` | Initial body text |
| `--body-file PATH` | Read body from *PATH*; use `'-'` to read from stdin |
| `--name SLUG` | Override the auto-derived slug (controls the name portion of the filename) |
| `--assignee USER` | Set `assignee` in frontmatter |
| `--owner USER` | Set `owner` in frontmatter |
| `--parent REF` | Set `parent` in frontmatter; bare refs are auto-wrapped as `[[REF]]` |
| `--depends-on REF` | Add a dependency; repeat for multiple; bare refs auto-wrapped |
| `--type TYPE` | Set `type` in frontmatter |
| `--fields KEY=VALUE`, `-f` | Set extra frontmatter fields; comma-separated values produce a list |
| `--dry-run`, `-n` | Print resolved frontmatter and body without writing any file |

**Kind-aware help** — `--help` renders a flag list tailored to the
requested kind. Pass `--kind` before `--help` to see the flags for a
specific kind:

```bash
artifacts create --kind task --help   # task-specific flags
artifacts create --kind note --help   # note-specific flags
artifacts create --help               # defaults to the project's default kind
```

Kind-aware help has two effects:

- **Filter (Variant A)** — convenience flags that don't apply to the
  kind (based on its `x-columns` declaration) are hidden from the flag
  list. They remain available via `--fields KEY=VALUE` as an escape hatch.
- **Augment (Variant B)** — schema properties without a dedicated flag
  get one automatically. For example, a `task` kind with a `priority`
  property gains a `--priority` flag.

**Wikilink auto-wrapping** — `--parent` and `--depends-on` accept bare
artifact refs (e.g. `t0042`) and wrap them as `[[t0042]]` automatically.
Passing an already-wrapped value like `[[t0042]]` is also fine.

**Comma-list values** — `--fields depends_on=t0001,t0002` produces a YAML
list `["[[t0001]]", "[[t0002]]"]`. Any field with commas in the value is
split the same way; wikilink wrapping applies only to `parent` and
`depends_on`.

**Examples:**

```bash
# Create a task (the default kind)
artifacts create "Fix login bug"
# → t0001-fix-login-bug

# Create an agent artifact
artifacts create "my-researcher" --kind agent
# → my-researcher

# Create with initial status and convenience flags
artifacts create "Deploy pipeline" \
  --fields status=ready \
  --assignee alice \
  --parent t0010 \
  --type feature

# Read body from a markdown file
artifacts create "Big spec" --body-file spec-draft.md

# Read body from stdin
echo "## Notes" | artifacts create "Scratch pad" --body-file -

# Override the auto-derived slug
artifacts create "Improve CLI ergonomics" --name improve-cli
# → t0001-improve-cli

# Preview without writing
artifacts create "Test task" --dry-run --assignee carol

# Multiple dependencies
artifacts create "Blocked task" \
  --depends-on t0001 --depends-on t0002

# Comma-list dependencies via --fields
artifacts create "Blocked task" --fields depends_on=t0001,t0002
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

---

### Property and Transition Verbs

Three flat verbs expose single-property read/write and state-machine
inspection without parsing `kind.json` or using `show` to read everything.

#### `get` — Read a property (or all frontmatter)

```
artifacts get <ref> [<property>] [-j]
```

| Argument / Flag | Description |
|-----------------|-------------|
| `ref` | Artifact reference (name, id, or partial) |
| `property` | Property name to read; omit to list all frontmatter fields |
| `-j`, `--json` | JSON output |

**With `<property>`** — prints the scalar value on one line. `--json`
returns `{"property": "<name>", "value": <value>}`.

**Without `<property>`** — prints all frontmatter as a two-column
key/value table (no body, unlike `show`). `--json` returns the full
frontmatter object.

Unknown property → exits 2 with `"Unknown property '<name>' for kind '<kind>' — known: [...]"`.

**Examples on `task` kind:**

```bash
# Read current status
artifacts get t0042 status
# → ready

# JSON form — pipe-friendly
artifacts get t0042 status --json
# → {"property": "status", "value": "ready"}

# All frontmatter fields (no body)
artifacts get t0042

# Full frontmatter as JSON
artifacts get t0042 --json

# Unknown property exits 2
artifacts get t0042 nonexistent
# error: Unknown property 'nonexistent' for kind 'task' — known: [...]
```

---

#### `set` — Write a single property

```
artifacts set <ref> <property> <value>
```

Writes exactly one frontmatter property. Runs the full validation
pipeline — transition check (s0033) for state-machined properties,
JSON Schema check for all. The body is preserved verbatim.

Free-form properties (those without a state machine) are allowed; `set`
writes them through schema validation only.

| Argument | Description |
|----------|-------------|
| `ref` | Artifact reference |
| `property` | Property name to write |
| `value` | New value (treated as a string; coercion follows YAML rules) |

Illegal transition → exits 2 with the s0033 D212 message:

```
error: Illegal transition for field 'status': 'in-progress' → 'verified' (allowed targets: ['review']) (allowed from any state: ['rejected'])
```

**Examples on `task` kind:**

```bash
# Advance status (transition-validated)
artifacts set t0042 status review

# Set a free-form property
artifacts set t0042 assignee alice

# Illegal transition exits 2
artifacts set t0042 status verified
# error: Illegal transition for field 'status': ...
```

---

#### `transitions` — Inspect legal next-values

```
artifacts transitions <ref> [<property>] [-j]
```

Displays the state-machine snapshot for one or all state-machined
properties declared on the artifact's kind.

| Argument / Flag | Description |
|-----------------|-------------|
| `ref` | Artifact reference |
| `property` | Property name; omit to show all state-machined properties |
| `-j`, `--json` | JSON output |

Output columns: `property`, `current`, `allowed_next`, `wildcard_targets`, `locked?`.

- `allowed_next` — targets reachable from the current value (explicit transitions table row, wildcard excluded for clarity).
- `wildcard_targets` — targets reachable from any state (from `transitions["*"]`).
- `locked?` — `yes` when `transitions == {}` (field is frozen at its initial value).

**Single property** — `--json` returns:
```json
{"property": "status", "current": "ready", "allowed_next": ["in-progress"], "wildcard_targets": [], "locked": false}
```

**All properties** — `--json` returns a dict keyed by property name.

A property with no state machine (e.g. `title`) exits 2 with:
```
error: no state machine declared for field 'title' in kind 'task'
```

**Examples on `task` kind:**

```bash
# All state-machined properties
artifacts transitions t0042

# Just 'status'
artifacts transitions t0042 status

# JSON for piping
artifacts transitions t0042 status --json
# → {"property": "status", "current": "ready", "allowed_next": ["in-progress"], ...}

# All properties as JSON
artifacts transitions t0042 --json

# Non-state-machined property exits 2
artifacts transitions t0042 title
# error: no state machine declared for field 'title' in kind 'task'
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
artifacts init [DIRECTORY] [--template TIER]
               [--distro URL] [--book NAME[:ITEMS]] ...
               [--force] [-y] [--dry-run]
```

Creates a new artifacts-os project in *DIRECTORY* (default: current directory).
Walks a two-stage selection flow:

1. **Settings tier** — always runs; writes `artifacts.yaml`.
2. **Book loop** — one multi-select prompt per book in the distro manifest
   (only when `--distro` or `$ARTIFACTS_DISTRO_URL` is set).

When no distro is configured, only Stage 1 runs and the bundled
`artifacts-os` skill is installed into `.claude/skills/artifacts-os/`.

All stages can be driven by flags for non-interactive use. On a TTY, un-flagged
stages prompt interactively. Pass `-y` to accept defaults. Refuses to run
in non-TTY mode unless `-y` or all applicable flags are supplied.

| Flag | Description |
|------|-------------|
| `DIRECTORY` | Target directory (default: `.`) |
| `--template TIER` | Settings tier: `minimal` or `standard` (default). Skips Stage 1 prompt. |
| `--distro URL` | Git-clonable distro URL. Activates the book loop after `artifacts.yaml` is written. Also injects `artbook.distro_url` into `artifacts.yaml`. Defaults to `$ARTIFACTS_DISTRO_URL` when unset. |
| `--book NAME[:ITEMS]` | Book to pull from distro (repeatable). `NAME` pulls the whole book; `NAME:item,item` pulls a subset. Requires `--distro` or `$ARTIFACTS_DISTRO_URL`. |
| `--force` | Overwrite existing files (per-file). Also bypasses the already-initialised guard. |
| `-y` / `--yes` | Accept defaults at every un-flagged stage (enables non-interactive mode). |
| `--dry-run` | Print planned writes without writing anything. |

**Environment defaults:**

- `ARTIFACTS_DISTRO_URL` — supplies the default value for `--distro` when the flag is omitted. An explicit `--distro` always wins; an empty or whitespace-only env var is treated as unset. Useful for teams that share a single internal distro across many vaults.

**Book loop behaviour:**

- `--distro` + `-y` → pulls **all books, all items** with no prompts.
- `--distro` + TTY (no `-y`) → one interactive multi-select prompt per book; default = all items.
- `--distro` + `--book agents` → pulls only the `agents` book (all items); skips other books.
- `--distro` + `--book agents:architect,developer` → pulls only those two items from `agents`.
- `-y` with no `--distro` → D2 fallback (settings tier + bundled skill, no book loop).
- `--dry-run` → prints `[would] pull from distro: <url>` without cloning or writing.

`artifacts.yaml` is written **before** the distro clone so destination resolution is always valid.

**Examples:**

```bash
# Interactive — prompts for tier; no distro = installs bundled skill
artifacts init

# Non-interactive with defaults (D2 fallback — skill only)
artifacts init -y

# Bootstrap with specific tier
artifacts init --template standard

# Re-initialise existing vault
artifacts init --force -y

# Dry-run to preview what would be written
artifacts init --template standard --dry-run

# Bootstrap and pull all books from a distro (non-interactive)
artifacts init --distro https://github.com/my-org/artbook-defaults -y

# Pull only the 'agents' book from a distro
artifacts init --distro https://github.com/my-org/artbook-defaults --book agents -y

# Pull filtered items: agents (2 items) + full skills book
artifacts init --distro https://github.com/my-org/artbook-defaults \
    --book agents:architect,developer --book skills -y

# Interactive distro setup — one prompt per book
artifacts init --distro https://github.com/my-org/artbook-defaults
```

See [docs/init-flow.md](../../docs/init-flow.md) for the full selection flow with transcripts.
See [docs/artbook.md](../../docs/artbook.md) for distro authoring and consumer quickstart.

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

### `kinds` — List registered artifact kinds or show detail for one

```
artifacts kinds [<name>] [--meta] [-q | -j | -e]
```

Without `<name>`: lists all artifact kinds registered in the active project,
including any vault-defined kinds loaded from `artifacts/kinds/<name>/kind.json`.

With `<name>`: prints the full body of `artifacts/kinds/<name>/ARTIFACT.md`
to stdout (pipe-friendly, no decoration). Use `--meta` to prepend a metadata
block, `-j` for JSON output with both meta and body, or `-e` to open
`ARTIFACT.md` in `$EDITOR`.

| Argument / Flag | Description |
|-----------------|-------------|
| `<name>` | Kind name; when given, shows detail instead of the listing |
| `--meta` | Prepend a YAML-like metadata block above the body (requires `<name>`) |
| `-q`, `--quiet` | Listing only: one kind name per line — good for scripts |
| `-j`, `--json` | JSON output; in listing mode: array of kind metadata; in detail mode: `{"meta": {...}, "body": "..."}` |
| `-e`, `--editor` | Open `artifacts/kinds/<name>/ARTIFACT.md` in `$EDITOR` (requires `<name>`; falls back to `vi` if `$EDITOR` is unset; silently downgrades to default text output in non-TTY contexts) |

`-q`, `-j`, and `-e` are mutually exclusive.

**Exit codes (detail mode):**

| Condition | Exit code |
|-----------|-----------|
| Success | 0 |
| Unknown kind | 3 |
| Kind exists but `ARTIFACT.md` missing (text or `-e` mode) | 3 |
| `--meta` or `-e` without `<name>` | 2 |

When `-j` is used with a missing `ARTIFACT.md`, the exit code is 0 and
`body` is `null` so JSON consumers can branch cleanly.

**Examples:**

```bash
# Table of all kinds
artifacts kinds

# Just the names
artifacts kinds -q

# JSON listing (includes dir, prefix, numbered, statuses)
artifacts kinds -j

# Print the ARTIFACT.md body for the task kind
artifacts kinds task

# Prepend kind metadata above the ARTIFACT.md body
artifacts kinds spec --meta

# JSON detail (includes meta object and raw body string)
artifacts kinds task -j

# Pipe body through jq
artifacts kinds task -j | jq -r .body

# Open the task kind's ARTIFACT.md in $EDITOR
artifacts kinds task -e
```

---

### `views` — List, execute, or inspect named views

```
artifacts views [<view_name> | show <view_name>] [-q | -j]
```

Lists all named views defined in `artifacts.yaml`, executes a view
by name, or inspects a single view's full definition.

| Flag | Description |
|------|-------------|
| `-q`, `--quiet` | One view name per line (list), one artifact stem per line (execute), or columns string (show) |
| `-j`, `--json` | JSON output |

**Examples:**

```bash
# Table of all views (name, kind filter, columns, sort, default-for)
artifacts views

# Just the names — useful for scripting
artifacts views -q

# JSON — includes full filters, sort, and default_views bindings
artifacts views -j
artifacts views -j | jq '.views[] | select(.default_for | length > 0)'
```

#### Execute mode

```
artifacts views <view_name> [-q | -j]
```

Pass a view name to execute it — lists all artifacts matching the view's
`filters`, displayed using its `columns` and sorted by its `sort` setting.
This is equivalent to `artifacts list --view <view_name>`.

**Examples:**

```bash
# List artifacts using the "open-tasks" view
artifacts views open-tasks

# Quiet list for scripting
artifacts views open-tasks -q

# JSON for pipelines
artifacts views open-tasks -j | jq length
```

If `<view_name>` is not defined, the command exits `2` with
`error: unknown view '<name>'` and offers close-match suggestions when available.

#### Show mode

```
artifacts views show <view_name> [-q | -j]
```

Inspect a single view's full definition — including the **untruncated**
`columns` string and the **complete** `filters` dict (which the list table
omits).

| Mode | Output |
|------|--------|
| default | Two-column rich table: `field` / `value` rows for `name`, `kind`, `columns`, `filters`, `sort`, `default-for`. |
| `-q` | Just the `columns` field-spec string on one line — designed for shell substitution into `artifacts list --fields`. |
| `-j` | A single JSON object equal to one element of the list-mode `views[]` array. Not wrapped in `{"views": [...]}`. |

**Examples:**

```bash
# Inspect a single view (full filters dict, untruncated columns)
artifacts views show ready

# Reuse a view's columns directly in a list query
artifacts list --fields "$(artifacts views show ready -q)"

# Single-view JSON for piping
artifacts views show ready -j | jq '.filters'
```

If `<view_name>` is not defined, the command exits `2` with
`error: unknown view '<name>'` and offers close-match suggestions when available.

---

### `book` — Browse and pull books from a configured distro

> **Namespaced exception to flat verbs.** `book` is the one command that
> uses a resource namespace (`book list`, `book show`, `book pull`) rather
> than a top-level flat verb. This matches the natural sentence structure
> of distro operations and follows the precedent set in spec
> s0029-artbook-mvp-distribution-model §5.1.

```
artifacts book list                        [--json]
artifacts book show <name>                 [--json]
artifacts book pull <name> [ITEM …]        [--json] [--dry-run] [--no-promote]
artifacts book promote [BOOK]              [--json] [--dry-run] [--clean]
```

Configure the distro URL once in `artifacts.yaml`:

```yaml
artbook:
  distro_url: https://github.com/your-org/artbook-defaults
```

> **Creating a distro?** See [`docs/artbook.md`](../../docs/artbook.md)
> for the author guide — `artbook.yaml` schema, walker modes, and
> destination patterns.

#### `book list` — list available books

Reads the distro manifest and prints one row per book. When
`artbook.yaml` is present at the vault root, it is read directly
without cloning (local-manifest auto-detect). Otherwise the distro
URL is cloned.

```
Distro: artifacts-os — Default agents shipped by artifacts-os.
URL:    https://github.com/example/artifacts-os @ a1b2c3d

Name      Source              Destination        Description
agents    artifacts/agents/   .claude/agents/    Default agent specs.
skills    src/ai/skills/      .claude/skills/    (recurse) Claude skills.

2 books.
```

`--json` emits a single JSON object:

```json
{
  "distro": {"name": "…", "description": "…", "url": "…", "sha": "…"},
  "books": [{"name": "agents", "src": "artifacts/agents/", "dest": ".claude/agents/", …}]
}
```

#### `book show <name>` — inspect a book

Shows book metadata and the list of files a pull would land.
Supports local-manifest auto-detect (no clone required).

```
Book:        agents
Source:      artifacts/agents/
Destination: .claude/agents/
Description: Default agent specs.

Distro:      artifacts-os
URL:         (local)

Contents (2 files):
  architect.md
  developer.md
```

Recurse-mode books group contents by unit:

```
Book:        skills
Source:      src/ai/skills/
Destination: .claude/skills/
Mode:        recurse (folder-of-folders)

Contents (2 units, 2 files):

  artifacts-os/
    SKILL.md

  release-changelog/
    SKILL.md
```

#### `book pull <name> [ITEM …]` — pull a book into the vault

Clones the distro and copies the book's files into `dest`,
overwriting existing files. Requires `artbook.distro_url` — there
is no local-manifest path for `pull`.

```
Pulling book 'agents' from artifacts-os @ a1b2c3d…

Action     Destination
write      .claude/agents/architect.md
overwrite  .claude/agents/developer.md

Summary: 2 written (1 overwritten, 1 new).
```

**Item selection** — pass one or more `ITEM` names after the book
name to pull only a matching subset.

| Walker mode | Item matches |
|-------------|-------------|
| Flat (default) / allowlist | Filename **stem** (`architect`) or full filename (`architect.md`) |
| Recurse (`recurse: true`) | **Unit folder name** — e.g. `artifacts-os`, `task`; all files within the unit are included |

```bash
# Pull only architect.md (flat book)
artifacts book pull agents architect

# Extension-qualified form works the same
artifacts book pull agents architect.md

# Pull two units from a recurse book
artifacts book pull skills artifacts-os release-changelog
```

If any item name is not found in the book, the command exits 1
**before writing any files** and lists available items:

```
error: items not found in book 'agents': ghost
       Available items: architect, developer
       Run `artifacts book show agents` to see all items.
```

`--dry-run` plans the writes but does not execute them; every action
line is prefixed with `[would]` and the summary with `[dry-run]`.

`--json` emits one JSONL record per file followed by a summary line:

```jsonl
{"action": "write", "destination": ".claude/agents/architect.md", "overwritten": false, "was_symlink": false}
{"summary": {"written": 2, "overwritten": 0, "new": 2}, "distro": {…}, "book": "agents"}
```

`--no-promote` skips the post-pull promotion step for this invocation
only. Canonical writes still happen; only the promotion step that fans
out to tool-specific locations (e.g. `.claude/agents/`) is suppressed.
This is a one-shot opt-out — it does not change `artbook.promotion` in
`artifacts.yaml`. Use `artbook.promotion: disabled` in `artifacts.yaml`
for a persistent opt-out. `--no-promote` always wins when both are set.

Both `--dry-run` and `--json` respect item filters when `ITEM …` is
supplied.

#### `book promote [BOOK]` — re-run promotion without pulling

Re-runs the promotion step against current canonical content without
cloning the distro or modifying canonical files. Useful when you
change `artbook.promote_mode`, restore a vault from backup, or
manually delete a promotion target.

```bash
# Re-promote all books that have a promote: field
artifacts book promote

# Re-promote one book
artifacts book promote agents

# Rebuild from scratch (ignore recorded state)
artifacts book promote agents --clean

# Preview what would happen
artifacts book promote agents --dry-run

# Machine-readable output
artifacts book promote agents --json
```

`--clean` ignores the existing state file entry for the book and
rebuilds it from current canonical content. Use this after manually
deleting a promotion target when the state file still records it as
promoted.

`--dry-run` prints the planned writes and cleanups without making any
filesystem changes.

`--json` emits a structured `PromotionReport` JSON object.

`--no-promote` is not valid on `book promote` — this verb *is* the
promotion step.

#### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Runtime error (clone failed / unknown book / write failed) |
| 2 | Usage error (bad flag, missing argument) |
| 3 | Vault not initialised (`artifacts.yaml` not found) |
| 4 | `artbook.distro_url` missing or empty in `artifacts.yaml` (`pull` only) |

---

### `hooks` — manage hook bundles

Hook bundles live under `artifacts/hooks/<slug>/`. Each bundle contains a
manifest (`<slug>.md`) and optional sibling scripts. A bundle must be
*promoted* before the loader fires it. See [`docs/hooks.md`](../../docs/hooks.md)
for the full model.

```
artifacts hooks list [--host HOST] [--active | --inactive]
                     [--source yaml|bundle] [--tail [N]] [-j]
                     [--prune [--dry-run]]
artifacts hooks show <slug>   [-j]
artifacts hooks promote <slug> [--force] [-j]
artifacts hooks demote  <slug> [-j]
```

#### `hooks list`

Lists all hooks (yaml + bundle) as a Rich table.

Default columns: `name`, `host`, `active`, `phase`, `event`, `source`.

`active` values: `yes` (symlink resolves), `dangling` (target missing), `no`
(no `.active/` entry).

| Flag | Effect |
|------|--------|
| `--host HOST` | Filter by `host:` value |
| `--active` | Show only hooks whose `.active/` entry resolves |
| `--inactive` | Show only hooks without a resolving `.active/` entry |
| `--source yaml\|bundle` | Restrict to one source |
| `--tail [N]` | Show last N results (default 50 with bare flag) |
| `-j` | JSON array output |
| `--prune` | Remove dangling `.active/` entries; emits `hook.demoted` with `reason: "prune"` |
| `--dry-run` | With `--prune`: show what would be removed without making FS changes |

**JSON shape (`-j`):**

```json
[
  {
    "name": "auto-commit",
    "host": "artifacts-os",
    "phase": "post",
    "blocking": false,
    "timeout": 30,
    "source": "bundle",
    "active": "yes",
    "matcher": {"event": "artifact.status_changed"}
  }
]
```

#### `hooks show <slug>`

Renders manifest frontmatter, sibling-file listing (`path`, `+x`, `size`),
active state, and a tail of the last 5 `hook.fired` / `hook.failed` events.

**JSON shape (`-j`):**

```json
{
  "frontmatter": {"kind": "hook", "name": "auto-commit", "host": "artifacts-os", …},
  "active": "yes",
  "siblings": [{"path": "action.sh", "executable": true, "size": 120}],
  "recent_events": [{"event": "hook.fired", "hook": "auto-commit", "phase": "post", …}]
}
```

#### `hooks promote <slug> [--force]`

Creates `artifacts/hooks/.active/<slug>` → `../<slug>/<slug>.md` (relative
symlink; falls back to a `.json` stub on filesystems without symlink support).
Idempotent on same target. `--force` overwrites a divergent entry.

**JSON shape (`-j`):**

```json
{
  "slug": "auto-commit",
  "active_path": "<vault>/artifacts/hooks/.active/auto-commit",
  "target": "../auto-commit/auto-commit.md",
  "was_stub": false,
  "was_idempotent": false
}
```

#### `hooks demote <slug>`

Removes the `.active/<slug>` entry. No-op when not active.

**JSON shape (`-j`):**

```json
{"slug": "auto-commit", "removed": true}
```

#### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | User error (unknown slug, divergent promote without `--force`) |
| 2 | Configuration error (broken manifest, malformed `.active/`) |
| 3 | Filesystem error (permissions) |

---

## Project Configuration (`cli` section)

The `cli` top-level key in `artifacts.yaml` lets you set
per-command defaults and command aliases.  Both sections are optional;
if the key is absent entirely, the CLI behaves as if neither were configured.

### Per-command defaults

```yaml
cli:
  defaults:
    show:
      editor: false   # opt out of the built-in editor default for `show`
```

| Setting | Type | Default | Effect |
|---------|------|---------|--------|
| `cli.defaults.show.editor` | bool | `true` (built-in) | Open `$EDITOR` automatically on `show` unless `-j` is passed. Set to `false` to disable. |
| `cli.defaults.create.kind` | string | `task` | Default artifact kind for `create` when `--kind` is not passed (e.g. `note`). |

**`show` opens in `$EDITOR` by default** on any interactive TTY — no configuration
required. The `cli.defaults.show.editor` key is an **opt-out**: set it to `false`
in `artifacts.yaml` to restore the plain-text rendering. Setting it to `true` is
a no-op (that is already the built-in behaviour).

Explicit flags always take precedence over defaults. Passing `-j` to `show`
prints JSON regardless of the `editor` setting. The editor default is also
suppressed automatically in non-interactive contexts (pipes, `CLAUDECODE` agent
runtime) so that machine callers always receive artifact content on stdout.

### Command aliases

The following aliases are **built in** and active in every vault — and
outside any vault — without any configuration:

| Alias | Command |
|-------|---------|
| `ls`  | `list` |
| `sh`  | `show` |
| `new` | `create` |
| `st`  | `status` |
| `vf`  | `verify` |
| `va`  | `validate` |
| `k`   | `kinds` |
| `v`   | `views` |

**Override rule — vault wins per key.** A vault-level `cli.aliases`
entry with the same key as a built-in replaces that built-in for the
current vault. All other built-ins remain active. Vault entries for
keys that are not built-ins are added alongside the defaults.

```yaml
cli:
  aliases:
    ls: status        # overrides the built-in ls→list for this vault
    x: list           # new alias alongside the defaults
```

Additional custom aliases can be added the same way:

```yaml
cli:
  aliases:
    t: status         # `artifacts t` → runs `status`
```

Aliases are applied to the first argument before argparse sees it.
An alias that maps to an unrecognised command produces the same error as
typing that command directly (argparse exits with code 2).

### Complete example

```yaml
layout_version: 1
project:
  name: my-project

cli:
  defaults:
    show:
      editor: false  # built-in default is true; set false to opt out
    create:
      kind: note   # `artifacts create "…"` creates a note by default
  aliases:
    ls: list
    t: status
```

---

## Extending the CLI — `register_kinds()`

Host applications inject custom `KindDef` objects before the CLI
dispatches by calling `register_kinds()`:

```python
from artifacts_os.cli import register_kinds, main
from artifacts_os.core import KindDef

register_kinds([
    KindDef(name="note", dir="notes", prefix="n", numbered=True,
            statuses=["draft", "published"]),
])
main()
```

Kinds registered this way are merged with any vault-defined kinds at
startup. When a vault kind shares the same name as a caller kind, the
**vault kind wins** (silent override — no error).

### Validation

`register_kinds()` raises `ValueError` on two classes of duplicates:

| Scenario | Message |
|----------|---------|
| Input list contains the same name twice | `"duplicate kind '<name>' in register_kinds() input"` |
| A name is already registered from a previous `register_kinds()` call | `"kind '<name>' is already registered"` |

These checks make duplicate registrations a hard error so bugs surface at
startup rather than at runtime.

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
