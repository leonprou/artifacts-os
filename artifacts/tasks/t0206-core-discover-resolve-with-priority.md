---
created: 2026-06-11
id: t0206
kind: task
name: core-discover-resolve-with-priority
owner: user
priority: medium
status: backlog
type: feature
---

# core.discover: resolve_with_priority(reg, ref, kinds=[...])

## Why

Filed from openstation bridge-dissolution Step H (open-station
`n0009-dissolve-aos-bridge-plan-and` / `n0010` §6 item 3).

When a bare reference could match multiple kinds, consumers want a
deterministic kind-priority resolution (e.g. task before note).
openstation carries this loop in its bridge (`core/_aos.py`,
sinking to `core/resolve.py` in its Step B, open-station
`[[t0490-step-b-sink-aos-py]]`); it is a generic primitive any
multi-kind vault consumer reimplements.

## Requirements

- `core.discover.resolve_with_priority(reg, ref, kinds=["task",
  "note", ...])` tries resolution kind-by-kind in the given order
  and returns the first hit (plus its kind).
- Falls back to all-kinds resolution when `kinds` is omitted.

## Verification

- [ ] Unit test: same stem existing in two kinds resolves to the
      earlier kind in the priority list.
- [ ] Unknown ref raises/returns the same not-found surface as
      `resolve`.
