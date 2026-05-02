---
assignee: developer
created: 2026-05-02
id: t0059
kind: task
name: fix-r0001-missing-created-field
owner: user
status: ready
type: implementation
---

## Goal

Add the missing `created` frontmatter field to `r0001-openstation-integration-audit` so it satisfies the `research` kind's required-fields contract.

## Context

`artifacts validate --all` reports:

```
research / r0001-openstation-integration-audit
  E  created  Required field 'created' is missing
```

The artifact body already documents the date in its header:

> **Date:** 2026-04-29

So no judgement call is needed — copy the body date into the frontmatter.

## Requirements

1. Add `created: 2026-04-29` to the frontmatter of
   `artifacts/research/r0001-openstation-integration-audit.md`.
2. Preserve all other frontmatter and the body verbatim.
3. Re-run `artifacts validate --all` and confirm the error
   for `r0001` is gone.

## Verification

- [ ] `artifacts show r0001 -j` shows `created: 2026-04-29` in frontmatter
- [ ] `artifacts validate --all` no longer reports an error for `r0001`
- [ ] No other field in the artifact is changed
- [ ] Reviewed and approved by user