---
assignee: architect
created: 2026-06-01
id: t0198
kind: task
name: support-config-flag-on-cli
owner: user
status: done
type: feature
started: 2026-06-01
subtasks:
  - "[[t0199-implement-artifacts-cli-config-flag]]"
artifacts:
  - "[[openstation/specs/s0034-artifacts-cli-config-flag]]"
completed: 2026-06-05
---

# Support `--config` flag on `artifacts` CLI to override settings discovery

## User story

**As a** host application or operator working in a project where the
artifacts-os settings file is not at the default location (or is
named something other than `artifacts.yaml`),
**I want** a `--config` flag on the `artifacts` CLI that points the
command at a specific settings file,
**so that** I can run `artifacts` against any vault without first
cd'ing into it, exporting env vars, or renaming files.

## Why

- Direct papercut surfaced in
  [[n0020-openstation-command-coverage-buckets]] — operators today
  have no way to override marker discovery from the CLI without
  environment-variable gymnastics.
- [[r0001-openstation-integration-audit]] §3 documents the
  host-extension surface (`from_base` settings chain). A CLI flag
  is the operator-facing complement to that library-level extension
  point — the architect can plumb settings from a known path without
  depending on CWD geometry.
- Companion to [[t0197-support-custom-marker-filename-for]], which
  targets the broader core-level primitive. **This task replaces
  t0197's CLI requirement (Req #3) — t0197 should be refined to
  drop the CLI bullet and stay focused on the core
  `find_vault_root` / `load_settings` primitive.**

## Directions (intent, not contract)

- The `artifacts` CLI accepts a top-level **`--config <ref>`** flag.
  The flag is **global**, not per-subcommand — it applies to every
  verb (`list`, `show`, `create`, `set`, `status`, `events`,
  `views`, …) that needs to resolve the settings file.
- The `<ref>` value accepts either:
  - **A path** (relative or absolute, e.g. `./custom.yaml`,
    `/etc/artifacts/openstation.yaml`) — use that file directly,
    no walk-up.
  - **A basename** (e.g. `openstation.yaml`) — walk up from CWD
    looking for a file with that name, same algorithm as today's
    `find_vault_root` but with a substituted filename.
  The architect chooses the disambiguation rule (e.g. presence of
  `os.sep`, or `os.path.exists` check on the literal value).
- When the flag is absent, behavior is identical to today (walk up
  from CWD looking for `artifacts.yaml`).
- A missing or invalid `<ref>` exits non-zero with a clear error
  message that names the value that was tried.
- **`--config` does NOT affect `artifacts init`.** `init` keeps
  writing to `artifacts.yaml` at the project root regardless of the
  flag. Custom-named markers are written by the host (e.g.
  openstation init writes `openstation.yaml` itself) — artifacts-os
  is read-side for non-default markers.
- **No precedence machinery.** There is no env-var override to
  reconcile with — only the flag and the default. If t0197 later
  adds an env var, that task owns the precedence rule.

## Sub-tasks

Architect spec sub-task — `s00XX-artifacts-cli-config-flag` —
optional but recommended:

- Defines the path-vs-basename disambiguation rule.
- Defines the exit-code / error-message contract for missing or
  malformed `<ref>` values.
- Confirms the flag plumbing (top-level `argparse` arg vs subparser
  inheritance) given artifacts' flat-verb convention.

If the architect judges the contract small enough to skip the spec,
this task can be implemented directly; flag the decision in the
implementation task.

## Progress

### 2026-06-01 22:55:53 — Incomplete run (r0212)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$2.52, turns=45

### 2026-06-01 — Architect spec complete

Wrote [[s0034-artifacts-cli-config-flag]] — the full design
contract for the `artifacts --config <ref>` global flag:
disambiguation rule (syntactic path-vs-basename), resolver
(`_resolve_settings_path` + `SettingsRef` + `ConfigRefError`),
argparse pre-parser plumbing, `init` carve-out, error contract
(exit 2, `--config:` prefix), 12-case test plan, and doc
updates. Decisions summarised in §4 (10 locked decisions) with
trade-off analysis in §14.

Created [[t0199-implement-artifacts-cli-config-flag]] for the
developer to build against the spec. Recorded the spec in the
parent's `artifacts` frontmatter and added `## Findings` /
`## Downstream` / `## Subtasks` sections.

Architect deliverable (spec) is done; implementation is
delegated to t0199. Transitioning t0198 to review.

## Verification

- [ ] `artifacts --config ./path/to/settings.yaml list` lists
      artifacts from the vault rooted at that file, regardless of
      CWD.
- [ ] `artifacts --config openstation.yaml list` (basename form)
      walks up from CWD and finds the file under its custom name.
- [ ] `artifacts --config ./missing.yaml list` exits non-zero and
      names the missing value in the error.
- [ ] Without `--config`, all existing CLI invocations behave
      identically (regression test added).
- [ ] The flag works the same way across at least three verbs
      spanning read + write surfaces (`list`, `show`, `create`).
- [ ] `artifacts init` is unaffected by `--config` (regression test
      added — `init` always writes `artifacts.yaml`).
- [ ] `docs/settings.md` gains a "CLI override" section pointing
      at the flag.

## Constraints

- **No schema fork.** The file targeted by `--config` must still
  parse as a `Settings`-shaped YAML; only the *location* is
  configurable, not the schema.
- **No process-wide caching.** Resolved per CLI entry; identical
  cost when unused.
- **Companion task t0197 covers the underlying core primitive.**
  This task is the CLI surface only.

## Subtasks

- [[t0199-implement-artifacts-cli-config-flag]] — developer
  builds against [[s0034-artifacts-cli-config-flag]].

## Findings

The architect chose to **write the spec** (not skip it). The
contract is small but it has three non-obvious decision points
that benefit from being pinned in one place rather than
re-derived during implementation:

1. **Path-vs-basename disambiguation** is a pure syntactic
   rule — `os.path.isabs(ref) or os.sep in ref or "/" in ref`
   → path; otherwise → basename. `os.path.exists`-based
   disambiguation was rejected because the same flag value
   would mean different things in different CWDs (spec §6.5).
2. **argparse plumbing** uses a pre-parser pass that strips
   `--config <ref>` from argv before alias resolution, then
   re-declares the flag on the real parser purely so `--help`
   documents it and typos (`--confg`) get clear argparse
   errors. This mirrors the existing `_peek_*` pattern in
   `_run` rather than introducing a new structure (spec §7).
3. **`init` carve-out** prints a one-line stderr note when
   `--config` is mixed with `init` rather than silently
   ignoring the flag — operator who typed
   `artifacts --config openstation.yaml init` is told the
   flag had no effect on `init` (spec §7.3, §14.3).

The full spec lives at
[[s0034-artifacts-cli-config-flag]]. It covers:

- CLI surface (§5) — synopsis, worked invocations, verb
  coverage.
- Disambiguation rule + resolver (§6) — `_classify_ref`,
  `_resolve_settings_path`, `SettingsRef`, `ConfigRefError`.
- argparse plumbing (§7) — pre-parser pass, real-parser
  re-declaration, `init` carve-out.
- Call-site plumbing in `cli/__init__.py` (§8).
- Error contract (§9) — exit 2 for every `--config` failure,
  with `--config:` prefix in every message.
- Dependency on t0197's `marker_filename` kwarg (§10) — either
  order ships cleanly; the implementing task picks based on
  what has landed.
- Tests (§11) — twelve cases in a new `test_config_flag.py`.
- Documentation updates (§12) — `docs/settings.md` new section,
  `cli/README.md` flag-table entry, CHANGELOG line.
- Trade-offs (§14) — flag name (`--config` vs `--config-file`
  vs `--marker`), re-declaration rationale, `init` carve-out
  noise level, exit-code choice.

Decisions are summarised as 10 locked decisions in §4. The
implementing task ([[t0199-implement-artifacts-cli-config-flag]])
lists the build-out steps and re-states the parent task's
verification items mapped to spec sections.

## Downstream

- **t0197 refinement.** Per the task spec's "Why" section,
  t0197 should drop its CLI passthrough requirement (Req #3)
  now that this task owns the CLI surface. The
  `marker_filename` kwarg on `find_vault_root` is shared
  between t0197 and t0198 — either task can land it. The user
  should refine t0197's spec to remove Req #3 explicitly.
- **TUI passthrough.** s0006 (TUI module) does not yet adopt
  `--config`. When the TUI gains a settings-discovery surface,
  it should mirror the CLI flag — its own spec, not folded
  here.
- **Env-var override.** `ARTIFACTS_CONFIG` /
  `ARTIFACTS_MARKER_FILENAME` is deliberately out of scope
  here (spec §3, §15). If t0197 ships an env var, it owns the
  precedence rule between flag and env in its own spec.