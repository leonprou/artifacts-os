---
name: spec
description: Locks an implementation contract before code — architecture, components, data models, surfaces, and file structure — concretely enough that an implementer builds from it and a reviewer approves it. Use when a change crosses a module boundary, lands across multiple tasks, or pins a public surface.
---

# Spec

## What is a spec?

A **spec** is a design document that locks an *implementation
contract* before code begins. It describes what is being built —
the architecture, the components, the data models, the surfaces
those imply, and the file structure they land in — concretely
enough that an implementer builds from it without re-deriving the
design and a reviewer approves it before any code is written. Its
load-bearing property is **buildability**: the anchors the
skeleton privileges are the ones that get re-read during
implementation and six months later.

Reach for a spec when at least one signal holds:

| Signal | Why a spec |
|---|---|
| The change crosses a module boundary in the dependency DAG | The architecture diagram and `## Surfaces` pin the contract each module sees. |
| Implementation will land across multiple tasks | The approved spec is the shared north star the sub-tasks build against. |
| A public surface (CLI, API, TUI, agent) is added or changed | `## Surfaces` pins signatures and shapes before a PR locks them in. |
| New data shapes are introduced, or a persisted/serialized shape changes | `## Data Models` freezes the schema implementers and reviewers depend on. |
| A new module or non-trivial file layout lands | `## File Structure` shows where the code goes before it sprawls. |

If none holds, prefer a `task` (mechanical change, bounded by its
own Requirements) or a `note` (`type: decision` locks a rationale
with no surface to design).

A spec has no fixed skeleton. A handful of anchors are **always
required** because they are what the implementer and reviewer
re-read; the implementation surfaces are **conditional** —
required when the change touches them, absent otherwise;
everything else is optional.

| Section | Required / when to add |
|---|---|
| One-paragraph summary | **Required.** Directly under the title — what is being built and why, in prose. Carries the goal; there is no `## Goals`. |
| `## Out of Scope` | **Required.** What the spec does *not* take responsibility for — the implementer's authoritative answer when scope creep arrives. May be a single bullet. |
| `## Architecture` | **Required, with a diagram.** How the pieces fit, anchored by a diagram (see Step 1). Prose-only is not acceptable. |
| `## Components` | **Conditional — multi-component.** Summary table + per-component contract when the change spans 2+ interacting components or modules. |
| `## Data Models` | **Conditional — shapes change.** Field-level shape of any new or changed structure (frontmatter schema, dataclass, JSON/event payload, persisted form). |
| `## Surfaces` | **Conditional — public surface touched.** Per CLI / API / TUI / agent surface added or changed: signatures, input/output shapes, backwards-compat impact. |
| `## File Structure` | **Conditional — new module or non-trivial layout.** The files and directories created or moved, and what each holds. |
| `## Test Plan` | **Required.** Grouped by the property each test verifies; the implementation task pulls this section verbatim into its work plan. |
| `## Cross-References` | **Required.** Every artifact and code path the spec consumes or affects, as bare wikilinks (`[[s0014-...]]`) or paths. Load-bearing for vault navigation — link, never copy. |
| `## Decisions` | Optional, high-level. Headline calls only (see Step 3). A `D1/D2` table with per-decision justification belongs only in a genuinely contested-design spec (`s0014`). Default: omit. |
| `## Build Sequence` | Optional. Dependency order when components must land in sequence. |
| `## Migration` | Optional. Upgrade path from the prior state, when one exists. |

## How to draft a spec

`s0023-multi-value-filters` is the worked example of the default
shape. `s0001-artifacts-os-ai-module` is the minimal early-era
shape (Purpose / Public API / Key Concepts / Scope Boundary).
`s0014-core-unified-filter-api` is the rare contested-design spec
that earns a full `## Decisions` table.

### Step 1 — Lead with the architecture and its diagram

Open with the one-paragraph summary, then `## Architecture`. The
section must carry a **diagram** — it is the single
highest-bandwidth artefact a spec ships.

- **ASCII boxes-and-arrows is the default.** Zero tooling, renders
  everywhere, diffs cleanly. Most specs need nothing more.
- **Mermaid is allowed** when the structure genuinely needs it; it
  renders in GitHub and Obsidian.
- **A committed image is allowed** for diagrams impractical as
  text.
- **Prose-only is not acceptable.** A three-box sketch carries
  more than a paragraph.

Use H3 sub-sections (`### Runtime Flow`, `### Data Flow`,
`### Invariants`) when one diagram is not enough.

### Step 2 — Pin only the surfaces the change touches

`## Components`, `## Data Models`, `## Surfaces`, and
`## File Structure` are conditional — include each only when its
trigger fires:

| Section | Include when | Skip when |
|---|---|---|
| `## Components` | The change spans 2+ components/modules that interact. Lead with a `# \| Component \| Location \| Purpose` table, then a per-component contract (inputs, outputs, constraints). | A single-file, single-component change. |
| `## Data Models` | A new data shape is introduced, or a persisted/serialized one changes (frontmatter schema, dataclass, JSON/event payload). | Pure behavioural changes that touch no shape. |
| `## Surfaces` | A public surface is added or changed — a CLI verb/flag, a Python public API, a TUI view, an agent-facing contract. Pin signatures, I/O shapes, and compat impact per surface. | Internal-only refactors. |
| `## File Structure` | A new module/package lands, or files move non-trivially. | Editing existing files in place. |

When genuinely unsure, include the section — a one-line "n/a:
single-file change" is cheaper than a reviewer guessing.

### Step 3 — Keep Out of Scope honest; decisions are the exception

`## Out of Scope` is the implementation task's authoritative
answer when scope creep arrives mid-work. Keep it current; if the
spec grows past what one reviewer can hold, descope into Out of
Scope (and a follow-up spec) *before* review, not after.

`## Decisions` is optional and high-level by default. Capture the
headline calls as bullets only when they are not already obvious
from the architecture. Reach for a numbered `D1/D2` table with
per-decision justification subsections **only** when the spec is
genuinely choosing between reasonable alternatives a reviewer must
adjudicate (`s0014`). Most specs lock a contract rather than
contest a design — those carry no `## Decisions` section at all.

Set `status: draft` on creation; advance to `review` after a
self-check, `approved` after reviewer sign-off, `deprecated` if
superseded. Implementation tasks must wait for `approved`. If
implementation reveals a flaw, amend the spec — never let code
drift from the approved contract.

## Skeleton

```markdown
# {{TITLE}}

{{ONE_PARAGRAPH_SUMMARY}}

## Out of Scope

## Architecture

<!-- Required: an ASCII / mermaid / image diagram, not prose. -->

<!-- Add the conditional sections the change touches (see ARTIFACT.md):
     ## Components, ## Data Models, ## Surfaces, ## File Structure. -->

## Test Plan

## Cross-References
```
