---
agent: architect
id: r0001
kind: research
name: openstation-integration-audit
status: done
created: 2026-04-29
---

# artifacts-os ↔ openstation Integration Audit

**Date:** 2026-04-29
**Agent:** architect
**Goal:** Identify which openstation responsibilities `artifacts-os`
already covers and which remain gaps, to inform an integration that
makes `artifacts-os` the base layer for openstation.

## TL;DR

`artifacts-os` is shaping up as a clean, layered **library + thin CLI**
for storing and querying frontmatter-driven markdown artifacts.
`openstation` is a much larger, opinionated **task-management harness**
built on the same idea, but with all the moving parts in one Python
package. Roughly **40–50% of openstation's code surface is generic
artifact mechanics that `artifacts-os` already does (or trivially can
do) better**. The remaining ~50% is openstation-specific value
(lifecycle, run/exec, sessions, hooks, events, alerts, init/scaffold)
that has no analogue in `artifacts-os` today.

The integration is feasible: openstation can become **the higher-layer
task harness** sitting on top of `artifacts_os.core` / `views`, with
the openstation Python package losing its in-house `artifacts.py`,
`registry.py`, parts of `core.py`, `tasks.py` discovery/CRUD,
`formatter.py`, and the artifact-rendering bits of `ui.py`.

## 1. Architectural shape, side by side

| Dimension | artifacts-os | openstation |
|---|---|---|
| Package style | Strict layered DAG: `core → views → cli/tui`; `core → log → ai`. No peer imports. | Single `openstation/` package; everything (`cli`, `tasks`, `runs`, `hooks`, `state`, `ui`, `init`) imports freely. |
| Vault marker | `artifacts/artifacts.yaml` walked up from CWD | `.openstation/` resolved from `git rev-parse --show-toplevel` |
| Storage root | `artifacts/` (with `openstation → artifacts` compat symlink) | `openstation/` (user) + `.openstation/` (framework plumbing) |
| Public API | Library-first: `find_vault_root`, `Registry`, `KindDef`, `create/get/update`, `list_artifacts`, `resolve`, `search`, `validate_*`, `load_settings`, `Settings` | CLI-first; library API not really exposed |
| Settings model | `artifacts.yaml` + `Settings` base with `from_base` extension subclasses (e.g. `ViewsSettings`) | `openstation.yaml` + ad-hoc dict access; many sections (`hooks`, `defaults`, `views`, `default_views`, `run`, `verify`, `connectors`, `autonomous`) |
| Kind registry | `Registry` merges caller-provided `KindDef`s with `artifacts/kinds/*.json` (JSON Schema with `x-` extensions) | Hardcoded `REGISTRY` dict in `registry.py` (`agent`, `note`, `research`, `spec`, `alert`, `task`) |
| Renderer | `views.render_table` → `rich.Table` driven by `KindDef.meta["columns"]` + `meta["status_colors"]` | `ui.py` with three renderers (`rich_task_table`, `rich_artifact_table`, alert variant) and a hardcoded `_STATUS_STYLES` dict |
| Atomicity | `O_CREAT|O_EXCL` for create, `os.replace` for update — explicit invariant | Same in `tasks.py` / `artifacts.py`, but not centrally documented |
| Tests | `tmp_path` + `make_vault` fixture, no mocking | Mix of fixtures and integration tests |

## 2. What is already covered by artifacts-os

These openstation responsibilities are already provided as library
primitives by `artifacts-os`. Adopting it removes openstation's
in-house implementation.

| Capability | openstation today | artifacts-os equivalent |
|---|---|---|
| Vault root discovery | `core.find_root` (git toplevel + `.openstation` check) | `core.find_vault_root` (walks up from CWD) |
| Frontmatter parse / write | `core.parse_frontmatter`, `tasks._write_frontmatter` | `core.frontmatter` module |
| Atomic create / update | `tasks._atomic_create`, `_write_task` | `core.store.create/update` |
| ID assignment | `tasks.next_task_id`, per-kind logic in `artifacts.py` | `core.ids.next_id` driven by `KindDef.prefix` + `numbered` |
| Reference resolution | `tasks.resolve_task` + `artifacts.resolve_artifact` + `registry.resolve_any` | `core.discover.resolve` (exact stem → prefixed ID → numeric → partial) |
| Listing / filtering | `tasks.discover_tasks`, `artifacts.discover_artifacts`, alert variant | `core.discover.list_artifacts(registry, kind=, status=, tag=)` |
| Kind registry | hardcoded `REGISTRY` dict + plural aliases | `Registry` merges caller `KindDef`s + JSON-schema kinds from `artifacts/kinds/*.json` |
| Frontmatter validation | `verify.py` + ad-hoc per-kind checks | `core.validate.validate_one/validate_many`, JSON Schema, fixable hints |
| Checklist verification | `verify.py` body checkbox parser | `cli.commands.verify` (`- [ ]` / `- [x]` count) |
| Field specs / column parsing | `formatter.parse_field_specs`, `format_field_value` | `views.parse_field_specs`, `views.format_field`, `views.FieldSpec` |
| Table rendering | `ui.rich_artifact_table`, `rich_task_table`, `_STATUS_STYLES` | `views.render_table(items, columns, kind_def=…)` honouring `meta["status_colors"]` |
| Named/default views | `views`/`default_views` keys parsed inline in `tasks.cmd_list` | `views.ViewsSettings` / `ViewConfig` / `ViewsConfig` + `from_base` parser |
| Settings loading | scattered `yaml.safe_load` calls | `core.load_settings` → `Settings` base + extension pattern, `layout_version` schema gate |

**Bottom line:** an openstation that depends on `artifacts-os` could
delete or thin out roughly `registry.py` (167 LOC), `artifacts.py`
(437 LOC), the discovery + CRUD half of `tasks.py`, `formatter.py`
(236 LOC), the artifact-rendering half of `ui.py`, the
listing/show/create/status portions of `cli.py`, and most of
`verify.py`'s frontmatter checks — comfortably 2,500+ lines deleted
with no behaviour loss.

## 3. Gaps in artifacts-os

These are openstation needs that `artifacts-os` does not currently
provide.

### 3.1 Lifecycle / workflow semantics — openstation-owned

Per CLAUDE.md: "No lifecycle logic in `cli`". These belong in
openstation:

- State machine (`VALID_TRANSITIONS`, `_STATUS_RANK`, `_MIN_PARENT_STATUS`)
- Sub-task model — `parent` / `subtasks` wikilinks, blocking rule, parent auto-promotion, all-done promotion
- Dependency model — `depends_on` wikilinks blocking `ready`
- Ownership rules — `owner: user|agent`, who may transition `review→verified`, `verified→done`
- Pre-review checklist sections — Findings, Downstream, Progress, Verification
- `/openstation.*` slash commands

`artifacts-os` `KindDef.statuses` is just a list — no notion of legal
transitions. That is the right boundary.

### 3.2 Agent execution & runs — no artifacts-os equivalent

- `run.py` (2,445 LOC) — by-task / by-agent / by-alert modes;
  execute/verify auto-detection; tmux/detached backend; budget,
  turns, cost; worktree pass-through; `--editor claude|opencode`;
  `--tools` merging
- `sessions.py` (419 LOC) + `state.py` (448 LOC) — SQLite `runs`
  table, `session_id`, lost-run GC, stale detection
- `cc-sessions` browser — Claude Code session file inspector
- `logs.py` (292 LOC) — stream-json log capture and replay

This is openstation's primary value-add. The `artifacts-os` `ai/`
stub (spec `s2066`) could host pieces eventually, but currently does
nothing. **Recommendation: keep entirely on the openstation side.**

### 3.3 Hooks — gap; could be a new artifacts-os module

`hooks.py` (571 LOC) — `StatusTransition` matchers, pre/post phases,
`OS_*` env vars, timeouts, abort-on-fail. Generic and reusable.
**Recommendation: design `artifacts_os.hooks` as a new module that
consumes core events.**

### 3.4 Events log — gap; partial overlap with stub `log/` module

`events.py` + `events_cli.py` — daily JSONL log of `task_created`,
`status_transition`, `run_started`, `run_complete`. **Recommendation:
this maps almost perfectly onto the `artifacts_os.log` stub module
(spec `s2063`). Consolidating openstation events into the
artifacts-os `log` module is a clean integration win.**

### 3.5 Alerts subsystem — openstation-specific, keep on top

`alerts.py` + `heartbeat.py` (569 LOC) — connector types
(`reminder`, `internal`, `github`, `slack`, `telegram`), cron
schedules, event names, pause/resume. The kind `alert` is registered
like any other artifact, but its semantics (heartbeat-driven,
connector dispatch) are not generic. **Keep openstation-side. Alert
artifact storage uses artifacts-os primitives; trigger / dispatch
logic stays in openstation.**

### 3.6 Init / scaffold — gap; partial overlap

`init.py` (881 LOC): creates `.openstation/`, `openstation/`,
`.claude/` symlinks; deploys hook scripts; injects managed CLAUDE.md
sections; copies example agents; sets up
`worktree.symlinkDirectories`; writes a starter `openstation.yaml`.

`artifacts-os` has a much smaller `cli init` that creates
`artifacts/artifacts.yaml`, per-kind directories,
`artifacts/kinds/*.json` schemas, and the legacy
`openstation → artifacts` symlink. **Gap: Claude Code integration
steps (CLAUDE.md injection, `.claude/` discovery symlinks, hook
deployment, agent templates) are openstation-specific. Keep
openstation init on top, but reuse `artifacts_os.cli.init` for the
vault-creation portion.**

### 3.7 Doctor / diagnostics — openstation-specific

`doctor.py` (675 LOC) — installation health checks, repair guidance.
No analogue in `artifacts-os`, no obvious need for one.

### 3.8 Worktrees — shared concern, complementary mechanisms

`artifacts-os` has natural worktree support via `find_vault_root`
walking up to `artifacts/artifacts.yaml`. openstation uses Claude
CLI's `worktree.symlinkDirectories` setting and
`git rev-parse --show-toplevel`. Two different strategies — the
upstream walk is more general, but openstation's symlink approach
is necessary for `.claude/` discovery. **Recommendation: artifacts-os
keeps walk-up; openstation overlays the Claude-symlink mechanism.**

### 3.9 Naming / ID convention drift — active divergence

This is the most concrete blocker today.

| Aspect | artifacts-os | openstation |
|---|---|---|
| Task filename | `t0042-fix-bug.md` (prefixed) | `0042-fix-bug.md` (unprefixed) |
| Task `name` field | slug only (per latest CLAUDE.md update) | `0042-fix-bug` (full stem) |
| `id` field | `t0042` | not stored as a separate field — derived from filename |
| Agent filename | `researcher.md` (no prefix) | `researcher.md` (no prefix) |
| Numbering scope | per-kind, prefix-disambiguated | per-kind, prefix-less collisions avoided by separate dirs |

In-flight task `t0037-redefine-name-field-as-slug` is currently
reshaping this on the artifacts-os side. **Until ID/name conventions
converge, openstation cannot consume artifacts-os reads/writes
against an openstation vault without a translation layer.**

### 3.10 Frontmatter field set — partial overlap

`artifacts-os` task kind: `kind`, `id`, `name`, `status`, plus
optional `assignee`, `owner`, `created`, `summary`.

openstation task kind: adds `type`, `parent`, `subtasks`,
`depends_on`, `artifacts` (wikilink list), `allowed-tools`,
`scheduled`, `started`, `completed`.

**Recommendation: artifacts-os stays permissive; openstation
registers its enriched `KindDef.schema` for `task` / `spec` / `agent`
via the per-kind JSON schema mechanism artifacts-os already supports.**

### 3.11 Wikilink semantics — gap

openstation universally uses Obsidian wikilinks (`"[[name]]"`) for
`parent`, `subtasks`, `depends_on`, `artifacts`, `task`. artifacts-os
has no notion of wikilinks today — fields are opaque.
**Recommendation: keep wikilink stripping/resolution in openstation;
artifacts-os stays as a string/list value store.**

## 4. Coverage matrix at a glance

| Concern | artifacts-os | openstation | Decision |
|---|:-:|:-:|---|
| Vault discovery | yes | yes (different strategy) | Use artifacts-os; openstation overlays Claude symlinks |
| Frontmatter parse/write | yes | yes | Replace openstation's with artifacts-os |
| Atomic file ops | yes | yes | Replace |
| Per-kind ID counter | yes | yes | Replace |
| Reference resolution | yes | yes | Replace |
| Kind registry | yes (extensible JSON Schema) | yes (hardcoded dict) | Replace; declare openstation kinds via `artifacts/kinds/*.json` |
| List / filter | yes | yes | Replace |
| Frontmatter validation | yes | partial | Replace |
| Checklist verify | yes | yes | Replace |
| Field specs / column parse | yes | yes | Replace |
| Table rendering | yes | yes | Replace |
| Named / default views | yes | yes | Replace |
| Settings loader | yes (extensible) | yes (ad-hoc) | Replace; openstation owns its sections via `from_base` |
| Status state machine | no | yes | Keep openstation-side |
| Sub-task / parent / depends_on | no | yes | Keep openstation-side |
| Ownership rules | no | yes | Keep openstation-side |
| Slash commands | partial (10 planned `/artifacts.*`) | yes (21 `/openstation.*`) | Both stay; different surfaces |
| Run / agent execution | stub `ai/` | yes | Keep openstation-side |
| Sessions / state.db | no | yes | Keep openstation-side |
| Hooks | no | yes | Push into artifacts-os (new module) |
| Events log | stub `log/` | yes | Push into artifacts-os `log/` module |
| Alerts / heartbeat | no | yes | Keep openstation-side |
| Init / scaffold | yes (minimal) | yes (heavy: CLAUDE.md, `.claude/`, agents) | Layer: openstation init wraps artifacts-os init |
| Doctor | no | yes | Keep openstation-side |
| Worktrees | yes (walk-up) | yes (Claude symlinks) | Both — complementary |
| TUI browser | stub `tui/` | no | Future artifacts-os-side win |
| Wikilinks | no | yes | Keep openstation-side (treat as string) |

## 5. Concrete divergences that block direct integration

These must be resolved before openstation can consume artifacts-os
against a real openstation vault:

1. **Task filename prefix.** openstation uses `0042-...`; artifacts-os
   uses `t0042-...`. Either openstation declares
   `KindDef(prefix="", numbered=True)` for tasks (verify
   `core.ids.next_id` accepts an empty prefix), or openstation
   migrates to prefixed filenames (large diff; breaks existing
   wikilinks). **Recommended: `prefix=""` for backward compatibility.**
2. **`name` vs `id` fields.** artifacts-os' new convention (per the
   latest CLAUDE.md edit) is `name = slug only`, `id = t0042`.
   openstation stores `name = "0042-fix-bug"` (full stem) and no
   separate `id`. The two semantics must be reconciled per-kind.
3. **Vault marker location.** artifacts-os looks for
   `artifacts/artifacts.yaml`; openstation looks for `.openstation/`.
   **Recommended: artifacts-os adds an alternative marker check or
   accepts a configured marker path; or openstation init writes
   both markers.**
4. **Storage root.** `artifacts/` vs `openstation/`. Both projects
   already maintain a compatibility symlink — sufficient for
   transitional period.
5. **Wikilink-aware fields.** artifacts-os reads `"[[t0042-foo]]"`
   literally; openstation needs wikilink-stripped semantics for
   resolve. **Recommended: a small openstation-side wrapper that
   pre-strips wikilinks before calling `core.resolve`.**

## 6. Recommended integration shape

A layered dependency, not a merger:

```
                 ┌─────────────────────────────────────────────┐
                 │  openstation (task harness)                 │
                 │  - lifecycle state machine                  │
                 │  - sub-tasks, parent, depends_on            │
                 │  - ownership / verification                 │
                 │  - runs / sessions / state.db               │
                 │  - alerts / heartbeat                       │
                 │  - slash commands /openstation.*            │
                 │  - doctor, init scaffold (CLAUDE.md, .claude/) │
                 │  - wikilink resolution wrapper              │
                 └────────────┬────────────────────────────────┘
                              │ depends on
                              ▼
                 ┌─────────────────────────────────────────────┐
                 │  artifacts-os                               │
                 │  core   — vault, registry, CRUD, validate   │
                 │  views  — table render, field specs, view   │
                 │  log    — JSONL events (← absorb openstation events) │
                 │  hooks  — pre/post transition (← absorb openstation hooks) │
                 │  cli    — `artifacts` CLI (orthogonal surface) │
                 │  ai     — (stub) future                     │
                 │  tui    — (stub) future                     │
                 └─────────────────────────────────────────────┘
```

Three net-new artifacts-os specs are implied:

- **`hooks` module** — extract from openstation `hooks.py`;
  generalize the matcher / phase / env-var contract.
- **`log` module fleshed out** — promote openstation `events.py`
  schema into the canonical event log.
- **Vault marker negotiation** — let `find_vault_root` accept the
  openstation `.openstation/` marker, or have openstation init
  write both markers.

Two openstation-side migration tasks:

- Replace `openstation/registry.py` + `artifacts.py` + parts of
  `tasks.py`, `formatter.py`, `ui.py` with `artifacts_os.core` /
  `views` calls.
- Reconcile naming convention (prefix, `name` / `id` split) —
  depends on the outcome of artifacts-os t0037.

## 7. Risks & uncertainties

- **Decided:** `artifacts-os` is the right substrate. Its layering,
  atomic-write discipline, and extensible settings/registry already
  cover the generic primitives openstation re-implements.
- **Recommended:** push openstation `events.py` and `hooks.py` *down*
  into `artifacts-os` `log` and a new `hooks` module. This is a
  generalization claim — needs review from whoever owns each
  subsystem in openstation before committing.
- **Needs further research:**
  - Does `core.ids.next_id` correctly handle `prefix=""` numbered
    kinds? A read of `src/artifacts_os/core/ids.py` will settle it.
  - Whether artifacts-os' validation can be extended to support
    custom transition rules without becoming a state machine itself,
    or whether transitions should remain wholly in openstation.
  - The exact migration path for openstation's existing 438 tasks
    (`name: 0042-...`, full stem). Rewrite frontmatter on read,
    one-time migration, or per-kind tolerance config in artifacts-os.

## Recommendations (next steps)

1. Spin up a follow-up **spec task** proposing the boundary layer:
   the three new artifacts-os modules (`hooks`, fleshed-out `log`,
   marker negotiation) and the two openstation migrations.
2. Resolve the in-flight `t0037-redefine-name-field-as-slug` first —
   the integration plan depends on the final shape of `id` vs
   `name`.
3. Validate `core.ids.next_id` behaviour for `prefix=""` numbered
   kinds before committing openstation to that path.

## Sources

- `/Users/leonid/workspace/os/artifacts-os/README.md`
- `/Users/leonid/workspace/os/artifacts-os/docs/architecture.md`
- `/Users/leonid/workspace/os/artifacts-os/docs/settings.md`
- `/Users/leonid/workspace/os/artifacts-os/src/artifacts_os/core/README.md`
- `/Users/leonid/workspace/os/artifacts-os/src/artifacts_os/views/README.md`
- `/Users/leonid/workspace/os/artifacts-os/src/artifacts_os/cli/README.md`
- `/Users/leonid/workspace/os/artifacts-os/artifacts/kinds/{task,agent,research,spec}.json`
- `/Users/leonid/workspace/open-station/README.md`
- `/Users/leonid/workspace/open-station/.openstation/docs/{lifecycle,task.spec,storage-query-layer,artifacts,cli,settings,hooks,events,sessions,worktrees}.md`
- `/Users/leonid/workspace/open-station/.openstation/skills/openstation-execute/SKILL.md`
- `/Users/leonid/workspace/open-station/src/openstation/registry.py`
- `/Users/leonid/workspace/open-station/src/openstation/core.py`
- LOC counts via `wc -l` over `src/openstation/*.py`