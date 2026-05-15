---
created: 2026-05-15
id: n0014
kind: note
name: books-integration-roadmap
---

A prioritized roadmap of which book contents the artifacts-os
artbook distro should ship, in what order, and why.
Design reference: [[s0029-artbook-mvp-distribution-model]] (v2
schema, post-D24/D25). Source analysis: this repo's current
content layout (`artifacts/agents/`,
`src/artifacts_os/ai/claude/{skills,commands}/`,
`.openstation/{skills,commands}/`, `artifacts/kinds/`).

The roadmap applies the Pareto principle — ship the books that
deliver ~80% of the consumer value with ~20% of the effort first,
then iterate.

---

## Ranking summary

| # | Book | Universal? | MVP-fits today? | Effort | Tier |
|---|------|------------|-----------------|--------|------|
| 1 | **agents** | ~100% — every Claude Code consumer | yes, flat dir of `.md` | already shipping | **1** |
| 2 | **commands** | ~90% — `/artifacts.*` slash commands | yes, flat dir of `.md` | +1 book entry | **1** |
| 3 | **skills** | ~85% — Claude learns the system from these | folder-of-folders (each skill is `<name>/SKILL.md`) | +N entries or walker tweak | **2** |
| 4 | **kinds** | ~30% — most projects start with defaults | folder-of-folders, `kind.json` (not `.md`) | needs allowlist + recursion | **3** |
| 5 | **hooks** | ~20% — per-project policy, executable | flat | sensitive (RCE surface) — defer | **3** |
| — | templates/agents | duplicate of agents | yes | redundant — skip | — |

The 80/20 line falls between Tier 1 and Tier 2. **Agents +
commands** delivers most of the value with zero MVP changes.

---

## Phase 1 — agents + commands (Tier 1, ready now)

**Goal**: a consumer who sets `artbook.distro_url` and runs
`artifacts book pull agents` + `artifacts book pull commands`
ends up with the artifacts-os agents *and* slash commands
installed under `.claude/`, ready to use in Claude Code.

### Phase 1 `artbook.yaml` addition

```yaml
books:
  - name: agents
    src: artifacts/agents/
    dest: .claude/agents/

  - name: commands
    src: src/artifacts_os/ai/claude/commands/
    dest: .claude/commands/
```

### Open question for Phase 1 — canonical commands location

`src/artifacts_os/ai/claude/commands/` currently contains only 3
files (`artifacts.create.md`, `artifacts.list.md`,
`artifacts.show.md`). The full canonical set used by this repo
(24 files, including `openstation.*`) lives at
`.openstation/commands/`, with many symlinked to `src/`.

Two options:

- **A — strict-package**: ship `src/.../commands/` as-is (3
  files). Honest about what the *package* ships today.
- **B — backfill canonical**: copy/sync the `artifacts.*`
  commands from `.openstation/commands/` into
  `src/.../commands/` first (a separate `author` cleanup task),
  then ship that fatter set.

**Recommendation**: ship **A now**, file **B as a follow-up**
author task. Keeps Phase 1 a pure data change and doesn't
conflate "publish what we have" with "fix where the canonical
source lives". After B lands, the commands book gets fatter for
free — no additional artbook work.

### Phase 1 dependencies

- v2 schema implementation (drop `type:`, accept `src:`/`dest:`):
  blocks the commands entry because `commands` is not a v1 type.
  Track via a separate developer task.
- Without the v2 implementation, Phase 1 can still ship as
  `type: commands` + `_PLACEMENT` extension — a one-line code
  change. But it bakes in the v1 model the v2 spec already
  supersedes; not recommended.

---

## Phase 2 — skills (Tier 2)

Each skill is `<name>/SKILL.md`. The MVP walker is non-recursive
(D20), so a single `src: .../skills/` would pick up nothing.
Two ways forward; pick one before Phase 2 lands.

### Option 2a — one book per skill (works today, no code change)

```yaml
- name: skill-artifacts-os
  src: src/artifacts_os/ai/claude/skills/artifacts-os/
  dest: .claude/skills/artifacts-os/

- name: skill-release-changelog
  src: src/artifacts_os/ai/claude/skills/release-changelog/
  dest: .claude/skills/release-changelog/
```

- **Pros**: works in current MVP; per-skill granularity (a
  consumer can pull just one).
- **Cons**: manifest churn — adding a skill requires editing
  `artbook.yaml`; the manifest gets long.

### Option 2b — one-level walker for skill folders (small extension)

Add an optional `recurse: 1` (or `nested: true`) flag to the
schema. The walker descends one level and ships each subfolder
as a unit.

```yaml
- name: skills
  src: src/artifacts_os/ai/claude/skills/
  dest: .claude/skills/
  recurse: 1
```

- **Pros**: clean manifest; new skills land in consumers without
  any artbook edit.
- **Cons**: requires a small spec amendment (s0029 §3.3, D20) and
  a few lines of code. Loses per-skill pull granularity unless
  we keep both modes.

**Decision (2026-05-15)**: shipped Option 2a — one book entry per
skill. The manifest now contains `skill-artifacts-os` and
`skill-release-changelog`. Revisit 2b if/when a third skill is
added and manifest churn becomes a real cost.

### Phase 2 skills inventory (today, in `src/artifacts_os/ai/claude/skills/`)

- `artifacts-os/SKILL.md` — teaches Claude to use the artifacts
  CLI (kinds, fetch, search, update).
- `release-changelog/SKILL.md` — drafts release entries from git
  log.

(`.openstation/skills/` adds `openstation-execute` and
`openstation-supervisor` — those belong to the openstation
distro, not the artifacts-os artbook.)

---

## Phase 3 — kinds, hooks (Tier 3, deferred)

### Kinds

✅ **Shipped 2026-05-15.** Added as `kinds` book in `artbook.yaml`
with `recurse: true` and `dest: artifacts/kinds/` (vault root,
not `.claude/`).

The earlier blockers turned out to be non-issues once D26 landed:
- Recursion — solved by `recurse: true` (D26).
- File-type override — not needed; the D26 recurse walker is not
  `*.md`-only, so `kind.json` is picked up automatically.

`book show kinds` confirms 5 units (agent, note, research, spec,
task), 10 files (ARTIFACT.md + kind.json each).

### Hooks

Hooks are executable Python files (or shell). Sensitive: a
distro that ships hooks effectively ships RCE on the consumer's
machine. The MVP has no signature / sandbox / policy story.
Defer until there's a hooks security model.

---

## What we explicitly skip

- **`templates/agents/`** — duplicate of `artifacts/agents/`
  minus `qa.md`. Same content; no value in shipping twice.
- **`templates/kinds/`** — same as `artifacts/kinds/`; covered
  by `artifacts init`, not the artbook.
- **`.openstation/agents/`** and **`.openstation/commands/`** —
  these are openstation's namespace, not artifacts-os's. They
  belong in a (hypothetical) openstation artbook, not this one.

---

## Dependencies, in order

1. ✅ **v2 schema implementation** — drop `type:`, accept
   `src:`/`dest:`, add vault-escape guard. Completed via t0158.
2. ✅ **Phase 1 ship** — `agents` + `commands` books in
   `artbook.yaml`. Completed 2026-05-15.
3. **(Optional) Option B — canonicalize commands** — author
   task to move/copy the artifacts-* commands from
   `.openstation/commands/` into `src/.../commands/`.
4. ✅ **Phase 2 decision** — Option 2a (one book per skill).
5. ✅ **Phase 2 ship** — `skill-artifacts-os` +
   `skill-release-changelog` added to `artbook.yaml`
   (2026-05-15).
6. ✅ **Phase 3 (kinds)** — `kinds` book added 2026-05-15. Hooks
   still deferred (no security model).

---

## Open follow-ups (file when ready)

- `t0NNN-implement-artbook-v2-schema` (developer) — implement
  D24/D25 in `manifest.py`, `placement.py`, `book.py`, tests.
- `t0NNN-canonicalize-claude-commands-source` (author) —
  Option B above; reconcile `src/.../commands/` and
  `.openstation/commands/`.
- `t0NNN-phase-2-skills-book-strategy` (architect) — decide
  between 2a and 2b; spec amend if 2b.