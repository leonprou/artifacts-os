---
assignee: developer
created: 2026-05-02
id: t0060
kind: task
name: migrate-s0009-status-to-deprecated
owner: user
status: ready
type: implementation
---

## Goal

Resolve the `status: superseded` data drift on
`s0009-artifacts-os-config-module` by migrating the value to
`deprecated` — a status that already exists in the `spec` schema
enum and accurately captures the artifact's lifecycle state.

## Context

`artifacts validate --all` reports:

```
spec / s0009-artifacts-os-config-module
  E  status   Unknown status 'superseded' — valid: draft, review, approved, deprecated
```

The artifact's body already begins with:

> **Superseded by [[s0010-core-settings-module-spec]]** — settings
> parsing has been folded into `core`; …

The supersession context is clearly preserved in the body, so
`deprecated` (already in the enum) is the right semantic landing
spot. This avoids extending the enum for a one-off case.

This issue was explicitly flagged as out-of-scope in
`t0054-complete-kind-schemas` ("s0009 data drift" note) and
deferred to a follow-up.

## Requirements

1. Change `status: superseded` → `status: deprecated` in
   `artifacts/specs/s0009-artifacts-os-config-module.md`.
2. Preserve the body verbatim — the "Superseded by [[s0010-…]]"
   header already conveys the cross-link.
3. Do **not** extend the spec schema enum.
4. Re-run `artifacts validate --all` and confirm the error for
   `s0009` is gone.

## Verification

- [ ] `artifacts show s0009 -j` reports `status: deprecated`
- [ ] `artifacts validate --all` no longer reports an error for `s0009`
- [ ] Body of `s0009` is unchanged (still references `s0010`)
- [ ] `spec.json` enum is unchanged (still 4 values)
- [ ] Reviewed and approved by user