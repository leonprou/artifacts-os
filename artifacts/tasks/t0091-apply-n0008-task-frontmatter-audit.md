---
assignee: developer
created: 2026-05-03
id: t0091
kind: task
name: apply-n0008-task-frontmatter-audit
owner: user
status: done
type: implementation
completed: 2026-05-04
---

## Source of truth

[[n0008-task-frontmatter-audit]] — the audit is binding; this task is a brief over D1–D5 and the migration steps they imply.

## Requirements

1. **Schema (D1–D5)** — `artifacts/kinds/task.json`:
   - declare every field a task carries today (`id`, `kind`, `name`, `created`, `started`, `completed`, `status`, `type`, `priority`, `assignee`, `owner`, `parent`, `subtasks`, `depends_on`, `artifacts`) with the right JSON Schema type;
   - `required: [id, kind, name, created, type, status, assignee, owner]`;
   - wikilink fields (`parent`, `subtasks`, `depends_on`, `artifacts`) carry `pattern: ^\[\[.+\]\]$`;
   - `additionalProperties: false`.
2. **Validator** — `src/artifacts_os/core/validate.py` and `src/artifacts_os/core/store.py`: pre-coerce `datetime.date` / `datetime.datetime` (which YAML auto-parses) to ISO strings before `jsonschema` validation, so `type: string` works on `created` / `started` / `completed` for both reads and creates.
3. **Data migration** — strip the three dead fields from existing tasks and fix the one null `assignee`:
   - `summary` from t0014, t0015, t0020, t0021, t0022, t0023;
   - `aliases: []` and `tags: []` from t0038, t0069;
   - `assignee: null` → `assignee: ""` on t0088;
   - clean stray YAML block-scalar remnants in t0015 and t0020 left by the strip pass.
4. **Verify** — `artifacts validate --kind task` reports 88/88 valid (post-migration count; this task itself bumps the total when filed).

## Out of scope

- **Date format enforcement** — `format: date` on `created` / `started` / `completed`. Would require normalising t0001's `started: 2026-04-20 15:13:25` (datetime-with-space) and turning on jsonschema's format checker. File as follow-up if/when wanted.
- **Cross-kind audit** — same audit on `note.json`, `research.json`, `spec.json`. Each kind has its own surface; one task per kind, not bundled.
- **Doc/spec drift** — `docs/adding-a-kind.md` § frontmatter table and `s0017 § 7` still describe the dropped `applies_to` / `placeholder_syntax` / `schema_version`. Separate documentation task.

## Test plan

- `artifacts validate --kind task` — full task vault must report 0 errors.
- `pytest tests/core/test_validate.py` — 15/15 pass.
- `pytest tests/core/test_store.py` — passes (validates the coercion helper on create).
- `pytest -q` — no new failures vs `main`. Pre-existing failures in `tests/ai/test_body_loader.py`, `tests/cli/test_settings.py`, `tests/test_module_system.py` are unrelated.

## Verification

- [ ] `artifacts/kinds/task.json` declares 16 properties (universal core + lifecycle + relationships + categorisation) with `required: [id, kind, name, created, type, status, assignee, owner]`.
- [ ] `task.json` carries `additionalProperties: false`.
- [ ] `parent`, `subtasks`, `depends_on`, `artifacts` carry the wikilink `pattern: ^\[\[.+\]\]$`.
- [ ] `core/validate.py` and `core/store.py` coerce `datetime.date` / `datetime.datetime` to ISO strings before jsonschema validation.
- [ ] `artifacts validate --kind task` reports 0 errors across the vault.
- [ ] No `summary`, `aliases`, or `tags` field remains on any task artifact.
- [ ] `pytest tests/core/test_validate.py` passes (15/15).
- [ ] `pytest -q` shows no new failures vs `main` (the 13 pre-existing failures are unrelated).
- [ ] Reviewed and approved by user.