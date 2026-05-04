---
kind: task
id: t0092
name: allow-openstation-status-to-transition
type: feature
status: backlog
assignee: 
owner: user
created: 2026-05-04
---

# Allow Openstation Status To Transition Multiple Artifacts In One Invocation

## User Story

**As an** operator or agent-owner working through a parent epic with several sibling artifacts sitting at the same lifecycle stage,
**I want** to transition multiple artifacts to the same target status in a single `openstation status` invocation,
**so that** I don't repeat the same command N times — risking typos, partial application, or silent inconsistency between siblings.

## Why

- **Concrete signal in this repo right now.** Under [[t0079-artifact-md-artifacts-ai-extension]], sub-tasks
  [[t0080-author-artifact-md-for-task]], [[t0081-author-artifact-md-for-spec]],
  [[t0082-author-artifact-md-for-research]] are all in `review` and need the same
  next transition. Operators repeat themselves for every batch like this.
- **Verbose flow already noted.** [[n0004-improve-create-command]] theme **I**
  ("sub-task creation flow is verbose"). The same shape applies to status
  transitions: in epics with N siblings, status changes are run N times.
- **Single-task surface is the only surface today.** `openstation status` accepts
  exactly one positional task argument (see `openstation status --help`), making
  batch operations a manual loop in the operator's head or shell.
- **Aligns with the strategy direction** of making the lifecycle pleasant for
  agents and operators alike — one of the core jobs Open Station claims to do.

## Directions

*Intent, not contract — the architect refines.*

- A single `openstation status` invocation should accept **one or more** artifact
  identifiers and transition all of them to the same target status.
- Single-task invocation must continue to work unchanged (don't break existing
  muscle memory or scripts).
- Per-artifact transitions should be **independent**: an invalid transition on
  one artifact should not silently break the others. Surface a per-artifact
  result (success / skipped / failed) in the output.
- Validate the batch up-front where feasible — e.g. if `--reason` is required
  for the target status, require it once for the whole batch.
- Interactive picker (`openstation status t0042` with no target) stays
  single-task; batch mode is non-interactive by definition.
- Exit code should communicate "all succeeded" vs "partial" vs "all failed" so
  scripts can react.

## Open Questions

*Decisions deliberately deferred to the architect spec sub-task.*

- **Syntax.** Variadic positional (`openstation status t0080 t0081 t0082 done`),
  a flag (`--tasks t0080,t0081,t0082`), or read IDs from stdin
  (`openstation list … | openstation status - done`)? Or all of the above?
- **Atomicity model.** Best-effort with a per-artifact report, or all-or-nothing
  with rollback? Best-effort is probably right but the spec should decide
  explicitly.
- **Filter shorthand.** Should batch mode also accept a filter expression
  (`openstation status --filter "status=review,parent=t0079" done`) so
  operators don't have to enumerate IDs? This may belong to a follow-up.
- **Scope of artifacts.** Today `status` is task-centric. Should batch mode
  apply to all artifact kinds with a `status` field, or stay task-only for now?
- **Reason handling.** When transitioning a batch to `failed`, is `--reason`
  shared across all tasks, or required per-task?
- **Output format.** Plain text summary, table, or JSON-on-`--json`? Should
  match conventions already used by `openstation list`.

## Sub-Tasks

- Spawn an **architect spec sub-task** to settle the CLI surface, atomicity
  model, output format, and edge cases (interactive picker, `--reason`,
  scope across kinds). The implementation task follows the spec.

## Verification

- Running `openstation status` with multiple task identifiers transitions all
  of them in one invocation — confirmed against the live vault, e.g. moving a
  group of `review` siblings to `verified` (or whatever target the spec lands on).
- Single-task invocation still works exactly as it does today: same arguments,
  same output, same exit code on success.
- When one artifact in a batch can't transition (wrong source status, missing
  required `--reason`, unknown ID), the command surfaces a clear per-artifact
  result; the others are not silently dropped.
- Exit code distinguishes "all succeeded", "partial success", and "all failed"
  in a way scripts can branch on.
- `openstation status --help` documents the batch form alongside the existing
  single-task form.
- The architect spec sub-task lands first, with the contract decided before
  implementation begins.
