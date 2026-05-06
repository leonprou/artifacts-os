---
assignee: ''
created: 2026-05-05
id: t0104
kind: task
name: generic-release-skill-uses-tasks
owner: user
status: done
type: feature
subtasks:
  - "[[t0106-implement-task-aware-release-changelog]]"
completed: 2026-05-06
---

## User story

> **As a release operator across any OpenStation-managed pip
> package, I want one task-aware release-changelog skill that reads
> project shape from `CLAUDE.md` and enriches each entry with the
> originating task's intent (`name`, `## Goal`, `## Findings`) — so
> the changelog reflects structured intent instead of just commit
> subjects, and we don't maintain two parallel copies of the skill
> across artifacts-os and OpenStation.**

## Why this exists

Today there are two near-identical release skills:

- `~/workspace/os/open-station/.openstation/skills/release-changelog/SKILL.md`
- `src/artifacts_os/ai/claude/skills/artifacts-release/SKILL.md`

Both are purely git-driven (commit subject + file paths). Neither
consults `artifacts/tasks/` even though every commit threads a
`(tNNNN)` task ID through its subject, and tasks carry the richest
structured intent in either repo (`name`, `type`, `parent`,
`## Goal`, `## Findings`).

The duplication and the missed task signal are linked: once the
skill assumes the OpenStation task contract, the only thing that
varies between projects is module taxonomy and release checklist —
and those naturally live in each project's `CLAUDE.md`.

## Scope (intent, not contract — spec to be authored)

- **One generic skill**, project-agnostic in shape, that runs in
  any OpenStation-managed repo.
- **`CLAUDE.md` as the project contract** — the skill reads
  project-specific shape (domain categories, file-path → category
  map, release checklist) from a structured section in `CLAUDE.md`.
- **OpenStation tasks as a hard assumption** — the skill expects
  `artifacts/tasks/<id>-<slug>.md` to exist with the standard
  frontmatter and body conventions; falls back gracefully when a
  commit lacks `(tNNNN)` or the referenced task is missing.
- **Enrichment over replacement** — task metadata enriches the
  changelog (better headlines, better bodies, parent-grouping) but
  git history remains the source-of-truth for what's *in* the
  release range.
- **Migration path** — replaces both `release-changelog` (in
  OpenStation) and `artifacts-release` (in artifacts-os) without
  silent regressions in either repo's release flow.

## Out of scope

- Changes to the release *workflow* itself
  (`.github/workflows/release.yml`). Just the changelog-drafting
  skill.
- Changes to commit conventions. The `(tNNNN)` trailer is already
  the de-facto standard.
- New task-aware features in the broader `artifacts` CLI. This
  task is purely about the skill.
- OpenStation's adoption of the new skill. Filed as a downstream
  task in the OpenStation repo once the artifacts-os migration
  proves out.

## Decomposition

1. **Spec the contract** — `architect` —
   [[t0105-spec-generic-release-skill-contract]]. Produced
   [[s0020-release-changelog-skill-contract]], which locks 14
   decisions covering project shape (`## Release` inline in
   `CLAUDE.md`), task resolution (`(tNNNN)` trailer regex + glob),
   body-field precedence (Findings → Goal → commit subject),
   multi-trailer + parent/sub-task collapse, fallback-never-fails
   discipline (with one hard error: malformed `## Release`),
   skill canonical home (artifacts-os wheel), clean-swap
   migration, and OpenStation-as-downstream.
2. **Implement and migrate** — `developer` —
   [[t0106-implement-task-aware-release-changelog]]. Originally
   two separate steps (implement + migrate); collapsed into one
   sub-task because spec D10 mandates a clean swap in a single
   release of artifacts-os. Covers spec § 8 in full: author the
   new SKILL.md, paste the `## Release` section into `CLAUDE.md`
   verbatim per § 5.2, remove the old `artifacts-release/`
   directory, widen `install.py`'s skill namespace allowlist,
   update the repo dogfood symlink, add the test suite from § 6.
3. **OpenStation downstream** — out of scope here; filed as a
   separate task in the OpenStation repo once the artifacts-os
   migration proves out.

## Subtasks

- [[t0105-spec-generic-release-skill-contract]] — spec
  (architect) — produced
  [[s0020-release-changelog-skill-contract]]. Awaiting user
  approval on the spec to close.
- [[t0106-implement-task-aware-release-changelog]] —
  implementation (developer) — `backlog`, blocked on t0105
  reaching `done`.

## Verification

Finalised against the spec's § 6 test plan. Each item maps to a
spec section so a reviewer can trace it back to a locked
decision. Status transitions on sub-tasks and their produced
artifacts are tracked separately; verification here is about
observable behaviour of the shipped skill.

- [ ] After `pip install -e . && artifacts init` in a fresh
      vault,
      `<vault>/.claude/skills/release-changelog/SKILL.md` is a
      working symlink resolving into the package source — and
      the package no longer ships
      `artifacts-release/SKILL.md` (spec D9, D10).
- [ ] In a vault that previously had
      `<vault>/.claude/skills/artifacts-release/SKILL.md`,
      `artifacts ai install` after the upgrade prunes the
      orphan symlink (spec D10, § 6.6).
- [ ] artifacts-os `CLAUDE.md` contains the `## Release`
      section verbatim from spec § 5.2 (Domain Categories,
      File Path Mapping, Checklist, Exclusions).
- [ ] End-to-end on artifacts-os `main`: drafting the next
      release with the new skill produces a CHANGELOG entry
      whose bullets reference task `name` (and Findings/Goal
      text) for every commit carrying a `(tNNNN)` trailer
      (spec § 6.2).
- [ ] Commits without `(tNNNN)` produce a draft bullet from
      the commit subject and surface in the Step 6 Fallbacks
      summary — never fail the skill (spec § 6.3, D8).
- [ ] A missing or malformed `## Release` section in
      `CLAUDE.md` halts after Step 1 with the D14 error
      message — no partial draft is written (spec § 6.4, D14).
- [ ] Multi-trailer commits and parent/sub-task collapse
      render per D6 and D7 (spec § 6.5).
- [ ] Layer isolation: pre/post directory hash for
      `artifacts/tasks/` and `artifacts/log/` is identical
      after a full skill run (spec § 6.1).
- [ ] CHANGELOG round-trip: Step 0 idempotency check fires for
      an existing `## v<VERSION>` heading; the skill's emitted
      entry parses through the same regex on subsequent runs
      (spec § 6.7, D12).
- [ ] Full test suite green; no module DAG violations
      (`core` → `views` → `cli`,`tui`; `core` → `log` → `ai`).
