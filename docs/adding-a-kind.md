# Adding a New Artifact Kind

Artifact kinds are declarative: add a kind definition under
`artifacts/kinds/` and the registry picks it up automatically at
vault load — no code changes required. Every `artifacts create`,
`artifacts list`, schema validation, and filter-flag generation works
immediately for the new kind.

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
`artifacts kinds`; its **body** (`## How to use` + `## Skeleton`
sections) is a body template the agent layer loads when drafting a
new artifact.

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
description: Body template for note artifacts — planning notes, brainstorm captures, meeting notes, decisions, and scratch work.
applies_to: note
placeholder_syntax: "{{NAME}}"
schema_version: 1
---
```

This description covers *what* ("body template for note artifacts")
and *when* ("planning notes, brainstorm captures, …"). Both halves
must be present.

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
│ note     │ notes    │ n      │ yes      │ (none)        │ Body template for note artifa…    │
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
  "description": "Body template for note artifacts — planning notes, brainstorm captures, meeting notes, decisions, and scratch work.",
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
