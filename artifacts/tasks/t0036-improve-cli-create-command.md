---
assignee: developer
id: t0036
kind: task
name: improve-cli-create-command
owner: user
status: backlog
type: feature
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

## Verification

- [ ] Spec `artifacts/specs/s0003-artifacts-os-cli-module.md` updated
      with the chosen flags, semantics, and examples
- [ ] `src/artifacts_os/cli/commands/create.py` implements the chosen
      improvements
- [ ] Tests in `tests/cli/` cover each new flag, including error paths
      (bad field spec, missing file, ambiguous slug)
- [ ] `src/artifacts_os/cli/README.md` documents the new flags with
      runnable examples
- [ ] `docs/` and the `artifacts-cli` skill reference stay in sync if
      user-facing behavior changes