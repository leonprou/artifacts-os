---
assignee: developer
created: 2026-05-22
id: t0180
kind: task
name: ship-cli-aliases-as-built
owner: user
status: done
type: implementation
started: 2026-05-24
completed: 2026-05-24
---

## Why

The vault's `cli.aliases` block has proven indispensable in
daily use — `ls`, `sh`, `new`, `st`, `vf`, `va`, `k`, `v` are
now muscle memory. But every new artifacts-os vault starts
without them: the operator either re-authors the same block in
`artifacts.yaml` or stumbles through the full verb names.
Shipping the curated set as **codebase defaults** removes that
papercut so the short aliases work out of the box, while
leaving vault-level `cli.aliases` intact as a customisation
hook.

## Source of truth

- **`artifacts.yaml` (this repo) — `cli.aliases:` block.** The
  set to lift verbatim: `ls→list`, `sh→show`, `new→create`,
  `st→status`, `vf→verify`, `va→validate`, `k→kinds`,
  `v→views`.
- **`src/artifacts_os/cli/settings.py` — `CliSettings`.** Today
  `aliases` defaults to an empty dict; this is where the
  built-in set should originate.
- **`src/artifacts_os/cli/__init__.py` —
  `_load_cli_settings` / `_apply_aliases`.** The call sites
  that must keep working when no vault exists (today aliases
  are silently dropped in that case).
- **`src/artifacts_os/cli/README.md` § Command aliases.**
  User-facing reference must learn about the built-ins and the
  override rule.
- **`tests/cli/test_settings.py`.** Existing alias tests pin
  the current vault-only behaviour and must be extended (not
  weakened) to cover defaults + override.

## Files to touch

| Path | Edit |
|---|---|
| `src/artifacts_os/cli/settings.py` | Declare a `DEFAULT_ALIASES` constant; merge it with the vault's `cli.aliases` (vault wins per key) inside `from_base`. |
| `src/artifacts_os/cli/__init__.py` | Apply built-in aliases even when `_load_cli_settings` returns `None` (no vault / parse error), so a fresh checkout works before `artifacts init` runs. |
| `src/artifacts_os/cli/README.md` | Document the shipped default set and the precedence rule (vault key wins). |
| `tests/cli/test_settings.py` | Add tests for: defaults active with no vault config; vault override replaces a single default; vault adds a new alias alongside defaults. |
| `artifacts.yaml` (this repo) | Remove the now-redundant `cli.aliases:` block once defaults ship — eat our own dogfood. |

## Constraints

- **Vault wins per key.** A vault's
  `cli.aliases.ls: something-else` overrides the built-in
  `ls→list`. Other built-ins remain in effect. Implementation
  detail (merge order, sentinel for "delete a default") is the
  developer's call — pick the simplest rule and document it.
- **Works without a vault.** Aliases must apply even when
  `find_vault_root()` returns `None`, i.e. running
  `artifacts ls` in a non-vault directory should still
  dispatch to `list` (the resulting "not in a vault" error
  from `list` is fine — the alias must resolve first).
- **No new CLI surface.** This is a defaults change, not a
  feature. No new flags, no new commands.
- **Curated set, not the kitchen sink.** Ship exactly the
  eight aliases that have proven their weight in this vault
  (`ls`, `sh`, `new`, `st`, `vf`, `va`, `k`, `v`). Resist the
  urge to invent more.

## Out of scope

- Aliasing flags or sub-arguments — only first-token verb
  aliases.
- Per-kind aliases (e.g. `tasks` as shorthand for
  `list --kind task`) — that lives in views / book pull /
  other tooling.
- Migration tooling for vaults that already define matching
  aliases — the existing per-key override is enough.
- Touching `cli.defaults` (per-command flag defaults) —
  separate concern, not addressed here.

## Test plan

- **`test_default_aliases_applied_without_vault`** — invoke
  `main(["ls"])` outside a vault; assert the parser sees
  `list` and exits with the expected "not in a vault" error
  (proves alias resolution happened pre-argparse, independent
  of vault state).
- **`test_default_aliases_applied_with_empty_vault`** — vault
  with no `cli:` section; assert `main(["sh", "t0001"])`
  dispatches to `show`.
- **`test_vault_override_replaces_default`** — vault declares
  `cli.aliases.ls: status`; assert `main(["ls", ...])` runs
  `status` (vault wins).
- **`test_vault_alias_adds_alongside_defaults`** — vault
  declares a new alias `cli.aliases.x: list`; assert
  `main(["x"])` runs `list` AND `main(["sh", "..."])` still
  runs `show`.
- All existing tests in `tests/cli/test_settings.py` continue
  to pass.

## Requirements

1. The eight aliases currently listed under `cli.aliases:` in
   this repo's `artifacts.yaml` are shipped as codebase
   defaults and work in any vault — and outside any vault —
   without requiring `cli.aliases:` configuration.
2. Vault-level `cli.aliases` continues to be honored, and a
   vault entry with the same key as a default replaces that
   default (vault wins).
3. The shipped default set is exactly: `ls→list`, `sh→show`,
   `new→create`, `st→status`, `vf→verify`, `va→validate`,
   `k→kinds`, `v→views`. No other aliases are added.
4. `src/artifacts_os/cli/README.md` § "Command aliases"
   documents the shipped defaults and the override rule.
5. The `cli.aliases:` block is removed from this repo's
   `artifacts.yaml` (the defaults now cover it).
6. New tests cover the four scenarios in § Test plan;
   existing alias tests in `tests/cli/test_settings.py`
   still pass.
7. `pytest` passes.

## Verification

- [x] `artifacts ls` works in a vault that has no `cli:`
  section.
- [x] `artifacts ls` resolves to `list` even outside any
  vault (failure mode is the existing "not in a vault"
  error, not an argparse unknown-command error).
- [x] A vault that sets `cli.aliases.ls: status` makes
  `artifacts ls` run `status` (vault wins).
- [x] A vault that sets `cli.aliases.x: list` (new alias)
  still has every shipped default active.
- [x] The shipped default set is exactly the eight aliases
  listed in Requirement 3 — verified by inspecting
  `CliSettings`'s default-aliases constant.
- [x] `cli.aliases:` is removed from this repo's
  `artifacts.yaml` and the daily commands (`ls`, `sh`,
  `new`, `st`, `vf`, `va`, `k`, `v`) still work in this
  checkout.
- [x] `src/artifacts_os/cli/README.md` § "Command aliases"
  describes the built-in set and the override rule.
- [x] All new and existing tests in
  `tests/cli/test_settings.py` pass; full `pytest` passes.
- [ ] Reviewed and approved by user.

## Verification Report

*Verified: 2026-05-24*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts ls` works in a vault without `cli:` section | PASS | `test_default_aliases_applied_with_empty_vault` passes; `artifacts ls --kind task -q` returns task names in this repo (cli section has no aliases). |
| 2 | `artifacts ls` resolves to `list` outside any vault | PASS | Verified live: `cd /tmp/empty-dir && artifacts ls` exits with "not in an artifacts-os vault" (the `list` command's vault-not-found path), not argparse error. Test `test_default_aliases_applied_without_vault` confirms exit code 2. |
| 3 | Vault `cli.aliases.ls: status` overrides built-in | PASS | `test_vault_override_replaces_default` exercises this exact scenario; passes. Merge order `{**DEFAULT_ALIASES, **vault_aliases}` in `cli/__init__.py` line 263 ensures vault wins per key. |
| 4 | Vault new alias `cli.aliases.x: list` keeps defaults active | PASS | `test_vault_alias_adds_alongside_defaults` asserts both `x` (new) and `sh` (default) work in the same vault; passes. |
| 5 | Shipped set is exactly the 8 aliases | PASS | `src/artifacts_os/cli/settings.py` lines 16-25 declare `DEFAULT_ALIASES` with exactly `ls→list`, `sh→show`, `new→create`, `st→status`, `vf→verify`, `va→validate`, `k→kinds`, `v→views` — no extras. |
| 6 | `cli.aliases:` removed from repo `artifacts.yaml`; dailies still work | PASS | `artifacts.yaml` `cli:` section contains only `defaults:` (lines 146-151), no `aliases:` key. Live test: `artifacts ls --kind task -q` and `artifacts sh t0180 -j` both succeed. |
| 7 | README documents built-ins and override rule | PASS | `cli/README.md` lines 1153-1178 contain "Command aliases" section with a built-in table (8 rows) and "Override rule — vault wins per key" with an example. |
| 8 | All tests pass | PASS | `pytest tests/cli/test_settings.py` → 17 passed. Full `pytest` → 1156 passed, 1 skipped. |
| 9 | Reviewed and approved by user | FAIL | Pending user review. |

### Summary

8 passed, 1 failed (user approval pending). All technical
verification criteria pass; only the final user-approval gate
remains.

## Findings

Shipped the eight built-in aliases (`ls`, `sh`, `new`, `st`, `vf`, `va`, `k`, `v`) as codebase defaults.

**Design decision**: `DEFAULT_ALIASES` is declared in `settings.py` (as specified), but the merge with vault aliases happens in `_run()` in `__init__.py` rather than inside `from_base`. This keeps `CliSettings.aliases` storing only the vault-provided overrides, which lets all existing unit tests on `CliSettings.aliases` pass without modification. The effective merged aliases `{**DEFAULT_ALIASES, **vault_aliases}` are computed at dispatch time — vault wins per key.

**Changes made**:
- `src/artifacts_os/cli/settings.py`: Added `DEFAULT_ALIASES` module-level constant with the 8 curated aliases.
- `src/artifacts_os/cli/__init__.py`: Updated `_run` to always apply `{**DEFAULT_ALIASES, **vault_aliases}` instead of only applying vault aliases when a vault exists. Imported `DEFAULT_ALIASES`.
- `src/artifacts_os/cli/README.md`: Rewrote the "Command aliases" section to document the built-in set as a table and explain the vault-wins-per-key override rule.
- `tests/cli/test_settings.py`: Added 4 new tests covering all scenarios from the test plan. All 17 tests pass.
- `artifacts.yaml`: Removed the `cli.aliases:` block. Daily aliases (`ls`, `sh`, etc.) still work via the built-in defaults.

`pytest` result: 1156 passed, 1 skipped.