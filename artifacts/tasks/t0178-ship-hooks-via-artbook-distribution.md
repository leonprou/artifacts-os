---
kind: task
id: t0178
name: ship-hooks-via-artbook-distribution
type: feature
status: review
assignee: developer
owner: user
created: 2026-05-22
subtasks:
  - "[[t0179-spec-hooks-via-artbook-distribution]]"
  - "[[t0181-add-directory-storage-primitive-to]]"
  - "[[t0182-add-hook-kind-and-bundle]]"
  - "[[t0184-add-artbook-kind-hook-book]]"
---

# Ship Hooks-Via-Artbook Distribution Mechanism

## Requirements

- As an operator of an artifacts-os consumer project, I want to receive hook scripts the same way I receive agents and skills — via `artifacts book pull` — so I no longer hand-copy `bin/hooks/*` files from upstream repos (closes the [[n0017-hook-scripts-not-installed-in-consumer]] papercut).
- As an author of a hook, I want the matcher and the script to live together as a single artifact so they cannot drift apart and can be shipped, listed, and referenced like every other artifact.
- As an operator, I want pulling a registry of hooks to be **inert** until I explicitly promote a hook, and I want my promotion decisions to **survive a re-pull** of the registry.
- As an operator, I want activation state to be visible in version control so changes to which hooks fire are PR-reviewable and consistent across developers/CI.
- As a future OpenStation adopter, I want the same mechanism to work for OpenStation-host hooks without requiring artifacts-os to know OpenStation's internals (decoupled codebases, shared substrate).
- *Intent, not contract:* the directory-storage primitive built here should be reusable by other directory-shaped kinds (e.g. skills) — exact reuse path is the architect's call.

Source brainstorm: [[n0018-hooks-via-artbook-design-brainstorm]].
Architect spec: [[s0032-hooks-via-artbook-distribution]] (s0032 §9 defines this decomposition).

## Subtasks

- [[t0179-spec-hooks-via-artbook-distribution]] — architect spec (gates the rest). **DONE**.
- [[t0181-add-directory-storage-primitive-to]] — implement s0032 §2 (`x-storage` + `x-manifest-name`, `core.create` + discover branches, docs).
- [[t0182-add-hook-kind-and-bundle]] — implement s0032 §3 + §4 + §6 + §7 (hook kind, bundle-aware loader, host dispatch, `.active/` promotion, CLI verbs, new events). Scope of cancelled t0183 folded in (2026-05-24 PM trim — loader + `.active/` are one coherent deliverable).
- [[t0184-add-artbook-kind-hook-book]] — implement s0032 §8 (artbook `kind:` field, pull pipeline emits `hook.pulled`, artifacts-os distro ships `os-hooks` book, end-to-end integration test).
- ~~t0183-add-active-promotion-mechanism-and~~ — **cancelled (rejected)**, scope merged into t0182.

## Verification

- [ ] Architect spec sub-task ([[t0179-spec-hooks-via-artbook-distribution]]) is complete and approved.
- [ ] All three implementation sub-tasks (t0181, t0182, t0184) are done and merged in declared order. (t0183 cancelled — scope folded into t0182.)
- [ ] Directory-storage primitive (`x-storage: directory`, `x-manifest-name`) lands in `core` with file-kind and directory-kind tests, and is documented in `docs/adding-a-kind.md` § "Directory Storage".
- [ ] `kind: hook` registers via `artifacts/kinds/hook/{kind.json, ARTIFACT.md}`; `artifacts list --kind hook` shows pulled bundles.
- [ ] Loader fires bundle hooks for `host: artifacts-os`, silently skips foreign `host:` values, and continues to fire legacy `artifacts.yaml hooks:` with a single one-time stderr deprecation notice (suppressible via `ARTIFACTS_HOOKS_LEGACY_QUIET=1`).
- [ ] `.active/` symlink mechanism: `artifacts hooks promote <slug>` activates a pulled bundle and survives a re-pull of the source book (no clobber).
- [ ] CLI verbs match s0032 §7: `artifacts hooks list` (with `--host`, `--active`/`--inactive`, `--source`, `--tail`, `-j`), `artifacts hooks show <slug>`, `artifacts hooks promote/demote <slug>`, `artifacts hooks list --prune`.
- [ ] Events `hook.promoted`, `hook.demoted`, `hook.pulled`, `hook.skipped` are added to `ALL_EVENT_TYPES` and emitted at the documented sites; `hook.fired`/`hook.failed` gain a `source:` key (`yaml` | `bundle`).
- [ ] Artbook parser accepts `kind: hook` on a book entry, auto-sets `recurse: true`, rejects `promote:` (`ManifestError`), rejects explicit `recurse: false`, and rejects unknown `kind:` values.
- [ ] artifacts-os distro's own `artbook.yaml` declares the `os-hooks` book pointing at `artifacts/hooks/`.
- [ ] End-to-end integration test (`tests/integration/test_hooks_via_artbook.py`): author → `book pull` → `hooks promote` → CRUD event fires hook → re-pull preserves activation.
- [ ] `docs/hooks.md`, `docs/artbook.md`, `docs/adding-a-kind.md`, `docs/events.md` updated for the new mechanism.
- [ ] `n0017-hook-scripts-not-installed-in-consumer` closes (covered by the integration test).
