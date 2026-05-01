---
assignee: developer
created: 2026-05-01
id: t0047
kind: task
name: cli-list-named-views
owner: user
status: ready
type: feature
subtasks:
  - "[[t0048-spec-cli-list-named-views]]"
artifacts:
  - "[[artifacts/specs/s0012-cli-list-named-views]]"
---

## User Story

**As a** vault user running `artifacts list`,
**I want** to define named views (columns + filters + sort) in
`artifacts/artifacts.yaml` and invoke them with `--view <name>` or
auto-bind per kind via `default_views`,
**so that** I can reuse curated list presets across kinds and expose
them as ergonomic slash commands without retyping flags.

## Directions

> Final tech requirements will be set by the spec sub-task. The bullets
> below are intent, not contract.

- `artifacts list` should consume the existing `ViewsSettings`
  (s0007). The data model is in place; the CLI currently ignores it.
- Support `--view <name>` lookup and `default_views` per-kind
  binding.
- Keep precedence consistent with openstation's reference
  (`src/openstation/tasks.py:cmd_list`, lines 1049–1102): explicit
  CLI flag > view config > registry defaults; filter merging is
  per-key, not wholesale.
- `.openstation/commands/` should be able to wrap view invocations
  as ergonomic slash-command shortcuts (e.g. `/artifacts.list.review`).
- `--json` / `--quiet` must remain machine-readable: filters and
  sort apply, columns do not.
- Reference openstation: `.openstation/docs/views.md` and
  `src/openstation/tasks.py:cmd_list`.

## Sub-tasks

- [[t0048-spec-cli-list-named-views]] — architect produces the spec; once
  approved, this task's tech requirements are finalized and it
  promotes from `backlog` to `ready`.

## Tech Requirements (finalized)

Authoritative spec: [[artifacts/specs/s0012-cli-list-named-views]].
Requirements below are normative; refer to the spec for rationale,
diagrams, and implementation outline.

1. **CLI surface** — add `--view <name>` (`-V`) to
   `artifacts list`. See spec §3.
2. **Resolution algorithm** — implement the algorithm in spec §4
   in a helper called from `cli/commands/list.py:run` *before*
   the existing branches for quiet / json / table. Mutate `args`
   to carry resolved filters, sort key, and column list.
3. **Precedence (columns)** — `--fields` > `view.columns` >
   registry default columns > hardcoded fallback. See spec §5.
4. **Precedence (filters)** — explicit CLI flag wins per-key over
   `view.filters[key]`; non-native keys (`assignee`, `type`, etc.)
   apply as a post-discovery equality filter on
   `meta.frontmatter[key]`. Wholesale replacement is forbidden.
5. **`default_views` binding** — keyed by **kind name**. Fires
   only when `args.view is None` and `args.kind is not None`.
   Inference from a homogeneous result set is deferred.
6. **JSON / quiet contract** — `-q` / `-j` ignore columns but
   apply filters and sort. Order: resolve filters/sort *above*
   the quiet/json short-circuit; resolve columns *below* it.
7. **Errors** — unknown `--view` exits `2` with
   `error: unknown view '<name>'`; unknown bound view exits `2`
   with `error: default_views.<k> refers to unknown view '<v>'`.
   See spec §9 for the full table.
8. **Slash-command shims** — convention
   `.openstation/commands/artifacts.list.<view>.md`. Body is a
   single fenced `artifacts list --view <view>` block. No
   generator.
9. **Settings loading** — add `_load_views_settings(root)` helper
   in `cli/__init__.py` returning `ViewsSettings | None`. Do
   **not** widen `CliSettings` to include views (would couple
   `cli` settings parsing to `views`).
10. **Docs** — update `src/artifacts_os/cli/README.md` and
    `docs/settings.md` per spec §11.5.

## Verification

- [x] Spec sub-task merged and approved before this task moves to
      `ready` (see [[t0048-spec-cli-list-named-views]])
- [ ] `artifacts list --view <name>` works end-to-end (filters,
      columns, sort all applied)
- [ ] `default_views: {<kind>: <view>}` binding fires
      automatically when `--kind <kind>` is supplied and no
      `--view` is
- [ ] Per-key filter merging: explicit `--status` overrides
      view's `filters.status` while leaving other keys intact
- [ ] Unknown `--view` exits `2` with the documented stderr
      message
- [ ] Unknown bound view exits `2` with the
      `default_views.<k>` message
- [ ] `-j` and `-q` ignore columns but apply filters + sort
- [ ] `tests/cli/test_list_views.py` covers all 10 cases listed
      in spec §11.4
- [ ] `src/artifacts_os/cli/README.md` documents the `--view`
      flag and the views/precedence model
- [ ] `docs/settings.md` cross-links to the views section
- [ ] At least one `.openstation/commands/artifacts.list.<v>.md`
      shim shipped, demonstrating the pattern in spec §12