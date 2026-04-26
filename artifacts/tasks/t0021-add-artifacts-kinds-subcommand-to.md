---
kind: task
id: t0021
name: add-artifacts-kinds-subcommand-to
type: implementation
status: verified
assignee: developer
owner: project-manager
depends_on:
  - "[[t0020-rename-artifacts-types-to-artifacts]]"
created: 2026-04-26
summary: >
  Add an `artifacts kinds` CLI subcommand that lists every kind
  registered with the active Registry, mirroring the formatting
  options of `artifacts list`.
started: 2026-04-26
---

# Add `artifacts kinds` Subcommand to CLI

## Background

Today there is no first-class way to discover which kinds are
registered in a project. Users must either `ls artifacts/kinds/`
(filesystem) or already know a kind name to run
`artifacts list -k <kind>`. The CLI help advertises the kinds it
knows in `--kind`'s `choices` only for `create`, and only for the
built-in kinds — vault-defined kinds are invisible to the user.

Adding a `kinds` subcommand closes the discovery loop: kinds are
the foundation of the storage layer, and a kind-agnostic CLI should
expose them as plainly as it exposes artifacts.

This task is unblocked by t0020, which finalizes the directory
name and terminology so this command and its tests can be written
against the settled contract.

---

## Requirements

### 1. New command module

Create `src/artifacts_os/cli/commands/kinds.py` following the same
shape as `list.py`:

- `register(subparsers)` — registers a `kinds` subparser
- `run(args, registry: Registry) -> int` — executes the command

Flags:

| Flag | Behavior |
|------|----------|
| `-q`, `--quiet` | One kind name per line, sorted alphabetically. Mutually exclusive with `-j`. |
| `-j`, `--json` | JSON array of `{name, dir, prefix, numbered, statuses}` objects. Mutually exclusive with `-q`. |
| (default) | Rich table with columns: `name`, `dir`, `prefix`, `numbered`, `statuses`. Sorted by `name`. |

Source data: `registry.all()` — this already merges caller-provided
and vault-defined kinds, so vault customizations show up
automatically.

### 2. Wire it up

In `src/artifacts_os/cli/__init__.py`:

- `from artifacts_os.cli.commands import kinds as _kinds_cmd`
- Add `_kinds_cmd.register(subparsers)` in `_build_parser()`
  alongside the other `register(...)` calls.

The command runs **after** vault/registry setup (it needs the
Registry), so no `_pre_registry` flag is required.

### 3. Output format details

**Default (rich table):**

```
  name        dir        prefix   numbered   statuses
  ────────────────────────────────────────────────────────────────
  agent       agents     (none)   no         (none)
  research    research   r        yes        draft, published
  spec        specs      s        yes        draft, accepted
  task        tasks      t        yes        backlog, ready, ...
```

- Empty `prefix` renders as `(none)` (dim).
- Empty `statuses` list renders as `(none)` (dim).
- `numbered` renders as `yes` / `no`.
- Use `rich.table.Table` and `rich.console.Console`, the same
  primitives already used by `views.render_table`.

**`-q` (quiet):** one name per line, no header, sorted.

**`-j` (json):** `print(json.dumps(payload, default=str))` — a list
of objects, one per kind. Field order: `name`, `dir`, `prefix`,
`numbered`, `statuses`. Do not include `schema` or `meta` (those
are implementation details).

### 4. Tests

Create `tests/cli/test_kinds.py`. Use the `make_vault` fixture
in `tests/cli/conftest.py`. Cases:

1. **Default kinds visible** — fresh vault from `make_vault` with
   the standard four kinds. `artifacts kinds -q` prints all four
   names sorted (`agent`, `research`, `spec`, `task`).
2. **JSON output** — `artifacts kinds -j` produces a list of four
   dicts; each dict has exactly the keys `name`, `dir`, `prefix`,
   `numbered`, `statuses`; values match the registered `KindDef`s.
3. **Custom vault kind appears** — drop a `changelog.json` schema
   into `artifacts/kinds/` (use the same pattern as
   `tests/core/test_registry.py::_write_schema`). `artifacts kinds -q`
   includes `changelog`.
4. **Vault override** — register a caller-provided kind with the
   same name as a vault file; verify the vault definition wins
   (matches existing registry semantics; see s0002 § registry).
5. **Mutually exclusive flags** — `artifacts kinds -q -j` exits
   non-zero with argparse's standard error.

Do not add a default-table snapshot test — the rich rendering is
exercised implicitly by `-q` and `-j` covering the data, and the
table is purely cosmetic.

### 5. Help text

- Subparser `help`: `"list registered kinds"`
- Subparser `description`: `"List all artifact kinds registered with the active project, including any vault-defined kinds under artifacts/kinds/."`

---

## Out of Scope

- Showing the full JSON Schema for a kind. If desired later, file a
  separate `artifacts kinds show <name>` task.
- Validating kind schemas at list time — that is `validate`'s job.
- Editing or registering kinds via the CLI.

---

## Progress

### 2026-04-26 — developer

Implemented artifacts kinds subcommand: created src/artifacts_os/cli/commands/kinds.py, wired into cli/__init__.py, added spec kind to cli conftest, wrote 5 tests in tests/cli/test_kinds.py. All 150 tests pass.

---

## Verification

- [x] `artifacts kinds` (no flags) prints a rich table with columns `name`, `dir`, `prefix`, `numbered`, `statuses`, sorted by name
- [x] `artifacts kinds -q` prints one kind name per line, sorted, no header
- [x] `artifacts kinds -j` prints a JSON array; each object has exactly `name`, `dir`, `prefix`, `numbered`, `statuses` (no `schema`, no `meta`)
- [x] `artifacts kinds -q -j` is rejected by argparse (mutually exclusive)
- [x] Vault-defined kinds (dropped into `artifacts/kinds/*.json`) appear in the output
- [x] A caller-registered kind with the same name as a vault kind is overridden by the vault kind, matching existing Registry semantics
- [x] Subcommand appears in `artifacts --help`
- [x] `pytest tests/cli/test_kinds.py` passes
- [x] `pytest` — full suite still passes
- [x] Implementation depends only on `Registry.all()` — no direct filesystem scanning in the command code

## Verification Report

*Verified: 2026-04-26*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Rich table with correct columns, sorted by name | PASS | `kinds.py` lines 49-62: `Table` with 5 columns, `sorted(registry.all(), key=lambda kd: kd.name)` |
| 2 | `-q` prints one name per line, sorted, no header | PASS | `kinds.py` lines 29-31; `test_kinds_quiet_default_four` passes |
| 3 | `-j` produces JSON array with exactly the 5 required keys | PASS | `kinds.py` lines 34-46; `test_kinds_json_output` verifies key set and values |
| 4 | `-q -j` mutually exclusive, non-zero exit | PASS | `add_mutually_exclusive_group()` in `kinds.py` line 20; `test_kinds_mutually_exclusive_flags` passes |
| 5 | Vault-defined kinds appear in output | PASS | `test_kinds_custom_vault_kind_appears` writes `changelog.json` and confirms it in output |
| 6 | Vault kind overrides caller-registered kind of same name | PASS | `test_kinds_vault_overrides_caller_kind` confirms `dir="tasks"` (vault) over `dir="caller-tasks"` (caller) |
| 7 | Subcommand in `artifacts --help` | PASS | `artifacts --help` output: `kinds     list registered kinds` |
| 8 | `pytest tests/cli/test_kinds.py` passes | PASS | 5/5 tests passed in 0.16s |
| 9 | Full suite still passes | PASS | 150 passed in 0.53s |
| 10 | No direct filesystem scanning in command code | PASS | `kinds.py` uses only `registry.all()` — no `Path`, `os`, or `glob` imports |

### Summary

10 passed, 0 failed. All verification criteria met.
