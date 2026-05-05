---
assignee: project-manager
created: 2026-05-02
id: t0079
kind: task
name: artifact-md-artifacts-ai-extension
owner: user
priority: normal
started: 2026-05-04
status: done
type: feature
---

# ARTIFACT.md — Artifacts AI Extension

## User story

> **As an agent (or operator) creating an artifact, I want a single
> per-kind extension surface — `ARTIFACT.md` — that tells me what
> the kind is for, how to draft its body, and how to pick the right
> kind in the first place, without paying the full cost on every
> invocation.**

This epic is the umbrella for that surface. Discovery, body
scaffolding, slash-command integration, and per-kind template
rollout all sit under it.

## Why this exists

`artifacts-os`'s schema layer (`kind.json`) is machine-readable but
prose-thin. Agents creating artifacts have no canonical place to learn:

- which kind fits the user's intent (selection signal),
- how to shape the body for a given kind (template + variants),
- which playbooks apply to a given variant.

Today the gap is filled ad-hoc by slash commands that guess, ask the
user, or punt to raw schema dumps. The result is inconsistent
artifact bodies, duplicated guidance, and high token cost when an
agent has to load every kind's full context just to make a choice.

`ARTIFACT.md` is the AI-extension layer that closes the gap. It
lives next to `kind.json` under `artifacts/kinds/<name>/` and carries
the human/agent-facing contract: a `description:` selection signal,
a `## How to use` prose section, a `## Skeleton` body template, and
optional `## Variants/<name>` blocks plus declared `playbooks/`.
The first slice — the L1 catalogue — keeps the always-on cost cheap
by exposing only `name + description + has_template` per kind.
Deeper layers may follow; this epic ships L1 and the per-kind
authoring work that fills the catalogue.

## Scope (sub-tasks)

The work below ships the epic. Each item is a separate task; this
parent is where overall progress and goal alignment lives.

| # | Sub-task | Status | Output |
|---|----------|--------|--------|
| 1 | `[[t0074-research-claude-skills-design-for]]` — research Claude Skills as a reference architecture | done | `[[r0002-claude-skills-design-reference]]` |
| 2 | `[[t0073-spec-artifact-kinds-discovery-mechanism]]` — spec the L1 discovery surface | done | `[[s0017-artifact-kinds-discovery-mechanism]]` (approved) |
| 3 | `[[t0076-implement-l1-kinds-catalogue-s0017]]` — implement L1 (`description` field, catalogue, `artifacts kinds` extension, retire `/artifacts.kinds` slash command) | done | `core/kinds_catalog.py`, CLI extension, tests per s0017 § 9 |
| 4 | `[[t0078-update-docs-adding-a-kind]]` — update authoring guide for `description:` contract and L1 catalogue | done | `docs/adding-a-kind.md` updated |
| 5 | `[[t0080-author-artifact-md-for-task]]` — author `kinds/task/ARTIFACT.md` | ready | populated catalogue row for `task` |
| 6 | `[[t0081-author-artifact-md-for-spec]]` — author `kinds/spec/ARTIFACT.md` | ready | populated catalogue row for `spec` |
| 7 | `[[t0082-author-artifact-md-for-research]]` — author `kinds/research/ARTIFACT.md` | ready | populated catalogue row for `research` |
| 8 | `[[t0083-author-artifact-md-for-agent]]` — author `kinds/agent/ARTIFACT.md` | ready | populated catalogue row for `agent` |
| 9 | `[[t0084-wire-artifacts-create-to-artifact]]` — wire `/artifacts.create` to consume `ARTIFACT.md` skeletons (mini-epic; spec sub-task `t0085` filed) | backlog | spec + impl + (optional) docs |

Future sub-tasks expected under this epic (not yet filed):

- **Authoring lints / template validators** — reserved; out of
  scope until at least three kinds have hand-authored
  `ARTIFACT.md` files and patterns stabilise. Sub-tasks 5–8 land
  this precondition.

## Brainstorm origins

- `[[n0004-improve-create-command]]` — original 10-theme problem
  framing for the create flow.
- `[[n0005-artifact-md-kind-folders-for]]` — locked decisions D1–D7
  on the per-kind folder layout, `ARTIFACT.md` schema, playbooks
  contract, and naming.

## Relevant documentation

Sub-task agents should read these before drafting. Listed in
priority order — start at the top and stop when you have enough
to draft.

### Authoring guide — start here

- [`docs/adding-a-kind.md`](../../docs/adding-a-kind.md) — **the
  canonical reference for sub-tasks #5–#8.** Updated by t0078
  (now `done`) to cover the `description:` field contract
  (required, ≤ 1024 chars, third-person, what+when), validation
  outcomes, anti-patterns from r0002 § 8, L1 catalogue surface,
  the evaluation-first authoring loop (write a description →
  test selection against real tasks → iterate), folder-form
  layout (`<kind>/kind.json` + `<kind>/ARTIFACT.md`), and a
  worked example. If you only read one doc, read this.

### Worked example

- `[[artifacts/kinds/note/ARTIFACT.md]]` — the v1 exemplar on
  disk. Sub-tasks #5–#8 reproduce its shape per-kind:
  frontmatter (`name`, `description`, `applies_to`,
  `placeholder_syntax`, `schema_version`) → `## How to use this
  template` prose → `## Skeleton` body template. Lift the
  structure verbatim; only the content changes per kind.

### Locked design (consult for contract questions)

- `[[s0017-artifact-kinds-discovery-mechanism]]` — the L1 spec.
  Authoring tasks rarely need this; read § 6 if you have a
  question about the `description:` contract that
  `docs/adding-a-kind.md` doesn't answer. § 11 is deferred work —
  do **not** widen scope into it.
- `[[r0002-claude-skills-design-reference]]` — original
  research. Most of its guidance is already distilled into
  `docs/adding-a-kind.md`; consult § 8 (anti-patterns) or § 6
  (evaluation-first authoring) only if you want the full
  reasoning.

### Project conventions

- [`CLAUDE.md`](../../CLAUDE.md) — coding style, naming
  conventions (filename / id / slug rules), atomic-write
  invariants, module DAG (`core → views → cli, tui`;
  `core → log → ai`). Sub-tasks introducing new files or APIs
  must honour these.
- [`README.md`](../../README.md) — project overview and the
  current public API surface.

### Architecture (only if touching code)

- [`docs/architecture.md`](../../docs/architecture.md) — module
  layout, dependency DAG, public-API re-export rules.
- [`docs/settings.md`](../../docs/settings.md) — base
  `Settings` + `from_base` extension pattern. Not load-bearing
  for per-kind authoring tasks.

### Module READMEs (only if touching that module)

- [`src/artifacts_os/core/README.md`](../../src/artifacts_os/core/README.md)
  — registry, store, frontmatter, validate. L1 catalogue
  (`KindCatalog`) lives here.
- [`src/artifacts_os/cli/README.md`](../../src/artifacts_os/cli/README.md)
  — argument parsing, kind-aware flags, output modes (`-q`,
  `-j`). `artifacts kinds` extension lives here.
- [`src/artifacts_os/ai/README.md`](../../src/artifacts_os/ai/README.md)
  — slash-command install / list / uninstall.
- [`src/artifacts_os/views/README.md`](../../src/artifacts_os/views/README.md)
  — table rendering, column specs, status colour mapping.

### Code touch-points (per sub-task)

- `artifacts/kinds/<name>/ARTIFACT.md` — the file each authoring
  sub-task creates (#5 → `task`, #6 → `spec`, #7 → `research`,
  #8 → `agent`).
- `src/artifacts_os/core/registry.py` — `_load_vault_kinds`,
  `_read_artifact_md_frontmatter`, `_validate_description`. Read
  only if you hit a loader question.
- `src/artifacts_os/core/kinds_catalog.py` — `KindCatalog` /
  `KindCatalogEntry`. The shipped L1 surface; sub-tasks #5–#8
  see their work surface here.
- `src/artifacts_os/cli/commands/kinds.py` — `artifacts kinds`
  CLI implementation.

## Constraints

- **CLI stays body-agnostic.** The CLI may surface paths to
  `ARTIFACT.md` and playbook files, but never reads or prints
  their body content. Body-template handling is an agent-layer
  concern (n0005 D6).
- **L1 layer-isolation is non-negotiable.** L1 invocations must
  never transitively read `ARTIFACT.md` body content or any
  `playbooks/*.md` file. Only `kind.json` and the **frontmatter**
  of `ARTIFACT.md` are touched. The layer-isolation invariant is
  the load-bearing claim of s0017 § 4 / § 9.1.
- **Locked decisions in n0005 (D1–D7) and s0017 (D1–D10) are
  inputs, not subjects of redesign.** Sub-tasks may extend them;
  they may not silently revisit them.

## Verification

- [x] Sub-task #3 (L1 implementation) lands and the in-repo vault
      ships a `description:` field for at least the `note` kind.
- [x] `artifacts kinds` table includes a `description` column;
      `-j` JSON includes `description` and `has_template` keys.
- [x] `/artifacts.kinds` slash command retired (s0017 § 11.6).
- [x] Sub-task #4 (docs) lands; `docs/adding-a-kind.md` describes
      the `description:` contract and the L1 catalogue.
- [ ] Sub-tasks #5–#8 land: every kind (`task`, `spec`, `research`,
      `agent`) has a hand-authored `ARTIFACT.md` so the L1
      catalogue ships with no `(no description)` rows.
- [ ] Sub-task #9 (`[[t0084-wire-artifacts-create-to-artifact]]`)
      lands: `/artifacts.create` consumes the per-kind skeleton
      and produces pre-populated bodies. Closes the consumer
      side of this surface.
- [ ] Reviewed and approved by user — closes the epic when all
      shipped sub-tasks are `done` and remaining work is captured
      in the backlog.

## Verification Report

*Verified: 2026-05-04*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | L1 implementation lands; vault ships `description:` for at least `note` | PASS | `t0076` is `done`; `artifacts kinds -j` returns a non-null `description` for `note` (and for `research`, `spec`, `task`). |
| 2 | `artifacts kinds` table has `description` column; `-j` JSON includes `description` and `has_template` | PASS | Table output shows a `description` column; JSON output includes `"description"` and `"has_template"` keys for every kind. |
| 3 | `/artifacts.kinds` slash command retired (s0017 § 11.6) | PASS | `git log --diff-filter=D` confirms `src/artifacts_os/ai/claude/commands/artifacts.kinds.md` was deleted; only a stale dangling symlink remains under `.openstation/commands/`. |
| 4 | `docs/adding-a-kind.md` describes `description:` contract and L1 catalogue | PASS | File exists at `docs/adding-a-kind.md`; covers folder form (`<kind>/kind.json` + `<kind>/ARTIFACT.md`), `description` contract, and L1 catalogue surface (8 references). |
| 5 | Sub-tasks #5–#8 land: every kind (`task`, `spec`, `research`, `agent`) has a hand-authored `ARTIFACT.md` | FAIL | `t0080`, `t0081`, `t0082` are `done`, but `t0083` (`agent` ARTIFACT.md) is still `ready`. `artifacts/kinds/agent/` does not exist; the L1 catalogue prints `(no description)` for the `agent` row. |
| 6 | Sub-task #9 (`t0084-wire-artifacts-create-to-artifact`) lands | FAIL | `t0084` is `in-progress`, not `done`. Its sub-tasks `t0086` and `t0087` are not yet complete. |
| 7 | Reviewed and approved by user | FAIL | The epic itself is still in `review`; user approval has not been recorded. |

### Summary

4 passed, 3 failed. The L1 catalogue surface and docs (items 1–4) are shipped, but the remaining authoring work (`agent` kind), the consumer wiring (`/artifacts.create` integration), and final user sign-off are still outstanding — the epic cannot close yet.

### What Needs Fixing

- Land `t0083` (`author-artifact-md-for-agent`) so `artifacts/kinds/agent/ARTIFACT.md` exists and the L1 catalogue no longer prints `(no description)` for the `agent` row.
- Drive `t0084` (`wire-artifacts-create-to-artifact`) and its sub-tasks (`t0086`, `t0087`) to `done`.
- Re-submit this epic for user approval once items 5 and 6 are satisfied.