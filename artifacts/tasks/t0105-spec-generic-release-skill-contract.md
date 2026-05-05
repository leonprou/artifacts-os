---
artifacts:
  - '[[s0020-release-changelog-skill-contract]]'
assignee: architect
created: 2026-05-05
id: t0105
kind: task
name: spec-generic-release-skill-contract
owner: user
parent: '[[t0104-generic-release-skill-uses-tasks]]'
status: done
type: spec
started: 2026-05-05
completed: 2026-05-05
---

# Spec — Generic, Task-Aware Release-Changelog Skill

## Context

Sub-task of `[[t0104-generic-release-skill-uses-tasks]]`. The
parent task ships a single generic release-changelog skill that
replaces both today's project-specific copies
(`artifacts-release` in artifacts-os, `release-changelog` in
OpenStation) by lifting project shape into `CLAUDE.md` and
enriching changelog entries from OpenStation task artifacts.

Read t0104 for the user story, scope, and rationale. This task
produces the locked design — a `spec` artifact — that the
implementation sub-task will consume.

## Goal

Produce an approved `spec` artifact that locks the contract for
the generic release-changelog skill: where project-specific shape
lives, how task references resolve, what the fallback rules are,
where the skill canonically lives, and how the migration from
`artifacts-release` lands without regressing today's release flow.

## Scope

The spec must lock at least these decisions:

1. **Where does project shape live?**
   - Inline in `CLAUDE.md` — a structured `## Release` (or named)
     section the skill parses by heading + table conventions?
   - Or a pointer from `CLAUDE.md` to a dedicated config file
     (e.g. `artifacts/release.yaml`, `docs/release.md`)?
   - Pick one. Document the parsing/reading rules so the skill
     body is unambiguous.

2. **What does `CLAUDE.md` (or the pointed-to file) declare?**
   - Domain category list (the `### CLI`, `### Core`, etc.
     headings the changelog uses).
   - File-path → category mapping (path prefix or glob →
     category).
   - Release checklist (which files to bump, what commit message
     prefix, which branch, which command).
   - Any project-specific exclusions (paths or commit patterns to
     drop).

3. **Task-resolution rules.**
   - How are `(tNNNN)` trailers extracted from commit subjects?
     (Lock the regex.)
   - How does the skill locate `artifacts/tasks/<id>-<slug>.md`?
     (Glob on `<id>-*.md` after walking up to the vault marker?
     Use `core` API directly?)
   - What does the skill use from each task — `name`, `type`,
     `parent`, `## Goal`, `## Findings`? In what precedence for
     headlines vs descriptions?
   - Multi-trailer commit (e.g. `feat: ... (t0099, t0100)`) —
     pick the first, the most prominent, all of them?
   - Sub-task and parent both touched in the range — collapse
     under parent, keep both lines, or let the spec define a
     collapse rule by `type`?

4. **Fallback rules.**
   - Commit lacks `(tNNNN)` — use commit subject (today's
     behaviour); flag in the present-for-review step.
   - Task referenced but file missing — warn, fall back to
     commit subject; never fail the skill.
   - Task file present but body lacks `## Findings` *and*
     `## Goal` — fall back to commit subject; flag.

5. **Where does the skill canonically live?**
   - Ship from artifacts-os via the t0096 wheel-borne
     `ai/claude/skills/` mechanism (most natural — `core` API
     for vault discovery is already there)?
   - OpenStation installs it transitively when it depends on
     artifacts-os, or vendors the file?
   - Pick one. Spell out the install path in artifacts-os's
     vault and how OpenStation's vault gets the same file.

6. **Migration story.**
   - Replace today's `artifacts-release` with the new generic
     `release-changelog` (clean swap)?
   - Or keep `artifacts-release` as a thin alias / preset that
     delegates to the generic skill?
   - Decide which, and define the deprecation window for the
     old name.
   - Same question conceptually applies to OpenStation's
     `release-changelog`, but OpenStation adoption is a
     downstream task — this spec only names the contract
     OpenStation will consume.

7. **Test plan.**
   - End-to-end against artifacts-os: drafting the next release
     from current `main` with the new skill produces an entry
     that mentions task names (not just commit subjects).
   - Fallback: a commit with no `(tNNNN)` is still represented
     in the draft.
   - Negative: a commit referencing a missing task file produces
     a warning, not a failure.
   - Project-shape parsing: a deliberately malformed `## Release`
     section in `CLAUDE.md` surfaces a clear error.
   - Layer-isolation: the skill never writes to
     `artifacts/tasks/` and never modifies frontmatter — it is a
     read-only consumer.

8. **Backwards compatibility.**
   - Today's `artifacts-release` invocation pathway must
     continue to produce a sensible draft until migration
     completes — define the transition (alias? cutover?
     deprecation note?).
   - Existing `CHANGELOG.md` format must remain valid input for
     the skill's idempotency check (Step 0).

## Source of truth

- `[[t0104-generic-release-skill-uses-tasks]]` — parent task
  with the user story, scope, and out-of-scope markers.
- `~/workspace/os/open-station/.openstation/skills/release-changelog/SKILL.md`
  — current OpenStation skill (purely git-driven). Reference for
  workflow shape only.
- `src/artifacts_os/ai/claude/skills/artifacts-release/SKILL.md`
  — current artifacts-os skill. Direct ancestor.
- `[[t0100-set-up-release-flow-and]]` — shipped the
  `artifacts-release` skill. Findings section documents what's
  installed.
- `[[t0096-ship-artifacts-os-skill-md]]` — shipped the
  wheel-borne skill install plumbing this task assumes.
- `CLAUDE.md` — the file the spec proposes to extend with a
  project-shape section.

## Constraints

- **Read-only consumer of tasks.** The skill must never mutate
  task artifacts, frontmatter, or the JSONL log.
- **Single skill file.** No multi-file skill packages; the
  workflow fits in one `SKILL.md` per the existing convention.
- **No new module dependencies in artifacts-os.** The skill is
  agent-layer (LLM instructions); it does not introduce new
  Python imports.
- **OpenStation adoption is downstream.** This spec defines the
  contract OpenStation will adopt; it does not block on
  OpenStation changes.

## Deliverable

A `spec` artifact (next free `s00XX` ID — currently `s0020`)
that satisfies scope items 1–8 above, with `status: approved`
after user review. The implementation sub-task spawned by the
PM will consume this spec without further design debate.

## Verification

- [x] A `spec` artifact is filed (architect picks the title and
      slug per `artifacts/kinds/spec/ARTIFACT.md` conventions).
- [x] The spec locks decisions on all eight scope items above.
- [x] `## Goals` / `## Non-goals` are explicit; OpenStation
      adoption is named in `## Non-goals`.
- [x] The spec engages the two existing skills
      (`artifacts-release` and OpenStation's `release-changelog`)
      via a LOCK / LOCK-WITH-EDIT / REJECT table for what
      carries forward.
- [x] Test plan section names every property the implementation
      must verify, in language the developer can turn into
      pytest cases or skill-runner end-to-end checks.
- [x] `CLAUDE.md` contract is fully specified — an example
      structured section is included so the developer can copy
      it into this repo's `CLAUDE.md` verbatim.

## Verification Report

*Verified: 2026-05-05*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | A `spec` artifact is filed per kind conventions. | PASS | `artifacts/specs/s0020-release-changelog-skill-contract.md` exists; frontmatter has `kind: spec`, `id: s0020`, slug `release-changelog-skill-contract` (≤5 words, hyphenated, lowercase), `task: "[[t0105-...]]"`, `agent: architect`. |
| 2 | The spec locks decisions on all eight scope items. | PASS | § 3 enumerates 14 decisions (D1–D14). Mapping: shape location D1/D2 (item 1); CLAUDE.md content D1/D2/D13/D14 + § 5.2 (item 2); task resolution D3/D4/D5/D6/D7 (item 3); fallback rules D8/D14 (item 4); canonical location D9 (item 5); migration D10/D11 (item 6); test plan § 6 (item 7); backwards compat D10/D12 (item 8). |
| 3 | `## Goals` / `## Non-goals` explicit; OpenStation adoption named in Non-goals. | PASS | § 2.1 lists 7 goals; § 2.2 lists 6 non-goals; first bullet of § 2.2 is "OpenStation adoption". |
| 4 | Engagement table classifies both ancestor skills as LOCK / LOCK-WITH-EDIT / REJECT. | PASS | § 4.1 (artifacts-release) covers Steps 0–8 + auxiliary sections with verdicts; § 4.2 (OpenStation release-changelog) covers Steps 0–8 plus the file-location verdict. Both tables use the exact LOCK / LOCK-WITH-EDIT / REJECT vocabulary. |
| 5 | Test plan names every property the implementation must verify in pytest/E2E-actionable language. | PASS | § 6 has 7 grouped sub-sections (layer isolation, end-to-end enrichment, fallbacks, hard error, multi-trailer + collapse, migration, idempotency). Each bullet states a concrete observable assertion (hash equality, presence of named line, halt behaviour, etc.). |
| 6 | `CLAUDE.md` contract fully specified with verbatim example. | PASS | § 5.2 contains a full ```markdown fenced block with `## Release`, `### Domain Categories`, `### File Path Mapping` (table populated for every artifacts-os module), `### Checklist` (4 numbered steps), and `### Exclusions` (3 entries) — copy-paste ready. |

### Summary

6 passed, 0 failed. All verification criteria met. The architect
produced a content-complete spec; this task is ready to close.
Spec approval (`s0020` status `review` → `approved`) is a separate
lifecycle gate owned by the user and is not part of this task's
verification.

## Progress

### 2026-05-05 — architect
> time: 18:17

Filed [[s0020-release-changelog-skill-contract]] (`status: review`).
Locked 14 decisions covering all eight scope items: project shape
inline in `CLAUDE.md` `## Release` section (D1–D2); trailer regex
and glob-based task resolution (D3–D4); body-field precedence
Findings → Goal → commit subject (D5); multi-trailer and
parent/sub-task collapse rules (D6–D7); fallbacks never fail
except for missing/malformed `## Release` (D8, D14); skill ships
from artifacts-os wheel and clean-swap migration (D9–D10);
OpenStation downstream (D11); CHANGELOG round-trip preserved
(D12); routing precedence (D13). Engagement table classifies
every step of `artifacts-release` and OpenStation's
`release-changelog` as LOCK / LOCK-WITH-EDIT / REJECT. Test plan
groups by property (layer isolation, enrichment, fallback, hard
error, collapse, migration, idempotency). Verbatim `## Release`
section provided in § 5.2 for paste into this repo's `CLAUDE.md`.
Task → `review`; spec → `review` (awaiting user gate).

## Findings

Filed [[s0020-release-changelog-skill-contract]] (`status: review`,
awaiting user approval). The spec locks 14 decisions (D1–D14)
covering all eight scope items from the task brief.

**Headline decisions:**

- **D1, D2** — Project shape lives **inline** in `CLAUDE.md` under
  a structured `## Release` section with four well-known H3
  subsections: `### Domain Categories`, `### File Path Mapping`,
  `### Checklist`, `### Exclusions` (optional). No separate config
  file. Rationale: every artifacts-os project already has
  `CLAUDE.md`, the H2/H3+table grammar matches existing
  conventions, and one file avoids a path-resolution step.
- **D3, D4** — Trailer regex
  `\(\s*t(\d{4,})(?:\s*,\s*t(\d{4,}))*\s*\)` applied to commit
  subjects; tasks resolved by globbing
  `<vault>/artifacts/tasks/t<id>-*.md` after walking up to the
  `artifacts/artifacts.yaml` marker. The skill stays
  agent-layer — no `import artifacts_os` from the skill body.
- **D5, D6, D7** — Body-field precedence is `## Findings` →
  `## Goal` → commit subject. Multi-trailer commits title with
  the first ID and append `(also tNNNN)`. Parent + sub-task
  collapse into one bullet with sub-bullets when both have
  commits in range; sub-tasks render flat when the parent has
  no commits in range (no synthetic parent line).
- **D8, D14** — Task-resolution fallbacks (missing trailer,
  missing file, empty body) **never fail** the skill — they emit
  a draft and are flagged in Step 6. The single hard error is a
  missing/malformed `## Release` section in `CLAUDE.md`, which
  halts after Step 1 with a fix-up pointer.
- **D9, D10** — Skill ships from artifacts-os at
  `src/artifacts_os/ai/claude/skills/release-changelog/SKILL.md`
  (rides the t0096 wheel-borne install). Migration is a clean
  swap: remove `artifacts-release`, add `release-changelog`,
  let `install.py` prune the orphan vault directory on the next
  `artifacts ai install` run. No alias, no deprecation window.
- **D11** — OpenStation adoption is non-goal; spec only documents
  the contract OpenStation will consume in a downstream task.
- **D12, D13** — `CHANGELOG.md` format (`## v<VERSION>` + H3
  categories + bold-em-dash bullets) is preserved verbatim.
  Routing precedence: exclusions → `fix:` override → longest
  path-prefix match → `Architecture` fallback.

**Engagement table (§ 4)** classifies every step of both
ancestor skills (`artifacts-release` and OpenStation's
`release-changelog`) as LOCK / LOCK-WITH-EDIT / REJECT. The two
hard-coded path → category maps are REJECTed; the workflow
shape (Steps 0–8) is locked.

**Surfaces (§ 5)** pin the skill frontmatter, install paths, and
provide a verbatim `## Release` section the developer can paste
into artifacts-os's `CLAUDE.md`.

**Test plan (§ 6)** groups assertions by property: layer
isolation (no writes to tasks/JSONL), end-to-end enrichment,
fallback non-failure, hard error on malformed `## Release`,
multi-trailer + parent collapse, migration prune, and
`CHANGELOG.md` round-trip.

**Implementation notes (§ 8)** pre-populate the follow-up
sub-task's scope: author the SKILL.md, add `## Release` to
`CLAUDE.md`, remove the old skill, widen `install.py`'s skill
namespace allowlist to permit a non-`artifacts-` prefix, and
add tests per § 6.

## Downstream

- **Implementation sub-task (next)** — to be filed by the PM
  against [[t0104-generic-release-skill-uses-tasks]]'s
  decomposition step 2 once this spec is `approved`. Inputs are
  spec § 4 (engagement), § 5 (surfaces), § 6 (test plan), and
  § 8 (implementation notes).
- **`install.py` namespace allowlist widening** — small
  mechanical change owned by the implementation sub-task; flagged
  here so the developer does not re-derive it from the spec.
- **Migration sub-task** — flipping artifacts-os to the new
  skill (decomposition step 3 of t0104) is a sibling of the
  implementation sub-task and consumes the same spec.
- **OpenStation downstream task** — out of scope here; filed in
  the OpenStation repo once the artifacts-os migration proves
  out. The spec's D11 names the contract OpenStation will
  consume.
