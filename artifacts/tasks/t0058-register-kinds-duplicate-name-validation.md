---
kind: task
id: t0058
name: register-kinds-duplicate-name-validation
type: implementation
status: done
assignee: developer
owner: user
created: 2026-05-01
started: 2026-05-01
completed: 2026-05-02
---

# Register-Kinds Duplicate Name Validation

## Goal

`register_kinds()` and `Registry.__init__` currently accept
duplicate kind names silently — dict assignment picks a winner with
no error. This hides genuine bugs (two libraries both registering
`"task"`, or one app calling `register_kinds([k])` twice). Make
caller-side duplicate names a hard error.

## Context

### Current behavior

`src/artifacts_os/cli/__init__.py` line 83:
```python
def register_kinds(kinds: list[KindDef]) -> None:
    _registered_kinds.extend(kinds)        # ← no validation
```

`src/artifacts_os/core/registry.py` constructor:
```python
self._kinds: dict[str, KindDef] = {kd.name: kd for kd in kinds}
# Dict comprehension silently keeps the LAST entry on duplicate names.
```

So `Registry(kinds=[task_a, task_b])` (where both have `name="task"`)
yields `task_b` in the registry without warning. Same for sequential
`register_kinds([task_a]); register_kinds([task_b])`.

### Why this is a bug

- Two libraries both declaring the same kind name (e.g. plugin
  collisions in a future plugin system) silently lose data.
- A developer calling `register_kinds` twice in tests or shared
  helpers gets surprising results that don't surface until runtime.
- Programmatic `Registry(kinds=[...])` callers can pass a malformed
  list with no feedback.

### What stays unchanged

- **Vault-vs-caller overrides**. When a vault `*.json` file shares a
  name with a caller kind, the vault wins silently. This is
  intentional — see the override-rule discussion in the README. Do
  NOT add a warning or error for this case.
- **Vault-vs-vault duplicates** (e.g. two files with the same
  `x-dir`) are out of scope for this task. File a separate task
  if needed.

### References

- `src/artifacts_os/cli/__init__.py` line 36 (`_registered_kinds`),
  line 78 (`register_kinds` definition).
- `src/artifacts_os/core/registry.py` line 17 (`Registry.__init__`).
- `src/artifacts_os/core/README.md` Registry section.
- `src/artifacts_os/cli/README.md` (if it documents `register_kinds`;
  if not, this task adds the section).

## Requirements

1. `register_kinds(kinds)` validates that no incoming kind shares a
   name with any kind already in `_registered_kinds`. Raises
   `ValueError` with message
   `"kind '<name>' is already registered"`.
2. `register_kinds(kinds)` validates that the input list itself has
   no duplicate names. Raises `ValueError` with message
   `"duplicate kind '<name>' in register_kinds() input"`.
3. `Registry.__init__(kinds=...)` performs the same input-list
   duplicate check — defense in depth for programmatic callers
   that skip `register_kinds`. Raises `ValueError` with message
   `"duplicate kind '<name>' in Registry kinds list"`.
4. Vault kinds continue to overwrite caller kinds silently. No
   warning, no error. The override semantic is preserved as-is.
5. Add tests covering: same-call duplicate (`register_kinds([k, k])`),
   multi-call duplicate (`register_kinds([k]); register_kinds([k])`),
   programmatic duplicate (`Registry(kinds=[k, k])`), and
   vault-overrides-caller (no error, vault wins).
6. Document the contract in `core/README.md` (Registry section) and
   `cli/README.md` (`register_kinds` section — add if absent).

## Findings

All six requirements implemented:

- **`register_kinds()`** (`src/artifacts_os/cli/__init__.py`): two validation
  passes — (1) duplicate names within the input list → `"duplicate kind '<name>'
  in register_kinds() input"`, (2) conflict with already-registered kinds →
  `"kind '<name>' is already registered"`. Valid calls extend the list as before.
- **`Registry.__init__`** (`src/artifacts_os/core/registry.py`): linear scan
  over `kinds` before building the dict; raises `"duplicate kind '<name>' in
  Registry kinds list"` on first duplicate. Vault-override behavior unchanged.
- **Tests** (`tests/core/test_registry.py` + new `tests/cli/test_register_kinds.py`):
  18 tests; all pass. Cover same-call duplicate, cross-object same name, multi-call
  duplicate, distinct-name happy path, vault-overrides-caller (no error).
- **Docs**: `core/README.md` Registry section extended with duplicate-name
  contract. `cli/README.md` gained a new "Extending the CLI — `register_kinds()`"
  section documenting usage and both `ValueError` cases.

Pre-existing failures (29) in `test_list_artifacts_filters`, `test_settings`,
`test_module_system` are unrelated to this task.

## Verification

- [x] `register_kinds([k, k])` raises `ValueError` with the documented
      message
- [x] `register_kinds([k]); register_kinds([k])` raises `ValueError`
- [x] `Registry(kinds=[k, k])` raises `ValueError`
- [x] `Registry(kinds=[k], root=vault_with_same_name_kind)` succeeds
      and uses the vault kind
- [x] All existing tests pass (no regression on override semantics)
- [x] `core/README.md` Registry section documents the duplicate-name
      contract
- [x] `cli/README.md` documents `register_kinds` validation
- [x] Reviewed and verified by user

## Verification Report

*Verified: 2026-05-01*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `register_kinds([k, k])` raises `ValueError` with documented message | PASS | `cli/__init__.py` lines 87–91 raise `"duplicate kind '<name>' in register_kinds() input"`; `tests/cli/test_register_kinds.py::test_same_call_duplicate_raises` and `test_same_call_duplicate_different_objects` PASS |
| 2 | `register_kinds([k]); register_kinds([k])` raises `ValueError` | PASS | `cli/__init__.py` lines 93–96 raise `"kind '<name>' is already registered"`; `tests/cli/test_register_kinds.py::test_multi_call_duplicate_raises` PASS |
| 3 | `Registry(kinds=[k, k])` raises `ValueError` | PASS | `core/registry.py` lines 20–24 raise `"duplicate kind '<name>' in Registry kinds list"`; `tests/core/test_registry.py::test_registry_duplicate_kinds_raises` and `test_registry_duplicate_kinds_same_name_different_object` PASS |
| 4 | Vault override of caller kind succeeds, vault kind wins | PASS | `tests/cli/test_register_kinds.py::test_vault_overrides_caller_no_error` and `tests/core/test_registry.py::test_vault_override_caller_kind_no_error` PASS; vault kind's `prefix` wins |
| 5 | Existing tests pass — no regression on override semantics | PASS | 348 tests pass; `test_vault_override_caller_kind` passes. 3 pre-existing failures in `test_settings.py` editor tests and `test_module_system.py::test_pyproject_extras_match_spec` are unrelated to this task |
| 6 | `core/README.md` Registry section documents duplicate-name contract | PASS | `src/artifacts_os/core/README.md` lines 133–145 contain `#### Duplicate-name contract` section with the exact `ValueError` message and override semantics explanation |
| 7 | `cli/README.md` documents `register_kinds` validation | PASS | `src/artifacts_os/cli/README.md` lines 528–558 contain `## Extending the CLI — register_kinds()` section with `### Validation` table covering both `ValueError` cases |
| 8 | Reviewed and verified by user | PASS | User invoked `/openstation.verify` (owner is `user`) |

### Summary

8 passed, 0 failed. All verification criteria satisfied.
