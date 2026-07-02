---
assignee: developer
created: 2026-06-14
id: t0209
kind: task
name: type-enum-omits-bug-rejects
owner: user
priority: high
status: backlog
type: implementation
---

# `type: bug` is not in the task `type` enum — bug artifacts are un-transitionable

Filed as `type: implementation` because the schema rejects `type: bug` —
which is precisely the defect described below.

## Repro

A task whose frontmatter has `type: bug` (e.g. t0208) cannot be moved
through its lifecycle:

```bash
artifacts status t0208 review
# error: 'bug' is not one of ['feature','implementation','spec','documentation','research','refactor']
# Failed validating 'enum' in schema['properties']['type']
```

Creating one is also rejected:

```bash
artifacts create "x" --kind task --type bug --fields assignee=a owner=user
# same enum rejection (after the 'assignee is required' check)
```

## Root cause

`artifacts/kinds/task/kind.json` defines `properties.type.enum` as
`['feature', 'implementation', 'spec', 'documentation', 'research', 'refactor']`
— `bug` is absent by design (schema comment: "Closed enum … new categories
require a schema bump"). Every write path re-validates the full record
against this schema, so any task carrying `type: bug`:

- cannot be transitioned by `artifacts status` (whole-record enum validation
  fails on a field unrelated to the transition), and
- cannot be created via `artifacts create --type bug`.

Yet t0208 carries `type: bug` (created 2026-06-11, never schema-validated
until a status change was attempted), leaving it stranded. On 2026-06-14 the
`developer` agent (run r0214) worked around this by rewriting
`type: bug → implementation` solely to pass validation — silently corrupting
the task's classification. That mutation has been reverted; t0208 is back to
`type: bug` via a manual frontmatter edit (the only available workaround),
and is itself now un-transitionable until this is resolved.

## Requirements

Choose one coherent resolution and apply it consistently:

- **Option A — make bugs first-class:** add `bug` to `type.enum` in
  `artifacts/kinds/task/kind.json` (intentional schema bump) and update any
  schema-derived tooling/tests/views that enumerate task types.
- **Option B — reject early, never strand:** if `bug` is intentionally
  unsupported, ensure no supported path can produce a `type: bug` artifact
  (audit the openstation bridge / `create.bug`), and confirm `create` fails
  loudly with no file left behind. A validation error must never leave an
  already-persisted artifact un-transitionable.
- Either way: a status transition must not fail on a frontmatter field
  unrelated to the transition without an actionable error telling the user
  how to fix it.

## Verification

- [ ] Decision (A or B) recorded with rationale in `## Findings`.
- [ ] If A: `artifacts create --type bug …` succeeds and the task can go
      backlog → ready → in-progress → review → done via `artifacts status`.
- [ ] If B: no supported command emits `type: bug`; `--type bug` fails at
      create with a clear message and leaves no orphan file.
- [ ] t0208 reaches a valid, transition-able state under the chosen option.
- [ ] A regression test covers the chosen behavior.