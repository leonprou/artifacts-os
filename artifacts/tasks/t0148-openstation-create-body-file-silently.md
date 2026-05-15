---
assignee: developer
created: 2026-05-14
id: t0148
kind: task
name: openstation-create-body-file-silently
owner: user
status: ready
type: implementation
---

# `openstation create --kind note --body-file` silently drops body

## Symptom

```bash
openstation create "Distributable harness — layers inventory" \
  --kind note \
  --body-file /tmp/n-distributable-harness-layers.md \
  --task t0144-distributable-opinionated-harness-for-artifacts
```

Reports success and writes the note with correct frontmatter
(including the `task` link), but the body contains only the
auto-generated `# <Title>` header — every line from
`--body-file` is discarded. No warning, no non-zero exit.

Workaround: `artifacts create --kind note --body-file <path>`
honours `--body-file` correctly (verified today on n0012).

## Why this matters

- Body is immutable through both CLIs after creation, so a
  silent drop on create means the artifact has to be deleted
  and recreated to fix. That's destructive and unobvious.
- It diverges from `artifacts create`, which is the canonical
  surface — users expect the wrappers to agree.

## Suspected scope

- Likely affects every kind, not just `note` — the body
  pipeline is shared.
- May also affect `--body` (stdin/literal); not yet verified.

## Acceptance

- [ ] Reproduce with a minimal `openstation create --kind note
      --body-file <path>` invocation.
- [ ] Identify whether `--body` (literal) has the same issue.
- [ ] Either forward `--body`/`--body-file` to the underlying
      `artifacts create` call, or surface a clear error if
      openstation intentionally doesn't accept body input.
- [ ] Add a regression test that creates a note via
      `openstation create --body-file` and asserts the body
      matches the input file.

## References

- n0011-distributable-harness-layers-inventory — empty stub
  produced by this bug; can be deleted once n0012 supersedes it.
- n0012-distributable-harness-layers-to-merge — same content
  via `artifacts create --body-file`, body written correctly.