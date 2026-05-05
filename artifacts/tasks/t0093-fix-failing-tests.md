---
kind: task
id: t0093
name: fix-failing-tests
type: implementation
status: review
assignee: developer
owner: user
created: 2026-05-05
started: 2026-05-05
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

- [ ] `pytest -q` exits 0 with 532 passed, 1 skipped, 0 failed (current: 13 failed).
- [ ] `tests/ai/test_body_loader.py` — all 10 previously-failing cases pass without skipping.
- [ ] `tests/cli/test_settings.py::test_show_editor_default_opens_editor` and `test_show_explicit_editor_flag_opens_editor` pass.
- [ ] `tests/test_module_system.py::test_pyproject_extras_match_spec` passes.
- [ ] No regressions introduced — the 519 currently-passing tests continue to pass.
- [ ] CI workflow (`.github/workflows/ci.yml`) runs green on Python 3.11, 3.12, and 3.13.
- [ ] Any intentional behaviour change (e.g. show no longer opens editor by default) is documented in the relevant module README or CHANGELOG.
