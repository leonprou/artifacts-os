---
created: 2026-05-14
id: n0012
kind: note
name: distributable-harness-layers-to-merge
task: '[[t0144-distributable-opinionated-harness-for-artifacts]]'
---

# Distributable Harness — Layers To Merge

Inventory of every layer the distribution model has to cover, with
the canonical source candidate and the duplication points that
exist today. Ordered by how visible the duplication is.

Today `.claude/{agents,commands,skills}` and
`.opencode/{agents,commands,skills}` are already symlinks into
`.openstation/`, so the per-harness mirroring described in t0144's
body is partly resolved for this repo. The library-side mirrors
(`src/artifacts_os/templates/`) and the vault-side mirrors
(`artifacts/agents/`, `artifacts/kinds/`) remain.

## 1. Agents
- Sources today: `src/artifacts_os/templates/agents/` (9 files),
  `artifacts/agents/` (10 — adds project-specific `qa.md`),
  `.openstation/agents/` (9, identical to templates).
- Canonical: `src/artifacts_os/templates/agents/`.
- Override: project-specific agents (`qa.md`) live in the consumer's
  override layer, not the canonical source.

## 2. Artifact kinds
- Sources today: `src/artifacts_os/templates/kinds/` and
  `artifacts/kinds/`. Each kind bundle = schema +
  status lifecycle + `ARTIFACT.md` + body template.
- Canonical: `src/artifacts_os/templates/kinds/`.
- Question: how does a consumer extend a kind's frontmatter schema
  or status list without forking the bundle? (M7 unknown.)

## 3. Skills
- Source today: `.openstation/skills/` (`artifacts-os`,
  `openstation-execute`, `openstation-supervisor`,
  `release-changelog`). No template copy.
- Canonical: needs to move under
  `src/artifacts_os/templates/skills/` so consumers pick subsets.

## 4. Slash commands
- Source today: `.openstation/commands/` — `artifacts.*` and
  `openstation.*` families.
- Canonical: `src/artifacts_os/templates/commands/`.
- Question: are the harnesses' command formats translatable from
  one source, or genuinely incompatible? (M7 unknown.)

## 5. Vault settings / views / aliases
- Source today: the 160-line `artifacts.yaml` at the project root
  (kinds list, status maps, view definitions, default-view
  mappings, CLI aliases).
- Canonical: tier presets under
  `src/artifacts_os/templates/settings/`, merged with consumer
  overrides at sync time. Consumer `artifacts.yaml` collapses to
  ~10 lines (M4).

## 6. Harness settings / wiring
- Sources today: `.openstation/openstation.yaml`,
  `.claude/settings.json`, `.claude/settings.local.json`,
  per-harness presets.
- Canonical: per-harness manifests under templates; depends on
  the harness-footprint research (M7).

## 7. Hooks, event reactions, CI
- Sources today: `.openstation/events/` (runtime log — NOT
  distributable), plus any pre-commit and GitHub Actions config.
- Canonical: opt-in recipes under
  `src/artifacts_os/templates/hooks/` keyed by name. Consumer
  enables them in the manifest (M6).

## 8. AI context (CLAUDE.md / AGENTS.md)
- Source today: hand-maintained `CLAUDE.md` and `AGENTS.md` at the
  project root, mixing managed conventions with project-specific
  text (e.g. this repo's `Release` block).
- Canonical: fence-delimited zones — managed conventions injected
  by sync, project-specific text preserved across syncs (M5).

## 9. Release tooling
- Source today: `release-changelog` skill (in
  `.openstation/skills/`) plus the `## Release` section of
  `CLAUDE.md` (domain categories, path-prefix mapping table,
  checklist).
- Canonical: skill ships from
  `src/artifacts_os/templates/skills/`; the
  `path → category` mapping moves out of `CLAUDE.md` and into
  `artifacts.yaml` so the skill is portable (M5).

## 10. Onboarding doc (new)
- Not yet present. M5 introduces `USAGE.md` — a sync-generated
  doc that tells a new consumer what landed and how to keep it
  in sync.
- Canonical: rendered by `artifacts sync`, not committed by the
  library.

## Cross-cutting concerns

- **Managed-file marker.** Every layer above needs a stamp that
  lets `sync --check` distinguish managed files from
  user-customized ones.
- **Override layer.** Each layer above needs a consumer-owned
  directory whose entries shadow the canonical source by name.
- **Per-file classification.** Research sub-task (t0146) produces
  the managed / project-specific / runtime-data label for every
  current file under `.claude/`, `.openstation/`, `.opencode/`,
  and `artifacts/` before sync can be designed safely.