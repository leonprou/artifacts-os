# Adding a New Artifact Kind

Artifact kinds are declarative: drop one JSON file into
`artifacts/kinds/` and the registry picks it up automatically at
vault load — no code changes required. Every `artifacts create`,
`artifacts list`, schema validation, and filter-flag generation works
immediately for the new kind.

---

## File Location and Naming

```
artifacts/kinds/<name>.json
```

The filename stem becomes the registered kind name. A file named
`bug.json` registers the kind `bug`; callers then use
`artifacts create bug ...` and `artifacts list --kind bug`.

---

## Schema Reference

`Registry._load_vault_kinds` reads the following fields from each
`artifacts/kinds/<name>.json` file:

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

## What You Get for Free

Once `artifacts/kinds/<name>.json` exists:

| Feature | Command / surface |
|---|---|
| Create artifacts | `artifacts create <name> "title"` |
| List artifacts | `artifacts list --kind <name>` |
| Schema-derived filter flags | `artifacts list --kind <name> --<property> <value>` |
| Frontmatter validation | `artifacts validate` |
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

### 1. Create the schema file

```json
// artifacts/kinds/bug.json
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

### 2. Verify the kind is registered

```bash
artifacts list --kind bug
# → empty table; no bugs yet
```

### 3. Create a bug artifact

```bash
artifacts create bug "login page crashes on empty password"
# → created: artifacts/bugs/b0001-login-page-crashes-on.md
```

### 4. Filter by schema-derived flags

```bash
# Enum-validated filter
artifacts list --kind bug --severity high

# Combine filters
artifacts list --kind bug --status open --component auth

# Check generated flags
artifacts list --kind bug --help
# → shows --status {open,triaged,fixed,wontfix}, --severity {low,...}, --component TEXT
```

### 5. Validate frontmatter

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
| [`artifacts/kinds/note.json`](../artifacts/kinds/note.json) | Numbered, free-form `type` property, date column |
| [`artifacts/kinds/agent.json`](../artifacts/kinds/agent.json) | **Non-numbered** (`x-numbered: false`), `x-required-fields` |

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

---

## Cross-References

- [`src/artifacts_os/core/README.md`](../src/artifacts_os/core/README.md) — Registry, KindDef, and validation pipeline
- [`src/artifacts_os/cli/README.md`](../src/artifacts_os/cli/README.md) — filter-flag generation rules and precedence table
- [`docs/architecture.md`](architecture.md) — module map and dependency DAG
