---
assignee: developer
created: 2026-06-11
id: t0208
kind: task
name: create-body-file-writes-0
owner: user
priority: high
status: in-progress
type: bug
---

# create --body-file writes 0-byte files

## Repro

```bash
f=$(mktemp); echo "some body" > "$f"
artifacts create "any title" --kind task --type feature --body-file "$f"
# stdout shows the created record (status: backlog) — looks successful
wc -c artifacts/tasks/<new-id>-*.md   # → 0 bytes
```

Reproduced 7/7 times on 2026-06-11 in this vault (tasks
t0202–t0208 were all created 0-byte). The CLI prints the
created-record summary and exits 0, but the file on disk is empty:
no frontmatter, no body. `artifacts show <id>` then returns an
empty record, and the vault contains an unparseable artifact.

## Root-cause leads

- The create path appears to allocate the ID and `touch` the file,
  then fail (or skip) the content write when `--body-file` is used —
  while still reporting success.
- Not tested whether inline `--body` has the same defect; check
  both paths.

## Requirements

- `artifacts create --body-file PATH` writes full frontmatter +
  body content atomically; a 0-byte artifact must never result
  from a create that exits 0.
- If the body file is unreadable, create must fail loudly (non-zero
  exit, no file left behind).

## Verification

- [ ] Repro above yields a complete file (frontmatter + body).
- [ ] `--body` inline path verified as well.
- [ ] Unreadable `--body-file` → non-zero exit and no orphan file.
