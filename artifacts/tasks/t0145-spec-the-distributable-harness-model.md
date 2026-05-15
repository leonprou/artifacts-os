---
kind: task
id: t0145
name: spec-the-distributable-harness-model
type: spec
status: review
assignee: architect
owner: user
parent: "[[t0144-distributable-opinionated-harness-for-artifacts]]"
created: 2026-05-14
started: 2026-05-14
artifacts:
  - "[[openstation/specs/s0028-distributable-harness-sync-model]]"
---

# Spec The Distributable Harness Model

## Goal

Produce the design spec for the distributable opinionated harness
described in the parent feature task. The spec is the technical
contract every subsequent milestone (M2–M6) builds against.

## Scope of the spec

The spec must define:

1. **Manifest schema** — what a consumer declares in `artifacts.yaml`
   (or a sibling file) to pick subsets of the catalogue: kinds,
   agents, skills, harnesses, hook recipes, settings tier.
2. **Sync command surface** — `artifacts sync` and `artifacts sync
   --check` semantics, exit codes, output format, idempotency
   guarantees, ordering of operations.
3. **Catalogue layout** — how the canonical sources are organized
   inside `src/artifacts_os/templates/` (extending today's layout).
4. **Per-harness manifest format** — how each render target
   (`.claude/`, `.openstation/`, `.opencode/`) declares the subdirs
   and file mappings it consumes from the catalogue.
5. **Managed-file marker convention** — header format, scope rules
   (which file types get markers vs. cannot), and the algorithm sync
   uses to decide overwrite vs. refuse vs. error.
6. **Override layer resolution** — directory location, lookup order,
   per-file-type merge semantics (markdown full-replace, YAML/JSON
   deep-merge), fence-delimited zones for `CLAUDE.md`-style hybrid
   files.
7. **Runtime-data exclusion** — explicit list of paths sync must never
   touch (`state.db*`, `events/*.jsonl`, `logs/`), with the rule that
   makes this enforced, not implicit.
8. **Migration plan for this repo** — concrete steps to convert the
   current hand-maintained `.claude/`, `.openstation/`,
   `artifacts/agents/`, `artifacts/kinds/` into sync output without
   losing project-specific content (e.g. `qa.md`).
9. **Relationship to `artifacts init`** — what `init` does after this
   feature lands; whether it becomes "manifest scaffolder + first
   sync" or retains its current one-shot copy behaviour.

## Inputs

- Parent feature task: user story, intent, milestones, out-of-scope.
- The researcher sub-task's findings on harness footprints and the
  per-file classification of everything currently under `.claude/`,
  `.openstation/`, `.opencode/`. The spec depends on these answers;
  draft work can begin in parallel, but final design cannot ship
  before research closes.
- Today's `src/artifacts_os/templates/` layout, today's settings tier
  presets, today's per-harness directory trees.

## Out of scope for this spec

- Distribution as a separate pip package — deferred per parent task.
- Watching files for changes / live sync — one-shot only.
- Replacing the events/hooks module design — orthogonal.

## Deliverable

A spec artifact under `artifacts/specs/` (numbered, conventional
format). The spec must be concrete enough that a developer can
implement M1 from it without further architectural questions:
manifest YAML examples, command-line surface, file path conventions,
error message catalogue, and a worked end-to-end example showing a
fresh consumer running `artifacts sync` and getting the expected
on-disk result.

## Verification

- [ ] Spec written and committed under `artifacts/specs/`.
- [ ] All nine scope items above are addressed.
- [ ] Worked example covers at least: fresh consumer init, override
      taking precedence, drift detected by `--check`, runtime-data
      survival.
- [ ] Migration plan reviewed against the researcher's per-file
      classification — no content loss path identified.
- [ ] Spec status promoted to `approved` after user review; parent
      feature task promoted from `backlog` to `ready`.

## Progress

### 2026-05-14 — architect

Architect verification pass on the produced spec. Confirmed
[[s0028-distributable-harness-sync-model]] addresses all 9 scope
items from the task body (manifest schema §5, sync surface §6,
catalogue layout §7, per-harness manifest §8, marker convention
§9, override layer §11, runtime-data exclusion §12, init
relationship §13, migration plan §14), the 4 required worked
examples (fresh init §16.1, override precedence §16.2, `--check`
drift §16.3, runtime survival §16.4 — plus a 5th catalogue
upgrade scenario §16.5), the error-message catalogue (§15:
E001–E005 manifest, E101–E104 render, W201–W203 refusal,
D301–D304 drift), and the test plan (§17, 11 groups). All six
research-gated items are tagged R1–R6 (§22) with recommended
defaults so M1 implementation can begin against drafts in
parallel with t0146 closing.

Status held at `review`. Owner (user) verifies; approval also
gates on R1–R6 closure (per t0144's M7 unknowns).

## Findings

Produced spec [[s0028-distributable-harness-sync-model]] (draft,
status held pending research and user review).

**Design summary.** A new top-level `harness:` key in
`artifacts.yaml` declares the consumer's chosen subset of the
shipped catalogue (`kinds`, `agents`, `skills`, `commands`,
`hooks`) and which harness targets to render into
(`.claude/`, `.openstation/`, `.opencode/`, plus the `artifacts`
pseudo-target for the vault itself). `artifacts sync`
materialises the chosen items idempotently into those targets;
`artifacts sync --check` is the read-only drift detector
suitable for CI. Per-harness manifests under
`src/artifacts_os/templates/harnesses/<name>.yaml` declare the
catalogue→destination mapping for each target, so adding a
fourth harness is a pure file-add. Project-specific content
lives in `artifacts/overrides/` and shadows the catalogue via a
documented lookup order; runtime data (`state.db*`,
`events/*.jsonl`, user-authored `tasks/`, …) is excluded by
an explicit `runtime_paths:` deny-list on each harness manifest.

**Key decisions (14 locked, 6 pending research).**
- D1 manifest in `artifacts.yaml :: harness:`, not a separate file.
- D2 one flat verb `artifacts sync` with `--check / --dry-run /
  --target / --force / --json`.
- D5 + D6 single-line managed-file marker
  (`<!-- artifacts-os:managed v1 src=... sha256=... -->`) plus a
  sidecar lock file `.artifacts-os/sync.lock` — markers for
  humans, lock for machines.
- D8 merge by file type — markdown full-replace, YAML/JSON
  deep-merge, hybrid (CLAUDE.md) via named fence-delimited zones.
- D9 deny-list (not allow-list) for runtime data so new runtime
  files appear as drift rather than being silently merged.
- D10 sync refuses to overwrite any file lacking both a marker
  and a lock entry — preserves today's `keep-foreign` invariant
  from `ai/install.py`.
- D11 init becomes "manifest scaffolder + first sync"; standalone
  `artifacts sync` is the upgrade path. Existing init flow UX
  from s0021 is preserved verbatim.
- D12 migration of this repo: catalogue moves first, then harness
  manifests, then engine, then `harness:` block written, then
  project-specific files routed to `artifacts/overrides/`, then
  symlink web torn down, then `artifacts sync` regenerates
  everything. Each step is a separate commit; rollback is
  `git revert`.

**Scope coverage (all 9 task items addressed).**
- §5 Manifest schema · §6 Sync CLI · §7 Catalogue layout · §8
  Per-harness manifests · §9 Marker convention · §10 Lock file ·
  §11 Override layer · §12 Runtime-data exclusion · §13 init
  relationship · §14 Migration plan · §15 Error catalogue · §16
  Worked end-to-end example (fresh consumer / override
  precedence / `--check` drift / runtime survival / catalogue
  upgrade) · §17 Test plan (11 groups) · §19 Module layout for
  `src/artifacts_os/sync/`.

**Research dependency.** Six items (R1–R6 in §22) cannot be
promoted from `recommended` to `decided` until
[[t0146-research-harness-footprints-and-current]] closes:
slash-command portability across harnesses, per-file
classification of today's `.claude/`/`.openstation/`/`.opencode/`
trees, OpenStation `docs/` ownership, this repo's `CLAUDE.md`
zone list, schema-extension precedents, and whether
`.opencode/` stays in v1. Each has a recommended default the
spec ships with, so M1 implementation can begin against the
defaults while research closes in parallel.

## Downstream

- **Spec needs user review and R1–R6 closure** before status can
  move from `draft → approved`. Parent task §92 of t0145's
  verification — and t0144's promotion from `backlog → ready` —
  gates on that approval.
- **M1 implementation task to be created** after approval:
  builds `src/artifacts_os/sync/` (planner, executor, marker,
  lock, overrides, zones modules per §19), adds the
  `artifacts sync` CLI command, moves the
  `src/artifacts_os/ai/claude/{commands,skills}/` files into
  `src/artifacts_os/templates/{commands,skills}/`, and ships
  the four harness manifests.
- **Migration sub-task** for the dogfood vault tracks §14.2's
  eight steps once the engine lands; cannot proceed past step 5
  until R4 (per-file classification) closes.
- **Drift-CI workflow** (§20 item 7) should be added as a GitHub
  Actions job `sync-check` running on every PR alongside the
  existing test workflow. Implementation lands with M1.
- **Docs sweep follow-up**: a new `docs/sync.md` describing the
  manifest schema, override layer, and marker contract is needed
  as part of M1 (CLAUDE.md `## Documentation First`). The spec
  references it from §15.1 E001's hint text.
- **Deprecation plan for `artifacts install`** (existing AI
  install CLI command): keep alongside `artifacts sync` for one
  release cycle, then remove per §18.3.
