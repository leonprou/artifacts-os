---
kind: spec
name: note-spec
---

# Note Specification

Defines the format for planning notes in Open Station. A note is a
free-form markdown document used for roadmaps, release plans,
architectural decisions, and other durable planning artifacts that
live beyond a single task.

For task format see `docs/task.spec.md`.

## File Location

Notes live permanently in `openstation/notes/`:

```
openstation/notes/<name>.md
```

Notes are created here once and never move.

## Naming

Two naming patterns are used depending on the note's lifespan:

- **Evergreen** — plain `kebab-slug` for long-lived notes not tied
  to a specific task (e.g., `roadmap.md`, `release-v0200.md`). Use
  this for notes that will be updated over time.
- **Numbered** — `NNNN-kebab-slug` for notes tied to a task or event,
  auto-assigned by `openstation create --kind note`. The ID counter
  is per-kind (`openstation/notes/` only).

The filename (without `.md`) and the `name` frontmatter field must
match exactly.

Never pick NNNN IDs manually — use `openstation create --kind note`.

> **CLI note:** `openstation create --kind note` **always** assigns a
> `NNNN-` prefix. There is no flag to create an evergreen (plain-slug)
> note via the CLI. To create an evergreen note (e.g. `roadmap.md`),
> create the file directly in `openstation/notes/` with the correct
> frontmatter — the CLI is not involved.

## Frontmatter Schema

```yaml
---
kind: note                  # Required. Always "note".
name: roadmap               # Required. Matches filename (without .md).
status: active              # Optional. See Status Values below.
created: YYYY-MM-DD         # Optional. Date the note was created.
agent: author               # Optional. Agent that created this note.
task: "[[NNNN-task-slug]]"  # Optional. Producing task (wikilink), if any.
aliases: []                 # Optional. Obsidian aliases for vault linking.
tags: []                    # Optional. Topic tags for discovery.
---
```

### Field Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `kind` | string | yes | — | Always `note` |
| `name` | string | yes | — | Kebab-case slug, matches filename (without `.md`) |
| `status` | enum | no | `active` | Current state. See Status Values below. |
| `created` | date | no | — | ISO 8601 date (`YYYY-MM-DD`) when the note was created |
| `agent` | string | no | empty | Agent that created this note (provenance). Use `manual` for human-authored notes. |
| `task` | string | no | empty | Wikilink to the task that produced this note (`"[[NNNN-slug]]"`), if applicable |
| `aliases` | list | no | `[]` | Obsidian aliases for vault linking |
| `tags` | list | no | `[]` | Topic tags for discovery and filtering |

### Status Values

| Value | Meaning |
|-------|---------|
| `active` | Note is current and in use |
| `planning` | Note is being drafted or not yet in effect |
| `archived` | Note is superseded or no longer relevant |

## Body Structure

Notes are free-form by design — there is no mandatory section
structure. Use whatever organization serves the content. Below
are common patterns.

### Opening Summary (recommended)

A short paragraph describing what the note covers and its purpose.

### `## Planned` / `## Committed` / `## Done` (for roadmaps)

Group items by readiness. Each item links to the relevant task or
note via a wikilink.

```markdown
## Planned

- [[release-v0210]] — next release (logging improvements)

## Done

- [[release-v0200]] — task completion & failure handling
```

### `## <Section>` (free-form)

Any organization that aids readability. Common patterns:
- Numbered lists for ordered steps or milestones
- Tables for comparisons or multi-column data
- Checklists (`- [ ]`) for tracking progress within the note

### Update Log (optional)

For notes that track ongoing activity, append timestamped update
entries at the bottom:

```markdown
## Update — 2026-04-07
- Promoted release plan to committed
```

## Provenance

Notes produced by agents should declare provenance in frontmatter:

```yaml
agent: author                          # Which agent created this
task: "[[0044-write-release-notes]]"   # Which task (wikilink), if applicable
```

Use `agent: manual` and omit `task` for manually created notes.

## Progressive Disclosure

Notes start minimal and grow as planning matures.

### Stages

| Stage | Frontmatter | Body |
|-------|-------------|------|
| **Draft** | `kind`, `name`, `status: planning` | Opening summary, rough content |
| **Active** | `status: active`, + `created`, `tags` if useful | Structured sections |
| **Archived** | `status: archived` | No further edits needed |

### Rules

1. **Start with the minimum** — `kind`, `name`, and a rough body.
   Add status and dates as the note stabilizes.
2. **Prefer updating over creating** — evergreen notes like roadmaps
   are meant to be edited in place. Only create new notes for
   distinct planning artifacts.
3. **Archive, don't delete** — set `status: archived` when a note is
   superseded; keep it as historical record.

## Example

### Evergreen roadmap note

```markdown
---
kind: note
name: roadmap
status: active
tags:
  - planning
---

# Roadmap

Prioritized list of planned work grouped by theme.

## Planned

- [[release-v0210]] — logging improvements (P0)
- [[release-v0220]] — agent analytics (P1)

## Done

- [[release-v0200]] — task completion & failure handling
```

### Release plan note

```markdown
---
kind: note
name: release-v0200
status: planning
created: 2026-04-09
---

# Release v0.20.0 — Task Completion & Failure Handling

Goal: agents reliably close out work on both the happy path and
the failure path.

## Committed

- [ ] [[0375-agent-task-close-out-self]] — unified close-out epic

## Done

*(moved here when shipped)*
```
