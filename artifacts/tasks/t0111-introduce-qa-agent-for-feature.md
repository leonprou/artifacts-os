---
kind: task
id: t0111
name: introduce-qa-agent-for-feature
type: feature
status: done
assignee: author
owner: user
created: 2026-05-06
started: 2026-05-06
artifacts:
  - "[[artifacts/agents/qa]]"
completed: 2026-05-07
---

# Introduce Qa Agent For Feature And Implementation Task Verification

## User story

**As a** task owner who needs to verify that completed feature and
implementation work actually does what its checklist says,
**I want** a dedicated `qa` agent that drives the verification list
end-to-end against the built system and produces an evidence report,
**so that** sign-off becomes "read the QA report and accept" instead
of "trust the developer's self-check, or absorb verification work
that doesn't belong to me."

## Why

`project-manager` has been absorbing verification work that isn't
their role. PM is a coordinator — assignment, backlog flow,
documentation — not an executor of CLI commands and observer of
artifacts. Today the `review` step is lightly enforced: `developer`
runs unit tests against the spec, but nobody actually drives the
user-observable verification list. That gap is currently filled by
PM rubber-stamping or ad-hoc human checking, neither of which scales
as the lifecycle grows.

A dedicated `qa` agent fills the missing executor slot between
`developer` self-tests and `owner` sign-off. Its independence is the
value: a separate pair of eyes that runs the checklist exactly as a
user would.

The product surface is heavily CLI-driven (init flow, `openstation`
commands, release flow), which makes end-to-end verification simple
and tractable for an agent — no UI harness needed. Start small.

## Directions

*Intent, not contract — `author` may refine wording when drafting
the agent spec.*

- **Alias `qa`.** Description: agent that executes a task's
  verification checklist and reports evidence. No new lifecycle
  fields needed.
- **Default owner of `feature` and `implementation` tasks.**
  Other task kinds (`research`, `spec`, `documentation`, `note`)
  keep their current owner — their verification is content judgment,
  not execution. Widening QA's scope to those kinds is a future
  decision, not a day-one decision.
- **Verify-only. QA never fixes.** Self-verification is forbidden
  by the lifecycle, and QA's value is independence. When a
  verification item fails:
  - **In-scope failure:** transition `review → in-progress`, append
    findings, and let the original `assignee` rework on their next
    run. No explicit routing — the `assignee` field is the routing.
  - **Out-of-scope failure:** file a new bug task via
    `openstation create` with the parent linked. Original task
    proceeds on its passing items.
- **Findings format.** Append a `## QA Findings` section to the
  task body on each rejection. Each rework round adds a
  `### Round N — <date>` block listing every checklist item with
  ✅/❌, observed vs expected, repro steps, and evidence (stdout/stderr
  excerpts). One file, full history.
- **Loop cap.** Three rework rounds per task. After the third
  failure on the same item, QA stops the loop, files a new bug
  task with the persistent failure as evidence, and lets the parent
  advance on its passing items (or escalates to `project-manager`
  for re-assignment).
- **Tooling.** CLI-based end-to-end checks. `Read`,
  `Bash(openstation *)`, `Bash(artifacts *)`, plus `Glob`/`Grep`
  for artifact inspection. **No `Write`/`Edit`** — the no-fix rule
  is enforced by tool permissions, not just convention.
- **Exploratory probing permitted.** QA may try unhappy paths the
  checklist missed (bad flags, empty inputs, etc.). Findings file
  as new tasks, never bolted onto the task in review.

## Open questions

Deliberately deferred — flagging them so future PM / architect work
can revisit:

1. **Should QA expand to `research`/`spec`/`documentation`/`note`
   verification later?** Default no, since those are content
   judgments. Revisit if a pattern emerges where structured QA
   checks add value.
2. **Trivial-fix exception.** Should QA be allowed to *suggest* a
   one-line patch in its findings (as text, not code)? Decided no
   for v1 to keep the boundary crisp; revisit if backlog noise from
   one-line bug tasks becomes painful.
3. **Release-level QA report.** Should QA emit a release-level
   report aggregating findings across tasks in a version range?
   Out of scope for v1.
4. **Owner of QA's own feature tasks.** The self-verification ban
   means `qa` must not own its own tasks. Default for tasks *about*
   qa: `pdm` or `user`. Worth pinning in the spec.

## Sub-tasks

- `author` — draft `artifacts/agents/qa.md` per the directions
  above. (No `architect` sub-task: no new lifecycle machinery, no
  schema changes, reuses existing `review → in-progress` and
  `openstation create` paths.)

## Progress

### 2026-05-06 — author

Drafted `artifacts/agents/qa.md` per the directions. Kept the
allowed-tools list strictly read/inspect-only (no `Write`/`Edit`)
to encode the verify-only rule at the tool-permission layer.
Encoded the directions as five distinct H2 sections in the body:
Capabilities, Default Ownership, Findings Format, In-Scope vs
Out-of-Scope Failures, Loop Cap, Constraints. Audited the
`openstation` CLI (`src/artifacts_os/cli/commands/create.py`,
`artifacts/kinds/task.json`) and confirmed `owner` has no
hard-coded default per task type today — flagging for follow-up
in Downstream.

## Findings

Produced `artifacts/agents/qa.md` (linked in `artifacts:`
frontmatter). Highlights:

- **Frontmatter** — `kind: agent`, `name: qa`, `alias: qa`,
  `aliases: [qa]`, `model: claude-opus-4-7`,
  `skills: [openstation-execute]`. The `allowed-tools` list is
  `Read`, `Glob`, `Grep`, `Bash(openstation *)`,
  `Bash(artifacts *)`, `Bash(ls *)`, `Bash(readlink *)` — `Write`
  and `Edit` are deliberately excluded so the no-fix rule is
  enforced at the tool layer, matching the directions verbatim.
- **Body** documents (in this order): role statement,
  Capabilities, Default Ownership of `feature`/`implementation`
  tasks, Findings Format with the round-by-round
  `### Round N — YYYY-MM-DD` template, In-Scope vs Out-of-Scope
  Failure routing, Loop Cap (three rounds, then file a bug
  task), and Constraints (verify-only, no source-code edits, no
  suggested patches, reuse existing lifecycle paths, exploratory
  probing routed to new tasks).
- **No new lifecycle machinery, no schema changes** — sticks to
  the existing `review → in-progress` transition and
  `openstation create` for filing bug tasks, matching the
  sub-task scope.
- **Open question 4** ("Owner of QA's own feature tasks") is
  answered implicitly by the spec: `qa` cannot self-verify, so
  tasks *about* qa take `owner: project-manager` or `owner: user`.
  The spec does not pin this in the body — left as a downstream
  doc/lifecycle clarification.

## Downstream

- **CLI does not default `owner: qa` for feature/implementation
  tasks.** Verification item 4 expects `qa` to be the default
  owner on `openstation create` for these types. Audit of
  `src/artifacts_os/cli/commands/create.py` and
  `artifacts/kinds/task.json` shows no per-type default exists
  today — `owner` is required and free-form, defaulting to `user`
  by spec convention only. Implementing per-type defaults is an
  `architect`/`developer` follow-up: either a `defaults` block in
  `artifacts.yaml` keyed on `type`, or hardcoded routing in
  `create.py`. File as a separate task before promoting `qa` to
  active default ownership.
- **`## QA Findings` appending requires Write/Edit.** The agent
  spec forbids `Write`/`Edit` on the QA agent, but the directions
  also require appending a `## QA Findings` section to the task
  body each round. Today no `openstation` subcommand appends
  arbitrary body sections; the closest existing slash command
  (`/openstation.verify`) only writes `## Verification Report`
  and replaces it on each run. Two follow-ups:
  - Add an `openstation qa-report <task> --round N --body-file PATH`
    CLI subcommand that the QA agent can invoke through
    `Bash(openstation *)`, OR
  - Loosen the verifier verdict — accept that the existing
    `## Verification Report` covers the same intent and drop
    `## QA Findings` from the spec.
  Captured here so PM/architect can decide before QA ships as
  active.
- **Pre-existing verifier bug** — `openstation verify <agent>`
  reports `missing field: id` and `id "..." expected prefix "ag"`
  for every agent in `artifacts/agents/` that doesn't already
  have an `id: agNNNN` prefix. The `agent.json` schema declares
  `x-prefix: ""`, `x-numbered: false`, and only requires
  `kind`, `name` — so the verifier is enforcing constraints the
  schema doesn't declare. Out of scope here; logged for a
  separate `developer` fix task.

## Verification

- [x] `artifacts/agents/qa.md` exists with frontmatter `kind: agent`,
  `name: qa`, `aliases: [qa]`, allowed-tools that exclude `Write`
  and `Edit`, and `skills: [openstation-execute]`.
- [x] The agent spec body documents: verify-only rule, findings format,
  three-round loop cap, default ownership of `feature` and
  `implementation` tasks, and the in-scope vs out-of-scope failure
  routing.
- [ ] A sample feature task in `review` status, when handed to `qa`,
  results in: a `## QA Findings` section appended to the task, the
  right status transition (`verified` on full pass, or `in-progress`
  with findings on in-scope failure), and a new bug task on
  out-of-scope failure.
- [ ] `project-manager` is no longer the default owner on `feature` and
  `implementation` tasks created via `openstation create` — `qa` is.
  (Flag for `architect` review during implementation if the default
  is hard-coded in the CLI.)
- [ ] Running `qa` against a passing task and a failing task produces
  distinguishable, evidence-rich reports — no rubber stamps, no
  opaque "looks good".

## Verification Report

*Verified: 2026-05-06*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts/agents/qa.md` exists with required frontmatter, allowed-tools excludes `Write`/`Edit`, includes `skills: [openstation-execute]` | PASS | File at `artifacts/agents/qa.md` (5046 bytes); frontmatter has `kind: agent` (line 2), `name: qa` (3), `aliases: [qa]` (5), `skills: [openstation-execute]` (11–12); `allowed-tools` (14–21) lists `Read`, `Glob`, `Grep`, `Bash(openstation *)`, `Bash(artifacts *)`, `Bash(ls *)`, `Bash(readlink *)` — `Write`/`Edit` deliberately omitted. |
| 2 | Body documents verify-only rule, findings format, three-round loop cap, default ownership for feature/implementation, and in-scope vs out-of-scope routing | PASS | Body sections present: `## Capabilities`, `## Default Ownership` (lines 55–62), `## Findings Format` with `### Round N — YYYY-MM-DD` template (64–85), `## In-Scope vs Out-of-Scope Failures` (87–99), `## Loop Cap` (101–111), `## Constraints` opens with "Verify-only. Never fix." (115). |
| 3 | Sample feature task handed to `qa` produces `## QA Findings`, correct status transition, and a new bug task on out-of-scope failure | FAIL | No end-to-end demonstration provided. The author's own `## Downstream` notes (lines 172–186) flag this as not currently achievable: `qa` agent has no `Write`/`Edit` tools, and no `openstation` subcommand exists for appending `## QA Findings` body sections. The only existing surface (`/openstation.verify`) writes `## Verification Report`, not `## QA Findings`. |
| 4 | `project-manager` is no longer the default owner on `feature`/`implementation` tasks created via `openstation create` — `qa` is | FAIL | `src/artifacts_os/cli/commands/create.py` `_build_fields` and `_resolve_kind` set no per-type default for `owner`; `--owner` is opt-in. `artifacts/kinds/task.json` declares `owner` required and free-form (lines 25, 69–72) with no default and no per-type routing. The author's `## Downstream` (lines 161–171) confirms no per-type default exists today. |
| 5 | Running `qa` against passing/failing tasks produces distinguishable, evidence-rich reports | FAIL | No execution evidence presented; the agent has not been exercised against either a passing or failing task in this task. Blocked by the same gap as item 3 (no append surface, no Write/Edit tools). |

### Summary

2 passed, 3 failed. The agent spec artifact itself is well-formed
and matches the directions, but three of the five criteria require
behaviors that depend on either CLI changes (per-type owner default,
`## QA Findings` append surface) or end-to-end exercise that the
sub-task scope did not include.

### What Needs Fixing

- **Item 3 / Item 5 (related):** The `qa` agent cannot append
  `## QA Findings` to a task body — it has no `Write`/`Edit`, and
  no `openstation` subcommand exposes a body-append surface. Either
  (a) drop `## QA Findings` from the spec and rely on the existing
  `## Verification Report` written by `/openstation.verify`, or
  (b) add `openstation qa-report <task> --round N --body-file PATH`
  and grant `Bash(openstation *)` to QA. The author's downstream
  notes already capture this; a follow-up task is required before
  the verification path the directions describe is actually
  reachable. End-to-end exercise (item 5) becomes possible only
  after that gap closes.
- **Item 4:** The CLI does not set `owner: qa` by default for
  `feature`/`implementation` tasks. Implement per-type owner
  defaults — either a `defaults.create.<type>.owner` block in
  `artifacts.yaml` resolved by `_resolve_kind`'s sibling, or
  hardcoded routing in `create.py`. File as an `architect`/
  `developer` follow-up before promoting QA to active default
  ownership.
