---
created: 2026-06-11
id: t0207
kind: task
name: core-create-atomic-create-with
owner: user
priority: medium
status: backlog
type: feature
---

# core.create: atomic create with retries kwarg (O_CREAT|O_EXCL + ID-collision retry)

## Why

Filed from openstation bridge-dissolution Step H (open-station
`n0009-dissolve-aos-bridge-plan-and` / `n0010` §6 item 4).

Concurrent agents creating artifacts race on next-ID assignment.
openstation carries ~30 LOC of glue: atomic file creation via
`O_CREAT|O_EXCL`, retrying with a fresh ID on collision
(open-station `[[t0492-step-e-inline-atomic-create]]` inlines it
meanwhile; it will switch to this primitive when it lands). This
belongs in the storage layer.

## Requirements

- `core.create(reg, kind, slug, fields, body, retries: int = 5)`
  creates the artifact file with `O_CREAT|O_EXCL`; on
  `FileExistsError` it re-computes the next ID and retries up to
  `retries` times before raising.
- Default behavior unchanged for existing callers (document the
  retries default chosen).

## Verification

- [ ] Unit test: pre-creating the target path forces a collision;
      the call succeeds with the next ID.
- [ ] Exhausting retries raises a clear error.
