---
assignee: developer
created: 2026-05-05
id: t0103
kind: task
name: polish-release-flow-user-invocable
owner: user
parent: '[[t0100-set-up-release-flow-and]]'
depends_on:
  - '[[t0100-set-up-release-flow-and]]'
status: backlog
type: implementation
---

## Goal

Polish the release flow scaffold (parent `t0100`) once the workflow,
skill, and dogfood land: add the user-invocable affordance, seed
the CHANGELOG, and ship operator-facing docs.

## Why this is a separate task

These items are independent of the workflow's core mechanics — they
are quality-of-life and onboarding work that benefits from being
tackled after `t0100` proves the underlying release flow runs end-to-
end. Splitting keeps `t0100` focused on the workflow contract and
the SKILL's logic; this task focuses on user-facing surface area.

## Requirements

### 1. Skill: `user-invocable: true`

Add `user-invocable: true` to the frontmatter of
`src/artifacts_os/ai/claude/skills/artifacts-release/SKILL.md` so the
user can invoke `/artifacts-release` directly (matches openstation's
`release-changelog` posture for non-AI-only invocation).

### 2. Confirm skill rides the wheel via t0096's machinery

`t0096` shipped the `ai/claude/skills/` install plumbing. This skill
should already be picked up by the existing walker without code
changes. Verify and document:

- `pip install -e .` in a fresh dir followed by `artifacts init`
  produces `<vault>/.claude/skills/artifacts-release/SKILL.md` as a
  symlink resolving into the package source.
- `artifacts ai list` reports the new skill alongside existing
  installed assets.
- Built wheel (`pip wheel . -w /tmp/aos-wheel`) contains
  `artifacts_os/ai/claude/skills/artifacts-release/SKILL.md`.

If any of these fail, raise it back to the t0100 scope or open a
follow-up against the install module — do not paper over it here.

### 3. Seed `CHANGELOG.md` at repo root

Create a `CHANGELOG.md` at the repo root with:

- Top-level `# Changelog` heading.
- A short blurb stating the format (Keep a Changelog flavour, semver,
  conventional-commits-driven).
- An initial `## v0.1.0` entry summarising what shipped in this
  version (use `git log` to enumerate; categorise by domain per the
  skill's mapping).

This makes the skill's Step 0 idempotency check (`grep "^## v0.1.0"`)
and Step 7 (insert after `# Changelog` heading) work on first
invocation.

### 4. `docs/release.md`

Operator-facing doc covering:

- **Trusted Publishers setup** — one-time PyPI + TestPyPI
  configuration steps (project name, repo owner, workflow filename,
  environment names). Include screenshots or links to the PyPI UI.
- **Cutting a release** — pointer to `/artifacts-release` skill;
  manual fallback (the four-step checklist if the skill isn't
  available).
- **What the workflow does** — brief diagram or flow of the four
  jobs in `release.yml` (test → build → tag-release in parallel with
  pypi-publish).
- **Debugging failures** — common failure modes (test matrix red,
  twine check rejects long_description, OIDC mis-config, name
  collision on PyPI), with remediation pointers.

Link the new doc from the root `README.md` ("Releases" section or
equivalent) and from `src/artifacts_os/ai/README.md`.

## Out of scope

- The release workflow itself (lives in parent `t0100`).
- The skill content (lives in parent `t0100`).
- Any change to `ai/install.py` — if t0100's dogfood works, this task
  consumes that contract unchanged.

## Verification

- [ ] `SKILL.md` frontmatter has `user-invocable: true`.
- [ ] Fresh-vault smoke test: `pip install -e . && artifacts init` →
      `<vault>/.claude/skills/artifacts-release/SKILL.md` symlink works.
- [ ] `artifacts ai list` reports the skill.
- [ ] Built wheel contains the skill file.
- [ ] `CHANGELOG.md` exists at repo root with `# Changelog` heading
      and a populated `## v0.1.0` entry.
- [ ] `docs/release.md` covers Trusted Publishers setup, cut-release
      procedure, workflow flow, and debugging.
- [ ] `README.md` links to `docs/release.md` from a "Releases" or
      equivalent section.
- [ ] `src/artifacts_os/ai/README.md` mentions the artifacts-release
      skill.
- [ ] Test suite still green.