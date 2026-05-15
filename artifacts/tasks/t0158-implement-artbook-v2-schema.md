---
assignee: developer
created: 2026-05-15
id: t0158
kind: task
name: implement-artbook-v2-schema
owner: user
parent: '[[t0150-artbook-distribution-model]]'
status: done
type: implementation
started: 2026-05-15
completed: 2026-05-15
---

# Implement Artbook V2 Schema

## Goal

Bring the `artbook` module, the `artifacts book` CLI command, and this repo's local `artbook.yaml` in line with the v2 schema decisions **D24** and **D25** in [[s0029-artbook-mvp-distribution-model]].

## Why

The architect revised the spec on 2026-05-15 to drop per-book `type:` dispatch and require an explicit `dest:` per book. The implementation lag is expected — spec changes first, code follows in a dedicated task. This task closes the lag.

- **D24** (supersedes D3) — drop `type:` from the manifest; books are pure `(name, src, dest)`. The directory walker (D20) and explicit-allowlist (D18) apply uniformly; no per-type handler dispatch, no `_PLACEMENT` table, no `UnknownBookTypeError`. Adding skills / commands / hooks books becomes schema-trivial — no library change required.
- **D25** (supersedes D8) — each book declares its own vault-relative `dest:` in the manifest. Parser rejects `..`, absolute paths, and any value resolving outside the vault. Write-time re-checks the resolved path (defense-in-depth).

## Scope

Four surfaces. Tests follow each.

### Manifest parser

1. Reject `type:` on any book entry with a clear migration hint ("v1 schema field — removed in v2; remove `type:` from your manifest").
2. Rename `path:` → `src:`; reject `path:` with a clear "renamed to `src:` in v2" hint.
3. Require `dest:` on every book entry.
4. Vault-escape guard on `dest:` at parse time — reject `..`, absolute paths, and any value that resolves outside the vault root.

### `artbook` module (`src/artifacts_os/artbook/`)

5. `Book` dataclass — replace `path` with `src`; add `dest` field.
6. Replace `_PLACEMENT` dispatch with the one-liner `destination_for(vault_root, book)` returning `vault_root / book.dest`.
7. Remove `UnknownBookTypeError`.
8. Replace per-type handlers with one universal copy handler (`_copy_book`) — D20 walker + D18 allowlist apply identically to every book.
9. Write-time defense-in-depth — re-check the resolved `dest` path before writing each file; raise a clear "dest escapes vault" error on violation.

### CLI surface (`src/artifacts_os/cli/commands/book.py`)

10. `book list` table columns: `Name | Source | Destination | Description` (was `Name | Type | Path | …`).
11. `book show` lines: `Source:` / `Destination:`; no `Type:` line.
12. `--json` payloads use `src` / `dest`; drop the standalone `destination` key from `show --json` output (it's already `book.dest`).
13. Exit-code 1 narrative in `--help` / error messages — drop "unknown book type"; add "dest escapes vault" and "removed v1 `type:` field" cases.

### Local distro manifest

14. Update this repo's own `artbook.yaml` to v2 — rename `path:` → `src:`, drop `type:`, add `dest:` per book.

## Out of scope

- Multi-destination-per-book (already schema-trivial per spec §9 seam; no v1 use case ships).
- Optional future `kind:` annotation (deferred seam per spec §10).
- Migration tooling for third-party distros (none exist yet).

## Depends on

- [[t0154-artifacts-book-cli-command-list]] — the v1 CLI surface this task migrates.
- [[t0153-artbook-module-manifest-fetch-placement]] — the v1 module this task migrates.

## Downstream

- [[t0157-book-local-distro-mode]] should land *after* this task so the local-mode wiring uses v2 field names from the start. Re-confirm t0157's verification still holds after v2 schema lands.

## Progress

### 2026-05-15 12:20:18 — Incomplete run (r0167)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$2.19, turns=51

## Verification

- [x] Manifest parser rejects `type:` with a v2 migration hint.
- [x] Manifest parser rejects `path:` and accepts `src:`.
- [x] Manifest parser rejects `dest:` containing `..`, absolute paths, or values that resolve outside the vault.
- [x] `Book` dataclass exposes `src` and `dest`; no `path` or `type` field.
- [x] `_PLACEMENT` removed; `destination_for` is a one-line join.
- [x] `UnknownBookTypeError` removed; one universal copy handler covers every book (no per-type dispatch).
- [x] `book list` shows `Name | Source | Destination | Description`.
- [x] `book show` shows `Source:` / `Destination:` lines, no `Type:` line.
- [x] `--json` payloads use `src` / `dest`.
- [x] This repo's `artbook.yaml` validates against the v2 parser.
- [x] All existing tests pass after schema migration; new tests cover the vault-escape guard and the `type:` / `path:` rejections.

## Verification Report

*Verified: 2026-05-15*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Manifest parser rejects `type:` with a v2 migration hint | PASS | `manifest.py:54-58` raises ManifestError with "v1 schema field 'type' — removed in v2" |
| 2 | Manifest parser rejects `path:` and accepts `src:` | PASS | `manifest.py:61-65` rejects `path:` with "renamed to `src:` in v2"; `src` accepted at line 74 |
| 3 | Manifest parser rejects `dest:` with `..` / absolute / vault-escape | PASS | `manifest.py:88-96` parse-time guard; `placement.py:131-137` write-time `is_relative_to` defense-in-depth |
| 4 | `Book` dataclass exposes `src` and `dest`; no `path` or `type` field | PASS | `manifest.py:22-35` — fields are `name`, `src`, `dest`, `description`, `files` only |
| 5 | `_PLACEMENT` removed; `destination_for` is a one-line join | PASS | `placement.py:41-48` is `return vault_root / book.dest`; grep finds no `_PLACEMENT` in src/ |
| 6 | `UnknownBookTypeError` removed; one universal copy handler | PASS | `errors.py` no longer defines `UnknownBookTypeError`; `placement.py:120` `_copy_book` is the sole handler |
| 7 | `book list` shows `Name \| Source \| Destination \| Description` | PASS | `book.py:152-157` columns + live output confirms `Name \| Source \| Destination \| Description` |
| 8 | `book show` shows `Source:` / `Destination:` lines, no `Type:` line | PASS | `book.py:282-283` prints `Source:` and `Destination:`; live output confirms no `Type:` line |
| 9 | `--json` payloads use `src` / `dest` | PASS | Live `book list --json` and `book show --json` outputs include `src`/`dest`; no standalone `destination` key in `show --json` |
| 10 | Local `artbook.yaml` validates against v2 parser | PASS | `parse_manifest(yaml.safe_load(...))` returns `Book(name='agents', src='artifacts/agents/', dest='.claude/agents/')` |
| 11 | All existing tests pass; new tests cover guard + rejections | PASS | `pytest tests/artbook/ tests/cli/test_book.py` → 78 passed; `test_manifest.py` contains rejection + escape-guard cases |

### Summary

11 passed, 0 failed. Task is ready to be marked verified.

## References

- Parent feature: [[t0150-artbook-distribution-model]]
- Spec: [[s0029-artbook-mvp-distribution-model]] — D24, D25, §3, §4, §5, §7
## Findings

All four surfaces migrated in commit `b102bd2`. 78 artbook+CLI-book tests pass.

- **Manifest parser**: `Book` dataclass now has `src`/`dest`; rejects `type:` ("removed in v2"), rejects `path:` ("renamed to src:"), requires `dest:`. Vault-escape guard rejects absolute paths and `..` in `dest:` at parse time.
- **Placement module**: `_PLACEMENT` removed; `destination_for(vault_root, book)` = `vault_root / book.dest`. `UnknownBookTypeError` removed. Universal `_copy_book` handler; write-time guard via `is_relative_to()` raises "escapes vault root".
- **CLI**: `book list` → Name|Source|Destination|Description. `book show` → Source:/Destination:, no Type:. `--json` uses `src`/`dest`, drops standalone `destination` key. `UnknownBookTypeError` handling removed.
- **artbook.yaml**: updated to `src: artifacts/agents/` / `dest: .claude/agents/`; validates against v2 parser.
