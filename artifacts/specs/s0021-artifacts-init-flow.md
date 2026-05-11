---
kind: spec
id: s0021
name: artifacts-init-flow
status: approved
task: "[[t0108-spec-artifacts-init-flow-with]]"
created: 2026-05-06
agent: architect
---

# `artifacts init` — Tiered Templates with Kind/Agent Selection

Specifies the new `artifacts init` subcommand: a single
non-destructive command that scaffolds a fresh artifacts-os
project (or re-scaffolds an existing one) by walking the operator
through three independent selection steps — settings tier, kinds,
and agents — and writing bundled templates that ship inside the
wheel via `importlib.resources`. Replaces the current stubby
`init` (a hard-coded four-kind dump with no settings progression
and no agents) without breaking existing vaults.

## 1. Background and Cross-References

- **Producing task** — [[t0108-spec-artifacts-init-flow-with]] —
  carries the verification checklist this spec must satisfy.
- **Direct ancestor (current init)** —
  `src/artifacts_os/cli/commands/init.py` — keeps the
  pre-registry hook and "refuse if already initialised" guard;
  drops the inline `_DEFAULT_KINDS` dict and the
  unconditional `openstation -> artifacts` symlink (the
  symlink is now optional, gated by an `--openstation-compat`
  flag — see §11.1).
- **Prior art (OpenStation)** —
  `/Users/leonid/.local/share/openstation/src/openstation/init.py`
  — `_select_template`, `_install_settings_template`,
  `TEMPLATE_CHOICES` patterns are reused; the file-cache
  source (`OPENSTATION_HOME`) is *not* — artifacts-os bundles
  templates in the wheel.
- **Settings basis** —
  `artifacts.yaml` (this repo's current vault config)
  is promoted verbatim as the basis for `advanced.yaml`. See §6.
- **Kind ARTIFACT.md sources** —
  `artifacts/kinds/{task,note,spec,research}/ARTIFACT.md` and
  the three loose `*.json` schemas — promoted into the bundled
  template tree. See §7.
- **Agent spec sources** —
  `artifacts/agents/*.md` (9 specs) — five are promoted into
  the bundled template tree. See §8.
- **Sibling spec** — [[s0017-artifact-kinds-discovery-mechanism]]
  — the `kind.json` + `ARTIFACT.md` pair is the discovery
  contract this spec installs templates against; not modified.

## 2. Goals

1. Replace the current `init` with a flow that (a) scaffolds
   the directory tree, (b) writes a settings file from one of
   three tiers, (c) installs zero or more kind templates, and
   (d) installs zero or more agent specs, in one command.
2. Make every step independently steerable from flags **or**
   prompts, so power users skip prompts and new users get
   guided choices.
3. Ship templates inside the wheel — no separate install cache,
   no `OPENSTATION_HOME` equivalent, no network fetch.
4. Re-init safely: skip-by-default, `--force` to overwrite, with
   per-file granularity (no all-or-nothing).
5. Fail loud in non-TTY contexts unless the operator opts into
   defaults explicitly (`-y`).

## 3. Non-Goals

- **No new TUI dependency.** Multi-select is plain `input()` —
  no `prompt_toolkit`, `questionary`, `survey`, etc.
- **No template versioning / migration.** Re-init writes the
  current bundled template; legacy migration is a separate task.
- **No remote template fetch.** Templates are wheel-local.
- **No JSON-schema authoring helpers.** This spec installs
  schemas; it does not validate or compose them.
- **No `.claude/` / `.opencode/` symlink trees.** That belongs
  to OpenStation's harness install, not artifacts-os's vault
  init. (If wanted later, a separate `artifacts install-claude`
  command — out of scope here.)
- **No interactive editing of templates after install.** Operator
  edits files in-place after init returns.

## 4. Locked Decisions Summary

| ID  | Decision                                                                                                                | Rationale (brief)                                                                                                          |
|-----|-------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| D1  | Subcommand is `artifacts init [DIRECTORY]`; pre-registry (no vault required); refuses if `artifacts.yaml` exists *unless* `--force`. | Preserves the only behavioural guard the current init relies on; matches operator mental model from OpenStation.           |
| D2  | Three-step prompt: tier (single) → kinds (multi) → agents (multi). Each step is skippable independently via its flag.    | Brainstorm pre-decision (Option Y) — three independent picks, not nested.                                                  |
| D3  | Non-TTY without `-y` and without all three flags supplied → exit 2 with explicit error. `-y` accepts every default.       | Fail-loud avoids surprise when scripts pipe `init`. `-y` is the explicit "I know the defaults" override.                    |
| D4  | Multi-select format: comma-separated numbers (e.g. `1,3,5`); empty input → defaults; `*` → all; `-` → none.                | Single-line, no extra dep, preserves keyboard-only accessibility. Per-item y/n is too chatty for 9-item agent lists.        |
| D5  | Three settings tiers (`basic` / `standard` / `advanced`); each strictly additive. `standard` is the default.              | Mirrors OpenStation's `minimal`/`standard`/`full` shape; "additive" makes upgrade-by-hand obvious.                          |
| D6  | Five kind templates ship: `task`, `note`, `spec`, `research`, `agent`. Default Step 2 selection: `task`, `note`, `spec`.   | The three universally-needed kinds; `research` and `agent` are opt-in.                                                      |
| D7  | Five agent templates ship: `architect`, `developer`, `author`, `researcher`, `technical-writer`. Default Step 3: none.    | Matches the brainstorm constraint; agents are an opt-in capability, not a default.                                          |
| D8  | Templates live under `src/artifacts_os/templates/{settings,kinds,agents}/` and are read via `importlib.resources.files`.   | Wheel-local, no extra install step; standard library API since Python 3.9.                                                  |
| D9  | Variable interpolation contract: `{{project_name}}`, `{{project_alias}}`, `{{created}}`. `str.replace` only — no Jinja.    | Three variables cover every templated file; full templating is overkill and a dep risk.                                     |
| D10 | Agent ↔ agent-kind coupling: selecting any agent in Step 3 **auto-includes** the `agent` kind in Step 2.                  | Agents are unusable without the kind installed; refusing would surprise the operator; loose-link would silently break Show. |
| D11 | `advanced.yaml` per-assignee queues are **dynamic-emit** — one queue per selected agent; commented-out stub when none.    | Static-emit leaves dangling assignee references; documentation-only loses the "look, here's how" affordance.                |
| D12 | Existing-file guard is **per-file**, applies to every written file. `--force` overwrites *only* the files it would write. | All-or-nothing forces operators to delete the vault to re-init one file; per-file matches the prevailing skip-or-overwrite. |
| D13 | Mid-init write failure: continue, accumulate errors, exit 1 at end. No rollback. `--dry-run` prints `[would] ✓ <path>`.   | Init is idempotent and per-file; a partial result is recoverable via re-run with `--force`. Rollback adds risk, not safety. |
| D14 | Flag/prompt precedence: each flag skips *its* step. Partial-flag mixing is allowed; missing flags still prompt on a TTY.  | Lets `--template advanced` non-interactively while still prompting for kinds/agents on the same invocation.                 |

## 5. CLI Surface

### 5.1 Synopsis

```
artifacts init [DIRECTORY] [--template TIER] [--kinds CSV]
              [--agents CSV] [--force] [-y] [--dry-run]
              [--openstation-compat]
```

### 5.2 Arguments

| Token | Type | Default | Help text |
|---|---|---|---|
| `DIRECTORY` (positional, optional) | path | `.` | `target directory (default: current directory)` |
| `--template` | str ∈ {`basic`,`standard`,`advanced`} | (prompt) | `settings tier (skips Step 1 when given)` |
| `--kinds` | csv | (prompt) | `comma-separated kind names to install (skips Step 2). Use 'all' for every kind, 'none' for none.` |
| `--agents` | csv | (prompt) | `comma-separated agent names to install (skips Step 3). Use 'all' for every agent, 'none' for none.` |
| `--force` | flag | `False` | `overwrite existing files (per-file)` |
| `-y` / `--yes` | flag | `False` | `accept defaults at every un-flagged step (non-interactive)` |
| `--dry-run` | flag | `False` | `print actions without writing anything` |
| `--openstation-compat` | flag | `False` | `also create the legacy 'openstation -> artifacts' symlink for the external openstation CLI` |

`--no-ai` (the current flag) is **removed** — AI command install is
out of scope per §3 (Non-Goals). Bundled agent templates are the
agent-installation surface in this spec.

### 5.3 Exit codes

| Code | Meaning                                                                              |
|------|--------------------------------------------------------------------------------------|
| 0    | Success — every requested file was written or already correct.                       |
| 1    | Partial failure — at least one file failed to write. Stderr lists every failure.     |
| 2    | Usage error — bad flag value, missing template, non-TTY without `-y`/all-flags, target already initialised without `--force`. |
| 3    | Not-found — `DIRECTORY` does not exist *and* its parent is not writable.             |

These match the codes the rest of the CLI emits (see
`src/artifacts_os/cli/__init__.py` `_run`).

### 5.4 Help text (top-level)

```
usage: artifacts init [-h] [--template {basic,standard,advanced}]
                      [--kinds CSV] [--agents CSV] [--force] [-y]
                      [--dry-run] [--openstation-compat]
                      [DIRECTORY]

initialise a new artifacts-os project

The init flow has three independent selection steps:
  1. Settings tier — basic / standard / advanced
  2. Kinds         — multi-select from the bundled catalogue
  3. Agents        — multi-select from the bundled catalogue

Pass --template / --kinds / --agents to skip the corresponding
step; use -y to accept defaults at every un-flagged step in
non-interactive mode.

positional arguments:
  DIRECTORY             target directory (default: current directory)

options:
  -h, --help            show this help message and exit
  --template {basic,standard,advanced}
                        settings tier (skips Step 1 when given)
  --kinds CSV           comma-separated kinds to install (skips Step 2)
  --agents CSV          comma-separated agents to install (skips Step 3)
  --force               overwrite existing files (per-file)
  -y, --yes             accept defaults at every un-flagged step
  --dry-run             print actions without writing anything
  --openstation-compat  also create 'openstation -> artifacts' symlink
```

## 6. Settings Templates — `basic` / `standard` / `advanced`

Every tier carries the **mandatory header**:

```yaml
layout_version: 1

project:
  name: "{{project_name}}"
  created: "{{created}}"
```

Each subsequent tier is **strictly additive** over the previous —
diffing tiers yields a one-way append, no rewrites. This is the
load-bearing property a hand-upgrade depends on.

### 6.1 `basic.yaml` — minimal viable

Header only, plus a single curated view set so `artifacts list`
returns something useful out of the box:

```yaml
# (mandatory header above)

views:
  active:
    columns: id,name,assignee,status
    filters: { kind: task, status: in-progress }
    sort: -started

  ready:
    columns: id,name,assignee,created:date
    filters: { kind: task, status: ready }
    sort: created

  done:
    columns: id,name,assignee,completed:date
    filters: { kind: task, status: done }
    sort: -completed
```

**Rationale.** A vault with no `views:` block makes `artifacts
list <name>` error out — `basic` ensures the `active` / `ready` /
`done` triad always exists. No `default_views`, no `cli` block —
the CLI falls back to its built-in defaults.

### 6.2 `standard.yaml` — sensible defaults

Adds:

- Two more lifecycle views (`review`, `backlog`) — covers every
  task `status` enum value the user is likely to query.
- The cross-kind `recent` view — answers "what changed today".
- A per-kind landing view for every shipped kind (`spec`,
  `research`, `note`, `agents`) — supports `artifacts list spec`,
  `artifacts list research`, etc.
- A `default_views` block mapping each kind to its landing view —
  what `artifacts list <kind>` resolves to.
- Per-type slices (`features`, `implementations`, `task-specs`,
  `task-docs`) — common power-user filters.

```yaml
# (mandatory header above)

views:
  # lifecycle slices (basic + review + backlog)
  active:   { columns: id,name,assignee,status,         filters: { kind: task, status: in-progress }, sort: -started }
  ready:    { columns: id,name,assignee,created:date,   filters: { kind: task, status: ready },       sort: created }
  review:   { columns: id,name,assignee,owner,          filters: { kind: task, status: review },      sort: -created }
  backlog:  { columns: id,name,assignee,type,           filters: { kind: task, status: backlog },     sort: created }
  done:     { columns: id,name,assignee,completed:date, filters: { kind: task, status: done },        sort: -completed }
  rejected: { columns: id,name,assignee,owner,          filters: { kind: task, status: rejected },    sort: -created }

  # per-type task slices
  features:         { columns: id,name,status,assignee, filters: { kind: task, type: feature },        sort: -created }
  implementations:  { columns: id,name,status,assignee, filters: { kind: task, type: implementation }, sort: -created }
  task-specs:       { columns: id,name,status,assignee, filters: { kind: task, type: spec },           sort: -created }
  task-docs:        { columns: id,name,status,assignee, filters: { kind: task, type: documentation },  sort: -created }

  # per-kind landing views
  spec:     { columns: id,name,status,created:date, filters: { kind: spec },     sort: -created }
  research: { columns: id,name,status,created:date, filters: { kind: research }, sort: -created }
  note:     { columns: id,name,type,created:date,   filters: { kind: note },     sort: -created }
  agents:   { columns: name,description,            filters: { kind: agent },    sort: name }

  # cross-kind utility
  recent:   { columns: id,kind,name,status,created:date, sort: -created }

default_views:
  task: ready
  spec: spec
  research: research
  agent: agents
  note: note
```

**Rationale.** The brainstorm constraint says tiers are additive;
`standard` is the column block + the rows that depend on it.
`default_views` only makes sense once the per-kind views exist,
so it lives here. The `cli` block (aliases) is held back to
`advanced` — pre-locking aliases on a fresh vault is an opinion,
not a default.

### 6.3 `advanced.yaml` — power user

Adds **on top of standard**:

- Per-assignee task queues — one per selected agent (D11).
- Spec lifecycle slices (`specs-draft`, `specs-approved`).
- Note sub-type slice (`note-planning`).
- A `cli` block: `defaults.show.editor: true`, the
  `defaults.create.kind: note` shortcut, and the alias map
  (`ls`, `sh`, `new`, `st`, `vf`, `va`, `k`, `v`).

The advanced template is generated at init time, **not** stored
verbatim — see §6.4 for the reason. The static skeleton
delivered as `advanced.yaml` looks like:

```yaml
# (standard.yaml content above, unchanged)

views:
  # ... standard views above ...

  # spec lifecycle slices
  specs-draft:    { columns: id,name,agent,created:date, filters: { kind: spec, status: draft },    sort: -created }
  specs-approved: { columns: id,name,agent,created:date, filters: { kind: spec, status: approved }, sort: -created }

  # note sub-types
  note-planning:  { columns: id,name,created:date, filters: { kind: note, type: planning }, sort: -created }

  # ── per-assignee task queues (dynamic — see §6.4) ─────────
  # {{assignee_queues}}

cli:
  defaults:
    show:
      editor: true
    create:
      kind: note
  aliases:
    ls: list
    sh: show
    new: create
    st: status
    vf: verify
    va: validate
    k: kinds
    v: views
```

### 6.4 Conditional content in `advanced.yaml` (D11)

The `{{assignee_queues}}` placeholder is replaced at write time
based on the agents selected in Step 3:

- **One or more agents selected** — emit one queue view per
  agent, named `<agent>-queue`:

  ```yaml
  architect-queue:        { columns: id,name,status,created:date, filters: { kind: task, assignee: architect },        sort: status }
  developer-queue:        { columns: id,name,status,created:date, filters: { kind: task, assignee: developer },        sort: status }
  ```

- **No agents selected** — emit a commented-out template stub so
  the operator can hand-add later:

  ```yaml
  # Per-assignee task queues — uncomment after creating agents.
  # Add one entry per agent name in artifacts/agents/.
  #
  # developer-queue:
  #   columns: id,name,status,created:date
  #   filters: { kind: task, assignee: developer }
  #   sort: status
  ```

This avoids dangling references (static-emit names agents that
may not exist) while preserving the affordance (documentation-
only would erase the example).

## 7. Kind Templates

### 7.1 Inventory

Five kinds ship in the bundle. Each kind is a directory under
`src/artifacts_os/templates/kinds/<name>/` containing two files:

| Kind       | `kind.json` source (current path)         | `ARTIFACT.md` source (current path)              | Default in Step 2 |
|------------|-------------------------------------------|--------------------------------------------------|-------------------|
| `task`     | `artifacts/kinds/task.json`               | `artifacts/kinds/task/ARTIFACT.md`               | yes               |
| `note`     | `artifacts/kinds/note.json`               | `artifacts/kinds/note/ARTIFACT.md`               | yes               |
| `spec`     | `artifacts/kinds/spec.json`               | `artifacts/kinds/spec/ARTIFACT.md`               | yes               |
| `research` | `artifacts/kinds/research.json`           | `artifacts/kinds/research/ARTIFACT.md`           | no                |
| `agent`    | `artifacts/kinds/agent.json`              | `artifacts/kinds/agent/ARTIFACT.md` *(new — see §7.3)* | no (auto via D10) |

Default selection in Step 2 (`task`, `note`, `spec`) is the
universal triad — the smallest set that supports the documented
`task`-with-`spec` decomposition pattern in
`artifacts/kinds/task/ARTIFACT.md`.

### 7.2 Installed-file layout

Per selected kind, init writes:

```
artifacts/kinds/<name>.json              # schema (D1 of s0017)
artifacts/kinds/<name>/ARTIFACT.md       # body template + description
artifacts/<x-dir>/.gitkeep               # storage directory (x-dir read from kind.json)
```

The `.gitkeep` ensures empty kind directories survive a clean
checkout.

### 7.3 `agent` kind ARTIFACT.md

`artifacts/kinds/agent/` does not currently exist as a directory
in this repo (only `agent.json` is present). The bundled
template ships an `ARTIFACT.md` for `agent` — content lives
under `src/artifacts_os/templates/kinds/agent/ARTIFACT.md`.
Adding it is part of the implementation task that lands this
spec, not in scope for the spec itself.

### 7.4 Variable interpolation in kind templates

Kind templates contain no `{{...}}` placeholders today — they
ship verbatim. The interpolation pass runs on every written
file uniformly (§9), so future templates can adopt placeholders
without changing the loader.

## 8. Agent Templates

### 8.1 Inventory

Five agents ship; each is a single `.md` file under
`src/artifacts_os/templates/agents/<name>.md`:

| Agent              | Source path (current)                              | Role summary                                              |
|--------------------|----------------------------------------------------|-----------------------------------------------------------|
| `architect`        | `artifacts/agents/architect.md`                    | Designs systems, writes specs, sets standards.            |
| `developer`        | `artifacts/agents/developer.md`                    | Implements features and fixes from specs.                 |
| `author`           | `artifacts/agents/author.md`                       | Writes prompts, agent specs, skills, commands.            |
| `researcher`       | `artifacts/agents/researcher.md`                   | Gathers and synthesizes information for decisions.        |
| `technical-writer` | `artifacts/agents/technical-writer.md`             | Owns docs/, READMEs, doc-relevant CLAUDE.md sections.     |

Default selection in Step 3: **none** (per brainstorm
constraint).

### 8.2 Excluded from the bundle (and why)

`devrel`, `product-manager`, `project-manager`,
`security-engineer` — these exist in this repo but are
artifacts-os-specific roles. The bundled five are the
generic role family that any artifacts-os vault benefits
from; the rest can be hand-added by the operator after
init.

### 8.3 Installed-file layout

Per selected agent, init writes one file:

```
artifacts/agents/<name>.md
```

### 8.4 Agent ↔ agent-kind coupling (D10)

If Step 3 selects one or more agents, init **auto-includes**
the `agent` kind in the Step 2 set (even if Step 2 explicitly
omitted it). The summary line that prints before writes
reflects this:

```
Selected:
  template : standard
  kinds    : task, note, spec, agent (agent kind auto-included for selected agents)
  agents   : architect, developer
```

If `--kinds` is supplied explicitly *without* `agent` and
`--agents` is supplied with at least one agent, init still
auto-includes — the auto-include applies whether the kind
list came from a flag or a prompt.

## 9. Variable Interpolation Contract (D9)

### 9.1 Variables

| Token              | Source rule                                                                                  | Used in              |
|--------------------|----------------------------------------------------------------------------------------------|----------------------|
| `{{project_name}}` | First `# H1` from `<DIRECTORY>/CLAUDE.md` if present (and not literally `Open Station`); otherwise `Path(DIRECTORY).name`. | `*.yaml` (settings) |
| `{{project_alias}}`| Lowercased first word of `{{project_name}}`, alphanumeric only, truncated to 8 chars.        | `*.yaml` (settings)  |
| `{{created}}`      | `datetime.date.today().isoformat()` evaluated once per init invocation.                      | `*.yaml` (settings)  |

Source-of-value resolution copies OpenStation's
`_get_project_name` / `_derive_project_alias` (init.py
lines 118–145) verbatim, swapping the `Open Station` literal
for `Artifacts OS` (so this repo's own CLAUDE.md doesn't
poison the alias).

### 9.2 Substitution mechanism

```python
content = src.read_text(encoding="utf-8")
content = content.replace("{{project_name}}", project_name)
content = content.replace("{{project_alias}}", project_alias)
content = content.replace("{{created}}",      today_iso)
content = content.replace("{{assignee_queues}}", queues_block)  # advanced.yaml only
```

`str.replace` only — **no Jinja, no f-string interpolation, no
Python `.format()`**. A literal `{{` or `}}` inside a template
that is *not* a known variable passes through untouched (the
replace list is closed; unknown tokens are not interpolated).

### 9.3 Adding a new variable

The variable list is closed. Adding a variable requires (a) a
spec amendment with rationale and (b) an entry in the table
above. This keeps the substitution mechanism's behaviour
auditable.

## 10. Three-Step Prompt Flow

### 10.1 Step 1 — settings tier (single choice)

```
Settings tier (1 of 3):
  1) basic     — header + lifecycle views (active / ready / done)
  2) standard  — adds per-type slices, default_views, cross-kind 'recent'
  3) advanced  — adds per-assignee queues, cli aliases, spec / note slices

Choice [2]: <enter>
```

- Empty input → default (`2` = `standard`).
- Numeric input (`1`, `2`, `3`) or name (`basic`, `standard`,
  `advanced`) accepted.
- Three invalid attempts → fall through to default with a
  warning line (parity with OpenStation's `_select_template`).
- `Ctrl-C` / `Ctrl-D` → exit code 130 (KeyboardInterrupt) /
  exit code 0 with "Aborted." printed.

### 10.2 Step 2 — kinds (multi-select)

```
Kinds (2 of 3) — comma-separated numbers, '*' for all, '-' for none:
  1) task      [default]
  2) note      [default]
  3) spec      [default]
  4) research
  5) agent

Choice [1,2,3]: <enter>
```

- Empty input → defaults (`1,2,3` = `task,note,spec`).
- `*` → every kind (`1,2,3,4,5`).
- `-` → none.
- Invalid number, duplicate, or unknown name → re-prompt with
  a per-token error (e.g. `error: '7' is out of range; pick
  from 1..5`). Three invalid attempts → fall through to
  defaults.
- Names accepted alongside numbers (`task,spec`, `1,spec`).

### 10.3 Step 3 — agents (multi-select)

```
Agents (3 of 3) — comma-separated numbers, '*' for all, '-' for none:
  1) architect
  2) developer
  3) author
  4) researcher
  5) technical-writer

Choice [-]: <enter>
```

- Empty input → default `-` (none — D7).
- Same input rules as Step 2.
- After this step, init prints the summary block (§8.4), then
  proceeds to write.

### 10.4 Worked transcript — `basic` tier, no agents

```
$ artifacts init my-vault
Settings tier (1 of 3):
  1) basic     — header + lifecycle views (active / ready / done)
  2) standard  — adds per-type slices, default_views, cross-kind 'recent'
  3) advanced  — adds per-assignee queues, cli aliases, spec / note slices

Choice [2]: 1

Kinds (2 of 3) — comma-separated numbers, '*' for all, '-' for none:
  1) task      [default]
  2) note      [default]
  3) spec      [default]
  4) research
  5) agent

Choice [1,2,3]: <enter>

Agents (3 of 3) — comma-separated numbers, '*' for all, '-' for none:
  1) architect
  2) developer
  3) author
  4) researcher
  5) technical-writer

Choice [-]: <enter>

Selected:
  template : basic
  kinds    : task, note, spec
  agents   : (none)

Writing files...
  ✓ artifacts.yaml
  ✓ artifacts/kinds/task.json
  ✓ artifacts/kinds/task/ARTIFACT.md
  ✓ artifacts/tasks/.gitkeep
  ✓ artifacts/kinds/note.json
  ✓ artifacts/kinds/note/ARTIFACT.md
  ✓ artifacts/notes/.gitkeep
  ✓ artifacts/kinds/spec.json
  ✓ artifacts/kinds/spec/ARTIFACT.md
  ✓ artifacts/specs/.gitkeep

Initialised artifacts-os project: /abs/path/to/my-vault
```

### 10.5 Worked transcript — `standard` tier with two agents

```
$ artifacts init
Settings tier (1 of 3): <enter>
Kinds (2 of 3): <enter>
Agents (3 of 3): 1,2

Selected:
  template : standard
  kinds    : task, note, spec, agent (agent kind auto-included for selected agents)
  agents   : architect, developer

Writing files...
  ✓ artifacts.yaml
  ✓ artifacts/kinds/task.json
  ...
  ✓ artifacts/kinds/agent.json
  ✓ artifacts/kinds/agent/ARTIFACT.md
  ✓ artifacts/agents/.gitkeep
  ✓ artifacts/agents/architect.md
  ✓ artifacts/agents/developer.md

Initialised artifacts-os project: /abs/path/to/cwd
```

### 10.6 Worked transcript — `advanced` tier with all agents

```
$ artifacts init --template advanced --kinds all --agents all
Selected:
  template : advanced
  kinds    : task, note, spec, research, agent
  agents   : architect, developer, author, researcher, technical-writer

Writing files...
  ✓ artifacts.yaml
  ✓ artifacts/kinds/task.json
  ...
  ✓ artifacts/agents/technical-writer.md
  ✓ openstation -> artifacts                  # only with --openstation-compat

Initialised artifacts-os project: /abs/path/to/cwd
```

The `architect-queue`, `developer-queue`, `author-queue`,
`researcher-queue`, `technical-writer-queue` views are emitted
inline in `artifacts.yaml` per §6.4.

## 11. Non-TTY Behavior (D3)

### 11.1 Decision matrix

| stdin TTY? | All three flags supplied? | `-y` supplied? | Outcome                                                                  |
|------------|--------------------------|----------------|--------------------------------------------------------------------------|
| yes        | any                      | any            | Prompt for un-flagged steps. `-y` is honoured (silently uses defaults).  |
| no         | yes                      | any            | Run non-interactively with the supplied flags. `-y` redundant but OK.    |
| no         | no                       | yes            | Run non-interactively with defaults for un-flagged steps.                |
| no         | no                       | no             | **Error** (exit 2) — see §11.2 for wording.                              |

### 11.2 Exact error message

```
error: stdin is not a TTY and no defaults were accepted.
       Pass -y to accept defaults at every un-flagged step,
       or supply --template, --kinds, and --agents explicitly.
```

Printed to stderr, single block, no colour codes when stderr
is not a TTY. Exit code 2.

## 12. Multi-Select Input Format (D4)

### 12.1 Decision

Comma-separated numbers (or names), with two single-char
shortcuts:

| Token | Meaning                          |
|-------|----------------------------------|
| `*`   | all options                      |
| `-`   | no options (empty selection)     |
| `n,m` | specific items                   |

Empty input → default selection.

### 12.2 Rationale

| Option           | Pro                                          | Con                                                         |
|------------------|----------------------------------------------|-------------------------------------------------------------|
| Comma-sep nums   | One line, screen-reader friendly, no dep     | No live preview of which item is which while choosing       |
| Per-item y/n     | Clear what each item is at decision time     | 9 prompts for 9-agent list — high friction for power users  |
| Spacebar TUI     | Visually rich                                | New dep (`prompt_toolkit`/`questionary`) — D8 forbids       |

Comma-sep wins because (a) the brainstorm forbids new TUI deps,
(b) the menu is shown immediately above the prompt so screen
position equals item identity, (c) `*` and `-` cover the two
common shortcuts that name-based input would also need.

### 12.3 Accessibility implications

- Screen readers read the menu top-to-bottom once, then the
  prompt — no live cursor to track.
- Keyboard-only operators type a comma-separated list; no arrow
  keys, no spacebar, no terminal capability requirements.
- The format is the same as `--kinds` / `--agents` flags, so a
  CSV pasted into the flag works identically in the prompt.

## 13. Bundled Template Layout (D8)

### 13.1 Wheel layout

```
src/artifacts_os/templates/
├── __init__.py                # empty (marker for importlib.resources)
├── settings/
│   ├── basic.yaml
│   ├── standard.yaml
│   └── advanced.yaml
├── kinds/
│   ├── task/
│   │   ├── kind.json
│   │   └── ARTIFACT.md
│   ├── note/
│   │   ├── kind.json
│   │   └── ARTIFACT.md
│   ├── spec/
│   │   ├── kind.json
│   │   └── ARTIFACT.md
│   ├── research/
│   │   ├── kind.json
│   │   └── ARTIFACT.md
│   └── agent/
│       ├── kind.json
│       └── ARTIFACT.md
└── agents/
    ├── architect.md
    ├── developer.md
    ├── author.md
    ├── researcher.md
    └── technical-writer.md
```

### 13.2 `pyproject.toml` packaging

The `templates/` package must ship in the wheel. Add to
`pyproject.toml`:

```toml
[tool.setuptools.package-data]
"artifacts_os.templates" = [
    "settings/*.yaml",
    "kinds/*/kind.json",
    "kinds/*/ARTIFACT.md",
    "agents/*.md",
]
```

`__init__.py` is empty — the `templates` package exists only as
an `importlib.resources` anchor.

### 13.3 Loader API (Python 3.9+)

```python
from importlib.resources import files

def _template_root():
    return files("artifacts_os.templates")

def _load_settings_template(tier: str) -> str:
    return _template_root().joinpath("settings", f"{tier}.yaml").read_text(encoding="utf-8")

def _load_kind_schema(name: str) -> str:
    return _template_root().joinpath("kinds", name, "kind.json").read_text(encoding="utf-8")

def _load_kind_artifact(name: str) -> str:
    return _template_root().joinpath("kinds", name, "ARTIFACT.md").read_text(encoding="utf-8")

def _load_agent_template(name: str) -> str:
    return _template_root().joinpath("agents", f"{name}.md").read_text(encoding="utf-8")
```

`importlib.resources.files()` returns a `Traversable`; `.joinpath`
+ `.read_text` works with both filesystem (editable installs)
and zipfile (built wheels) backends. **No `pkg_resources`** —
deprecated and slow.

### 13.4 Discovery

Step 2 / Step 3 menus are derived at runtime by listing the
templates directory:

```python
def _discover_kinds() -> list[str]:
    return sorted(
        p.name for p in _template_root().joinpath("kinds").iterdir()
        if p.is_dir() and p.joinpath("kind.json").is_file()
    )

def _discover_agents() -> list[str]:
    return sorted(
        p.name.removesuffix(".md")
        for p in _template_root().joinpath("agents").iterdir()
        if p.is_file() and p.name.endswith(".md")
    )
```

Adding a kind or agent to the bundle is therefore a pure file-add
— no registration list to update.

## 14. Existing-File Guard (D12)

### 14.1 Granularity

Per-file. Every write target (settings file, each kind's
`kind.json`, each kind's `ARTIFACT.md`, each `.gitkeep`, each
agent file) is checked individually:

- File does not exist → write.
- File exists, no `--force` → skip with `⊘ <path> (exists,
  skipped — use --force to overwrite)`.
- File exists, `--force` → overwrite with `✓ <path>
  (overwritten)`.

### 14.2 What the top-level guard refuses

The top-level guard (`if (target / "artifacts" / "artifacts.yaml").is_file()`)
is preserved from the current init **but only when `--force`
is NOT supplied**:

```
$ artifacts init
error: already initialised at /abs/path; pass --force to re-init in place
```

With `--force`, init proceeds; per-file guards (§14.1) decide
each individual write.

### 14.3 Worked example

```
$ artifacts init --template standard --force
Selected:
  template : standard
  kinds    : task, note, spec
  agents   : (none)

Writing files...
  ✓ artifacts.yaml (overwritten)
  ⊘ artifacts/kinds/task.json (exists, skipped — use --force was supplied; this file is per-file-locked)
  ✓ artifacts/kinds/task/ARTIFACT.md (overwritten)
  ...
```

`--force` overwrites by default; a future `--force-only-settings`
flag could narrow this further but is out of scope.

## 15. Error Handling (D13)

### 15.1 Missing template in package

```
error: template not found: artifacts_os/templates/settings/standard.yaml
       (this is a bug — please file an issue)
```

Exit 2. Should be unreachable in a correctly-built wheel; the
self-check at top of `cmd_init` validates the template root.

### 15.2 Mid-init write failure

Every write is wrapped in try/except. On failure:

1. Print `✗ <path>: <reason>` to stderr.
2. Increment a `failed` counter.
3. Continue with the next file.

After the write loop:

```
Initialised artifacts-os project: /abs/path/to/cwd
  18 files written, 1 failed.

Failures:
  ✗ artifacts/agents/developer.md: Permission denied
```

Exit 1 if `failed > 0`. **No rollback** — init is per-file
idempotent, and a partial result is recoverable via re-run with
`--force`.

### 15.3 `--dry-run` output format

Identical structure to a real run, with `[would]` prefix on
every action line and **zero** filesystem writes:

```
$ artifacts init --template standard --dry-run
Selected:
  template : standard
  kinds    : task, note, spec
  agents   : (none)

Writing files...
  [would] ✓ artifacts.yaml
  [would] ✓ artifacts/kinds/task.json
  ...

Dry-run complete. 12 files would be written.
```

`--dry-run` always exits 0 unless flag-validation fails (exit
2) — file-write failures cannot occur.

### 15.4 Exit code summary

| Code | Trigger                                                                          |
|------|----------------------------------------------------------------------------------|
| 0    | All requested writes succeeded (or `--dry-run`).                                 |
| 1    | At least one write failed; the rest succeeded.                                   |
| 2    | Usage: bad flag value; non-TTY without `-y` / all flags; already-init w/o force; missing bundled template. |
| 3    | DIRECTORY does not exist *and* parent is not writable.                           |

## 16. Flag/Prompt Precedence (D14)

### 16.1 Per-step skip

Each flag turns off **only its step**:

| Invocation                            | Step 1 | Step 2 | Step 3 |
|---------------------------------------|--------|--------|--------|
| `init`                                | prompt | prompt | prompt |
| `init --template advanced`            | skip   | prompt | prompt |
| `init --kinds task,spec`              | prompt | skip   | prompt |
| `init --agents architect`             | prompt | prompt | skip   |
| `init --template basic --kinds all`   | skip   | skip   | prompt |
| `init --template basic --kinds all --agents none` | skip | skip | skip   |
| `init -y`                             | skip (default) | skip (default) | skip (default) |
| `init -y --template advanced`         | skip (advanced) | skip (default kinds) | skip (default agents) |

`-y` is shorthand for "every un-flagged step uses its default
without prompting". Flags layer on top — `--template advanced -y`
means tier=advanced, kinds=defaults, agents=defaults.

### 16.2 Mixing partial flags with prompts (TTY)

`init --kinds task,note` on a TTY prompts Steps 1 and 3, skips
Step 2 with the supplied selection. The summary line shows the
final selection regardless of source:

```
Selected:
  template : standard      (prompt)
  kinds    : task, note    (--kinds)
  agents   : architect     (prompt)
```

The `(source)` annotations are optional in the implementation
but required in dry-run output to aid debugging.

### 16.3 Validation on flag values

- `--template <not-in-set>` → exit 2 with `error: invalid
  template '<value>'; expected one of basic, standard, advanced`.
- `--kinds <unknown>` → exit 2 with `error: unknown kind
  '<value>'; available: task, note, spec, research, agent`.
- `--agents <unknown>` → exit 2 with same shape.

Validation runs **before** any filesystem write — never
half-init on a typo.

## 17. Surfaces

### 17.1 Public surfaces this spec changes

| Surface                                              | Change                                                                                          |
|------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| `artifacts init` CLI flags                           | Replaces the current `--name` / `--no-ai` shape (§5).                                           |
| `artifacts_os.templates` package                     | New (§13.1).                                                                                    |
| `pyproject.toml` package-data                        | New entry (§13.2).                                                                              |
| `src/artifacts_os/cli/commands/init.py`              | Rewritten; pre-registry hook + refuse-if-init guards preserved.                                 |
| `artifacts/kinds/agent/ARTIFACT.md`                  | New file (§7.3).                                                                                |

### 17.2 Public surfaces this spec preserves

- The pre-registry execution path (`_pre_registry=True` on the
  init args) — init runs before Registry/find_vault_root.
- Exit code mapping (`_run` in `src/artifacts_os/cli/__init__.py`).
- The `openstation -> artifacts` symlink (now opt-in via
  `--openstation-compat` — preserves backwards-compat for the
  external openstation CLI).

### 17.3 Surfaces this spec deliberately drops

- `--name` flag — project name now derives from CLAUDE.md / cwd
  (§9.1). Operators who want a different name edit
  `artifacts.yaml` after init.
- `--no-ai` flag — AI command install is out of scope (§3).
- The `_default_settings()` inline string and the inline
  `_DEFAULT_KINDS` dict — replaced by bundled templates.

## 18. Test Plan

Tests live under `tests/cli/commands/test_init.py` (extending
the existing module). Group by property:

### 18.1 Bundled-template loading

- 18.1.1 `_load_settings_template("basic"|"standard"|"advanced")`
  returns non-empty text.
- 18.1.2 `_discover_kinds()` returns `["agent", "note",
  "research", "spec", "task"]` (sorted).
- 18.1.3 `_discover_agents()` returns the five names sorted.
- 18.1.4 Loader raises a clear error when a tier name is unknown
  (covers §15.1).
- 18.1.5 Loader works under both editable install (filesystem)
  and built wheel (zipimport) — assert via `tmp_path` and a
  built wheel install in CI.

### 18.2 Variable interpolation

- 18.2.1 `{{project_name}}` derives from `CLAUDE.md` H1 when
  present and not literally `Artifacts OS`.
- 18.2.2 Falls back to `Path.name` of the target directory.
- 18.2.3 `{{project_alias}}` strips non-alphanumerics, lowercases,
  truncates at 8.
- 18.2.4 `{{created}}` is today's ISO date.
- 18.2.5 An unknown `{{var}}` token in a template passes through
  untouched (no interpolation, no error).

### 18.3 Step skipping and flag/prompt precedence

- 18.3.1 `--template basic --kinds task --agents none` runs
  non-interactively with no prompts (TTY or not).
- 18.3.2 `--template basic` on a TTY skips Step 1, prompts
  Steps 2 and 3.
- 18.3.3 `-y` accepts every default; combined with `--template
  advanced` it sets tier=advanced, kinds=default, agents=none.
- 18.3.4 Non-TTY without `-y` and without all three flags exits
  2 with the §11.2 error.

### 18.4 Multi-select parsing

- 18.4.1 Empty input → defaults.
- 18.4.2 `*` → all options.
- 18.4.3 `-` → no options.
- 18.4.4 `1,3,5` selects items 1, 3, 5.
- 18.4.5 Names accepted (`task,spec`).
- 18.4.6 Mixed numbers and names accepted (`1,spec`).
- 18.4.7 Out-of-range number re-prompts up to 3 times.
- 18.4.8 Unknown name re-prompts up to 3 times.
- 18.4.9 Duplicate input deduped (`1,1,task` → `[task]`).

### 18.5 Existing-file guard

- 18.5.1 Pre-existing `artifacts.yaml` without
  `--force` → exit 2 with the §14.2 message.
- 18.5.2 With `--force`, every existing file is overwritten and
  every missing file is written; output shows `(overwritten)` /
  `(skipped)` per file.
- 18.5.3 `--force` is per-file: a file not in the current write
  set is left alone (no destructive sweep).

### 18.6 Agent ↔ agent-kind coupling (D10)

- 18.6.1 `--agents architect --kinds task,note` → final kind
  list is `task,note,agent`; summary line says
  `(agent kind auto-included for selected agents)`.
- 18.6.2 `--agents none --kinds task` → no auto-include.
- 18.6.3 Auto-include happens once even if multiple agents are
  selected (no duplicate kind installs).

### 18.7 Conditional `advanced.yaml` content (D11)

- 18.7.1 `--template advanced --agents architect,developer` →
  emitted YAML contains `architect-queue` and `developer-queue`
  views, no others.
- 18.7.2 `--template advanced --agents none` → emitted YAML
  contains the commented stub from §6.4 verbatim, no live
  queue views.
- 18.7.3 `--template advanced --agents all` → all five queues
  emitted.

### 18.8 Dry-run

- 18.8.1 No files are written.
- 18.8.2 Output lines are prefixed `[would] ✓ <path>`.
- 18.8.3 Exit code is 0 even when the target directory has
  pre-existing files that would be skipped.

### 18.9 Error handling

- 18.9.1 Write failure on one file → others succeed → exit 1
  with the `Failures:` block.
- 18.9.2 Missing bundled template → exit 2 (simulated by
  monkeypatching the loader).
- 18.9.3 Unknown `--template` value → exit 2 before any write.
- 18.9.4 Unknown `--kinds` value → exit 2 before any write.

### 18.10 Backwards-compat

- 18.10.1 The current "refuse if `artifacts.yaml` exists" guard
  still triggers for `init` invoked without `--force`.
- 18.10.2 `--openstation-compat` creates the legacy
  `openstation -> artifacts` symlink; without it, no symlink is
  created.
- 18.10.3 Init runs without a registry (the `_pre_registry=True`
  flag still routes the args through `_run` correctly).

## 19. Cross-References

- [[t0108-spec-artifacts-init-flow-with]] — producing task.
- [[s0017-artifact-kinds-discovery-mechanism]] — kind schema +
  ARTIFACT.md contract this spec installs templates against.
- `src/artifacts_os/cli/commands/init.py` — module being
  rewritten.
- `src/artifacts_os/cli/__init__.py` — exit-code mapping and
  pre-registry routing preserved.
- `/Users/leonid/.local/share/openstation/src/openstation/init.py`
  — prior art for `_select_template`, `_install_settings_template`,
  `_get_project_name`, `_derive_project_alias`. Functions to
  port (with edits) into `commands/init.py`.
- `artifacts.yaml` — basis for `advanced.yaml`.
- `artifacts/kinds/{task,note,spec,research,agent}/{kind.json,ARTIFACT.md}`
  — sources for the bundled kind templates. `agent/ARTIFACT.md`
  is new (§7.3).
- `artifacts/agents/{architect,developer,author,researcher,technical-writer}.md`
  — sources for the bundled agent templates.

## 20. Implementation Notes

The follow-up implementation task should:

1. Land `pyproject.toml` package-data + the empty `templates/__init__.py`
   first; verify the wheel contains the templates by running
   `python -m build && unzip -l dist/*.whl | grep templates/`.
2. Copy the source files into the bundle (§7.1, §8.1) before
   touching `init.py` — keeps the existing init working until
   the rewrite lands.
3. Author `artifacts/kinds/agent/ARTIFACT.md` as part of the
   first PR (§7.3).
4. Rewrite `commands/init.py` in a single PR — partial rewrites
   risk leaving the user with a broken init.
5. Tests in §18 should be added alongside the rewrite, not
   after.
