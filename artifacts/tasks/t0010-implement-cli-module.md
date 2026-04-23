---
kind: task
id: t0010
name: implement-cli-module
type: implementation
status: done
assignee: developer
owner: user
depends_on:
  - "[[t0009-implement-views-module]]"
created: 2026-04-22
started: 2026-04-22
completed: 2026-04-23
---

# Implement Cli Module

## Requirements

Implement `src/artifacts_os/cli/` per `artifacts/specs/s0003-artifacts-os-cli-module.md`.

Depends on `t0009` (views module) — do not start until views is done.

### Entry point

```toml
# pyproject.toml (already present)
[project.scripts]
artifacts = "artifacts_os.cli:main"
```

```python
# src/artifacts_os/cli/__init__.py
def main() -> None: ...
```

### Command set

| Command | Synopsis |
|---------|----------|
| `list` | `list [--kind KIND] [--status S] [--fields F] [-q\|-j]` |
| `show` | `show <ref> [--kind KIND] [-j\|-e]` |
| `create` | `create <title> [--kind KIND] [--body B] [--fields F]` |
| `status` | `status <ref> <new-status>` |
| `verify` | `verify [<ref>] [--kind KIND] [--all] [-j]` |
| `agents` | `agents [--show <name>] [-q\|-j\|-e]` |

Omit `--view` flag for now — depends on `ViewConfig`/`load_views` which are
still deferred.

### Structure

Each command lives in its own module:

```
src/artifacts_os/cli/
  __init__.py       # main(), argument parser setup, subparser registration
  commands/
    list.py
    show.py
    create.py
    status.py
    verify.py
    agents.py
```

### Argument parsing

Use stdlib `argparse` only. No `click` or `typer`.

### Output modes

- Default: `views.render_table` printed via `rich.Console`
- `-q` / `--quiet`: one name per line to stdout
- `-j` / `--json`: JSON array/object to stdout

### `register_kinds` hook

```python
def register_kinds(kinds: list[KindDef]) -> None:
    """Called by host app before main() dispatches. Stores kinds for Registry construction."""
```

`cli` calls `find_vault_root()` at startup; exits code 2 with
`"error: not in an artifacts-os project"` if not found.
`Registry` is constructed once per invocation from vault root + registered kinds.

### Error handling

| Exception | Exit code |
|-----------|-----------|
| `NotFoundError` | 3 |
| `AmbiguousError` | 4 |
| `ValidationError` | 2 |
| `ValueError` (bad args) | 1 |

Errors go to stderr. Exit codes are checked by tests.

### Tests

Add `tests/cli/`. Use `tmp_path` + `make_vault` fixture.
Cover happy path and error exits for each command.
No mocking — invoke `main()` via `subprocess` or directly with patched `sys.argv`.

## Progress

### 2026-04-22 23:36:11 — Incomplete run (r0006)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$1.00, turns=46

### 2026-04-23 — Resumed and completed

Implemented all six commands per spec. All 35 CLI tests pass; full
suite (119 tests) green. Smoke-tested the installed `artifacts`
entry point end-to-end.

## Findings

Built `src/artifacts_os/cli/` as a thin dispatcher over `core` and
`views`. No lifecycle logic lives in `cli` — status changes go
through `core.update`.

### What was built

- `src/artifacts_os/cli/__init__.py` — `main(argv=None)` entry point,
  `register_kinds(kinds)` hook, argparse setup, error→exit-code mapping.
- `src/artifacts_os/cli/commands/` — one module per subcommand:
  `list.py`, `show.py`, `create.py`, `status.py`, `verify.py`,
  `agents.py`. Each exposes `register(subparsers)` and `run(args, registry)`.
- `tests/cli/` — 35 tests covering happy paths and every documented
  exit code (1/2/3/4) across the six commands.

### Key design decisions

- **`main()` signature:** accepts optional `argv` param for direct
  testability (`main(["list", "-q"])`) and only calls `sys.exit()`
  on non-zero codes so successful calls return cleanly.
- **Vault discovery up-front:** `find_vault_root()` runs before
  argparse. Missing root → exit 2 with the spec-mandated message.
- **`register_kinds` hook:** appends to a module-level
  `_registered_kinds` list; `Registry(_registered_kinds, root=root)`
  at each invocation merges with vault-defined kinds.
- **Verify exit code:** `verify` returns exit 1 when any checklist
  item is unchecked, regardless of output mode (plain or `-j`).
  This lets CI wire it in directly.
- **Test isolation without mocking:** `tests/cli/conftest.py`
  builds a real vault under `tmp_path` with JSON schemas in
  `openstation/types/`, then `monkeypatch.chdir(root)` +
  `monkeypatch.setattr` on `_registered_kinds` — no mocks of
  `core` or `find_vault_root`.

### Gotchas

- `list`/`verify` import the file as `artifacts_os.cli.commands.list`
  — Python builtin `list` is only shadowed inside that module,
  and the parent `cli/__init__.py` aliases it (`as _list_cmd`).
- `show -e`, `agents --show ... -e`: shell out via `subprocess.run`
  to `$EDITOR` (default `vi`). Not covered by automated tests
  since it launches an interactive process.
- `write_artifact` is a **fixture**, not a helper import —
  pytest's collection doesn't put `tests/` on `sys.path` so
  `from tests.cli.conftest import ...` fails.

### Files

- `src/artifacts_os/cli/__init__.py`
- `src/artifacts_os/cli/commands/__init__.py`
- `src/artifacts_os/cli/commands/{list,show,create,status,verify,agents}.py`
- `tests/cli/__init__.py`
- `tests/cli/conftest.py`
- `tests/cli/test_{list,show,create,status,verify,agents}.py`

## Downstream

- `--view` flag omitted per spec (depends on deferred
  `ViewConfig`/`load_views`). Add when views config lands.
- `run`, `logs`, `sessions` commands deferred per the spec
  (need `ai` and `log` modules first).

## Verification

- [x] `artifacts list`, `show`, `create`, `status`, `verify`, `agents` all work end-to-end
- [x] Default output uses `views.render_table`; `-q` and `-j` modes work
- [x] Exit codes match the error handling table
- [x] `register_kinds` hook documented and functional
- [x] `pytest tests/cli/` passes
- [x] No lifecycle logic in `cli` (status transitions go through `core.update`)

## Verification Report

*Verified: 2026-04-23*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | All 6 commands work end-to-end | PASS | 35 tests pass (test_list, test_show, test_create, test_status, test_verify, test_agents); all command modules exist |
| 2 | Default output uses `views.render_table`; `-q` and `-j` modes work | PASS | `list.py`, `show.py`, `agents.py` all call `views.render_table`; `-q` prints names, `-j` dumps JSON; covered by tests |
| 3 | Exit codes match error handling table | PASS | `__init__.py` maps `NotFoundError→3`, `AmbiguousError→4`, `ValidationError→2`, `ValueError→1`; test files assert correct exits |
| 4 | `register_kinds` hook documented and functional | PASS | `register_kinds()` in `__init__.py` has docstring, appends to `_registered_kinds`, used in `Registry` construction per invocation |
| 5 | `pytest tests/cli/` passes | PASS | 35 passed in 0.31s, zero failures |
| 6 | No lifecycle logic in `cli` | PASS | `status.py` delegates entirely to `core.update(registry, ref, status=…)` |

### Summary

6 passed, 0 failed. All verification criteria satisfied.
