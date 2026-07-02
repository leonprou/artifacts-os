---
created: 2026-06-11
id: t0204
kind: task
name: core-discover-reverse-lookup-field
owner: user
priority: medium
status: backlog
type: feature
---

# core.discover: reverse_lookup(field, target) inverse-dependency query

## Why

Filed from openstation (spec ref: open-station
`s2068-openstation-module-system` § 13.1). Consumers need
"what links here" queries (e.g. which tasks `depends_on` X) and
currently must scan the full corpus. A generic inverse lookup
enables `show --blocks/--blocked-by` style features in any
downstream.

## Requirements

- `core.discover.reverse_lookup(reg, field, target)` returns all
  artifacts whose frontmatter `field` contains a reference
  (wikilink or plain id/name) to `target`.
- Handles list-valued fields (`depends_on`, `subtasks`) and scalar
  fields (`parent`).

## Verification

- [ ] Unit test: task A depends_on B → `reverse_lookup(reg,
      "depends_on", B)` returns A.
- [ ] Wikilink and bare-name reference forms both match.
