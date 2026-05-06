---
kind: task
id: t0108
name: spec-artifacts-init-flow-with
type: spec
status: done
assignee: architect
owner: user
created: 2026-05-06
started: 2026-05-06
artifacts:
  - "[[artifacts/specs/s0021-artifacts-init-flow]]"
completed: 2026-05-06
---

# Spec Artifacts-Init Flow With Tiered Templates And Kind/Agent Selection

## Requirements

1. **CLI surface** — Specify the `artifacts init` subcommand: positional/flag arguments (`--template`, `--kinds`, `--agents`, `--force`, `-y`, `--dry-run`), help text, exit codes, and how flags interact with prompts.
2. **Three-step prompt flow** — Specify Step 1 (settings tier: basic/standard/advanced, single choice), Step 2 (kinds multi-select), Step 3 (agents multi-select). Include example transcripts and the default selection at each step.
3. **Non-TTY behavior** — Resolve fail-loud vs silent-fallback; specify `-y` semantics, error wording when stdin isn't a TTY and no flags are passed.
4. **Multi-select input format** — Choose between comma-separated numbers and per-item y/n; document rationale and accessibility implications. No new TUI dependency permitted.
5. **Settings template inventory** — Specify the contents of `basic.yaml` / `standard.yaml` / `advanced.yaml`: which sections each carries (`project`, `views`, `default_views`, `cli`), field-by-field, with progression rationale (each tier additive).
6. **Kind template inventory** — Specify which kinds ship (`task`, `note`, `spec`, `research`, `agent`), the template structure (`kind.json` + `ARTIFACT.md`), and the default selection in Step 2.
7. **Agent template inventory** — Specify which agents ship, the template structure, and the default selection in Step 3 (none).
8. **Bundled template layout** — Specify the `importlib.resources` package path, directory layout under `src/artifacts_os/`, and the loader API used at init time.
9. **Variable interpolation** — Specify the variable list (`{{project_name}}`, `{{project_alias}}`, others?), source-of-value rules (CLAUDE.md H1 → cwd basename; first-word lowercase ≤8 chars), and substitution mechanism (str.replace; no Jinja).
10. **Agent ↔ agent-kind coupling** — Resolve: if Step 3 selects an agent but Step 2 omits the `agent` kind, what happens? Auto-include, refuse, or allow loose? Specify behavior + summary-line wording.
11. **Conditional content in `advanced.yaml`** — Resolve: per-assignee queue views (`developer-queue` etc.) reference agents that may not be installed. Choose static-emit vs dynamic-emit vs documentation-only; specify the chosen approach.
12. **Existing-file guard** — Specify per-file vs all-or-nothing; apply to `artifacts.yaml` only or also to `artifacts/kinds/<name>/` and agent files; `--force` semantics for partial overwrite.
13. **Error handling** — Specify behavior for: missing template in package, write failure mid-init (rollback?), `--dry-run` output format (per-file lines), and exit codes.
14. **Flag/prompt precedence** — Specify: does `--template advanced` + bare invocation skip Step 1 only, or all steps? Can the user mix `--kinds task,note` with an interactive Step 3?

## Verification

- [x] Spec doc lands at `artifacts/specs/sNNNN-artifacts-init-flow.md`, status `approved`.
- [x] CLI surface fully specified — every flag has type, default, help text, and interaction rules with prompts.
- [x] Three-step prompt flow specified with at least one TTY transcript per tier.
- [x] Non-TTY behavior specified including `-y` semantics and the exact error message.
- [x] Multi-select input format chosen with rationale for accessibility / dependency-freedom.
- [x] Settings templates (`basic` / `standard` / `advanced`) specified field-by-field with rationale for each addition between tiers.
- [x] Kind template inventory specified — names, file structure, defaults.
- [x] Agent template inventory specified — names, file structure, defaults.
- [x] `importlib.resources` package layout specified.
- [x] Variable interpolation contract specified — variable list, sources, substitution rules.
- [x] Agent ↔ agent-kind coupling resolved with worked example in summary output.
- [x] Conditional content handling in `advanced.yaml` resolved.
- [x] Existing-file guard specified — file-level granularity, `--force` interaction.
- [x] Error handling and exit codes specified.
- [x] Flag/prompt precedence specified.

## Verification Report

*Verified: 2026-05-06*

| #  | Criterion | Result | Evidence |
|----|-----------|--------|----------|
| 1  | Spec doc lands at `artifacts/specs/sNNNN-artifacts-init-flow.md`, status `approved`. | PASS | `artifacts/specs/s0021-artifacts-init-flow.md` exists; frontmatter `status: approved`, `task: [[t0108-...]]`. |
| 2  | CLI surface fully specified — every flag has type, default, help text, and interaction rules with prompts. | PASS | §5.1 synopsis, §5.2 arguments table (type, default, help text per flag), §5.4 help text, §16 prompt interaction rules. |
| 3  | Three-step prompt flow specified with at least one TTY transcript per tier. | PASS | §10.4 (basic), §10.5 (standard), §10.6 (advanced) — one transcript per tier with prompts and writes. |
| 4  | Non-TTY behavior specified including `-y` semantics and the exact error message. | PASS | §11.1 decision matrix covers all four (TTY × flags × `-y`) cases; §11.2 exact stderr error block, exit 2. |
| 5  | Multi-select input format chosen with rationale for accessibility / dependency-freedom. | PASS | §12.1 format (CSV with `*`/`-`); §12.2 rationale comparing per-item y/n and TUI; §12.3 accessibility (screen reader, keyboard-only). |
| 6  | Settings templates specified field-by-field with rationale for each addition between tiers. | PASS | §6.1 basic, §6.2 standard (each addition called out), §6.3 advanced; mandatory header in §6; rationale paragraphs per tier. |
| 7  | Kind template inventory specified — names, file structure, defaults. | PASS | §7.1 inventory table (5 kinds with `kind.json` + `ARTIFACT.md`, defaults marked); §7.2 installed-file layout. |
| 8  | Agent template inventory specified — names, file structure, defaults. | PASS | §8.1 inventory (5 agents); §8.2 exclusions; §8.3 layout (one `.md` per agent); default = none. |
| 9  | `importlib.resources` package layout specified. | PASS | §13.1 wheel directory tree; §13.2 `pyproject.toml` package-data; §13.3 `importlib.resources.files()` loader API; §13.4 discovery. |
| 10 | Variable interpolation contract specified — variable list, sources, substitution rules. | PASS | §9.1 closed three-variable table with sources; §9.2 `str.replace`-only mechanism; §9.3 closed-list rule for additions. |
| 11 | Agent ↔ agent-kind coupling resolved with worked example in summary output. | PASS | D10 in §4; §8.4 specifies auto-include and shows summary line wording (`agent kind auto-included for selected agents`). |
| 12 | Conditional content handling in `advanced.yaml` resolved. | PASS | §6.4 dynamic-emit rule with both code paths (queues per agent vs. commented stub); D11 in §4. |
| 13 | Existing-file guard specified — file-level granularity, `--force` interaction. | PASS | §14.1 per-file granularity with three states; §14.2 top-level guard + `--force` override; §14.3 worked example. |
| 14 | Error handling and exit codes specified. | PASS | §15.1 missing template, §15.2 mid-init write failure (no rollback), §15.3 dry-run format, §15.4 exit code table; §5.3 mirrors. |
| 15 | Flag/prompt precedence specified. | PASS | §16.1 per-step skip table covering 8 invocation patterns; §16.2 partial mixing; §16.3 flag-value validation. |

### Summary

15 passed, 0 failed. All verification criteria are satisfied by `artifacts/specs/s0021-artifacts-init-flow.md`.

## Notes for the architect

Pre-decided in brainstorm (don't re-litigate; document as constraints):

- New `artifacts init` subcommand (not extending an existing one).
- Three independent selection steps (Option Y).
- Tiers (`basic`/`standard`/`advanced`) shape only the *rest* of `artifacts.yaml`; kinds and agents are independent picks.
- Templates bundled with the wheel via `importlib.resources` (no separate install cache).
- Skip-by-default + `--force` to overwrite.

Reference openstation's `init.py` (`/Users/leonid/.local/share/openstation/src/openstation/init.py`) for prior art — specifically `_select_template`, `_install_settings_template`, `TEMPLATE_CHOICES` patterns. Promote this repo's current `artifacts/artifacts.yaml` as the basis for `advanced.yaml`.

## Findings

Specced the new `artifacts init` flow as
[[artifacts/specs/s0021-artifacts-init-flow]] (status `approved`).
Fourteen requirements from this task map 1:1 onto fourteen locked
decisions (D1–D14) in §4 of the spec.

Headline calls:

- **Subcommand shape (D1, D14)** — `artifacts init [DIRECTORY]`
  with `--template`, `--kinds`, `--agents`, `--force`, `-y`,
  `--dry-run`, plus a new `--openstation-compat` flag that
  preserves the legacy `openstation -> artifacts` symlink as
  opt-in. `--name` and `--no-ai` are dropped.
- **Three independent steps (D2)** — settings tier (single),
  kinds (multi), agents (multi). Each step is independently
  skippable via its flag; `-y` accepts every default at every
  un-flagged step.
- **Non-TTY contract (D3)** — fail loud (exit 2) unless `-y` is
  set or all three flags are supplied. Exact error message
  pinned in §11.2.
- **Multi-select format (D4)** — comma-separated numbers (or
  names), with `*` for all and `-` for none. No new TUI
  dependency. Defaults via empty input.
- **Settings tiers (D5)** — three strictly additive tiers
  (`basic`/`standard`/`advanced`). `basic` is header + three
  lifecycle views; `standard` adds per-type slices,
  `default_views`, and a cross-kind `recent` view; `advanced`
  adds per-assignee queues, spec/note slices, and a `cli` block
  (aliases + `defaults.create.kind: note`). Field-by-field
  inventory in §6. The promoted basis for `advanced.yaml` is
  this repo's current `artifacts/artifacts.yaml`, with the
  per-assignee queue block placeholdered to support D11.
- **Bundle (D8)** — templates ship under
  `src/artifacts_os/templates/{settings,kinds,agents}/` inside
  the wheel; loaded via `importlib.resources.files()`. Discovery
  is filesystem listing — adding a kind/agent is a file-add, no
  registration list to update.
- **Variable interpolation (D9)** — closed three-variable list:
  `{{project_name}}` (CLAUDE.md H1 → cwd basename),
  `{{project_alias}}` (first word, lowercase, alphanumeric, ≤8
  chars), `{{created}}` (today). `str.replace` only — no Jinja.
- **Agent ↔ kind coupling (D10)** — auto-include the `agent`
  kind whenever any agent is selected, regardless of whether the
  kind list came from a flag or a prompt. Summary line states the
  auto-include explicitly so it is never silent.
- **Conditional `advanced.yaml` (D11)** — dynamic-emit: one
  `<agent>-queue` view per selected agent; commented stub when
  none. Avoids dangling references without losing the affordance.
- **File-level guards (D12, D13)** — per-file overwrite
  granularity. `--force` overrides per-file. Mid-init failures
  do not roll back; failures accumulate, exit 1 at end. Dry-run
  prints `[would] ✓ <path>` per file, exit 0.
- **Test plan (§18)** — ten test groups covering bundled-template
  loading (incl. wheel zipimport), interpolation, step skipping,
  multi-select parsing, existing-file guard, agent/kind coupling,
  conditional advanced content, dry-run, error handling, and
  backwards-compat.

The implementation work is non-trivial (rewrite of
`commands/init.py`, new `templates/` package, packaging entry,
new `artifacts/kinds/agent/ARTIFACT.md`) and is recommended to
land as a single PR per §20 — partial rewrites would leave init
broken between commits.

## Downstream

- File a follow-up implementation task to land the rewrite
  (per spec §17 and §20). Should be `type: implementation`,
  assignee `developer`, source-of-truth = this spec.
- `artifacts/kinds/agent/ARTIFACT.md` does not yet exist; the
  implementation task must author it or block on a separate
  documentation task.
- The bundled `templates/` directory must be added to
  `pyproject.toml`'s package-data — verify the wheel includes
  it before declaring init shipped.
- `--openstation-compat` is a backwards-compat affordance for the
  external openstation CLI; once the openstation harness fully
  reads `artifacts/`-shape vaults, the flag can be deprecated in
  a follow-up.
