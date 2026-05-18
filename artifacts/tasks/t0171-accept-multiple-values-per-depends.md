---
assignee: developer
created: 2026-05-17
id: t0171
kind: task
name: accept-multiple-values-per-depends
owner: user
status: ready
type: implementation
---

## User story

> **As an** operator (or agent) using `artifacts create` to file a task with several dependencies
> **I want** `--depends-on A B C` (space-separated, one flag occurrence) to work the same as `--depends-on A --depends-on B --depends-on C`
> **so that** list-y flags behave consistently with `--fields KEY=VALUE ...` and I stop hitting `unrecognized arguments: <second-ref>` errors when I forget to repeat the flag.

## Why

Today's `artifacts create` flag surface mixes two argparse conventions for list-y inputs:

| Flag | Spelling | argparse |
|------|----------|----------|
| `--depends-on` | repeat: `--depends-on A --depends-on B` | `action="append"` |
| `--fields` | space-separated: `--fields k=v k=v` | `nargs="+"` |

The inconsistency is a real footgun. A user (or AI agent) who just typed `--fields a=1 b=2` reaches for the same form on the next line and gets:

```
error: unrecognized arguments: t0171-i4-update-consumer-docs-for
```

…which doesn't even hint that the flag should have been repeated. Caught in this session's PDM workflow when filing release-notes task dependencies (see [[n0015-artbook-promotion-mechanism-design-brainstorm]] — same session surfaced the issue alongside other CLI ergonomics gaps).

## Directions (intent, not contract)

- Promote `--depends-on` to `nargs="+"` **with an append-style action** so that both forms work:
  - `--depends-on A B` (space-separated, single flag)
  - `--depends-on A --depends-on B` (repeated — keeps working, no regression)
  - `--depends-on A B --depends-on C` (mixed — produces three values)
- Wikilink auto-wrapping (`t0042` → `[[t0042]]`) keeps working unchanged.
- Same treatment for any **other ref-list flag** that uses `action="append"` today; the developer audits and aligns them in one pass. Likely candidates: any flag whose schema property is `type: array` and is currently exposed as a convenience flag.
- `--parent` stays singular (one parent per artifact — out of scope).
- `--fields` stays as-is (already `nargs="+"`).

## Out of scope

- Other CLI ergonomics items from the same session: kind-aware help promoting required schema props to argparse `required=True`, and `artifacts show --fields` parity with `list`. Each can be its own task if we want them.
- Changing the wikilink wrapping behaviour.
- Touching `--fields` parsing.

## Verification

- [ ] `artifacts create "X" --depends-on t0001 t0002` writes `depends_on: [[[t0001]], [[t0002]]]` (two-element list).
- [ ] `artifacts create "X" --depends-on t0001 --depends-on t0002` still writes the same list (no regression).
- [ ] `artifacts create "X" --depends-on t0001 t0002 --depends-on t0003` writes a three-element list.
- [ ] Wikilink auto-wrap still applies to each ref regardless of form.
- [ ] `--parent` rejects multiple values with a clear error (singular by design).
- [ ] Test coverage in `tests/cli/test_create.py` for the three new forms plus the backward-compatible form.
- [ ] `src/artifacts_os/cli/README.md` `create` section shows the space-separated form in at least one example; the existing "repeat for multiple" line is updated to "space-separated or repeat".
- [ ] No new help-output regressions (`artifacts create --kind task --help` still lists `--depends-on REF [REF ...]`).

## References

- [[n0015-artbook-promotion-mechanism-design-brainstorm]] — session that surfaced this and related ergonomics gaps.
- `src/artifacts_os/cli/commands/create.py` — `--depends-on` registration.
- `src/artifacts_os/cli/README.md` § `create` — flag table + examples to update.