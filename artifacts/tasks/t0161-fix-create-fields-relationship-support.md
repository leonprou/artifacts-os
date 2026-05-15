---
assignee: developer
created: 2026-05-15
id: t0161
kind: task
name: fix-create-fields-relationship-support
owner: user
status: ready
type: implementation
---

# Fix Create Fields Relationship Support

## Goal

Fix two reproducible gaps in `artifacts create --fields` that prevent the CLI from fully populating task relationships at creation time, currently forcing direct file edits or manual follow-ups.

## Why

While filing the artbook MVP sub-task chain ([[t0150-artbook-distribution-model]] → [[t0151-spec-the-artbook-model]] / [[t0157-book-local-distro-mode]] / [[t0158-implement-artbook-v2-schema]]), two failures surfaced repeatably:

1. **Array-valued fields don't parse.** `--fields depends_on='["[[t0154-…]]"]'` is rejected: the CLI treats the value as a single string and wraps it in `[[...]]`, producing `[[["[[t0154-…]]"]]]` which fails the array-of-wikilink-strings schema. There is no documented syntax for setting `depends_on`, `subtasks`, or `artifacts` at create time.
2. **Parent set, but parent's `subtasks` array not back-linked.** `--fields parent="[[t0150-…]]"` correctly sets the new task's `parent` frontmatter, but the parent task's `subtasks` array stays untouched. Existing parents (e.g. t0144) have their `subtasks` populated, so the relationship is expected — the create command just doesn't maintain it.

Both push the operator (or PM agent) toward direct file edits, which violates the `artifacts-os` skill's "CLI only" rule.

## Scope

### Array-valued `--fields`

1. Accept a syntax for setting `depends_on`, `subtasks`, `artifacts`, and any other array-typed field at create time. Candidate forms (developer picks one and documents it):
   - JSON array literal: `--fields depends_on='["[[t0152-…]]", "[[t0153-…]]"]'`
   - Repeated key: `--fields depends_on="[[t0152-…]]" depends_on="[[t0153-…]]"`
   - Comma-separated value: `--fields depends_on="[[t0152-…]],[[t0153-…]]"`
2. Per-field schema-aware handling: array-typed fields parse the chosen syntax into a list; scalar wikilink fields (e.g. `parent`) keep today's auto-wrap behaviour. Stop wrapping array values in `[[...]]`.

### Parent backlink

3. When `--fields parent="[[<ref>]]"` is set, the create command also appends the new task's wikilink to the parent's `subtasks` array atomically (read parent → modify frontmatter → atomic write).
4. If the parent does not exist, fail with a clear error *before* writing the child (no orphaned children).
5. Idempotent on re-creation — if the parent already lists the child wikilink, no-op.

### Documentation

6. Update `artifacts create --help` output and the `artifacts-os` skill's `### Create` section with the chosen array-field syntax and the parent-backlink behaviour.

## Out of scope

- A dedicated `--parent` / `--depends-on` flag separate from `--fields` (decide in a follow-up if `--fields` proves clunky in practice).
- Backfilling `subtasks` arrays on existing parents whose children were filed via the broken path (one-time data fix, not CLI behaviour).
- A generic frontmatter-update CLI command (separate concern; bodies-immutable rule is intentional).

## Verification

- [ ] `artifacts create "…" --kind task --fields depends_on=…` populates `depends_on` as a wikilink array (chosen syntax documented in `--help`).
- [ ] Creating a child with `--fields parent="[[parent-ref]]"` results in the parent's `subtasks` array containing the new child's wikilink.
- [ ] Creating a child whose parent does not exist fails with a clear error before any write happens.
- [ ] Re-creating an existing child link is idempotent — parent's `subtasks` array unchanged.
- [ ] `artifacts create --help` documents the array-field syntax.
- [ ] The `artifacts-os` skill `### Create` section is updated to match.
- [ ] Tests cover all four cases (array set, parent backlink, missing parent, idempotency).

## References

Surfaced during filing of:
- [[t0157-book-local-distro-mode]] — `depends_on` couldn't be set via `--fields`
- [[t0158-implement-artbook-v2-schema]] — same
- [[t0150-artbook-distribution-model]] / [[t0151-spec-the-artbook-model]] — parent's `subtasks` array not auto-populated when filed via `--fields`

Related (separate body-handling bugs already in queue):
- [[t0147]] / [[t0148]] — `openstation create --body-file` silent failures