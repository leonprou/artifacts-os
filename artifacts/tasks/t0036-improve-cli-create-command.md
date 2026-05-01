---
assignee: developer
id: t0036
kind: task
name: improve-cli-create-command
owner: user
status: verified
type: feature
created: 2026-04-29
started: 2026-04-30
subtasks:
  - "[[t0042-cli-create-kind-aware-help]]"
---

## Goal

Improve the ergonomics and capability of `artifacts create`. Today the
command supports `--kind`, `--body`, and `--fields KEY=VALUE…`, which is
sufficient for simple one-liners but awkward for multi-line bodies,
common frontmatter fields, and structured values (lists, wikilinks).

## Candidate Improvements

Triage and pick the subset to ship. Refine before promoting to ready.

- **Body input from file/stdin.** `--body-file PATH` and/or `--body -`
  to read body from a file or stdin (avoids shell-escaping multi-line
  markdown).
- **Convenience flags for common fields.** `--assignee`, `--owner`,
  `--parent`, `--depends-on`, `--type` so callers do not have to spell
  out `--fields assignee=… owner=…`.
- **Wikilink-aware values.** When a field name expects a wikilink
  (e.g. `parent`, `depends_on`), accept bare names (`t0042`) and wrap
  them automatically — or accept the full `[[…]]` form.
- **List values.** Allow `--fields depends_on=t0001,t0002` (comma-list)
  or repeated `--depends-on t0001 --depends-on t0002`.
- **Name override.** `--name <name>` to override the auto-derived
  `name` (slug). Depends on **t0037** which makes `name` slug-only
  across all kinds. Filename stem stays `{id}-{name}.md` for numbered
  kinds; the override controls the slug portion.
- **Dry run.** `--dry-run` prints the resolved name, kind, frontmatter,
  and body without writing the file.
- **Templates.** `--template <name>` scaffolds a default body
  (e.g. `## Requirements`, `## Verification`) per kind.

## Findings

Shipped all candidate improvements except **templates** (deferred — requires kind-level template definitions not yet designed):

- **`--body-file PATH` / `--body-file -`** — reads body from a file or stdin; mutually exclusive with `--body`
- **Convenience flags** — `--assignee`, `--owner`, `--parent`, `--depends-on`, `--type`; convenience flags take precedence over `--fields` for the same key
- **Wikilink auto-wrap** — `--parent` and `--depends-on` accept bare refs (`t0042`) and wrap them as `[[t0042]]`; already-wrapped values are left unchanged; applies to `parent`/`depends_on` in `--fields` too
- **Comma-list fields** — `--fields tags=a,b,c` produces a YAML list; wikilink wrapping applies when the field is `parent` or `depends_on`
- **`--name SLUG`** — overrides the auto-derived slug; controls the name portion of the filename stem (`{id}-{slug}.md` for numbered kinds)
- **`--dry-run` / `-n`** — prints resolved frontmatter + body via `_frontmatter.dump()` without writing any file; returns exit 0

All 32 tests pass (25 new + 7 existing). One pre-existing failure in `test_pyproject_extras_match_spec` is unrelated to this task.

Updated files: `src/artifacts_os/cli/commands/create.py`, `tests/cli/test_create.py`, `src/artifacts_os/cli/README.md`, `artifacts/specs/s0003-artifacts-os-cli-module.md`.

## Progress

### 2026-04-30 — developer
> time: 00:09

Implemented all candidate improvements except templates: `--body-file`/stdin, `--assignee`/`--owner`/`--parent`/`--depends-on`/`--type` convenience flags, wikilink auto-wrap, comma-list fields, `--name` override, `--dry-run`. 32 tests written and passing. Updated `src/artifacts_os/cli/README.md` and `artifacts/specs/s0003-artifacts-os-cli-module.md`.

### 2026-04-30 — developer

Updated `.openstation/skills/artifacts-os/SKILL.md` `### Create — artifacts create` section: expanded synopsis, added per-flag table, documented wikilink auto-wrap and comma-list semantics, added runnable examples for --body-file, stdin, convenience flags, --dry-run, --name, and comma-list --fields. Fixes the one remaining verification failure.

## Verification

- [x] Spec `artifacts/specs/s0003-artifacts-os-cli-module.md` updated
      with the chosen flags, semantics, and examples
- [x] `src/artifacts_os/cli/commands/create.py` implements the chosen
      improvements
- [x] Tests in `tests/cli/` cover each new flag, including error paths
      (bad field spec, missing file, ambiguous slug)
- [x] `src/artifacts_os/cli/README.md` documents the new flags with
      runnable examples
- [x] `docs/` and the `artifacts-cli` skill reference stay in sync if
      user-facing behavior changes

## Verification Report

*Verified: 2026-04-30*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec `s0003-artifacts-os-cli-module.md` updated with chosen flags/semantics/examples | PASS | `create` row in command table lists `--body-file`, `--name`, `--assignee`, `--owner`, `--parent`, `--depends-on`, `--type`, `--fields`, `--dry-run`; dedicated `### create flags` table + "Wikilink convention" note (s0003 lines 45, 50–67) |
| 2 | `src/artifacts_os/cli/commands/create.py` implements chosen improvements | PASS | `register()` adds mutually-exclusive `--body`/`--body-file`, plus `--assignee`/`--owner`/`--parent`/`--depends-on`/`--type`/`--name`/`--dry-run`; `_parse_fields` handles comma-lists with wikilink wrapping; `_read_body` supports `-`/stdin and missing-file error; `_print_dry_run` previews via `_frontmatter.dump` (create.py lines 13–193) |
| 3 | Tests cover each new flag including error paths | PASS | `tests/cli/test_create.py` has 37 passing tests covering body-file/stdin/missing-file/mutex, all convenience flags, parent + depends-on wrapping (single/repeated/already-wrapped), `--fields` comma-list and bad-spec error, `--name` override on numbered/non-numbered + bad-slug error, and dry-run for slug/fields/body/name (`pytest tests/cli/test_create.py` → 37 passed) |
| 4 | `src/artifacts_os/cli/README.md` documents new flags with runnable examples | PASS | `### create — Add a new artifact` synopsis lists every new flag; per-flag table at lines 162–175; "Wikilink auto-wrapping" + "Comma-list values" notes; runnable examples for `--body-file`, stdin, `--name`, `--dry-run`, repeated `--depends-on`, comma-list `--fields depends_on=t0001,t0002` (README.md lines 145–223) |
| 5 | `docs/` and the `artifacts-cli` skill reference stay in sync with user-facing behavior changes | PASS | `.openstation/skills/artifacts-os/SKILL.md` `### Create — artifacts create` section now shows the expanded synopsis with `--body-file`, `--name`, `--dry-run`, `--assignee`, `--owner`, `--parent`, `--depends-on`, `--type` (lines 84–92); per-flag table (lines 94–106); "Wikilink auto-wrap" and "Comma-list values" notes (lines 108–114); runnable examples for body-file, stdin, dry-run, `--name`, comma-list `--fields` (lines 116–146) |

### Summary

5 passed, 0 failed. All verification criteria pass — the task is
ready to be marked verified.