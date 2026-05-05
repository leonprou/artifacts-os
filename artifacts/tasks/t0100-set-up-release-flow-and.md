---
assignee: developer
created: 2026-05-05
id: t0100
kind: task
name: set-up-release-flow-and
owner: user
status: in-progress
type: implementation
started: 2026-05-05
---

## Goal

Set up the release flow for artifacts-os so a version bump + a single
commit on `main` triggers tag + GitHub Release + PyPI publish, driven
by an AI skill modelled on openstation's `release-changelog` SKILL but
adapted to a pip package.

## Reference shape

- `~/workspace/os/open-station/.github/workflows/release.yml` — the
  trigger pattern (`paths: [pyproject.toml]` + `chore: release v...`
  commit prefix + `workflow_dispatch` fallback).
- `~/workspace/os/open-station/.openstation/skills/release-changelog/SKILL.md`
  — the skill template: idempotency check, conventional-commit parsing,
  domain-category mapping, version-bump recommendation, present-for-
  review-then-write, finally release.

artifacts-os adds **PyPI Trusted Publishers** publishing on top of the
openstation tag-and-release shape.

## Requirements

### 1. `.github/workflows/release.yml`

Mirror openstation's pattern, extended for PyPI:

- **Triggers:** push to `main` touching `pyproject.toml` AND commit
  message matching `^chore: release v[0-9]`; plus `workflow_dispatch`
  with a `tag` input.
- **Job 1 — test:** re-run the pytest matrix (3.11/3.12/3.13) — guards
  against shipping a red `main`.
- **Job 2 — build:** depends on job 1. Build sdist + wheel with
  `python -m build`, run `twine check dist/*`, install the built wheel
  into a fresh venv and `python -c "import artifacts_os"` as a smoke
  test.
- **Job 3 — github-release:** depends on job 2. Tag `v<version>` and
  create a GitHub Release (`softprops/action-gh-release@v2`,
  `generate_release_notes: true`).
- **Job 4 — pypi-publish:** depends on job 2. Publish via
  `pypa/gh-action-pypi-publish@release/v1` using **Trusted Publishers
  (OIDC)** — no `PYPI_API_TOKEN` secret in the repo. Note the one-time
  PyPI-side Trusted Publisher configuration (project, owner, workflow
  filename, environment) in this task body when complete.
- **Permissions:** `contents: write` (job 3), `id-token: write`
  (job 4, OIDC).
- **TestPyPI dry-run:** wire pre-release versions (`v*-rc*`, `v*a*`,
  `v*b*`) to publish to TestPyPI instead of prod PyPI. Halves the blast
  radius of the first launch.

### 2. `src/artifacts_os/ai/claude/skills/artifacts-release/SKILL.md`

Author a skill modelled on openstation's `release-changelog`, adapted
to artifacts-os:

- Same workflow shape: idempotency check, range determination, commit
  collection, parse + categorize, draft, version recommendation,
  present-for-review, write, release.
- **Domain categories** sourced from artifacts-os module structure:
  `core`, `views`, `cli`, `tui`, `ai`, `log`, `Install`,
  `Architecture`, `Fix`.
- **File path → category mapping** uses `src/artifacts_os/<module>/`
  paths (instead of openstation's `bin/openstation`, `agents/`,
  `commands/`).
- **Step 8 release checklist** updated for the pip-package flow:
  1. Update `version` in `pyproject.toml`.
  2. Write CHANGELOG entry.
  3. Commit as `chore: release v<VERSION>`.
  4. Push to `main`.

### 3. Repo dogfood

This repo's `.claude/skills/` should expose `artifacts-release/` the
same way it exposes other artifacts-os skills (file-level symlink
into `src/artifacts_os/ai/claude/skills/artifacts-release/`). Same
pattern as the t0096 dogfood step.

## Out of scope (handled in sub-task)

- Skill frontmatter polish (`user-invocable: true` + verifying the
  skill rides the wheel via t0096's machinery).
- Seeding `CHANGELOG.md` at the repo root.
- Operator-facing docs (`docs/release.md` or equivalent) covering
  Trusted Publishers setup, how to cut a release, and how to debug
  workflow failures.

These follow as a sub-task once the workflow + skill + dogfood land.

## Verification

- [ ] `.github/workflows/release.yml` exists and is YAML-valid.
- [ ] Workflow correctly distinguishes release commits from non-release
      commits on push; `workflow_dispatch` works with an explicit tag.
- [ ] `src/artifacts_os/ai/claude/skills/artifacts-release/SKILL.md`
      exists with valid frontmatter (`name`, `description`).
- [ ] PyPI-side Trusted Publisher is configured for repo
      `leonprou/artifacts-os`, workflow `release.yml`, environment
      `pypi` (one-time, manual; record completion in this task body).
- [ ] TestPyPI Trusted Publisher configured analogously for pre-release
      versions.
- [ ] Repo `.claude/skills/artifacts-release/SKILL.md` is a working
      symlink into the package source.
- [ ] End-to-end dry run: bump pyproject to a pre-release version
      (e.g. `0.1.0a1`), commit `chore: release v0.1.0a1`, push or use
      `workflow_dispatch`; confirm jobs 1-4 succeed; pre-release lands
      on TestPyPI.
- [ ] Test suite still green; no module DAG violations.

## PyPI Trusted Publisher Setup (one-time, manual)

To be completed by the operator before the first real release. Steps
for both PyPI (prod) and TestPyPI (pre-release):

### PyPI (production — environment `pypi`)

1. Go to <https://pypi.org/manage/account/publishing/> (log in as `leonprou`).
2. Add a new Trusted Publisher with:
   - **PyPI project name:** `artifacts-os`
   - **Owner:** `leonprou`
   - **Repository:** `artifacts-os`
   - **Workflow filename:** `release.yml`
   - **Environment:** `pypi`
3. Create a GitHub Actions environment named `pypi` in the repo settings
   (Settings → Environments → New environment).

### TestPyPI (pre-release — environment `testpypi`)

1. Go to <https://test.pypi.org/manage/account/publishing/>.
2. Same settings as above but **Environment:** `testpypi`.
3. Create a GitHub Actions environment named `testpypi` in the repo settings.

Record completion here: _(pending)_

## Findings

Three artefacts produced:

1. **`.github/workflows/release.yml`** — Four-job pipeline:
   `check` (gate) → `test` (3.11/3.12/3.13 pytest matrix) → `build`
   (sdist + wheel, twine check, smoke test) → `github-release` +
   `pypi-publish` in parallel. Pre-release detection via PEP 440
   suffix regex routes to `testpypi` environment; stable releases
   go to `pypi`. Permissions are set at job level (`contents: write`
   for github-release, `id-token: write` for pypi-publish OIDC).

2. **`src/artifacts_os/ai/claude/skills/artifacts-release/SKILL.md`**
   — Mirrors openstation's `release-changelog` workflow (Steps 0–8)
   with artifacts-os domain categories (`core`, `views`, `cli`,
   `tui`, `ai`, `log`, `Install`, `Architecture`, `Fix`) and the
   pip-package release checklist in Step 8.

3. **`.openstation/skills/artifacts-release/SKILL.md`** — Symlink
   to the package source, following the same pattern as `artifacts-os`
   skill. (`.claude/skills/` is itself a symlink to `.openstation/skills/`.)

Pre-existing test failures in `tests/ai/` (9 tests) are unrelated to
this task — confirmed by running the suite on `main` before changes.

## Downstream

- Operator must complete the one-time PyPI/TestPyPI Trusted Publisher
  setup (see section above) before the first release attempt.
- The sub-task covering CHANGELOG seeding, `user-invocable: true`
  frontmatter polish, and `docs/release.md` is tracked separately
  (out-of-scope for this task).