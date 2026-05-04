---
kind: task
id: t0066
name: improve-date-handling-in-artifact
type: spec
status: backlog
assignee: architect
owner: user
created: 2026-05-02
---

# Improve Date Handling In Artifact Frontmatter

## Context

Discovered while investigating which fields the CLI auto-fills on create. Several gaps exist in how dates are modeled and written:

1. **`created` is auto-filled in the CLI layer, not core.** `src/artifacts_os/cli/commands/create.py` (line 254) does `fields.setdefault('created', date.today())`. Direct callers of `core.store.create()` get no `created` field. Inconsistent contract: core says "the body and these fields are what you give me," but the CLI silently augments.

2. **`created` is date-only (no time).** Stored as `created: 2026-05-02`. View formatters in `src/artifacts_os/views/_views.py` already accept full ISO datetime (`fmt="datetime"` → `YYYY-MM-DD HH:MM`), so the column path is ready, but the writer never produces time. Sorting by `-created` cannot disambiguate same-day artifacts.

3. **No `updated` / `modified` field exists.** `core.store.update()` rewrites frontmatter atomically but never stamps a modification time. `artifacts status t0042 done` and any future field-update command leave no trace in the artifact itself (the JSONL event log captures it, but the artifact is opaque).

4. **No spec covers this today.** `docs/adding-a-kind.md` doesn't mention `created`; no kind schema declares it under `properties`. It's a de-facto convention enforced only by the CLI.

## Requirements

The spec must decide and document:

- **R1.** Date format for `created` — keep `YYYY-MM-DD` or move to ISO datetime (e.g. `2026-05-02T07:11:12+00:00`). Document trade-offs (sort granularity, YAML quoting, backward compatibility with existing artifacts).
- **R2.** Whether to introduce `updated` (or `modified`) as a tracked field. If yes: which writes update it (`core.store.update`, status change, future field-update commands), and whether old artifacts get back-filled.
- **R3.** Where auto-population lives — core vs CLI. Recommendation: move to `core.store.create` / `core.store.update` so all callers (CLI, tests, future programmatic users) get consistent behavior.
- **R4.** Schema contract — should `created`/`updated` be declared under `properties` in shipped kind schemas, or stay implicit "core-managed" fields? If declared, decide whether `x-required-fields` should include them.
- **R5.** Migration plan — how existing artifacts with `created: 2026-04-30` (date only) coexist with any new format. View formatters already tolerate both; document the policy.
- **R6.** Output artifacts — the spec doc itself (e.g. `docs/specs/sNNNN-date-handling.md` or under `artifacts/specs/`), plus a follow-up implementation task referencing it.

## Verification

- [ ] Spec document committed (under `docs/` or `artifacts/specs/`) covering R1–R5
- [ ] Each decision (R1–R4) is explicitly marked **decided** vs **recommended** vs **needs research**
- [ ] Trade-offs documented for the chosen `created` format (date vs datetime) including impact on YAML output, sort behavior, and `views/_views.py` parsing
- [ ] Migration policy for existing artifacts is written and approved
- [ ] Follow-up implementation task created in `backlog` referencing the spec
- [ ] `docs/adding-a-kind.md` updated (or queued for update in the impl task) to document core-managed fields
