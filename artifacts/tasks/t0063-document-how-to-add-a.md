---
kind: task
id: t0063
name: document-how-to-add-a
type: documentation
status: done
assignee: technical-writer
owner: user
created: 2026-05-02
started: 2026-05-02
completed: 2026-05-04
---

# Document How To Add A New Artifact Kind — User Manual Page In

## Context (codebase research)

This task is grounded in the following findings from inspecting the
current code, schemas, and docs. Treat these as authoritative starting
points and verify them again during writing.

### Source of truth: `Registry._load_vault_kinds`

Implemented at `src/artifacts_os/core/registry.py:48-89`. The registry
walks `artifacts/kinds/*.json` on init and constructs one `KindDef`
per file. Behavior observed in the loader:

| Schema field read | KindDef field | Notes |
|---|---|---|
| `path.stem` | `name` | Filename stem becomes the kind name. |
| `x-dir` | `dir` | **Required** — raises `ValidationError` if missing. |
| `x-prefix` (default `""`) | `prefix` | ID prefix for numbered kinds. |
| `x-numbered` (default `True`) | `numbered` | Toggles numbered vs slug-only filenames. |
| `properties.status.enum` (default `[]`) | `statuses` | Status validation list. |
| `x-columns` (optional) | `meta["columns"]` | Default list columns. |
| `x-status-colors` (optional) | `meta["status_colors"]` | Rich rendering hints. |
| `x-required-fields` (optional) | `required_fields` | Frontmatter required at create-time. |
| `<full schema>` | `schema` | Stored verbatim for JSON Schema validation. |

### Registry merge semantics

`Registry.__init__(kinds=[...], root=...)` first installs
caller-provided `KindDef`s, then loads vault JSONs from
`<root>/artifacts/kinds/*.json` and **silently overrides** any
same-named caller kind. Two caller kinds with the same name raise
`ValueError: duplicate kind '<name>' in Registry kinds list`. See
`registry.py:14-28` and `src/artifacts_os/core/README.md:133-145`.
Implication: dropping a JSON file is sufficient for end-users;
programmatic callers can still ship defaults.

### Existing shipped schemas (`artifacts/kinds/`)

Five schemas exist as templates:

- `task.json` — numbered (`x-prefix: t`), full status lifecycle
  (8 statuses), mix of enum + free-form string properties (status,
  priority, assignee, owner, type), demonstrates `x-columns` and
  `x-status-colors`.
- `agent.json`, `note.json`, `research.json`, `spec.json` —
  additional patterns including non-numbered variants where
  `name` is the identity (per `CLAUDE.md` 'Naming Conventions').

The doc's worked example should pick a kind name **not** already
shipped (e.g., `bug`) so a reader copy-pasting hits no conflict.

### Filter-flag generation (from t0062 / s0015)

`src/artifacts_os/cli/commands/list.py` plus `cli/__init__.py`
auto-generate `--<key>` flags from each kind's `properties.*` at
`artifacts list` time. Enums → `choices=`; strings → free-form;
`description` → `--help` text. Reserved flag names (`--kind`,
`--fields`, `--view`, `--quiet`, `--json`, `--filter`) are
silently skipped on collision. The doc should reference this surface
but defer detail to `src/artifacts_os/cli/README.md` (the
'Schema-derived filter flags' section, lines 120-174 at time of
research).

### Validation pipeline

`validate_one` order (`src/artifacts_os/core/README.md:174-176`):
`kind` present and registered → required fields present → status
in allowed set → ID format → JSON Schema constraints → unknown
fields (warnings). Schema validation requires `jsonschema`;
skipped silently if unavailable.

### Naming conventions (`CLAUDE.md` 'Naming Conventions')

Relevant for the numbered vs non-numbered subsection:

- Numbered: filename `{prefix}{NNNN}-{slug}.md`; frontmatter
  `id: t0042`, `name: fix-bug`.
- Non-numbered: filename `{slug}.md`; frontmatter
  `id: researcher`, `name: researcher`.
- Slugs: lowercase, hyphenated, max 5 words.

### Existing docs structure

`docs/` currently contains `architecture.md`, `settings.md`, and
`docs/plans/*`. There is no `docs/guides/` directory. Adding a
single sibling file (`docs/adding-a-kind.md`) is consistent with
current layout; creating `docs/guides/` for one doc is premature.

### Constraint reminder (from `CLAUDE.md`)

'No lifecycle logic in `cli` (status transitions stay in
OpenStation).' The doc should explicitly note that beyond
`properties.status.enum` (validation only), status-transition logic
is **not** part of artifact-kind definition.

## Requirements

1. New file `docs/adding-a-kind.md` titled 'Adding a New Artifact Kind'.
2. **Overview** — one paragraph: kinds are declarative; one JSON file
   in `artifacts/kinds/`, no code changes, registry picks it up at
   vault load.
3. **File location & naming** — `artifacts/kinds/<name>.json` defines
   kind `<name>`; filename stem is the registered name.
4. **Schema reference table** — document every `x-*` extension and
   standard JSON Schema field consumed by
   `Registry._load_vault_kinds`. Must match the table in the
   Context section above.
5. **What you get for free** — `artifacts create <kind>`,
   `artifacts list --kind <kind>`, schema-derived filter flags,
   validation, view targeting.
6. **Worked example** — complete walkthrough adding a `bug` kind (or
   similar **not** already in `artifacts/kinds/`), with the JSON
   file and CLI commands showing it works (`artifacts create bug
   'title'`, `artifacts list --kind bug --severity high`). Include
   at least one enum and one free-form string property.
7. **Filter-flag generation rules** — short subsection: each
   `properties.*` becomes `--<key>`; enums → `choices`; strings
   → free-form. Defer detail to `src/artifacts_os/cli/README.md`
   via link.
8. **Numbered vs non-numbered kinds** — when to set
   `x-numbered: false` (e.g., agents). Reference `CLAUDE.md`
   'Naming Conventions'.
9. **Reference templates** — table or list pointing to all five
   shipped schemas with one-line descriptions of the pattern each
   demonstrates.
10. **Optional follow-up** — kinds can be exposed via named views in
    `artifacts/artifacts.yaml` (link to views README);
    status-transition / lifecycle logic lives in OpenStation, not
    artifacts-os.
11. **Cross-references** — links to:
    - `src/artifacts_os/core/README.md` (Registry, KindDef, validation)
    - `src/artifacts_os/cli/README.md` (filter flags)
    - `docs/architecture.md` (module map)
12. Doc passes markdown lint; no broken internal links; renders cleanly.

## Findings

Created `docs/adding-a-kind.md` — a complete user guide for adding
new artifact kinds. Covers: declarative-kind overview, file location
and naming, schema reference table (all `x-*` extensions and
`properties.status.enum` read by `Registry._load_vault_kinds`), what
CLI surfaces are unlocked for free, a filter-flag generation summary
(linked to `src/artifacts_os/cli/README.md`), numbered vs
non-numbered kind guidance, worked example with a `bug` kind (not
in the shipped set), reference template table for all five shipped
schemas, and optional follow-up notes on named views and lifecycle
separation.

Also updated:
- `docs/architecture.md` — added `adding-a-kind.md` to the
  Cross-References section.
- `README.md` — added row to `## Documentation` → Guides table.

All internal links verified against actual repo paths.

## Progress

### 2026-05-02 — technical-writer
> time: 10:10

Wrote docs/adding-a-kind.md covering all 11 requirements (overview, schema reference table, what you get for free, filter-flag generation, numbered vs non-numbered, worked example with bug kind, reference templates, optional follow-up, cross-references). Updated docs/architecture.md cross-references and README.md Documentation index. All link targets verified.

## Verification

- [ ] `docs/adding-a-kind.md` exists with all sections in
      requirements 2–11.
- [ ] Schema reference table matches the fields read by
      `Registry._load_vault_kinds` (verify against current
      `src/artifacts_os/core/registry.py`).
- [ ] Worked example uses a kind that does **not** already exist in
      `artifacts/kinds/`.
- [ ] All cross-reference links resolve to real paths in the repo.
- [ ] At least one shipped kind schema (e.g., `task.json`) is
      referenced as a template.
- [ ] Filter-flag generation section links to
      `src/artifacts_os/cli/README.md` rather than duplicating its
      content.
- [ ] `docs/architecture.md` updated (or new doc is added to its
      index) so the guide is discoverable.
- [ ] Reviewed and verified by user.
