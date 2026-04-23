---
kind: task
id: t0006
name: write-readme-for-cli-module
type: documentation
status: done
assignee: author
owner: user
created: 2026-04-22
started: 2026-04-23
completed: 2026-04-23
---

# Write Readme For Cli Module

## Requirements

Write `src/artifacts_os/cli/README.md` documenting the `cli` module.

### Source material

- `src/artifacts_os/cli/` — implemented source code (primary)
- `artifacts/specs/s0003-artifacts-os-cli-module.md` — spec reference
- `pyproject.toml` — entry point definition
- `tests/cli/` — usage examples

### Content outline

1. **Purpose** — argument parsing and command dispatch; the user-facing entry point
2. **Install & invoke** — `pip install artifacts-os`, then `artifacts --help`
3. **Commands** — one subsection per implemented command with synopsis and example:
   - `list [--kind KIND] [--status S] [--fields F] [-q|-j]`
   - `show <ref> [--kind KIND] [-j|-e]`
   - `create <title> [--kind KIND] [--body B] [--fields F]`
   - `status <ref> <new-status>`
   - `verify [<ref>] [--kind KIND] [--all] [-j]`
   - `agents [--show <name>] [-q|-j|-e]`
4. **Output modes** — default rich table, `-q` one-per-line, `-j` JSON; `--view` not yet implemented
5. **`register_kinds` hook** — how host apps inject `KindDef` objects before dispatch
6. **Exit codes** — table mapping exceptions to codes (1–4)
7. **Constraint** — no lifecycle logic in `cli`; status transitions go through `core.update`
8. **Dependency** — sits above `views`

### Constraints

- Document actual implemented commands — read the source, not just the spec
- Each command section must include a real invocation example

## Verification

- [x] `src/artifacts_os/cli/README.md` exists
- [x] All six commands documented with synopsis and example
- [x] Exit code table present and matches implementation
- [x] `--view` noted as not yet implemented
- [x] `register_kinds` hook documented
- [x] No-lifecycle constraint mentioned

## Verification Report

*Verified: 2026-04-23*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `src/artifacts_os/cli/README.md` exists | PASS | File present and readable at `src/artifacts_os/cli/README.md` |
| 2 | All six commands documented with synopsis and example | PASS | `list`, `show`, `create`, `status`, `verify`, `agents` — each has a synopsis block and `**Examples:**` section |
| 3 | Exit code table present and matches implementation | PASS | README table (0–4) matches `_run()` in `cli/__init__.py`: `ValueError`→1, `ValidationError`→2, `NotFoundError`→3, `AmbiguousError`→4, no-vault→2 |
| 4 | `--view` noted as not yet implemented | PASS | Output Modes section contains `> **Note:** \`--view\` is not yet implemented.` |
| 5 | `register_kinds` hook documented | PASS | Dedicated `## \`register_kinds\` Hook` section with concrete `KindDef` example |
| 6 | No-lifecycle constraint mentioned | PASS | Purpose line and `## Constraint` section both state no lifecycle logic in `cli` |

### Summary

6 passed, 0 failed. All verification criteria met.

## Progress

### 2026-04-23 — author
> time: 08:38

Wrote src/artifacts_os/cli/README.md; all six commands documented with synopsis, examples, exit codes, register_kinds hook, and no-lifecycle constraint.

## Findings

Created `src/artifacts_os/cli/README.md` documenting the full CLI module based on reading the implemented source.

All six commands documented with synopsis tables and working examples (drawn from `tests/cli/`):
- `list` — filters, field specs, quiet/JSON modes
- `show` — partial ref resolution, editor mode
- `create` — title-to-slug, kind override, `KEY=VALUE` fields
- `status` — delegates to `core.update`; no lifecycle logic
- `verify` — checklist parsing, exit 0/1 semantics, `--all` mode
- `agents` — shorthand list/show for agent kind

Exit code table maps all four exception types (`ValueError`→1, `ValidationError`→2, `NotFoundError`→3, `AmbiguousError`→4) plus the "not in project" case (→2).

`register_kinds` documented with a concrete `KindDef` example showing how host apps extend the registry before calling `main()`.

`--view` noted as not yet implemented in the Output Modes section.

## Downstream

- **Split `verify` vs `validate` semantics** — `artifacts verify` (this CLI) checks task *completeness* via markdown checklists; `openstation verify` checks artifact *structural correctness* via JSON schema. These are orthogonal concerns that should have separate commands:
  - **Keep `artifacts verify`** — task-completeness gate (checklist ticked → ready for `done`). Correctly named.
  - **Add `artifacts validate`** — port `openstation verify`'s schema-linting logic (with `--fix` / `--dry-run`) into the new CLI under the correct name. Operates on frontmatter, not body checklists.
  - Follow-up task: reimplement `openstation verify` as `artifacts validate` in the `artifacts_os.cli` module.
- **`create` has no pre-flight validation surface** — the README's Validation table documents the schema/slug/kind checks inside `core.create`, but there's no way to dry-run a create (e.g. `artifacts create --dry-run`) to check inputs without writing to disk. Once `artifacts validate` exists, it could accept `--stdin` or similar to validate prospective frontmatter before creation.
