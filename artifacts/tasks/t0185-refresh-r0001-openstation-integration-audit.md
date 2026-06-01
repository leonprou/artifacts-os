---
kind: task
id: t0185
name: refresh-r0001-openstation-integration-audit
type: research
status: review
assignee: architect
owner: user
created: 2026-05-24
started: 2026-05-24
artifacts:
  - "[[r0001-openstation-integration-audit]]"
---

# Refresh R0001 Openstation-Integration Audit Against Current Artifacts-Os

## User story

> **As a maintainer planning the next phase of artifacts-os ↔ openstation
> integration, I want the integration audit to reflect the current state
> of artifacts-os — not the snapshot from 2026-04-29 — so that downstream
> spec and migration decisions are grounded in what actually ships today,
> not in gaps that have since been closed.**

`[[r0001-openstation-integration-audit]]` was authored on 2026-04-29.
Since then a large amount of work has landed (or has a locked spec and
is treated as shipped per this task) that directly affects the audit's
coverage matrix, gap analysis, and recommended integration shape —
including the events log, the hooks subsystem
(`[[s0032-hooks-via-artbook-distribution]]`), vault marker relocation,
books-driven init, artbook distribution, ARTIFACT.md skeletons, tree
layout, and the new `hook` / `artbook` kinds. Several "gaps" called
out in §3 of `r0001` are now closed; several "Recommended" next steps
have been superseded by concrete tasks.

Refreshing it is cheaper than warning every consumer to cross-check.

## Why

- The audit is cited from `t0041`, `t0044`, `t0054`, `t0059`, `t0082`
  and is the load-bearing source for the layered "artifacts-os as
  base, openstation on top" framing. Stale citations mislead.
- New integration-shaped work is starting (hooks-via-artbook,
  books-driven init, harness distribution under `t0144`) and would
  benefit from an updated coverage matrix rather than re-deriving it.
- The simplest action is a refresh of the existing artifact, not a
  net-new audit — the *shape* of `r0001` (TL;DR → side-by-side →
  coverage → gaps → divergences → recommended shape → risks) still
  fits the question.

## Requirements

1. The refreshed audit reflects the **current** state of artifacts-os
   — every "yes / no / partial" cell in the coverage matrix and every
   "gap" sub-section in §3 is re-checked against what ships in `main`
   today. For the hooks subsystem specifically, treat
   `[[s0032-hooks-via-artbook-distribution]]` as implemented (the
   feature is mid-development at audit time; the spec is the
   contract).
2. Items that have closed since 2026-04-29 are marked closed, with a
   pointer to the shipping task / spec. Items still open keep their
   gap framing, but with updated context. At minimum re-evaluate:
   - §3.3 Hooks — now a first-class kind with host dispatch (s0032,
     t0178–t0184); openstation is explicitly a reserved foreign host.
   - §3.4 Events log — `core.events` shipped (t0135, t0139–t0141);
     catalogue gate exists.
   - §3.6 Init / scaffold — books-driven init shipped
     (t0165–t0167); harness distribution model defined under
     `t0144` / `t0150`.
   - §3.9 Naming / ID convention drift — `t0037` shipped; current
     `name = slug` / `id = t0042` convention is locked.
   - §5 Concrete divergences — re-check each of the five blockers
     against current behaviour.
3. The "Recommended integration shape" (§6) and "Risks &
   uncertainties" (§7) are revised to match the current backlog —
   the three "net-new artifacts-os specs implied" by the original
   audit (hooks module, fleshed-out log, marker negotiation) should
   each be marked as their current state.
4. The follow-up `## Recommendations` list is rewritten against the
   current backlog — old recommendations that already shipped are
   replaced with the next concrete decisions (e.g. openstation-side
   adoption of `host: openstation` bundle hooks; migration of
   openstation's events emitter to `artifacts_os.events`).
5. `## Sources` is refreshed: stale paths removed, new doc / kind /
   spec references added (notably `docs/hooks.md`, `docs/events.md`,
   `docs/artbook.md`, `s0029`, `s0031`, `s0032`).
6. The frontmatter `status` stays `done` only if the refresh
   genuinely brings the audit current; otherwise drop back to
   `draft` until findings are firm.

Intent, not contract: the architect doing the refresh owns the
detailed edits and may restructure sub-sections where the new state
of the world makes the old shape awkward. The user-level goal is "a
reader in 2026-05 finds an audit that matches reality."

## Source of truth

- `[[r0001-openstation-integration-audit]]` — the artifact to refresh
- `[[s0032-hooks-via-artbook-distribution]]` — treat as implemented
- Recent shipped tasks affecting the audit's claims (non-exhaustive):
  - Events / hooks: `[[t0135-implement-artifact-events-and-hooks]]`,
    `[[t0139-align-events-cli-with-list]]`,
    `[[t0140-implement-s0027-align-events-cli]]`,
    `[[t0141-docs-events-and-hooks-user]]`,
    `[[t0178-ship-hooks-via-artbook-distribution]]`,
    `[[t0179-spec-hooks-via-artbook-distribution]]`,
    `[[t0181-add-directory-storage-primitive-to]]`,
    `[[t0182-add-hook-kind-and-bundle]]`,
    `[[t0183-add-active-promotion-mechanism-and]]`,
    `[[t0184-add-artbook-kind-hook-book]]`
  - Vault marker / layout: `[[t0134-spec-relocate-vault-marker-to]]`,
    `[[t0137-implement-vault-marker-relocation-per]]`,
    `[[t0138-docs-sweep-for-vault-marker]]`,
    `[[t0113-spec-tree-layout-for-art]]`,
    `[[t0118-document-tree-layout]]`
  - Harness distribution / books: `[[t0144-distributable-opinionated-harness-for-artifacts]]`,
    `[[t0150-artbook-distribution-model]]`,
    `[[t0163-artifacts-init-artbook-distro-integration]]`,
    `[[t0165-init-selection-driven-by-books]]`,
    `[[t0167-implement-books-driven-init-flow]]`,
    `[[t0173-implement-artbook-promotion-engine-and]]`
  - ARTIFACT.md / kinds: `[[t0079-artifact-md-artifacts-ai-extension]]`,
    `[[t0084-wire-artifacts-create-to-artifact]]`,
    `[[t0142-drop-legacy-flat-kind-schema]]`
  - Naming convention: `[[t0037-redefine-name-field-as-slug]]`
    (referenced in r0001 §3.9 as in-flight — now shipped)

## Out of scope

- A net-new research artifact. The deliverable is an updated `r0001`,
  not `r000X`.
- Re-auditing openstation itself. The audit's openstation-side
  claims should be spot-checked but not re-surveyed unless a
  specific finding looks stale.
- Producing a follow-up spec for the integration work itself. That
  is a separate task the refreshed audit will inform.

## Verification

- [ ] `r0001-openstation-integration-audit` body reflects current
      artifacts-os state — every §2 coverage row and §3 gap is
      re-checked against `main` and updated where reality has moved.
- [ ] Hooks subsystem (§3.3 + relevant coverage rows + §6) is
      rewritten on the assumption that
      `[[s0032-hooks-via-artbook-distribution]]` is implemented,
      including the `host: openstation` reserved foreign host.
- [ ] Items that have shipped since 2026-04-29 are marked closed and
      linked to the shipping task or spec.
- [ ] §6 "Recommended integration shape" and §7 "Risks &
      uncertainties" reflect the current backlog (hooks, log,
      marker negotiation, naming).
- [ ] `## Recommendations` lists the next concrete decisions, not the
      ones that have already been acted on.
- [ ] `## Sources` is refreshed: dead paths removed, new docs / specs
      / kinds added.
- [ ] Reviewed and approved by user.

## Progress

### 2026-05-24 — architect
> time: 19:18

Refreshed r0001 end-to-end. Closed §3.3 Hooks (s0025 + s0032), §3.4
Events (shipped as `events/`, not `log/`), §3.6 Init (books-driven),
§3.9 Naming (t0037). Reframed `## Recommendations` as six concrete
decisions: events absorption, `host: openstation` bundles, init
wrapper, naming alignment, dual marker, wikilink resolver. Updated
`## Sources` with new docs + folder-form kinds; removed dead flat-form
paths.

### 2026-05-24 — architect
> time: 20:50

Course correction from user review: §3.3 and Rec #2 over-claimed
that openstation must walk the same `.active/` tree. Rewrote §3.3
to split hooks integration into (1) settled storage + schema and
(2) open activation-model decision, with a three-option table
(share `.active/` ↔ parallel `.openstation/hooks/.active/` ↔ no
separate activation) and the trade-offs for each. Updated §4
coverage matrix row, §7 "Needs further research" (added activation
question as the first item), and Rec #2 (flag the decision as
open, name share-`.active/` as the default recommendation but
not a requirement).

### 2026-05-24 — architect
> time: 21:08

Second course correction: user settled the vault-layout question
with the rule "`artifacts/` for artifacts only; `.openstation/` for
internal state like the db." This collapses the audit's "two
parallel data trees + marker negotiation" framing entirely.
Edits:

- Added §6.1 "Vault layout (collapsed)" with the concrete target
  tree and two tables: what dissolves (the entire `openstation/`
  user tree, `.openstation/agents+skills+commands+docs+events`,
  `openstation.yaml`) and what stays in `.openstation/` (state.db,
  run captures, future doctor cache).
- §5 divergence #3 (vault marker) — flipped 🟡 → ✅; closed by
  collapse. No second marker; openstation is recognised by an
  `openstation:` section in `artifacts.yaml`.
- §5 divergence #4 (storage root) — flipped 🟡 → ✅; closed by
  collapse. The user-facing `openstation/` tree dissolves into
  `artifacts/`.
- §1 "Storage root" row — added "Recommended target shape" pointer
  to §6.1.
- "Three net-new specs" table — vault-marker-negotiation row
  credits collapse, not just relocation.
- §3.6 "Residual openstation-specific work" — `.openstation/`
  scoped to runtime state only; replaced "openstation.yaml write"
  with "inject `openstation:` section into `artifacts.yaml`".
- Rec #5 rewritten from "write both markers at init" to
  "openstation collapses into the artifacts-os vault" with
  concrete migration steps.

## Findings

Refreshed `[[r0001-openstation-integration-audit]]` end-to-end against
the 2026-05-24 state of `main`. Headline shifts:

- **Three of the original audit's "net-new artifacts-os specs" have
  landed.** Hooks shipped under `src/artifacts_os/hooks/` via
  [[s0025-artifact-events]] + [[t0135-implement-artifact-events-and-hooks]],
  then extended for distribution under [[s0032-hooks-via-artbook-distribution]]
  with `kind: hook` directory bundles, operator-owned `.active/`
  symlinks, and `host:`-keyed dispatch. Events shipped as
  `src/artifacts_os/events/` (not in `log/` as the original audit
  predicted) with a closed catalogue, daily JSONL stream, `artifacts
  events` CLI and `register_emitter` extension point. Vault marker
  negotiation was superseded by relocation (`artifacts.yaml` now at
  project root per [[t0137-implement-vault-marker-relocation-per]]).
- **§3.3 Hooks** rewritten in full against s0032: `kind: hook`,
  `x-storage: directory`, `host: artifacts-os` vs reserved `host:
  openstation`, `.active/` activation, ten-event catalogue. Marked
  **closed** on the artifacts-os side. Integration consequence
  splits cleanly: (1) storage + manifest schema is settled —
  openstation reuses `kind: hook` and `host: openstation`; (2)
  the activation model is an **open openstation-side design
  decision** (share `.active/` ↔ parallel registry ↔ no separate
  activation) with trade-offs documented in the audit.
- **§3.4 Events log** marked **closed** with the correction that the
  shipped module is `events`, not `log` — the `log/` stub remains and
  has a different (operational-run-log) purpose.
- **§3.6 Init / scaffold** marked **mostly closed** by the
  books-driven init + artbook distribution + promotion stack
  ([[s0029-artbook-mvp-distribution-model]],
  [[s0030-books-driven-init-flow]],
  [[s0031-artbook-post-pull-artifact-promotion]]). Residual
  openstation-specific work (CLAUDE.md managed section,
  `.openstation/` dir) is the only thing openstation init needs to
  overlay; `--openstation-compat` exists for the wrapper.
- **§3.9 Naming / ID drift** marked **closed on the artifacts-os
  side** by [[t0037-redefine-name-field-as-slug]] (done 2026-04-29 —
  the day after the original audit). Divergence now sits purely on
  openstation's side; resolution is a one-time openstation-side
  rewrite or a `KindDef(prefix="")` declaration. Confirmed via code
  read that `core.ids.next_prefixed_id` handles `prefix=""` correctly
  — the original audit's "needs research" question is resolved.
- **§5 Concrete divergences** rechecked. Three of five blockers have
  moved (filename prefix supported via `prefix=""`; `name`/`id`
  locked; marker relocated). Two remain (storage root divergence;
  wikilink stripping not in `core.discover.resolve`).
- **§6 Recommended shape** revised — the three "net-new artifacts-os
  specs implied" are now annotated with their shipped state. The
  diagram is updated to show `events` and `hooks` as shipped, not
  proposed.
- **`## Recommendations`** rewritten from three items to six,
  reflecting the current backlog: (1) openstation absorbs
  `artifacts_os.events`; (2) openstation ships `host: openstation`
  hook bundles via an openstation-defaults distro; (3) openstation
  init wraps `artifacts init --openstation-compat`; (4) openstation
  aligns task naming with artifacts-os; (5) openstation writes both
  markers at init time; (6) add `resolve(..., wikilink=True)` to
  `core.discover` to remove the openstation wrapper.
- **`## Sources`** refreshed: added `docs/{hooks,events,artbook,
  init-flow,migration}.md`, folder-form kind paths, specs
  s0022/s0025–s0032, artbook + events + hooks source files, the
  repo's own `artbook.yaml`. Removed the dead `artifacts/kinds/*.json`
  flat-form paths and `artifacts/artifacts.yaml` (relocated).

Frontmatter: kept `status: done` (the refresh genuinely brings the
audit current — per t0185 §6, draft was the fallback only if the
refresh failed to converge). Added an `updated: 2026-05-24` field.

## Downstream

Concrete follow-ups the refreshed audit implies but does not itself
schedule (deferred to a separate spec task per t0185 "Out of scope"):

- **Spec task** for the openstation-side adoption plan (Recs #1–#5).
  Likely shape: a single integration spec under `openstation/specs/`
  laying out the events-absorption + hooks-loader + init-wrapper +
  naming-alignment migration as four sequenced sub-tasks.
- **artifacts-os task** for `resolve(..., wikilink=True)` (Rec #6).
  Small, well-scoped change in `core.discover`. Should land before
  openstation starts deleting its strip wrapper.
- **openstation-defaults distro repo** — needed to host the
  `host: openstation` hook bundles published per Rec #2. Decision
  point flagged in §7: same distro as openstation agents, or a
  separate `openstation-hooks` distro.
- The audit notes that `core.discover.resolve` does not strip
  wikilinks. That observation is incidental — it should be filed as
  a task in artifacts-os, not buried in this audit.
