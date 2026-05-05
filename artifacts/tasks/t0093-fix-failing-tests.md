---
assignee: developer
created: 2026-05-05
id: t0093
kind: task
name: fix-failing-tests
owner: user
started: 2026-05-05
status: verified
type: implementation
---

# Fix Failing Tests

## Requirements

Three independent failure clusters were observed in `pytest -q` on `main` (13 failed / 519 passed / 1 skipped):

1. **`tests/ai/test_body_loader.py` — 10 failures.**
   The body loader returns `LoadResult(body='', info="info: kind '<X>' has no ARTIFACT.md; created with empty body.")` when tests expect `info is None`. Affected parametrised cases: `task`, `spec`, `research`, `note` for `test_e2e_kind_skeleton_substitutes_title`; subset for `test_e2e_kind_unresolved_placeholders_preserved`; plus `test_kind_catalog_entry_artifact_md_path_set_for_kinds_with_template` and `test_kind_catalog_entry_artifact_md_path_none_when_no_template`.
   Either the loader's ARTIFACT.md discovery path is wrong, or the test fixture isn't placing `ARTIFACT.md` where the loader looks. Reconcile so the e2e shipped kinds resolve their bundled ARTIFACT.md and the catalogue entry tests match implementation.

2. **`tests/cli/test_settings.py` — 2 failures (`test_show_editor_default_opens_editor`, `test_show_explicit_editor_flag_opens_editor`).**
   `cli show` no longer invokes `subprocess.run` for the editor when `cli.defaults.show.editor: true` (or the `-e` flag) is set; it renders a Rich table instead. Restore the editor-opening branch so the tests pass, or update the tests if the behaviour change is intentional and document it.

3. **`tests/test_module_system.py::test_pyproject_extras_match_spec` — 1 failure.**
   Test asserts `any("rich" in dep for dep in extras["views"])`, but `rich` is now a base dependency and `views = []`. Either move `rich` back into `views` extra, or update the test (and the spec it references) to reflect that `rich` is core.

## Findings

Prior session (commit af8bb04) resolved the original 13 failing tests by fixing the body loader, editor branch, and pyproject extras, but then deleted 12 test functions (§ 11.1: `test_e2e_kind_skeleton_substitutes_title`, `test_e2e_kind_unresolved_placeholders_preserved`, `test_e2e_kind_frontmatter_unchanged_by_substitution` — 4 parametrized variants each) rather than keeping them passing. This dropped the total from 532 to 520 passed.

Fix (commit c48bd38):
- Re-added `## Skeleton` blocks with `{{TITLE}}` and kind-specific placeholders to all four shipped ARTIFACT.md files (`task`, `note`, `spec`, `research`)
- Restored `_PROJECT_ROOT` / `_KINDS_DIR` / `_shipped_artifact_md` helpers and all 12 deleted test functions in `tests/ai/test_body_loader.py`

Result: `pytest -q` → 532 passed, 1 skipped, 0 failed.

## Progress

### 2026-05-05 — developer
> time: 14:49

Restored skeleton sections to task/note/spec/research ARTIFACT.md files and re-added 12 deleted e2e tests (§ 11.1). Root cause: prior session commit af8bb04 deleted tests instead of fixing them. Fix: restored ## Skeleton blocks and test helpers/_shipped_artifact_md. Result: 532 passed, 1 skipped, 0 failed.

## Verification

- [x] `pytest -q` exits 0 with 532 passed, 1 skipped, 0 failed (current: 13 failed).
- [x] `tests/ai/test_body_loader.py` — all 10 previously-failing cases pass without skipping.
- [x] `tests/cli/test_settings.py::test_show_editor_default_opens_editor` and `test_show_explicit_editor_flag_opens_editor` pass.
- [x] `tests/test_module_system.py::test_pyproject_extras_match_spec` passes.
- [x] No regressions introduced — the 519 currently-passing tests continue to pass.
- [x] CI workflow (`.github/workflows/ci.yml`) runs green on Python 3.11, 3.12, and 3.13.
- [x] Any intentional behaviour change (e.g. show no longer opens editor by default) is documented in the relevant module README or CHANGELOG.

## Verification Report

*Verified: 2026-05-05*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `pytest -q` exits 0 with 532 passed, 1 skipped, 0 failed | PASS | `pytest -q` → `551 passed, 1 skipped in 2.43s` (count exceeds 532 because subsequent commits added tests; 0 failed) |
| 2 | `tests/ai/test_body_loader.py` — all 10 previously-failing cases pass | PASS | `pytest tests/ai/test_body_loader.py -v` → 28 passed, including all 4 `test_e2e_kind_skeleton_substitutes_title`, 4 `test_e2e_kind_unresolved_placeholders_preserved`, plus `test_kind_catalog_entry_artifact_md_path_set_for_kinds_with_template` and `test_kind_catalog_entry_artifact_md_path_none_when_no_template` |
| 3 | Editor tests in `tests/cli/test_settings.py` pass | PASS | `pytest tests/cli/test_settings.py::test_show_editor_default_opens_editor tests/cli/test_settings.py::test_show_explicit_editor_flag_opens_editor -v` → 2 passed |
| 4 | `tests/test_module_system.py::test_pyproject_extras_match_spec` passes | PASS | `pytest tests/test_module_system.py::test_pyproject_extras_match_spec -v` → 1 passed |
| 5 | No regressions introduced | PASS | Full suite green: 551 passed, 1 skipped, 0 failed (>= 519 baseline + 13 fixed) |
| 6 | CI workflow runs green on Python 3.11, 3.12, 3.13 | PASS | Workflow run [25379961502](https://github.com/leonprou/artifacts-os/actions/runs/25379961502) on `main` after push of e0dc350 → all three matrix jobs green (3.11 in 24s, 3.12 in 23s, 3.13 in 25s) |
| 7 | Intentional behaviour changes documented | PASS (vacuous) | No intentional behaviour change in this fix — commit ffb09b9 *restored* prior editor-opening behaviour (subprocess.run reinstated; TTY guard removed) rather than introducing a new one. Nothing to document |

### Summary

7 passed, 0 failed. All verification criteria met. Final CI confirmation came from run [25379961502](https://github.com/leonprou/artifacts-os/actions/runs/25379961502) after `e0dc350` was pushed to `main`: all three Python matrix jobs (3.11, 3.12, 3.13) green.