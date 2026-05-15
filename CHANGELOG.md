# Changelog

## v0.4.0

Fourth release of **artifacts-os**. Headline feature: a new **artbook**
module that distributes opinionated bundles of agents, skills, kinds,
and templates into a vault — turning artifacts-os into a portable
harness. Also: `artifacts book` CLI, `--distro/--books` flags on
`init`, array wikilink field support in `create`, and the legacy
flat-kind schema removed.

### Architecture

- **Artbook module (s0029)** — new `src/artifacts_os/artbook/` package
  for declarative artifact bundles. A book manifest (`artbook.yaml`)
  describes a distro and its books; `artifacts book pull` fetches and
  places them into a target vault. Supports local-path and registry
  sources, item-level filtering, and recursive folder books (t0151,
  t0152, t0153, t0157, t0158, t0160, t0150).
- **Drop legacy flat kind schema (t0142)** — kinds now live
  exclusively under `artifacts/kinds/<kind>/kind.json` (with optional
  `ARTIFACT.md` body template). The old flat
  `artifacts/kinds/<kind>.json` shape is no longer accepted by the
  registry; migrate by moving each file into its own directory.

### Artbook

- **`artifacts book` CLI** — `list`, `show`, and `pull` operations
  over an artbook manifest. `pull` accepts item-level filters and
  walks recursive folder books (t0154, t0160, t0162).
- **v2 manifest schema** — `version: 1` manifest with typed `books`
  entries (D24, D25). See [`docs/artbook.md`](docs/artbook.md).

### CLI

- **`artifacts init --distro` / `--books`** — bootstrap a vault with
  one or more artbooks pulled inline at init time (t0163).
- **Array wikilink fields in `create` (t0161)** — `create` now parses
  list-valued wikilink fields (e.g. `subtasks: "[[t0001]], [[t0002]]"`)
  and writes parent-subtask backlinks automatically.

### Core

- **ItemMeta base class (t0152)** — core models refactored around a
  shared `ItemMeta` parent, generalizing `render_table` across views
  and unblocking artbook item rendering.

### Fix

- **Harden discover against malformed frontmatter** — `discover` no
  longer crashes on artifacts with unparseable frontmatter; affected
  files are skipped with a warning.

### Install

- **Version bump** — `pyproject.toml` to `0.4.0`.

## v0.3.0

Third release of **artifacts-os**. Headline features: a new artifact
**event stream** and declarative **hooks** layer that observe every
CRUD operation and run user-defined side-effects; the **vault marker
relocated** to the project root (one-line migration required); and a
new `artifacts events` CLI for tailing the event log.

### Architecture

- **Event stream + hooks layer (s0025)** — every `create`, `update`,
  status change, and `validate` call emits a typed event through a
  central dispatcher. Hooks subscribe declaratively in
  `artifacts.yaml` and run in `pre` or `post` phase, with
  `BlockedByPreHook` aborting the operation when a blocking pre-hook
  fails. New `src/artifacts_os/events/` and `src/artifacts_os/hooks/`
  modules implement the dispatcher, catalog, JSONL stream writer,
  hook loader, and built-in actions (t0130, t0135, t0136).
- **Vault marker relocated to project root (s0026)** — `artifacts.yaml`
  now lives at `<vault-root>/artifacts.yaml` instead of
  `<vault-root>/artifacts/artifacts.yaml`. Hard cutover, pre-1.0;
  existing vaults migrate with a one-line `git mv`. See
  [`docs/migration.md`](docs/migration.md) (t0132, t0137, t0138).

### Core

- **Dispatcher wired into store** — `store.create` and `store.update`
  call `_dispatch` for both pre and post phases, surfacing pre-hook
  failures as `BlockedByPreHook` errors and emitting every CRUD as
  a typed event (t0135).

### Events

- **Closed event catalog** — six event types:
  `artifact.created`, `artifact.updated`, `artifact.status_changed`,
  `artifact.validated`, `hook.fired`, `hook.failed`. Each fires
  after its operation; pre-phase events are not persisted. The
  catalog is closed — new types require a spec revision.
- **Daily JSONL stream** — events append to
  `artifacts/logs/events/YYYY-MM-DD.jsonl`, one record per line,
  with ISO 8601 UTC timestamps. No configuration required; the
  stream is on as soon as the package is installed. Full reference
  in [`docs/events.md`](docs/events.md).

### Hooks

- **Declarative YAML hooks** — `hooks:` list in `artifacts.yaml`
  matches event type + payload fields and runs an action (shell,
  notification, file write). `pre` hooks can block operations;
  `post` hooks log warnings on failure. A reentrancy guard prevents
  catch-all hooks from recursing. Worked examples and full schema
  in [`docs/hooks.md`](docs/hooks.md).

### CLI

- **`artifacts events`** — tail the JSONL event log with the same
  flag shape as `artifacts list`. Defaults to a Rich table; `--json`
  emits raw JSONL; `--tail [N]` (default 50) slices after filters
  and sorts. Filter flags: `--since`, `--event`, `--kind`,
  `--status` (s0027, t0139, t0140).
- **`artifacts init` updated** — bootstraps the new marker location
  (`<vault-root>/artifacts.yaml`) and produces the standard data
  tree alongside it (t0137).

### Log

- **Log module aligned with events** — `src/artifacts_os/log/`
  documentation rewritten against the s0025 event-stream model;
  the operation-log surface now references the events catalog as
  the source of truth.

### Install

- **Version bump** — `pyproject.toml` to `0.3.0`.
- **Migration guide** — new [`docs/migration.md`](docs/migration.md)
  covering the v0.3.0 vault-marker move with the one-line `git mv`
  procedure.

## v0.2.0

Second release of **artifacts-os**. Headline features: `artifacts init`
bootstraps a fresh vault with kinds, agents, and Claude skills; a new
**tree layout** for hierarchical artifacts wired through `views`,
`core`, and the CLI's `--layout` flag; multi-value filters in
`artifacts list`; and a generic, task-aware `release-changelog` skill.
Two new agents (qa, product-manager brainstorming mode) and the
agent-template consolidation round out the release.

### Architecture

- **Agent template consolidation** — every agent spec now ships from a
  single source under `src/artifacts_os/templates/agents/` and is
  copied into the vault's `artifacts/agents/` on `artifacts init`.
  Eliminates the prior alias drift between in-tree and shipped copies
  (t0112).
- **Layout configuration relocated** — layouts live in
  `artifacts.yaml`'s `default_layouts` and `view.layout` /
  `view.parent_field`, no longer in `kind.json`. Resolution flows
  through a 4-rung chain documented in `docs/settings.md` and
  `src/artifacts_os/cli/README.md` (s0022, t0120, t0121, t0124).

### Core

- **Multi-value filters** — `artifacts list --status ready,in-progress`
  treats comma-separated values as OR within a key (s0023, t0127).
- **Tree-aware discovery** — `discover.py` exposes the data needed to
  compute parent/child relationships for the tree renderer (t0116).
- **Layout removed from `KindDef.meta`** — `kind.json` no longer carries
  `x-layouts`; `core` returns layout-free models and the views layer
  is the sole consumer of layout config (t0121, t0123).

### Views

- **Tree layout renderer** — new hierarchical layout for artifacts that
  declare a parent field. Ships alongside the existing table renderer
  through a registry (`LAYOUTS`) and a `Layout` protocol. Exposed as
  `render_tree`, `compute_tree`, and `TreeNote` from the public views
  API (s0022, t0116, t0122, t0123).
- **Prune modes for tree** — `strict`, `ancestors`, and `lenient`
  control how filtered nodes affect the rendered tree. Default is
  `strict`; `ancestors` keeps the path to a matched node visible
  (s0024, t0128, t0129).

### CLI

- **`artifacts init`** — bootstraps a vault: writes
  `artifacts/artifacts.yaml`, registers built-in kinds, lays down agent
  files, and installs the artifacts-os Claude skill into the local
  `.claude/` tree. Documented in `docs/init-flow.md` (s0021, t0108,
  t0110).
- **`--layout {table,tree}`** — `artifacts list` accepts an explicit
  layout flag; falls through to `default_layouts` in `artifacts.yaml`
  if unspecified. `-q` / `-j` are unaffected (t0117, t0124).
- **Multi-value filter syntax** — same comma-OR semantics as the core
  filter API, surfaced through every kind-specific filter flag (t0127).

### AI

- **`artifacts init` ships Claude skills** — the `artifacts-os` skill
  is installed into the vault's `.claude/skills/` tree at init time so
  agents can find the right entry point without manual setup (t0110).
- **Generic `release-changelog` skill** — task-aware and
  project-agnostic. Reads `CLAUDE.md`'s release section for domain
  categories and path mappings instead of hard-coding OpenStation
  conventions (t0104, t0106).
- **Tree-layout note in the artifacts-os skill** — one-paragraph guide
  to `--layout` and `default_layouts` so agents reach for the right
  knob when surfacing hierarchical artifacts (t0125).

### Agents

- **`qa` agent** — feature-verification agent definition added under
  `artifacts/agents/qa.md` and the templates tree (t0111).
- **product-manager brainstorming mode** — distinct ideation mode that
  forbids task creation and lifecycle mutations while permitting
  knowledge-capture writes (notes, research, strategy memos).
- **Specs published this cycle** — `s0021-artifacts-init-flow`,
  `s0022-tree-layout` (revised), `s0023-multi-value-filters`,
  `s0024-tree-prune-modes-strict-ancestors`, and the
  not-yet-implemented `s0025-artifact-events` (two-layer event stream
  + opt-in subscriber model).

## v0.1.0

First public release of **artifacts-os** — a Python library and CLI for
storing, discovering, and managing structured markdown artifacts
(tasks, specs, agents, research) in a vault directory. This release
ships the foundational `core` storage layer, the `views` formatting
layer, the `artifacts` CLI, and the `ai` extension surface for Claude
commands and skills, along with a release pipeline that publishes to
PyPI via Trusted Publishers.

### Architecture

- **Module dependency DAG** — `core` → `views` → `cli`, `tui`;
  `core` → `log` → `ai`. No peer imports outside declared deps; the
  CLI carries no lifecycle logic. Documented in
  [`docs/architecture.md`](docs/architecture.md).
- **ARTIFACT.md kinds extension layer** — every registered kind under
  `artifacts/kinds/<name>/` may ship an `ARTIFACT.md` describing the
  kind's intent, body skeleton, and variants. Bound by specs s0017
  (discovery) and s0018 (body loader). Provides agents a single
  per-kind extension surface without paying full cost on every
  invocation.
- **L1 kinds catalogue** — every kind exposes a one-line `description`
  and a `has_template` boolean through both the Python API
  (`KindCatalog.list_kinds()`) and the CLI (`artifacts kinds`).

### Core

- **Storage and registry** — atomic create (`O_CREAT | O_EXCL`) and
  update (`os.replace`); `update` is frontmatter-only with body
  preserved verbatim. Numbered (`t0042-fix-bug.md`) and non-numbered
  (`researcher.md`) artifact kinds.
- **Settings** — base-class + extension-subclass pattern parsed from
  `artifacts/artifacts.yaml`. Modules extend via a `from_base`
  classmethod without coupling to the library's release cycle. See
  [`docs/settings.md`](docs/settings.md).
- **Vault discovery** — `find_vault_root` walks up from CWD until it
  finds the `artifacts/artifacts.yaml` marker.
- **Unified filter API** — schema-derived filters across `list`/query
  paths so callers can filter by any frontmatter field defined on a
  kind.
- **Per-kind required fields and validation** — `kind.json`-driven
  schema with duplicate-name validation at registry load.
- **Kinds catalogue module** — new `core/kinds_catalog.py` with
  `KindCatalog` / `KindCatalogEntry` that read `ARTIFACT.md`
  frontmatter alongside `kind.json`.

### Views

- **Formatting layer** — column specs, field formatters, and Rich
  table rendering. `ViewsSettings` extends the base settings via
  `from_base`. Spec `s2062` locked the contract.
- **Named views** — view definitions live in vault settings; the CLI
  surfaces them via `artifacts list <view>` and `artifacts views`.

### CLI

- **`artifacts` command** — `init`, `list`, `show`, `create`,
  `status`, `validate`, `kinds`, `views`. Schema-derived filter flags
  are generated per-kind from `kind.json`.
- **`artifacts views`** — execute mode (`artifacts views <name>`) and
  detail mode for inspecting view definitions; replaces the earlier
  `views show` subcommand.
- **`artifacts kinds <name>`** — per-kind detail surface. Default
  output is the kind's `ARTIFACT.md` body; `--meta` adds metadata,
  `-j` emits JSON with `meta` and `body` keys; missing-template and
  unknown-kind cases handled with clear errors.
- **`artifacts create`** — kind-aware help; `created` auto-populated;
  default kind read from `artifacts.yaml`; positional title is
  shell-expansion safe.
- **Programmatic access** — `--meta` projection on `show`/`list` and
  schema-derived filters expose frontmatter and relationships for
  scripting.
- **`--version` / `-v`** — flag prints `artifacts_os.__version__`.
- **`artifacts init`** — sets up a vault and installs Claude commands
  and skills into the vault's `.claude/` tree.

### AI

- **Claude commands shipped in the wheel** — `/artifacts.create`,
  `/artifacts.show`, `/artifacts.list`, etc., live under
  `src/artifacts_os/ai/claude/commands/` and are installed into a
  vault's `.claude/commands/` by `artifacts init` (symlink default,
  copy fallback).
- **Skills shipped via wheel** — `artifacts-os` and `artifacts-release`
  skills under `src/artifacts_os/ai/claude/skills/` install into
  `.claude/skills/` the same way commands do.
- **`/artifacts.create` body loader** — slash command substitutes
  `{{TITLE}}` into the chosen kind's `## Skeleton` (or selected
  variant) per s0018; empty body when the kind has no `ARTIFACT.md`.
- **Per-kind `ARTIFACT.md` templates** — task, spec, research, agent
  kinds ship authored skeletons plus selection guidance.
- **Agent specs** — `product-manager`, `security-engineer`, plus the
  existing `developer`, `architect`, `researcher`, `author`,
  `project-manager`.

### Install

- **PyPI release pipeline** — `.github/workflows/release.yml` runs
  the pytest matrix (3.11 / 3.12 / 3.13), builds sdist + wheel,
  smoke-installs the wheel, creates the GitHub Release, and publishes
  via **PyPI Trusted Publishers (OIDC)** — no API token in the repo.
  Pre-release versions (`*a*`, `*b*`, `*rc*`) route to TestPyPI.
  Triggered by `chore: release v<version>` commits touching
  `pyproject.toml`, plus `workflow_dispatch`.
- **`artifacts-release` skill** — generates a task-aware changelog
  entry from conventional commits and the originating tasks'
  `## Findings`. Reads the `## Release` section in `CLAUDE.md` for
  domain categories, path mapping, and the release checklist.
- **PyPI metadata** — full project metadata in `pyproject.toml`,
  classifiers, keywords, and per-extra optional dependencies
  (`views`, `cli`, `tui`, `log`, `ai`, `all`).
- **MIT license** — added at repo root.
- **CI workflows** — GitHub Actions test matrix and Dependabot config.
- **`rich` promoted to base dependency** so the CLI works without
  optional extras.

### Fix

- **Restored failing test fixtures** for the `tests/ai/` install /
  list / uninstall suite after adding the second skill changed the
  installed-skill count (t0093).
- **Auto-commit hook** runs blocking instead of detached tmux to avoid
  hook-state races.
- **Vault marker restored** — `artifacts/artifacts.yaml` was
  inadvertently deleted; reinstated.
- **Skeleton sections restored** in `ARTIFACT.md` files after the
  thinner refactor regressed end-to-end skeleton coverage.
