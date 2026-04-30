---
assignee: author
created: 2026-04-30
id: t0043
kind: task
name: author-browse-and-inspect-claude
owner: user
parent: '[[t0041-ai-claude-commands-support]]'
status: done
type: implementation
started: 2026-04-30
completed: 2026-04-30
---

## Scope

Author the 3 markdown command files in the **Browse & Inspect** category from `t0041`'s surface definition. Pure prompt/content deliverables — no Python, no install machinery (those land in a separate developer subtask).

| Command | File | Maps to |
|---|---|---|
| `/artifacts.list` | `artifacts.list.md` | `artifacts list` |
| `/artifacts.show` | `artifacts.show.md` | `artifacts show` |
| `/artifacts.kinds` | `artifacts.kinds.md` | `artifacts kinds` |

All three files land at: `src/artifacts_os/ai/claude/commands/`

## Requirements

1. Create the directory `src/artifacts_os/ai/claude/commands/` (and parents `src/artifacts_os/ai/`, `src/artifacts_os/ai/claude/` as needed) with `__init__.py` placeholders so the path is importable as package data via `importlib.resources`.
2. Author `src/artifacts_os/ai/claude/commands/artifacts.list.md`:
   - Frontmatter: `description`, `name`, plus conventions matching `.openstation/commands/openstation.list.md`.
   - Procedure walks Claude through invoking `artifacts list` with appropriate flags (`--kind`, `--status`, `--fields`, `-q`, `-j`).
   - Cover common patterns (filter by kind, filter by status, scripting/JSON output).
   - Document edge cases (empty vault, unknown kind, ambiguous fields).
3. Author `src/artifacts_os/ai/claude/commands/artifacts.show.md`:
   - Procedure covers `<ref>` resolution (full name, numeric ID, partial slug) and the three output modes (default table, `-j`, `-e` editor).
   - Document `--kind` for disambiguating partial-slug refs.
4. Author `src/artifacts_os/ai/claude/commands/artifacts.kinds.md`:
   - Procedure covers listing all registered kinds, with `-q` and `-j` modes.
   - Brief note on kind registration (points to `/artifacts.kinds.create` once that lands).
5. Each file follows the structure of existing `.openstation/commands/openstation.*.md` references — frontmatter + `## Procedure` + examples.
6. Files are **kind-agnostic** — no hardcoded `note`, `spec`, `task` references that assume a specific vault's registry.
7. No **lifecycle terminology** — these are read-only browse/inspect commands; words like `ready`, `progress`, `done`, `verify`, `transition` belong to `/openstation.*` and must not appear.
8. Cross-link the three files where helpful (e.g., `show` mentions `list` for discovering refs; `kinds` mentions `list --kind <K>`).

## Verification

- [x] `src/artifacts_os/ai/claude/commands/artifacts.list.md` exists with valid frontmatter and a `## Procedure` section.
- [x] `src/artifacts_os/ai/claude/commands/artifacts.show.md` exists with valid frontmatter and a `## Procedure` section.
- [x] `src/artifacts_os/ai/claude/commands/artifacts.kinds.md` exists with valid frontmatter and a `## Procedure` section.
- [x] Each file documents the underlying CLI invocation, inputs, and at least one worked example.
- [x] No lifecycle terminology (`ready`, `progress`, `done`, `verify`, `suspend`, `fail`, `reject`, `transition`) appears in any of the three files.
- [x] No vault-specific kind names hardcoded (no assumed `note`/`spec`/`task` semantics — references to kind names appear only as illustrative examples or pulled from the registry at runtime).
- [x] Directory structure `src/artifacts_os/ai/claude/commands/` exists; can be loaded via `importlib.resources.files("artifacts_os.ai.claude.commands")` (verifiable by a one-liner — no test code required for this subtask).
- [x] Files reviewed by `architect` for boundary correctness against `t0041`'s design before the subtask closes.

## Verification Report

*Verified: 2026-04-30*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts.list.md` exists with valid frontmatter + `## Procedure` | PASS | File present (3609 bytes); frontmatter has `name`/`description`; `## Procedure` at line 27. |
| 2 | `artifacts.show.md` exists with valid frontmatter + `## Procedure` | PASS | File present (3723 bytes); frontmatter has `name`/`description`; `## Procedure` at line 30. |
| 3 | `artifacts.kinds.md` exists with valid frontmatter + `## Procedure` | PASS | File present (2848 bytes); frontmatter has `name`/`description`; `## Procedure` at line 24. |
| 4 | Each file documents CLI invocation, inputs, and at least one worked example | PASS | All three files include an `## Input` table, `## Procedure` with literal `artifacts <subcmd>` invocations, and `## Worked example(s)` sections. |
| 5 | No lifecycle terminology in any file | PASS | `grep -iE '\b(ready\|progress\|done\|verify\|verification\|suspend\|fail\|reject\|transition)\b'` returns zero matches. (`rejects`/`rejected` appear only in CLI-input-validation prose, not as lifecycle verbs — architect-review confirmed.) |
| 6 | No hardcoded kind names | PASS | All kind references use `<KIND>`/`<K>` placeholders; only illustrative example is `t0042-fix-login-bug` carried from CLI README. Architect-review confirmed kind-agnostic phrasing. |
| 7 | Package importable via `importlib.resources` | PASS | `importlib.resources.files("artifacts_os.ai.claude.commands").iterdir()` returned all three `.md` files plus `__init__.py`. |
| 8 | Reviewed by `architect` for boundary correctness vs. `t0041` | PASS | `architect-review` agent returned PASS on all five boundary criteria (surface separation, kind-agnostic, read-only scope, structural fidelity, cross-reference completeness). |

### Summary

8 passed, 0 failed. All verification criteria satisfied — task ready to be marked verified and promoted to done.

## Reference material

- `t0041-ai-claude-commands-support` — full design context including surface tables, package layout, conflict policy.
- `src/artifacts_os/cli/README.md` — current `artifacts list` / `show` / `kinds` flag reference.
- `.openstation/commands/openstation.list.md` and `openstation.show.md` — structural prior art.

## Progress

### 2026-04-30 — author
> time: 21:25–21:28

Authored the three Browse & Inspect command prompts
(`artifacts.list.md`, `artifacts.show.md`, `artifacts.kinds.md`) under
`src/artifacts_os/ai/claude/commands/` plus `__init__.py` placeholders
in `ai/claude/` and `ai/claude/commands/`. Verified with
`importlib.resources.files("artifacts_os.ai.claude.commands").iterdir()`
that the package data loads. Lifecycle-vocabulary scan
(`ready|progress|done|verify|verification|suspend|fail|reject|transition`)
returns zero matches across the three files. YAML frontmatter parses
and each file contains a `## Procedure` section. Transitioning the
task to `review` for the owner.

## Findings

Authored the three Browse & Inspect command prompts and the package
plumbing needed to ship them as wheel data:

- `src/artifacts_os/ai/claude/__init__.py` — new sub-package marker.
- `src/artifacts_os/ai/claude/commands/__init__.py` — new sub-package marker.
- `src/artifacts_os/ai/claude/commands/artifacts.list.md`
- `src/artifacts_os/ai/claude/commands/artifacts.show.md`
- `src/artifacts_os/ai/claude/commands/artifacts.kinds.md`

**Structure mirrors `.openstation/commands/openstation.*.md`** — YAML
frontmatter with `name` + `description`, followed by `# <Title>`, an
`## Input` section explaining `$ARGUMENTS`, a `## Procedure` block with
the literal `artifacts <subcommand>` invocation, the standard
"Run the command exactly as shown" guard, a flag/mode reference
table, at least one worked example, and an edge-cases table.

**Kind-agnostic phrasing** — argument tokens use `<KIND>`, `<STATUS>`,
`<ref>` placeholders. The only kind-name occurrences are inside
illustrative ref slugs (e.g., `t0042-fix-login-bug`) carried over from
the CLI README; nothing in the prompts assumes a specific kind is
registered. Each prompt explicitly tells Claude to call
`/artifacts.kinds` first when a user has not specified a kind.

**No lifecycle terminology** — verified via
`grep -iE '\b(ready|progress|done|verify|verification|suspend|fail|reject|transition)\b'`
which returns zero matches across the three files.

**Cross-links** —
- `list.md` → `show.md` (for inspecting a row) and `kinds.md` (for
  filter discovery).
- `show.md` → `list.md` (for ref discovery) and `kinds.md` (for
  `--kind` disambiguation).
- `kinds.md` → `list.md --kind <KIND>` (next-step discovery) and
  `show.md` (single-artifact inspection); also points forward to
  `/artifacts.kinds.create` for registration (per requirement 4).

**Package importability** — the prompts load cleanly via
`importlib.resources.files("artifacts_os.ai.claude.commands")` and
iterate as expected (verified with a one-liner; no test code added,
matching the subtask's scope).

### Design decisions

- **Used both `key:value` tokens and CLI flag aliases.** The
  `$ARGUMENTS` table maps user-typed `kind:foo` shorthand to the
  underlying `--kind foo` flag, mirroring the pattern in
  `openstation.list.md`. Both forms are documented so Claude can
  translate either way.
- **Explicit "do not modify the command" guard.** Copied verbatim
  from the openstation prompts because Claude has historically tried
  to add `2>/dev/null` or `|| echo` decoration to bash invocations.
- **`-q` vs `-j` mutual-exclusion called out explicitly** in the edge
  cases — the CLI raises if both are passed and Claude needs to pick
  one based on intent.
- **`-e` + missing `$EDITOR`** is surfaced in `show.md`'s edge cases
  with concrete remediation (`export EDITOR=vim`) rather than a
  generic "ask the user" — keeps the prompt self-sufficient.

### Out of scope (handled by sibling subtasks under `t0041`)

- The other six commands (`create`, `kinds.create`, `kinds.edit`,
  `validate`, `verify`, `init`) — separate authoring subtasks.
- The install module (`ai/install.py`), CLI subcommands
  (`artifacts ai install/uninstall/list`), and `artifacts init`
  integration — developer subtask.
- The `artifacts-os` skill at
  `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` — also
  out of this subtask's scope.
- Wheel-target verification that `*.md` files are bundled correctly —
  developer subtask.

## Downstream

- `architect` review (per the verification checklist) — owner should
  schedule before promoting through `t0041`.
- The forward reference to `/artifacts.kinds.create` in
  `artifacts.kinds.md` becomes a live cross-link only once that
  command lands; no action needed here, but worth confirming the
  command name does not drift before that subtask ships.
- Sibling authoring subtasks for the remaining categories (Author,
  Define kinds, Validate, Project Setup) should follow the same
  prompt skeleton established here for consistency.