---
kind: task
id: t0179
name: spec-hooks-via-artbook-distribution
type: spec
status: done
assignee: architect
owner: user
parent: "[[t0178-ship-hooks-via-artbook-distribution]]"
created: 2026-05-22
started: 2026-05-22
artifacts:
  - "[[openstation/specs/s0032-hooks-via-artbook-distribution]]"
completed: 2026-05-22
---

# Spec Hooks-Via-Artbook Distribution + Directory-Storage Kinds

## Requirements

- Produce a single spec (weak prior per [[n0018-hooks-via-artbook-design-brainstorm]] §12) covering: directory-storage kinds primitive, hook kind + manifest schema, `.active/` promotion mechanism, hook CLI verbs, and the `type: hook` artbook book type.
- Resolve the 12 open contract questions enumerated in n0018 "Open contract questions": `.active/` naming, `x-storage` field shape, `x-manifest-name` template default, sibling-file resolution rule, stale-symlink cleanup behavior, legacy `hooks:` migration tool scope, `--attach` flag treatment, `host:` enum policy, skills-as-kind sibling relationship, hook book-type semantic differences, auto-promote policy for locally-authored hooks, combined-vs-split spec decision.
- Define the loader contract: which loader fires which `host:` value, how an `.active/` symlink is resolved into a fired hook, and how legacy `artifacts.yaml hooks:` entries coexist (soft-deprecation path).
- Define the events the new mechanism emits (pull/promote/demote/fire) so the existing events stream stays the single source of truth.
- Specify the CLI surface: `artifacts hooks list|show|promote|demote` flag shape, table columns, JSON output, and how it composes with `artifacts list --kind hook`. Must match the CLI conventions in `CLAUDE.md` (flat verbs, default Rich table, `-j` for JSON, `--tail` semantics where applicable, top-level filter flags).
- Specify the artbook `type: hook` book contract: canonical landing path, absence of auto-promote, and any manifest-side requirements distinct from existing book types.
- Identify the sub-task decomposition the developer will execute (e.g. "x-storage primitive" → "hook kind + loader" → "promote/demote + .active/" → "hook book type in artbook"), so the parent's verification checklist can be derived from it.
- Out of scope (per n0018): OpenStation adoption, skills-as-kind migration, cryptographic trust posture, `--attach` flag, one-shot migration tool.

## Verification

- [ ] Spec document created under `artifacts/specs/` and linked from the parent task
- [ ] All 12 contract questions from n0018 are answered (or explicitly deferred with rationale)
- [ ] Loader contract documented: host dispatch, symlink resolution, legacy coexistence
- [ ] Events emitted by the new mechanism enumerated
- [ ] CLI surface specified (verbs, flags, output modes) and consistent with CLI conventions in `CLAUDE.md`
- [ ] Artbook `type: hook` semantics specified and contrasted with existing book types
- [ ] Implementation sub-task decomposition listed so parent verification can be authored
- [ ] User approves the spec before the parent feature task flips to `ready`

## Findings

Locked the combined spec [[openstation/specs/s0032-hooks-via-artbook-distribution]]
covering directory-storage primitive, hook kind + loader, `.active/`
promotion, hook CLI verbs, and the new `kind: hook` artbook book
field. Twenty new locked decisions (D101–D120) carry the contract.

Key design moves worth flagging to the reviewer:

- **`x-storage: directory` as a generic primitive (D103, §2).**
  The hook kind is the first consumer, but the field lives on
  `kind.json`/`KindDef` so the skills-as-kind sibling task lands
  with no further loader work — skills will set
  `x-manifest-name: "SKILL.md"` and otherwise reuse the same code.
- **Manifest file is the symlink target, not the bundle dir
  (D110).** `os.readlink` returns the `.md` file path; the loader
  derives the bundle via `target.parent`. One syscall, both
  pieces.
- **Artbook field rename — `kind:` not `type:` (D116).** v2's
  parser already rejects any `type:` key on books (legacy v1
  schema). Reusing `type:` would either require relaxing that
  rejection (regression risk) or live with a confusing clash.
  `kind:` is fresh and forward-compatible (closed enum, MVP =
  `hook` only).
- **`hook.pulled`, `hook.promoted`, `hook.demoted`, `hook.skipped`
  added to the closed events catalogue (§5).** `hook.fired` /
  `hook.failed` gain an optional `source:` key so consumers can
  distinguish yaml-list from bundle hooks. The catalogue gate at
  s0025 § C2 is preserved — new events land in the same commit
  as the loader.
- **Locally-authored hooks are never auto-promoted (D119, Q11).**
  Pull and hand-authoring are treated identically: activation is
  always `artifacts hooks promote <slug>`. This was the new
  question added beyond n0018's original 10.
- **Combined single spec (D120, Q12).** Decomposition for
  execution lives in s0032 §9 (four sequential implementation
  sub-tasks, t0181 → t0184). The parent t0178 verification
  checklist has been re-derived from the spec and recorded in
  full.

Sub-tasks created under the parent:

- t0181 — Add directory-storage primitive to core (s0032 §2)
- t0182 — Add hook kind and bundle-aware loader (s0032 §3 + §6)
- t0183 — Add `.active/` promotion mechanism and hook CLI verbs (s0032 §4 + §7)
- t0184 — Add artbook `kind: hook` book type and pull pipeline (s0032 §8)

The parent task body now lists these under a `## Subtasks` section
and carries the re-derived verification checklist.

## Downstream

- **Sibling task — skills-as-kind migration.** n0018 §4 flags this
  as a strong follow-up. The spec deliberately keeps the
  directory-storage primitive generic (Q9) so the skills task
  should not require any loader/registry code change beyond the
  new `artifacts/kinds/skill/{kind.json, ARTIFACT.md}` files and a
  pull-side renamer for existing `artifacts/skills/<unit>/`
  layouts. Worth filing as a separate parent task once t0178 lands.
- **OpenStation adoption.** Separate task in the OpenStation repo
  per D8 / §11. Their loader will reuse this spec verbatim —
  same `.active/` tree, same matcher vocabulary, just a different
  `host:` filter (`openstation`).
- **Optional fast-follows.** `--attach <path>` flag on
  `artifacts create --kind hook` (D115); one-shot migration tool
  for `artifacts.yaml hooks:` → bundles (D114); a generic
  `artifacts delete --kind hook <slug>` verb (§2.4). None block
  the parent feature.
- **Documentation surface.** Sub-task t0184 should add a
  `## Hook Books` section to `docs/artbook.md` and a "Migrating
  from the legacy hooks list" section to `docs/hooks.md` so the
  deprecation notice has a clear destination link.

## Progress

- 2026-05-22 — Read brainstorm n0018, papercut n0017, parent t0178,
  and the existing hooks/events/artbook/adding-a-kind docs.
  Surveyed loader (`src/artifacts_os/hooks/loader.py`), kind
  registry (`src/artifacts_os/core/registry.py` `_load_vault_kinds`),
  store create path, and artbook manifest parser. Confirmed v2
  artbook manifest already rejects `type:` on books — chose
  `kind:` as the new field instead.
- 2026-05-22 — Drafted [[openstation/specs/s0032-hooks-via-artbook-distribution]]
  (20 locked decisions D101–D120, 12 contract questions resolved,
  loader + events + CLI + book-type sections, sub-task decomposition).
- 2026-05-22 — Created implementation sub-tasks t0181, t0182, t0183,
  t0184 under parent t0178, in declared execution order. Updated
  parent body with `## Subtasks` and re-derived verification
  checklist.
- 2026-05-22 — Transitioning t0179 to `review` for user approval
  per the final verification item ("User approves the spec before
  the parent feature task flips to `ready`").
