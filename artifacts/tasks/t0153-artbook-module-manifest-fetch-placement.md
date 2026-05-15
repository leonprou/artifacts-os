---
kind: task
id: t0153
name: artbook-module-manifest-fetch-placement
type: implementation
status: done
assignee: developer
owner: user
parent: "[[t0150-artbook-distribution-model]]"
created: 2026-05-15
started: 2026-05-15
completed: 2026-05-15
---

# Artbook Module — Manifest, Fetch, Placement, Pull, Settings, Errors

## User story

> **As a** consumer of artifacts-os **I want** the `artbook` Python
> module to read a distro manifest, fetch its content, and write the
> right files into my project **so that** the `artifacts book` CLI
> verbs have a clean, tested logic layer to call into.

## Why

[[s0029-artbook-mvp-distribution-model]] §4 defines the module as a
pure-logic peer to `core`, `cli`, `views`. Building it independently
of the CLI keeps the contract tight, makes tests fast (no argparse,
no Rich), and lets the CLI sub-task focus purely on UX and rendering.

## Scope (intent — see spec for contract)

- New package `src/artifacts_os/artbook/` with `manifest`, `fetch`,
  `placement`, `pull`, `settings`, `errors` modules (per spec §4.1).
- Public API as listed in spec §4.4: dataclasses `Book`, `Manifest`,
  `WrittenFile`, `PullReport`; functions `read_manifest`, `find_book`,
  `pull_book`, `destination_for`; exception hierarchy rooted at
  `ArtbookError`.
- `ArtbookSettings` extends `core.Settings` via the `from_base`
  pattern; reads `artbook.distro_url` from `artifacts.yaml`.
- Manifest schema v1 (YAML, `version: 1` required), validated before
  any clone or write.
- Shallow git clone (`git clone --depth 1 --branch main --single-branch`)
  via `subprocess.run`; tmpdir lifecycle owned by the caller.
- `agents` book type writes to `<vault>/.claude/agents/` per spec §7.
- Honours `files:` allowlist (D18) when set; falls back to D20 walker
  (`*.md` minus `README.md` minus dotfiles, non-recursive).
- Unlink-then-write atomic copy (D19) — symlinks replaced with regular
  files; tmp file + `os.replace` for atomicity.
- Unit tests against a fixture distro repo created in `tmp_path` via
  `git init` (matches existing test patterns).
- Update `docs/settings.md` to document `artbook.distro_url`.

## Out of scope

- The `artifacts book` CLI command (separate sub-task).
- Rich rendering, `--json` output, exit-code mapping (those live in
  the CLI sub-task).
- Caching, multi-distro, override layer, additional book types — all
  deferred per spec §1.3.

## Verification

- [x] `src/artifacts_os/artbook/` package exists with the modules
      listed above; `__init__.py` re-exports the public API
- [x] All dataclasses match spec §4.3 (field names, types, frozen)
- [x] `read_manifest` validates `version == 1` and rejects mismatch
      with the spec's error message
- [x] `pull_book` honours `files:` allowlist when set, else walks per
      D20 filter
- [x] Symlinked destinations are unlinked before write
      (`WrittenFile.was_symlink == True`)
- [x] `ArtbookSettings.from_base` reads `artbook.distro_url` and
      returns `None` when missing/empty
- [x] `docs/settings.md` documents `artbook.distro_url`
- [x] Unit tests cover: happy path pull, manifest version mismatch,
      unknown book name, unknown book type, missing files in
      allowlist, symlink destination, pre-existing regular file
      (overwrite), missing destination parent directory
- [x] Module dependency rule respected — `artbook` imports only from
      `core` and stdlib + `yaml`; no imports from `views`, `cli`,
      `log`, `tui`, `ai`, `hooks`, `events`

## Verification Report

*Verified: 2026-05-15*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Package exists with all modules; `__init__.py` re-exports public API | PASS | `src/artifacts_os/artbook/` contains `errors.py`, `manifest.py`, `fetch.py`, `placement.py`, `pull.py`, `settings.py`, `__init__.py`. `__init__.py` re-exports all dataclasses, functions, settings, and exceptions per spec §4.4. |
| 2 | All dataclasses match spec §4.3 (field names, types, frozen) | PASS | `Book`, `Manifest`, `WrittenFile`, `PullReport` are all `@dataclass(frozen=True)` with field names/types matching spec §4.3 exactly (verified line-by-line). |
| 3 | `read_manifest` validates `version == 1` with spec error message | PASS | `manifest.py:104-107` checks `version != _REQUIRED_VERSION` and raises `ManifestError("this artifacts-os version speaks artbook manifest v1; distro declares v{version}")` matching spec §3.3 line 217. Test `test_parse_manifest_version_mismatch` confirms. |
| 4 | `pull_book` honours `files:` allowlist; else D20 walker | PASS | `placement.py:_select_files` branches on `book.files is not None`. Tests `test_pull_book_allowlist` and `test_copy_book_d20_excludes_readme` confirm both paths. |
| 5 | Symlinked destinations unlinked before write; `was_symlink == True` | PASS | `placement.py:_atomic_write:104-115` detects `dst.is_symlink()`, unlinks first, then writes via `os.replace`. Test `test_pull_book_symlink_destination` asserts `was_symlink is True` and dest is no longer a symlink. |
| 6 | `ArtbookSettings.from_base` reads `artbook.distro_url`; returns `None` when missing/empty | PASS | `settings.py:34-36` reads `base.raw.get("artbook", {}) or {}` and `raw.get("distro_url") or None`. Tests cover: missing section, empty section, null section, empty-string URL — all return `None`. |
| 7 | `docs/settings.md` documents `artbook.distro_url` | PASS | `docs/settings.md:497-529` contains "Artbook Section" with YAML example, key table, and `from_base` code sample. |
| 8 | Unit tests cover all required scenarios | PASS | All 8 scenarios present and passing: happy-path pull (`test_pull_book_happy_path`), version mismatch (`test_parse_manifest_version_mismatch`), unknown book name (`test_find_book_not_found`), unknown book type (`test_pull_book_unknown_type_raises`), missing allowlist file (`test_pull_book_allowlist_missing_file_raises`), symlink destination (`test_pull_book_symlink_destination`), pre-existing file overwrite (`test_pull_book_overwrites_existing`), missing parent dir (`test_pull_book_creates_missing_parent_directory`). 46/46 tests pass. |
| 9 | Module dependency rule respected | PASS | `grep` of all artbook source files shows only `from artifacts_os.artbook.*` (internal) and `from artifacts_os.core.models import Settings` — no imports from `views`, `cli`, `log`, `tui`, `ai`, `hooks`, `events`. |

### Summary

9 passed, 0 failed. All verification criteria met — task ready for completion.

## References

- [[s0029-artbook-mvp-distribution-model]] §§3, 4, 6, 7
- Parent: [[t0150-artbook-distribution-model]]
- Settings pattern reference: [[s0010-core-settings-module-spec]]

## Findings

Implemented the complete `artbook` module as specified in s0029 §4.

**What was built:**

- `src/artifacts_os/artbook/errors.py` — exception hierarchy: `ArtbookError`, `ManifestError`, `FetchError`, `UnknownBookError`, `UnknownBookTypeError`, `DistroNotConfiguredError`.
- `src/artifacts_os/artbook/manifest.py` — `Book` and `Manifest` frozen dataclasses; `parse_manifest` validates version gate first (D17), then all other fields; `load_manifest` handles file I/O and YAML parse errors.
- `src/artifacts_os/artbook/fetch.py` — `clone()` runs `git clone --depth 1 --branch main --single-branch`; `get_short_sha()` returns the HEAD short SHA; `read_manifest()` is the public entry point combining clone + parse.
- `src/artifacts_os/artbook/placement.py` — `WrittenFile` frozen dataclass; `destination_for()` looks up `_PLACEMENT` dict; `_select_files()` implements D18 allowlist and D20 walker; `_atomic_write()` implements D19 unlink-then-write; `copy_book()` orchestrates the copy.
- `src/artifacts_os/artbook/pull.py` — `PullReport` frozen dataclass; `find_book()` raises `UnknownBookError` with available names; `pull_book()` calls `destination_for` + `copy_book`.
- `src/artifacts_os/artbook/settings.py` — `ArtbookSettings` standalone frozen dataclass (not extending Settings, per spec §4.5) with `from_base` classmethod.
- `src/artifacts_os/artbook/__init__.py` — re-exports full public API.
- `tests/artbook/` — 46 tests covering all required scenarios, all passing.
- `docs/settings.md` — new "Artbook Section" documents `artbook.distro_url`.

**Key design decisions:**
- `ArtbookSettings` is a standalone `@dataclass(frozen=True)` (not subclassing `Settings`), matching the spec §4.5 code exactly.
- The D20 `.md` suffix check uses `.lower()` for case-insensitivity consistency with the README exclusion.
- `read_manifest(distro_url, clone_into=None)` accepts an optional `clone_into` path matching the CLI pseudocode in §5.1.4; if None, creates a tmpdir (caller owns teardown).

## Progress

- 2026-05-15: Implemented all 7 source modules + 46 tests + docs/settings.md update. All tests pass (46/46 new; 944/948 total — 4 pre-existing failures in test_release_changelog_skill.py unrelated to this task).
