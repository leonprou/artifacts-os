---
assignee: developer
created: 2026-05-15
id: t0157
kind: task
name: book-local-distro-mode
owner: user
parent: '[[t0150-artbook-distribution-model]]'
status: done
type: implementation
started: 2026-05-15
completed: 2026-05-15
---

# Book Local Distro Mode

## Goal

Add D23 local-manifest auto-detect to `artifacts book list / show` so distro authors (Layout B in [[s0029-artbook-mvp-distribution-model]]) can preview their `artbook.yaml` from inside the repo without configuring a synthetic `distro_url` or pushing to git first.

## Why

D23 in the spec introduces an author-side flow: when `<vault_root>/artbook.yaml` exists, `list` and `show` read it in place; otherwise the existing remote-clone path is used. A `--remote` flag forces the clone path even when a local manifest is present. `pull` is *not* subject to auto-detect (preserves the deferred-dogfood-migration guardrail in §1.3 / §7.2.1).

The data layer (`manifest.load_manifest(path)` in [[t0153-artbook-module-manifest-fetch-placement]]) already supports loading from a directory. This task wires that capability into the CLI verbs in [[t0154-artifacts-book-cli-command-list]] and adds the `--remote` flag.

## Depends on

- [[t0154-artifacts-book-cli-command-list]] — the base `book list / show / pull` commands this task extends.

## Scope

1. **`list` / `show` auto-detect** — before falling through to the remote clone, check for `<vault_root>/artbook.yaml`. If present, call `manifest.load_manifest(<vault_root>)` directly and render.
2. **`--remote` flag** — when present on `list` or `show`, skip local-manifest detection and force the remote-clone path.
3. **`pull` unaffected** — `pull` always clones the remote regardless of local manifest presence; D23's deferred-dogfood-migration guardrail stays intact.
4. **Error paths** — local manifest invalid → exit 1 using the same error catalogue as the remote path; no special "but it's local" hint required.

## Out of scope

- `book pull` against a local manifest (deferred — would write to a destination that may already be the source).
- Local-manifest validation differences vs. the remote path.
- Manifest discovery beyond `<vault_root>/artbook.yaml` (no search up the tree, no alternative filenames).

## Implementation hints (intent, not contract)

- Data-layer change: none. `manifest.load_manifest(path)` already accepts any directory containing `artbook.yaml`.
- All changes live inside `cli/commands/book.py`.

## Verification

- [x] `artifacts book list` in a vault containing `<vault>/artbook.yaml` and no `artbook.distro_url` configured returns the local manifest's books with no network access.
- [x] `artifacts book show <name>` in the same vault returns the book contents from the local manifest.
- [x] `artifacts book list --remote` in the same vault forces the clone path (or exits 4 if `artbook.distro_url` is unset).
- [x] `artifacts book pull <name>` in the same vault always clones the remote regardless of the local manifest.
- [x] Tests cover the four scenarios above.

## Verification Report

*Verified: 2026-05-15*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `book list` reads local `artbook.yaml` with no network when `distro_url` unset | PASS | `cli/commands/book.py` `_run_list` lines 170–195 — checks `root / "artbook.yaml"` before the `distro_url` gate, calls `load_manifest(root)`. Tests `test_book_list_local_manifest_table` / `test_book_list_local_manifest_json` (test_book.py:439–463) verify exit 0, distro name "local-distro", `(local)` marker, `local: True` / `url: None` in JSON. |
| 2 | `book show <name>` returns book contents from local manifest | PASS | `_run_show` lines 352–379 mirrors the auto-detect, then `_render_book_show` with `distro_url=""`. Tests `test_book_show_local_manifest` / `test_book_show_local_manifest_json` (test_book.py:466–493) verify exit 0, `(local)` marker, `architect.md` + `developer.md` listed, `README.md` excluded, `local: True` in JSON. |
| 3 | `book list --remote` forces clone path (exits 4 when `distro_url` unset) | PASS | `--remote` registered on both `list` and `show` parsers (book.py:633–639, 655–661). `_run_list` line 174 short-circuits local path when `args.remote`. Test `test_book_list_remote_flag_bypasses_local` (test_book.py:496–501) and `test_book_show_remote_flag_bypasses_local` (504–509) confirm exit 4 with `distro_url` error. |
| 4 | `book pull` always clones regardless of local manifest | PASS | `_run_pull` (book.py:470–477) calls `_artbook_settings_from_raw(raw)` and gates on `distro_url` unconditionally — no local-manifest branch exists. Test `test_book_pull_ignores_local_manifest` (test_book.py:512–517) confirms exit 4 with `distro_url` error when local manifest present but `distro_url` unset. |
| 5 | Tests cover the four scenarios above | PASS | D23 test block at test_book.py:398–517 covers all four scenarios (list local table+json, show local table+json, `--remote` bypass for list and show, pull ignores local). Full suite (30 tests) passes via `pytest tests/cli/test_book.py`. |

### Summary

5 passed, 0 failed. All verification criteria pass — D23 local-manifest auto-detect is wired into `list` and `show`, `--remote` cleanly bypasses it, `pull` is unaffected, and the four spec scenarios are covered by tests.

## References

- Parent feature: [[t0150-artbook-distribution-model]]
- Spec: [[s0029-artbook-mvp-distribution-model]] — D23
- Predecessor (CLI command base): [[t0154-artifacts-book-cli-command-list]]
- Predecessor (artbook module): [[t0153-artbook-module-manifest-fetch-placement]]
## Findings

All changes confined to `src/artifacts_os/cli/commands/book.py` (as hinted). No data-layer changes — `manifest.load_manifest(path)` was already ready.

**What was built:**
- `_run_list` and `_run_show` check for `<vault_root>/artbook.yaml` before the `distro_url` gate. When found and `--remote` absent, the local manifest is loaded via `load_manifest(root)` and rendered with `url=(local), sha=None`.
- `--remote` flag added to both `list` and `show` parsers; skips auto-detect and runs the remote-clone path (exits 4 if `distro_url` is unset).
- `_run_pull` is unchanged — `distro_url` is required unconditionally.
- Shared render helpers `_render_book_list` and `_render_book_show` extracted to avoid duplicating rich/json output logic between local and remote branches.
- 7 new tests in `tests/cli/test_book.py` cover all four spec scenarios (table + json variants, `--remote` bypass, pull ignoring local manifest). All 26 tests pass.
