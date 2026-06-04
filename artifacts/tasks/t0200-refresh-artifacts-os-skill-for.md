---
assignee: author
created: 2026-06-04
id: t0200
kind: task
name: refresh-artifacts-os-skill-for
owner: user
status: ready
type: documentation
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

- [ ] Skill has a "Read a property — `artifacts get`" section covering single-property, no-property, and `-j` forms, with at least two examples.
- [ ] Skill has a "Write a property — `artifacts set`" section covering transition + schema validation and the illegal-transition error shape, with at least two examples.
- [ ] Skill has an "Inspect transitions — `artifacts transitions`" section covering single + all-properties forms and pointing at s0033.
- [ ] Skill has a "Manage hooks — `artifacts hooks`" section covering `list`, `show`, `promote`, `demote` and linking to `docs/hooks.md`.
- [ ] Skill has a "Global flags" section listing `--version` and `--config` and linking to `docs/settings.md`.
- [ ] The "only CLI command that updates an existing artifact" claim is gone from the `status` section.
- [ ] The "Updating non-status fields" paragraph is replaced with a one-liner pointing at `set`.
- [ ] Rule 5 wording no longer implies `status` is the sole mutation verb.
- [ ] Frontmatter `description:` mentions `artifacts.yaml` at the project root (not `artifacts/artifacts.yaml`).
- [ ] `git diff src/artifacts_os/cli/ src/artifacts_os/core/` is empty.
- [ ] `pytest -q` passes with no incidental breakage.
- [ ] Reviewed and approved by user.

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