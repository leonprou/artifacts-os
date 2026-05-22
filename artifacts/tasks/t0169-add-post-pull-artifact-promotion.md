---
artifacts:
- '[[n0015-artbook-promotion-mechanism-design-brainstorm]]'
assignee: ''
created: 2026-05-17
id: t0169
kind: task
name: add-post-pull-artifact-promotion
owner: user
status: review
subtasks:
- '[[t0170-spec-the-artbook-promotion-mechanism]]'
- '[[t0173-implement-artbook-promotion-engine-and]]'
- '[[t0174-document-artbook-promotion-mechanism]]'
- '[[t0175-migrate-artbook-yaml-to-promote]]'
type: feature
---

## User story

> **As a** user pulling a distro book (or running `init` against a configured distro)
> **I want** the pulled content to land in its canonical `artifacts/…` location *and* automatically surface in any tool-specific consumer location the distro declares (e.g. `.claude/agents/`)
> **so that** the artifacts CLI and the consuming tool both see the same content without me running a second copy/symlink step, and so distros are self-installing with zero consumer config.

## Why

After the books-driven `init` flow ([[t0167-implement-books-driven-init-flow]]) lands, the artifacts-os distro's `agents` book pulls into `.claude/agents/` only — the consumer's `artifacts/agents/` is empty even though `agent` is a first-class kind. `artifacts list --kind agent` returns nothing on a freshly-initialised vault.

The fix splits cleanly into two pieces the brainstorm settled on (see [[n0015-artbook-promotion-mechanism-design-brainstorm]]):

1. **Canonical landing.** Books pull into `artifacts/…` (mirroring `src:` by default). `dest:` becomes optional and reserved for legacy / non-canonical content.
2. **Distro-author-owned promotion.** A new `promote:` field per book declares a tool-shaped consumer location. The CLI runs the promotion (symlink or copy) after every pull and ignores what the path means — it's just a vault-relative string. Distros remain self-installing; consumers add zero config.

This makes the artifacts-os distro work the way operators expect: pulled agents are immediately visible to both the artifacts CLI and Claude Code, no manual wiring.

## Intent (directional, not contract)

The architect spec sub-task owns the contract. Directional notes only:

- `artbook.yaml` v2 gains `promote:` per book (string shorthand or object form). `dest:` becomes optional and defaults to mirroring `src:` under `artifacts/…`.
- Promotion runs implicitly after `book pull` and after every `init` book step.
- Mode default is symlink with copy fallback on filesystems that can't symlink.
- CLI stays tool-agnostic — `promote:` is just a path string; no special-casing of `.claude/`, `.cursor/`, etc.
- MVP scope is **Claude only** in the sense that artifacts-os ships a Claude-flavoured distro; multi-tool support is deferred. See [[n0015]] § Multi-tool support — deferred.

## Open contract questions (deferred to spec)

The brainstorm note ([[n0015]]) lists eight open questions for the architect:

1. `dest:` migration — strict (mirror `src:` only) vs lenient.
2. `promote:` shape — single target string vs list.
3. Mode default — symlink with copy fallback vs copy always.
4. Consumer opt-out lever — `--no-promote` flag, `disable_promotion:` in `artifacts.yaml`, both, neither.
5. Bake promotion rules into `artifacts.yaml` at init? (Decides whether `artifacts create` auto-promotes user-authored content.)
6. Idempotency / stale-item cleanup on re-pull.
7. Verb naming and whether `artifacts promote` exists as an explicit re-run verb.
8. D2 fallback ([[t0167]] bundled artifacts-os skill) — does it flow through promotion, or stay special.

## Out of scope (this task / MVP)

- Tool-shape transformers (e.g. Codex's `AGENTS.md` aggregation).
- CLI-shipped tool profiles.
- Cursor / Codex distro flavours.
- Tool-aware kinds.
- Bundled tool-conventions library inside the artifacts CLI.

## Sub-tasks

- **Architect spec sub-task** — produces the technical contract resolving the eight open questions.

## Verification

Implementation-level checklist — promoted to `ready` only after the spec is approved and implementation sub-tasks are scoped.

- [ ] Architect spec produced, reviewed, approved.
- [ ] `artbook.yaml` v2 accepts `promote:` per book; existing v1 manifests still validate (or migration path documented).
- [ ] After `artifacts book pull agents` against the artifacts-os distro, **both** `artifacts/agents/` and `.claude/agents/` reflect the pulled content (one canonical, one promotion).
- [ ] `artifacts list --kind agent` returns the pulled agents after a fresh init.
- [ ] Claude Code's sub-agent picker continues to surface the same agents.
- [ ] Promotion is idempotent across repeated `book pull` runs; no duplicate files / dangling symlinks.
- [ ] Consumer opt-out lever (per architect's choice) works as documented.
- [ ] The artifacts-os distro's `artbook.yaml` is updated to the new shape and the bundled-skill flow in [[t0167]]'s D2 fallback is consistent with the promotion model.
- [ ] Docs in `docs/artbook.md` cover the `promote:` field, default mode, and consumer behaviour.

## References

- [[n0015-artbook-promotion-mechanism-design-brainstorm]] — the design exploration that produced the α + tool-agnostic decision and the eight open questions.
- [[t0167-implement-books-driven-init-flow]] — the books-driven init flow whose D2 fallback (bundled skill) intersects this work.
- `src/artifacts_os/artbook/` — current artbook implementation; `pull_book` and the placement / walker code is where promotion would slot in.
- `docs/artbook.md` — author + consumer guide; needs updates after this lands.
- `artbook.yaml` (root) — the artifacts-os repo's own distro manifest; the reference for the new shape.