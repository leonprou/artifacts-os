---
created: 2026-05-17
id: n0015
kind: note
name: artbook-promotion-mechanism-design-brainstorm
---

## Context

Session brainstorm (2026-05-17) refining the design for **post-pull artifact promotion** — bridging downloaded book content from its canonical `artifacts/…` location to consumer-tool-shaped locations like `.claude/agents/`.

Related: [[t0165-init-selection-driven-by-books]], [[s0030-books-driven-init-flow]], [[t0167-implement-books-driven-init-flow]], `docs/artbook.md`, `artbook.yaml`.

## The gap we identified

Today's artifacts-os distro `artbook.yaml` declares `dest: .claude/agents/` for the agents book. Result: after `book pull`, agents land **only** in `.claude/agents/`. The consumer's `artifacts/agents/` is empty even though `agent` is a first-class kind. `artifacts list --kind agent` returns nothing. Claude is the only consumer that can see them; the artifacts CLI cannot.

Same shape for any dual-purpose content (agents, kinds, possibly skills). Each tool (Claude, Cursor, Codex) has different consumer conventions; the single-`dest` model forces the distro author to pick one view at the expense of the other.

## Framings considered (diverged before converging)

| Framing | Mechanism | Verdict |
|---|---|---|
| A — Single canonical store + generated views | Files in `artifacts/`; `.claude/` is regenerated | Path we ended up on |
| B — Dual destinations in manifest | `dest: { vault, claude }` | Manifest leaks tool assumptions |
| C — Consumer-side exposures in `artifacts.yaml` | Consumer declares promotions | Burdens consumer setup |
| D — One-time symlink at init | `ln -s artifacts/agents .claude/agents` | Too brittle; Windows breaks |
| E — Drop `artifacts/agents/` view; let agents live in `.claude/` | Tool-specific kind `dir` | Layering violation; asymmetric |
| F — Projections (build-step model) | Canonical store + named output renderings | Over-engineered for one tool |

## Locked direction

1. **Books download to `artifacts/…`** — single canonical location. `dest:` in `artbook.yaml` becomes optional / defaults to mirror `src:`.
2. **Distro author owns the promotion config** (option α). New `promote:` field per book in `artbook.yaml`. Self-installing distros — zero consumer config required.
3. **CLI stays tool-agnostic.** `promote:` is just a vault-relative path string; the CLI doesn't know `.claude/` is special.
4. **Tool-flavored distros are the scaling unit, not tool-flavored CLI features.** Cursor support = someone writes a cursor-defaults distro. Codex support = someone writes a codex-defaults distro that emits `AGENTS.md` as its source.

## Strawman `artbook.yaml` shape

```yaml
books:
  - name: agents
    src: artifacts/agents/
    # dest omitted → defaults to artifacts/agents/
    promote: .claude/agents/       # shorthand, symlink default

  - name: kinds
    src: artifacts/kinds/
    # no promote — canonical only

  - name: skills
    src: artifacts/skills/
    promote:
      target: .claude/skills/
      mode: copy
      recurse: true
```

## Multi-tool support — deferred

We pulled on Cursor (path-only, model handles it) and Codex (shape mismatch — `AGENTS.md` aggregation). Decided:

- **Cursor:** the α model handles it as-is. A cursor-defaults distro just declares `promote: .cursor/rules/`. Optional `extension:` rename smooths `.md → .mdc`.
- **Codex:** shape mismatch is real. The clean answer under α is "a codex-flavored distro commits already-aggregated content". CLI-side transformers (the projection model F) is the alternative — rejected as speculative for now.
- **Scope call: MVP supports Claude only.** Multi-tool revisits when (a) a second tool has real traction or (b) the "fork-per-tool" cost for distro authors becomes visible.

## Open contract questions (defer to architect spec)

1. **`dest:` migration** — strict (only mirror `src:`) or keep flexible? Likely v2 of artbook.yaml.
2. **`promote:` shape** — single target string vs list. List enables future multi-tool but adds schema complexity.
3. **Mode default** — symlink with copy fallback (POSIX), or copy always (portability).
4. **Consumer opt-out** — `--no-promote` flag, `disable_promotion: true` in `artifacts.yaml`, both, neither?
5. **Bake promotion rules into `artifacts.yaml` at init?** Decides whether user-authored content auto-promotes on `artifacts create`, or promotion is book-pull-only.
6. **Idempotency** — symlinks trivially idempotent; copies need hash or force; stale-item cleanup policy on re-pull.
7. **Verb name** — "promote" / "mount" / "expose" / "link". Also: do we want `artifacts promote` as an explicit re-run verb?
8. **D2 fallback in [[t0167]]** — bundled artifacts-os skill: write to `artifacts/skills/artifacts-os/` + promote, or stay special (`.claude/skills/` direct)?

## Things explicitly out of scope (MVP)

- Transformers / shape conversion (Codex's `AGENTS.md`).
- CLI-shipped tool profiles (the ε option).
- Cursor / Codex support in the artifacts-os distro itself.
- Re-architecting kinds to be tool-aware.

## References

- Earlier session brainstorm under [[t0165]] / [[t0166]] led to the books-driven `init` flow; this brainstorm is a follow-on identifying a gap that surfaces *after* books-driven init lands.
- t0167 verification for D2 (bundled skill) already implicitly depends on this promotion model — open question 8 above.