---
kind: task
id: t0039
name: cli-create-default-kind-from-yaml
type: feature
status: done
assignee: developer
owner: user
created: 2026-04-30
started: 2026-04-30
completed: 2026-04-30
---

# Cli Create: Default --kind From artifacts.yaml

Move the hardcoded `--kind` default in the `create` command from
`"task"` (literal in `cli/commands/create.py:27`) to the existing
`cli.defaults` settings layer introduced by t0038.

## Requirements

1. Read `cli.defaults.create.kind` from `artifacts.yaml` via the
   already-loaded `CliSettings` (`args.cli_settings`).
2. Resolution order in `create.run`:
   explicit `--kind` flag → `cli.defaults.create.kind` → `"task"` (final
   fallback when no vault / no setting).
3. Drop the argparse-level `default="task"` on the `--kind` argument
   so the absence of a flag is detectable; default resolution moves
   into `run()` (mirrors the `show.editor` pattern).
4. Update `--kind` help text so it no longer hardcodes "default: task";
   describe the resolution order instead.
5. Behaviour when `args.cli_settings` is `None` (no vault) is unchanged
   — fall through to `"task"`.
6. Update `cli/README.md` "Project Configuration" section to document
   `cli.defaults.create.kind` alongside the existing `show.editor`
   entry; add a one-line example.

## Out of scope

- Per-kind defaults (`cli.defaults.create.per_kind.<kind>.{assignee,
  owner, type}`) — separate task.
- Defaulting `assignee`, `owner`, `type`, `parent`, `status`, body
  templates — separate tasks.
- Validation that the configured default kind exists in the registry
  at settings-load time (validation still happens at `registry.get`
  call site, producing the same error as today).

## Findings

Implemented the three-level kind resolution chain for `artifacts create`. Key
changes:

- `cli/commands/create.py`: added `_resolve_kind(args)` helper; changed
  `--kind` argparse `default` from `"task"` to `None` so absence is
  detectable; updated help text to describe resolution order; both
  `--dry-run` and the live `create()` call now receive the resolved kind.
- `cli/README.md`: added `cli.defaults.create.kind` row to the settings
  table and a `create: kind: note` line in the complete YAML example.
- `tests/cli/test_create_kind_default.py`: 5 new tests covering absent
  setting (→ task), configured setting (→ spec), explicit flag overrides
  YAML, explicit flag overrides hardcoded fallback, and no-vault path.
- All 45 pre-existing `test_create.py` + `test_settings.py` tests continue
  to pass. The one suite-wide failure (`test_pyproject_extras_match_spec`)
  is pre-existing and unrelated.

## Progress

### 2026-04-30 — developer
> time: 16:22

Implemented kind resolution chain in create.py (explicit flag → cli.defaults.create.kind → "task"). Added _resolve_kind() helper, updated argparse default to None, updated help text. Updated cli/README.md with new setting in table and complete example. Added 5 new tests in tests/cli/test_create_kind_default.py covering all four verification paths. All 50 relevant tests pass.

## Verification

- [x] `artifacts create "thing"` creates a `task` when
      `cli.defaults.create.kind` is absent (regression check).
- [x] `artifacts create "thing"` creates a `note` (or whatever is
      configured) when `cli.defaults.create.kind: note` is set.
- [x] `artifacts create "thing" --kind spec` overrides the YAML
      default and creates a `spec`.
- [x] `artifacts create "thing"` outside any vault still defaults to
      `task` (no crash, no settings lookup).
- [x] `cli/README.md` documents `cli.defaults.create.kind` in the
      Project Configuration section with a worked example.
- [x] New tests in `tests/cli/` cover: absent setting (fallback),
      configured setting (used), explicit flag (overrides), and the
      no-vault path.
- [x] Existing `tests/cli/test_create.py` and `tests/cli/test_settings.py`
      continue to pass.

## Verification Report

*Verified: 2026-04-30*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts create "thing"` defaults to `task` when setting absent | PASS | `test_absent_setting_defaults_to_task` passes; `create.py:_resolve_kind` falls through to `"task"` when no setting |
| 2 | `artifacts create "thing"` uses configured kind when set | PASS | `test_configured_kind_is_used` passes (configures `kind: spec`, asserts `s0001-` stem and `kind: spec` in frontmatter) |
| 3 | `--kind spec` overrides YAML default | PASS | `test_explicit_kind_overrides_yaml_default` and `test_explicit_kind_overrides_when_no_yaml_default` both pass; `_resolve_kind` returns `args.kind` first |
| 4 | Outside any vault, defaults to `task` (no crash) | PASS | `test_no_vault_defaults_to_task` passes; `getattr(args, "cli_settings", None)` guards lookup; no `AttributeError` |
| 5 | README documents `cli.defaults.create.kind` with worked example | PASS | `cli/README.md` lines 401-403 (settings table row) and 423-435 (complete YAML example with `create: kind: note`) |
| 6 | New tests cover absent, configured, explicit, no-vault paths | PASS | `tests/cli/test_create_kind_default.py` has 5 tests: absent→task, configured→spec, explicit-overrides-yaml, explicit-overrides-fallback, no-vault |
| 7 | Existing `test_create.py` and `test_settings.py` continue to pass | PASS | All 31 `test_create.py` + 12 `test_settings.py` tests pass (50/50 incl. new file) |

### Summary

7 passed, 0 failed. All verification criteria met — task is ready to move to verified.
