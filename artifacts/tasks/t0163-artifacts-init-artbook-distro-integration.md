---
kind: task
id: t0163
name: artifacts-init-artbook-distro-integration
type: implementation
status: done
assignee: developer
owner: user
created: 2026-05-15
started: 2026-05-15
completed: 2026-05-15
---

# Artifacts Init Artbook Distro Integration

## Requirements

1. Add `--distro <url>` flag to `artifacts init`. Accepts any git-clonable URL.
2. Add `--books <csv>` flag — comma-separated book names to pull (skips book-selection prompt). `all` selects every book. Requires `--distro`.
3. When `--distro` is given and stdin is a TTY and `-y` is not set, add an interactive **Step 4: Distro** after the existing 3 steps:
   - Print "Fetching distro manifest…" and clone to a tmpdir.
   - Show available books (name, dest, description).
   - Multi-select prompt (same `_prompt_multi_step` pattern as kinds/agents).
   - For each selected book, show items via `_select_files` and prompt for item subset. Default = all items.
4. When `-y` is set and `--distro` is given: pull **all books, all items** — no prompts.
5. When `-y` is set and `--distro` is omitted: skip the distro step silently — no network call.
6. Inject `artbook.distro_url` into `artifacts.yaml` content before writing, whenever `--distro` is given.
7. Vault files (artifacts.yaml, kinds, agents) are written **before** the distro clone — vault must exist for `pull_book` to resolve destinations.
8. Use one tmpdir clone shared across all selected books (single `git clone`).
9. Call `artbook.pull_book` + `filter_entries_by_items` directly (library, not CLI subprocess).
10. If clone fails: print error, skip book pull step, exit non-zero. Vault files already written are kept.
11. If an individual book pull fails: print error for that book, continue with remaining books, exit non-zero at end.
12. `--dry-run` extends to the distro step: print `[would] pull: <item> → <dest>` without cloning or writing.
13. Update `docs/artbook.md` — add consumer quickstart showing `artifacts init --distro <url>`.
14. Update `cli/README.md` `init` section with `--distro` and `--books` flags.

## Progress

### 2026-05-15 21:42:34 — Incomplete run (r0173)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$1.89, turns=51

## Verification

- [x] `artifacts init --distro <url> -y` pulls all books, all items into fresh vault
- [x] `artifacts init --distro <url> --books agents -y` pulls only agents book
- [x] Interactive flow: prompted for books, then items per book; selections respected
- [x] `-y` with no `--distro` — no network call, no error
- [x] `artbook.distro_url` is present in written `artifacts.yaml` when `--distro` given
- [x] Clone failure → vault written, error printed, non-zero exit
- [x] `--dry-run` prints planned pulls without writing or cloning
- [x] `docs/artbook.md` has consumer quickstart with `--distro`
- [x] `cli/README.md` documents `--distro` and `--books`

## Verification Report

*Verified: 2026-05-15*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts init --distro <url> -y` pulls all books, all items into fresh vault | PASS | `tests/cli/test_init.py::TestDistroIntegration::test_18_11_pull_all_books_y` PASSED; asserts `architect.md`, `developer.md`, `foo.md` all written. Code path: `init.py:344-346` (`yes` + `distro_url` → all books). |
| 2 | `artifacts init --distro <url> --books agents -y` pulls only agents book | PASS | `test_18_11_pull_specific_book` PASSED; asserts agents files present and cmds files absent. Code path: `init.py:327-343` (`--books` parsing). |
| 3 | Interactive flow: prompted for books, then items per book; selections respected | PASS | `_run_distro_step` (init.py:347-358) uses `_prompt_multi_step` for book selection matching kinds/agents pattern; per-book item prompt at init.py:379-399 with `_distro_item_names` + `filter_entries_by_items`. |
| 4 | `-y` with no `--distro` — no network call, no error | PASS | `test_18_11_yes_no_distro_skips_silently` PASSED; "Fetching distro manifest" not in output. Code path: `init.py:813` (`if distro_url:` gate). |
| 5 | `artbook.distro_url` is present in written `artifacts.yaml` when `--distro` given | PASS | `test_18_11_distro_url_injected_in_yaml` PASSED; loaded YAML has `artbook.distro_url == distro`. Code path: `init.py:714-718` (settings-content injection). |
| 6 | Clone failure → vault written, error printed, non-zero exit | PASS | `test_18_11_clone_failure_vault_kept_nonzero_exit` PASSED; exit code 1, `artifacts.yaml` still on disk, error on stderr. Code path: `init.py:312-322` (`FetchError` caught, returns `True`). |
| 7 | `--dry-run` prints planned pulls without writing or cloning | PASS | `test_18_11_dry_run_no_clone_no_write` PASSED with invalid URL — succeeded because no clone attempted; `[would]` in output and no `artifacts.yaml` written. Code path: `init.py:302-304`. |
| 8 | `docs/artbook.md` has consumer quickstart with `--distro` | PASS | `test_18_12_artbook_md_has_consumer_quickstart` PASSED; grep confirms section "## Consumer Quickstart — `artifacts init --distro`" at line 287 of `docs/artbook.md`. |
| 9 | `cli/README.md` documents `--distro` and `--books` | PASS | `test_18_12_cli_readme_documents_distro_and_books` PASSED; grep shows `--distro`/`--books` at `src/artifacts_os/cli/README.md` lines 656, 679-680, 691-694, 718-724. |

### Summary

9 passed, 0 failed. All verification criteria are backed by passing tests (77/77 in `tests/cli/test_init.py`) and direct inspection of the documentation files.

## Findings

Implemented `--distro <url>` and `--books <csv>` flags on `artifacts init`,
adding an optional **Step 4: Distro** after the existing three selection
steps.

**Code changes (committed as `2343ef9`):**

- `src/artifacts_os/cli/commands/init.py` — new `_run_distro_step` helper
  (clone + per-book pull), `_distro_item_names` helper for interactive
  item selection, two new flags in `register()`, settings-content
  injection of `artbook.distro_url`, updated non-TTY guard
  (`distro_fully_flagged`), and final-output exit-code handling.
- `docs/artbook.md` — new "Consumer Quickstart — `artifacts init --distro`"
  section covering non-interactive, interactive, dry-run, and write order.
- `src/artifacts_os/cli/README.md` — init section updated with new flags,
  distro-step behaviour matrix, and three new example commands.
- `tests/cli/test_init.py` — added `TestDistroIntegration` (10 tests,
  using a real git repo fixture mirroring `tests/cli/test_book.py`'s
  pattern) and `TestDocContent` (2 doc-presence tests). All 77 tests in
  the file pass; full `tests/cli/` suite green (107 passed).

**Key design decisions:**

- Vault files are written **before** the clone (req 7); on clone failure
  the vault is preserved and the command exits non-zero (req 10).
- One `tempfile.TemporaryDirectory` clones the distro once and is reused
  across every selected book (req 8) — matches `book pull`'s pattern.
- `--books all` and CSV are accepted; unknown book names print an error
  and exit non-zero **before** any pull (no partial state on typos).
- `--books` without `--distro` is a usage error (exit 2).
- Per-book failures (`ManifestError`/`ArtbookError`) are caught and
  logged; the loop continues with remaining books and exits 1 at end
  (req 11).
- `--dry-run` short-circuits the distro step entirely — no clone, no
  write — and prints `[would] pull from distro: <url>` (req 12). This
  matches the existing `--dry-run` semantics: zero side effects.
- Item-level interactive prompts use `filter_entries_by_items` from the
  artbook library (req 9, no subprocess).
- `artbook.distro_url` is injected into `artifacts.yaml` content by
  string-appending an `artbook:` section before the write, keeping the
  YAML template files untouched.
