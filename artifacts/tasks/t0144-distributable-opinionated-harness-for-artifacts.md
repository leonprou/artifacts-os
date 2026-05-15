---
kind: task
id: t0144
name: distributable-opinionated-harness-for-artifacts
type: feature
status: in-progress
assignee: 
owner: user
created: 2026-05-14
subtasks:
  - "[[t0145-spec-the-distributable-harness-model]]"
  - "[[t0146-research-harness-footprints-and-current]]"
---

# Distributable Opinionated Harness For Artifacts-Os

## User story

> **As a consumer of artifacts-os — a new project adopting it, or this
> repo itself — I want to declaratively pull a curated subset of
> opinionated defaults (agents, kinds, skills, settings, hooks, harness
> wiring) from a single source, and keep them in sync with the library
> version, so that I can adopt artifacts-os's conventions without
> copy-pasting files and silently drifting over time.**

Today artifacts-os mixes four concerns under one repo root:

1. The Python library (`src/artifacts_os/`)
2. Shipped defaults bundled with the library (`src/.../templates/`)
3. The dogfood vault (`artifacts/`, `artifacts.yaml`)
4. Hand-maintained AI-harness configs (`.claude/`, `.openstation/`,
   `.opencode/`)

Concerns 3 and 4 have no distribution model: the only way to reuse the
opinionated harness in another project is to copy files out of this
repo. Worse, even *inside* this repo there are multiple parallel copies
of the same content — `.claude/agents/` is byte-identical to
`.openstation/agents/`; `artifacts/agents/` and
`src/.../templates/agents/` differ by exactly one file. Edits to one
silently fail to propagate to the others.

This feature treats the opinionated harness as a **distributable
product surface** alongside the library: there is one canonical source
per item, consumers pick subsets they want, and a sync command keeps
on-disk state aligned with the chosen manifest.

## Intent (not contract)

Precise design — manifest schema, sync command surface, override
resolution rules, managed-file markers, merge semantics — is owned by
the architect spec sub-task. User-level intent only:

1. **Single source of truth per shipped item.** Every agent, kind,
   skill, hook recipe, settings preset, and harness manifest exists in
   exactly one place inside the library distribution. Today's
   `.claude/` ≡ `.openstation/` mirroring stops being a manual job.
2. **Consumer chooses subsets by name.** A consumer manifest declares
   which kinds, which agents, which harnesses, and which hook recipes
   the project wants. No item is mandatory.
3. **Managed vs. user-owned files are explicit.** Sync only touches
   files it owns (marked with a header stamp). User customizations
   live in a dedicated override layer; sync never clobbers them.
4. **Drift is detectable.** CI can prove that the on-disk state
   matches the canonical source — `sync --check` exits non-zero on any
   unmanaged edit to a managed file.
5. **This repo dogfoods the new model.** Its own `.claude/`,
   `.openstation/`, `artifacts/agents/`, and `artifacts/kinds/` become
   sync output, not hand-maintained source. The duplication
   disappears by construction.
6. **Upgrade is a one-command operation.** `pip install -U
   artifacts-os && artifacts sync` brings every consumer up to the new
   library version's harness.

## Milestones

Ordered by importance. Each milestone is outcome-level — concrete
design lives in the spec sub-task.

### M1 — Sync foundation
A consumer can declare a manifest, run one command, and have selected
defaults materialized into the project, idempotently and safely.
Managed files are stamped; an override layer is honoured; a `--check`
mode catches drift in CI. Nothing else in this feature ships before M1.

### M2 — Agents, skills, and harness wiring distributed
Agents and skills become subsets pickable from a catalogue. Sync
renders them into the harness paths the consumer enabled
(`.claude/`, `.openstation/`, etc.). This repo's own three+ parallel
copies are eliminated. Highest-visibility duplication is gone.

### M3 — Artifact kinds as distributable bundles
Consumers pick which kinds they want; each kind ships as a bundle of
schema, status lifecycle, `ARTIFACT.md`, and a body template. This
repo's hand-maintained `artifacts/kinds/` becomes sync output.

### M4 — Settings, views, and aliases as presets
View definitions, default-view mappings, and CLI aliases stop being
copy-pasted boilerplate in every consumer's `artifacts.yaml`. They
ship as tier presets and merge with consumer overrides at sync time.
The 160-line `artifacts.yaml` in this repo collapses to ~10 lines.

### M5 — AI context and onboarding portable
The `CLAUDE.md` / `AGENTS.md` contract that teaches an AI how to work
in an artifacts-os vault is portable across consumer projects, with
fence-delimited zones separating managed conventions from project-
specific text. New consumers receive a `USAGE.md` explaining what
landed and how to maintain it. Release tooling generalizes (path
mapping moves from `CLAUDE.md` into `artifacts.yaml`).

### M6 — Automation and tooling (opt-in)
Hooks, pre-commit config, and GitHub Actions workflows ship as
opt-in recipes the consumer enables by name. A consumer can adopt the
full artifacts-os automation suite without writing any of it by hand.

### M7 — Blocked / research first
The following items cannot start until research closes specific
unknowns. The research sub-task covers them; design begins only
after answers land.

- **Harness footprint** — what each of `.claude/`, `.openstation/`,
  `.opencode/` actually consumes. Until known, per-harness manifests
  are guesses.
- **Schema extension model** — how consumers extend a kind's
  frontmatter schema or status lifecycle without forking the kind.
- **Slash-command portability** — whether the harnesses' command
  formats are translatable from one source, or genuinely incompatible.
- **Example vault and per-kind authoring guides** — defer until M2/M3
  stabilize; shipping examples that churn would confuse consumers.
- **`KindDef.meta` defaults** — current architecture explicitly
  leaves this caller-owned; needs an explicit decision before the
  library starts populating it.

## Sub-tasks

- **architect spec sub-task** — design the distribution model:
  manifest schema, sync command semantics, override resolution,
  managed-file marker, merge rules per file type, migration plan for
  this repo's existing hand-maintained trees, deprecation strategy
  for `artifacts init`'s current copy-once behaviour.
- **researcher sub-task** — close M7 unknowns: enumerate each
  harness's required file layout; produce a per-file classification
  (managed / project-specific / runtime data) of everything currently
  under `.claude/`, `.openstation/`, `.opencode/`, and `artifacts/`;
  identify any project-specific content in this repo that must move
  to the override layer to survive migration.

## Verification

High-level acceptance signals — detailed criteria live in the
architect spec once produced.

- [ ] Architect spec produced, reviewed, and approved.
- [ ] Research sub-task complete; M7 unknowns closed.
- [ ] A consumer (test repo or openstation) can declare a manifest
      and materialize the chosen subset with one command.
- [ ] Sync refuses to overwrite files that lack the managed marker;
      override layer takes precedence over bundled defaults.
- [ ] `artifacts sync --check` catches drift in a CI workflow.
- [ ] This repo's `.claude/`, `.openstation/`, `artifacts/agents/`,
      and `artifacts/kinds/` are regenerated from canonical sources;
      drift CI is green.
- [ ] No content loss in migration — anything project-specific
      (e.g. this repo's `qa.md` agent) is preserved in the override
      layer.
- [ ] `pip install -U artifacts-os && artifacts sync` upgrades a
      consumer's harness to the new library version end-to-end.

## Out of scope

- A separate distribution package (`artifacts-os-defaults`). Deferred
  until the harness needs a release cadence independent of the
  library.
- Live updates without re-running sync (e.g. file watcher). One-shot
  sync is the contract.
- Cross-vault event federation, remote/webhook event delivery — these
  belong to the events/hooks feature line, not distribution.
- Brand, license, IDE-config, language-toolchain templates — these
  are out of artifacts-os's domain.
- Replacing `artifacts init` entirely; `init` remains the bootstrap
  for fresh consumer repos, while `sync` is the ongoing operation.

## References

- The current settings tier mechanism (`src/artifacts_os/templates/`)
  is the seed of the distribution catalogue; the spec extends it
  rather than replacing it.
- The existing events/hooks system ([[s0025-artifact-events]],
  [[t0136-artifact-event-and-hook-system]]) is a precedent for the
  "managed core + opt-in reactions" split this feature mirrors.
- This repo's `CLAUDE.md :: Release` block is the working example of
  project-specific content that today is mixed with managed
  conventions and needs the fence-delimited-zone treatment in M5.
