---
assignee: author
created: 2026-06-04
id: t0200
kind: task
name: refresh-artifacts-os-skill-for
owner: user
status: verified
type: documentation
started: 2026-06-05
---

# Refresh artifacts-os skill for v0.5.0 CLI surface

## Why

v0.5.0 shipped four new top-level verbs (`get`, `set`, `transitions`,
`hooks`) plus the global `--config` flag, but the bundled
`artifacts-os` skill — the contract every agent uses to drive the CLI
— still reflects the pre-v0.5.0 surface. Two of its statements are
now actively wrong:

- "`status` is the **only CLI command that updates an existing
  artifact**" — false since `artifacts set` landed in t0189.
- "the CLI does not currently expose a generic field-update command"
  — false for the same reason.

Agents that follow the skill verbatim will refuse to use `set` when
asked to change a non-status field, and will fall back to either
re-creation or direct file edits — exactly the failure mode the skill
exists to prevent.

The fix is doc-only: bring the skill (and its symlinked copies) in line
with the v0.5.0 CLI README, remove the contradicted paragraphs, and add
worked examples for the new verbs. No CLI change.

## Context

The diff between the v0.5.0 CLI README
(`src/artifacts_os/cli/README.md`) and the bundled skill was
enumerated in chat on 2026-06-04. This task scopes the **v0.5.0
deltas only** — the new verbs, the new global flag, and the
contradicted framing. Pre-v0.5.0 gaps (`init`, `book`, `kinds`,
`views`, `events`, list ref-set / schema-derived flags / multi-value
CSV, layouts/prune, aliases, `cli.defaults`) are out of scope and
should be filed as a separate completeness-sweep task — see
Downstream.

The shipped skill copy lives under
`src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`. Per t0176,
the other two paths
(`.openstation/skills/artifacts-os/SKILL.md` and
`.claude/skills/artifacts-os/SKILL.md` in initialised vaults) are
symlinks to that file, so a single edit satisfies all consumers.

## Source of truth

- **`src/artifacts_os/cli/README.md`** — the v0.5.0 CLI reference. The
  skill must agree with this document on what each verb does and which
  flags it accepts. See in particular:
  - `### get` (Property and Transition Verbs)
  - `### set`
  - `### transitions`
  - `### hooks`
  - `## Global Flags` (the `--config` entry)
- **`CHANGELOG.md` v0.5.0 + Unreleased** — lists the headline features
  (per-property state-machine substrate, `get`/`set`/`transitions`
  verbs, `hooks` kind, `--config` flag) and the task IDs that landed
  them (t0187, t0189, t0182, t0192, t0199).
- **`docs/settings.md`** — the `--config` override is documented in
  the "CLI override" section; the skill's global-flags table should
  link there.
- **s0033 — per-property state machines** — locks the transition
  semantics that `set` and `transitions` expose. The skill should
  point at this spec when explaining `transitions` rather than
  duplicating the rules.
- **t0176** (the previous skill refresh) — establishes the voice,
  symlink topology, and verification pattern this task should follow.

## Files to touch

| Path | Surface | Edit |
|---|---|---|
| `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` | Canonical shipped skill (the other two paths symlink here) | Add `get` / `set` / `transitions` / `hooks` sections; add global-flags section with `--config`; remove the two contradicted paragraphs; reframe Rule 5. |

If the symlink topology has changed since t0176, mirror the edits to
every real copy so the canonical and shipped skills stay in sync.

## Constraints

- **Skill voice.** Match the existing artifacts-os skill voice:
  directive ("Run X", "Pass Y"), example-led (fenced code blocks),
  with an explicit Rules section. Do not adopt the human-reference
  density of `docs/` or duplicate the CLI README verbatim — the skill
  is a tight contract, not a reference manual.
- **Cite, don't duplicate, for state-machine details.** The
  `transitions` section should link to s0033 for the full
  state-machine model rather than re-stating the transition rules.
- **No CLI change.** This is a doc-only task. Do not edit anything
  under `src/artifacts_os/cli/` or `src/artifacts_os/core/`.
- **`--body-file` example unchanged.** The existing create-flow
  guidance from t0176 (ARTIFACT.md selection, `{{TITLE}}`
  substitution, variant precedence) stays as written. This task adds
  alongside that flow; it does not rewrite it.

## Out of scope

- Pre-v0.5.0 gaps (`init`, `book`, `kinds`, `views`, `events`, list
  ref-set / schema-derived flags / multi-value CSV, layouts/prune,
  aliases, `cli.defaults`). File these as a separate completeness
  sweep task — captured in Downstream.
- Any change to the CLI itself.
- Re-organising the skill's overall structure (e.g. moving the Create
  section, renaming the Rules section). Keep the existing layout;
  insert new sections where they fit alphabetically / by command
  family.
- Updating `docs/` to cross-reference the skill — separate downstream
  task.

## Requirements

1. **`get` verb documented.** Skill includes a "Read a property —
   `artifacts get`" section covering the single-property form, the
   no-property form (lists all frontmatter as key/value), and the
   `-j` JSON shape. At least one example reads `status`; at least
   one reads an arbitrary frontmatter field.

2. **`set` verb documented.** Skill includes a "Write a property —
   `artifacts set`" section that explicitly supersedes the old "no
   generic field-update command" framing. Covers: transition
   validation for state-machined properties, schema validation for
   free-form properties, illegal-transition error shape. At least
   one example sets `status`; at least one sets a free-form field
   (e.g. `assignee`).

3. **`transitions` verb documented.** Skill includes an "Inspect
   transitions — `artifacts transitions`" section covering the
   single-property and all-properties forms, the JSON shape
   (`current`, `allowed_next`, `wildcard_targets`, `locked`), and
   the non-state-machined-property error. Points at s0033 for the
   full state-machine semantics.

4. **`hooks` verb documented.** Skill includes a "Manage hooks —
   `artifacts hooks`" section covering `list`, `show`, `promote`,
   `demote`. Explains the `.active/` promotion model briefly and
   links to `docs/hooks.md` for the full model. At least one
   example each for `list` and `promote`.

5. **Global flags section added.** Skill gains a "Global flags"
   section listing `--version` / `-v` and `--config <ref>`. The
   `--config` entry explains that `<ref>` can be a path or a
   basename, and that it has no effect on `artifacts init`. Links
   to `docs/settings.md § "CLI override"`.

6. **Contradicted paragraphs removed.** The two stale claims are
   gone:
   - The "only CLI command that updates an existing artifact"
     framing in the `artifacts status` section (was line 262 of
     the v0.5.0 skill).
   - The "Updating non-status fields" paragraph (was lines
     277–282). Replaced with a one-liner pointing at `set`.

7. **Rule 5 reframed.** The Rules section's body-immutability rule
   stays, but the wording no longer implies `status` is the only
   mutation verb. Should read along the lines of "Body is
   immutable through the CLI — `set` and `status` update
   frontmatter only; if the body needs to change, surface that to
   the user".

8. **Vault marker description corrected.** The skill description
   (frontmatter `description:` field) currently mentions
   `artifacts/artifacts.yaml`; v0.3 moved the marker to the
   project root. Update to `artifacts.yaml` at the project root.

9. **No CLI change.** `src/artifacts_os/cli/` and
   `src/artifacts_os/core/` are not modified. `pytest` still passes.

10. **Shipped copy stays in sync.** If symlinks no longer cover all
    skill paths, the canonical and shipped skill copies are edited
    in step so consumers pulling via the artbook harness get the
    new content.

## Verification

- [x] Skill has a "Read a property — `artifacts get`" section covering single-property, no-property, and `-j` forms, with at least two examples.
- [x] Skill has a "Write a property — `artifacts set`" section covering transition + schema validation and the illegal-transition error shape, with at least two examples.
- [x] Skill has an "Inspect transitions — `artifacts transitions`" section covering single + all-properties forms and pointing at s0033.
- [x] Skill has a "Manage hooks — `artifacts hooks`" section covering `list`, `show`, `promote`, `demote` and linking to `docs/hooks.md`.
- [x] Skill has a "Global flags" section listing `--version` and `--config` and linking to `docs/settings.md`.
- [x] The "only CLI command that updates an existing artifact" claim is gone from the `status` section.
- [x] The "Updating non-status fields" paragraph is replaced with a one-liner pointing at `set`.
- [x] Rule 5 wording no longer implies `status` is the sole mutation verb.
- [x] Frontmatter `description:` mentions `artifacts.yaml` at the project root (not `artifacts/artifacts.yaml`).
- [x] `git diff src/artifacts_os/cli/ src/artifacts_os/core/` is empty.
- [x] `pytest -q` passes with no incidental breakage.
- [x] Reviewed and approved by user.

## Verification Report

*Verified: 2026-06-15*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts get` section with single-, no-property, `-j` forms + ≥2 examples | PASS | SKILL.md lines 300-335; examples read `status` (L319) and `assignee` (L327); covers `<property>`, no-property, and `-j` variants |
| 2 | `artifacts set` section covering transition + schema validation + illegal-transition error + ≥2 examples | PASS | SKILL.md lines 337-374; explicit illegal-transition error shape (L353-356); examples set `status` (L363), `assignee` (L366), and an illegal transition (L369) |
| 3 | `artifacts transitions` section with single + all-property forms, points at s0033 | PASS | SKILL.md lines 376-408; both forms documented; `s0033` cited at L408 |
| 4 | `artifacts hooks` section with `list`, `show`, `promote`, `demote` + links to `docs/hooks.md` | PASS | SKILL.md lines 436-467; all four subverbs documented; `docs/hooks.md` linked at L442 |
| 5 | Global flags section listing `--version` and `--config` + links to `docs/settings.md` | PASS | SKILL.md lines 30-45; flag table at L37-38; `docs/settings.md § "CLI override"` linked at L45 |
| 6 | "only CLI command that updates an existing artifact" claim removed from `status` section | PASS | grep confirms phrase is absent from SKILL.md; status section (L273-298) describes `status` as "the focused, ergonomic verb for advancing an artifact's lifecycle state" |
| 7 | "Updating non-status fields" paragraph replaced with one-liner pointing at `set` | PASS | SKILL.md L295-298: short "Other frontmatter fields" paragraph pointing at `artifacts set <ref> <property> <value>` |
| 8 | Rule 5 no longer implies `status` is the sole mutation verb | PASS | SKILL.md L512-515: "`set` and `status` update frontmatter only" — both verbs named explicitly |
| 9 | Frontmatter `description:` uses `artifacts.yaml` (no `artifacts/` prefix) | PASS | SKILL.md L3: "...contains an `artifacts.yaml` vault marker." |
| 10 | `git diff src/artifacts_os/cli/ src/artifacts_os/core/` is empty | PASS | `git status --short` and `git diff` against those paths produced no output |
| 11 | `pytest -q` passes with no incidental breakage | PASS | `python -m pytest -q` → 1367 passed, 1 skipped in 23.79s |
| 12 | Reviewed and approved by user | PASS | User invoked `/openstation.verify` on this task, exercising the user-owned review path |

### Summary

12 passed, 0 failed. All verification criteria are satisfied; the task is ready to transition to `verified`.

## Progress

### 2026-06-05 — author
> time: 09:20

Refreshed the `artifacts-os` skill to the v0.5.0 CLI surface. Added a
**Global flags** section (`--version` / `--config`) before `## Commands`;
added **get** / **set** / **transitions** sections after `status`; added a
**hooks** section after `verify`. Removed the two contradicted paragraphs
(the "only CLI command that updates an existing artifact" claim and the
"Updating non-status fields" paragraph) and reframed Rules 1 and 5 so no
rule implies `status` is the sole mutation verb. Req 8 (vault marker) was
already satisfied in the canonical file. Edited the canonical SKILL.md
only; symlinks cover the other two paths. `src/cli/` and `src/core/`
untouched (empty diff). `python -m pytest`: 1355 passed, 1 skipped, and 1
pre-existing unrelated failure (`test_show_editor_default_opens_editor`,
the t0192 non-TTY `$EDITOR` guard) — proven independent of this doc change
by re-running with the skill edit stashed. Transitioning to review.

## Findings

Doc-only refresh of the canonical `artifacts-os` skill
(`src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`) to the
v0.5.0 CLI surface. Single file edited; symlink topology from t0176 is
intact (`.openstation/skills/...` and `.claude/skills/...` both symlink
to the canonical file — verified with `ls -la`), so one edit satisfies
all consumers. No `src/cli/` or `src/core/` change.

**Sections added** (inserted by command family, structure preserved):

- **Global flags** — new top-level section before `## Commands`, with a
  `--version` / `--config` table. The `--config` entry explains
  path-vs-basename resolution and the "no effect on `artifacts init`"
  caveat, plus a worked example and a pointer to
  `docs/settings.md` § "CLI override". (Req 5)
- **Read a property — `artifacts get`** — single-property, no-property,
  and `-j` forms; examples read `status` and the free-form `assignee`.
  (Req 1)
- **Write a property — `artifacts set`** — explicitly framed as *the*
  generic field-update command; covers transition validation (s0033),
  schema validation, and the illegal-transition error shape; examples
  set `status` and `assignee`. (Req 2)
- **Inspect transitions — `artifacts transitions`** — single/all-property
  forms, the `current` / `allowed_next` / `wildcard_targets` / `locked`
  JSON shape, the non-state-machined-property error, and a pointer to
  `s0033` instead of restating the rules. (Req 3)
- **Manage hooks — `artifacts hooks`** — `list` / `show` / `promote` /
  `demote`, a brief `.active/` promotion explanation, a link to
  `docs/hooks.md`, and examples for `list` and `promote`. (Req 4)

**Stale framing removed/reframed:**

- The "only CLI command that updates an existing artifact" claim is gone
  from the `status` section, replaced with a pointer to `set`. (Req 6)
- The "Updating non-status fields" paragraph is replaced by a one-liner
  directing the user to `artifacts set`. (Req 6)
- Rule 5 now reads "`set` and `status` update frontmatter only"; Rule 1
  also updated to mention `get`/`set` so no rule implies `status` is the
  sole mutation verb. (Req 7)

**Req 8 (vault marker) was already satisfied** in the canonical file —
its `description:` already reads `artifacts.yaml` (no `artifacts/`
prefix). The stale `artifacts/artifacts.yaml` text only survives in an
out-of-repo cached skill registration; the repo canonical and both
symlinks are correct. Confirmed no repo `SKILL.md` contains
`artifacts/artifacts.yaml`.

**Citation style.** Specs and docs are cited as bare backticked
references (`s0033`, `docs/hooks.md`, `docs/settings.md`) to match the
skill's existing convention (e.g. `s0022-tree-layout`, `s0018`) and to
stay robust under symlink/pip-install relocation, rather than brittle
relative markdown links.

**Verification status:**

- `git diff src/artifacts_os/cli/ src/artifacts_os/core/` is empty. ✓
- `python -m pytest -q` → **1355 passed, 1 skipped, 1 failed**. The lone
  failure (`tests/cli/test_settings.py::test_show_editor_default_opens_editor`)
  is **pre-existing and unrelated** to this doc-only change: it fails
  identically with the skill edit stashed (proven via
  `git stash push -- <skill>` + re-run). It is environmental — the
  t0192 non-TTY `$EDITOR` guard suppresses the editor in agent/CI
  contexts — and is the subject of active in-flight work (untracked
  `t0201-ship-show-editor-default-in` + modified settings templates).
  A markdown skill file is never imported by any test, so it cannot
  affect a `subprocess.run` assertion.
- Note: bare `pytest` aborts at collection on
  `tests/cli/test_config_flag.py` (`from tests.cli.conftest import …`
  needs the repo root on `sys.path`); `python -m pytest` (CWD on path)
  collects all tests cleanly. Also pre-existing, from t0198.

## Downstream

- File a follow-on **completeness-sweep** task covering pre-v0.5.0 gaps
  in the skill: `init`, `book`, `kinds`, `views`, `events`,
  `list` ref-set positional args, schema-derived filter flags,
  multi-value CSV filters, layouts/prune, CLI aliases, and
  `cli.defaults` / `cli.aliases` in `artifacts.yaml`.
- File a docs cross-reference task to add a pointer from
  `docs/settings.md` § "CLI override" back to the skill's new
  global-flags section, so human readers and agents land in the same
  place.