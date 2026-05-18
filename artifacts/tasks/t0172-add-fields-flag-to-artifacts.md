---
assignee: developer
created: 2026-05-17
id: t0172
kind: task
name: add-fields-flag-to-artifacts
owner: user
status: ready
type: implementation
---

## User story

> **As an** operator (or agent) extracting one or more frontmatter fields from a known artifact
> **I want** `artifacts show <ref> --fields f1,f2,f3` to project just those fields — with the same `-q` / `-j` output mode semantics that `list --fields` already has —
> **so that** I can stop piping `-j` output through `jq`/`python` for single-field lookups and write clean shell substitutions like `$(artifacts show t0042 --fields status -q)`.

## Why

`artifacts list --fields …` is already supported for multi-record queries. `show` — the single-record cousin — has only two modes: the full pretty render (default) and full JSON (`-j`). Extracting a single field from a known artifact requires a `jq` or Python dance for every lookup, which was a real friction multiple times in this session (e.g. checking whether a spec was `draft` or `verified`).

Closing the asymmetry between `list --fields` and `show --fields` is purely additive; no existing command line breaks.

## Directions (intent, not contract)

- Add `--fields F1,F2,…` (alias `-f`) to `artifacts show`, accepting the same comma-list parser as `list --fields`.
- **Default output** — render a two-column `field` / `value` table for the requested fields. Visual consistency with `views show`-style key/value tables.
- **`-q` output** — one value per line, no labels. Single-field + `-q` is the killer combination for shell substitution.
- **`-j` output** — a JSON object containing only the requested keys (not wrapped in an array).
- **Array fields** (`depends_on`, `subtasks`, `artifacts`) under `-q` — comma-join the items on one line. (Keeps `-q`'s "one value per requested field, one line" promise.)
- **`body`** is a valid field name. Under `-q` it dumps the full body.
- **Unknown field name** — exit 2 with `error: unknown field '<name>'; available: <list of frontmatter keys>`. Fail fast; do not silently emit empty.
- **`-e` (editor)** is unchanged — opens the file; `--fields` is ignored when `-e` is set (consistent with how `-e` already overrides other output flags).

## Out of scope

- No new field-extraction syntax (no jq-style paths, no glob field names). Same comma-list `list` already accepts.
- No mutation of the artifact (`show` stays read-only).
- No deduplication of `--fields` with `-j` 's default "emit everything" behaviour — passing `-j` *without* `--fields` keeps emitting the full object.

## Verification

- [ ] `artifacts show t0042 --fields id,status,assignee` renders a two-column field/value table with the three rows.
- [ ] `artifacts show t0042 --fields status -q` prints exactly one line: the status value.
- [ ] `artifacts show t0042 --fields id,status,assignee -q` prints three lines, one per field, in the order requested.
- [ ] `artifacts show t0042 --fields id,status -j` emits `{"id": "…", "status": "…"}` (no array wrapping, only the requested keys).
- [ ] Array-typed fields under `-q` comma-join their items on one line.
- [ ] `artifacts show t0042 --fields body -q` dumps the full body to stdout.
- [ ] `artifacts show t0042 --fields nonexistent` exits 2 with `error: unknown field 'nonexistent'; available: …`.
- [ ] `artifacts show t0042 -e --fields status` opens the file in `$EDITOR` (the `--fields` flag is ignored when `-e` is set; documented).
- [ ] Test coverage in `tests/cli/test_show.py` for the three output modes and the unknown-field error.
- [ ] `src/artifacts_os/cli/README.md` `show` section adds the `--fields` row and one example per output mode.
- [ ] No regression in existing `show` behaviour (default render and `-j` without `--fields` unchanged).

## References

- [[n0015-artbook-promotion-mechanism-design-brainstorm]] — session that surfaced this and related ergonomics gaps.
- `src/artifacts_os/cli/commands/show.py` — current `show` command surface.
- `src/artifacts_os/cli/commands/list.py` — reference implementation for `--fields` semantics.
- `src/artifacts_os/cli/README.md` § `show` — flag table + examples to update.