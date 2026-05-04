# Adding a New Artifact Kind

Artifact kinds are declarative: add a kind definition under
`artifacts/kinds/` and the registry picks it up automatically at
vault load — no code changes required. Every `artifacts create`,
`artifacts list`, schema validation, and filter-flag generation works
immediately for the new kind.

For creating an *instance* of an existing kind, see
[`creating-an-artifact.md`](creating-an-artifact.md).

---

## File Layout

A kind can be defined in two forms:

**Legacy flat form:**

```
artifacts/kinds/<name>.json
```

**Folder form (preferred for new kinds):**

```
artifacts/kinds/<name>/
  kind.json      # machine-readable JSON Schema
  ARTIFACT.md    # human/agent-facing prose (selection signal + body template)
```

The registry loads both; **folder form takes precedence** when both
exist (a warning is logged). The filename stem (`<name>`) becomes the
registered kind name in both cases.

---

## `ARTIFACT.md` — Selection Signal and Body Template

`ARTIFACT.md` is the human and agent-facing entry point for a kind.
Its **frontmatter** carries the L1 selection signal consumed by
`artifacts kinds`; its **body** is a body-authoring guide the agent
layer loads when drafting a new artifact.

### Required body section: `## What is a <kind>?`

Every `ARTIFACT.md` body **must** open with a `## What is a <kind>?`
section that gives a clear, concise, kind-level definition: what the
artifact captures, when to reach for it, and (if applicable) the
conventional sub-types or variants. This is the only mandatory body
section — everything that follows (authoring steps, worked example
references) is optional and depends on whether the kind needs
structural scaffolding.

The definition is what an agent or human reads first when opening
the file; it is also what gets quoted when the kind is referenced
elsewhere. Keep it general enough to apply to **every** instance of
the kind, not just a specific sub-type.

The note (`artifacts/kinds/note/ARTIFACT.md`), research
(`artifacts/kinds/research/ARTIFACT.md`), and spec
(`artifacts/kinds/spec/ARTIFACT.md`) kinds are the v1 exemplars.
For the full body-shape contract see
[`## ARTIFACT.md body authoring guidelines`](#artifactmd-body-authoring-guidelines)
below.

### `description:` field contract

The `description` field is the **sole L1 selection signal** — the
one line agents and humans read when deciding which kind to use.

| Property | Rule |
|---|---|
| Required | yes — missing or empty triggers a registration warning |
| Length | ≤ 1024 characters |
| Voice | third-person ("Captures planning notes…", not "I capture…") |
| Content | encodes both **what** the kind is **and when** to choose it |
| Forbidden | XML tags (`<…>`); reserved words `anthropic` and `claude` |
| Format | plain string; no markdown formatting |

Voice is guidance, not a registration gate — it is documented here
and caught in authoring review, not blocked at load time (see
s0017 D6).

**Validation outcomes:**

| Condition | Outcome |
|---|---|
| `description` absent or empty | warning logged; kind still listed with `description=None` |
| `description` > 1024 chars | hard error; kind registration fails |
| `description` contains XML tag | hard error; kind registration fails |
| `description` contains reserved word | hard error; kind registration fails |
| first-person voice | not enforced mechanically — guidance only |

**Worked example — `artifacts/kinds/note/ARTIFACT.md`:**

```yaml
---
name: note
description: Captures thinking at a point in time — planning, decisions, brainstorms, meetings, or scratch work. Use when context (decisions, trade-offs, references) must outlive the conversation that produced it.
applies_to: note
placeholder_syntax: "{{NAME}}"
schema_version: 1
---
```

This description covers *what* ("captures thinking at a point in
time — planning, decisions, brainstorms, …") and *when* ("use when
context … must outlive the conversation that produced it"). Both
halves must be present.

### Anti-patterns (from r0002 § 8)

| Anti-pattern | Why it breaks |
|---|---|
| Vague description ("Helps with documents") | Agent cannot distinguish this kind from others; silently skipped |
| First-person voice ("I capture planning notes…") | Discovery fails — description must be third-person |
| Time-sensitive or version-pinned text | Description rots; no mechanism to catch stale text at load time |
| XML tags in description | Hard registration error |
| Too many equal choices in `## Skeleton` without a default | Produces inconsistent artifact bodies run-to-run |
| Deeply nested file references (ARTIFACT.md → A → B) | Risk of partial reads; one level deep from `ARTIFACT.md` is the limit |

### Full `ARTIFACT.md` frontmatter schema

L1 reads only `description` and the file's existence (`has_template`).
Other fields are reserved for L2/L3 surfaces (per-kind detail and
template content, both deferred — see s0017 § 11).

| Field | Type | Required | L1 reads? | Notes |
|---|---|---|---|---|
| `name` | string | yes | — | Must match the kind name; mismatch → hard error |
| `applies_to` | string | yes | — | Must match the kind name; mismatch → hard error |
| `description` | string | yes (warning if missing) | **yes** | Contract above |
| `placeholder_syntax` | string | no | — | Reserved for L2 |
| `schema_version` | int | no | — | Reserved for L2 |
| `variant_field` | string | no | — | Reserved for L2 |
| `variants` | list[string] | no | — | Reserved for L2 |
| `playbooks` | list[string] | no | — | Reserved for L2 |

---

## `ARTIFACT.md` body authoring guidelines

The `note`, `research`, and `spec` kinds are the v1 exemplars. The
patterns below crystallise from iterating on all three. Apply them
when authoring or reviewing any new `ARTIFACT.md` body.

### 1. Body shape — three sections

Every `ARTIFACT.md` body follows the same three-section spine:

```
# <Kind>

## What is a <kind>?
  → 1–2 paragraph definition + selection table   (the only REQUIRED body section)

## How to draft a <kind>
  → preamble + 2–3 numbered steps
  → writing-discipline step(s) first
  → anchored-required-sections step last
```

Drop a step if it does not apply; do not pad to fill three.

### 2. Definition — lead with a differentiating verb

`## What is a <kind>?` is the only mandatory body section. The lead
sentence uses a verb that immediately distinguishes the kind from
adjacent ones:

| Kind | Lead verb |
|---|---|
| note | "Captures thinking at a point in time…" |
| research | "Captures cited findings from an investigation…" |
| spec | "Locks a technical contract before implementation…" |
| bug | "Tracks a confirmed defect…" |

Name the kind's **load-bearing property** in one phrase (note:
*fidelity* of transcription; research: *traceability* of every
claim; spec: *decision-locking* with explicit rationale). Then
include a selection table that helps the author choose this kind
over adjacent options — either sub-variants within the kind
(note's `type` table) or signals against a sibling kind (research's
"research vs. note" table; spec's "when to file a spec vs. a task
or note" table).

### 3. Frontmatter description — mirror the body in 1–2 sentences

The frontmatter `description` is the L1 selection signal — agents
read it without opening the body. Mirror the body's discriminator
using the reliable pattern:

> *\<verb\> \<what\>. Use when \<selection trigger\>.*

Both halves must be present. Worked examples are in the
`### description: field contract` section above.

### 4. Anchor required sections; do not inline skeletons

When the kind demands specific sections (research's TL;DR,
Recommendations, Sources), name them in a final "anchor" step with
a one-line role for each. **Do not inline a `{{TOKEN}}`-style
skeleton** — it biases the author toward filling slots rather than
writing for a future reader. A 60–80 line `ARTIFACT.md` beats a
300-line one.

A skeleton may still earn its place for kinds with truly rigid
structure (e.g., a release-notes kind whose every section is
fixed). Default to the guide-style; reach for a skeleton only when
the structure genuinely cannot be expressed as anchored sections.

### 5. Cite worked examples in the vault

Point at real artifacts (`[[r0001-...]]`, `[[r0002-...]]`,
`[[n0005-...]]`) for any shape the body references. Real examples
expose the kind under realistic constraints; invented examples
drift. The `note` and `research` `ARTIFACT.md` files cite `r0001`,
`r0002`, and `n0005` for exactly this reason.

### Body anti-patterns

| Anti-pattern | Why it breaks |
|---|---|
| `{{TOKEN}}`-heavy skeleton | Author fills slots instead of writing for the reader; structure ossifies. |
| Description = "Body template for X artifacts" | Passive; no discriminator verb; no "when". |
| Definition buried under Step 1 | An agent has to read authoring steps to find what the kind *is*. |
| More than 3 numbered steps | Usually a signal the body is doing too much. Collapse writing disciplines or required sections. |
| Required sections mentioned only inside a skeleton | Without a separate anchor step, the requirement is invisible to anyone scanning. |
| Invented examples instead of vault-cited ones | Drifts from reality; vault-cited examples stay honest as the project evolves. |

---

## `kind.json` — Schema Reference

`Registry._load_vault_kinds` reads the following fields from each
`kind.json` file:

| Field | Required | Default | `KindDef` field | Notes |
|---|---|---|---|---|
| `x-dir` | **yes** | — | `dir` | Subdirectory under `artifacts/` where files are stored. Raises `ValidationError` if absent. |
| `x-prefix` | no | `""` | `prefix` | ID prefix for numbered kinds (e.g. `"t"` → `t0001`). Empty string disables the prefix. |
| `x-numbered` | no | `true` | `numbered` | `true` → `{prefix}{NNNN}-{slug}.md`; `false` → `{slug}.md`. |
| `x-columns` | no | none | `meta["columns"]` | Default column list shown by `artifacts list`. |
| `x-status-colors` | no | none | `meta["status_colors"]` | Rich rendering hints, keyed by status value. |
| `x-required-fields` | no | none | `required_fields` | Frontmatter fields required at create time. |
| `properties.status.enum` | no | `[]` | `statuses` | Allowed status values; validated by `validate_one`. |
| `properties.*` | no | — | `schema` | Full JSON Schema stored verbatim; drives validation and filter-flag generation. |

The full schema object is stored on `KindDef.schema` and used for
JSON Schema validation (requires `jsonschema`; skipped silently if
unavailable).

---

## L1 Catalogue Surface

After the L1 implementation (t0076), `artifacts kinds` shows a
`description` column drawn from each kind's `ARTIFACT.md`:

```
$ artifacts kinds
┏━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ name     ┃ dir      ┃ prefix ┃ numbered ┃ statuses      ┃ description                       ┃
┡━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ note     │ notes    │ n      │ yes      │ (none)        │ Captures thinking at a point…     │
│ task     │ tasks    │ t      │ yes      │ backlog, …    │ (no description)                  │
└──────────┴──────────┴────────┴──────────┴───────────────┴───────────────────────────────────┘
```

Kinds without an `ARTIFACT.md` (or without a `description` field)
appear as `(no description)`. The description is truncated at 60
characters in the table; the full string is available via `-j`.

**JSON output** (`artifacts kinds -j`) gains two keys per kind:

```json
{
  "name": "note",
  "dir": "notes",
  "prefix": "n",
  "numbered": true,
  "statuses": [],
  "description": "Captures thinking at a point in time — planning, decisions, brainstorms, meetings, or scratch work. Use when context (decisions, trade-offs, references) must outlive the conversation that produced it.",
  "has_template": true
}
```

`has_template` is `true` iff `ARTIFACT.md` exists on disk for that
kind. It signals that body scaffolding is available; it does not
guarantee the `description` field is populated.

**Quiet mode** (`artifacts kinds -q`) is unchanged — one name per
line, no description column.

> **Note — `/artifacts.kinds` slash command retired.** Agents that
> previously invoked `/artifacts.kinds` to list registered kinds should
> call `artifacts kinds` directly. The slash command was a thin
> passthrough whose prompt body added ~100+ tokens per invocation with
> no behavioural gain (s0017 D10, § 11.6). The CLI is the only
> agent-facing surface for kind discovery.

---

## Evaluation-First Authoring (r0002 R8)

Before writing extensive `ARTIFACT.md` content, **build representative
test scenarios first**:

1. **Identify two or three real creation tasks** for the new kind —
   not hypothetical ones. What would an agent actually create?
2. **Draft the skeleton** and use it to produce sample artifacts for
   those tasks.
3. **Evaluate consistency.** Does the skeleton produce similar
   structures across different tasks of the same kind? Does the
   `description` allow an agent to distinguish this kind from adjacent
   ones?
4. **Iterate** the `description` text against those real selection
   use-cases before freezing it.
5. **Freeze the template** only once the skeleton produces consistent
   bodies and the description survives selection tests.

This mirrors the Anthropic Skills authoring loop (r0002 § 6): build
test scenarios before, not after, writing extensive documentation.
Templates authored without evaluation tend to be over-long, offer
too many equal choices without a default, or fail to distinguish the
kind from adjacent ones at selection time.

---

## What You Get for Free

Once `artifacts/kinds/<name>.json` (or `artifacts/kinds/<name>/kind.json`)
exists:

| Feature | Command / surface |
|---|---|
| Create artifacts | `artifacts create <name> "title"` |
| List artifacts | `artifacts list --kind <name>` |
| Schema-derived filter flags | `artifacts list --kind <name> --<property> <value>` |
| Frontmatter validation | `artifacts validate` |
| L1 catalogue entry | `artifacts kinds` (includes `description` column if `ARTIFACT.md` is present) |
| View targeting | `artifacts list --view <named-view>` (if configured) |

---

## Filter-Flag Generation

When `--kind <name>` is supplied, `artifacts list` auto-generates a
`--<property>` flag for every entry under `properties` in the kind's
JSON schema:

- **`enum` array** → flag enforces `choices=` at parse time (typos
  are immediate errors).
- **`type: string`** → free-form `TEXT` flag.
- **`type: integer`** → parsed as `int`.

Flags that collide with static flags (`--kind`, `--filter`, `--view`,
`--fields`, `--meta`, `--quiet`, `--json`, `--children`, `--parent`)
are silently skipped; use `--filter k=v` to reach those fields.

For the full generation rules and precedence table see
[`src/artifacts_os/cli/README.md`](../src/artifacts_os/cli/README.md)
§ "Schema-derived filter flags".

---

## Numbered vs Non-Numbered Kinds

**Numbered** (default, `x-numbered: true`): each artifact gets a
sequential four-digit ID. Filename: `{prefix}{NNNN}-{slug}.md`;
frontmatter `id: t0042`, `name: fix-bug`. Use for artifacts that
accumulate over time and need a stable opaque ID (tasks, specs,
research notes).

**Non-numbered** (`x-numbered: false`): the slug *is* the identity.
Filename: `{slug}.md`; frontmatter `id: researcher`,
`name: researcher`. Use for singleton-style registries where the
name is the natural key (agents, configuration stubs). Set
`x-prefix: ""` (or omit `x-prefix`) when `x-numbered: false`.

See `CLAUDE.md` § "Naming Conventions" for slug rules (lowercase,
hyphenated, max 5 words).

---

## Worked Example — Adding a `bug` Kind

### 1. Create the kind folder

```
artifacts/kinds/bug/
  kind.json
  ARTIFACT.md
```

### 2. `kind.json`

```json
{
  "x-dir": "bugs",
  "x-prefix": "b",
  "x-numbered": true,
  "x-columns": ["id", "name", "status", "severity"],
  "x-status-colors": {
    "open":     "red",
    "triaged":  "yellow",
    "fixed":    "green",
    "wontfix":  "dim strike"
  },
  "title": "Bug",
  "type": "object",
  "properties": {
    "status": {
      "enum": ["open", "triaged", "fixed", "wontfix"],
      "description": "Bug lifecycle stage."
    },
    "severity": {
      "enum": ["low", "medium", "high", "critical"],
      "description": "Impact severity. Closed enum for consistent filtering."
    },
    "component": {
      "type": "string",
      "description": "Affected component or module (free-form)."
    }
  }
}
```

### 3. `ARTIFACT.md` frontmatter

```yaml
---
name: bug
description: Tracks a confirmed defect with root-cause context and a reproduction path. Use when a failure mode is understood well enough to scope a fix.
applies_to: bug
schema_version: 1
---
```

Note the description: *what* ("tracks a confirmed defect…") + *when*
("when a failure mode is understood…"). Both halves present.

### 4. Verify the kind is registered

```bash
artifacts kinds
# → bug row appears with description column
```

### 5. Create a bug artifact

```bash
artifacts create bug "login page crashes on empty password"
# → created: artifacts/bugs/b0001-login-page-crashes-on.md
```

### 6. Filter by schema-derived flags

```bash
# Enum-validated filter
artifacts list --kind bug --severity high

# Combine filters
artifacts list --kind bug --status open --component auth

# Check generated flags
artifacts list --kind bug --help
# → shows --status {open,triaged,fixed,wontfix}, --severity {low,...}, --component TEXT
```

### 7. Validate frontmatter

```bash
artifacts validate
# → reports missing required fields or unknown status values
```

---

## Reference Templates

The five shipped schemas cover the most common patterns:

| Schema | Pattern demonstrated |
|---|---|
| [`artifacts/kinds/task.json`](../artifacts/kinds/task.json) | Numbered, multi-status lifecycle, `x-columns`, `x-status-colors`, mixed enum + string properties |
| [`artifacts/kinds/spec.json`](../artifacts/kinds/spec.json) | Numbered, status colors, `agent` free-form string property |
| [`artifacts/kinds/research.json`](../artifacts/kinds/research.json) | Numbered, minimal two-status enum |
| [`artifacts/kinds/note.json`](../artifacts/kinds/note.json) | Numbered, free-form `type` property, date column; has `artifacts/kinds/note/ARTIFACT.md` (the v1 exemplar) |
| [`artifacts/kinds/agent.json`](../artifacts/kinds/agent.json) | **Non-numbered** (`x-numbered: false`), `x-required-fields` |

`note` is the only shipped kind with an `ARTIFACT.md` today. The
others will gain templates as their body conventions stabilise
(tracked under the parent epic t0079).

---

## Optional Follow-Up

**Named views.** Once a kind exists you can add named views for it
in `artifacts/artifacts.yaml` (pre-configured filters, columns, sort
order). See
[`src/artifacts_os/views/README.md`](../src/artifacts_os/views/README.md).

**Status-transition logic.** `properties.status.enum` is validation
only — it tells `artifacts-os` which values are legal. Lifecycle
transitions (who may move an artifact from one status to another) are
the concern of the host application (e.g., OpenStation), not
`artifacts-os`. Do not encode transition rules inside a kind schema.

**Per-kind `ARTIFACT.md`.** Only `note` ships a body template today.
Add an `ARTIFACT.md` to a kind's folder when agents need body
scaffolding for that kind. Follow the evaluation-first model above
before writing extensive template content.

---

## Cross-References

- [`src/artifacts_os/core/README.md`](../src/artifacts_os/core/README.md) — Registry, KindDef, KindCatalog, and validation pipeline
- [`src/artifacts_os/cli/README.md`](../src/artifacts_os/cli/README.md) — filter-flag generation rules and precedence table
- [`docs/architecture.md`](architecture.md) — module map and dependency DAG
- s0017 (`s0017-artifact-kinds-discovery-mechanism`) — L1 catalogue spec: locked decisions D1–D10, description contract, validation rules, CLI surface
- r0002 (`r0002-claude-skills-design-reference`) — Claude Skills design reference; source of the description contract and evaluation-first authoring model
- n0004 (`n0004-improve-create-command`) — original problem framing (10 themes, 4 designs) that motivated the kind-folder and description work
- n0005 (`n0005-artifact-md-kind-folders-for`) — locked decisions D1–D7 for the kind folder layout and `ARTIFACT.md` format
- t0076 (`t0076-implement-l1-kinds-catalogue-s0017`) — implementation task that landed the L1 catalogue (`description` column, `-j` keys, loader compatibility, `/artifacts.kinds` retirement)
