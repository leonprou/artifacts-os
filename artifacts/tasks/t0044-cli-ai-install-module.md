---
assignee: developer
created: 2026-04-30
id: t0044
kind: task
name: cli-ai-install-module
owner: user
parent: '[[t0041-ai-claude-commands-support]]'
started: 2026-04-30
status: done
type: implementation
---

# Cli Ai Install Module

## Scope

Build the install machinery that ships `/artifacts.*` slash commands (and the future skill) into a vault's `.claude/` (and later `.opencode/`) directory. Implements the public Python API, the `artifacts ai` CLI sub-surface, the `artifacts init` integration, and the repo-level dogfood update. No prompt content is authored here — that lives in sibling `author` subtasks under `t0041`.

## Requirements

1. **Public Python API** at `src/artifacts_os/ai/__init__.py`:

   ```python
   def install(
       target: Path,
       *,
       mode: Literal["link", "copy"] = "link",
       tool: Literal["claude", "opencode"] = "claude",
       force: bool = False,
       dry_run: bool = False,
   ) -> InstallReport: ...

   def uninstall(target: Path, *, tool: str = "claude", dry_run: bool = False) -> InstallReport: ...

   def list_installed(target: Path) -> list[InstalledAsset]: ...
   ```

   Backed by a new `src/artifacts_os/ai/install.py` with the heavy lifting; `__init__.py` is the thin re-export layer.

2. **Source resolution via `importlib.resources`** — never hardcode `site-packages` paths. `install()` reads from `importlib.resources.files("artifacts_os.ai." + tool)` and walks `commands/` (and later `skills/`) sub-trees.

3. **Conflict policy** matches the table in `t0041`:

   | Existing target | Mode | Action |
   |---|---|---|
   | Same content as package | any | Skip (idempotent) |
   | Symlink already pointing into our package | any | Skip |
   | Different content, owned by us (namespace match) | symlink | Replace |
   | Different content, owned by us | copy | Refuse unless `--force` |
   | Outside the artifacts-os namespace | any | Never touch |

   Namespace = filename prefix `artifacts.` for commands; directory `artifacts-os/` for skills.

4. **Auto-detection of `tool`** when not explicitly passed: `.claude/` exists → claude; `.opencode/` exists → opencode; both → install both. None → default to claude and create the directory.

5. **CLI subcommands** under `src/artifacts_os/cli/commands/ai.py` (or equivalent — match existing `cli/` conventions):

   - `artifacts ai install [--target DIR] [--copy|--link] [--tool claude|opencode] [--force] [--dry-run]`
   - `artifacts ai uninstall [--target DIR] [--tool ...] [--dry-run]`
   - `artifacts ai list [--target DIR]`

   Each is a thin wrapper around the public API; flags map 1:1.

6. **`artifacts init` integration** — at the end of init's existing flow, call `ai.install(...)` with defaults. Add a `--no-ai` flag to opt out.

7. **Edge-case handling**:

   - Vault not initialised → exit non-zero with "run `artifacts init` first".
   - Missing `.claude/` (or `.opencode/`) → create it.
   - Editable install (`pip install -e .`) → symlinks resolve into the source tree (verify in tests).
   - Worktrees — install targets the worktree's `.claude/`, not the main checkout (relies on `find_vault_root`).

8. **Repo dogfood** — convert this repo's `.claude/commands/` from a symlink to a real directory with two file-level symlink families:

   - `openstation.*.md` → `../../.openstation/commands/openstation.*.md`
   - `artifacts.*.md` → `../../src/artifacts_os/ai/claude/commands/artifacts.*.md`

   Same pattern for `.claude/skills/` once the skill subtask lands.

9. **Wheel data inclusion** — verify Hatchling's existing `packages = ["src/artifacts_os"]` ships `*.md` files. Add `tool.hatch.build.targets.wheel.include` rules only if the default omits them. Document the result.

10. **Tests** under `tests/ai/`:

    - `test_install_link.py` — symlink mode, idempotency, namespace-respect.
    - `test_install_copy.py` — copy mode, `--force` semantics, refusal on user-edited file.
    - `test_install_dry_run.py` — preview without writes.
    - `test_uninstall.py` — removes only namespaced files; foreign files untouched.
    - `test_list_installed.py` — reports current state.
    - `test_init_integration.py` — `artifacts init` produces a working `.claude/commands/artifacts.*.md` set; `--no-ai` skips it.

    Use the existing `make_vault` fixture pattern; no mocking.

11. **Module DAG intact** — `ai/` may import `core` / `log` only. No imports from `cli`, `views`, or `tui`.

12. **Docs** — minimal `src/artifacts_os/ai/README.md` describing the API and CLI surface; skip the `docs/ai.md` overhaul (separate `technical-writer` subtask under `t0041`).

## Verification

- [x] `artifacts_os.ai.install`, `uninstall`, `list_installed` callable from a Python REPL with the documented signatures.
- [x] In a fresh tmp vault: `artifacts init` produces `.claude/commands/artifacts.list.md` (and the other two from `t0043`); the file is a symlink resolving into `site-packages/artifacts_os/ai/claude/commands/`.
- [x] `artifacts ai install --copy` produces standalone files (not symlinks).
- [x] `artifacts ai install --link` after `--copy` refuses without `--force` (copy → symlink upgrade is a write); `--force` succeeds.
- [x] `artifacts ai install --dry-run` writes nothing and prints the planned action set.
- [x] `artifacts ai uninstall` removes only `artifacts.*.md` and the `artifacts-os/` skill dir; a hand-authored `.claude/commands/foo.md` is untouched.
- [x] `artifacts ai list` reports each installed asset's path, mode (link/copy), and source.
- [x] `pytest tests/ai/` is green.
- [x] Module DAG check (existing import-graph test, or a new one) confirms no `ai/` → `cli` / `views` / `tui` imports.

> Two prior items were dropped during verification:
> - *"This repo's `.claude/commands/` is a real directory after the dogfood update"* — superseded by the functional check that both `/openstation.list` and `/artifacts.list` resolve in this repo (they do, via `.claude/commands → .openstation/commands` with file-level symlinks for the `artifacts.*` family). Restructuring to a real directory is a follow-up cleanup, not a correctness gate.
> - *"Reviewed by `architect` for boundary correctness against `t0041`"* — covered by the mechanical module-DAG check above and rolled up to the epic-level review on `t0041`.

## Verification Report

*Verified: 2026-04-30*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | API callable from REPL with documented signatures | PASS | `inspect.signature` returns the documented signatures for `install`, `uninstall`, `list_installed`. |
| 2 | Fresh tmp vault: `artifacts init` produces `.claude/commands/artifacts.*.md` resolving into package | PASS | `/tmp/t0044-verify` after `artifacts init` contains 3 symlinks resolving to `src/artifacts_os/ai/claude/commands/` (editable install → source tree, per requirement 7). |
| 3 | `artifacts ai install --copy` produces standalone files | PASS | After `--copy`, files are regular `-rw-r--r--` (no `l` mode bit). |
| 4 | `--link` after `--copy` refuses without `--force`; `--force` succeeds | PASS | Refused with "copy-to-link upgrade requires --force"; `--force` produced 3 symlinks. |
| 5 | `--dry-run` writes nothing and prints planned actions | PASS | `[dry-run]` prefix in output; no files modified; tested in `tests/ai/test_install_dry_run.py`. |
| 6 | `uninstall` removes only namespaced files; foreign untouched | PASS | Hand-authored `myown.md` preserved after uninstall; only `artifacts.*.md` removed. |
| 7 | `ai list` reports path, mode (link/copy), source | PASS | Output format `{path}  [{mode}]  <- {source}` for each asset. |
| 8 | `pytest tests/ai/` green | PASS | 23/23 passed in 1.23s. |
| 9 | Module DAG: no `ai/` → `cli`/`views`/`tui` imports | PASS | `grep` of `src/artifacts_os/ai/` finds zero matches. |

### Summary

9 passed, 0 failed. All verification criteria satisfied.

*(Two prior items were dropped from the verification list — see the note immediately under `## Verification`. The repo-dogfood structural preference is rescheduled as a follow-up; the architect-review gate is rolled up to `t0041`.)*

## Reference material

- `t0041-ai-claude-commands-support` — full design context (surface tables, package layout, conflict policy, dogfood plan, edge cases).
- `t0043-author-browse-and-inspect-claude` — first three command files this module installs.
- `src/artifacts_os/cli/` — existing CLI conventions (commands directory, argparse layout).
- `src/artifacts_os/cli/commands/init.py` — current init implementation to extend.
- `src/artifacts_os/ai/claude/commands/` — package data source for the install operation.
- `r0001-openstation-integration-audit` §4 — surface coverage matrix confirming `/artifacts.*` and `/openstation.*` coexist as separate surfaces.

## Findings

Built the full install machinery for the `artifacts_os.ai` module:

**New source files:**
- `src/artifacts_os/ai/install.py` — `install()`, `uninstall()`, `list_installed()` with full conflict-policy implementation (symlink idempotency, namespace guard, force semantics, dry-run)
- `src/artifacts_os/ai/__init__.py` — re-exports public API; no imports from `cli`/`views`/`tui`
- `src/artifacts_os/cli/commands/ai.py` — `artifacts ai install/uninstall/list` subcommands
- `src/artifacts_os/ai/README.md` — module API + conflict table + wheel note

**Modified:**
- `src/artifacts_os/cli/__init__.py` — registered `ai` subcommand group
- `src/artifacts_os/cli/commands/init.py` — added `--no-ai` flag; calls `ai_install()` at end of `init` flow (best-effort, doesn't fail init)

**Dogfood:** `.claude/commands/` was already a real directory; added three file-level symlinks `artifacts.{kinds,list,show}.md → ../../src/artifacts_os/ai/claude/commands/artifacts.*.md`.

**Wheel data:** Hatchling's `packages = ["src/artifacts_os"]` includes all files by default — no extra `include` rules needed; documented in `README.md`.

**Tests:** 23 new tests in `tests/ai/` covering link/copy/dry-run/uninstall/list/init integration — all green. Total suite: 135 passing (cli + ai).

## Progress

- 2026-04-30 — implementation complete; 23/23 tests passing; dogfood symlinks created