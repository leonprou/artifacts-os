---
artifacts:
- '[[artifacts/specs/s0012-cli-list-named-views]]'
assignee: architect
created: 2026-05-01
id: t0048
kind: task
name: spec-cli-list-named-views
owner: user
parent: '[[t0047-cli-list-named-views]]'
started: 2026-05-01
status: done
type: spec
---

## Goal

Produce a spec under `artifacts/specs/` that finalizes the technical
contract for the parent task [[t0047-cli-list-named-views]]. After
approval, the spec's verification criteria become the parent task's
checklist, and the parent promotes from `backlog` to `ready`.

## Approach

Architect's call: extend `s0007-artifacts-os-views-module` or add a
new sibling spec (e.g. `s00XX-cli-list-named-views`). Either way,
cross-link `s0007` and openstation's reference (`.openstation/docs/views.md`,
`src/openstation/tasks.py:cmd_list` lines 1049–1102).

## Required Spec Coverage

1. **CLI surface** — exact flags (`--view`, optional alias,
   interaction with `--fields`, `--status`, `--kind`).
2. **Resolution algorithm** — order of operations from `args` →
   `ViewsSettings` → applied filters / columns / sort. Reference
   openstation's `cmd_list`.
3. **Precedence rules** — table form: explicit CLI flag > `--fields`
   > view `columns` > registry default columns. Filter merging is
   per-key.
4. **`default_views` binding** — when it fires (kind known via
   `--kind` or homogeneous result set), error semantics for unknown
   bound view (exit 2 + message format).
5. **JSON / quiet contract** — `columns` ignored; `filters` +
   `sort` still applied.
6. **Error handling** — unknown `--view` name behavior (exit code,
   message), missing `views:` section (silent no-op vs error).
7. **Slash-command pattern** — convention for
   `.openstation/commands/artifacts.list.<name>.md` shims; whether
   to ship a generator or document by example.
8. **Open questions to resolve** — alias for `--view`? Sort
   stability across kinds? Filter keys allowed (status / assignee /
   kind / type only, or arbitrary frontmatter)?

## Verification

- [x] Spec file committed under `artifacts/specs/`
- [x] Covers all eight points listed under *Required Spec Coverage*
- [x] Cross-links `s0007` and openstation's
      `.openstation/docs/views.md` reference
- [x] Reviewed and approved by user
- [x] Parent task [[t0047-cli-list-named-views]] updated with
      finalized tech requirements + `artifacts: [[spec-link]]`
      frontmatter

## Verification Report

*Verified: 2026-05-01*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec file committed under `artifacts/specs/` | PASS | `artifacts/specs/s0012-cli-list-named-views.md` exists (494 lines, frontmatter `kind: spec, id: s0012, task: [[t0048-spec-cli-list-named-views]]`). |
| 2 | Covers all eight points listed under *Required Spec Coverage* | PASS | §3 CLI surface, §4 resolution algorithm, §5 precedence (table form), §7 + §10 `default_views` binding & error semantics, §8 JSON/quiet contract, §9 error handling table, §12 slash-command pattern, §10 open questions resolved. All eight numbered top-level sections present. |
| 3 | Cross-links `s0007` and openstation's `.openstation/docs/views.md` reference | PASS | s0007 referenced at lines 15, 24, 60, 169, 307, 484; `.openstation/docs/views.md` linked at lines 31, 265, 422, 484; `src/openstation/tasks.py:cmd_list` lines 1049–1102 cited at lines 33, 141. |
| 4 | Reviewed and approved by user | PASS | User invoked `/openstation.verify` on this task (owner = `user`); parent t0047 already records spec approval in its first verification item. |
| 5 | Parent task t0047 updated with finalized tech requirements + `artifacts:` frontmatter | PASS | t0047 frontmatter has `artifacts: - "[[artifacts/specs/s0012-cli-list-named-views]]"`; body carries a "Tech Requirements (finalized)" section with 10 numbered items pointing at s0012 and an 11-item verification checklist drawn from spec §13. |

### Summary

5 passed, 0 failed. All verification criteria satisfied — task ready to transition to `verified`.

## Findings

Produced [[artifacts/specs/s0012-cli-list-named-views]] as a new
sibling spec to s0007 (rather than extending s0007 in place).

**Key reasoning for a separate spec:**

- s0007 is the views *module* spec — data model and YAML parsing.
  It is shipped and stable.
- The CLI integration is a distinct surface with its own
  precedence model, error semantics, and slash-command
  conventions. Bundling it into s0007 would mix module-level
  decisions with consumer-level decisions.
- A standalone spec gives the implementing developer a single
  document to verify against (matches the parent task's
  verification checklist 1:1).

**Coverage of the eight required points** — all addressed in
s0012:

| Point | Section in s0012 |
|-------|-------|
| 1. CLI surface | §3 |
| 2. Resolution algorithm | §4 |
| 3. Precedence rules | §5 |
| 4. `default_views` binding | §7, §10 |
| 5. JSON / quiet contract | §8 |
| 6. Error handling | §9 |
| 7. Slash-command pattern | §12 |
| 8. Open questions resolved | §10 |

**Notable design decisions** (full rationale in s0012 §10, §14):

- **Bind by `--kind`**, not `--type`. artifacts-os is kind-first;
  `type` is a per-kind frontmatter convention.
- **Unknown `--view` is a hard exit-2 error**, not a warning
  (diverges from openstation reference). Slash-command typos
  silently falling through is harder to debug than a clear error.
- **Filter keys other than `status` / `kind` apply as
  post-discovery equality filters** on `frontmatter[key]`.
  Generalises beyond the openstation reference's
  `status` / `assignee` / `type` allowlist while staying
  predictable.
- **Sort: lexicographic with missing-last** in both ascending
  and descending modes. Cross-kind sort uses stringified
  comparison.
- **Alias `-V` for `--view`** (capital V). Leaves `-v` free for
  future `--verbose`.
- **Helper-based `ViewsSettings` loading** in `cli/__init__.py`,
  not coupling `CliSettings` to views. Preserves the module DAG.

**Deferred items** (flagged in s0012 §10):

- Inferring `binding_kind` from a homogeneous result set.
- Generator tooling for slash-command shims.
- Filter expressions richer than equality.
- Per-kind sort orderings.

**Cross-links present in spec:**

- s0007 (data model) — §1 paragraph 1.
- s0003 (CLI module) — §1 paragraph 2.
- s0010 (settings extension pattern) — §1 paragraph 4.
- `.openstation/docs/views.md` — §1 paragraph 3, §8.
- `src/openstation/tasks.py:cmd_list` lines 1049–1102 — §1
  paragraph 3, §4.

**Parent task update:** [[t0047-cli-list-named-views]] now carries
the finalized tech requirements (10 numbered items) and a 11-item
verification checklist drawn directly from s0012 §13. The
`artifacts:` frontmatter on both this task and the parent points
at the spec.

## Downstream

- The parent task [[t0047-cli-list-named-views]] is now `ready`
  for a developer pickup once the spec is approved by the user.
  No additional decomposition needed — implementation outline
  in s0012 §11 is concrete enough for a single developer pass
  (one new test file, one new helper, one updated command, two
  doc files, one slash-command example).
- s0003 mentions `--view` only in passing; once t0047 lands, a
  follow-up doc edit could replace that paragraph with a pointer
  to s0012. Not blocking.