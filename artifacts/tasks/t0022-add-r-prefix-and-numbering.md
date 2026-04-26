---
kind: task
id: t0022
name: add-r-prefix-and-numbering
type: implementation
status: verified
assignee: developer
owner: project-manager
created: 2026-04-26
summary: >
  Give the research kind an "r" prefix and numbered IDs so research
  artifacts follow the same naming pattern as tasks (t) and specs
  (s).
started: 2026-04-26
---

# Add `r` Prefix and Numbering to Research Kind

## Background

Today the research kind has no prefix and no numbering — research
files are stored as `artifacts/research/<slug>.md`. Tasks and specs
both use a single-letter prefix and numeric IDs (`t0042-…`,
`s0007-…`), and `artifacts kinds` makes the inconsistency visible:

```
agent     agents     (none)   no    active, inactive
research  research   (none)   no    draft, done           ← outlier
spec      specs      s        yes   draft, review, ...
task      tasks      t        yes   backlog, ready, ...
```

There are no existing research artifacts in this vault
(`artifacts/research/.gitkeep` is the only file, confirmed via
`artifacts list -k research` returning empty), so the change is
purely a config update with no migration cost.

Agents are intentionally non-numbered (named entities, not items in
a stream) and are out of scope.

## What to change

Update the **research** kind in two places — the live vault schema
and the `init` bootstrap template — so future projects get the same
shape.

### 1. `artifacts/kinds/research.json`

```json
{
  "x-dir": "research",
  "x-prefix": "r",
  "x-numbered": true,
  "x-columns": ["id", "name", "created:date", "status"],
  "title": "Research",
  "type": "object",
  "properties": {
    "status": {
      "enum": ["draft", "done"]
    }
  }
}
```

Changes vs. current:
- `x-prefix`: `""` → `"r"`
- `x-numbered`: `false` → `true`
- `x-columns`: prepend `"id"` so the new ID surfaces in
  `artifacts list -k research` output. Keep `created:date` — useful
  context for research listings.

### 2. `src/artifacts_os/cli/commands/init.py`

The `_DEFAULT_KINDS["research"]` entry (lines 64–72) must mirror
the same change so `artifacts init` produces the new shape. Apply
the same field updates.

### 3. Tests

If `tests/cli/test_init.py` (or any other test) asserts the
research schema content, update those assertions to match. A grep
for `"research"` across `tests/` will surface the spots.

No new tests required — existing kind/registry/init coverage
already exercises the prefix+numbered code paths via tasks and
specs.

---

## Out of Scope

- Renaming or numbering existing research files (there are none).
- Changing the agent kind to be numbered.
- Adding new statuses or columns beyond what's specified above.

---

## Progress

### 2026-04-26 — developer
> time: 20:16

Updated `artifacts/kinds/research.json` and `_DEFAULT_KINDS["research"]` in `init.py`: `x-prefix` `""` → `"r"`, `x-numbered` `false` → `true`, `x-columns` prepends `"id"`. All 150 tests pass. Smoke test confirmed `r0001-test-note.md` created with `id: r0001` (then reverted). `artifacts kinds` shows research with prefix `r`, numbered `yes`.

## Verification

- [x] `artifacts/kinds/research.json` has `"x-prefix": "r"`, `"x-numbered": true`, and `"id"` is the first entry in `x-columns`
- [x] `src/artifacts_os/cli/commands/init.py` `_DEFAULT_KINDS["research"]` matches the same shape
- [x] `artifacts kinds` (against this repo) shows `research` with prefix `r`, numbered `yes`
- [x] `artifacts create --kind research "test note"` (manual smoke test) creates `artifacts/research/r0001-test-note.md` with `id: r0001` in frontmatter — then revert the smoke test file before committing
- [x] `pytest` — full suite passes
- [x] Fresh `artifacts init` in a tmp dir produces `artifacts/kinds/research.json` with the new shape
- [x] No existing research artifacts were renamed or modified (the directory only contained `.gitkeep`)

## Verification Report

*Verified: 2026-04-26*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `research.json` has `x-prefix: "r"`, `x-numbered: true`, `id` first in `x-columns` | PASS | File confirms all three fields exactly as specified |
| 2 | `init.py` `_DEFAULT_KINDS["research"]` matches same shape | PASS | Lines 64–72 of `init.py` show identical values |
| 3 | `artifacts kinds` shows research with prefix `r`, numbered `yes` | PASS | Live output confirms `r` / `yes` in the table |
| 4 | Smoke test: `r0001-test-note.md` created then reverted | PASS | Progress note documents smoke test was run and reverted; research dir contains only `.gitkeep` |
| 5 | `pytest` — full suite passes | PASS | 150 passed in 0.56s |
| 6 | Fresh `artifacts init` produces correct `research.json` | PASS | `tmp` init output matches spec exactly |
| 7 | No existing research artifacts renamed/modified | PASS | `artifacts/research/` is empty (only `.gitkeep`) |

### Summary

7 passed, 0 failed. All verification criteria satisfied.
