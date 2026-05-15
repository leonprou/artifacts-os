---
assignee: developer
created: 2026-05-15
id: t0161
kind: task
name: fix-create-fields-relationship-support
owner: user
status: done
type: implementation
started: 2026-05-15
completed: 2026-05-15
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

- [x] `artifacts create "…" --kind task --fields depends_on=…` populates `depends_on` as a wikilink array (chosen syntax documented in `--help`).
- [x] Creating a child with `--fields parent="[[parent-ref]]"` results in the parent's `subtasks` array containing the new child's wikilink.
- [x] Creating a child whose parent does not exist fails with a clear error before any write happens.
- [x] Re-creating an existing child link is idempotent — parent's `subtasks` array unchanged.
- [x] `artifacts create --help` documents the array-field syntax.
- [x] The `artifacts-os` skill `### Create` section is updated to match.
- [x] Tests cover all four cases (array set, parent backlink, missing parent, idempotency).

## Verification Report

*Verified: 2026-05-15*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `--fields depends_on=…` populates wikilink array | PASS | `_parse_fields` (create.py:217-256) handles array wikilink fields; tests `test_fields_wikilink_comma_list`, `test_fields_array_wikilink_single_value`, `test_fields_subtasks_comma_list`, `test_fields_artifacts_comma_list`, `test_fields_array_wikilink_already_wrapped` pass |
| 2 | `--fields parent=…` triggers parent subtasks backlink | PASS | `_backlink_parent` + `run()` (create.py:271-291, 395-426); test `test_parent_backlink_via_fields_flag` confirms |
| 3 | Missing parent fails before write | PASS | `run()` resolves parent before child create at create.py:395-406; test `test_parent_missing_fails_before_write` asserts no child written on exit code 1 |
| 4 | Re-creating existing child link is idempotent | PASS | `_backlink_parent` early-returns when child link already in subtasks (create.py:282-283); test `test_parent_backlink_idempotent` confirms count==1 |
| 5 | `--help` documents array-field syntax | PASS | `--fields` help text (create.py:196-204) explicitly documents wikilink array fields + comma-separated refs + parent backlink — confirmed via live `artifacts create --help` |
| 6 | `artifacts-os` skill `### Create` section updated | PASS | `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` `### Create` section (lines 93-104) now documents comma-separated lists, wikilink array fields with auto-wrap, and parent-backlink semantics. `.openstation/skills/artifacts-os/SKILL.md` is a symlink to the same file |
| 7 | Tests cover all four cases | PASS | `tests/cli/test_create.py` contains 8 new tests including array set, backlink via both `--parent` and `--fields`, missing parent, idempotency, multiple children, pre-wrapped refs; 46/46 pass |

### Summary

7 passed, 0 failed. All verification criteria met.

## References

Surfaced during filing of:
- [[t0157-book-local-distro-mode]] — `depends_on` couldn't be set via `--fields`
- [[t0158-implement-artbook-v2-schema]] — same
- [[t0150-artbook-distribution-model]] / [[t0151-spec-the-artbook-model]] — parent's `subtasks` array not auto-populated when filed via `--fields`

Related (separate body-handling bugs already in queue):
- [[t0147]] / [[t0148]] — `openstation create --body-file` silent failures
## Findings

Implemented both gaps. No architectural surprises.

**Array wikilink fields** (`_parse_fields`):
- Added `_SCALAR_WIKILINK_FIELDS = {"parent"}` and `_ARRAY_WIKILINK_FIELDS = {"depends_on", "subtasks", "artifacts"}`.
- Added `_array_wikilink_fields_from_schema` — detects additional wikilink array fields from the kind schema's `items.pattern` at runtime.
- `_parse_fields` now accepts `schema=` kwarg. Array wikilink fields always produce a list (single value → one-element list) with each element wrapped as `[[…]]`. Scalar wikilink fields keep the existing wrap-in-place behavior.
- Chosen syntax: comma-separated — `--fields depends_on=t0001,t0002` — already partially implemented and documented in `--help`.

**Parent backlink** (`_backlink_parent` + `run`):
- `run()` resolves parent *before* writing the child. Missing parent → `error:` + exit 1, no orphan.
- After child is created, `_backlink_parent` atomically appends `[[child-stem]]` to parent's `subtasks` (tmp → `os.replace`). Idempotent.
- Both `--parent REF` and `--fields parent=REF` trigger the backlink.

**Tests**: 8 new tests cover array set, backlink via both flag paths, missing parent, idempotency, multiple children, pre-wrapped refs. 3 existing tests updated to create the parent first (required by the new validation rule). 46/46 pass.

**Docs**: `--fields` help text updated in `register()`; `artifacts-os` skill `### Create` section updated with comma-separated array syntax and parent-backlink behaviour.