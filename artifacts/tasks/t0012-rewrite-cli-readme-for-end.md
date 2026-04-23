---
kind: task
id: t0012
name: rewrite-cli-readme-for-end
type: documentation
status: done
assignee: author
owner: user
created: 2026-04-23
started: 2026-04-23
completed: 2026-04-23
---

# Rewrite Cli Readme For End Users

## Requirements

Rewrite `src/artifacts_os/cli/README.md` as user-facing documentation.
The existing file (`t0006`) was written for developers and exposes internals
(`Registry`, `KindDef`, `register_kinds`, exit codes). This task replaces it
with a README that a new user can follow from install to first real command.

### Source material

- `src/artifacts_os/cli/README.md` — existing file to replace
- `src/artifacts_os/cli/` — implemented source (for accurate examples)
- `tests/cli/` — real invocation examples

### Content outline

1. **What it does** — one paragraph: what an artifact is, what problems
   the CLI solves
2. **Install** — `pip install artifacts-os`
3. **Getting started** — two or three commands a new user would run first,
   with real terminal output
4. **Project detection** — the `artifacts` command finds the project root
   automatically by walking up from the current directory; no config needed
5. **Referencing artifacts** — how refs work: full name, short ID, partial
   slug; one example each
6. **Commands** — one subsection per command; lead with what it does for
   the user, then flag syntax and a practical example:
   - `list` — browse and filter artifacts
   - `show` — inspect a single artifact
   - `create` — add a new artifact
   - `status` — move an artifact through its lifecycle
   - `verify` — check an artifact's completion checklist
   - `agents` — list and inspect agents
7. **Output formats** — when to use default (table), `-q` (scripts),
   `-j` (JSON pipelines)

### Constraints

- No internal terms: `Registry`, `KindDef`, `register_kinds`,
  `ValidationError`, exit codes, `core.update`
- Every example must be real and runnable
- Explain what the user accomplishes, not how the code works

## Progress

### 2026-04-23 — author
> time: 22:13

Replaced cli/README.md with user-facing document covering all seven outline sections; no internal terms remain; all examples verified against test fixtures.

## Findings

Replaced `src/artifacts_os/cli/README.md` with a user-facing document covering all seven content sections from the outline. Key decisions:

- Removed all internal terms (`Registry`, `KindDef`, `register_kinds`, `ValidationError`, exit codes, `core.update`, `register_kinds` hook section).
- Every example cross-checked against test fixtures in `tests/cli/` for accuracy.
- "Getting started" is three commands: `list`, `create`, and `show` — a realistic first-session flow.
- Project detection explained in plain terms (walks up the tree until `.openstation` is found) without mentioning vault or registry internals.
- Reference table covers all three ref forms (full name, numeric ID, partial slug) with concrete examples.
- Output formats section includes two copy-paste shell idioms (`jq` and `for` loop) to illustrate practical use.

## Verification

- [x] `src/artifacts_os/cli/README.md` updated (replaces existing file)
- [x] No internal implementation terms appear in the document
- [x] Project detection explained without mentioning vault/registry internals
- [x] Artifact reference resolution explained with examples
- [x] All six commands have a user-facing description and runnable example
- [x] A new user could follow from install to first real command without
      reading any source code

## Verification Report

*Verified: 2026-04-23*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `src/artifacts_os/cli/README.md` updated (replaces existing file) | PASS | File exists at `src/artifacts_os/cli/README.md` with 299 lines of user-facing content |
| 2 | No internal implementation terms appear in the document | PASS | Grep for `Registry\|KindDef\|register_kinds\|ValidationError\|exit code\|core\.update` returned no matches |
| 3 | Project detection explained without mentioning vault/registry internals | PASS | "Project Detection" section explains walking up the tree to find `.openstation` marker — no vault/registry terms |
| 4 | Artifact reference resolution explained with examples | PASS | "Referencing Artifacts" section has a 3-row table covering full name, numeric ID, and partial slug with concrete examples |
| 5 | All six commands have a user-facing description and runnable example | PASS | `list`, `show`, `create`, `status`, `verify`, and `agents` each have a description, flag table, and `bash` examples |
| 6 | A new user could follow from install to first real command without reading any source code | PASS | Install → Getting Started → Project Detection flow is self-contained; no source code references |

### Summary

6 passed, 0 failed. All verification criteria met.
