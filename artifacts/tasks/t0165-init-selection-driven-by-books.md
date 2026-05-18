---
assignee: ''
created: 2026-05-15
id: t0165
kind: task
name: init-selection-driven-by-books
owner: user
status: in-progress
subtasks:
- '[[t0166-spec-the-books-driven-init]]'
- '[[t0167-implement-books-driven-init-flow]]'
type: feature
---

# Init Selection Driven By Books, Not Bundled Kinds + Agents

## User story

> **As a** user running `artifacts init --distro <url>`
> **I want** the selection prompts to be organised by **book** —
> one prompt per book, asking which items to install —
> **so that** I don't have to answer the same question twice
> (once for the bundled catalogue, once for the distro book of
> the same name) and end up with two collections that can
> disagree.

## Why

The current flow asks the user three independent questions:

1. **Step 1 — settings tier** (legitimate; tier is a real choice).
2. **Step 2 — kinds**: pick from the bundled `templates/kinds/`
   catalogue (`task`, `note`, `spec`, `research`, `agent`).
3. **Step 3 — agents**: pick from the bundled `templates/agents/`
   catalogue (`architect`, `author`, `developer`, …).
4. **Step 4 — distro books**: pick which books to pull, then for
   each selected book pick items.

In Steps 2–3 the user picks from a hard-coded set bundled in the
Python package. In Step 4 the same items reappear inside the
distro's `kinds` and `agents` books and the user is asked to
choose them all over again. Worst case the two answers
disagree — Step 2 installed `task,note,spec` while Step 4's
`kinds` book is left at the default `*` and silently overwrites
the kind files the bundled templates just wrote.

This is the conceptual mismatch:

- **Bundled templates** are a parallel catalogue baked into the
  library at release time.
- **Distro books** are the live, distributable catalogue
  consumers actually want to install from.

There should be **one** catalogue and **one** selection model:
books. Each book asks which of its items to install.

## Intent — locked decisions

User-confirmed decisions. Precise contract (flag surface,
migration mechanics, error semantics) is finalised in the
architect spec sub-task ([[t0166-spec-the-books-driven-init]]).

1. **Two-stage flow.** Step 1 selects the settings tier
   (`minimal` / `standard`, single choice). Step 2 onwards
   iterates the distro manifest's books — one prompt per book,
   defaulting to "all items" with a comma-separated multi-
   select identical to today's kinds/agents prompt. No
   separate "kinds" question; no separate "agents" question.
2. **No-distro fallback = settings + skill, nothing else.**
   When neither `--distro` nor `$ARTIFACTS_DISTRO_URL` is set,
   init runs Step 1 only and then installs the bundled
   **artifacts-os skill** into `.claude/skills/artifacts-os/`
   as the bare-minimum bootstrap. No kinds, no agents — the
   vault is intentionally empty but functional. The user
   grows it later via `artifacts book pull` or a re-init with
   `--distro`.
3. **Per-book prompt** = single multi-select, defaulting to
   `*` (all items). Same shape as today's kinds/agents step.
4. **Settings tier stays bundled.** Step 1 keeps its current
   source (`src/artifacts_os/templates/settings/`); the tier
   is not a book.
5. **`-y` keeps its meaning.** With `-y` plus a distro,
   init pulls every book / every item with no prompts. With
   `-y` and no distro, init runs the fallback path (settings
   + bundled skill) with no prompts.
6. **`--force` re-prompts everything.** Re-init runs every
   prompt from scratch and overwrites matching files; no
   "skip books already present" optimisation.

## Open contract questions (deferred to spec)

- Disposition of today's `--kinds CSV` / `--agents CSV` flags
  (delete / deprecate / keep as sugar).
- Shape of the non-interactive per-book item filter flag.
- Migration plan for `src/artifacts_os/templates/{kinds,agents}/`
  (these become dead weight once the fallback is settings-only).
- Optional per-book `init:` / `default:` fields in
  `artbook.yaml` for distro authors who want to opt a book out
  of init's loop or change its default item set.

## Out of scope

- Authoring new books in the distro manifest.
- The `book pull` / `book list` / `book show` CLI surfaces —
  those are shipped and unchanged.
- The broader distributable-harness model (M3 of
  [[t0144-distributable-opinionated-harness-for-artifacts]]); this
  task is a UX correction on `init`, not a redesign of how
  artifacts-os distributes content.

## Sub-tasks

- **Architect spec sub-task** —
  [[t0166-spec-the-books-driven-init]] — produces the
  technical contract built on the locked decisions above.

## Verification

Implementation-level checklist — promoted to `ready` only after
the spec ([[t0166]]) is approved and implementation sub-tasks
are scoped.

- [ ] Architect spec produced, reviewed, and approved.
- [ ] **No-distro fallback (D2):** `art init` with no
      `--distro` and no `$ARTIFACTS_DISTRO_URL` writes
      `artifacts.yaml` (per chosen tier) and installs
      `.claude/skills/artifacts-os/`. Nothing else is created
      (no kinds, no agents).
- [ ] **Interactive distro flow (D1/D3):** `art init --distro
      <url>` runs Step 1, then one multi-select prompt per
      book in manifest declaration order. Each prompt defaults
      to all items.
- [ ] **Non-interactive `-y` with distro:** `art init --distro
      <url> -y` pulls every book and every item with no
      prompts.
- [ ] **Non-interactive `-y` without distro:** `art init -y`
      runs the fallback (settings + bundled skill) with no
      prompts.
- [ ] **`--force` re-prompts:** rerunning on an initialised
      vault with `--force` re-asks every prompt and overwrites
      matching files.
- [ ] **Flag disposition:** behaviour of legacy `--kinds` /
      `--agents` flags matches the spec's chosen disposition;
      release notes reflect it.
- [ ] **Bundled-templates cleanup:** disposition of
      `src/artifacts_os/templates/{kinds,agents}/` matches the
      spec's migration plan.
- [ ] **Docs:** `docs/artbook.md` consumer quickstart and
      `src/artifacts_os/cli/README.md` `init` section reflect
      the new flow.

## References

- Spec: [[t0166-spec-the-books-driven-init]] — technical
  contract.
- [[t0163-artifacts-init-artbook-distro-integration]] — original
  Step 4 (distro) integration; this task corrects the
  redundancy it introduced between Steps 2/3 and Step 4.
- [[t0144-distributable-opinionated-harness-for-artifacts]] — M3
  (kinds as distributable bundles) and M2 (agents as pickable
  subsets) anticipated this consolidation.
- `src/artifacts_os/cli/commands/init.py` — current selection
  flow implementation.
- `src/artifacts_os/templates/{kinds,agents}/` — bundled
  catalogue that becomes dead weight under D2; spec proposes
  removal.
- `src/artifacts_os/ai/claude/skills/artifacts-os/` — the
  bundled skill that becomes the no-distro fallback payload
  (D2).
- `artbook.yaml` — the artifacts-os repo's own distro manifest,
  used as the reference for the books-as-selection-unit model.