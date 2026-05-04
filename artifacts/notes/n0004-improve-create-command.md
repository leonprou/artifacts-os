---
created: 2026-05-02
id: n0004
kind: note
name: improve-create-command
type: planning
---

Captures the brainstorm about why the current create flow underspecifies
task body structure, and what to do about it. Originated from the t0053
gap (long brainstorm collapsed into a thin task body) compared against
t0050/t0051/t0052 and t0061/t0062/t0063 conventions.

## What we rely on today

### Kind schema (`artifacts/kinds/task.json`)

Defines **frontmatter only**:

```json
"properties": {
  "status": {"enum": ["backlog", "ready", "in-progress", ...]},
  "priority": {"type": "string"}
}
```

No body shape, no required sections. Schema-derived filter flags
(t0062) auto-generate from this — adding a `type` enum would make
`--type` a validated CLI flag, but body structure remains
unconstrained.

### Skills / commands inventory

`.openstation/commands/` has **multiple create variants**:

| Command | Targets | Body template |
|---|---|---|
| `openstation.create` (general) | any `--type` | Goal / Requirements / Verification — minimal |
| `openstation.create.bug` | `--type bug` | **Rich**: root-cause context, numbered reqs with file paths, preserve boundaries, mechanical verification |
| `openstation.create.note` | `kind: note` | Title + content (minimal) |
| `openstation.create.spec` | `kind: spec` artifact | Title / Design summary / Scope — note: operates on **spec artifacts**, not spec **tasks** |
| `openstation.create.agent` | `kind: agent` | (not surveyed) |
| `openstation.create.alert`, `.research` | various | (not surveyed) |

**Naming-overlap nuance:** `openstation.create.spec` materializes a
`kind: spec` artifact (what the architect runs to produce
`s00XX-....md`). This is **different** from the spec **task** that
the PM files to assign the architect. Two distinct flows share a
`spec` keyword.

### The structural gap

Type-specific commands exist by **kind** (spec artifact, note,
agent) but **not by task `type`**:

- No `openstation.create.feature` (epic)
- No `openstation.create.spec-task` (architect spec sub-task)
- No `openstation.create.impl` (developer implementation)
- No `openstation.create.doc` (technical-writer)

`bug` is the only per-task-type command. Its body template
(root-cause context → scoped reqs with file paths → preserve
boundaries → mechanical verification) is essentially the same shape
t0061/t0062/t0063 use organically.

## Convention vs skill template — observed drift

The skill template is the floor. Established practice (t0050–t0063)
consistently produces denser artifacts. Side-by-side:

| Section | Skill template | Repo convention (t0050–t0063) |
|---|---|---|
| Goal / User Story | yes | yes (User Story for epic; Goal for sub-tasks) |
| Authoritative Spec callout | — | yes (epic feature tasks) |
| Sub-tasks list | — | yes (epic feature tasks) |
| Tech Requirements (from sNNNN) | — | yes (epic — references the spec; sub-tasks lift requirements) |
| Context (with sub-headers) | — | **yes — load-bearing** |
| Touch points table (files + line refs) | — | yes (impl, doc) |
| 'Do not re-litigate' framing | — | yes (sub-tasks of epic) |
| Requirements | yes | yes |
| Verification | yes | yes (often executable CLI invocations) |
| Primary References footer | — | yes |

## Context section — the load-bearing pattern

Recent good tasks open with `## Context` containing 4–7 sub-headers.

**t0062 (impl)** — 5 sub-headers:
- `### Why this task is backlog` — names blockers + ready conditions
- `### What lands in this task` — high-level scope
- `### Touch points (per sNNNN)` — files + line refs
- `### Test matrix (per sNNNN)` — copies cases from spec
- `### References` — wikilink list

**t0063 (doc)** — 7 sub-headers:
- `### Source of truth: <code path>` — file/line refs with table
- `### Existing shipped <X>` — current state
- `### <Adjacent system> generation` — context dependencies
- `### Validation pipeline` — how related code works
- `### Naming conventions` — relevant constraint
- `### Existing docs structure` — where new doc fits
- `### Constraint reminder (from CLAUDE.md)` — guardrails

**t0053 (initial draft I produced — too thin):** had only Goal +
Requirements + Verification. After feedback, I added 4 Context
sub-headers but still missed Touch points and Primary References.

## Themes (problems → fixes)

### A. Template floor too thin
Skill produces `Goal/Requirements/Verification`. Convention is
`Context (sub-headers) + Tech Requirements + Verification + Primary
References`. Skill output is below repo norm by default.

### B. Type-blind scaffolding
Epic features, spec sub-tasks, impl sub-tasks, and doc tasks have
distinctly different section shapes. Skill doesn't differentiate.

### C. Brainstorm-to-task transcription is lossy
Long brainstorming converges in chat; skill collapses it into bullet
section headings. Decisions-already-locked, code refs, rationale all
disappear unless manually transcribed. **This is what bit t0053.**

### D. Verification depth varies
Skill produces 'checklist items derived from requirements' — often
just restated requirements. Recent good tasks ship verification as
**executable** items: `artifacts list --kind task --status invalid
exits with parse-time error` is testable cold; the prose version
isn't.

### E. Round 1 output format is freeform
Skill says 'present a complete draft' without prescribing order.
Different invocations produce different shapes.

### F. 'Do not re-litigate' framing absent
Recent sub-tasks consistently include this guardrail. Skill should
suggest it for sub-tasks of a parent epic.

### G. Touch points table is high-value
t0062's file+line-ref table is more actionable than prose. Skill
could prompt: 'list every file the assignee will read or modify.'

### H. Repo-pattern crawler
Skill could read 2 most recent same-type tasks before drafting and
mimic their structure. Cheap, eliminates drift.

### I. Sub-task creation flow is verbose
Each sub-task = separate `openstation create` with 30-line body
heredoc. Could be cleaner with a multi-task draft + batch create.

### J. Status defaults per type unspecified
- Spec sub-task → `ready` (architect can start immediately)
- Impl sub-task → `backlog` (depends on spec)
- Epic feature → `backlog` until spec lands
Skill says 'backlog or ready' without typing.

## Possible designs

### Design 1: per-type template bodies inside the existing skill

Extend `openstation.create` to switch body scaffolding on `--type`.
No new commands. Single entry point. Each branch encodes its own
Context sub-headers / Touch points / Authoritative Spec callout
pattern.

**Pros:** Single discovery surface; no naming collisions.
**Cons:** One large skill file with N branches; each branch grows.

### Design 2: per-type create commands (mirrors `bug` pattern)

Add `openstation.create.feature`, `.spec-task`, `.impl`, `.doc`
alongside the existing `bug` command. General `openstation.create`
becomes a router: dispatch on `--type` to the specialized command.

**Pros:** Files match the existing `bug` precedent; each command
stays small; per-type specialization is local.
**Cons:** More files to maintain; potential for drift between
commands; `spec` overload (artifact-spec vs spec-task) needs
explicit naming (e.g. `spec-task` to disambiguate).

### Design 3: declarative templates in artifacts

Body templates as files under `artifacts/templates/<type>.md.tpl`,
loaded by the skill at draft time. Skill stays generic; templates
are data.

**Pros:** Templates live alongside the conventions they encode;
editable without touching the skill; could even be kind-extension
data in `artifacts/kinds/task.json` as `x-body-template`.
**Cons:** Adds a new abstraction; templates need a substitution
language (placeholders for spec ID, parent ref, etc.); harder to
encode conditional logic ('only if epic, include sub-tasks list').

### Design 4: hybrid — skill encodes flow, kind schema declares shape

`task.json` adds `x-body-sections` per `type`:

```json
"properties": {
  "type": {
    "enum": ["feature", "spec", "implementation", "documentation", "bug"],
    "x-body-sections": {
      "feature": ["User Story", "Authoritative Spec", "Sub-tasks", "Tech Requirements", "Verification"],
      "spec": ["Goal", "Context", "Requirements (spec must cover)", "Verification", "Primary References"],
      "implementation": ["Goal", "Context", "Requirements", "Verification", "Primary References"],
      "documentation": ["Context (codebase research)", "Requirements", "Verification"]
    }
  }
}
```

Skill reads schema, generates section skeleton with placeholders.

**Pros:** Convention lives where validation lives (kind schema is
single source of truth); skill stays small; per-vault customization
possible.
**Cons:** Schema gets opinionated about body, not just frontmatter;
section headings as data is a low-value abstraction unless
sub-section guidance comes with it.

## Priorities (impact × effort)

1. **C (brainstorm-to-task)** — fixes the recurring problem. Highest
   value, low effort: a 'first transcribe convergence into Context'
   instruction in the skill.
2. **B (type-aware templates)** — second highest value. Real
   artifact: 4 short type-specific scaffolds.
3. **A + F + G** — bundle into B's templates: Context with
   sub-headers, 'do not re-litigate' framing, touch points table.
4. **D (executable verification)** — high value for impl tasks.
5. **H, I, J** — quality-of-life, file later.

## Open questions

- **Design choice (1/2/3/4):** which of the four designs above
  matches the project's preference for code-vs-data separation?
- **Spec-task naming:** `spec` already overloaded (artifact kind
  vs task type). Use `spec-task` or `design` to disambiguate?
- **Migration:** existing tasks (t0050–t0063) follow convention but
  weren't generated from a template. Do we backfill, or only apply
  to new tasks?
- **Brainstorm-to-note pre-step:** when the create comes after long
  context, should the skill produce a note (`nNNNN`) and let the
  task reference it (the n0003 → t0050 pattern), rather than
  cramming everything into the task body?

## References

- Existing create variants: `.openstation/commands/openstation.create*.md`
- Convention exemplars: t0050–t0052 (programmatic CLI access),
  t0061–t0063 (schema-derived filter flags + docs)
- Counter-example (thin draft, post-fix): t0053-spec-core-unified-filter-api
- Bug template (existing rich pattern):
  `.openstation/commands/openstation.create.bug.md`
- Decomposition heuristics: `docs/decomposition.md`
- Naming conventions: `CLAUDE.md` ('Naming Conventions')