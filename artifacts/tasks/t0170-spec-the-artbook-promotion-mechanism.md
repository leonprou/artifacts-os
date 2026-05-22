---
artifacts:
- '[[n0015-artbook-promotion-mechanism-design-brainstorm]]'
- '[[s0031-artbook-post-pull-artifact-promotion]]'
assignee: architect
created: 2026-05-17
id: t0170
kind: task
name: spec-the-artbook-promotion-mechanism
owner: user
parent: '[[t0169-add-post-pull-artifact-promotion]]'
status: done
type: spec
started: 2026-05-17
completed: 2026-05-22
---

## Goal

Produce an architect spec defining the **post-pull artifact promotion mechanism** for distro books — the technical contract for the parent feature ([[t0169-add-post-pull-artifact-promotion]]).

The parent task captures **user-level intent** and the **locked direction** from the brainstorming session. This task produces the technical contract resolving the eight open questions.

## Locked decisions (from brainstorming — see [[n0015]])

These are foundational; the spec restates them verbatim and designs around them.

### L1 — Canonical landing under `artifacts/…`

Books pull into `artifacts/…` by default, mirroring `src:`. `dest:` becomes optional. The vault's canonical view of book content is always under `artifacts/`.

### L2 — Distro-author owns promotion config (option α)

A new `promote:` field per book in `artbook.yaml` declares the tool-shaped consumer location. Distros are self-installing — zero consumer config required to consume a promotion-using distro.

### L3 — CLI is tool-agnostic

`promote:` is just a vault-relative path string. The CLI doesn't special-case `.claude/`, `.cursor/`, or any other tool convention. "Supporting Claude" means the artifacts-os repo ships a Claude-flavoured distro; the CLI itself learns nothing about Claude.

### L4 — Tool-flavoured distros are the scaling unit

Multi-tool support (Cursor, Codex, etc.) is delivered by **writing more distros**, not by adding tool-specific CLI features. MVP scope is Claude-flavoured artifacts-os distro only. Transformers / shape conversion (e.g. Codex's `AGENTS.md` aggregation) are explicitly deferred.

### L5 — Promotion runs implicitly after pulls

Every `book pull` and every `init` book step runs promotion as a post-step. The operator does not need an explicit verb for the common case.

## Questions the spec must answer

The eight open questions ([[n0015]] § Open contract questions):

1. **`dest:` migration.** Strict (only allowed to mirror `src:` under `artifacts/`) or lenient (back-compat with v1 manifests that point `dest:` outside `artifacts/`)? Tied: v2 manifest bump, or stay v1 with optional `promote:` field. Spec picks one and documents the deprecation path.

2. **`promote:` shape.** String shorthand (`promote: .claude/agents/`), object form (`promote: { target, mode, recurse }`), or list of either? List enables a single book promoting to multiple targets — useful for future multi-tool distros — but adds parser complexity. Spec picks one and documents.

3. **Mode default and matrix.** Symlink-with-copy-fallback (POSIX-clean, Windows-fragile) vs copy-always (portable, doubles bytes). Per-promotion override? Per-vault override in `artifacts.yaml`?

4. **Consumer opt-out.** Operators who want to skip promotion (because their tool stack differs or they want a 'pure' canonical vault) need a lever:
   - `--no-promote` flag on `book pull` and `init`?
   - `disable_promotion: true` in `artifacts.yaml`?
   - Both? Neither?

5. **Bake promotion rules into `artifacts.yaml`?** Should init persist the distro's promotion rules into the consumer's `artifacts.yaml` (or a sidecar) so that subsequent `artifacts create <kind=agent>` auto-promotes user-authored content? Or is promotion purely book-pull-time, leaving user-authored content canonical-only?

6. **Idempotency and stale-item cleanup.** Promotion runs twice on a re-pull:
   - Symlinks: trivially idempotent (re-pointing is no-op).
   - Copies: hash-check or force-overwrite semantics.
   - Item removed from the source between pulls: clean up the stale promotion target, or leave it?

7. **Verb naming and explicit re-run.** "promote" reads well in author context ("this book is promoted to .claude/agents"); alternatives include "mount", "expose", "link", "surface". Independently: do we ship an explicit `artifacts promote` (or equivalent) verb for re-running the promotion step against an existing canonical state, separately from `book pull`?

8. **D2 fallback in [[t0167]].** The books-driven init flow installs a bundled `artifacts-os` skill in the no-distro case. Under the promotion model, this should plausibly write to `artifacts/skills/artifacts-os/` and promote to `.claude/skills/artifacts-os/`. The spec must confirm — or explicitly mark D2 as special (writes direct to `.claude/` without going through the canonical-then-promote loop).

## Deliverables

- A spec artifact under `artifacts/specs/` (likely `s00NN-artbook-promotion-mechanism.md`) containing:
  - Background and motivation (linking back to [[t0169]] and [[n0015]]).
  - L1–L5 restated verbatim with no contradicting design choices.
  - A numbered decision (with rationale and rejected alternatives) for each of Q1–Q8.
  - **Three worked transcripts:**
    - A consumer running `artifacts book pull agents` against a v2 `artbook.yaml` with `promote:` set — showing both canonical and promotion writes.
    - The same scenario with promotion disabled (per Q4's chosen mechanism).
    - The artifacts-os distro's own `artbook.yaml` rewritten to the new shape (the worked migration example).
  - A migration section listing every file that changes: `artbook.yaml` schema, `src/artifacts_os/artbook/` modules (manifest parser, `pull_book`, walker / placement), `docs/artbook.md`, the artifacts-os repo's own `artbook.yaml`, tests.
  - An implementation sub-task breakdown — project-manager creates those tasks once the spec is approved.
- Recorded in this task's `artifacts:` frontmatter (alongside the brainstorm note already linked).

## Out of scope

- Implementation. Producing the spec is the only deliverable.
- Multi-tool support (Cursor, Codex) — defer per L4.
- Transformers / shape conversion.
- Re-architecting kinds to be tool-aware.
- The broader distributable-harness redesign in [[t0144-distributable-opinionated-harness-for-artifacts]] — this spec covers the promotion mechanism only.

## Verification

- [x] Spec artifact exists under `artifacts/specs/`.
- [x] L1–L5 are restated verbatim with no contradicting design choices.
- [x] Every open question Q1–Q8 has an explicit decision in the spec with rationale.
- [x] Spec includes at least three worked transcripts (pull with promote, pull with promote disabled, artifacts-os distro `artbook.yaml` migration example).
- [x] Migration section names every file that will change.
- [x] Spec proposes an implementation-sub-task breakdown for project-manager to create from.
- [x] Spec linked in this task's `artifacts:` frontmatter.

## Verification Report

*Verified: 2026-05-18*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec artifact exists under `artifacts/specs/` | PASS | `artifacts/specs/s0031-artbook-post-pull-artifact-promotion.md` present (1410 lines). |
| 2 | L1–L5 restated verbatim with no contradicting design choices | PASS | Spec § 2 ("Locked Foundations") restates L1–L5 verbatim from [[n0015]]; §§ 3–6 explicitly stay consistent (e.g., D29 defers list-form per L4; D40 ties D2 fallback through canonical + promote per L1+L5). |
| 3 | Every open question Q1–Q8 has an explicit decision with rationale | PASS | D28 (Q1), D29 (Q2), D30 (Q3), D31 (Q4), D35 (Q5), D32 (Q6), D34 (Q7), D40 (Q8) — each with Decision / Rationale / Rejected alternatives sections. |
| 4 | At least three worked transcripts | PASS | § 4.1 pull-with-promote; § 4.2 promote-disabled (variants B1 setting + B2 flag); § 4.3 artifacts-os distro before/after migration. |
| 5 | Migration section names every file that will change | PASS | § 5 enumerates source code (5.1), distro manifest (5.2), documentation (5.3), tests (5.4), and spec-side revision notes (5.5). § 1.4 also provides the summary table. |
| 6 | Implementation sub-task breakdown for project-manager | PASS | § 6 defines S1–S5 sub-tasks with scope, verification, and blocking relationships sized for single-PR delivery. |
| 7 | Spec linked in this task's `artifacts:` frontmatter | PASS | Frontmatter contains `'[[s0031-artbook-post-pull-artifact-promotion]]'` alongside the brainstorm note `n0015`. |

### Summary

7 passed, 0 failed. All verification criteria met; task is ready to transition to `verified`.

## References

- Parent: [[t0169-add-post-pull-artifact-promotion]]
- Brainstorm: [[n0015-artbook-promotion-mechanism-design-brainstorm]]
- [[t0167-implement-books-driven-init-flow]] — D2 fallback intersection (Q8).
- [[s0029-artbook-mvp-distribution-model]] — current distro model; needs v2 amendment or a successor.
- `src/artifacts_os/artbook/` — current artbook implementation; promotion slots in after `pull_book`.
- `artbook.yaml` (root) — the artifacts-os repo's own distro manifest; needs migration to v2 shape per L1.
- `docs/artbook.md` — author + consumer guide; updates after spec lands.

## Progress

### 2026-05-17 — architect
> time: 23:33

Produced architect spec [[s0031-artbook-post-pull-artifact-promotion]]. Eight open questions resolved as decisions D28–D40, additive on top of s0029 (no v2 manifest bump). Three worked transcripts and a five-sub-task implementation breakdown included. Findings + downstream sections appended to task. Ready for review.

## Findings

Produced [[s0031-artbook-post-pull-artifact-promotion]] — the architect spec for the post-pull artifact promotion mechanism. Eight open questions resolved as decisions D28–D40, tightening v1's semantics on top of [[s0029]] (no version bump — v1 has not been published beyond this repo).

**Key design choices.**

- **Q1 / D28 — Schema stays at `version: 1`; v1 semantics tightened in place.** `dest:` becomes optional with default `artifacts/<basename(src)>/`; explicit `dest:` outside `artifacts/` is rejected (canonical-only); new optional `promote:` field surfaces tool-shaped consumer locations. No back-compat shim — v1 has not been published beyond this repo, so the only existing manifest (artifacts-os' own `artbook.yaml`) is migrated in the same commit.
- **Q2 / D29 — `promote:` is string-shorthand OR single-object form.** List-of-promotions deferred per L4 (multi-tool support arrives via more distros, not by complicating the schema).
- **Q3 / D30 — Default mode `symlink` with automatic copy fallback** on filesystems that reject `os.symlink` (Windows without dev mode). Per-promotion `mode:` and per-vault `artbook.promote_mode` overrides, precedence per-promotion > per-vault > default.
- **Q4 / D31 — Both opt-out levers.** Persistent `artbook.promotion: disabled` in `artifacts.yaml`; one-shot `--no-promote` on `book pull` and `init`. Flag wins on collision.
- **Q5 / D35 — No auto-promotion of user-authored content at MVP.** Promotion is book-pull-time only. Punted to a follow-up spec.
- **Q6 / D32 — Idempotent re-pull + safe stale-target cleanup via a sidecar state file** at `artifacts/.artbook/state.json`. Tracks per-book promoted paths; symlink ownership verified via `os.readlink`, copy ownership verified via SHA-256 hash. Never deletes user-modified or unrelated files in shared target directories.
- **Q7 / D34 — Field name and verb are `promote`.** Ships an explicit re-run verb `artifacts book promote [BOOK] [--clean] [--dry-run] [--json]` for re-emitting promotions against the current canonical content without re-cloning.
- **Q8 / D40 — D2 fallback flows through canonical + promote.** The bundled `artifacts-os` skill is written via a synthetic in-memory `Book` so the promotion pipeline can be reused unchanged. One and only one path for content that ends up in `.claude/`.

**Three worked transcripts in § 4** — pull-with-promote (canonical + symlink, with state-file output), pull-with-promote-disabled (both setting and flag variants), and the artifacts-os distro `artbook.yaml` before/after migration.

**Implementation breakdown in § 6** — five sub-tasks sized for single-PR delivery: S1 manifest schema, S2 placement + state, S3 CLI surface, S4 docs, S5 distro migration + init D2. S1→S2→S5 is the critical path; S3 and S4 are independently shippable.

The spec is recorded in this task's `artifacts:` frontmatter alongside the brainstorm note.

## Downstream

- **Implementation sub-tasks** — `project-manager` should create the five sub-tasks (S1–S5) from § 6 of the spec once it is approved. Suggested ordering: S1 → S2 (required), then S3 + S4 + S5 in parallel.
- **Revision notes on s0029 and s0030** — § 5.5 of the spec calls out short revision notes pointing at s0031. Owned by the corresponding implementation sub-tasks (S1 for s0029, S5 for s0030), not separate tasks.
- **Follow-up spec — auto-promotion of user-authored content (D35).** Out of scope here. Trigger condition: user demand for `artifacts create --kind agent` to flow through to `.claude/agents/` without a manual re-promote.
- **`docs/artbook.md` "Destination patterns" deprecation.** Current doc presents `dest: .claude/agents/` as the standard pattern. Once s0031 lands and the artifacts-os distro is migrated, that section will mislead new distro authors. The S4 doc sub-task owns the rewrite.
- **Concurrent-pull safety on the state file.** Spec § 8 notes the state file is not locked; concurrent `book pull` against the same vault races. Acceptable for MVP but flag for a future hardening pass.