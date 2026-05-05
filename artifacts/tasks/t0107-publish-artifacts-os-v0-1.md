---
kind: task
id: t0107
name: publish-artifacts-os-v0-1
type: feature
status: backlog
assignee: 
owner: user
created: 2026-05-05
---

# Publish artifacts-os v0.1.0 to PyPI

## User story

> **As a Python developer, I want `pip install artifacts-os` to fetch
> the v0.1.0 release from PyPI so I can use the library without cloning
> the repo.**

The v0.1.0 GitHub Release is already live; PyPI publish is the only
missing surface for public consumption.

## Context

The first run of the release pipeline (workflow run
[`25392268348`](https://github.com/leonprou/artifacts-os/actions/runs/25392268348))
succeeded for tests, build, and GitHub Release but failed at
`Publish to PyPI` with `invalid-publisher` — the PyPI Trusted Publisher
was not configured at the time of the release. The built wheel and
sdist are still attached to the run as the `dist` artifact and can be
re-used by rerunning the failed job.

## Requirements

1. **Operator** — register a PyPI Trusted Publisher for the project
   using PyPI's "pending publisher" flow (the project name does not
   yet exist on PyPI).
2. **Operator** — optionally register a TestPyPI Trusted Publisher for
   future pre-release dry-runs (environment `testpypi`).
3. **Re-run** the failed `Publish to PyPI` job from run
   `25392268348` (no rebuild, no re-tag).
4. **Verify** `pip install artifacts-os` resolves `0.1.0` from PyPI in
   a clean virtualenv.
5. **Update** `artifacts/tasks/t0100-set-up-release-flow-and.md` —
   replace `_(pending)_` in the "PyPI Trusted Publisher Setup" section
   with today's date and mark verification items 4, 5, 7 as PASS.

## Verification

- [ ] PyPI Trusted Publisher exists for `leonprou/artifacts-os`,
      workflow `release.yml`, environment `pypi`.
- [ ] Workflow run `25392268348` shows a successful `Publish to PyPI`
      step after rerun (or a fresh release run if PyPI requires it).
- [ ] `pip install artifacts-os==0.1.0` succeeds in a clean venv and
      `python -c "import artifacts_os; print(artifacts_os.__version__)"`
      prints `0.1.0`.
- [ ] t0100 verification report updated to reflect completed
      Trusted Publisher setup.

## Reference

See the "PyPI Trusted Publisher Setup (one-time, manual)" section in
[[t0100-set-up-release-flow-and]] for the exact form fields.
