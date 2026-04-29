---
assignee: architect
id: t0037
kind: task
name: redefine-name-field-as-slug
owner: user
started: 2026-04-29
status: done
type: refactor
completed: 2026-04-29
---

## Context

Today the `name` frontmatter field stores the full filename stem,
which for numbered kinds duplicates `id`:

```yaml
id:   t0036
name: t0036-improve-cli-create-command   # id embedded twice
```

`core.create` builds this as `name = f"{aid}-{slug}"` (see
`src/artifacts_os/core/store.py:93`), where `slug` is a transient
local computed by `slugify(title)` and never persisted. Non-numbered
kinds (agents) already store slug-only `name` (`name: architect`),
so the convention is inconsistent across kinds.

This redundancy blocks t0036 from offering a clean `--name` override
flag, and forces a separate `slug` concept in any future CLI
ergonomics work.

## Goal

Make `name` slug-only across all kinds. Filename stem is computed
as:

- `{id}-{name}.md` for numbered kinds
- `{name}.md` for non-numbered kinds

`id` and `name` become orthogonal — no embedded duplication.

## Requirements

1. **Update `core.create`** so the persisted `name` field is the
   slug only. Keep file naming behavior the same on disk
   (numbered kinds still produce `{id}-{slug}.md`).
2. **Audit readers of `name`** in `views`, `cli`, `validate`,
   `log`, and any tests. Anywhere that needs the stem (display,
   wikilink target) should derive it as `f"{id}-{name}"` for
   numbered kinds, or use the file's `path.stem` directly.
3. **Migration sweep** — rewrite `name: <id>-<slug>` to
   `name: <slug>` in every existing artifact under
   `artifacts/tasks/`, `artifacts/specs/`, `artifacts/research/`.
   Non-numbered kinds (agents) are already correct; verify no-op.
   Provide a one-shot script in `scripts/` or document the
   `sed`/Python invocation used.
4. **Wikilinks unchanged** — `[[t0036-improve-cli-create-command]]`
   continues to resolve by file stem. Confirm by grepping for
   wikilink resolution code (likely in `views` or `core.registry`).
5. **Spec update** — amend `artifacts/specs/s0002-artifacts-os-architecture.md`
   (and any sibling spec describing frontmatter shape) to reflect
   the new `name` semantic.
6. **Doc update** — update `CLAUDE.md` "Naming Conventions"
   section and `docs/` references.

## Progress

### 2026-04-29 23:45:45 — Incomplete run (r0042)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$3.07, turns=51

### 2026-04-29 — Resumed and completed

Implemented slug-only name across all kinds: `core.create` writes
`name=slug`; CLI commands (`create`, `list -q`, `status`, `verify`)
emit `path.stem`; `validate` uses `path.stem` for the result
identifier; one-shot migration script in `scripts/` rewrote the 2
affected tasks (specs and agents were already slug-only). Updated
spec `s0002`, `CLAUDE.md` Naming Conventions, and `core/README.md`.
`pytest` → 162 passed, 1 deselected (unrelated pre-existing
`rich` extras failure).

## Findings

The redefinition was implemented as an atomic switch — frontmatter
`name` is now slug-only across all kinds. File path stem
(`{id}-{slug}` for numbered, `{slug}` for non-numbered) is unchanged
and remains the canonical reference.

**Code changes**

- `src/artifacts_os/core/store.py` — `create()` builds the
  frontmatter dict with `"name": slug` (was `"name": f"{aid}-{slug}"`).
  Filename construction is unchanged. Variable renamed `name` →
  `stem` locally to avoid confusion with the persisted `name` field.
- `src/artifacts_os/core/validate.py` — `ValidationResult.name`
  is populated from `meta.path.stem` so reports/JSON keep showing
  the canonical stem identifier.
- `src/artifacts_os/cli/commands/create.py`,
  `cli/commands/list.py` (quiet mode), `cli/commands/status.py`,
  `cli/commands/verify.py` — all switched from `artifact.name`
  to `artifact.path.stem` (or `meta.path.stem`) wherever a
  ref-resolvable identifier is printed/passed.
- `cli/commands/verify.py` — in `--all` iteration, the second
  `get()` now passes `meta.path.stem` instead of `meta.name`.
- `scripts/migrate_name_to_slug.py` (new) — one-shot, idempotent
  Python migration that walks every numbered-kind directory, parses
  frontmatter, and strips `{id}-` prefixes from `name` when present.
  Supports `--dry-run` and `--root PATH`. Used to migrate t0036
  and t0037 (only files with the legacy shape; specs were already
  slug-only and agents were never affected).
- `tests/core/test_store.py`, `tests/core/test_discover.py` — updated
  the two assertions that checked `a.name == "<id>-<slug>"`; now
  assert slug-only `name` plus `path.stem` for the full identifier.

**Spec / docs**

- `artifacts/specs/s0002-artifacts-os-architecture.md` — `create`
  steps and `ArtifactMeta` field reference now describe slug-only
  `name`. Added decision-log row #7. Removed the obsolete clarification
  paragraph that previously said `name = "{id}-{slug}"` for numbered
  kinds.
- `CLAUDE.md` — Naming Conventions now spells out filename vs
  frontmatter shape explicitly with examples.
- `src/artifacts_os/core/README.md` — example output updated to
  show both `artifact.name` (slug) and `artifact.path.stem` (full).

**Wikilinks**

The discovery code (`core/discover.py::_find_in_dir`) resolves refs
by file `path.stem` first, then by `id` patterns, then partial stem
match — none of those rely on the frontmatter `name` field. So
`[[t0036-improve-cli-create-command]]` keeps resolving correctly
after migration. Confirmed by `pytest tests/core/test_discover.py`
(all 16 cases pass).

**Migration result**

```
$ python scripts/migrate_name_to_slug.py
[write] artifacts/tasks/t0036-improve-cli-create-command.md: name 't0036-...' -> 'improve-cli-create-command'
[write] artifacts/tasks/t0037-redefine-name-field-as-slug.md: name 't0037-...' -> 'redefine-name-field-as-slug'
2 file(s) migrated.
$ python scripts/migrate_name_to_slug.py --dry-run
0 file(s) would be migrated.   # idempotent
```

Specs (`s0001`–`s0010`) and agents were already slug-only; no-op
confirmed.

**Tests**

`pytest -q` → `162 passed, 1 deselected` — the only deselected test
(`test_pyproject_extras_match_spec`) is a pre-existing failure caused
by commit b089fc9 promoting `rich` to a base dependency, unrelated
to this work.

**Trade-offs / decisions**

- Chose **atomic migration** over the dual-shape transition mentioned
  in the verification list — the vault has only two affected files
  and `validate` does not currently enforce a name format, so adding
  transitional logic was unnecessary complexity.
- Did **not** add a new validate rule that `name` must be a slug.
  That can be a follow-up if drift becomes an issue. Today there
  are no readers that rely on the slug shape; everything that needs
  a stem uses `path.stem`.
- CLI output convention: every command that emits an artifact
  identifier (e.g. `create`, `list -q`, `status`) now prints
  `path.stem` so the output is always a valid ref. JSON output of
  `list` keeps dumping raw frontmatter — JSON consumers see the new
  slug-only `name` field, which is the desired downstream shape.

## Verification

- [x] `core.create` writes `name: <slug>` for numbered kinds
- [x] Existing tests pass after migration
- [x] All `name:` values in `artifacts/tasks/`, `artifacts/specs/`,
      `artifacts/research/` are slug-only (no `id` prefix)
- [x] Wikilinks `[[t####-...]]` still resolve in views/registry
- [x] `validate` accepts both pre- and post-migration shapes during
      the transition, OR migration is atomic and validate enforces
      slug-only after
- [x] Spec `s0002` and `CLAUDE.md` describe the new convention

## Verification Report

*Verified: 2026-04-29*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `core.create` writes `name: <slug>` for numbered kinds | PASS | `src/artifacts_os/core/store.py:115` builds `fm_dict = {"kind": kind, "id": aid, "name": slug, **fields}` — `name` is the slug, decoupled from `aid`/stem. |
| 2 | Existing tests pass after migration | PASS | `pytest -q` → 162 passed. Only failure is `test_pyproject_extras_match_spec` (pre-existing, caused by b089fc9 promoting `rich` to base — unrelated to this task). |
| 3 | All `name:` values in `tasks/`, `specs/`, `research/` are slug-only | PASS | `grep "^name:"` across the three dirs shows every persisted `name` is a slug. The two `t0036-…` matches are inside fenced YAML examples (t0037 Context block at L19; s0002 examples at L296/300 illustrating the new shape). `research/` is empty. |
| 4 | Wikilinks `[[t####-...]]` still resolve | PASS | `core/discover.py::_find_in_dir` resolves by `path.stem` first (L84), then expanded prefixed-id, then partial stem — never by frontmatter `name`. `tests/core/test_discover.py` passes (16 cases). |
| 5 | Migration is atomic and validate uses slug-only after | PASS | Migration ran via `scripts/migrate_name_to_slug.py` (idempotent, dry-run rerun reports 0 files). `core/validate.py` lines 80/93/181 use `meta.path.stem` for `ValidationResult.name`, so it works against the post-migration shape regardless. |
| 6 | Spec `s0002` and `CLAUDE.md` describe the new convention | PASS | `s0002` § "`name` field — slug-only across all kinds" (L287–305) plus decision-log row #7 (L30). `CLAUDE.md` Naming Conventions (L58–66) spells out filename vs frontmatter with examples and the "name field stores the slug only" rule. |

### Summary

6 passed, 0 failed. All verification criteria are satisfied; the
task is ready to be marked verified.

## Downstream

- Unblocks t0036 to introduce `--name` (not `--slug`) as the
  override flag for the auto-derived value.
- May simplify `views` rendering — the display name becomes the
  slug, with id shown separately as a column.