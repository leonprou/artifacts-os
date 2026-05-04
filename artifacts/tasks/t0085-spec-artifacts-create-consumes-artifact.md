---
artifacts:
- '[[artifacts/specs/s0018-artifact-md-body-loader-for]]'
assignee: architect
created: 2026-05-03
id: t0085
kind: task
name: spec-artifacts-create-consumes-artifact
owner: user
parent: '[[t0084-wire-artifacts-create-to-artifact]]'
priority: normal
started: 2026-05-03
status: done
type: spec
---

# Spec — `/artifacts.create` Consumes ARTIFACT.md Skeletons

## Context

Sub-task of `[[t0084-wire-artifacts-create-to-artifact]]`. The parent
epic ships the consumer side of t0079: when an agent runs
`/artifacts.create`, the resulting body should be pre-populated
with the kind's skeleton (with placeholders substituted) instead
of being empty.

Read t0084 for the user story, scope, and the full reading list.
This task produces the locked design — a `spec` artifact — that
the implementation sub-task will consume.

## Goal

Produce an approved `spec` artifact that locks the contract for
`/artifacts.create`'s consumption of `ARTIFACT.md` skeletons.
After approval, an implementation sub-task (filed by the PM)
ships the slash-command update with no further design debate.

## Scope

The spec must lock at least these decisions. Each is an open
question per t0084's "Open design questions" section.

1. **Placeholder substitution contract.**
   - Which placeholders are recognised (just `{{NAME}}`-shaped
     `placeholder_syntax` from frontmatter, or a wider set)?
   - Where do values come from — slash-command tokens
     (`name:<slug>`), CLI flags (`--name`, `--type`,
     `--assignee`, `--parent`), free-form prompt content, or
     all of the above with a precedence order?
   - What happens for an un-resolvable placeholder — leave it
     literal, drop it, or error?

2. **Variant selection.**
   - When `ARTIFACT.md` declares `## Variants/<name>` blocks,
     how does the agent pick which variant body to substitute
     into? Candidates: `--type` flag, an explicit
     `variant:<name>` slash-command token, agent inference
     from the user's title, or fallback to the default
     `## Skeleton`.
   - Lock a single rule. Document the precedence.

3. **Fallback when a kind ships no `ARTIFACT.md`.**
   - Behaviour: empty body (current behaviour), error, or a
     generic skeleton stub? Pick one.

4. **CLI / slash-command boundary.**
   - Restate the n0005 D6 invariant: CLI stays body-agnostic;
     all skeleton-loading and substitution lives in the slash
     command (agent layer). Spell out exactly which artifacts
     the slash command reads (the chosen kind's
     `artifacts/kinds/<kind>/ARTIFACT.md`) and which it does
     **not** (every kind, playbook bodies, kind.json bodies).

5. **Token budget.**
   - The slash command must read only the chosen kind's
     `ARTIFACT.md` body, not the whole catalogue.
   - Skeleton size is bounded by which conventions? Reference
     `docs/adding-a-kind.md` if it sets a guideline; otherwise
     propose one (e.g. ≤ 200 lines) and justify.

6. **Test plan.**
   - End-to-end: invoking `/artifacts.create kind:<K>` for each
     of the four shipped kinds (`task`, `spec`, `research`,
     `note`) produces the expected pre-populated body.
   - Negative path: a kind with no `ARTIFACT.md` (or with one
     that fails frontmatter validation) hits the fallback.
   - Layer-isolation: `artifacts kinds` invocations triggered
     by the slash command (selection signal) still do not read
     `ARTIFACT.md` bodies (s0017 § 4).

7. **Backwards compatibility.**
   - `artifacts create` CLI surface unchanged.
   - Agents that don't use the slash command continue to get
     empty-body files — no implicit body injection at the CLI
     layer.

## Source of truth

- `[[t0084-wire-artifacts-create-to-artifact]]` — parent epic
  with the user story, constraints, and the reading list.
- `[[s0017-artifact-kinds-discovery-mechanism]]` — locked L1
  surface. § 4 (layer isolation), § 6 (description contract),
  § 7 (source-file split). The new spec must not redesign any
  of these; it consumes them.
- `[[n0005-artifact-md-kind-folders-for]]` — D6 (CLI
  body-agnostic) is the load-bearing constraint.
- `[[n0004-improve-create-command]]` — themes A, B, H frame
  the user-visible problem the spec must solve.

## Constraints

- **No L2 / L3 widening.** The spec is about the consumer side
  of L1 + the per-kind ARTIFACT.md surface t0079 shipped. Do
  not introduce L2 (per-kind detail layer) or L3 (template
  body layer) concepts here — those are deferred per s0017
  § 11.
- **No CLI surface change.** The `artifacts create` CLI stays
  exactly as today. Any new behaviour lives in the slash
  command.
- **Recommendation engagement table** — when the spec engages
  research or notes that propose decisions, use the
  LOCK / LOCK-WITH-EDIT / REJECT pattern shipped in s0017 § 10.

## Deliverable

A `spec` artifact (next free `s00XX` ID) that satisfies the
scope items 1–7 above, with status `approved` after user
review. The spec's verification checklist itself is a separate
concern owned by the architect.

## Verification

- [x] A `spec` artifact is filed (architect picks the title and
      slug per `artifacts/kinds/spec/ARTIFACT.md` conventions).
- [x] The spec locks decisions on all six design questions
      (placeholder substitution, variant selection, fallback,
      CLI boundary, token budget, test plan, backcompat).
- [x] The spec's `## Goals` / `## Non-goals` are explicit; the
      L2 / L3 expansion is named in `## Non-goals`.
- [x] The spec engages `[[n0004-improve-create-command]]` and
      `[[n0005-artifact-md-kind-folders-for]]` via a
      LOCK / LOCK-WITH-EDIT / REJECT table (s0017 § 10
      pattern).
- [x] Test plan section names every property the implementation
      must verify, in language the developer can turn into
      pytest cases.
- [x] Spec status reaches `approved` (user gate).
- [x] Reviewed and approved by user.

## Verification Report

*Verified: 2026-05-03*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | A `spec` artifact is filed per `artifacts/kinds/spec/ARTIFACT.md` conventions. | PASS | `artifacts/specs/s0018-artifact-md-body-loader-for.md` exists; frontmatter `kind: spec`, `id: s0018`, `agent: architect`, `task: "[[t0085-…]]"`; title and slug follow `s{NNNN}-{topic}.md` convention. |
| 2 | Spec locks decisions on all six design questions (placeholder substitution, variant selection, fallback, CLI boundary, token budget, test plan, backcompat). | PASS | § 3 "Locked Decisions Summary" enumerates D1–D9 across all areas: placeholder (D1–D3, § 4), variant (D4, § 5), fallback (D5, § 6), CLI boundary (D6–D7, § 7), token budget (D8, § 8), test plan (§ 11), backcompat (D9, § 10). |
| 3 | `## Goals` / `## Non-goals` are explicit; L2 / L3 expansion is named in `## Non-goals`. | PASS | § 2.1 Goals (7 items) and § 2.2 Non-Goals are present; § 2.2 explicitly lists "L2 (per-kind detail surface)" and "L3 (template / playbook content surface)" with deferred references to s0017 § 11.1 / § 11.2. |
| 4 | Spec engages n0004 and n0005 via a LOCK / LOCK-WITH-EDIT / REJECT table (s0017 § 10 pattern). | PASS | § 12.1 covers n0004 themes A–J with verdicts (A/B/H LOCK; F LOCK-WITH-EDIT; C/D/E/G/I/J REJECT) and rationale; § 12.2 covers n0005 D1–D7 (D1/D2/D4/D5/D6/D7 LOCK; D3 LOCK-WITH-EDIT). |
| 5 | Test plan names every property the implementation must verify, in language the developer can turn into pytest cases. | PASS | § 11 lists pytest-ready names across four groups: § 11.1 e2e per shipped kind, § 11.2 fallback negatives, § 11.3 variant fixture, § 11.4 layer isolation, § 11.5 CLI surface snapshot. Examples: `test_e2e_<kind>_skeleton_substitutes_title`, `test_variant_explicit_token_picks_variant`, `test_slash_command_reads_only_chosen_kind_artifact_md`. |
| 6 | Spec status reaches `approved` (user gate). | PASS | `artifacts show s0018-artifact-md-body-loader-for -j` returns `"status": "approved"`. User promoted the spec from `draft` → `approved`. |
| 7 | Reviewed and approved by user. | PASS | Spec status flipped to `approved` by the user (recorded in this task's Progress entry "2026-05-03 — Spec approved; transitioning to review"); no outstanding revision requests. |

### Summary

7 passed, 0 failed. All verification criteria met. The spec artifact
[[s0018-artifact-md-body-loader-for]] is filed, content-complete, and
user-approved. Task ready to transition to `verified`.

## Findings

**Filed [[s0018-artifact-md-body-loader-for]]** — locks the contract
for `/artifacts.create`'s consumption of per-kind `ARTIFACT.md`
skeletons. Status: `draft`, awaiting user approval.

### Design summary

- **Placeholder substitution (D1–D3, § 4):** the slash command
  substitutes a single structural token, **`{{TITLE}}`**, sourced
  from the positional title. All other `{{TOKEN}}` placeholders are
  left literal for the agent to fill on first edit. Grammar pinned
  to `\{\{[A-Z][A-Z0-9_]*\}\}`. The `placeholder_syntax`
  frontmatter field is informational in v1; declared mismatches
  warn but do not block. Conservative set chosen to avoid the
  `{{NAME}}`-means-person-not-slug trap in `note`'s skeleton and
  to honour the agent-prompt intent of the shipped templates.
- **Variant selection (D4, § 5):** precedence is
  `variant:<name>` token → `--type` token (when frontmatter
  declares `variant_field: type`) → default `## Skeleton`. Title
  inference is explicitly rejected. None of the four shipped
  kinds exercise variants today, but the rule lands fully tested
  on a synthetic fixture (§ 11.3) so the first real consumer
  needs no further design.
- **Fallback (D5, § 6):** kinds with `has_template=False` produce
  empty-body files, mirroring today's behaviour, plus a one-line
  agent-context note. Empty over error to avoid breaking `agent`
  and other untemplated kinds; empty over generic stub to keep
  missing-template state honest.
- **CLI ↔ slash boundary (D6–D7, § 7):** restated n0005 D6.
  Slash command reads exactly one body file per invocation
  (`artifacts/kinds/<chosen-kind>/ARTIFACT.md`), pipes the
  resolved body via `--body-file -`. CLI never reads any
  `ARTIFACT.md`. L1 catalogue invocations preserve the s0017 § 4
  isolation invariant.
- **Token budget (D8, § 8):** authoring guideline of ≤ 400 lines /
  ≤ 8 KB per `## Skeleton` block. The four shipped templates
  (166–331 lines) fit comfortably. Not a load-time gate
  (false-positive risk).
- **Test plan (§ 11):** four groups — end-to-end per kind,
  fallback negatives, variant fixture, layer isolation — plus a
  CLI-surface-snapshot test pinning D9 backwards-compat.
- **Backwards compatibility (D9, § 10):** `artifacts create` flags
  / exit codes / stdout unchanged; direct CLI invocations
  continue to produce empty bodies; `$ARGUMENTS` token grammar
  remains additive.

### Key trade-offs

1. **Substitute one token, not many.** A wider substitution set
   (e.g. `{{NAME}}`, `{{KIND}}`, `{{PARENT}}`) was rejected for
   v1 because (a) `{{NAME}}` collides with note-author intent,
   (b) the agent already has the values it needs in the prompt,
   and (c) additive future expansion is backwards-compatible.
2. **Variant rule landed despite no v1 consumer.** The
   alternative — defer the decision — was rejected because
   t0085's spec scope explicitly required locking it. Shipping
   the rule with synthetic-fixture coverage is cheaper than
   re-litigating later.
3. **Fallback as info note, not as silent.** The agent-visible
   one-liner makes the missing-template state obvious without
   blocking creation; this avoids surprising regressions for
   `agent` and any future templateless kind.
4. **Authoring-guide cap, not a load-time gate.** Mirrors s0017's
   D6 rationale on description voice: false-positive risk
   outweighs author-blocking value.

### Engagement tables

- **n0004 themes A–J (§ 12.1):** A, B, H **LOCK** (close under
  this epic); F **LOCK-WITH-EDIT** (carried by the skeletons
  themselves, not the slash command); C, D, E, G, I, J
  **REJECT** for this spec (separate workstreams).
- **n0005 D1–D7 (§ 12.2):** D1, D2, D4, D5, D6, D7 **LOCK**
  (consumed verbatim); D3 **LOCK-WITH-EDIT** (`types/` rename
  superseded by s0017 retaining `kinds/`).

### Open follow-ups (for the PM)

The spec's § 9.2 names two sub-tasks the PM should file under
`[[t0084-wire-artifacts-create-to-artifact]]` once the user
approves s0018:

1. **Implementation sub-task** — updates
   `src/artifacts_os/ai/claude/commands/artifacts.create.md`
   per s0018 §§ 4–7, with the test plan from § 11. The
   implementation may optionally add an additive
   `KindCatalogEntry.artifact_md_path` field (s0018 § 9 item 2).
2. **Documentation sub-task** — updates `docs/adding-a-kind.md`
   to reference the size cap (§ 8.2), document the
   `## Variants/<name>` block convention, and cross-link s0018.
   May be closed with rationale if the implementation surfaces
   no new authoring conventions beyond what s0018 already
   captures.

## Downstream

- `docs/adding-a-kind.md` is unchanged in this task; the PM's
  documentation sub-task references s0018 once approved.
- The shipped `ARTIFACT.md` files for `note`, `task`, `spec`,
  `research` are unchanged; the implementation sub-task
  consumes them as-is.
- `KindCatalogEntry` may gain an `artifact_md_path` field
  (additive) — owned by the implementation sub-task, not this
  spec.

## Progress

### 2026-05-03 — Spec drafted (architect)

- Read t0084 (epic), s0017 (parent L1 spec), n0005 (D1–D7
  inputs), n0004 (theme inputs), and the four shipped
  `ARTIFACT.md` files.
- Confirmed the latest spec ID (s0017) — next free is s0018.
- Filed [[s0018-artifact-md-body-loader-for]] (`status: draft`)
  covering placeholder substitution, variant selection,
  fallback, CLI ↔ slash boundary, token budget, test plan, and
  backwards compatibility, plus the n0004 / n0005 engagement
  tables.
- Verified the spec via `openstation verify
  s0018-artifact-md-body-loader-for` — frontmatter passes.
- Ready for user review. Spec status moves draft → approved on
  user sign-off; this task moves review → verified → done in
  the same gate.

### 2026-05-03 — Spec approved; transitioning to review (architect)

- User promoted [[s0018-artifact-md-body-loader-for]] from
  `status: draft` to `status: approved`.
- Verification items 6 (spec status reaches `approved`) and 7
  (reviewed and approved by user) now have evidence.
- No further architect work required. Transitioning task to
  `review` so the user owner can re-run
  `/openstation.verify t0085-spec-artifacts-create-consumes-artifact`
  and close the task via `/openstation.done`.