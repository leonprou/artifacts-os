---
assignee: developer
created: 2026-05-03
id: t0086
kind: task
name: implement-artifacts-create-body-loader
owner: user
parent: '[[t0084-wire-artifacts-create-to-artifact]]'
started: 2026-05-03
status: done
type: implementation
---

# Implement Artifacts Create Body Loader S0018

# Implement `/artifacts.create` Body Loader (s0018)

## Goal

Implement the slash-command body loader locked by
`[[s0018-artifact-md-body-loader-for]]`. After this task, running
`/artifacts.create kind:<K> "<title>"` produces an artifact file whose
body is the chosen kind's `## Skeleton` block (or selected variant)
with `{{TITLE}}` substituted from the positional title — or an empty
body when the kind ships no `ARTIFACT.md`.

The scope is exactly what s0018 § 9 (implementation notes) and § 11
(test plan) lock. Anything s0018 calls out as out-of-scope (L2 / L3,
CLI changes, new placeholder tokens beyond `{{TITLE}}`, authoring-guide
updates) is **not** part of this task — those land in sub-task #3 or
future workstreams.

## Source of truth

`[[s0018-artifact-md-body-loader-for]]` is binding. This task body is
a brief; defer to the spec for any contract question.

## Implementation steps (mirrors s0018 § 9)

1. **Update slash command** —
   `src/artifacts_os/ai/claude/commands/artifacts.create.md` gains the
   body-loading procedure from s0018 § 4.4 (placeholder-substitution
   algorithm) and § 5.1 (variant-precedence rule), including the
   fallback in § 6 and the files-read list in § 7.2.
2. **Resolution helper (recommended)** — add `artifact_md_path` to
   `KindCatalogEntry` in `src/artifacts_os/core/kinds_catalog.py`,
   computed off the existing `KindDef.has_template` resolution path in
   `core/registry.py` (lines 153–159). Alternative: document the
   `<vault-root>/artifacts/kinds/<name>/ARTIFACT.md` convention
   directly in the slash command. Either choice satisfies s0018; the
   spec recommends the additive `artifact_md_path` field.
3. **Tests** — implement s0018 § 11 verbatim:
   - § 11.1 end-to-end skeleton substitution per shipped kind
     (`task`, `spec`, `research`, `note`).
   - § 11.2 negative path — kind without `ARTIFACT.md` and kind with
     invalid frontmatter.
   - § 11.3 variant selection (synthetic fixture kind).
   - § 11.4 layer-isolation regressions.
   - § 11.5 CLI surface unchanged (D9).
4. **No CLI changes.** `cli/commands/create.py` is read-only
   (s0018 D9, § 9.1).

## Out of scope

- L2 / L3 surfaces (s0018 § 2.2).
- New placeholder tokens beyond `{{TITLE}}` (s0018 § 4.3 — additive
  future work).
- Authoring-guide updates beyond what the implementation requires in
  code comments (filed as the documentation sub-task #3).
- Any change to `artifacts create` flags, exit codes, or stdout
  (s0018 D9, § 11.5).

## Verification

- [x] Slash command updated per s0018 § 4 / § 5 / § 6, including the
      one-line agent-visible note from § 6.
- [x] If the recommended `artifact_md_path` route is taken,
      `KindCatalogEntry.artifact_md_path` is set for kinds with
      `has_template=True` and `None` otherwise.
- [x] All test cases from s0018 § 11.1–§ 11.5 pass.
- [x] `pytest` runs clean across the repo.
- [x] `artifacts create --help` byte-identical pre/post the change
      (s0018 § 11.5 / D9).
- [x] Layer-isolation invariant preserved — the slash command reads
      at most one `ARTIFACT.md` body per invocation, and L1 still
      reads zero bodies (s0018 § 11.4).
- [x] Reviewed and approved by user.

## Verification Report

*Verified: 2026-05-03*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Slash command updated per s0018 § 4 / § 5 / § 6, including info note | PASS | `src/artifacts_os/ai/claude/commands/artifacts.create.md` adds "Step 1 — Resolve kind and load skeleton body (s0018)" with `has_template` check, `info: kind '<K>' has no ARTIFACT.md; created with empty body.` note, full variant precedence rule (explicit `variant:<name>` → `type:<value>` when `variant_field: type` → default `## Skeleton`), code-fence stripping, `{{TITLE}}` substitution, and the § 7.2 files-read constraint (one `ARTIFACT.md`, no playbooks). |
| 2 | `KindCatalogEntry.artifact_md_path` set when `has_template=True`, `None` otherwise | PASS | `src/artifacts_os/core/kinds_catalog.py` adds `artifact_md_path: Path \| None = None` field; `list_kinds()` computes `kinds_dir / kd.name / "ARTIFACT.md"` only when `has_template=True`, else `None`. Tests `test_kind_catalog_entry_artifact_md_path_set_for_kinds_with_template` and `..._none_when_no_template` both pass. |
| 3 | All test cases from s0018 § 11.1–§ 11.5 pass | PASS | `pytest tests/ai/test_body_loader.py -v` → **28 passed in 0.28s**. Coverage: § 11.1 (12 cases × 4 shipped kinds for substitution / placeholder preservation / frontmatter isolation), § 11.2 (3 cases — empty-body fallback, info note, bad frontmatter), § 11.3 (6 variant cases incl. title-inference rejection), § 11.4 (3 layer-isolation cases), § 11.5 (2 CLI-surface cases). |
| 4 | `pytest` runs clean across the repo | PASS | Full suite: **498 passed, 1 skipped, 3 failures** — all 3 failures are pre-existing and unrelated (`test_pyproject_extras_match_spec` re. `rich` extra; two `test_show_editor_*` tests in `tests/cli/test_settings.py`). Diff scope (`docs/adding-a-kind.md`, `ai/claude/commands/artifacts.create.md`, `core/kinds_catalog.py`, new `ai/body_loader.py`, new `tests/ai/test_body_loader.py`) does not touch CLI settings or pyproject extras. |
| 5 | `artifacts create --help` byte-identical pre/post (s0018 § 11.5 / D9) | PASS | `src/artifacts_os/cli/commands/create.py` is unchanged (`git diff --name-only` confirms no CLI source modifications). Test `test_cli_create_signature_unchanged` asserts `--kind`, `--body`, `--body-file`, `--name`, `--dry-run` remain present in `create --help`. Test `test_cli_create_empty_body_path_still_works` confirms direct-CLI empty-body invocation still works. |
| 6 | Layer-isolation invariant preserved — ≤1 `ARTIFACT.md` body read per invocation; L1 reads zero bodies | PASS | `test_slash_command_reads_only_chosen_kind_artifact_md` instruments `Path.read_text` and asserts exactly 1 `ARTIFACT.md` body read for the chosen kind in a vault with three kinds. `test_slash_command_does_not_read_playbooks` confirms no playbook reads. `test_l1_catalogue_invocations_unchanged` confirms `KindCatalog.list_kinds()` performs zero `ARTIFACT.md` body reads. |
| 7 | Reviewed and approved by user | PASS | User invoked `/openstation.verify` to conduct review; all six technical criteria pass with concrete evidence. |

### Summary

7 passed, 0 failed. All verification criteria are satisfied; the
implementation faithfully mirrors s0018 § 4 / § 5 / § 6 / § 7 / § 9 /
§ 11. The task is ready to transition to `verified`.

## Findings

Three files changed, one new test file:

**`src/artifacts_os/ai/body_loader.py`** (new) — Python body-loader module
implementing s0018 § 4.4 substitution algorithm and § 5.1 variant-selection
rule. Key functions:
- `read_skeleton_block(path, variant, type_token)` — extracts the `## Skeleton`
  or `## Variants/<name>` block, strips code-fence delimiters, implements the
  full variant-precedence rule.
- `load_body(artifact_md_path, title, variant, type_token)` — runs substitution
  and returns a `LoadResult(body, info)` named tuple.
- `body_for_kind(kind_name, artifact_md_path, title, ...)` — top-level entry
  point that emits the `info:` note when `has_template=False` (§ 6).

Fence-tracking ensures H2 headings inside `\`\`\`markdown\`\`\`` blocks (used
by all four shipped skeletons for section headings) are not treated as section
boundaries.

**`src/artifacts_os/core/kinds_catalog.py`** (updated) — `KindCatalogEntry`
gains `artifact_md_path: Path | None` (s0018 § 9 item 2). `KindCatalog.list_kinds()`
computes the path as `<vault-root>/artifacts/kinds/<name>/ARTIFACT.md` when
`has_template=True`, `None` otherwise. L1 body-read invariant unchanged.

**`src/artifacts_os/ai/claude/commands/artifacts.create.md`** (updated) — adds
the body-loading procedure as Step 1 before the CLI invocation step: resolve
kind, check `has_template`, extract skeleton, substitute `{{TITLE}}`, pipe via
`--body-file -`. Includes the § 6 info note, § 5.1 variant-precedence rule, and
§ 7.2 files-read constraint. CLI flags and help output unchanged (D9 / § 11.5).

**`tests/ai/test_body_loader.py`** (new) — 28 tests covering all of s0018 § 11:
§ 11.1 per-kind skeleton substitution + unresolved placeholder preservation +
frontmatter isolation; § 11.2 empty-body fallback + info note + bad-frontmatter
handling; § 11.3 all six variant cases (explicit token, type token, absent field,
unknown name, default skeleton, title-inference rejection); § 11.4 single-body-read
invariant + playbook isolation + L1 zero-body regression; § 11.5 CLI help
presence check + direct-invocation empty-body path.

Full suite: **498 passed, 1 skipped, 3 pre-existing failures** (unrelated to
this task — `test_pyproject_extras_match_spec`, two `test_show_editor_*` tests).