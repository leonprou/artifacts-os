---
artifacts:
  - '[[openstation/specs/s0030-books-driven-init-flow]]'
assignee: architect
created: 2026-05-15
id: t0166
kind: task
name: spec-the-books-driven-init
owner: user
parent: '[[t0165]]'
status: done
type: spec
started: 2026-05-16
completed: 2026-05-18
---

# Spec The Books-Driven Init Flow

## Goal

Produce an architect spec that defines the new `artifacts init`
selection flow where **books** are the only selection unit
beyond Step 1 (settings tier) — replacing today's separate
"kinds" and "agents" bundled prompts.

The parent ([[t0165-init-selection-driven-by-books]]) captures
**user-level intent only**. This task produces the **technical
contract** off the locked decisions below.

## Locked decisions (from brainstorming with the user)

These are not open questions for the spec — they are the
foundation. The spec records them and designs around them.

### D1 — Flow shape

```
Step 1: Settings tier               (single choice: minimal / standard)
Step 2..N: For each book in distro: (only when a distro is configured)
            multi-select prompt for items, default = all
```

Two stages, nothing else. No standalone "kinds" prompt; no
standalone "agents" prompt.

### D2 — No-distro fallback = templates stage only + bundled skill

When neither `--distro` nor `$ARTIFACTS_DISTRO_URL` is set:

- Run Step 1 only (settings tier → write `artifacts.yaml`).
- Install the bare-minimum bootstrap: the **artifacts-os
  skill** (currently
  `src/artifacts_os/ai/claude/skills/artifacts-os/`) into
  `.claude/skills/artifacts-os/`.
- Exit.

No kinds are installed. No agents are installed. The vault is
intentionally **empty but functional** — the user grows it
later by configuring `artbook.distro_url` and running
`artifacts book pull`, or by re-running `artifacts init
--distro <url> --force`.

The bundled artifacts-os skill is the only piece of
opinionated content the package itself ships into the vault.

### D3 — Per-book prompt = single multi-select

Each book in the distro gets the same prompt UX as today's
kinds/agents step (`_prompt_multi_step`), defaults to all
items:

```
Book 'agents' (11 items) — comma-separated numbers, '*' for all, '-' for none:
  1) architect  [default]
  2) author     [default]
  ...
Choice [*]:
```

One round-trip per book. No separate "all / select / none"
gate.

### D4 — Settings tier stays bundled

Step 1 keeps its current source: bundled
`src/artifacts_os/templates/settings/{minimal,standard}.yaml`.
The tier is **not** a book and does not move into the distro
manifest.

### D5 — `--force` re-prompts every book

A re-init on an existing vault with `--force` re-runs every
prompt (including the book loop) from scratch and overwrites
all matching files. No "skip books with items already
present" optimisation — predictable beats clever.

### D6 — `-y` with no distro installs the D2 defaults

`-y` means "accept defaults non-interactively", not "do
nothing". With no `--distro` and no `$ARTIFACTS_DISTRO_URL`,
`art init -y` runs the D2 fallback exactly: writes
`artifacts.yaml` for the default tier (`standard`) and
installs the bundled `artifacts-os` skill into
`.claude/skills/artifacts-os/`. No prompts, no kinds, no
agents — the same payload the interactive no-distro path
produces, just without the tier question. Don't overthink
it; the common case wins.

## Questions the spec must still answer

The locked decisions above settle the user-facing flow. These
remain genuine design choices for the architect:

1. **Flag-surface disposition.** What happens to today's
   `--kinds CSV` and `--agents CSV` flags? Options:
   - Delete (clean break, release note).
   - Deprecate over one minor release (warn-and-still-work,
     map to book-item filters where unambiguous).
   - Keep as syntactic sugar for the equivalent book-item
     filter (no removal).

   Tied question — what is the **non-interactive item-filter
   flag** for scripted runs? Candidates:
   - `--books NAME,NAME` (today; wholesale book selection only).
   - `--book-items NAME=ITEM,ITEM` (repeatable per book).
   - `--books NAME:ITEM,ITEM NAME:ITEM,ITEM` (single flag,
     namespaced — risk of shell-quoting bugs).

2. **Migration of `src/artifacts_os/templates/{kinds,agents}/`.**
   Once D2 is in place these directories are dead weight.
   Spec must propose:
   - Outright deletion in the same release.
   - Move to a deprecation folder and remove in the next minor.
   - Keep as a "self-distro" source so `art book pull` from
     the bundled package works without network. (Probably
     overkill given D2.)
   - Loader-code cleanup: `_load_kind_schema`,
     `_load_kind_artifact`, `_load_agent_template`,
     `_discover_kinds`, `_discover_agents` all disappear or
     change.

3. **Bundled skill location.** The artifacts-os skill lives at
   `src/artifacts_os/ai/claude/skills/artifacts-os/` today
   (per `artbook.yaml`). The spec must confirm: the
   no-distro fallback copies from **the package install
   location** (importlib resources), not from the source
   tree. The skill must be packaged into the wheel.

4. **Distro skill collision.** When a distro is configured and
   its `skills` book ships an `artifacts-os` skill, that
   pull overwrites the bundled-skill copy init wrote in
   Step 1. Confirm last-write-wins is correct, or skip the
   bundled-skill install when `--distro` is given. (My lean:
   only install the bundled skill in the **no-distro
   fallback**; when a distro is present, defer entirely to
   the book loop.)

5. **Book ordering in the loop.** Books are looped in
   manifest declaration order. Confirm and document — the
   spec needs to say whether distro authors can opt a book
   out of init's loop (e.g. a `init: false` field) or
   change the default item set per book (e.g. `default: []`
   or `default: [item1, item2]`).

6. **Error semantics.** What happens if a book's `dest`
   resolves outside the vault, or its `src` is empty, or its
   manifest entry is malformed? Init must fail fast vs. skip
   the book — spec picks one.

7. **Backward compatibility & release notes.** Define the
   deprecation / breakage matrix for:
   - Existing CI scripts running `art init --kinds … --agents …`.
   - Existing docs and example transcripts (including
     `docs/artbook.md` and `cli/README.md`).
   - Distro authors who may have assumed init ships kinds.

## Deliverables

- A spec artifact under `artifacts/specs/` (likely
  `s00NN-books-driven-init-flow.md`) containing:
  - Background and motivation (linking back to t0165).
  - The six locked decisions restated verbatim (D1–D6).
  - Numbered decisions for every still-open question (1–7).
  - **Two worked transcripts** — one for the no-distro
    fallback flow (D2), one for the distro-configured
    flow (D1/D3).
  - **One worked transcript** for the non-interactive
    (`-y` and fully-flagged) flow.
  - A migration section listing every file that changes in
    `src/artifacts_os/cli/commands/init.py`,
    `src/artifacts_os/templates/`, packaging metadata
    (`pyproject.toml` if needed for the skill resource),
    `docs/`, and the test suite.
  - An implementation sub-task breakdown — at minimum: the
    init code change, the bundled-templates cleanup, the
    docs update, and test coverage. The project-manager
    will create those tasks once the spec is approved.
- Recorded in this task's `## Findings` and listed in
  `artifacts:` frontmatter.

## Out of scope

- Implementation. Producing the spec is the only deliverable.
- Re-engineering `book pull` / `book list` / `book show` —
  these stay untouched.
- The bigger distributable-harness redesign in
  [[t0144-distributable-opinionated-harness-for-artifacts]].
  This spec covers the `init` UX correction only.

## Verification

- [x] Spec artifact exists under `artifacts/specs/`.
- [x] D1–D5 are restated verbatim with no contradicting
      design choices.
- [x] Every still-open question (1–8) has an explicit decision
      in the spec.
- [x] Spec includes both a no-distro transcript (D2) and a
      distro-configured transcript (D1/D3).
- [x] Spec includes a non-interactive (`-y`) flow transcript.
- [x] Migration section names every file that will change,
      including the disposition of
      `src/artifacts_os/templates/{kinds,agents}/`.
- [x] Spec proposes an implementation-sub-task breakdown.
- [x] Spec linked in this task's `artifacts:` frontmatter.

## Verification Report

*Verified: 2026-05-16*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec artifact exists under `artifacts/specs/`. | PASS | `openstation/specs/s0030-books-driven-init-flow.md` (40k, frontmatter `kind: spec`, `id: s0030`, `task: [[t0166-spec-the-books-driven-init]]`). |
| 2 | D1–D5 restated verbatim with no contradicting choices. | PASS | Spec §4 restates D1–D6 verbatim (lines 120–197). Goal §2 and Non-Goals §3 do not contradict any locked decision; no "skip books with items present" optimisation reintroduced. |
| 3 | Every still-open question (1–8) has an explicit decision. | PASS | Task body lists Q1–Q7 (the "1–8" in the checklist is a typo). Spec §5 has decisions for all seven: Q1.a/Q1.b (delete flags, add `--book`), Q2 (delete dirs), Q3 (importlib.resources + wheel), Q4 (skip bundled skill under distro), Q5.a/Q5.b (declaration order, no new fields), Q6 (two-tier table), Q7 (breaking, release notes). |
| 4 | Both no-distro (D2) and distro-configured (D1/D3) transcripts. | PASS | §7.1 Transcript A (no-distro interactive, D2) and §7.2 Transcript B (distro-configured interactive with four-book manifest, D1 + D3). |
| 5 | Non-interactive (`-y`) flow transcript. | PASS | §7.3 Transcript C with two variants: bare `-y` (D6) and fully-flagged `--book` + `-y`. |
| 6 | Migration section names every changing file incl. `templates/{kinds,agents}/` disposition. | PASS | §6 lists 14 src paths (rewrite/delete), 1 packaging file, 2 test files, 4 doc files. `templates/kinds/{agent,note,research,spec,task}` and 9 `templates/agents/*.md` are individually enumerated as `Delete` (lines 490–502). |
| 7 | Implementation sub-task breakdown proposed. | PASS | §10 lists six sub-tasks I1–I6 with touched paths, dependencies, and complexity estimates. |
| 8 | Spec linked in task's `artifacts:` frontmatter. | PASS | Frontmatter line 3: `- '[[openstation/specs/s0030-books-driven-init-flow]]'`. |

### Summary

8 passed, 0 failed. Spec satisfies every verification criterion; task is ready to be marked `verified`.

## References

- Parent: [[t0165-init-selection-driven-by-books]]
- [[t0163-artifacts-init-artbook-distro-integration]] —
  introduced today's Step 4 (distro) integration.
- `src/artifacts_os/cli/commands/init.py` — current
  selection flow.
- `src/artifacts_os/ai/claude/skills/artifacts-os/` — the
  bundled skill that becomes the no-distro fallback payload
  (D2).
- `artbook.yaml` — the artifacts-os repo's own distro
  manifest; the reference for what books look like.
- `docs/artbook.md` — author + consumer guide; will need
  updates after this spec lands.

## Progress

### 2026-05-16 — Architect spec drafted

Wrote `openstation/specs/s0030-books-driven-init-flow.md` —
D1–D6 restated verbatim, Q1–Q7 each given an explicit
decision with rationale, three worked transcripts (no-distro
fallback, distro-configured interactive, non-interactive
`-y` + fully-flagged `--book`), migration inventory naming
every changed source / packaging / test / doc file, and a
six-task implementation breakdown (I1–I6 with dependency
ordering). Transitioning task to review.

## Findings

Produced **[[openstation/specs/s0030-books-driven-init-flow]]** — the
architect spec for the books-driven `artifacts init` flow.

### Locked decisions (D1–D6)

Restated verbatim from this task in §4 of the spec; no
contradicting design choices introduced.

### Resolutions for the seven open questions

| Q  | Resolution                                                                                                                                                         |
|----|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Q1 | **Delete `--kinds` / `--agents`** in the same release (clean break, no shim). **Replace `--books CSV` with repeatable `--book NAME[:item,item]`** for item-level scripted filtering. |
| Q2 | **Delete `src/artifacts_os/templates/{kinds,agents}/` outright.** Drop the matching loader code and `pyproject.toml` wheel globs. Settings templates are kept (D4). |
| Q3 | Read the bundled skill via `importlib.resources.files("artifacts_os.ai.claude.skills") / "artifacts-os"`. Add `SKILL.md` to the wheel artifacts list; exclude `__init__.py`/`__pycache__` from the install walk so the consumer's directory matches what `book pull skills artifacts-os` would produce. |
| Q4 | **Skip the bundled-skill install when any distro is configured.** Bundled skill ships only on the D2 fallback path; the distro is authoritative when one is given. |
| Q5 | Books loop in `artbook.yaml` declaration order. **No new manifest fields** (`init:`, `default:`) in this spec — reserved for a future revision of s0029 if a real distro needs them. |
| Q6 | Two-tier error handling: manifest-invalid / clone-failure / unknown-book-or-item → exit 2 pre-pull; per-book runtime failure logs, continues the loop, exits 1 at end. Carries over today's `_run_distro_step` semantics. Env-supplied distro URL failure falls back to D2 with a warning; CLI-supplied `--distro` failure is fatal. |
| Q7 | Breaking change in the next minor. Release notes call out: `--kinds`/`--agents` removed, `--books CSV` removed (replaced by `--book`), no-distro init no longer ships kinds/agents (only the artifacts-os skill). Migration: configure `artbook.distro_url` and re-init, or `art book pull` post-init. |

### Transcripts

Three transcripts in §7 of the spec — A (no-distro interactive,
D2), B (distro-configured interactive, D1/D3 with manifest of
four books), and C (non-interactive: bare `-y` and
fully-flagged `--book` variants).

### Migration inventory

§6 lists every file changed: 14 source-tree paths (rewrites +
deletes), 1 packaging file, 2 test-suite files, 4 documentation
files. Settings templates and the bundled skill source files
are explicitly marked unchanged.

### Implementation sub-task breakdown

§10 proposes six sub-tasks (I1–I6):

- **I1** — rewrite `init` command for books-driven flow
  (medium).
- **I2** — delete bundled `kinds/` and `agents/` templates
  (trivial).
- **I3** — repackage bundled skill in wheel manifest
  (trivial).
- **I4** — update consumer docs (`docs/init-flow.md`,
  `docs/artbook.md`, `cli/README.md`) (medium).
- **I5** — rewrite init test suite (large).
- **I6** — release notes / changelog entry (trivial).

I3 has no dependencies; I1 depends on I3; I2/I4/I5/I6 depend
on I1.

### Key design judgement calls (worth flagging for review)

1. **Pre-fetch the manifest before Step 1.** I picked
   Option 1 in §8.2 — clone before the tier prompt — so the
   operator sees clone failures *before* answering any
   question. Trade-off: typo'd `--distro` fails earlier (good
   UX) at the cost of one unavoidable round-trip even if the
   user cancels Step 1.
2. **Env-default distro failure falls back to D2 with a
   warning.** This is a sub-decision under Q6 (§8.2) — only
   `$ARTIFACTS_DISTRO_URL` failures degrade gracefully;
   explicit `--distro` failures are fatal. Asymmetric on
   purpose: env is "default convenience", CLI is "I asked
   for it specifically".
3. **Reserved (but not introduced) per-book manifest fields
   `init:` and `default:`** under Q5.b. The spec deliberately
   doesn't add them now, but names them as the future-extension
   contract so a follow-up doesn't accidentally pick conflicting
   names.

## Downstream

- **s0021-artifacts-init-flow** is partially superseded — once
  s0030 lands, mark s0021 as superseded (and link from s0030).
  Done in this spec's §1.2 cross-references, but the s0021
  frontmatter should also reflect this.
- **docs/init-flow.md** will need a near-complete rewrite (the
  current copy describes the three-step bundled flow). The
  doc-update sub-task (I4) does this; no additional work
  surfaced.
- A **post-implementation follow-up** task may emerge for
  `init: false` / `default:` per-book manifest fields if any
  distro author requests opt-out (Q5.b). Out of scope here; no
  task created.
