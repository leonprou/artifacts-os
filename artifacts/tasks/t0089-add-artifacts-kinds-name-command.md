---
assignee: developer
created: 2026-05-03
id: t0089
kind: task
name: add-artifacts-kinds-name-command
owner: user
started: 2026-05-03
status: done
type: implementation
---

# Add Artifacts Kinds <Name> Command For Per-Kind Detail

## Requirements

- **R1 — `artifacts kinds <name>` resolves a single kind.** Extend
  the existing `artifacts kinds` command to accept an optional
  positional `<name>` argument. When provided, output detail for
  that one kind instead of the listing.
- **R2 — Default output: the full `ARTIFACT.md` body.** When
  `<name>` is given without other flags, print the full contents of
  `artifacts/kinds/<name>/ARTIFACT.md` to stdout (markdown,
  pipe-friendly, no decoration).
- **R3 — `--meta` flag adds kind metadata.** When `--meta` is
  passed alongside `<name>`, prepend a metadata block above the
  body containing: `name`, `dir`, `prefix`, `numbered`, `statuses`,
  `description` (the same fields the listing shows). Format: small
  YAML-like block or a compact table — implementer's call, but it
  must be visually distinct from the markdown body. `--meta`
  requires `<name>` (using it without a name is a usage error;
  this rules out the alternative interpretation rejected during
  the draft round).
- **R4 — `-j` (JSON) output.** When `-j` is passed alongside
  `<name>`, emit a JSON object with keys `meta` (the metadata
  fields above) and `body` (the raw `ARTIFACT.md` content as a
  string). `--meta` and `-j` together: `-j` wins (JSON output
  always includes meta, so `--meta` is redundant but not an
  error).
- **R5 — Unknown kind: clear error, non-zero exit.** If `<name>`
  doesn't match a registered kind, print an error to stderr
  listing the available kinds and exit non-zero. Match the
  resolution-failure pattern used elsewhere in the CLI (e.g.
  `artifacts show`).
- **R6 — Missing `ARTIFACT.md`: graceful handling.** If the kind
  exists but `artifacts/kinds/<name>/ARTIFACT.md` is missing,
  print a clear message ("no `ARTIFACT.md` defined for kind
  `<name>`") to stderr and exit non-zero in the default text
  mode. With `-j`, return `{"meta": {...}, "body": null}` and
  exit 0 — JSON consumers can branch on the null.
- **R7 — Documentation.** Update `--help` for `artifacts kinds`
  to describe the new positional argument and the `--meta` /
  `-j` flags. If `docs/cli.md` (or any other doc that documents
  the command) exists, update it too.

## Verification

- [x] `artifacts kinds task` prints the full body of
      `artifacts/kinds/task/ARTIFACT.md` to stdout, byte-for-byte.
- [x] `artifacts kinds spec --meta` prints the metadata block
      followed by the full `ARTIFACT.md` body.
- [x] `artifacts kinds task -j | jq -r .body` round-trips the
      `ARTIFACT.md` content unchanged; `jq .meta.prefix` returns
      `"t"`.
- [x] `artifacts kinds nonexistent` exits non-zero, prints an
      error to stderr listing available kinds.
- [x] A kind directory without `ARTIFACT.md` (constructed in a
      test fixture) produces a clear stderr message in default
      mode and `{"body": null}` in `-j` mode.
- [x] `artifacts kinds --help` documents `<name>`, `--meta`, and
      `-j`.
- [x] `artifacts kinds` with no argument still produces the
      existing listing (regression).
- [x] `artifacts kinds --meta` (no name) is rejected as a usage
      error.
- [x] New tests in `tests/cli/` cover all the above paths.

## Verification Report

*Verified: 2026-05-04*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts kinds task` prints body byte-for-byte | PASS | `diff <(artifacts kinds task) artifacts/kinds/task/ARTIFACT.md` produced no output; test_kinds_name_prints_body + test_kinds_name_body_exact_roundtrip pass |
| 2 | `artifacts kinds spec --meta` prepends metadata block | PASS | Live invocation shows `---`-delimited block with name/dir/prefix/numbered/statuses/description, then full body; test_kinds_name_meta_flag + test_kinds_name_meta_block_visually_distinct pass |
| 3 | `kinds task -j` round-trips body, prefix == `"t"` | PASS | Python json roundtrip confirmed `body matches: True` and `prefix: 't'`; test_kinds_name_json_output + test_kinds_name_json_body_roundtrip pass |
| 4 | `artifacts kinds nonexistent` exits non-zero, lists available kinds | PASS | Live invocation: `error: unknown kind 'nonexistent'. Available kinds: agent, note, research, spec, task` on stderr, exit 3; test_kinds_nonexistent_* pass |
| 5 | Missing `ARTIFACT.md`: stderr in text mode, `{"body": null}` in `-j` mode | PASS | test_kinds_missing_artifact_md_text_error (exit non-zero + stderr) and test_kinds_missing_artifact_md_json_body_null (exit 0 + `body: null`) pass |
| 6 | `--help` documents `<name>`, `--meta`, `-j` | PASS | Help output includes `<name>` positional, `--meta`, `-j/--json` (and `-e/--editor`); test_kinds_help_documents_name_meta_j passes |
| 7 | Listing without `<name>` still works (regression) | PASS | `artifacts kinds` renders the rich table with all four kinds; test_kinds_listing_regression + test_kinds_listing_table_regression + test_kinds_listing_json_regression pass; baseline test_kinds.py (11 tests) all pass |
| 8 | `artifacts kinds --meta` (no name) is a usage error | PASS | Live invocation: `error: --meta requires <name>`, exit 2; test_kinds_name_meta_requires_name passes |
| 9 | New tests cover all paths in `tests/cli/` | PASS | `tests/cli/test_kinds_name_command.py` adds 25 tests (17 core + 8 editor-flag); full suite passes in 0.56s |

### Summary

9 passed, 0 failed. All verification criteria pass with concrete evidence — implementation in `src/artifacts_os/cli/commands/kinds.py`, docs updated in `src/artifacts_os/cli/README.md`, and 25 new tests covering all paths.

## Origin

Surfaced as the `kinds <name>` affordance gap during the
2026-05-03 session that produced
`[[s0019-artifacts-os-public-api]]`. The architect agent tried
`artifacts kinds spec` and the CLI rejected it
(`unrecognized arguments: spec`), forcing a fallback to direct
file reads. Captured as Finding 7 / Q5 in
`[[n0007-artifact-creation-case-s0019-via]]`.

## References

- [[n0007-artifact-creation-case-s0019-via]] — Finding 7 / Q5
  flagged this gap
- [[n0006-artifact-creation-cases-r0004-vs]] — parent analysis
  framework
- `src/artifacts_os/cli/commands/` — where the `kinds`
  subcommand lives today
- `artifacts/kinds/<name>/ARTIFACT.md` — the per-kind template
  files this command will surface

## Findings

Extended `src/artifacts_os/cli/commands/kinds.py` with:
- Optional positional `<name>` arg (`nargs='?'`) routing to `_run_single()`
- `--meta` flag (requires `<name>`; usage error otherwise)
- Detail modes: plain body (default), metadata block + body (`--meta`), JSON
  `{"meta": {...}, "body": "..."|null}` (`-j`)
- Unknown kind: exit 3, stderr error listing available kinds
- Missing `ARTIFACT.md`: exit 3 + stderr in text mode; `body: null` + exit 0
  in `-j` mode (JSON consumers can branch on null)

Updated `src/artifacts_os/cli/README.md` §`kinds` to document `<name>`,
`--meta`, `-j`, exit codes, and new examples.

Added 17 tests in `tests/cli/test_kinds_name_command.py` covering all 9
verification checklist items. All 290 pre-existing (non-editor) tests pass;
2 pre-existing editor-open failures in `test_settings.py` are unrelated.

### Update — `-e` (editor) flag

Follow-up addition: `artifacts kinds <name> -e` opens
`artifacts/kinds/<name>/ARTIFACT.md` in `$EDITOR` (falls back to `vi`).
Mirrors `show -e` semantics: `os.execvp` so the editor inherits the
terminal cleanly; silently downgrades to default text output when
stdout is not a TTY (avoids hangs in pipes/CI). Added to the same
mutex group as `-q` / `-j`. Eight new tests cover invocation,
`$EDITOR` fallback, non-TTY downgrade, missing `ARTIFACT.md` handling,
mutex with `-q`/`-j`, usage error without `<name>`, and `--help`
mention.