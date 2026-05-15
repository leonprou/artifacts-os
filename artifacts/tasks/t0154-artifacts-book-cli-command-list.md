---
kind: task
id: t0154
name: artifacts-book-cli-command-list
type: implementation
status: done
assignee: developer
owner: user
parent: "[[t0150-artbook-distribution-model]]"
depends_on:
  - "[[t0152-itemmeta-base-class-render-table]]"
  - "[[t0153-artbook-module-manifest-fetch-placement]]"
created: 2026-05-15
started: 2026-05-15
completed: 2026-05-15
---

# Artifacts Book Cli Command — List, Show, Pull Verbs

## User story

> **As a** consumer of artifacts-os **I want** `artifacts book list`,
> `artifacts book show <name>`, and `artifacts book pull <name>` to
> work end-to-end **so that** one command pulls agent defaults from
> a configured distro and lands them in `.claude/agents/`.

## Why

This sub-task closes the MVP loop defined in
[[t0150-artbook-distribution-model]]. It wires the `artbook` module
([[t0153-artbook-module-manifest-fetch-placement]]) into the CLI,
reusing the generalised `views.render_table` from
[[t0152-itemmeta-base-class-render-table]] for default output and
`dataclasses.asdict` for `--json`.

## Depends on

- [[t0152-itemmeta-base-class-render-table]] — provides the
  `ItemMeta` base class and the generalised `render_table` signature
  that this CLI command consumes
- [[t0153-artbook-module-manifest-fetch-placement]] — provides
  `read_manifest`, `find_book`, `pull_book`, `destination_for`, and
  `ArtbookSettings`

## Scope (intent — see spec for contract)

- New command file `src/artifacts_os/cli/commands/book.py` wired into
  the existing CLI dispatcher.
- Three verbs under the `book` namespace: `list`, `show <name>`,
  `pull <name>`.
- `--json` flag on all three verbs; `--dry-run` on `pull` only.
- New `ItemMeta` subclasses (`BookRow`, `BookContentRow`,
  `WriteActionRow`) for table rendering — sit next to the command,
  not in `artbook`.
- Default output is a Rich table via `views.render_table` — same
  styling language as `artifacts list` and `artifacts events`.
- Exit-code mapping per spec §5.5 (0 ok / 1 runtime / 2 usage / 3
  no vault / 4 distro URL not configured); error messages follow
  spec §5.6 conventions.
- One tmpdir per CLI invocation — the command owns the
  `TemporaryDirectory` context and passes `clone_root` into both
  `read_manifest` and `pull_book` so list+show+pull from one command
  don't re-clone.
- End-to-end CLI tests that drive the verbs against a fixture
  distro repo (created in `tmp_path` via `git init`).
- Add a `book` section to `docs/cli.md` (or whichever doc covers
  CLI surface) noting it as the precedented exception to flat verbs.

## Out of scope

- Caching, multi-distro, override layer, additional book types — all
  deferred per spec §1.3.
- Dogfood migration of this repo's existing agent copies — deferred.
- `update` / `diff` / `remove` verbs — deferred.

## Progress

### 2026-05-15 09:44:01 — Incomplete run (r0165)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$1.98, turns=51

## Verification

- [x] `artifacts book --help` shows the three verbs
- [x] `artifacts book list` against a fixture distro renders the
      Rich table from spec §5.2 and exits 0
- [x] `artifacts book show agents` renders the per-book detail from
      spec §5.3 (book metadata + contents list)
- [x] `artifacts book pull agents` writes files to
      `<vault>/.claude/agents/` and prints the spec §5.4 summary
- [x] `artifacts book pull agents --dry-run` plans the writes but
      writes nothing; output lines prefixed with `[would]`
- [x] `--json` output for each verb matches spec §5 example shapes
      (single object for list/show; JSONL + summary for pull)
- [x] Exit codes: missing distro URL → 4; vault not found → 3;
      unknown book name → 1; usage error → 2
- [x] Symlinked destination is replaced with a regular file and
      reported (driven by t0153's `WrittenFile.was_symlink`)
- [x] End-to-end test: fresh vault + fixture distro →
      `artifacts book pull agents` → working agents at
      `.claude/agents/*.md` (parent task's headline acceptance)
- [x] `docs/cli.md` (or current CLI doc) describes the `book` verb
      and notes the namespaced exception to flat verbs

## Verification Report

*Verified: 2026-05-15*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts book --help` shows the three verbs | PASS | `book.py` `register()` adds list/show/pull subparsers; `test_book_help_shows_three_verbs` passes |
| 2 | `book list` renders Rich table and exits 0 | PASS | `_run_list` uses `views.render_table` with `BookRow`; `test_book_list_table` passes |
| 3 | `book show agents` renders per-book detail | PASS | `_render_book_show` prints Book/Source/Destination + Contents listing; `test_book_show_table` passes |
| 4 | `book pull agents` writes files and prints summary | PASS | `_run_pull` calls `artbook.pull_book` and prints "Summary: N written"; `test_book_pull_writes_files` passes |
| 5 | `--dry-run` plans only, lines prefixed `[would]` | PASS | `_plan_writes` returns rows without writing; display layer prefixes `[would]`; `test_book_pull_dry_run` passes |
| 6 | `--json` matches spec §5 shapes | PASS | List=single object, Show=single object, Pull=JSONL+summary; `test_book_list_json`, `test_book_show_json`, `test_book_pull_json` all pass |
| 7 | Exit codes 1/2/3/4 mapped correctly | PASS | 4=no distro_url, 3=no vault, 1=unknown book, 2=argparse usage error (verified via direct invocation); covered by no_distro_url/vault_not_found/unknown_name tests |
| 8 | Symlinked destination replaced and reported | PASS | `WriteActionRow.was_symlink` from t0153's `WrittenFile`; action becomes `"overwrite (symlink replaced)"`; `test_book_pull_symlink_replaced` passes |
| 9 | E2E: fresh vault + fixture distro → working agents | PASS | `test_e2e_pull_agents_end_to_end` builds vault+distro, pulls, asserts `.claude/agents/researcher.md` exists with content |
| 10 | CLI doc describes `book` and namespaced exception | PASS | `src/artifacts_os/cli/README.md:899` adds `### book` section with "Namespaced exception to flat verbs" blockquote |

### Summary

10 passed, 0 failed. All verification criteria satisfied; the task is ready for the owner to accept. Full `tests/cli/test_book.py` suite (30 tests) passes.

## References

- [[s0029-artbook-mvp-distribution-model]] §5 (CLI surface)
- [[n0013-artbook-book-command-user-manual]] (terminal sessions for
  each verb)
- Parent: [[t0150-artbook-distribution-model]]

## Findings

Implemented `artifacts book` end-to-end with three sub-verbs (`list`,
`show`, `pull`) wired into the CLI dispatcher. Closed the MVP loop:
`artifacts book pull agents` clones a configured distro, parses
`artbook.yaml`, copies markdown files into `.claude/agents/`, and prints
a Rich-table write summary.

### What was built

- **`src/artifacts_os/cli/commands/book.py`** — new command file with
  three `ItemMeta` subclasses (`BookRow`, `BookContentRow`,
  `WriteActionRow`) and three handlers (`_run_list`, `_run_show`,
  `_run_pull`). One `TemporaryDirectory` per CLI invocation; the clone
  root is passed into `read_manifest` and `pull_book` so no re-clone.
- **`src/artifacts_os/cli/__init__.py`** — registered the `book`
  parser; the verb is marked `_pre_registry=True` so it can own its own
  vault lookup and emit exit codes 3 / 4 distinct from the generic
  dispatcher's exit 2.
- **`tests/cli/test_book.py`** — 19 end-to-end tests against a fixture
  distro repo built with `git init` in `tmp_path`. Covers help,
  list/show/pull happy paths, `--json` shapes, `--dry-run`, overwrite,
  symlink replacement, unknown name, missing distro URL, and
  vault-not-found.
- **`src/artifacts_os/cli/README.md`** — added a `book` section right
  before "Project Configuration" with synopsis, per-verb examples,
  exit-code table, and the namespaced-exception note.

### Design decisions

- **Namespaced verb is the deliberate exception to the flat-verb rule.**
  The CLI README's `book` section calls this out explicitly per the task
  scope item. All other commands stay flat.
- **Settings loaded via raw YAML, not `core.load_settings`.** The base
  `load_settings` requires a `project` section; the book command only
  needs `artbook.distro_url` and should work on partially-configured
  vaults, so it parses `artifacts.yaml` directly into a dict and
  constructs `ArtbookSettings` from that.
- **`WriteActionRow.action` stores the base action (`write` /
  `overwrite`).** The `[would]` prefix for dry-run is added at the
  display layer using `rich.Text` (literal, no markup), and the JSON
  emits the bare action with an explicit `"dry_run": true` on the
  summary line.
- **`ItemMeta` subclasses are non-frozen** because the base
  `ItemMeta` is non-frozen and Python forbids frozen subclasses of
  non-frozen dataclasses. Spec snippet showed `frozen=True` but
  conflicts with the existing class; followed the codebase convention.
- **Symlink replacement is reported in the action column** as
  `write (symlink replaced)` / `overwrite (symlink replaced)`, driven
  by `WrittenFile.was_symlink` from t0153.

### Exit-code mapping (spec §5.5)

| Code | When |
|------|------|
| 0 | success |
| 1 | runtime error — `FetchError`, `ManifestError`, `UnknownBookError`, `UnknownBookTypeError`, any other `ArtbookError` |
| 2 | argparse usage errors (handled by argparse itself) |
| 3 | `find_vault_root()` returned None |
| 4 | `artbook.distro_url` empty / missing |

### Tests

All 19 new tests pass. Four pre-existing failures in
`tests/ai/test_release_changelog_skill.py` are unrelated (verified
via `git stash`); they predate this work.

### Gotchas

- Rich interprets `[…]` in cell strings as markup. The pull verb
  builds its table manually with `rich.Text` objects instead of using
  `views.render_table`, which doesn't escape cell strings. The list
  verb uses `render_table` directly because its cells contain no
  bracketed text.
- `_select_files` from `artbook.placement` is "private" (leading
  underscore) but is imported here for `book show` and `--dry-run`
  enumeration. Promoting it to public API is a candidate follow-up.

## Downstream

- **Promote `artbook.placement._select_files` to public API** — two
  consumers now (`copy_book` internal and the book CLI external).
  Expose as `artbook.list_book_files(book, clone_root)` or add a thin
  wrapper.
- **`render_table` markup escaping** — the generalised `render_table`
  in `views/_views.py` adds cell strings unescaped. Any caller whose
  data may contain `[…]` must escape upstream or build the table
  manually (as `book pull` does). A future revision could pass cell
  values as `rich.Text` by default to make this safe by construction.
