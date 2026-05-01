---
kind: task
id: t0038
name: cli-settings-per-command-defaults
type: feature
status: done
assignee: developer
owner: user
created: 2026-04-30
started: 2026-04-30
completed: 2026-04-30
aliases: []
tags: []
---

# Cli Settings: Per-Command Defaults And Aliases

## Requirements

1. Define `CliSettings(Settings)` in `src/artifacts_os/cli/` with `from_base` reading the `cli` top-level key from `base.raw`.
2. Support `cli.defaults.show.editor: true` — when set, `show` behaves as if `-e` was passed unless the user explicitly passes `-j`.
3. Support `cli.aliases` dict — remap command names before argparse sees `argv`. Example: `ls: list`, `t: status`.
4. Load `CliSettings` in `_run` (after `find_vault_root`, before dispatch); pass defaults to commands that need them.
5. Aliases and defaults are silently ignored when no `artifacts.yaml` is found (e.g., running `init`).

## Findings

`CliSettings(Settings)` was added to `src/artifacts_os/cli/settings.py` following the existing `ViewsSettings.from_base` pattern. It reads the `cli.defaults` and `cli.aliases` keys from `base.raw`, returning empty dicts when the section is absent.

`_run` in `cli/__init__.py` now calls `find_vault_root()` before argparse so aliases can be remapped before argument parsing. A `_load_cli_settings` helper silently returns `None` on any error (missing vault, missing `project` section, etc.), satisfying requirement 5. The resulting `CliSettings` instance is attached to `args` before dispatch, making it available to all commands.

`show.py` checks `args.cli_settings.defaults.get("show", {}).get("editor")` after the `-j` early return, so JSON output always takes precedence over the editor default.

13 new tests in `tests/cli/test_settings.py` cover unit-level `from_base` parsing, the editor-default integration path, the JSON-override path, alias dispatch to `list` and `status`, and the argparse-error fallthrough for unknown commands. All 200 existing tests continue to pass.

`src/artifacts_os/cli/README.md` gained a new **Project Configuration** section documenting `cli.defaults`, `cli.aliases`, and a full worked example.

## Progress

### 2026-04-30 — developer
> time: 00:22

Implemented CliSettings.from_base, alias remapping in _run, show editor default, 13 new tests (all passing), and README documentation for the cli YAML section.

## Verification

- [x] `CliSettings.from_base` parses `cli.defaults` and `cli.aliases` from `artifacts.yaml`; returns sensible defaults when section is absent
- [x] `artifacts show <ref>` opens `$EDITOR` without `-e` when `cli.defaults.show.editor: true` is set; explicit `-j` still overrides
- [x] `artifacts ls` dispatches to `list` when `cli.aliases.ls: list` is configured
- [x] Unknown aliases are ignored gracefully (no crash, falls through to argparse error)
- [x] `cli/README.md` documents the `cli` YAML section with a worked example
- [x] Tests in `tests/cli/` cover settings load, alias remapping, and default flag behaviour

## Verification Report

*Verified: 2026-04-30*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `CliSettings.from_base` parses `cli.defaults`/`cli.aliases`; sensible defaults when absent | PASS | `src/artifacts_os/cli/settings.py` defines `CliSettings(Settings)` with `from_base`; uses `base.raw.get("cli") or {}` for safe absence handling. Tests `test_from_base_empty_section`, `test_from_base_parses_defaults`, `test_from_base_parses_aliases`, `test_from_base_partial_cli_section` all pass. |
| 2 | `show` opens `$EDITOR` when `cli.defaults.show.editor: true`; `-j` overrides | PASS | `cli/commands/show.py:34-43` reads `args.cli_settings.defaults.get("show")` only after the `-j` early-return at line 27-30. Tests `test_show_editor_default_opens_editor` and `test_show_json_overrides_editor_default` pass. |
| 3 | `artifacts ls` dispatches to `list` via `cli.aliases.ls: list` | PASS | `cli/__init__.py:52-57` `_apply_aliases` rewrites `argv[0]` before argparse. Test `test_alias_dispatches_to_list` (and `test_alias_dispatches_to_status` for `t → status`) pass. |
| 4 | Unknown aliases fall through to argparse error gracefully | PASS | When alias does not match, `_apply_aliases` returns argv unchanged; argparse then exits 2. Tests `test_unknown_command_falls_to_argparse_error` and `test_no_aliases_configured_unknown_command_exits_2` pass. Also `_load_cli_settings` returns `None` on missing vault (lines 38-49). |
| 5 | `cli/README.md` documents `cli` YAML section with worked example | PASS | `src/artifacts_os/cli/README.md` lines 385-435 contain a "Project Configuration (`cli` section)" heading covering per-command defaults, command aliases, and a complete YAML example. |
| 6 | Tests in `tests/cli/` cover settings load, alias remapping, and default flag behaviour | PASS | `tests/cli/test_settings.py` contains 13 tests (all passing): 5 unit tests for `from_base`, 4 integration tests for the editor default & JSON override, and 4 alias-dispatch / unknown-command tests. |

### Summary

6 passed, 0 failed. All verification criteria are met.

Note: A single unrelated failure exists in `tests/test_module_system.py::test_pyproject_extras_match_spec` (asserts `rich` in the `views` extras of `pyproject.toml`). This is pre-existing and outside the scope of t0038, which did not touch `pyproject.toml`.
