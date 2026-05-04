---
created: 2026-05-02
id: n0005
kind: note
name: artifact-md-kind-folders-for
type: planning
---

Captures the 2026-05-02 brainstorm with the user on redesigning the
/artifacts.create slash command so body content is scaffolded per-kind.
Designed to give a future task all the context needed to act without
re-running the brainstorm.

## Origin

Session 2026-05-02. Started from `What's the process of creating an
artifact?` → discovered `created` is auto-filled in CLI but not core
(spawned `t0066-improve-date-handling-in-artifact`) → comparison of
`openstation create` vs `artifacts create` (layered: workflow wrapper
vs schema primitive) → user asked to brainstorm the
`/artifacts.create` slash command. Builds directly on
`n0004-improve-create-command` (problem framing — Themes A "template
floor too thin", B "type-blind scaffolding", C "brainstorm-to-task
lossy transcription").

## Problem statement

The `/artifacts.create` slash command (defined in
`src/artifacts_os/ai/claude/commands/artifacts.create.md`) handles
the **header** (frontmatter) very well: kind-aware flags are
auto-generated from `artifacts/kinds/<name>.json` schemas (Variant A
filter + Variant B augment, see `cli/commands/create.py`). The
**body**, however, is unstructured — `--body "<TEXT>"` and that's
it. AI agents drafting bodies produce inconsistent shapes
run-to-run, and recent good tasks (t0050–t0063) follow conventions
the slash command doesn't encode.

n0004 already enumerated 10 themes and 4 design options. This
brainstorm picked a specific path through them.

## Decisions (from the brainstorm)

### D1 — Redesign target: `/artifacts.create`, not `/openstation.create`

Brainstorm scoped to the artifacts-os layer slash command. OpenStation
wrapper is a separate concern. (Q1 → option b.)

### D2 — Scope: body only, header is fine

Header is schema-driven and works. Body is the open problem.
(Q2 → option a.)

### D3 — Storage: per-kind folder; `kinds/` → `types/`

```
artifacts/types/task/
  kind.json       <- schema (was artifacts/kinds/task.json)
  ARTIFACT.md     <- body template for this kind
```

Instances stay where they are (`artifacts/tasks/t0066-foo.md`); only
the kinds-directory restructures. (Q5 → Reading 1.)

User's framing: "artifacts looking like skills in claude code" —
artifacts will accumulate more responsibility (markdown + scripts)
over time; the kind folder pattern positions us for that.

### D4 — File names: `kind.json` and `ARTIFACT.md` (uppercase)

`ARTIFACT.md` mirrors `SKILL.md` convention (claude code). Uppercase
flags it as the canonical entry point of the kind directory.

### D5 — Self-sufficient with optional companions

`ARTIFACT.md` is comprehensive by default; can reference sibling
files (`templates/<type>.md`, `scripts/`, etc.) when a kind genuinely
needs sub-structure. For task in particular the user judged that the
six task types (feature/implementation/spec/documentation/research/
refactor) are similar enough that a single `ARTIFACT.md` suffices —
no `templates/` subdirectory in v1. (Q6 → between options a and c,
landing on "single file by default, escape hatch when needed".)

### D6 — AI-only consumption; CLI stays body-agnostic

`/artifacts.create` (slash command) reads `ARTIFACT.md` and uses it
to scaffold the body. The `artifacts` CLI does NOT auto-load any
template — body is whatever is passed via `--body` / `--body-file`.

Rationale: matches the existing layering (CLI = schema-driven
primitive; agent layer = workflow-aware), and matches the SKILL.md
analogy (no CLI ever reads SKILL.md). (Q7 → option a.)

### D7 — `ARTIFACT.md` format: hybrid (frontmatter + guidance + skeleton)

```markdown
---
name: task
description: Body template for task artifacts.
---
## How to use this template
<prose for the AI: type-specific notes, when to add sections,
 brainstorm-to-task transcription guidance, cross-references>

## Skeleton
<literal markdown the AI emits, with {{placeholder}} markers>
```

Two sections: the `## How to use` prose handles per-context and
per-type variations (n0004 Themes B/C); the `## Skeleton` keeps the
floor consistent (n0004 Theme A). (Q8 → option c.)

## Open questions

### Q9 — V1 scope (NOT YET DECIDED)

Two foundational changes are now coupled:

1. Directory restructure (`artifacts/kinds/<name>.json` →
   `artifacts/types/<name>/kind.json`) — touches `core/registry.py`,
   `_load_vault_kinds`, every test that builds a vault, and migrates
   the in-repo vault. Breaking change for anyone with a vault.
2. `ARTIFACT.md` authoring + slash-command read path — write the
   template files, update `/artifacts.create` to read them, define
   placeholder convention.

Options offered:
- **(a)** Both, single shot — rename + ship task `ARTIFACT.md`.
- **(b)** Restructure only (templates v2).
- **(c)** Templates only (skip rename — drop `ARTIFACT.md` next to
  the existing `*.json`).
- **(d, recommended)** Rename all kinds + ship `ARTIFACT.md` for
  `task` only; other kinds get folderified with no template until
  needed.

The conversation pivoted to creating this note before Q9 was
answered. The follow-up task should re-pose Q9 to the user before
breaking ground.

### Other deferred questions
- Placeholder convention — `{{title}}` vs `${title}` vs comment-based
  hints. Not discussed.
- Migration mechanics — hard cutover vs registry tries-both-paths.
  Not discussed (D6 implies hard cutover is acceptable but not
  decided).
- Other kinds' templates — v1 punts; the trigger to add `ARTIFACT.md`
  for `spec`, `note`, `research`, `agent` is each kind's own
  convention drift.

## Affected code (touch points for the implementing task)

| Surface | File | Change |
|---|---|---|
| Kind registry | `src/artifacts_os/core/registry.py` (`_load_vault_kinds`) | Read from `artifacts/types/<name>/kind.json` instead of `artifacts/kinds/<name>.json` |
| In-repo vault | `artifacts/kinds/*.json` | Move 5 files to `artifacts/types/<name>/kind.json` |
| Tests | `tests/core/` and `make_vault` fixture | Update vault layout fixtures |
| Documentation | `docs/adding-a-kind.md` | Update file paths + introduce `ARTIFACT.md` section |
| Slash command | `src/artifacts_os/ai/claude/commands/artifacts.create.md` | Add "Read ARTIFACT.md if present" step + body scaffolding behavior |
| Template | `artifacts/types/task/ARTIFACT.md` | NEW — author the hybrid-format template per D7 |

## Suggested decomposition (if scope d is chosen)

1. **Spec task (architect)** — write `s00XX-artifact-md-kind-folders.md`
   formalizing decisions D1–D7, defining placeholder convention,
   migration plan, and `ARTIFACT.md` schema (frontmatter fields +
   section structure).
2. **Implementation: registry + migration (developer)** — rename
   `kinds/` → `types/<name>/`, update `_load_vault_kinds`, move the
   5 in-repo schemas, update tests.
3. **Implementation: task ARTIFACT.md (architect or technical-writer)** —
   author `artifacts/types/task/ARTIFACT.md` per the spec.
4. **Implementation: slash command update (author)** — extend
   `artifacts.create.md` to read `ARTIFACT.md` and apply the skeleton
   when scaffolding new artifacts; document placeholder substitution.
5. **Documentation (technical-writer)** — update
   `docs/adding-a-kind.md` to reflect the new structure and
   introduce the `ARTIFACT.md` concept.

## Cross-references

- `n0004-improve-create-command` — original problem framing (10 themes, 4 designs)
- `t0066-improve-date-handling-in-artifact` — sibling backlog item from same session
- `src/artifacts_os/ai/claude/commands/artifacts.create.md` — current slash command
- `src/artifacts_os/cli/commands/create.py` — CLI create implementation
- `src/artifacts_os/core/registry.py` — `_load_vault_kinds` (rename target)
- `docs/adding-a-kind.md` — current kind-authoring guide
- `artifacts/kinds/task.json` — task schema (declares the type enum)
- Existing rich-template precedent: `.openstation/commands/openstation.create.bug.md`
- SKILL.md reference: `~/.claude/plugins/.../skills/brainstorming/SKILL.md`

## How to act on this note

The natural next step is option (d) from Q9: a small epic with
sub-tasks per the decomposition above. Before spawning sub-tasks,
confirm Q9 with the user — they may pick (a), (b), or (c) instead.
Do not re-litigate D1–D7; those are decided.