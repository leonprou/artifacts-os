---
agent: architect
artifacts: '[[n0020-openstation-command-coverage-buckets]]'
created: 2026-04-29
id: r0001
kind: research
name: openstation-integration-audit
status: done
updated: 2026-05-24
---

# artifacts-os ↔ openstation Integration Audit

**Original date:** 2026-04-29
**Refreshed:** 2026-05-24 (per [[t0185-refresh-r0001-openstation-integration-audit]])
**Agent:** architect
**Goal:** Identify which openstation responsibilities `artifacts-os`
already covers and which remain gaps, to inform an integration that
makes `artifacts-os` the base layer for openstation.

> **Refresh note (2026-05-24).** A large fraction of the "Recommended"
> next steps in the original audit have since shipped or been spec-locked:
> the always-on events stream, the hooks subsystem with `host:`
> dispatch (`[[s0032-hooks-via-artbook-distribution]]` — treated as
> implemented per t0185 §1), books-driven init, the artbook
> distribution + promotion model, vault-marker relocation, ARTIFACT.md
> skeletons, and the `name = slug` / `id = t0042` convention.
> Sections below are rewritten against what ships in `main` today;
> closed items are linked to their shipping task or spec.

## TL;DR

`artifacts-os` is now a multi-module **library + thin CLI** for storing,
discovering, observing, and (reactively) responding to frontmatter-driven
markdown artifacts. `openstation` remains the much larger, opinionated
**task-management harness** with all its moving parts in one Python
package. Roughly **50–60% of openstation's code surface is now generic
artifact mechanics that `artifacts-os` already does** — up from the
original 40–50% estimate, because events + hooks + artbook + init have
landed since 2026-04-29. The remaining ~40% is openstation-specific value
(lifecycle, run/exec, sessions, alerts, doctor) that has no analogue
in `artifacts-os` today and intentionally stays openstation-side.

The integration is feasible **today** in a way it was not in April: the
substrate (`core.events`, `hooks.loader`, artbook with `kind: hook`,
project-root marker, locked naming convention) is in place. openstation
can become **the higher-layer task harness** sitting on top of
`artifacts_os.core` / `views` / `events` / `hooks`, losing its in-house
`artifacts.py`, `registry.py`, parts of `core.py`, `tasks.py`
discovery/CRUD, `formatter.py`, the artifact-rendering bits of `ui.py`,
its in-house `events.py`, and most of `hooks.py` — keeping only the
openstation-host hook bundles.

## 1. Architectural shape, side by side

| Dimension | artifacts-os | openstation |
|---|---|---|
| Package style | Strict layered DAG: `core → events → hooks`; `core → views → cli/tui`; `core → log → ai`. Eight modules, no peer imports across branches. | Single `openstation/` package; everything (`cli`, `tasks`, `runs`, `hooks`, `state`, `ui`, `init`, `events`) imports freely. |
| Vault marker | `artifacts.yaml` at **project root** (was `artifacts/artifacts.yaml` until v0.3.0 — relocated per [[t0137-implement-vault-marker-relocation-per]] / docs/migration.md). Walked up from CWD. | `.openstation/` resolved from `git rev-parse --show-toplevel` |
| Storage root | `artifacts/` (data dir, sibling of `artifacts.yaml` marker; legacy `openstation → artifacts` compat symlink removed) | `openstation/` (user) + `.openstation/` (framework plumbing). **Recommended target shape:** collapse `openstation/` into `artifacts/` and reduce `.openstation/` to runtime state only (state.db, run captures) — see §6.1 "Vault layout". |
| Public API | Library-first: `find_vault_root`, `Registry`, `KindDef`, `create/get/update`, `list_artifacts`, `resolve`, `search`, `validate_*`, `load_settings`, `Settings`, `register_emitter` (events) | CLI-first; library API not really exposed |
| Settings model | `artifacts.yaml` + `Settings` base with `from_base` extension subclasses (`ViewsSettings`, `EventsSettings`, plus hooks settings — see `src/artifacts_os/hooks/settings.py`) | `openstation.yaml` + ad-hoc dict access; many sections (`hooks`, `defaults`, `views`, `default_views`, `run`, `verify`, `connectors`, `autonomous`) |
| Kind registry | `Registry` merges caller-provided `KindDef`s with `artifacts/kinds/<name>/{kind.json,ARTIFACT.md}` folder form. Flat-schema legacy form dropped per [[t0142-drop-legacy-flat-kind-schema]]. Kinds ship: `task`, `agent`, `note`, `research`, `spec`, `hook`. | Hardcoded `REGISTRY` dict in `registry.py` (`agent`, `note`, `research`, `spec`, `alert`, `task`) |
| Renderer | `views.render_table` → `rich.Table` driven by `KindDef.meta["columns"]` + `meta["status_colors"]`; tree layout per [[s0022-tree-layout]] (parent/children rendering) | `ui.py` with three renderers (`rich_task_table`, `rich_artifact_table`, alert variant) and a hardcoded `_STATUS_STYLES` dict |
| Atomicity | `O_CREAT|O_EXCL` for create, `os.replace` for update — documented invariant; carried into directory-storage create path (`x-storage: directory` kinds via s0032 §2.2). | Same in `tasks.py` / `artifacts.py`, but not centrally documented |
| Events | Always-on JSONL stream (`artifacts/logs/events/YYYY-MM-DD.jsonl`), closed catalogue of 6 (+ 4 hook-bundle) event types, `register_emitter` extension point, `artifacts events` CLI with `--follow` / `--tail` / `--since` / `--event` filters. | In-house `events.py` writes ad-hoc JSONL; `events_cli.py` reads it; not a shared substrate. |
| Hooks | Opt-in reactive layer: `hooks:` list in `artifacts.yaml` + (per s0032) `kind: hook` directory-bundle artifacts under `artifacts/hooks/<slug>/` with operator-owned `.active/` symlinks; pre/post phases; reentrancy guard. | `hooks.py` (571 LOC) — openstation-specific `StatusTransition` matchers, `OS_*` env vars, abort-on-fail. |
| Tests | `tmp_path` + `make_vault` fixture, no mocking | Mix of fixtures and integration tests |

## 2. What is already covered by artifacts-os

These openstation responsibilities are already provided as library
primitives by `artifacts-os`. The "could replace" column lists the
canonical artifacts-os API.

| Capability | openstation today | artifacts-os equivalent |
|---|---|---|
| Vault root discovery | `core.find_root` (git toplevel + `.openstation` check) | `core.find_vault_root` (walks up from CWD to `artifacts.yaml` at project root) |
| Frontmatter parse / write | `core.parse_frontmatter`, `tasks._write_frontmatter` | `core.frontmatter` module |
| Atomic create / update | `tasks._atomic_create`, `_write_task` | `core.store.create/update` |
| ID assignment | `tasks.next_task_id`, per-kind logic in `artifacts.py` | `core.ids.next_prefixed_id` driven by `KindDef.prefix` + `numbered` (handles `prefix=""` correctly — see §5 below; the original "needs research" question is closed) |
| Reference resolution | `tasks.resolve_task` + `artifacts.resolve_artifact` + `registry.resolve_any` | `core.discover.resolve` (exact stem → prefixed ID → numeric → partial) |
| Listing / filtering | `tasks.discover_tasks`, `artifacts.discover_artifacts`, alert variant | `core.discover.list_artifacts(registry, kind=, status=, tag=)` |
| Kind registry | hardcoded `REGISTRY` dict + plural aliases | `Registry` merges caller `KindDef`s + folder-form kinds (`artifacts/kinds/<name>/kind.json` + `ARTIFACT.md`) |
| Frontmatter validation | `verify.py` + ad-hoc per-kind checks | `core.validate.validate_one/validate_many`, JSON Schema, fixable hints |
| Checklist verification | `verify.py` body checkbox parser | `cli.commands.verify` (`- [ ]` / `- [x]` count) |
| Field specs / column parsing | `formatter.parse_field_specs`, `format_field_value` | `views.parse_field_specs`, `views.format_field`, `views.FieldSpec` |
| Table rendering | `ui.rich_artifact_table`, `rich_task_table`, `_STATUS_STYLES` | `views.render_table(items, columns, kind_def=…)` honouring `meta["status_colors"]` |
| Tree-layout rendering | `_render_tree` in `cli.py` over parent/subtasks | `views.render_tree` ([[s0022-tree-layout]], shipped) |
| Named/default views | `views`/`default_views` keys parsed inline in `tasks.cmd_list` | `views.ViewsSettings` / `ViewConfig` / `ViewsConfig` + `from_base` parser |
| Settings loading | scattered `yaml.safe_load` calls | `core.load_settings` → `Settings` base + extension pattern (`ViewsSettings`, `EventsSettings`, hooks settings), `layout_version` schema gate |
| **Events stream** (new since 2026-04-29) | `events.py` writes ad-hoc JSONL; `events_cli.py` reads it | `artifacts_os.events` — always-on, closed catalogue, `register_emitter` extension, `artifacts events` CLI with `--follow`/`--tail`/`--since`/`--event`. Spec [[s0025-artifact-events]]; CLI [[s0027-align-events-cli-with-list]]. |
| **Hooks** (new since 2026-04-29) | `hooks.py` `StatusTransition` matchers + `OS_*` env vars | `artifacts_os.hooks` — declarative `hooks:` list in `artifacts.yaml` + (per [[s0032-hooks-via-artbook-distribution]]) `kind: hook` directory-bundle artifacts with operator-owned `.active/` activation. `host: openstation` is a reserved foreign host — openstation can ship its own loader against the same `.active/` tree. |
| **Init / scaffold** (much closer than April) | `init.py` (881 LOC) | `artifacts init` with two-stage flow ([[s0030-books-driven-init-flow]]): settings tier → per-book multi-select. Distro-driven; falls back to bundled `artifacts-os` skill. `--openstation-compat` flag exists. |
| **Distribution model** (new since 2026-04-29) | (none — manual file copy) | `artbook.yaml` distros with `book pull` / `book list` / `book show` / `book promote`, canonical-`dest:` + tool-shape-`promote:` separation ([[s0029-artbook-mvp-distribution-model]], [[s0031-artbook-post-pull-artifact-promotion]]). |

**Bottom line (updated):** an openstation that depends on `artifacts-os`
today could delete or thin out `registry.py` (167 LOC), `artifacts.py`
(437 LOC), the discovery + CRUD half of `tasks.py`, `formatter.py`
(236 LOC), the artifact-rendering half of `ui.py`, the
listing/show/create/status portions of `cli.py`, most of
`verify.py`'s frontmatter checks, **plus** `events.py` / `events_cli.py`
(events absorbed) **plus** the generic matcher/action plumbing in
`hooks.py` (only the openstation-host bundles need to stay) — well over
**3,500 LOC** deletable with no behaviour loss, vs. ~2,500 LOC in the
original audit.

## 3. Gaps in artifacts-os

These are openstation needs that `artifacts-os` still does not provide
(or provides only partially). Items closed since 2026-04-29 are marked
with a striked heading and a "closed by" pointer.

### 3.1 Lifecycle / workflow semantics — openstation-owned ✅ unchanged

Per CLAUDE.md: "No lifecycle logic in `cli`". These belong in
openstation:

- State machine (`VALID_TRANSITIONS`, `_STATUS_RANK`, `_MIN_PARENT_STATUS`)
- Sub-task model — `parent` / `subtasks` wikilinks, blocking rule, parent auto-promotion, all-done promotion
- Dependency model — `depends_on` wikilinks blocking `ready`
- Ownership rules — `owner: user|agent`, who may transition `review→verified`, `verified→done`
- Pre-review checklist sections — Findings, Downstream, Progress, Verification
- `/openstation.*` slash commands

`artifacts-os` `KindDef.statuses` is just a list — no notion of legal
transitions. That is the right boundary, **and the events stream
makes it cleanly observable from a higher layer**: a state-machine
enforcer can subscribe to `artifact.status_changed` via
`register_emitter` and veto by raising in a `phase: pre`
`blocking: true` bundle hook.

### 3.2 Agent execution & runs — no artifacts-os equivalent ✅ unchanged

- `run.py` (2,445 LOC) — by-task / by-agent / by-alert modes;
  execute/verify auto-detection; tmux/detached backend; budget,
  turns, cost; worktree pass-through; `--editor claude|opencode`;
  `--tools` merging
- `sessions.py` (419 LOC) + `state.py` (448 LOC) — SQLite `runs`
  table, `session_id`, lost-run GC, stale detection
- `cc-sessions` browser — Claude Code session file inspector
- `logs.py` (292 LOC) — stream-json log capture and replay

The `artifacts-os` `ai/` stub (spec `s2066`) remains a stub and
nothing in flight changes that. **Recommendation: keep entirely on
the openstation side.**

### 3.3 ~~Hooks — gap; could be a new artifacts-os module~~ **Closed** ✅

**Closed by** [[s0025-artifact-events]] (hooks shipped under
`src/artifacts_os/hooks/`, t0135) **and** [[s0032-hooks-via-artbook-distribution]]
(directory-bundle hook kind + `.active/` promotion + `host:`
dispatch — implemented across [[t0178-ship-hooks-via-artbook-distribution]] →
[[t0181-add-directory-storage-primitive-to]],
[[t0182-add-hook-kind-and-bundle]], and remaining sub-tasks; treated
as implemented per t0185 §1).

The shipped contract:

- `hooks` is a first-class artifact kind (`x-storage: directory`,
  `x-manifest-name: "{slug}.md"`, non-numbered). Bundles live
  at `artifacts/hooks/<slug>/<slug>.md` + sibling files.
- Each bundle carries a `host:` field. Reserved values:
  `artifacts-os` (this loader fires it) and `openstation` (foreign
  host — listed but **not fired** by the artifacts-os loader).
  Unknown values warn once and skip. s0032 D112 expresses an
  *aspiration* that openstation's loader will eventually walk the
  same `.active/` tree; the contract itself only requires that
  artifacts-os ignore non-`artifacts-os` hosts during fire.
- Activation is operator-owned via `artifacts/hooks/.active/<slug>`
  symlinks. Re-pull of a hook book preserves `.active/` state
  (s0032 §4.3).
- The legacy `artifacts.yaml hooks:` list coexists with a single
  soft-deprecation notice (s0032 D114).
- Six event types catalogue is extended to ten:
  `hook.fired`, `hook.failed`, `hook.promoted`, `hook.demoted`,
  `hook.pulled`, `hook.skipped`.

**Integration consequence:** openstation no longer needs to "push
hooks down into artifacts-os" — the mechanism is already there.
The remaining work is on the **openstation side**, and breaks into
two parts:

1. **Storage + schema (settled).** openstation hook bundles live under
   `artifacts/hooks/<slug>/`, carry `host: openstation`, and reuse
   the matcher/action manifest schema. openstation extends the
   matcher vocabulary (e.g. `status_transition`, `assignment_changed`)
   on its own side; the bundle on disk looks like every other hook.

2. **Activation model (open design question).** s0032's `.active/`
   directory is artifacts-os's activation registry. Openstation has
   three real choices for how to participate, and the audit does
   **not** assume any of them:

   | Option | Mechanism | Trade-off |
   |---|---|---|
   | **(a) Share `.active/`** | openstation loader walks `artifacts/hooks/.active/`, dispatches `host: openstation` entries | One operator gesture (`artifacts hooks promote`), one `hooks list` view across hosts, re-pull preservation already solved. Couples openstation's activation lifecycle to artifacts-os's slug-keyed-symlink primitive. |
   | **(b) Parallel registry** | openstation owns `.openstation/hooks/.active/` (or similar) and ignores artifacts-os's `.active/` | Clean ownership separation; openstation can choose a different activation granularity (per-status, per-assignee, …) that doesn't map to a slug toggle. Two registries to operate; bundles live in one repo subtree but get armed via another. |
   | **(c) No separate activation** | openstation fires every `host: openstation` bundle it discovers under `artifacts/hooks/` | Simplest model. Defeats the s0032 D107/D119 "pull is inert" property — pulling a hook book auto-arms every openstation hook with no operator opt-in. |

   The strongest argument for (a) is **unified operator UX**: one
   `artifacts hooks list`, one promote/demote verb, regardless of
   which loader fires the hook. The strongest argument for (b) is
   that openstation's natural activation granularity may not be
   "one slug at a time" — e.g. it may want activation scoped by
   `assignee:` or by task `type:`, which is awkward to encode as
   a symlink filename. (c) is included for completeness; it is
   likely the wrong answer for any system that pulls hook bundles
   from a distro, but right for openstation-internal hooks that
   ship in-tree.

   This decision belongs to openstation, not to artifacts-os, and
   should be settled before the openstation-side loader is built.
   See §7 "Needs further research" and Recommendation #2 below.

### 3.4 ~~Events log — gap; partial overlap with stub `log/` module~~ **Closed** ✅

**Closed by** [[s0025-artifact-events]] (events shipped:
[[t0135-implement-artifact-events-and-hooks]],
[[t0139-align-events-cli-with-list]],
[[t0140-implement-s0027-align-events-cli]],
[[t0141-docs-events-and-hooks-user]]).

What landed differs from the April audit's prediction in one
important way: **events shipped as its own module
(`src/artifacts_os/events/`), not inside `log/`**. The `log/` stub
remains — its purpose is the opt-in **operational log** for agent
runs (per `s0004`), distinct from the always-on artifact event
stream. The two are intentionally separated; openstation's
analogue would be:

| openstation today | artifacts-os module |
|---|---|
| `events.py` (CRUD-event JSONL) | `artifacts_os.events` (always-on, closed catalogue) |
| `logs.py` (per-run stream-json) | `artifacts_os.log` (still stub) |

The events catalogue is closed (`s0025` § C2) — adding event
types requires a spec revision. openstation-specific events
(`task.run_started`, `task.run_complete`, alert lifecycle) belong
in a **separate openstation catalogue**, emitted through the same
JSONL file via `register_emitter` and a documented `openstation.*`
namespace. This decouples openstation's catalogue cadence from
artifacts-os's release cadence.

### 3.5 Alerts subsystem — openstation-specific, keep on top ✅ unchanged

`alerts.py` + `heartbeat.py` (569 LOC) — connector types
(`reminder`, `internal`, `github`, `slack`, `telegram`), cron
schedules, event names, pause/resume. The kind `alert` is registered
like any other artifact, but its semantics (heartbeat-driven,
connector dispatch) are not generic. **Keep openstation-side. Alert
artifact storage uses artifacts-os primitives; trigger / dispatch
logic stays in openstation.** (Note: post-hooks-via-artbook,
alert dispatch could be expressed as `host: openstation`
hook bundles — but the connector clients still live openstation-side.)

### 3.6 ~~Init / scaffold — gap; partial overlap~~ **Mostly closed** 🟡

**Closed by** [[s0030-books-driven-init-flow]] +
[[s0029-artbook-mvp-distribution-model]] +
[[s0031-artbook-post-pull-artifact-promotion]] (shipping tasks:
[[t0150-artbook-distribution-model]],
[[t0163-artifacts-init-artbook-distro-integration]],
[[t0165-init-selection-driven-by-books]],
[[t0167-implement-books-driven-init-flow]],
[[t0173-implement-artbook-promotion-engine-and]]).

What's now in artifacts-os:

- Two-stage `artifacts init`: settings-tier select, then one
  multi-select prompt per book in the configured distro
  (docs/init-flow.md).
- `--distro <url>` (or `$ARTIFACTS_DISTRO_URL`), `--book NAME[:items]`
  repeatable, `-y` non-interactive, `--dry-run`, `--no-promote`,
  **`--openstation-compat`** flag (so openstation init can wrap it).
- Distros publish `agents`, `commands`, `skills`, `kinds` books
  with canonical-`dest:` + tool-shape-`promote:` separation.
  artifacts-os ships itself as a distro at the repo root
  (`artbook.yaml`).
- Per s0032 §8, distros can now also publish `kind: hook` books
  that land inert bundles in `artifacts/hooks/` for the operator
  to promote.

**Residual openstation-specific work** (the 🟡), after collapsing
per §6.1:

- CLAUDE.md managed-section injection (openstation tone, ownership)
- `.openstation/` directory creation — for **runtime state only**
  (state.db skeleton, run-capture dir). Not for user content.
- `worktree.symlinkDirectories` wiring
- doctor diagnostics deployment
- Inject the `openstation:` section into `artifacts.yaml` (replaces
  the standalone `openstation.yaml` write)

These remain openstation-specific. **Recommendation:** openstation
`init` becomes a thin wrapper that (1) calls
`artifacts init --openstation-compat --distro <openstation-defaults-repo>`,
(2) overlays the CLAUDE.md / `.openstation/` / `.claude/` symlinks.
The "everything heavy" path is now upstream.

### 3.7 Doctor / diagnostics — openstation-specific ✅ unchanged

`doctor.py` (675 LOC) — installation health checks, repair guidance.
No analogue in `artifacts-os`, no obvious need for one.

### 3.8 Worktrees — shared concern, complementary mechanisms ✅ unchanged

`artifacts-os` retains natural worktree support via `find_vault_root`
walking up to `artifacts.yaml` (now at project root). openstation
uses Claude CLI's `worktree.symlinkDirectories` setting and
`git rev-parse --show-toplevel`. **Recommendation unchanged:
artifacts-os keeps walk-up; openstation overlays the Claude-symlink
mechanism.**

### 3.9 ~~Naming / ID convention drift — active divergence~~ **Closed on the artifacts-os side; divergence persists on openstation's** 🟡

**Closed by** [[t0037-redefine-name-field-as-slug]] (done 2026-04-29
— the day after this audit was written). Current artifacts-os
convention is **locked**:

| Aspect | artifacts-os (locked) | openstation (unchanged) |
|---|---|---|
| Task filename | `t0042-fix-bug.md` (prefixed) | `0042-fix-bug.md` (unprefixed) |
| Task `name` field | **slug only** (`fix-bug`) | `0042-fix-bug` (full stem) |
| `id` field | `t0042` (stored explicitly) | not stored — derived from filename |
| Numbering scope | per-kind, prefix-disambiguated | per-kind, prefix-less collisions avoided by separate dirs |

The kind schemas now enforce this: `task/kind.json` has
`"id": {"pattern": "^t\\d{4}$"}` and
`"name": {"description": "Slug portion of the file stem (no id prefix)."}`.

The divergence is no longer "in-flight on artifacts-os" — it is
"openstation has not yet aligned". Two paths exist:

1. **openstation aligns** — rename task files to `t0042-...`,
   add explicit `id: t0042` field, set `name` to slug only.
   Large diff; breaks existing wikilinks unless redirected.
2. **openstation registers its own KindDef** with `prefix=""` and
   a different `name` semantic. `core.ids.next_prefixed_id`
   handles `prefix=""` correctly (see §5).

Path 1 is the cleaner long-term answer; path 2 unblocks the
integration sooner.

### 3.10 Frontmatter field set — partial overlap; converging 🟡

artifacts-os `task/kind.json` now declares all the
"openstation-enriched" fields with proper JSON-schema patterns:
`parent` (wikilink), `subtasks` (array of wikilinks),
`depends_on` (array of wikilinks), `artifacts` (array of wikilinks),
`scheduled`, `started`, `completed`, `priority`. openstation's
extras still not in artifacts-os: `type` enum (different
vocabularies), `allowed-tools`. **Recommendation: openstation
overrides only the fields that diverge by declaring its own
`task/kind.json` in its own distro, leaning on artifacts-os's
folder-form kind loading.**

### 3.11 Wikilink semantics — partial overlap; still openstation-side 🟡

artifacts-os now declares wikilink fields **at the schema level**
(`pattern: ^\[\[.+\]\]$` on `parent`, `subtasks`, `depends_on`,
`artifacts`) but the resolver (`core.discover.resolve`) does **not**
strip `[[…]]` before lookup — callers must pre-strip. openstation
universally pre-strips today, so the integration cost is small but
nonzero.

**Recommendation:** add a thin `resolve_wikilink` helper to
`core.discover` (or a `wikilink=True` flag on `resolve`) so the
strip happens once, in core, behind a documented seam. This is
cheap, well-scoped, and removes the "openstation needs a wrapper"
caveat across every consumer.

## 4. Coverage matrix at a glance

| Concern | artifacts-os | openstation | Decision |
|---|:-:|:-:|---|
| Vault discovery | ✅ root-marker | ✅ different strategy | Use artifacts-os; openstation overlays Claude symlinks |
| Frontmatter parse/write | ✅ | ✅ | Replace openstation's with artifacts-os |
| Atomic file ops | ✅ (file + directory storage) | ✅ | Replace |
| Per-kind ID counter | ✅ (handles `prefix=""`) | ✅ | Replace |
| Reference resolution | ✅ (strip wikilink TBD) | ✅ | Replace (after small `resolve_wikilink` helper) |
| Kind registry | ✅ folder form (`kind.json` + `ARTIFACT.md`) | ✅ hardcoded dict | Replace; declare openstation kinds via folder form in openstation distro |
| List / filter | ✅ | ✅ | Replace |
| Frontmatter validation | ✅ | partial | Replace |
| Checklist verify | ✅ | ✅ | Replace |
| Field specs / column parse | ✅ | ✅ | Replace |
| Table rendering | ✅ + tree layout | ✅ | Replace |
| Named / default views | ✅ extensible | ✅ ad-hoc | Replace; openstation owns its sections via `from_base` |
| Settings loader | ✅ extensible | ✅ ad-hoc | Replace; openstation owns its sections via `from_base` |
| Status state machine | ❌ (intentional) | ✅ | Keep openstation-side; observe via events |
| Sub-task / parent / depends_on | 🟡 schema-level only | ✅ enforced | Keep enforcement openstation-side; schema in shared kind defs |
| Ownership rules | ❌ | ✅ | Keep openstation-side |
| Slash commands | ✅ `/artifacts.*` (`artifacts.create`, `artifacts.list`, `artifacts.show`) | ✅ ~21 `/openstation.*` | Both stay; different surfaces |
| Run / agent execution | stub `ai/` | ✅ | Keep openstation-side |
| Sessions / state.db | ❌ | ✅ | Keep openstation-side |
| **Hooks** | ✅ yaml-list + `kind: hook` bundles + `host:` dispatch | ✅ openstation-internal | openstation absorbs `kind: hook` storage + manifest schema and deletes its in-house bundle/matcher plumbing. **Activation model (share `.active/` vs parallel registry vs none) is an open openstation-side design decision** — see §3.3. |
| **Events log** | ✅ always-on, closed catalogue | ✅ in-house | openstation absorbs `artifacts_os.events`; declares its own `openstation.*` event namespace; emits via `register_emitter` |
| Alerts / heartbeat | ❌ | ✅ | Keep openstation-side (dispatch could express as `host: openstation` hooks) |
| Init / scaffold | ✅ books-driven + `--openstation-compat` | ✅ heavy: CLAUDE.md, `.claude/`, agents | Layer: openstation init wraps `artifacts init --openstation-compat` |
| **Distribution model** | ✅ artbook + promotion | ❌ | openstation publishes its own distro; consumers `artifacts book pull` it |
| Doctor | ❌ | ✅ | Keep openstation-side |
| Worktrees | ✅ walk-up | ✅ Claude symlinks | Both — complementary |
| TUI browser | stub `tui/` | ❌ | Future artifacts-os-side win |
| Wikilinks | 🟡 schema-only, no strip helper | ✅ | Push small helper into core; keep openstation-side resolution wrapper until then |

## 5. Concrete divergences that block direct integration (rechecked)

Original blockers, re-evaluated 2026-05-24:

1. **Task filename prefix.** ✅ **Confirmed resolvable.**
   `core.ids.next_prefixed_id` handles `prefix=""` cleanly — the regex
   becomes `^(\d+)-` and matches openstation's `0042-foo-bar` filenames
   without modification. openstation can declare
   `KindDef(prefix="", numbered=True)` for tasks today. (The original
   audit flagged this as "needs research" — closed.)

2. **`name` vs `id` fields.** 🟡 **artifacts-os locked; openstation
   unchanged.** Per [[t0037-redefine-name-field-as-slug]] (done) the
   artifacts-os shape is `name = slug`, `id = <prefix><NNNN>` (stored
   explicitly). openstation still stores `name = "0042-foo"` (full
   stem) with no separate `id`. The reconciliation work is now
   purely openstation-side — a one-time frontmatter rewrite.

3. **Vault marker location.** ✅ **Resolvable by collapse — see §6
   "Vault layout".** artifacts-os marker is `artifacts.yaml` at
   project root (per [[t0137-implement-vault-marker-relocation-per]];
   [[t0134-spec-relocate-vault-marker-to]] was rejected in favour of
   the direct relocation). Under the recommended collapse,
   openstation has no separate vault marker: it's recognised by the
   presence of an `openstation:` section in `artifacts.yaml`. The
   `.openstation/` directory still exists, but as a sibling for
   **runtime state only** (state.db, run captures) — not as a
   discovery marker. `find_vault_root` is unchanged.

4. **Storage root.** ✅ **Resolvable by collapse — see §6
   "Vault layout".** The user-facing `openstation/` data tree
   (`openstation/tasks/`, `openstation/agents/`, …) dissolves into
   `artifacts/` with openstation-extended kind schemas registered
   via folder-form `artifacts/kinds/<name>/kind.json`. After
   collapse: artifacts under `artifacts/`, openstation runtime
   state under `.openstation/`, no overlap. The legacy
   `openstation → artifacts` compat symlink (removed in the
   meantime) is no longer needed and won't be re-introduced.

5. **Wikilink-aware fields.** 🟡 **Partly closed at the schema
   level.** artifacts-os declares wikilink patterns at the kind
   schema layer; `core.discover.resolve` still requires
   pre-stripping. **Recommended:** small `resolve(..., wikilink=True)`
   addition to core. Until then, an openstation-side strip wrapper
   suffices.

## 6. Recommended integration shape

A layered dependency, not a merger. **Refreshed module list:**

```
                 ┌─────────────────────────────────────────────┐
                 │  openstation (task harness)                 │
                 │  - lifecycle state machine                  │
                 │  - sub-tasks, parent, depends_on enforcement│
                 │  - ownership / verification                 │
                 │  - runs / sessions / state.db               │
                 │  - alerts / heartbeat                       │
                 │  - slash commands /openstation.*            │
                 │  - doctor                                   │
                 │  - init overlay: CLAUDE.md, .claude/,       │
                 │    .openstation/ (runtime state only)       │
                 │  - openstation hook loader (host: openstation)│
                 │  - openstation events namespace via         │
                 │    register_emitter                         │
                 │  - openstation defaults distro              │
                 └────────────┬────────────────────────────────┘
                              │ depends on
                              ▼
                 ┌─────────────────────────────────────────────┐
                 │  artifacts-os (shipped today)               │
                 │  core   — vault (root marker), registry,    │
                 │           CRUD, validate, file + directory  │
                 │           storage                           │
                 │  events — closed catalogue + JSONL stream + │
                 │           register_emitter (✓)              │
                 │  hooks  — yaml list + kind:hook bundles +   │
                 │           .active/ + host: dispatch (✓)     │
                 │  views  — table + tree render, field specs (✓)│
                 │  cli    — artifacts CLI + init + book (✓)   │
                 │  log    — (stub) opt-in run logs            │
                 │  ai     — (stub) future                     │
                 │  tui    — (stub) future                     │
                 └─────────────────────────────────────────────┘
```

### 6.1 Vault layout (collapsed)

The original audit treated `artifacts/`, `openstation/`, and
`.openstation/` as three parallel trees that needed cohabitation
rules. After the integration, the rule is much simpler: **`artifacts/`
contains artifacts only; `.openstation/` contains openstation
runtime state; nothing else lives at the project root.**

```
<project-root>/
├── artifacts.yaml            ← single vault marker + settings
│                                (includes openstation: section
│                                 via Settings.from_base)
├── artifacts/                ← artifacts only (frontmatter+body MD)
│   ├── tasks/                  - openstation-extended task kind
│   ├── agents/                 - shared kind, openstation-enriched schema
│   ├── research/
│   ├── specs/
│   ├── notes/
│   ├── hooks/                  - kind: hook bundles (s0032)
│   │   ├── auto-commit/
│   │   │   └── auto-commit.md  (host: artifacts-os or openstation)
│   │   └── .active/            - operator-promoted activations
│   ├── kinds/                  - folder-form kind definitions
│   │   └── task/{kind.json, ARTIFACT.md}
│   ├── commands/               - slash commands (artifacts) + promoted
│   ├── skills/                 - skills + promoted
│   └── logs/
│       └── events/             - artifacts-os always-on JSONL stream
│                                  + openstation.* events via
│                                    register_emitter
└── .openstation/             ← openstation runtime state only
    ├── state.db                - SQLite runs table, sessions
    ├── state.db-shm
    ├── state.db-wal
    └── logs/
        └── runs/               - per-run stream-json capture
                                  (interim, until log/ module ships)
```

**What dissolves from today's layout:**

| Today | After collapse |
|---|---|
| `openstation/tasks/`, `agents/`, `research/`, `specs/`, `notes/`, `hooks/`, `logs/`, `kinds/` (whole tree) | Merged into `artifacts/<kind>/` with openstation-extended kind schemas registered via `artifacts/kinds/<name>/kind.json` |
| `.openstation/agents/`, `.openstation/skills/`, `.openstation/commands/` | Canonical under `artifacts/`, promoted to `.claude/` (and to `.openstation/<...>/` only if the openstation runtime needs to read them — typically it doesn't) via artbook `promote:` symlinks |
| `.openstation/events/*.jsonl` | Merged into `artifacts/logs/events/` via `register_emitter`; openstation declares `openstation.*` event namespace |
| `.openstation/docs/` | Ship with the openstation **package**, not the vault (analogous to artifacts-os docs in the artifacts-os package) |
| `.openstation/openstation.yaml` | Folded into `artifacts.yaml` under an `openstation:` section, parsed via `Settings.from_base` (same pattern as `EventsSettings`, `ViewsSettings`) |

**What stays in `.openstation/`:**

| Item | Reason it doesn't belong under `artifacts/` |
|---|---|
| `state.db` (+ `-shm`, `-wal`) | Operational state, not an artifact. Hidden so it doesn't surface in `artifacts list`. |
| Per-run stream-json captures (interim) | Same reason — operational, not artifact. Move to `artifacts_os.log` (under `artifacts/logs/runs/` or wherever the log module lands) once that module ships. |
| Any future doctor cache / lock files | Same reason — runtime, not artifact. |

This collapse closes §5 divergences #3 (vault marker) and #4
(storage root) at the cost of a one-time openstation-side
migration. Init becomes a one-shot setup that creates an
`artifacts.yaml` with an `openstation:` section and an empty
`.openstation/` for state.

**The three "net-new artifacts-os specs implied" by the original
audit have all landed (or are spec-locked):**

| Original gap | Status |
|---|---|
| `hooks` module | **Shipped** ([[s0025-artifact-events]]) and **extended for distribution** ([[s0032-hooks-via-artbook-distribution]] — spec-locked, sub-tasks landing under [[t0178-ship-hooks-via-artbook-distribution]]). |
| `log` module fleshed out | **Reshaped and shipped under a different name** — events live in `artifacts_os.events`, not `log/`. The `log/` stub remains as the operational-run-log API. |
| Vault marker negotiation | **Closed by relocation + collapse** — artifacts-os marker now at project root (`artifacts.yaml`); under the recommended collapse (§6.1) there is no second marker. openstation is recognised by an `openstation:` section in `artifacts.yaml`, not by a dedicated marker file. |

**The remaining openstation-side migration tasks** (was: two) become
**five concrete decisions** (see §"Recommendations" below).

## 7. Risks & uncertainties (rechecked)

- **Decided (unchanged):** `artifacts-os` is the right substrate. Its
  layered DAG, atomic-write discipline, extensible settings/registry,
  and now its events + hooks + artbook plumbing already cover the
  generic primitives openstation re-implements.
- **Decided (new since 2026-04-29):** the events catalogue is **closed**
  by spec (`s0025` § C2). openstation must declare an `openstation.*`
  catalogue separately if it wants new event types; it cannot extend
  `artifact.*` or `hook.*` directly.
- **Decided (new):** the hooks substrate is `host:`-dispatched
  ([[s0032-hooks-via-artbook-distribution]] D112–D113). openstation
  gets a reserved host name; the artifacts-os loader ignores
  non-`artifacts-os` hosts during fire, leaving openstation free
  to ship its own loader without forking artifacts-os.
- **Recommended:** openstation absorbs `artifacts_os.events` and
  the `kind: hook` storage / manifest schema from `artifacts_os.hooks`,
  rather than maintaining parallel implementations. The compatibility
  surface for `host: openstation` matchers is the only place
  openstation needs to extend the artifacts-os contract.
- **Needs further research:**
  - **Openstation activation model for hooks.** Three options
    (share `.active/` ↔ parallel `.openstation/hooks/.active/` ↔
    no separate activation) are laid out in §3.3. Each has real
    trade-offs; the choice depends on whether openstation's
    natural activation granularity is per-slug (favours share)
    or per-attribute like `assignee:`/`type:` (favours parallel).
    Must be settled before the openstation loader is built.
  - **Wikilink resolver placement.** Worth adding a `wikilink=True`
    flag to `core.discover.resolve` rather than duplicating the
    strip in every consumer? Small surface change, but it crosses
    a "core stays string-typed" boundary. Decision blocks
    decommissioning the openstation wrapper.
  - **openstation distro shape.** Should `host: openstation` hook
    bundles ship in the openstation defaults distro, or in a
    separate `openstation-hooks` distro that consumers opt into?
    Affects [[n0017-hook-scripts-not-installed-in-consumer]] — the
    inciting papercut.
  - **Migration cost for openstation's existing tasks.** Concrete
    count: ~438 task files (as of original audit). One-time rewrite
    or per-kind tolerance config in openstation? Now that artifacts-os
    has locked the convention, the per-kind tolerance path is
    available but is technical debt; a one-time rewrite (path 1 in
    §3.9) is cleaner.

## Recommendations (next steps — refreshed)

The original recommendations have all been acted on or superseded.
Refreshed list:

1. **openstation absorbs `artifacts_os.events`.** Replace `events.py`
   and `events_cli.py` with a thin openstation event namespace that
   emits through `register_emitter`. Declare `openstation.task_run_started`,
   `openstation.task_run_complete`, alert lifecycle, etc. as a
   separate, openstation-owned catalogue. Inherit the daily-JSONL
   stream, `--follow`/`--tail`/`--since`/`--event` CLI, and the
   `register_emitter` extension point for free.

2. **openstation ships `host: openstation` hook bundles via an
   openstation-defaults distro, and decides on an activation model.**
   Author the openstation matcher vocabulary (`status_transition`,
   `assignment_changed`, …) as `host: openstation` bundle manifests
   under `artifacts/hooks/<slug>/` and publish via `kind: hook`
   books (s0032 §8). The storage / schema half is settled.

   The **activation half is an open design decision** (§3.3): share
   `.active/` with the artifacts-os loader, run a parallel
   `.openstation/hooks/.active/` registry, or use no separate
   activation. Pick one before building the loader. Default
   recommendation (lowest-friction, highest-UX-coherence) is to
   share `.active/` and live with the slug-keyed activation
   granularity, but reasonable arguments exist for both
   alternatives; the call is openstation's.

   This closes [[n0017-hook-scripts-not-installed-in-consumer]].

3. **openstation init becomes a wrapper around
   `artifacts init --openstation-compat`.** Stop maintaining
   parallel scaffolding logic; let artifacts-os handle settings
   tier + book pull + promotion symlinks. Overlay only the
   openstation-specific bits (CLAUDE.md managed section,
   `.openstation/` dir, doctor seed data).

4. **openstation aligns task naming with artifacts-os.** Either
   one-time rewrite (`0042-foo` → `t0042-foo` + add explicit
   `id: t0042`, set `name` to slug only — preferred), or declare
   `KindDef(prefix="", numbered=True)` and live with the divergence.
   `core.ids.next_prefixed_id` supports `prefix=""` today, so
   path 2 is unblocked even without a rewrite.

5. **openstation collapses into the artifacts-os vault.** Drop the
   parallel `openstation/` data tree and the `.openstation/`
   user-content subdirs (`agents/`, `skills/`, `commands/`, `docs/`,
   `events/`, `openstation.yaml`). After collapse:

   - All openstation artifacts (tasks, agents, research, specs,
     notes, hooks) live under `artifacts/` with openstation-extended
     kind schemas registered via folder-form `artifacts/kinds/<name>/kind.json`.
   - Settings fold into `artifacts.yaml` under an `openstation:`
     section, parsed by an `OpenstationSettings.from_base(base)`
     extension class (same pattern as `EventsSettings` /
     `ViewsSettings`). `openstation:` section presence is the
     "this is an openstation vault" sentinel.
   - **`.openstation/` stays, but for runtime state only** —
     `state.db` + sidecars, per-run stream-json captures (until
     `log/` module ships and they migrate to `artifacts/logs/runs/`),
     any future doctor cache. Nothing user-facing, nothing that
     should show up in `artifacts list`.
   - openstation framework docs (today under `.openstation/docs/`)
     ship with the openstation Python package, not in the vault.

   Concrete migration: one-time openstation tool that moves
   `openstation/<kind>/*.md` → `artifacts/<kind>/*.md`, rewrites
   the frontmatter to match the locked `name = slug, id = t0042`
   convention (Rec #4), deletes the obsolete `.openstation/`
   subdirs, and merges `openstation.yaml` into `artifacts.yaml`
   under the new `openstation:` section. Wikilinks are stable
   because the file stem is unchanged from the openstation side
   (post-naming-alignment).

   This obsoletes the original audit's "two-markers / negotiation"
   framing entirely — there is one vault, one marker, one settings
   file, with two consumers (`artifacts` and `openstation` CLIs)
   reading from the same root.

6. **Add `resolve(..., wikilink=True)` to `artifacts_os.core.discover`.**
   Small, self-contained change. Removes the openstation-side
   strip wrapper and lets every consumer (including third-party
   ones) resolve `parent` / `subtasks` / `depends_on` fields
   directly without knowing the wikilink convention. Schedule
   alongside / after t0178 lands; no current task tracks this.

## Sources

In this repo (`artifacts-os`):

### Docs

- `README.md`
- `docs/architecture.md`
- `docs/settings.md`
- `docs/adding-a-kind.md`
- `docs/creating-an-artifact.md`
- `docs/events.md` *(new since 2026-04-29)*
- `docs/hooks.md` *(new)*
- `docs/artbook.md` *(new)*
- `docs/init-flow.md` *(new)*
- `docs/migration.md` *(new — vault marker relocation)*

### Module READMEs

- `src/artifacts_os/core/README.md`
- `src/artifacts_os/views/README.md`
- `src/artifacts_os/cli/README.md`

### Kind definitions (folder form per [[t0142-drop-legacy-flat-kind-schema]])

- `artifacts/kinds/task/{kind.json, ARTIFACT.md}`
- `artifacts/kinds/agent/{kind.json, ARTIFACT.md}`
- `artifacts/kinds/research/{kind.json, ARTIFACT.md}`
- `artifacts/kinds/spec/{kind.json, ARTIFACT.md}`
- `artifacts/kinds/note/{kind.json, ARTIFACT.md}`
- `artifacts/kinds/hook/{kind.json, ARTIFACT.md}` *(new — per s0032)*

### Specs (relevant to the integration)

- [[s0022-tree-layout]] — tree render in `views`
- [[s0025-artifact-events]] — closed catalogue + hooks layer
- [[s0026-vault-marker-at-root]] — `artifacts.yaml` at project root
- [[s0027-align-events-cli-with-list]] — CLI flag alignment
- [[s0029-artbook-mvp-distribution-model]] — `artbook.yaml` + book pull
- [[s0030-books-driven-init-flow]] — two-stage init
- [[s0031-artbook-post-pull-artifact-promotion]] — promotion engine
- [[s0032-hooks-via-artbook-distribution]] — `kind: hook` + `.active/` + `host:`
- `s2060-artifacts-os-architecture`, `s2061-artifacts-os-module-system`
- `s2063` (`log/` stub), `s2065` (`tui/` stub), `s2066` (`ai/` stub)

### Source files

- `src/artifacts_os/core/ids.py` (confirmed `next_prefixed_id`
  handles `prefix=""`)
- `src/artifacts_os/core/vault.py` (root-marker walk-up)
- `src/artifacts_os/events/{catalog.py, stream.py, settings.py}`
- `src/artifacts_os/hooks/{loader.py, actions.py, promotion.py, settings.py}`
- `src/artifacts_os/artbook/{manifest.py, pull.py, placement.py, state.py}`
- `src/artifacts_os/cli/commands/{hooks.py, book.py, events.py, init.py}`
- `artbook.yaml` (the repo's own distro manifest)

In the sibling `open-station` repo (spot-checked, not re-surveyed
— per t0185 scope):

- `README.md`
- `.openstation/docs/{lifecycle,task.spec,storage-query-layer,artifacts,cli,settings,hooks,events,sessions,worktrees}.md`
- `.openstation/skills/openstation-execute/SKILL.md`
- `src/openstation/registry.py`
- `src/openstation/core.py`
- LOC counts via `wc -l` over `src/openstation/*.py`

### Removed since 2026-04-29

- `artifacts/kinds/*.json` (flat form) — replaced by folder form
  per [[t0142-drop-legacy-flat-kind-schema]]. Cite the folder-form
  paths above instead.
- `artifacts/artifacts.yaml` — relocated to project-root
  `artifacts.yaml` per [[t0137-implement-vault-marker-relocation-per]].