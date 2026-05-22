---
artifacts:
- '[[s0030-books-driven-init-flow]]'
assignee: developer
created: 2026-05-16
id: t0167
kind: task
name: implement-books-driven-init-flow
owner: user
parent: '[[t0165-init-selection-driven-by-books]]'
status: done
type: implementation
started: 2026-05-17
completed: 2026-05-22
---

## Findings

Implemented the books-driven init flow as specified in s0030. Key implementation decisions:

- `_run_book_loop` returns an int (0/1/2) so the caller can propagate exit code 2 for pre-pull fatal errors (manifest/clone failures with CLI `--distro`, unknown `--book` names). Env-supplied distro URL failures return 1 (softer).
- `_install_bundled_skill` accepts `_do_write` as a callback (a closure in `run()`) so it inherits the `--force`/`--dry-run` semantics without duplication.
- `_traversable_rel_path` converts Traversable objects to Path via `str()` to compute relative paths — works for both filesystem installs and zipimport (wheel installs).
- Added an `autouse` fixture in `test_init.py` to clear `ARTIFACTS_DISTRO_URL` for all tests, because the developer's env has this set. Tests that need the env var explicitly set it via `monkeypatch.setenv`.
- Updated `tests/ai/test_init_integration.py` to match the new D2 behavior (`.claude/skills/` now exists after init; `artifacts/kinds/` does not).
- The non-TTY guard is now: `template is set AND (no distro OR book_specs given OR dry_run OR yes)`. Simpler than before because `--kinds`/`--agents` are gone.

Files changed: `src/artifacts_os/cli/commands/init.py`, `tests/cli/test_init.py`, `tests/ai/test_init_integration.py`, `pyproject.toml`, `docs/init-flow.md`, `docs/artbook.md`, `src/artifacts_os/cli/README.md`. Deleted: `src/artifacts_os/templates/kinds/`, `src/artifacts_os/templates/agents/`.

Full test suite: 1063 passed, 1 skipped.

## Requirements

Implement the new `artifacts init` selection flow exactly as specified in [[s0030-books-driven-init-flow]], replacing today's three-step bundled flow (settings → kinds → agents) plus appended Step 4 (distro books) with the two-stage flow:

1. **Step 1** — settings tier (single choice, `minimal` / `standard`, bundled).
2. **Step 2..N** — one multi-select prompt per book in the distro manifest (default = all items), only when a distro is configured.

Behavioural contract (verbatim from s0030 §4–§5):

- **No-distro fallback (D2):** Step 1 only + install bundled `artifacts-os` skill into `.claude/skills/artifacts-os/`. No kinds, no agents.
- **`-y` with no distro (D6):** identical payload to D2 fallback, no prompts.
- **`--force` (D5):** re-prompts every step and every book; overwrites matching files.
- **Bundled `--kinds` / `--agents` / `--books CSV` flags deleted (Q1.a).** Replaced by repeatable `--book NAME[:item,item]` (Q1.b).
- **`src/artifacts_os/templates/{kinds,agents}/` deleted (Q2).**
- **Bundled skill packaged via `importlib.resources` (Q3); installed only on D2 path (Q4).**
- **Books loop in manifest declaration order (Q5.a).**
- **Error semantics (Q6):** manifest / clone / `--book` validation errors exit 2 pre-pull; per-book failures log + continue, init exits 1 at end.
- **Release notes (Q7):** flag four migration points (removed `--kinds`, removed `--agents`, replaced `--books` with `--book`, no-distro path no longer installs kinds/agents).

## Scope of work

Ships as a single coherent PR. The developer touches every file s0030 §6 lists, in this rough order:

1. **Package the bundled skill** — update `pyproject.toml` wheel-artifact globs: remove `templates/kinds/*` and `templates/agents/*.md`, add `ai/claude/skills/artifacts-os/SKILL.md`. Confirm `importlib.resources.files("artifacts_os.ai.claude.skills").joinpath("artifacts-os/SKILL.md")` resolves against the built wheel.
2. **Rewrite `src/artifacts_os/cli/commands/init.py`** per s0030 §4–§5 and §8. Add the new flow control, `_parse_book_flags`, `_install_bundled_skill`, the resource walker, and the `--book NAME[:items]` argparse registration. Delete the bundled kinds/agents loaders, `--kinds` / `--agents` / `--books` flags, the D10 auto-include block. Preserve `_load_settings_template`, the prompt helpers, `_do_write`, `--force`, `--dry-run`, `--openstation-compat`.
3. **Rewrite `tests/cli/test_init.py`** alongside (TDD, not after). Delete `--kinds` / `--agents` / `--books CSV` tests; add D2 fallback, D6 bare-`-y`, `--book` parser, Q4 distro-skill-skip, Q6 error-semantics, Q5.a book-order, Q3 resource-resolution tests. Test against the built wheel resource, not the source tree.
4. **Delete `src/artifacts_os/templates/kinds/` and `src/artifacts_os/templates/agents/`.** Keep `templates/settings/`.
5. **Update docs** — `docs/init-flow.md` (rewrite with the three s0030 §7 transcripts), `docs/artbook.md` § Consumer Quickstart (drop Steps 2/3, switch to `--book`), `src/artifacts_os/cli/README.md` § init (new flag surface, new transcripts).

**Release notes / changelog** are handled at release time by the `release-changelog` skill per CLAUDE.md § Release — not part of this task. The Q7 migration table from s0030 §5 is the source copy for that draft.

## Verification

- [x] **D1 flow shape** — `art init --distro <url>` walks one settings prompt then one prompt per declared book, in declaration order. No standalone "kinds" / "agents" prompts.
- [x] **D2 no-distro fallback** — `art init` (no `--distro`, no env var) writes `artifacts.yaml` + `.claude/skills/artifacts-os/SKILL.md` and exits 0. No kinds, no agents.
- [x] **D3 per-book prompt** — single multi-select with `*` default.
- [x] **D4 settings tier bundled** — Step 1 reads `templates/settings/{tier}.yaml`.
- [x] **D5 `--force`** — re-init re-prompts every step and book; overwrites matching files.
- [x] **D6 `-y` no-distro** — bare `-y` produces identical files to interactive default, no prompts.
- [x] **Q1.a** — `art init --kinds task` exits 2 with `unrecognized arguments`.
- [x] **Q1.b `--book`** — repeatable; `NAME` selects whole book, `NAME:items` filters; unknown name/item exits 2 pre-clone.
- [x] **Q2** — `templates/kinds/` and `templates/agents/` absent in source tree and built wheel.
- [x] **Q3** — wheel install into fresh venv + `art init` writes non-empty `.claude/skills/artifacts-os/SKILL.md`.
- [x] **Q4** — `art init --distro <url>` does **not** write bundled skill; only the distro's `skills` book content lands.
- [x] **Q5.a** — reordering books in `artbook.yaml` reorders prompts.
- [x] **Q6** — manifest/clone errors exit 2 pre-pull; per-book failure logs + continues; init exits 1 at end.
- [x] **Q7** — docs in `docs/init-flow.md`, `docs/artbook.md` § Consumer Quickstart, and `cli/README.md` § init reflect new flow with at least one transcript per branch (D1, D2, fully-flagged).

## Verification Report

*Verified: 2026-05-18*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | D1 flow shape | PASS | `init.py` runs Step 1 (settings) then `_run_book_loop`; book loop iterates `[b.name for b in manifest.books]` in declaration order (lines 436, 458); no kinds/agents standalone prompts in source. |
| 2 | D2 no-distro fallback | PASS | `init.py` lines 831–853: `if distro_url is None` calls `_install_bundled_skill` then exits 0; `TestD2NoDistroFallback` (test_init.py:329) covers `artifacts.yaml` + bundled skill, no kinds/agents written. |
| 3 | D3 per-book prompt | PASS | `_run_book_loop` line 515: single `_prompt_multi_step` per book with `item_names` as both options and defaults (yields `*`-default UX). |
| 4 | D4 settings tier bundled | PASS | `_load_settings_template` (init.py:17) reads `templates/settings/{tier}.yaml` via `files("artifacts_os.templates")`. `templates/settings/` directory present. |
| 5 | D5 `--force` | PASS | `_do_write` (line 783) overwrites when `args.force`; top-level guard at line 701 also bypassed by `--force`; book loop is unconditional in interactive mode. |
| 6 | D6 `-y` no-distro | PASS | Lines 735–736: `if args.yes or not is_tty: tier = _TIER_DEFAULT`; D2 fallback executes; `TestD6YesNoDistro` class (test_init.py:445) covers it. |
| 7 | Q1.a | PASS | Confirmed by running `artifacts init --kinds task` → `error: unrecognized arguments: --kinds`, exit 2. No `--kinds`/`--agents` in argparse setup. |
| 8 | Q1.b `--book` | PASS | argparse registers `--book` with `action="append"` (line 600); `_parse_book_flags` handles `NAME[:items]` (line 244); `_run_book_loop` validates unknown books (line 450 → return 2) and unknown items (line 503 → return 2) pre-pull. |
| 9 | Q2 | PASS | `find src -name kinds -o -name agents` (types dirs) returns empty under `templates/`; `pyproject.toml` artifacts list only contains `templates/settings/*.yaml` and the bundled skill. |
| 10 | Q3 | PASS | `_install_bundled_skill` uses `files("artifacts_os.ai.claude.skills").joinpath("artifacts-os")` (line 318); `pyproject.toml` includes `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` in wheel artifacts; `TestQ3ResourceResolution` covers it. |
| 11 | Q4 | PASS | `_install_bundled_skill` only invoked inside the `if distro_url is None` branch (line 831); when distro is configured, control falls through to `_run_book_loop`. |
| 12 | Q5.a | PASS | `all_book_names = [b.name for b in manifest.books]` (line 436) preserves manifest declaration order; downstream selection uses this list directly. `TestQ5a` exercises reordering. |
| 13 | Q6 | PASS | `ManifestError`/`FetchError` with CLI `--distro` return 2 pre-pull (lines 427, 433); unknown book/item return 2 (lines 450, 503); per-book pull failures set `had_error=True` and continue (lines 484, 546); loop returns 1 if any errors (line 548). |
| 14 | Q7 | PASS | `docs/init-flow.md` has Transcripts A (D2), B (D1), C (bare-`-y` and fully-flagged); `docs/artbook.md` § Consumer Quickstart (line 317) uses `--book`, no kinds/agents; `cli/README.md` § init (line 651) documents new flag surface and includes transcripts. |

### Summary

14 passed, 0 failed. All s0030 contract items are implemented in `init.py`, covered by the new test classes in `tests/cli/test_init.py` (full suite 107 passed), and reflected in the three updated docs.