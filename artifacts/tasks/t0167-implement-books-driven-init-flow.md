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
status: review
type: implementation
started: 2026-05-17
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

- [ ] **D1 flow shape** — `art init --distro <url>` walks one settings prompt then one prompt per declared book, in declaration order. No standalone "kinds" / "agents" prompts.
- [ ] **D2 no-distro fallback** — `art init` (no `--distro`, no env var) writes `artifacts.yaml` + `.claude/skills/artifacts-os/SKILL.md` and exits 0. No kinds, no agents.
- [ ] **D3 per-book prompt** — single multi-select with `*` default.
- [ ] **D4 settings tier bundled** — Step 1 reads `templates/settings/{tier}.yaml`.
- [ ] **D5 `--force`** — re-init re-prompts every step and book; overwrites matching files.
- [ ] **D6 `-y` no-distro** — bare `-y` produces identical files to interactive default, no prompts.
- [ ] **Q1.a** — `art init --kinds task` exits 2 with `unrecognized arguments`.
- [ ] **Q1.b `--book`** — repeatable; `NAME` selects whole book, `NAME:items` filters; unknown name/item exits 2 pre-clone.
- [ ] **Q2** — `templates/kinds/` and `templates/agents/` absent in source tree and built wheel.
- [ ] **Q3** — wheel install into fresh venv + `art init` writes non-empty `.claude/skills/artifacts-os/SKILL.md`.
- [ ] **Q4** — `art init --distro <url>` does **not** write bundled skill; only the distro's `skills` book content lands.
- [ ] **Q5.a** — reordering books in `artbook.yaml` reorders prompts.
- [ ] **Q6** — manifest/clone errors exit 2 pre-pull; per-book failure logs + continues; init exits 1 at end.
- [ ] **Q7** — docs in `docs/init-flow.md`, `docs/artbook.md` § Consumer Quickstart, and `cli/README.md` § init reflect new flow with at least one transcript per branch (D1, D2, fully-flagged).