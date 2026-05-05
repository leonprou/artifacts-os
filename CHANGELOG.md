# Changelog

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
