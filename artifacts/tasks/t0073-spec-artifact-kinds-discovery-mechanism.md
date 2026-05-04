---
artifacts:
- '[[artifacts/specs/s0017-artifact-kinds-discovery-mechanism]]'
assignee: architect
created: 2026-05-02
id: t0073
kind: task
name: spec-artifact-kinds-discovery-mechanism
owner: user
parent: '[[t0079-artifact-md-artifacts-ai-extension]]'
started: 2026-05-02
status: done
type: spec
---

# Spec Artifact Kinds Discovery Mechanism

## Goal

Produce a spec under `artifacts/specs/` for an artifact-kind
**discovery mechanism**. The mechanism's primary use case is helping
an agent (or human) **choose the right kind when creating a new
artifact** — and surface the per-kind detail needed to scaffold the
body without paying the full cost on every invocation.

The spec must apply **progressive disclosure** so the discovery
surface stays cheap when uninvoked and rich when needed.

Implementation is **not** in scope — a follow-up task will be filed
once this spec is approved.

## Context

### Use case (user-level)

When creating an artifact, the operator-or-agent asks: "what kind
should this be, and what shape should its body take?" Today the
flow is friction-heavy:

- The `/artifacts.create` slash command may guess the kind, ask the
  user, or punt to `/artifacts.kinds` and read raw output.
- There is no canonical place to learn what each kind is *for*
  beyond the kind's JSON schema (machine-readable, prose-thin).
- Per-kind body templates (`ARTIFACT.md`) are starting to land
  (see `artifacts/kinds/note/ARTIFACT.md`), but no surface exposes
  their existence or content programmatically.

A discovery mechanism closes the gap: a single, layered surface
that answers "what kinds exist?", "which one fits my intent?", and
"how do I draft its body?" without forcing every consumer to load
everything every time.

### Already-locked context (do NOT re-litigate)

- **Per-kind folder layout.** `artifacts/kinds/<kind>/` contains
  `kind.json` (schema; possibly still at `artifacts/kinds/<kind>.json`
  during transition), `ARTIFACT.md` (body template), and optional
  `playbooks/<variant>.md` files. See `artifacts/kinds/note/ARTIFACT.md`
  for the v1 exemplar.
- **`ARTIFACT.md` schema.** Frontmatter (`name`, `applies_to`,
  `variant_field?`, `variants?`, `playbooks?`, `placeholder_syntax`,
  `schema_version`) + `## How to use` prose + `## Skeleton` or
  `## Variants/<name>` blocks.
- **Playbooks contract.** Lazy load, declared explicitly in
  `ARTIFACT.md` frontmatter `playbooks:` list, missing-but-declared
  files are an error.
- **Naming.** `kinds/` (not `types/`) — vocabulary collision avoided.
- **CLI stays body-agnostic.** Body templates are an agent-layer
  concern; the CLI may surface paths but never reads `ARTIFACT.md`
  content.

### Consumers the mechanism must serve

- `/artifacts.create` slash command — the primary consumer; uses
  discovery to scaffold body from the right `ARTIFACT.md` + variant.
- `/artifacts.kinds` slash command — already exists; should evolve
  to expose richer per-kind detail.
- Future TUI browser — needs the same surface to render kind picker
  views.
- Humans reading the repo — `docs/adding-a-kind.md` should
  cross-reference the discovery surface.

### Progressive disclosure as design constraint

The spec must define a layered model:

| Layer | Loaded when | Carries |
|---|---|---|
| L1 | Always (e.g. when listing kinds) | Names, one-line descriptions |
| L2 | When focusing on one kind | Paths, variants, playbook list, schema summary |
| L3 | When actually using the kind | `ARTIFACT.md` content + playbook content |

The spec must specify what triggers each layer, what content lives
where, and how consumers traverse them.

### References

- **`[[r0002-claude-skills-design-reference]]` — primary reference.**
  Read this first. Its `## Recommendations for t0073` section lists
  eight directional inputs (`description:` field contract, L1/L2/L3
  trigger semantics, one-deep nesting rule, `variants` divergence,
  schema/description split, fallback semantics, evaluation-first
  authoring) the architect must either adopt and lock, or explicitly
  reject with rationale. Treat the recommendations as **starting
  positions, not decisions** — the spec locks them.
- `artifacts/kinds/note/ARTIFACT.md` — v1 `ARTIFACT.md` exemplar.
- `src/artifacts_os/ai/claude/commands/artifacts.create.md` —
  current create slash command (does NOT yet load templates).
- `src/artifacts_os/ai/claude/commands/artifacts.kinds.md` —
  current kinds slash command.
- `src/artifacts_os/core/registry.py` — `_load_vault_kinds`,
  the only existing path-walking helper.
- `docs/adding-a-kind.md` — current authoring guide (will need
  cross-referencing once discovery lands).
- `[[n0004-improve-create-command]]`,
  `[[n0005-artifact-md-kind-folders-for]]` — brainstorm origins.

## Scope (revised during execution)

Original brief covered the full L1 / L2 / L3 progressive-disclosure
mechanism plus `/artifacts.create` slash-command integration. Two
user-driven scope reductions narrowed the deliverable:

1. **Revision 2 (descope to L1).** "simplify to only the L1 in spec,
   L2 spec can be removed nearly all. just keep it in high level in
   next steps section." → s0017 locks L1 only; L2 (per-kind detail),
   L3 (template / playbook content), and `/artifacts.create`
   integration appear in § 11 "Next Steps" at sketch level only.
2. **Revision 3 (retire `/artifacts.kinds` slash command).**
   "instead calling claude artifacts.kinds (line 73), we can just
   use the CLI command of artifact kinds. this will save tokens."
   → s0017 § 11.6 + decision **D10** retire the slash command;
   agents invoke `artifacts kinds` directly. Folded into the L1
   implementation task as an extra step.

The **Requirements** section below preserves the original brief
(unchanged) for traceability. The **Verification** section has been
rewritten to match the descoped deliverable; original Requirements
2, 5, and parts of 3 / 8 are explicitly deferred to the L2 follow-up
spec (see s0017 § 11). Findings § "Coverage of original 11
requirements" tracks per-requirement status.

## Requirements (spec must cover) — original brief

*The 11 requirements below capture the original full-scope brief.
Per the Scope section, requirements 2, 5, and the L2/L3 portions of
3 and 8 are deferred to a follow-up spec. The deferral is locked in
s0017 § 11 and acknowledged in the revised Verification checklist.*

1. **Catalogue surface.** Define the canonical lookup that lists all
   registered kinds with one-line descriptions. CLI command shape,
   output formats (text + JSON), and where the description copy
   comes from. **Starting position from r0002 (R6):** description
   lives in `ARTIFACT.md` frontmatter as a required `description:`
   field; `kind.json` keeps the machine-readable schema. Spec must
   either lock this split or explicitly reject it.

2. **Per-kind detail surface.** Given a kind name, expose: schema
   path, `ARTIFACT.md` path (and existence), declared variants,
   declared playbooks, summary of frontmatter properties. Specify
   output shape and the CLI / API surface. **Starting position
   from r0002 (R5):** declared variants surface at L2, not L1.
   _Deferred to L2 follow-up (s0017 § 11.1)._

3. **Progressive disclosure model.** Formalise the L1 / L2 / L3
   layering. For each layer specify: trigger, content, output shape,
   and which consumer reads it. Show that L1 invocations never
   implicitly load L3 data. **Starting positions from r0002
   (R2/R3/R4):** L1 = name + description only, ~100–200 tokens per
   kind, always loaded; L2 trigger = "agent has selected this
   kind"; L3 = declared playbooks loaded on-reference, with a
   one-level-deep rule (no playbook→playbook chains). Spec locks
   each trigger and budget. _L1 fully locked here; L2/L3 deferred
   directionally to follow-up (s0017 § 4, § 11)._

4. **Selection signal.** What does the discovery surface expose to
   help "pick the right kind"? **Starting position from r0002
   (R1):** the sole selection signal is the `description:` field —
   required, non-empty, ≤1024 chars, third-person, encodes both
   *what* the kind is and *when* to choose it. Mirrors the Claude
   Skills `description` contract exactly. Spec must lock the cap,
   the voice constraint, and the "what + when" requirement, or
   justify deviation.

5. **`/artifacts.create` integration.** How the slash command uses
   the discovery surface to: locate `ARTIFACT.md`, validate
   frontmatter (`applies_to`, `schema_version`), resolve a variant,
   load a playbook only when declared. Path resolution must NOT
   require the slash command to walk the filesystem.
   _Deferred to L2 follow-up (s0017 § 11.3)._ The L1 implementation
   only swaps `/artifacts.kinds` → `artifacts kinds` in the
   slash-command body (D10, § 11.6).

6. **Reuse for non-CLI consumers.** TUI and future agent harnesses
   should reach the same data without going through CLI subprocess
   calls. Spec must propose a Python-API surface (or justify
   CLI-only).

7. **Evolution of existing `artifacts kinds`.** Today it lists
   kinds. Specify the upgrade path: new sub-commands
   (`artifacts kinds show <name>`?), new flags (`--detail`,
   `--paths`?), or a clean break. Backwards compatibility note.
   _New sub-commands (e.g. `kinds show`) deferred to L2; the L1
   evolution adds a `description` column + JSON keys additively
   (s0017 § 8.2, § 8.3)._

8. **Conflict / fallback semantics.** When `ARTIFACT.md` is absent,
   when a declared playbook is missing, when frontmatter validation
   fails — what does each layer return? Loud-vs-silent rules.
   **Starting position from r0002 (R7):** missing `ARTIFACT.md` =
   soft warning (kind usable, body scaffolding unavailable); missing
   *declared* playbook = hard error (already locked in n0005);
   missing or empty `description:` = registration warning. Spec
   locks all three loud/silent boundaries. _L1-side rules locked
   (missing `ARTIFACT.md` = soft; missing `description` = warning).
   "Missing declared playbook = hard" is L2-side, locked
   directionally only._

9. **Test plan.** Coverage matrix for: each layer in isolation,
   layer triggers, missing-template fallback, missing-playbook
   error, cross-consumer parity (CLI vs Python API). Layer-isolation
   tests are critical — the spec's value depends on them.
   _L1 layer-isolation locked (s0017 § 9.1); L2/L3 isolation tests
   deferred to follow-up._

10. **Cross-link.** Reference `[[artifacts/kinds/note/ARTIFACT.md]]`
    as exemplar, the locked decisions above, the research artifact
    `[[r0002-claude-skills-design-reference]]`, and the parent
    brainstorms (n0004, n0005).

11. **Engagement with r0002.** For each of the eight recommendations
    in `r0002` `## Recommendations for t0073`, the spec must record
    one of: `LOCK` (adopted as written), `LOCK-WITH-EDIT` (adopted
    with stated modifications), or `REJECT` (with rationale). No
    silent drops. This requirement is process-only — its output is
    a short table in the spec, not a separate deliverable.

## Progress

- 2026-05-02 — architect: drafted
  [[artifacts/specs/s0017-artifact-kinds-discovery-mechanism]] covering
  the full L1/L2/L3 surface; locked decisions D1–D15; engaged each
  of the eight r0002 recommendations. Transitioned to review.
- 2026-05-02 — architect: per user feedback ("simplify to only the L1
  in spec, L2 spec can be removed nearly all. just keep it in high
  level in next steps section"), narrowed s0017 to L1 only.
  Removed the L2/L3 detailed sections (data model, surface,
  loud-vs-silent matrix, layer-isolation tests for L2/L3, slash-command
  integration flow). L2/L3 and `/artifacts.create` integration moved
  to § 11 "Next Steps" at high-level only. Re-marked R3, R4, R7 as
  `LOCK-WITH-EDIT` to reflect the directional-only locks for the
  L2/L3 follow-up. Decisions reduced to D1–D9 (L1-only).
  Transitioned back to review.
- 2026-05-02 — architect: per user feedback ("instead calling claude
  artifacts.kinds (line 73), we can just use the CLI command of
  artifact kinds. this will save tokens"), retired the
  `/artifacts.kinds` slash command in the spec. Added decision
  **D10** (§ 3) and a new § 11.6 detailing the retirement steps
  (delete `artifacts.kinds.md`, update `artifacts.create.md` to
  swap the `/artifacts.kinds` reference for the CLI, grep for
  stragglers). Updated § 5 trigger row, § 12 implementation notes,
  § 13 scope history (Revision 3), and § 14 cross-references to
  match. Transitioned back to review.
- 2026-05-02 — architect: per user request "update task" and the
  prior Verification Report's recommended fix ("update the
  verification list to match the L1-only scope"), reconciled the
  task body with the descope. Added a `## Scope` section
  documenting Revisions 2 and 3, annotated original Requirements
  2/3/5/7/8/9 with deferral pointers into s0017 § 11, and rewrote
  the `## Verification` checklist with L1-aligned criteria
  (catalogue surface, selection signal, source-file split,
  fallback semantics, slash-command retirement, process
  cross-cutting). Marked the prior Verification Report as
  superseded — re-run `/openstation.verify` against the
  reconciled checklist for a fresh report. Original full-scope
  Requirements section preserved for traceability. Spec status is
  already `approved` (set by user); this update only brings the
  task body in sync.

## Findings

The spec — [[artifacts/specs/s0017-artifact-kinds-discovery-mechanism]]
— locks **L1 only**: the always-on catalogue surface that lists every
registered kind with a one-line `description`. L2 (per-kind detail) and
L3 (template / playbook content) are explicitly deferred; they appear
in § 11 "Next Steps" at the level needed to file a follow-up spec
task, not as locked design.

### Key decisions (L1)

- **L1 carries `name + description + has_template` only.** ≤ 200
  tokens per kind. Reads `kind.json` and the **frontmatter** of
  `ARTIFACT.md` — never the body, never any playbook file. The
  layer-isolation invariant is the spec's load-bearing claim and
  must survive into the L2 follow-up.
- **`description:` is the sole selection signal.** Lives in
  `ARTIFACT.md` frontmatter (separate from `kind.json` schema).
  Required, non-empty, ≤ 1024 chars, third-person, encodes both
  *what* and *when*. Voice unenforced mechanically (false-positive
  risk); documented in authoring guide.
- **Source-file split locked.** `kind.json` = machine-readable
  schema. `ARTIFACT.md` frontmatter = human/agent-facing prose. No
  merge.
- **Loud-vs-silent for L1.** Missing `ARTIFACT.md` = soft warning;
  `has_template=False`. Missing/empty `description` = registration
  warning; entry still listed with `description=None`. Description
  > 1024 chars or containing XML / reserved words = hard error.
- **CLI is a thin printer.** `KindCatalog.list_kinds()` is the one
  L1 method; `artifacts kinds` gains a `description` column and the
  `-j` JSON gains `description` + `has_template` keys. `KindCatalog`
  is named to anticipate L2/L3 methods landing later.
- **`/artifacts.kinds` slash command retired (D10).** It was a thin
  passthrough whose prompt body added ~100+ tokens per invocation
  with no behavioural gain. Agents invoke `artifacts kinds` directly.
  The L1 implementation deletes `artifacts.kinds.md` and updates the
  one-line reference in `artifacts.create.md`. Other workflow-bearing
  slash commands (`/artifacts.create`, `/artifacts.show`,
  `/artifacts.list`) stay — they encode token translation, edge
  cases, and wikilink wrapping that direct CLI cannot replicate
  without re-instructing the agent each time.
- **Backwards-compatible.** New column / JSON keys are additive;
  `-q` mode unchanged; legacy flat `artifacts/kinds/<name>.json`
  coexists with the folder form (folder wins on collision).

### Why the descope

L2's surface design is best driven by a concrete consumer
(`/artifacts.create`'s template loader). Shipping L1 first unlocks
the catalogue improvements (descriptions visible to agents picking
kinds) without committing to an L2 shape that may need iteration.
The spec's § 13 "Scope History" records the decision for future
readers.

### r0002 engagement

- **`LOCK` (4):** R1, R2, R5, R6 — fully addressed by L1.
- **`LOCK-WITH-EDIT` (4):** R3 (L2 trigger), R4 (L3 + one-deep),
  R7 (loud-vs-silent — L1 portion locked, L2 portion directional),
  R8 (authoring-guide concern, not the spec itself).
- **`REJECT` (0).**

### Coverage of original 11 requirements

| Req | Coverage |
|---|---|
| 1. Catalogue surface | ✅ Fully locked (§ 5, § 8). |
| 2. Per-kind detail surface | Deferred — § 11.1 sketch only. |
| 3. Progressive disclosure model | L1 fully locked; L2/L3 noted directionally (§ 4, § 11). |
| 4. Selection signal | ✅ Fully locked (§ 6). |
| 5. `/artifacts.create` integration | Deferred — § 11.3 sketch only. |
| 6. Reuse for non-CLI consumers | ✅ Locked for L1 (§ 8.1). |
| 7. Evolution of `artifacts kinds` | ✅ Locked for L1 (§ 8.2, § 8.3). |
| 8. Conflict / fallback semantics | L1 fully locked (§ 6.3, § 7); L2 deferred. |
| 9. Test plan | ✅ Locked for L1 (§ 9). |
| 10. Cross-link | ✅ § 14. |
| 11. r0002 engagement table | ✅ § 10. |

Verification items 1, 4, 5 (r0002 table), and 6 (cross-links) are
satisfiable; items 2, 3, and 7 are partially addressed (L1 locked,
L2/L3 deferred per the user's descope) — owner verification should
treat the descope as intentional per § 13 of the spec.

## Downstream

Forward-looking sub-tasks under
`[[t0079-artifact-md-artifacts-ai-extension]]`. Anything sketched in
s0017 § 11 lives there as next-steps notes only and does **not** spawn
a sub-task at this stage.

- **L1 implementation task** — `[[t0076-implement-l1-kinds-catalogue-s0017]]`.
  Covers § 12 of the spec: new `core/kinds_catalog.py` with
  `KindCatalog` + `KindCatalogEntry`, loader extension to read
  `ARTIFACT.md` frontmatter, `artifacts kinds` CLI changes
  (description column, additive JSON keys), dual-path loader, tests
  per § 9, **and** retirement of the `/artifacts.kinds` slash command
  per § 11.6 (D10).
- **Authoring-guide update** — `[[t0078-update-docs-adding-a-kind]]`.
  `docs/adding-a-kind.md` adopts r0002 R8 (evaluation-first authoring)
  and cross-links s0017 once L1 lands.
- **Per-kind `ARTIFACT.md` rollout.** Only `note` has an
  `ARTIFACT.md` today; without others, L1's description column will
  show "(no description)" for `task`, `spec`, `research`, `agent`.
  Authoring an `ARTIFACT.md` for each is adjacent work — each lifts
  the catalogue's signal-to-noise. Tracked under t0079 as future
  sub-tasks.

## Verification

*Reconciled with the descoped (L1-only) deliverable per the Scope
section above and the prior Verification Report. Original full-scope
checklist items related to L2 / L3 / `/artifacts.create` integration
have been replaced with L1-aligned criteria; L2/L3 will be verified
against a follow-up spec when it lands.*

### L1 catalogue surface (the spec's locked surface)

- [ ] Spec file committed under `artifacts/specs/` as
      `s0017-artifact-kinds-discovery-mechanism.md`.
- [ ] L1 `KindCatalogEntry` shape locked: `name`, `description`,
      `has_template` (s0017 § 5.1).
- [ ] L1 trigger and source-file rules locked: `kind.json` + only
      the **frontmatter** of `ARTIFACT.md` are read at L1; body and
      playbooks are never read (s0017 § 5).
- [ ] L1 layer-isolation invariant has explicit tests in the test
      plan (s0017 § 9.1).
- [ ] CLI evolution is backwards-compatible: `description` column
      added to default table; `description` and `has_template`
      keys added to `-j` JSON; `-q` mode unchanged (s0017 § 8.2,
      § 8.3).
- [ ] Python-API surface (`KindCatalog.list_kinds()`) specified
      and CLI ↔ Python-API parity is testable (s0017 § 8.1, § 9.5).

### Selection signal & source-file split

- [ ] `description:` field contract fully locked: required,
      ≤ 1024 chars, third-person, what+when, length / XML /
      reserved-word validation rules (s0017 § 6).
- [ ] Voice constraint is documentation-only (not lint-enforced)
      with a stated rationale (s0017 § 6.3, D6).
- [ ] Source-file split locked: schema in `kind.json`; prose in
      `ARTIFACT.md` frontmatter; loader handles both legacy flat
      and folder forms with folder winning on collision (s0017
      § 7.1, § 8.3).

### L1 fallback semantics

- [ ] Missing `ARTIFACT.md` → soft warning, kind still listed,
      `has_template=False` (D5).
- [ ] Missing/empty `description` → registration warning, kind
      still listed with `description=None` (D4).
- [ ] Description longer than 1024 chars / containing XML /
      reserved word → hard error (s0017 § 6.3).

### Slash-command retirement (D10)

- [ ] s0017 § 11.6 documents the retirement of the
      `/artifacts.kinds` slash command with concrete steps
      (delete the .md, update `artifacts.create.md` reference,
      grep for stragglers) so the L1 implementation task can
      execute without further design work.

### Process / cross-cutting

- [ ] r0002 engagement table present: each of the eight r0002
      recommendations marked `LOCK` / `LOCK-WITH-EDIT` /
      `REJECT` with rationale where edited or rejected
      (s0017 § 10).
- [ ] L2, L3, and `/artifacts.create` integration appear in
      s0017 § 11 "Next Steps" at sketch level only — no detailed
      locking attempted (per Scope revision 2).
- [ ] Cross-links `[[artifacts/kinds/note/ARTIFACT.md]]`, the
      locked decisions, `[[r0002-claude-skills-design-reference]]`,
      n0004, n0005 (s0017 § 14).
- [ ] Findings include the per-requirement coverage table for
      the original 11 items (this task's Findings section).
- [ ] Follow-up **L1 implementation task** can be filed against
      the spec without further design work. The L2 follow-up spec
      is itself a separate downstream item.
- [ ] Reviewed and approved by user.

## Verification Report

*Superseded — verification ran against the pre-descope checklist;
the checklist has since been reconciled with the L1-only scope
(see Verification section above). Re-run `/openstation.verify` to
generate a fresh report against the reconciled criteria.*

*Verified: 2026-05-02*

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Spec file committed under `artifacts/specs/` | PASS | `artifacts/specs/s0017-artifact-kinds-discovery-mechanism.md` exists (556 lines, frontmatter `kind: spec`, `id: s0017`, `task: [[t0073-…]]`). |
| 2 | All 11 requirements covered | FAIL | Reqs 2 (per-kind detail), 5 (`/artifacts.create` integration), and the L2 portion of req 8 (fallback semantics) are intentionally **deferred** per user-driven descope (§ 13, Revisions 2–3). They appear only as directional sketches in § 11.1, § 11.3, and the Findings coverage table explicitly marks them "Deferred". Strictly, not all 11 are *covered*. |
| 3 | Progressive disclosure model L1/L2/L3 all locked | FAIL | Only L1 is locked (§ 4–§ 9). § 4 explicitly tables L2/L3 as "Locked? No — see § 11"; § 11.1 and § 11.2 are sketches, not locks. The descope is documented but the criterion ("all locked") is not met. |
| 4 | Picks Python-API + CLI surface (or justifies CLI-only) | PASS | § 8.1 introduces `KindCatalog.list_kinds()` Python API; § 8.2 defines CLI; § 8.1.1 justifies API-plus-CLI for slash command, TUI, and agent harness consumers; § 9.5 pins parity by test. |
| 5 | r0002 engagement table with 8 marks | PASS | § 10 contains a table covering all eight r0002 recommendations (R1–R8): 4 LOCK, 4 LOCK-WITH-EDIT, 0 REJECT — each with rationale. Cross-checked against `artifacts/research/r0002-…` § "Recommendations for t0073". |
| 6 | Cross-links to ARTIFACT.md, decisions, r0002, n0004, n0005 | PASS | § 14 links `[[artifacts/kinds/note/ARTIFACT.md]]`, `[[r0002-claude-skills-design-reference]]`, `[[n0004-improve-create-command]]`, `[[n0005-artifact-md-kind-folders-for]]`; § 3 lists locked decisions D1–D10. |
| 7 | Reviewed and approved by user | FAIL | No explicit user approval recorded. The user has provided two iterative feedback rounds (descope to L1, retire `/artifacts.kinds`) but has not signalled final approval. Sign-off must come from the owner. |
| 8 | Follow-up implementation task can be filed without further design work | PASS | § 12 enumerates six concrete implementation steps for L1 (new module, loader extension, CLI changes, dual-path loader, tests, slash-command retirement); § 11.6 spells out the retirement procedure. An L1 implementation task is fileable against the spec as-is. |

### Summary

5 passed, 3 failed. Items 2 and 3 fail strictly because the
user-driven descope (§ 13) intentionally deferred L2/L3 — the
verification checklist still reads as written before the descope and
needs reconciliation. Item 7 cannot be self-asserted by an agent
verifier — only the owner (`user`) can mark it.

### What Needs Fixing

- **Reconcile checklist with descoped scope (items 2 & 3).** Either
  (a) update the verification list to match the L1-only scope (e.g.
  "All 11 requirements addressed: locked or directionally deferred
  per § 13"), or (b) re-expand the spec to lock L2/L3. Recommend
  option (a) — the descope was deliberate and the L2 surface is
  better designed once a concrete consumer exists (Findings rationale).
- **Owner sign-off (item 7).** User to review the spec end-to-end
  and confirm the descope, then re-run `/openstation.verify` so the
  approval can be checked off.