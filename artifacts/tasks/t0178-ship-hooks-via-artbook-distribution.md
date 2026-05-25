---
kind: task
id: t0178
name: ship-hooks-via-artbook-distribution
type: feature
status: done
assignee: developer
owner: user
created: 2026-05-22
subtasks:
  - "[[t0179-spec-hooks-via-artbook-distribution]]"
  - "[[t0181-add-directory-storage-primitive-to]]"
  - "[[t0182-add-hook-kind-and-bundle]]"
  - "[[t0184-add-artbook-kind-hook-book]]"
completed: 2026-05-25
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

- [x] Architect spec sub-task ([[t0179-spec-hooks-via-artbook-distribution]]) is complete and approved.
- [x] All three implementation sub-tasks (t0181, t0182, t0184) are done and merged in declared order. (t0183 cancelled — scope folded into t0182.)
- [x] Directory-storage primitive (`x-storage: directory`, `x-manifest-name`) lands in `core` with file-kind and directory-kind tests, and is documented in `docs/adding-a-kind.md` § "Directory Storage".
- [x] `kind: hook` registers via `artifacts/kinds/hook/{kind.json, ARTIFACT.md}`; `artifacts list --kind hook` shows pulled bundles.
- [x] Loader fires bundle hooks for `host: artifacts-os`, silently skips foreign `host:` values, and continues to fire legacy `artifacts.yaml hooks:` with a single one-time stderr deprecation notice (suppressible via `ARTIFACTS_HOOKS_LEGACY_QUIET=1`).
- [x] `.active/` symlink mechanism: `artifacts hooks promote <slug>` activates a pulled bundle and survives a re-pull of the source book (no clobber).
- [x] CLI verbs match s0032 §7: `artifacts hooks list` (with `--host`, `--active`/`--inactive`, `--source`, `--tail`, `-j`), `artifacts hooks show <slug>`, `artifacts hooks promote/demote <slug>`, `artifacts hooks list --prune`.
- [x] Events `hook.promoted`, `hook.demoted`, `hook.pulled`, `hook.skipped` are added to `ALL_EVENT_TYPES` and emitted at the documented sites; `hook.fired`/`hook.failed` gain a `source:` key (`yaml` | `bundle`).
- [x] Artbook parser accepts `kind: hook` on a book entry, auto-sets `recurse: true`, rejects `promote:` (`ManifestError`), rejects explicit `recurse: false`, and rejects unknown `kind:` values.
- [x] artifacts-os distro's own `artbook.yaml` declares the `os-hooks` book pointing at `artifacts/hooks/`.
- [x] End-to-end integration test (`tests/integration/test_hooks_via_artbook.py`): author → `book pull` → `hooks promote` → CRUD event fires hook → re-pull preserves activation.
- [x] `docs/hooks.md`, `docs/artbook.md`, `docs/adding-a-kind.md`, `docs/events.md` updated for the new mechanism.
- [x] `n0017-hook-scripts-not-installed-in-consumer` closes (covered by the integration test).

## Verification Report

*Verified: 2026-05-25*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Architect spec sub-task (t0179) complete and approved | PASS | `openstation show t0179` → `status: done`, completed 2026-05-22, artifact `[[s0032-hooks-via-artbook-distribution]]` linked. |
| 2 | All three impl sub-tasks (t0181, t0182, t0184) done in declared order | PASS | t0181 done 2026-05-24, t0182 done 2026-05-24, t0184 done 2026-05-25; t0183 cancelled per noted scope fold. |
| 3 | Directory-storage primitive (`x-storage`, `x-manifest-name`) lands in core with tests, documented in `docs/adding-a-kind.md` § "Directory Storage" | PASS | `tests/core/test_directory_storage.py` exercises create/discover/update for file + directory kinds + `ValidationError` paths; `docs/adding-a-kind.md` line 391 has "Directory Storage" section with `x-storage`/`x-manifest-name` table rows (lines 243-244). |
| 4 | `kind: hook` registers via `artifacts/kinds/hook/{kind.json, ARTIFACT.md}`; `artifacts list --kind hook` shows pulled bundles | PASS | Both files exist; `kind.json` declares `x-storage: directory`, `x-manifest-name: {slug}.md`; live `artifacts list --kind hook` renders a table with the `demo` bundle row. |
| 5 | Loader fires `host: artifacts-os` bundle hooks, silently skips foreign hosts, legacy yaml hooks still fire with one-time deprecation notice (suppressible via `ARTIFACTS_HOOKS_LEGACY_QUIET=1`) | PASS | `src/artifacts_os/hooks/loader.py` lines 11-13, 77, 95 (default host), 152-186 (one-shot warning gated on `ARTIFACTS_HOOKS_LEGACY_QUIET` env), 202 (unknown-host warn-once), 434 (skip-from-fire). |
| 6 | `.active/` symlink mechanism: `hooks promote` activates and survives re-pull | PASS | Integration tests `test_promote_creates_active_symlink`, `test_active_dir_not_touched_by_repull`, `test_repull_preserves_hook_activation` all green. |
| 7 | CLI verbs match s0032 §7 | PASS | `artifacts hooks --help` lists `list/show/promote/demote`; `hooks list --help` shows `--host`, `--active/--inactive`, `--source {yaml,bundle}`, `--tail [N]` (sentinel default 50), `-j`, `--prune`, `--dry-run`. |
| 8 | New events added to `ALL_EVENT_TYPES`; `hook.fired/failed` gain `source:` key | PASS | `src/artifacts_os/events/catalog.py` lines 22-27 (six event constants), 111/125 (`source: str \| None = None  # "yaml" \| "bundle"` on `HookFired`/`HookFailed` payloads). |
| 9 | Artbook parser accepts `kind: hook`, auto-sets `recurse: true`, rejects `promote:`, rejects explicit `recurse: false`, rejects unknown kinds | PASS | `src/artifacts_os/artbook/manifest.py` lines 254-281 enforce D116-D118 (closed enum: only `"hook"`, `ManifestError` on unknown; `promote:` forbidden; explicit `recurse: false` rejected; auto-set `recurse = True`). |
| 10 | distro's `artbook.yaml` declares `os-hooks` book pointing at `artifacts/hooks/` | PASS | `artbook.yaml` lines 70-73: `name: os-hooks`, `src: artifacts/hooks/`, `kind: hook`. |
| 11 | End-to-end integration test covers author → pull → promote → fire → re-pull | PASS | `tests/integration/test_hooks_via_artbook.py` runs 13/13 passing in 1.03s. |
| 12 | `docs/hooks.md`, `docs/artbook.md`, `docs/adding-a-kind.md`, `docs/events.md` updated | PASS | `docs/hooks.md` (503 lines, full bundle/promote/CLI reference); `docs/artbook.md` "Hook Books" section line 767; `docs/events.md` lines 24-29 document all six events incl. `source` field; `docs/adding-a-kind.md` § "Directory Storage" line 391. |
| 13 | `n0017-hook-scripts-not-installed-in-consumer` closes | PASS | `openstation show n0017` → `status: closed`, `closed: 2026-05-25`, `resolved_by: "[[t0178-ship-hooks-via-artbook-distribution]]"`. |

### Summary

13 passed, 0 failed. All verification criteria satisfied — the hooks-via-artbook distribution mechanism ships end-to-end (directory-storage primitive, hook kind, bundle-aware loader, `.active/` promotion, `kind: hook` artbook book type, self-hosted `os-hooks` distro book, refreshed docs, and a green integration suite that proves the n0017 papercut is closed).

## Findings

Verification pass on 2026-05-25 (PM):

- All four sub-tasks complete (t0179 done 2026-05-22; t0181 done 2026-05-24; t0182 done 2026-05-24; t0184 done 2026-05-25). t0183 cancelled, scope folded into t0182 per the 2026-05-24 trim.
- Integration test suite green: `tests/integration/test_hooks_via_artbook.py` — 13/13 passing (pull lands bundle, emits `hook.pulled`, re-pull preserves `.active/` and reports `overwritten`, no-op promote for hook books, list shows bundle, promote creates symlink, loader picks up `.active/`, hook fires + sentinel, `hook.fired` carries `source: bundle`, re-pull preserves activation, `os-hooks` book parses + pulls into a fresh consumer).
- Broader hook/artbook/directory-storage test surface: 296/296 passing (artbook state, hooks CLI, core directory storage, hook bundle/loader/actions, events e2e).
- CLI surface matches s0032 §7: `artifacts hooks {list,show,promote,demote}` registered as flat verbs; `list` exposes `--host`, `--active`/`--inactive`, `--source {yaml,bundle}`, `--tail [N]` with sentinel default 50, `-j/--json`, `--prune`, `--dry-run`. `artifacts list --kind hook` renders the bundle table.
- Event catalog covers all six events (`hook.fired`, `hook.failed`, `hook.skipped`, `hook.promoted`, `hook.demoted`, `hook.pulled`) with payload dataclasses; `docs/events.md` documents the `source: yaml|bundle` field on `hook.fired`/`hook.failed`.
- Artbook parser enforces D116–D118: closed enum on `kind:` (currently `"hook"` only), `kind: hook` auto-sets `recurse: true` and rejects explicit `recurse: false`, rejects `promote:`, raises `ManifestError` on unknown `kind:` values.
- Self-hosted distro: root `artbook.yaml` declares the `os-hooks` book (`src: artifacts/hooks/`, `kind: hook`); ships the `demo` bundle as a working example.
- Docs refreshed: `docs/hooks.md` (~470 lines) covers bundle layout, manifest frontmatter, sibling-file resolution, `source:` distinction, host dispatch, promote/demote, re-pull preservation, stale-symlink policy, full CLI reference, and legacy migration; `docs/artbook.md` documents the `kind: hook` book type; `docs/adding-a-kind.md` § "Directory Storage" covers `x-storage`/`x-manifest-name`; `docs/events.md` lists all new event types.
- Papercut [[n0017-hook-scripts-not-installed-in-consumer]] marked `closed` with backlink to this task; integration test `test_pull_lands_bundle_in_consumer` + `test_hook_fires_and_creates_sentinel` together prove the consumer no longer needs to hand-copy hook scripts.

Verified by: product-manager (verifier role per `owner: user`, executed on the user's behalf).
