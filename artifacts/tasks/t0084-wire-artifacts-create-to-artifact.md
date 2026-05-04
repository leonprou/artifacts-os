---
assignee: project-manager
created: 2026-05-03
id: t0084
kind: task
name: wire-artifacts-create-to-artifact
owner: user
parent: '[[t0079-artifact-md-artifacts-ai-extension]]'
priority: normal
status: in-progress
type: feature
started: 2026-05-03
subtasks:
  - "[[t0086-implement-artifacts-create-body-loader]]"
  - "[[t0087-update-docs-adding-a-kind]]"
---

# Wire `/artifacts.create` to ARTIFACT.md Skeletons

## User story

> **As an agent (or operator) running `/artifacts.create`, I want
> the resulting artifact body pre-populated with the chosen kind's
> `ARTIFACT.md` skeleton — with placeholders filled from my prompt
> — so I don't copy boilerplate or have to remember section
> conventions per kind every time.**

This epic is the umbrella for the consumption side of
`[[t0079-artifact-md-artifacts-ai-extension]]`. t0079 shipped the
per-kind `ARTIFACT.md` skeletons; this epic wires
`/artifacts.create` to actually use them.

## Why this exists

After t0079, every registered kind exposes a hand-authored
`ARTIFACT.md` with a `description:` (selection signal), a `## How
to use` prose section, and a `## Skeleton` body template. But the
create flow doesn't consume any of it:

- `/artifacts.create` knows to call `artifacts kinds` first
  (selection signal — works), then runs `artifacts create
  <title> --kind <K>`, producing an **empty body**.
- Agents have to author the body from scratch every time, which
  reproduces the very drift `n0004` was filed to prevent
  (themes A "template floor too thin", B "type-blind
  scaffolding", H "repo-pattern crawler").

The user-visible outcome of this epic: when an agent runs
`/artifacts.create kind:task ...`, the resulting file's body is
the `task` kind's skeleton with `{{NAME}}`-style placeholders
substituted, ready for the agent to fill in real content.

## Scope (sub-tasks)

| # | Sub-task | Status | Output |
|---|----------|--------|--------|
| 1 | `[[t0085-spec-artifacts-create-consumes-artifact]]` — lock the slash-command consumption contract | review | `[[s0018-artifact-md-body-loader-for]]` |
| 2 | `[[t0086-implement-artifacts-create-body-loader]]` — update `artifacts.create.md` per s0018 | ready | updated slash command + tests |
| 3 | `[[t0087-update-docs-adding-a-kind]]` — authoring-guide touch-up for s0018 (size cap + variant block) | ready (depends on t0086) | doc change |

All three sub-tasks are now filed. Sub-task #1 produced the
locked spec [[s0018-artifact-md-body-loader-for]]; sub-tasks #2
and #3 are scoped to that spec and were filed once the spec was
ready (per the t0079 pattern). Sub-task #3 depends on #2 landing
first so the docs describe behaviour that exists.

## Open design questions (for the architect)

These are inputs to the spec, not pre-decided answers:

1. **Placeholder syntax.** Each `ARTIFACT.md` declares
   `placeholder_syntax: "{{NAME}}"` in frontmatter. Which
   placeholders does the slash command know how to substitute,
   and where do values come from (slash-command tokens like
   `name:<slug>`, frontmatter flags, free-form prompt content)?
2. **Variant selection.** `ARTIFACT.md` may declare
   `## Variants/<name>` blocks. How does the agent pick a
   variant — from `--type` flag? from a `variant:<name>` token?
   from the user's title? Falls through to the default
   `## Skeleton` if no variant matches?
3. **Fallback when no `ARTIFACT.md`.** Some kinds may not ship
   one (today: `agent`, until t0083 lands). What does the slash
   command do — empty body, error, or fallback to a generic
   skeleton?
4. **CLI / agent boundary.** n0005 D6 locks "CLI stays
   body-agnostic" — the agent reads `ARTIFACT.md`, substitutes
   placeholders, and pipes the resolved body via
   `--body-file -`. Spec must restate this so future
   refactors don't re-litigate.
5. **Token budget.** Reading every kind's `ARTIFACT.md`
   eagerly is expensive. The slash command should only load the
   chosen kind's skeleton, not the whole catalogue.
6. **n0004 carry-over themes.** Decide which n0004 themes
   close under this epic vs which spawn separate work:
   - A (template floor too thin) — closes here
   - B (type-blind scaffolding) — closes here via variant
     selection
   - H (repo-pattern crawler) — closes here (skeleton *is*
     the crawled pattern, baked once at authoring time)
   - C, D, E, F, G, I, J — likely separate workstream

## Brainstorm origins

- `[[n0004-improve-create-command]]` — original 10-theme problem
  framing for the create flow. Themes A/B/H are the targets of
  this epic.
- `[[n0005-artifact-md-kind-folders-for]]` — D6 ("CLI is
  body-agnostic; templating is agent-layer concern") is the
  load-bearing constraint.

## Relevant documentation

Sub-task agents should consult these — listed in priority order.

### Locked design (must read)

- `[[t0079-artifact-md-artifacts-ai-extension]]` — the parent
  programme. Establishes that `ARTIFACT.md` is the AI extension
  surface; this epic builds the consumer.
- `[[s0017-artifact-kinds-discovery-mechanism]]` — § 6
  (`description:` field contract), § 7 (source-file split),
  § 11 (deferred work). Read § 11.5 if the architect is
  tempted to widen scope into L2.
- `artifacts/kinds/note/ARTIFACT.md`,
  `artifacts/kinds/task/ARTIFACT.md`,
  `artifacts/kinds/spec/ARTIFACT.md`,
  `artifacts/kinds/research/ARTIFACT.md` — the four shipped
  skeletons. Spec author should use these as concrete inputs
  when designing placeholder + variant semantics.

### Existing surface (read before redesigning)

- `src/artifacts_os/ai/claude/commands/artifacts.create.md` —
  the slash command being updated.
- `src/artifacts_os/cli/commands/create.py` — the CLI it
  invokes. Body is passed via `--body` or `--body-file -`.
  Must remain body-agnostic per n0005 D6.
- `src/artifacts_os/core/kinds_catalog.py` — the L1 catalogue
  surface. Useful for resolving the `ARTIFACT.md` path for a
  chosen kind without re-implementing the loader.

### Project conventions

- [`CLAUDE.md`](../../CLAUDE.md) — naming conventions,
  atomic-write invariants, module DAG.
- [`README.md`](../../README.md) — project overview.

## Constraints

- **CLI stays body-agnostic** (n0005 D6). All template-handling
  logic lives in the slash command (agent layer). The CLI must
  not gain an "auto-load skeleton" flag.
- **L1 layer-isolation is preserved** (s0017 § 4). The slash
  command may read the chosen kind's `ARTIFACT.md` body — but
  the CLI's catalogue path (`artifacts kinds`) must not.
- **Locked decisions in n0005 (D1–D7) and s0017 (D1–D10) are
  inputs, not subjects of redesign.**

## Verification

- [ ] Sub-task #1 (architect spec) lands; spec is approved.
- [ ] Sub-task #2 (implementation) lands; running
      `/artifacts.create kind:task title:"foo"` produces a file
      whose body matches the `task` skeleton with placeholders
      substituted (or an explicit fallback when no skeleton).
- [ ] Sub-task #3 (docs touch-up) lands if the spec surfaces
      new authoring conventions; otherwise this checkbox is
      explicitly skipped with rationale.
- [ ] Reviewed and approved by user — closes the epic when all
      shipped sub-tasks are `done`.

## Progress

### 2026-05-03 12:09:15 — Coordination begin (project-manager)

- Sub-task #1 — `[[t0085-spec-artifacts-create-consumes-artifact]]`
  — already filed, status `ready`, assignee `architect`. Verified
  its scope covers all six open design questions from this epic
  (placeholder substitution, variant selection, fallback,
  CLI/agent boundary, token budget, test plan, backcompat) plus
  a LOCK / LOCK-WITH-EDIT / REJECT engagement table and explicit
  `## Goals` / `## Non-goals` (with L2/L3 named in non-goals).
- Updated the Scope (sub-tasks) table to wikilink t0085 directly
  (was inline text "filing now") so the epic surfaces the
  filed sub-task to readers and tooling.
- Sub-tasks #2 (implementation) and #3 (docs touch-up) cannot be
  filed yet — the parent task spec stipulates they are filed
  **after** t0085's spec is approved, mirroring the t0079 pattern.
- Status: `ready → in-progress`. The PM is now actively
  coordinating; next concrete action is to file sub-tasks #2
  and #3 once t0085 reaches `done` with an approved spec
  artifact attached.

**Blocker:** waiting on architect to deliver `t0085`. No further
PM action is possible on this epic until that lands.

### 2026-05-03 13:37:16 — Spec landed; sub-tasks #2 + #3 filed (project-manager)

- User signalled `t0085` spec is ready. Read the produced spec
  `[[s0018-artifact-md-body-loader-for]]` end-to-end. The spec
  locks all nine decisions (D1–D9) covering placeholder
  substitution (`{{TITLE}}` only in v1), variant selection
  precedence, empty-body fallback, CLI/slash-command boundary,
  token budget (≤ 400 lines / ≤ 8 KB skeleton cap), test plan
  (§ 11), and backcompat (D9 — `artifacts create` surface
  unchanged). Includes a full LOCK / LOCK-WITH-EDIT / REJECT
  engagement table for both n0004 and n0005 (§ 12).
- Per s0018 § 9.2, the spec explicitly directs the PM to file
  **two** sub-tasks (implementation + documentation) — the size
  cap and variant-block convention are new authoring conventions
  that warrant the docs touch-up, so #3 is in-scope (not skipped).
- Filed `[[t0086-implement-artifacts-create-body-loader]]`
  (developer, type `implementation`, status `ready`). Brief
  delegates the contract to s0018 and mirrors its § 9 / § 11
  steps; explicitly out-of-scope: L2/L3, CLI changes, new
  placeholder tokens, authoring-guide updates.
- Filed `[[t0087-update-docs-adding-a-kind]]` (technical-writer,
  type `documentation`, status `ready`, `depends_on: t0086`).
  Brief covers the three doc deltas s0018 surfaces: size cap
  (§ 8.2), `## Variants/<name>` block convention (§ 5), and
  cross-link to s0018. Depends-on ensures the doc lands after
  the implementation, mirroring the t0078 ⇢ t0076 pattern.
- Updated this epic's Scope table to wikilink all three
  sub-tasks with their current statuses.

**Next:** wait for `t0085` to transition `review → verified →
done` (user-owned), and for `t0086`/`t0087` to complete. Once
both ship, the PM transitions this epic `in-progress → review`
with a Findings + Downstream summary.