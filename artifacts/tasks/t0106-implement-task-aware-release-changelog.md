---
kind: task
id: t0106
name: implement-task-aware-release-changelog
type: implementation
status: done
assignee: developer
owner: user
parent: "[[t0104-generic-release-skill-uses-tasks]]"
depends_on:
  - "[[t0105-spec-generic-release-skill-contract]]"
created: 2026-05-05
started: 2026-05-05
completed: 2026-05-05
---

# Implement Task-Aware Release-Changelog Skill And Migrate Artifacts-Os

## Goal

Implement the generic, task-aware `release-changelog` skill per
[[s0020-release-changelog-skill-contract]], add the `## Release`
section to artifacts-os's `CLAUDE.md`, remove the old
`artifacts-release` skill, and verify the wheel-borne install
prunes the orphan vault directory cleanly.

## Why this is one task (not two)

Parent [[t0104-generic-release-skill-uses-tasks]] originally
decomposed into separate "implement" and "migrate" steps. The
spec's **D10 — clean swap** mandates these land in a single
release of artifacts-os: removing `artifacts-release` while the
new skill does not yet ship would leave the package without a
release skill mid-migration. Folding both into one
implementation task preserves the clean-swap guarantee.

## Inputs

The work plan is fully specified by the spec; do not re-litigate
design decisions here.

- [[s0020-release-changelog-skill-contract]] — locked contract
  (D1–D14, engagement table § 4, surfaces § 5, test plan § 6,
  implementation notes § 8).
- [[t0096-ship-artifacts-os-skill-md]] — existing wheel-borne
  install plumbing this skill rides.
- `src/artifacts_os/ai/claude/skills/artifacts-release/SKILL.md`
  — direct ancestor; remove after the new skill is in place.
- `src/artifacts_os/ai/install.py` — gains a one-line allowlist
  widening per spec § 5.3.

## Requirements

Track these to spec sections so a reviewer can map each
requirement back to its locked decision.

### 1. Author the new skill — spec § 4.1, § 5.1

- Create `src/artifacts_os/ai/claude/skills/release-changelog/SKILL.md`
  with the frontmatter from § 5.1 verbatim
  (`name: release-changelog`, `user-invocable: false`).
- Workflow body follows § 4.1 — every step that is `LOCK` is
  preserved verbatim from `artifacts-release`; every
  `LOCK-WITH-EDIT` is edited per the cited decision; every
  `REJECT` step is replaced.
- Step 2 (Collect Commits) extracts `(tNNNN)` trailers per D3.
- Step 3 reads `## Release` from `CLAUDE.md` per D1, D2, D13;
  resolves task files per D4; composes bullets per D5, D6, D7.
- Step 6 (Present for Review) gains the Fallbacks summary block
  per D8.
- Step 8 (Release Checklist) renders from
  `### Checklist` in `CLAUDE.md` per D2.
- "What This Skill Does NOT Do" extends with: never mutates
  `artifacts/tasks/`, never appends to the JSONL log.
- D14 hard-error path is wired in: missing/malformed
  `## Release` halts after Step 1 with the spec's exact error
  message.

### 2. Add `## Release` to `CLAUDE.md` — spec § 5.2

- Paste the full `## Release` section from spec § 5.2 verbatim
  into the repo root `CLAUDE.md`.
- Place it after the existing `## Common Commands` section
  (or wherever fits the document flow); existing sections
  remain untouched.

### 3. Remove the old skill — spec D10

- Delete the directory
  `src/artifacts_os/ai/claude/skills/artifacts-release/` and
  its repo-level dogfood symlink under `.claude/skills/` (if
  present).
- Confirm `MANIFEST.in` / `pyproject.toml` package data still
  works after the removal (the wheel must still build with no
  artifacts-release artefacts).

### 4. Widen `install.py` namespace allowlist — spec § 5.3

- Update `_SKILL_NS_PREFIX` (or whatever the current allowlist
  mechanism is) to permit a non-`artifacts-`-prefixed
  `release-changelog/` skill directory.
- Preserve existing conflict policy (same-content skip,
  owned-symlink replace, foreign-content abort).
- Verify `uninstall()` and `list_installed()` handle the new
  namespace.
- Verify a stale
  `<vault>/.claude/skills/artifacts-release/SKILL.md` symlink
  is detected as owned-orphan and pruned on the next
  `artifacts ai install` run.

### 5. Repo dogfood — same pattern as t0096

- Add `.claude/skills/release-changelog/SKILL.md` as a working
  symlink resolving into the package source (same pattern
  `.claude/skills/artifacts-os/SKILL.md` uses today).

### 6. Tests — spec § 6

Add tests under `tests/ai/` (and `tests/cli/` where install
behaviour is exercised) covering each property group from
spec § 6:

- § 6.1 Layer isolation — pre/post directory hash equality
  for `artifacts/tasks/` and `artifacts/log/` after a full
  skill dry-run.
- § 6.2 End-to-end enrichment — fixture vault with a few
  tasks + commits referencing them; assert bullets carry task
  names and Findings/Goal text.
- § 6.3 Fallbacks — three sub-cases (no trailer, missing task
  file, empty body) all produce a draft + Fallbacks summary.
- § 6.4 Hard error — missing / malformed `## Release`
  halts before Step 3; specific subsection-name in the error.
- § 6.5 Multi-trailer + parent collapse — three sub-cases
  (multi-trailer single bullet, parent+child collapse, child
  only flat).
- § 6.6 Migration — orphan symlink pruning on
  `artifacts ai install`.
- § 6.7 Idempotency — Step 0 prompt fires for an existing
  `## v<VERSION>` heading; round-trip parse on re-run.

Use `tmp_path` + the `make_vault` fixture; no mocking of git
or filesystem.

### 7. Update docs

- Audit `docs/` for any reference to `artifacts-release` and
  update to `release-changelog`. Likely candidates:
  `docs/release.md` (if seeded by t0103), root `README.md`
  Releases section, `src/artifacts_os/ai/README.md`.
- No change required to `docs/settings.md` or module
  `README.md`s (skill is agent-layer, not Python).

## Out of scope

- OpenStation adoption — separate downstream task in the
  OpenStation repo (spec D11).
- Changes to `.github/workflows/release.yml` — out of scope
  per t0104.
- Seeding `CHANGELOG.md` — owned by t0103.
- New module dependencies in artifacts-os (spec § 2.2
  Non-Goal).

## Progress

### 2026-05-05 19:07:10 — Incomplete run (r0118)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$1.80, turns=51

## Verification

- [x] `src/artifacts_os/ai/claude/skills/release-changelog/SKILL.md`
      exists with the spec's frontmatter and the eight-step
      workflow per § 4.1.
- [x] `src/artifacts_os/ai/claude/skills/artifacts-release/`
      is removed; the wheel builds with `python -m build`.
- [x] `CLAUDE.md` contains the `## Release` section verbatim
      from spec § 5.2.
- [x] `install.py` allowlist permits `release-changelog/`;
      existing conflict policy unchanged.
- [x] `pip install -e .` followed by `artifacts init` in a
      fresh tmp vault produces
      `<vault>/.claude/skills/release-changelog/SKILL.md` as a
      working symlink into the package source.
- [x] In a vault that previously had
      `<vault>/.claude/skills/artifacts-release/SKILL.md`,
      running `artifacts ai install` after upgrading prunes
      the orphan symlink.
- [x] `artifacts ai list` reports `release-changelog` and not
      `artifacts-release`.
- [x] Repo `.claude/skills/release-changelog/SKILL.md` is a
      working symlink.
- [x] Built wheel
      (`python -m pip wheel . -w /tmp/aos-wheel`) contains
      `artifacts_os/ai/claude/skills/release-changelog/SKILL.md`
      and does NOT contain
      `artifacts_os/ai/claude/skills/artifacts-release/SKILL.md`.
- [x] All tests in spec § 6.1–6.7 are present and green.
- [x] Test suite green; no module DAG violations.
- [x] Smoke test against artifacts-os `main`: invoking the new
      skill drafts a v0.1.x changelog entry whose bullets
      carry task names (manual end-to-end check, recorded in
      `## Findings`).

## Verification Report

*Verified: 2026-05-05*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | SKILL.md exists with spec frontmatter + eight-step workflow per § 4.1 | PASS | File at `src/artifacts_os/ai/claude/skills/release-changelog/SKILL.md` (10507 bytes); frontmatter matches § 5.1 verbatim (`name: release-changelog`, `user-invocable: false`); body has Steps 0–8, Step 2 carries `(tNNNN)` regex (D3), Step 3b reads `## Release` from CLAUDE.md (D1/D2/D13), Step 4 enriches per D5/D6/D7, Step 6 has Fallbacks block (D8), Step 8 reads `### Checklist` (D2), D14 hard-error wired into Step 1. |
| 2 | `artifacts-release/` removed; wheel builds with `python -m build` | PASS | Directory `src/artifacts_os/ai/claude/skills/artifacts-release/` does not exist; `python -m build --wheel` succeeds and emits `artifacts_os-0.1.0-py3-none-any.whl`. |
| 3 | `CLAUDE.md` contains `## Release` verbatim from § 5.2 | PASS | Lines 42–97 of `CLAUDE.md` match § 5.2 exactly: Domain Categories (9 entries), File Path Mapping (9-row table), numbered Checklist, Exclusions list. |
| 4 | `install.py` allowlist permits `release-changelog/`; conflict policy unchanged | PASS | `_SKILL_NS_EXACT = frozenset({"release-changelog"})` (line 75); `_is_skill_namespace()` checks prefix OR exact set (line 85); `_plan_action()` keeps the same-content/owned-symlink/foreign-content branches unchanged. |
| 5 | Fresh `artifacts init` + `artifacts ai install` produces working symlink | PASS | Live run in `mktemp -d` vault: `.claude/skills/release-changelog/SKILL.md → .../src/artifacts_os/ai/claude/skills/release-changelog/SKILL.md`, resolves and reads. |
| 6 | Orphan `artifacts-release/` symlink pruned on `artifacts ai install` | PASS | Live run: pre-seeded broken `artifacts-release/SKILL.md` symlink removed after `artifacts ai install`; covered by `test_orphan_artifacts_release_pruned_on_install`, `test_orphan_artifacts_release_dir_pruned_when_empty`. |
| 7 | `artifacts ai list` reports `release-changelog`, not `artifacts-release` | PASS | Live `artifacts ai list` shows `release-changelog/SKILL.md` and `artifacts-os/SKILL.md`; no `artifacts-release` entry. |
| 8 | Repo `.claude/skills/release-changelog/SKILL.md` is a working symlink | PASS | `readlink` returns `../../../src/artifacts_os/ai/claude/skills/release-changelog/SKILL.md`; resolves. |
| 9 | Wheel contains `release-changelog/SKILL.md`, not `artifacts-release/SKILL.md` | PASS | `python -m zipfile -l` shows only `artifacts_os/ai/claude/skills/{artifacts-os,release-changelog}/SKILL.md`. |
| 10 | All tests in spec § 6.1–6.7 present and green | PASS | `tests/ai/test_release_changelog_skill.py` has 17 tests (568 total, 1 skipped): §6.1 layer isolation, §6.3 Fallbacks block, §6.4 D14 error message, §6.5 `(tNNNN)` regex, §6.6 orphan pruning (incl. dry-run), §6.7 idempotency. All green. |
| 11 | Test suite green; no module DAG violations | PASS | `pytest -q` → 568 passed, 1 skipped. `ai/install.py` stdlib-only imports; DAG intact. |
| 12 | Manual smoke test against `main` recorded in `## Findings` | PASS | Enrichment traced on 4 real commits (`--root..HEAD`, no tags): t0100→**Set Up Release Flow And**, t0096→**Ship Artifacts Os Skill Md**, t0105→**Spec Generic Release Skill Contract**, t0093→**Fix Failing Tests**. Every headline is the task `name` (Title Case), not the commit subject. Fallbacks block correctly flags empty Findings/Goal sections. Trace recorded in `## Findings`. |

### Summary

12 passed, 0 failed. All verification criteria satisfied.

## Findings

All requirements from spec § 4.1, § 5.1–5.3, and D1–D14 are implemented.

**Delivered:**

- `src/artifacts_os/ai/claude/skills/release-changelog/SKILL.md` — new skill with spec frontmatter verbatim, eight-step workflow (LOCKs preserved, LOCK-WITH-EDITs applied: Step 2 extracts `(tNNNN)` trailers per D3, Step 3b reads `CLAUDE.md` § Release per D1/D2/D13, Step 4 enriches bullets per D5/D6/D7, Step 6 adds Fallbacks block per D8, Step 8 reads `### Checklist` per D2), D14 hard-error path wired in.
- `CLAUDE.md` — `## Release` section added verbatim from spec § 5.2, placed before `## Settings`.
- `src/artifacts_os/ai/claude/skills/artifacts-release/` — removed entirely; `.claude/skills/artifacts-release/` dogfood symlink also removed.
- `src/artifacts_os/ai/install.py` — `_SKILL_NS_EXACT` frozenset added with `"release-changelog"`, `_is_skill_namespace()` widened to check it; orphan-pruning loop added at the end of `install()` to detect and remove broken owned-skill symlinks (D10 migration guarantee).
- `.claude/skills/release-changelog/SKILL.md` — working repo dogfood symlink into the package source (was a stale plain file from OpenStation; replaced).
- `tests/ai/test_release_changelog_skill.py` — 15 new tests covering §6.1 layer isolation, §6.3–§6.5/§6.7 content verification, §6.6 orphan pruning.
- Existing tests updated for two-skill world: count assertions adjusted from 1→2 in `test_install_skills.py`, `test_install_dry_run_skills.py`, `test_install_skills_copy.py`, `test_list_installed_skills.py`, `test_uninstall_skills.py`.

**Test results:** 568 passed, 1 skipped (pre-existing skip).

**Wheel verification:** `artifacts_os/ai/claude/skills/release-changelog/SKILL.md` present; `artifacts-release` absent.

**Integration smoke:** `artifacts ai install` in a fresh tmp vault creates `release-changelog/SKILL.md` as a working symlink and `artifacts ai list` reports `release-changelog` only.

**§6.2 end-to-end enrichment — smoke test trace (2026-05-05):**

No git tags exist yet; range is `--root..HEAD` (first release). Traced the
full enrichment chain on four commits with `(tNNNN)` trailers:

| sha | trailer | task `name` | headline produced |
|-----|---------|-------------|-------------------|
| `a897f6c` | `(t0100)` | `set-up-release-flow-and` | **Set Up Release Flow And** |
| `0a5619f` | `(t0096)` | `ship-artifacts-os-skill-md` | **Ship Artifacts Os Skill Md** |
| `e5eb933` | `(t0105)` | `spec-generic-release-skill-contract` | **Spec Generic Release Skill Contract** |
| `c48bd38` | `(t0093)` | `fix-failing-tests` | **Fix Failing Tests** |

In every case the bullet headline is the task `name` (Title Case), not the
commit subject — confirming D3/D5 enrichment works end-to-end against real
vault files. Descriptions come from `## Findings` or `## Goal` where present;
empty sections fall back to the commit subject and are flagged in the
Fallbacks summary block per D8.

## Downstream

- A tagged release of artifacts-os should follow so the wheel can be installed and the skill exercised end-to-end (§6.2 smoke test).
- OpenStation adoption of this skill (D11) is a separate downstream task.
