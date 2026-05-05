---
assignee: developer
created: 2026-05-05
id: t0096
kind: task
name: ship-artifacts-os-skill-md
owner: user
parent: '[[t0095-ship-artifacts-os-skill-via]]'
status: done
type: implementation
---

## Goal

Make `pip install artifacts-os && artifacts init` produce a working
`<vault>/.claude/skills/artifacts-os/SKILL.md` with no further user
action. Vault-local only — no pip postinstall hook, no user-global
install.

## Context

- `t0044` already shipped `src/artifacts_os/ai/install.py` with
  symlink-default install for `commands/`. It is invoked
  automatically at the end of `artifacts init` (see
  `src/artifacts_os/cli/commands/init.py`, the `if not getattr(args, "no_ai", False):` block).
- The skill content currently lives **out-of-tree** at
  `~/.claude/skills/artifacts-os/SKILL.md`. It must move into the
  package so it rides the wheel.
- `install.py` today walks only `artifacts_os.ai.{tool}.commands`;
  it has no concept of skills. Generalise it.
- The wheel target is Hatchling `packages = ["src/artifacts_os"]`.
  Verify `*.md` under the new `skills/` sub-tree is included; if
  not, add a `tool.hatch.build.targets.wheel.include` rule.

## Requirements

### 1. Author SKILL.md into the package

- Copy `~/.claude/skills/artifacts-os/SKILL.md` verbatim to:
  `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`
- Add empty `__init__.py` files at:
  - `src/artifacts_os/ai/claude/skills/__init__.py`
  - `src/artifacts_os/ai/claude/skills/artifacts-os/__init__.py`
  (so `importlib.resources.files` can locate the tree).
- Do not edit content — exact byte-for-byte port.

### 2. Generalise `install.py` to handle skills

Extend the existing module without breaking command behaviour:

- Add an asset-kind concept: `commands` (filename-namespaced,
  prefix `artifacts.`) and `skills` (directory-namespaced, dir
  name `artifacts-os`). Internal enum or two small predicates —
  whatever reads cleanest.
- New source walker: enumerate `artifacts_os.ai.{tool}.skills`
  sub-directories; treat each immediate sub-directory whose name
  is namespaced (`artifacts-os`) as one installable unit. For
  this iteration, "unit" = the single `SKILL.md` file inside
  it. **Do not** symlink the whole directory — symlink the
  individual file at `<tool_dir>/skills/artifacts-os/SKILL.md`.
  Rationale: keeps namespace ownership at file granularity (same
  as commands), avoids surprising users who put their own files
  next to ours.
- The conflict policy is identical to commands: same-content skip,
  symlink-already-points-to-package skip, owned symlink replace,
  owned copy refuse without `--force`, foreign keep.
- `install()`, `uninstall()`, and `list_installed()` must all
  cover skills in addition to commands. `uninstall()` removes the
  namespaced skill files **and** prunes the now-empty
  `<tool_dir>/skills/artifacts-os/` directory if empty (do not
  remove if it contains foreign files).
- `list_installed()` returns one `InstalledAsset` per installed
  file, regardless of whether it's a command or a skill. `mode`
  reflects file-level link vs copy.

### 3. `artifacts init` integration — no signature change

`init`'s existing call to `ai_install(target, mode="link", dry_run=False)`
must remain unchanged; the install module's broader walk picks up
the skill automatically. Verify this end-to-end in a test.

### 4. Wheel data inclusion

- Run `pip wheel . -w /tmp/aos-wheel` (or `hatch build`) and
  inspect the resulting wheel for
  `artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`. If
  missing, add to `pyproject.toml`:
  ```toml
  [tool.hatch.build.targets.wheel]
  include = ["src/artifacts_os/**/*.md"]
  ```
  (or the minimal rule that captures it without overcollecting).

### 5. Tests under `tests/ai/`

Mirror the existing command-install test patterns:

- `test_install_skills.py` — fresh vault → `init` →
  `<vault>/.claude/skills/artifacts-os/SKILL.md` exists, is a
  symlink, resolves into the package source.
- `test_install_skills_copy.py` — `mode="copy"` produces a
  regular file with identical content.
- `test_uninstall_skills.py` — removes the SKILL.md and prunes
  the empty `artifacts-os/` dir; foreign sibling files (if any)
  cause the dir to be retained.
- `test_list_installed_skills.py` — reports the skill alongside
  any installed commands.
- `test_install_dry_run_skills.py` — preview without writes.
- Extend `test_init_integration.py` (or its equivalent) to
  assert the SKILL.md is present after `artifacts init` in a
  fresh tmp dir, and absent after `init --no-ai`.

### 6. Repo dogfood

Once 1-5 land:

- This repo's `.claude/skills/` (create if absent) should contain
  a file-level symlink:
  `.claude/skills/artifacts-os/SKILL.md` →
  `../../../src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`
- This is what `artifacts ai install` would produce; doing it by
  hand here proves the layout works for editable installs.

### 7. Documentation touch-ups

- Update `src/artifacts_os/ai/README.md` to mention skills
  alongside commands (one short section).
- Update the section of `docs/` (if any) that describes what
  `init` installs. If no such doc exists, no new doc required.

## Out of scope

- The other six unfinished commands from `t0041`.
- User-global install (`~/.claude/skills/`).
- pip postinstall hooks.
- New CLI flags (`--scope`, `--skill-only`, etc.).
- Authoring new skill content — port the existing one as-is.
- Multi-tool work beyond what `install.py` already supports
  (`opencode` symmetry comes for free if the existing code does
  it for commands; do not add new tool support).

## Verification

- [ ] `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` exists and matches `~/.claude/skills/artifacts-os/SKILL.md` byte-for-byte.
- [ ] `pip install -e .` followed by `artifacts init` in a fresh tmp dir produces `<tmp>/.claude/skills/artifacts-os/SKILL.md` as a symlink resolving into the package source.
- [ ] `artifacts init --no-ai` produces no `.claude/skills/` directory.
- [ ] `artifacts ai install --copy` in an existing vault produces a regular-file copy at the same path.
- [ ] `artifacts ai install --dry-run` previews skill action; no files written.
- [ ] `artifacts ai uninstall` removes the SKILL.md and the empty `artifacts-os/` directory.
- [ ] `artifacts ai list` reports the skill.
- [ ] Built wheel (`pip wheel .`) contains `artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`.
- [ ] All new tests under `tests/ai/` pass; existing `tests/ai/` suite still green.
- [ ] Module DAG intact: no new cross-module imports introduced.
- [ ] Repo's `.claude/skills/artifacts-os/SKILL.md` symlink exists and resolves.
- [ ] `src/artifacts_os/ai/README.md` mentions skills.