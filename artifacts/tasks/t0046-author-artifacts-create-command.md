---
kind: task
id: t0046
name: author-artifacts-create-command
type: implementation
status: review
assignee: author
owner: user
parent: "[[t0041-ai-claude-commands-support]]"
created: 2026-04-30
started: 2026-04-30
---

# Author /Artifacts.Create Command

## Scope

Author the single `/artifacts.create` slash-command in the **Author artifacts** category from `t0041`'s surface definition. This is Category 2 — one kind-aware creator that maps to `artifacts create --kind <K>`. Pure prompt/content deliverable — no Python, no install machinery (those land in the developer subtask).

| Command | File | Maps to |
|---|---|---|
| `/artifacts.create` | `artifacts.create.md` | `artifacts create --kind <K>` |

File lands at: `src/artifacts_os/ai/claude/commands/artifacts.create.md`

Pattern set by sibling subtask `t0043-author-browse-and-inspect-claude` — follow that skeleton for consistency (frontmatter + `## Input` + `## Procedure` + worked examples + edge-cases table + cross-references).

## Requirements

1. Author `src/artifacts_os/ai/claude/commands/artifacts.create.md`:
   - Frontmatter: `name: artifacts.create` and a `description` matching the prompt-discovery convention used in `.openstation/commands/openstation.create.md` and the three sibling `artifacts.*` files.
   - `## Input` table maps `$ARGUMENTS` tokens (free-form `title`, `kind:<value>`, `body:<…>`/`body-file:<path>`, `name:<slug>`, `dry-run`, plus convenience fields like `assignee:<…>`, `parent:<ref>`, `depends-on:<ref>`, etc.) to their CLI flag equivalents.
   - `## Procedure` block walks Claude through invoking `artifacts create` with the canonical positional `title` plus translated flags, including the `--kind` resolution chain (explicit flag → `cli.defaults.create.kind` → `task` fallback) so the prompt does not assume a kind.
   - Cover the **kind-aware help** behaviour — re-running `artifacts create --kind <K> --help` reveals kind-specific schema flags (e.g. `--status`, `--priority`, `--assignee`) — and instruct Claude to consult that help when the user names a kind.
   - Document the body input modes: `--body "…"`, `--body-file PATH`, `--body-file -` (stdin).
   - Document `--name` slug override and `--fields KEY=VALUE` escape hatch (with comma-list-to-array semantics).
   - Document `--dry-run`/`-n` for previewing without writing.
2. Worked examples — at least three, following the t0043 pattern:
   - Default kind from settings ("create a note titled X").
   - Explicit kind with convenience fields ("create a task assigned to <agent> with parent <ref>").
   - Dry-run preview before commit.
3. Edge-cases table covering at minimum:
   - Unknown kind (point to `/artifacts.kinds`).
   - `--body` and `--body-file` mutually exclusive.
   - Wikilink fields (`parent`, `depends_on`) — bare ref auto-wraps to `[[ref]]`.
   - Slug derivation failure (`--name` produces empty slug after slugification).
   - Validation failure (frontmatter rejected by kind schema — exit code 2).
4. Cross-references at the bottom:
   - `/artifacts.kinds` — discover registered kinds before passing `--kind`.
   - `/artifacts.list` — verify the artifact appears after creation.
   - `/artifacts.show <ref>` — inspect the created artifact.
5. **Kind-agnostic phrasing** — no hardcoded `note`/`spec`/`task` semantics. Kind names appear only as `<KIND>`/`<K>` placeholders or labelled examples.
6. **No lifecycle terminology** — the same vocabulary scan from t0043 applies (`ready`, `progress`, `done`, `verify`, `verification`, `suspend`, `fail`, `reject`, `transition`). Status values may appear only as illustrative `--fields status=<value>` examples.
7. **"Run the command exactly as shown" guard** — copy verbatim from sibling commands; Claude has historically decorated bash invocations.
8. File loads cleanly via `importlib.resources.files("artifacts_os.ai.claude.commands")` (already importable from t0043; this just adds another file).

## Verification

- [ ] `src/artifacts_os/ai/claude/commands/artifacts.create.md` exists with valid YAML frontmatter (`name`, `description`) and a `## Procedure` section.
- [ ] File documents the underlying CLI invocation, all input modes (positional title, `--kind`, body inputs, convenience flags, `--fields`, `--name`, `--dry-run`), and at least three worked examples.
- [ ] No lifecycle terminology (`ready`, `progress`, `done`, `verify`, `suspend`, `fail`, `reject`, `transition`) appears.
- [ ] No hardcoded vault-specific kind names (only placeholder syntax or labelled examples).
- [ ] The kind-resolution chain (explicit → settings → `task`) is documented so the prompt does not assume a kind.
- [ ] The kind-aware help loop is documented — Claude is told to re-run `artifacts create --kind <K> --help` after picking a kind to discover kind-specific flags.
- [ ] Cross-references to `/artifacts.kinds`, `/artifacts.list`, `/artifacts.show` are present.
- [ ] Importable via `importlib.resources.files("artifacts_os.ai.claude.commands")`.

## Reference material

- `t0041-ai-claude-commands-support` — full design context for the surface.
- `t0043-author-browse-and-inspect-claude` — prior-art skeleton; mirror its structure exactly.
- `src/artifacts_os/cli/commands/create.py` — current `artifacts create` implementation (kind-aware help, `_resolve_kind` chain, body-input modes, `--fields` semantics, wikilink wrapping for `parent`/`depends_on`).
- `src/artifacts_os/cli/README.md` — flag reference for `artifacts create`.
- `.openstation/commands/openstation.create.md` — structural prior art for prompt layout.

## Findings

Authored the single `/artifacts.create` slash-command prompt at
`src/artifacts_os/ai/claude/commands/artifacts.create.md` and added the
repo-dogfood symlink under `.openstation/commands/` (visible through the
existing `.claude/commands -> ../.openstation/commands` link).

### What ships

- `src/artifacts_os/ai/claude/commands/artifacts.create.md` (new, 7.8 KB).
- `.openstation/commands/artifacts.create.md` → symlink into the new prompt.

### Structure (mirrors `t0043` skeleton)

YAML frontmatter (`name: artifacts.create`, `description`) → `# Create
Artifact` → intro → `## Input` table → `## Procedure` block with the
literal `artifacts create` invocations + the verbatim-command guard +
flag/mode reference table → `### Kind-aware help` subsection → `### Output`
subsection → `## Worked examples` (three) → `## Edge cases` table → `##
Cross-references`.

### Kind-resolution + kind-aware help

- The `## Input` table and the first procedure invocation document the
  resolution chain explicitly: `--kind` → `cli.defaults.create.kind` →
  built-in fallback. The hardcoded `'task'` fallback from `_resolve_kind`
  was generalised to "built-in fallback" so the prompt stays kind-agnostic
  (sibling Browse & Inspect prompts contain zero references to specific
  built-in kinds; this file follows that precedent).
- A dedicated `### Kind-aware help` subsection instructs Claude to re-run
  `artifacts create --kind <KIND> --help` after picking a kind to discover
  kind-specific schema flags (the parser builds its convenience-flag set
  from the schema in two-phase parsing — see
  `src/artifacts_os/cli/commands/create.py`).

### Worked examples (three)

1. Default-kind creation with a free-form title — exercises the resolution
   chain without naming a kind.
2. Explicit kind with `--assignee`, `--parent`, and `--body-file` —
   demonstrates wikilink auto-wrapping and the file-based body input.
3. `--dry-run` preview — exercises the no-write path that prints the
   resolved frontmatter under `--- dry run (no file written) ---`.

A fourth illustrative snippet covers `--name` slug override + repeated
`--fields KEY=VALUE` with comma-to-list semantics.

### Edge cases covered

- Unknown kind → cross-reference to `/artifacts.kinds`.
- `--body` and `--body-file` mutually exclusive.
- `--body-file -` with empty stdin (silent empty body).
- Slug-derivation failure when `--name` slugifies to empty.
- Validation failure → exit code 2.
- Wikilink fields (`parent`, `depends_on`) auto-wrap behaviour.
- Comma-list semantics in `--fields` (literal-comma escape hatch).
- Conflict between `kind:<x>` and `cli.defaults.create.kind` (explicit
  wins).

### Verification scan

Programmatic check confirmed:
- Frontmatter parses; `name` + `description` present.
- `## Procedure` section present.
- Zero matches for forbidden lifecycle terminology
  (`ready|progress|done|verify|verification|suspend|fail|reject|transition`).
- Zero matches for vault-specific kind words
  (`note|spec|task|alert|research`) — fully kind-agnostic.
- Three `User asks:` worked examples.
- All required flags documented (`--body`, `--body-file`, `--name`,
  `--fields`, `--dry-run`, plus convenience flags).
- Cross-references to `/artifacts.kinds`, `/artifacts.list`,
  `/artifacts.show` all present.
- Verbatim-command guard ("Run the command exactly as shown") present.
- File loads cleanly through
  `importlib.resources.files("artifacts_os.ai.claude.commands")`.

### Design decisions

- **Used `<AGENT>` and `<PARENT-REF>` placeholders** in the worked
  examples instead of named openstation agents to keep the prompt
  reusable across vaults.
- **Generalised the `task` fallback** to "built-in fallback" in the prompt
  copy. The CLI still hardcodes `'task'`, but documenting that here would
  contradict the kind-agnostic constraint from t0043. The CLI's
  unknown-kind error will surface naturally if a vault has not registered
  the built-in.
- **Repeated `kind:<value>` token guidance** at the top of the Input
  table and again in the Kind-aware help subsection — Claude has
  historically forgotten to re-check `--help` after the kind changes.
- **Kept the verbatim-command guard verbatim** from sibling files; same
  motivation (Claude decorating bash invocations with redirects).

### Out of scope (sibling subtasks under `t0041`)

- The remaining commands (`kinds.create`, `kinds.edit`, `validate`,
  `verify`, `init`) — separate authoring subtasks per category.
- `ai/install.py`, the `artifacts ai install/uninstall/list` CLI, and
  `artifacts init` integration — `t0044`.
- The `artifacts-os` skill at
  `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` — out of
  scope here.

## Progress

### 2026-04-30 — author
> time: 22:45–23:10

Authored `src/artifacts_os/ai/claude/commands/artifacts.create.md`
mirroring the t0043 skeleton; added the dogfood symlink under
`.openstation/commands/` (re-exposed via the existing
`.claude/commands` link). Verified import via
`importlib.resources.files("artifacts_os.ai.claude.commands")`,
confirmed three worked examples, and ran the lifecycle-terminology +
kind-name scans (both clean). Transitioning to `review`.
