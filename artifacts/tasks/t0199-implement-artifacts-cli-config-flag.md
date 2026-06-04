---
kind: task
id: t0199
name: implement-artifacts-cli-config-flag
type: feature
status: backlog
assignee: developer
owner: user
parent: "[[t0198-support-config-flag-on-cli]]"
created: 2026-06-01
---

# Implement `artifacts --config <ref>` CLI flag

Implement the design specified in
[[s0034-artifacts-cli-config-flag]]. The spec defines every
decision; this task is the build-out.

## Context

- **Spec** — [[s0034-artifacts-cli-config-flag]] is the
  authoritative source. Read it end-to-end before starting; do
  not re-derive decisions.
- **Parent task** — [[t0198-support-config-flag-on-cli]] holds
  the user story, "why", and high-level verification.
- **Companion core primitive** — [[t0197-support-custom-marker-filename-for]]
  ships the broader `find_vault_root` / `load_settings` /
  doctor / init surface. **Sequencing:** if t0197 has already
  landed the `marker_filename` kwarg on `find_vault_root` when
  this task starts, consume it and skip step 3 below. Otherwise,
  ship the minimal kwarg addition as part of this PR (spec
  §6.4, §10.1, §13 step 3).

## Requirements

Each requirement maps to a section of s0034. Implement in this
order; the spec calls out trade-offs and edge cases for each.

1. **Add `cli/_config.py`** — `_classify_ref(ref) -> str`,
   `SettingsRef` dataclass (`root`, `settings_path`),
   `_resolve_settings_path(*, config_ref, cwd) -> SettingsRef | None`,
   and `ConfigRefError(ValueError)`. Surface and disambiguation
   rule per s0034 §6.1–6.2. Edge cases per §6.3.
2. **Wire the pre-parser into `cli/__init__.py:_run`** — Phase 0
   pass per s0034 §7.1. Use `allow_abbrev=False`. Strip
   `--config <ref>` from argv before alias resolution and
   subcommand peek-parsers. Catch `ConfigRefError` and exit 2
   with the formatted message (s0034 §9).
3. **Extend `find_vault_root`** in `src/artifacts_os/core/vault.py`
   to accept `marker_filename: str = "artifacts.yaml"` per
   s0034 §6.4. *Skip this step if t0197 has already shipped it.*
4. **Re-declare `--config` on the real parser** for `--help`
   documentation and typo-safety (s0034 §7.1, §14.2). The real
   parser receives argv without `--config`, so the re-declaration
   never fires at parse time.
5. **Update `_load_views_settings` / `_load_cli_settings`** in
   `cli/__init__.py` to consume the resolved `settings_path`
   instead of constructing `Path(root) / "artifacts.yaml"`.
   Surface change per s0034 §8.
6. **Add the `init` carve-out** in
   `cli/commands/init.py` — emit the stderr note from s0034 §7.3
   when `args.config is not None`. `init` keeps writing
   `artifacts.yaml` regardless of the flag.
7. **Tests** — add `tests/cli/test_config_flag.py` with all
   twelve cases in s0034 §11.1. Add `make_vault_with_marker`
   helper to `tests/cli/conftest.py` per §11.3. Add the two
   `find_vault_root` cases to `tests/core/test_vault.py` per
   §11.2 (skip if t0197 covered them).
8. **Docs** — add the "CLI override — `--config`" section to
   `docs/settings.md` per s0034 §12.1. Add the flag-table entry
   to `src/artifacts_os/cli/README.md` per §12.2. Add the
   CHANGELOG line per §12.4.

## Verification

- [ ] `artifacts --config ./path/to/settings.yaml list` lists
      artifacts from the vault rooted at that file, regardless
      of CWD. (Maps to spec §11.1 #1, #2.)
- [ ] `artifacts --config openstation.yaml list` (basename form)
      walks up from CWD and finds the file under its custom
      name. (Maps to §11.1 #3, #12.)
- [ ] `artifacts --config ./missing.yaml list` exits 2 with
      stderr containing `--config: ./missing.yaml: file not
      found`. (Maps to §11.1 #4.)
- [ ] `artifacts --config missing.yaml list` (basename not
      found) exits 2 with stderr containing
      `--config: missing.yaml: no file with that name found
      walking up from`. (Maps to §11.1 #5.)
- [ ] Symmetric position — both `artifacts --config x.yaml list`
      and `artifacts list --config x.yaml` produce identical
      output. (Maps to §11.1 #7.)
- [ ] Without `--config`, all existing CLI invocations behave
      identically (regression test added at §11.1 #10, #11).
- [ ] The flag works across `list`, `show`, `create`, `set`,
      `status`, `events` — one parameterised test (§11.1 #8).
- [ ] `artifacts init` is unaffected by `--config`: it writes
      `artifacts.yaml` at the target directory and emits the
      stderr note (§11.1 #9).
- [ ] `--config ""` exits 2 via argparse (§11.1 #6).
- [ ] `docs/settings.md` gains a "CLI override — `--config`"
      section (§12.1).
- [ ] `src/artifacts_os/cli/README.md` flag table includes the
      new flag (§12.2).
- [ ] CHANGELOG entry added (§12.4).
- [ ] `pytest` is green; no existing test removed.
- [ ] `--help` output for `artifacts` shows `--config <ref>`
      (re-declared per §7.1, §14.2).
