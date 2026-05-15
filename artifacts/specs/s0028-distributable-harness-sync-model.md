---
kind: spec
id: s0028
name: distributable-harness-sync-model
status: draft
task: "[[t0145-spec-the-distributable-harness-model]]"
created: 2026-05-14
agent: architect
---

# Distributable Harness Sync Model

Specifies the **distributable opinionated harness** for
artifacts-os: a single canonical catalogue inside the library, a
declarative consumer manifest that picks a subset, and an
`artifacts sync` command that materialises the chosen items into
the consumer's `.claude/`, `.openstation/`, `.opencode/`, and
`artifacts/` trees idempotently. Replaces today's hand-maintained
parallel copies (`.claude/agents/` ≡ `.openstation/agents/` ≡
`.opencode/agents/`, `artifacts/agents/` ≈
`src/.../templates/agents/`, `artifacts/kinds/` ≈
`src/.../templates/kinds/`) with sync output, and grows the
existing `artifacts_os.ai.install` machinery into a general
distribution model that covers kinds, agents, skills, commands,
hook recipes, settings tier, and per-harness manifests.

This spec is the design contract every subsequent milestone
(M2 – M6) of [[t0144-distributable-opinionated-harness-for-artifacts]]
builds against. M1 — the sync foundation — is implementable from
this spec alone.

## 1. Background and Cross-References

### 1.1 Producing artefacts

- **Parent feature** —
  [[t0144-distributable-opinionated-harness-for-artifacts]] —
  captures user-level intent (single source of truth, consumer
  picks subsets, drift detectable, this repo dogfoods).
- **This spec's task** —
  [[t0145-spec-the-distributable-harness-model]] — carries the
  nine scope items §§5–14 below address one-for-one.
- **Blocking research sub-task** —
  [[t0146-research-harness-footprints-and-current]] — closes
  the M7 unknowns from the parent (per-harness footprint,
  per-file classification, drift inventory, command-format
  portability, schema-extension precedents, `.opencode/` usage).
  Items in this spec marked **R[N]** depend on the research
  artefact landing before they can be promoted from
  `recommended` to `decided` (see §22).

### 1.2 Direct ancestors

- **Existing install machinery** —
  `src/artifacts_os/ai/install.py` (484 lines) — already
  implements namespace-scoped install/uninstall/list with
  link/copy modes, per-file actions
  (`install-link` / `install-copy` / `replace-link` / `skip` /
  `refuse` / `keep-foreign` / `remove`), and an `InstallReport`
  dataclass. The sync engine §§7–8 generalises this surface;
  it is not a rewrite from scratch.
- **Existing init flow** — [[s0021-artifacts-init-flow]] —
  defines `artifacts init`'s three-step prompt
  (tier/kinds/agents) and the bundled-template layout under
  `src/artifacts_os/templates/`. This spec **extends** that
  layout (§7) and reframes `init` as "manifest scaffolder +
  first sync" (§13), preserving the prompt UX.
- **Existing settings basis** — `artifacts.yaml` — gains a new
  top-level `harness:` block (§5). The `Settings`
  extension pattern from [[s0010-core-settings-module-spec]]
  is reused (a `HarnessManifest` dataclass with a
  `from_base` classmethod owned by a new `sync/` module).
- **Existing event system precedent** — [[s0025-artifact-events]]
  / [[t0136-artifact-event-and-hook-system]] — the
  "managed core + opt-in reactions" split this spec mirrors at
  the file-tree layer.

### 1.3 Out-of-scope (parent task verbatim)

- A separate distribution package (`artifacts-os-defaults`).
- Live updates without re-running sync.
- Cross-vault event federation, remote/webhook event delivery.
- Brand, license, IDE-config, language-toolchain templates.
- Replacing `artifacts init` entirely; `init` remains the
  bootstrap, `sync` is the ongoing operation.

## 2. Goals

1. **One canonical source per shipped item.** Every agent, kind,
   skill, command, hook recipe, settings preset, and harness
   manifest lives in exactly one path inside the wheel
   (`src/artifacts_os/templates/`). The parallel copies under
   `.claude/`, `.openstation/`, `.opencode/`, and
   `artifacts/{agents,kinds}/` become sync output.
2. **Consumers pick subsets by name.** A consumer manifest
   under the `harness:` key in `artifacts.yaml` declares which
   kinds, agents, skills, commands, hook recipes, and which
   harness targets the project wants. No item is mandatory;
   omitting any list installs none of that kind.
3. **Idempotent and safe.** `artifacts sync` is a one-shot
   operation that produces the same result regardless of the
   pre-existing state. Managed files are stamped (§9); user
   customisations live in an override layer (§11); runtime data
   (§12) is never touched.
4. **Drift detectable.** `artifacts sync --check` exits non-zero
   when any managed file diverges from the catalogue
   (post-override). Suitable for CI.
5. **Existing consumers can upgrade in place.** `pip install -U
   artifacts-os && artifacts sync` brings every consumer up to
   the new library version's harness without losing project-
   specific content.
6. **The dogfood vault converges by construction.** After M1
   lands and the migration (§14) is applied, this repo's
   `.claude/`, `.openstation/`, `.opencode/`, `artifacts/agents/`,
   `artifacts/kinds/` are 100 % sync output, with project-
   specific items (`qa.md`, and any others the researcher
   ratifies) routed through the override layer.

## 3. Non-Goals (this spec only)

- **No new templating language.** Variable interpolation
  uses the closed set from
  [[s0021-artifacts-init-flow]] §9
  (`{{project_name}}`, `{{project_alias}}`, `{{created}}`).
  Extending the variable list requires a spec amendment.
- **No remote catalogue fetch.** The catalogue ships in the
  wheel via `importlib.resources`; consumers receive new
  catalogue entries by upgrading the `artifacts-os` package.
- **No three-way merge.** Sync resolves conflicts by either
  taking the override (full file or per-key merge) or refusing
  to overwrite. No interactive resolution, no
  `.orig` / `.rej` files.
- **No watcher / live reload.** One-shot sync only — see
  parent task out-of-scope.
- **No automatic harness directory creation.** Sync only writes
  into a harness target if the consumer manifest opts in
  (§5). A consumer can have `.claude/` without `.opencode/`;
  sync writes only what the manifest declares.
- **No package separation of catalogue.** The catalogue stays
  inside the `artifacts-os` wheel for M1–M6. A separate
  `artifacts-os-defaults` package is deferred per parent task.

## 4. Locked Decisions Summary

| ID  | Decision | Rationale (brief) |
|-----|----------|-------------------|
| D1  | Consumer manifest lives at `artifacts.yaml :: harness:` (new top-level key). No separate `harness.yaml` file in v1. | One vault config to read; matches existing `views:` / `cli:` / `hooks:` keys; defer split to v2 if the key grows past ~30 lines. |
| D2  | Sync surface is one flat verb: `artifacts sync` with `--check`, `--dry-run`, `--target`, `--force`. No nested subcommands. | CLAUDE.md `## CLI Conventions` mandates flat verbs; `--check` is the universal "read-only" primitive paralleling pytest, ruff, terraform. |
| D3  | Catalogue layout extends today's `src/artifacts_os/templates/` with `skills/`, `commands/`, `hooks/`, `harnesses/` siblings to the existing `kinds/`, `agents/`, `settings/`. | Reuses the established `importlib.resources` anchor; `init` already reads this tree. |
| D4  | Per-harness manifest is a YAML file under `templates/harnesses/{name}.yaml` declaring `root`, `maps:` (catalogue→destination), and `marker_style`. | Static data; lets sync support a new harness by adding one file, no Python changes. |
| D5  | Managed-file marker is a single-line header stamp `<!-- artifacts-os:managed v1 src=<catalogue-path> sha256=<hex> -->` (comment form varies by file type, §9). | Single-line header is greppable, edit-detectable, and survives `git diff` cleanly; sidecar lock-file complements but does not replace. |
| D6  | Sidecar lock file `.artifacts-os/sync.lock` (YAML) records every managed path and its catalogue source + content hash at last sync. Source of truth for `--check`. | Lock file is the authoritative manifest of what sync owns. Headers are for humans; lock is for machines. |
| D7  | Override layer lives at `artifacts/overrides/<harness>/...` (mirrors the harness destination tree below the harness root). | Sibling to the vault makes overrides version-controllable; per-harness sub-tree keeps overrides scoped (an override applies to one render target, not all). |
| D8  | Merge semantics by file type: markdown / SKILL.md / .md commands → full-replace; YAML / JSON (kind schemas, settings, harness manifests) → deep-merge with override-wins; hybrid (CLAUDE.md, AGENTS.md) → fence-delimited zones. | Markdown has no structural merge that round-trips well; YAML/JSON deep-merge is well-defined; fences localise managed and user content in the same file. |
| D9  | Runtime-data exclusion is an explicit deny-list under each harness manifest (`runtime_paths:`), enforced before any read or write. Drift report never reports excluded paths. | Deny-list is auditable; allow-list would silently break when new runtime files are introduced (e.g. when events grew `state.db-shm`). |
| D10 | Sync refuses to overwrite a file that lacks a managed marker **and** is not in the lock file. Foreign files are reported and skipped. | Mirrors today's `_plan_action` `keep-foreign` behaviour; preserves the no-clobber invariant. |
| D11 | First sync after `init` is implicit (`init` calls `sync` internally). Standalone `artifacts sync` is the upgrade / re-render path. | One-shot bootstrap is the natural mental model; explicit re-sync is the ongoing maintenance verb. |
| D12 | This repo's existing hand-maintained mirrors are migrated by (a) staging the canonical catalogue, (b) routing project-specific files (`qa.md` and any others the researcher identifies) to `artifacts/overrides/`, (c) deleting the hand-maintained mirrors, (d) running `artifacts sync` once to regenerate them. Symlink-based mirror today becomes file-based render after migration. | Eliminates the symlink web without losing content; the override layer is the persistence point for any non-canonical asset. |
| D13 | Hash algorithm for markers and lock entries is SHA-256, hex-encoded, computed over the post-render byte stream (i.e. after variable interpolation). | Matches `ai/install.py :: _sha256`; deterministic; the post-render hash detects edits regardless of variable resolution. |
| D14 | `--check` is read-only and exits 1 on any drift (managed file edited, lock file missing/stale, foreign file in managed slot). Exit 0 = clean; exit 2 = usage error. | Single non-zero code keeps CI integrations simple; usage vs. drift split mirrors `ruff check`. |

## 5. Manifest Schema (Scope Item 1)

### 5.1 Location

The consumer manifest is a new top-level key `harness:` in
`artifacts.yaml`. No separate file in v1 (D1).

Why one file: today's vault config already aggregates four
domains (`project`, `views`, `default_views`, `cli`, optionally
`hooks`). Adding `harness:` keeps a single read; if it grows
past ~30 lines the v2 escape hatch is a `harness_file:` pointer
to an external file — defer until needed.

#### Disambiguation — two meanings of "harness"

The word *harness* is already overloaded in artifacts-os's
vocabulary, and this spec adds a third sense. Operators reading
`artifacts.yaml` should not mistake one for another:

| Sense | Meaning | Where it appears |
|-------|---------|------------------|
| Runtime harness | The AI tool / orchestrator (Claude Code, OpenStation, OpenCode) that reads what sync renders and runs against the vault. | Agent spec frontmatter ("the harness loads skill docs"), `kind.json` ("written by the harness on transition"), CLAUDE.md prose. |
| Project harness | The artifacts-os project as a whole, called "an agentic harness" in CLAUDE.md's opening line. | CLAUDE.md, README.md. |
| **Distribution harness (this spec)** | The opinionated bundle of files (agents, kinds, skills, commands, hook recipes, per-harness manifests) that sync materialises into one or more runtime-harness target directories. | `artifacts.yaml :: harness:` key (the manifest), `templates/harnesses/<name>.yaml` (per-target manifests), this spec. |

`harness:` in `artifacts.yaml` always means the **distribution
harness** (sense 3). It selects what runtime harnesses (sense 1)
receive which files. The single overload is intentional — the
distribution is a harness *of harness configs* — but the spec
disambiguates everywhere prose ambiguity could arise.

#### Key-collision audit

Inventory of every documented top-level key in `artifacts.yaml`
as of this spec's writing (sources: `docs/settings.md` § Public
API, Events, Hooks; `s0010`, `s0007`, `s0022`, `s0023`, `s0024`,
`s0025`):

| Top-level key | Owner module | Collides with `harness:` ? |
|---------------|--------------|-----------------------------|
| `layout_version` | core/settings.py | no |
| `project` | core/settings.py | no |
| `default_layouts` | views | no |
| `views` | views | no |
| `default_views` | views | no |
| `cli` | cli | no |
| `events` | events | no |
| `hooks` | hooks | **prose overlap — see §5.3 row `harness.hooks`** |

`harness:` is unclaimed. Adding it is strictly additive at the
parser level (extensions read from `base.raw[<key>]`; no key
sharing, no order-dependency — see [[s0010-core-settings-module-spec]]).

### 5.2 Schema

```yaml
# artifacts.yaml
layout_version: 1

project:
  name: artifacts-os
  created: 2026-04-20

# --- new in this spec ---
harness:
  # Settings tier — picks src/artifacts_os/templates/settings/<tier>.yaml
  # as the base for artifacts.yaml itself.  See §5.3.
  settings_tier: standard            # basic | standard | advanced

  # Catalogue subsets — each list names items by their catalogue stem.
  # Special tokens: "all" (every item in the catalogue),
  # "none" (empty selection — same as omitting the key or [] ).
  kinds:    [task, note, spec]
  agents:   [architect, developer, author]
  skills:   [artifacts-os, release-changelog]
  commands: all                      # all 26 artifacts.* / openstation.* commands
  hooks:    [auto-commit]            # opt-in recipe names (M6)

  # Targets — which harness directories sync renders into.  Each is a
  # boolean enable flag; the per-harness manifest at
  # src/artifacts_os/templates/harnesses/<name>.yaml owns the layout.
  targets:
    claude: true        # renders into .claude/
    openstation: true   # renders into .openstation/
    opencode: false     # renders into .opencode/   (held until R6)
    vault: true         # renders into artifacts/   (the vault itself)

  # Override scope — relative path under the vault for the override layer.
  # See §11.  Defaults to "artifacts/overrides" when omitted.
  overrides_dir: artifacts/overrides
```

### 5.3 Field semantics

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `harness.settings_tier` | str ∈ {basic, standard, advanced} | `standard` | Tier used to seed `artifacts.yaml`. Sync **does not rewrite** the consumer's `artifacts.yaml` body — the tier only controls what `init` writes on first run; on re-sync it is informational (manifest preset binding). |
| `harness.kinds` | list[str] \| "all" \| "none" | `[]` | Each entry is a sub-directory name under `templates/kinds/`. `"all"` expands at sync time to every directory there. Unknown name → exit 2. |
| `harness.agents` | list[str] \| "all" \| "none" | `[]` | Each entry is the stem of a file under `templates/agents/<name>.md`. |
| `harness.skills` | list[str] \| "all" \| "none" | `[]` | Each entry is the namespace dir under `templates/skills/<name>/SKILL.md`. |
| `harness.commands` | list[str] \| "all" \| "none" | `[]` | Each entry is the stem of a file under `templates/commands/<name>.md` (commands ship at the catalogue top-level, not per-harness — see §8 and R1). |
| `harness.hooks` | list[str] \| "all" \| "none" | `[]` | Each entry names a **recipe** under `templates/hooks/<name>.yaml`. **Distinct from the top-level `hooks:` key** (s0025) — that key holds the **runtime** hook list (matchers + actions); this key holds the **selector** of recipes sync should install. Sync deep-merges each chosen recipe into the top-level `hooks:` block on first install via the override-layer rules (§11.3). Recipes ship in M6; the key is reserved in M1. |
| `harness.targets.<name>` | bool | (see table below) | One key per harness manifest in `templates/harnesses/`. Unknown key → exit 2 with `unknown harness target '<name>'`. |
| `harness.overrides_dir` | path (vault-relative) | `artifacts/overrides` | Used by §11 lookup. Must not collide with a harness target root. |

Default `targets` map when the `targets:` block is omitted: every
harness manifest with `default_enabled: true` in its own metadata
is enabled. The shipped harnesses use:

| Harness | `default_enabled` | Rationale |
|---------|-------------------|-----------|
| claude | true | Universal target; if Claude Code isn't used, the consumer flips it off explicitly. |
| openstation | true | OpenStation CLI is the assumed driver of the vault. |
| opencode | false | OpenCode adoption is sparse; opt-in until R6 closes. |
| vault | true | The vault itself (`artifacts/`) is always a render target — eliminates today's `artifacts/agents/` ≡ `templates/agents/` duplication. The pseudo-target is named `vault` (not `artifacts`) so the key doesn't visually collide with the `artifacts/` directory or the `artifacts` CLI verb. |

#### Naming guideline for `targets:` keys

Harness target names should avoid reserved top-level keys
(`views`, `hooks`, `events`, `cli`, `project`, `default_views`,
`default_layouts`) to keep `harness.targets:` readable. The
validator does **not** enforce this — a harness manifest can be
named anything matching `templates/harnesses/<name>.yaml` — but
landing a harness called `views` would require a deliberate file
add and is discouraged by the catalogue review process.

### 5.4 Token expansion

`"all"` / `"none"` are expanded once, at sync planning time,
before any filesystem operation. Expansion sources:

| Subset | Source for `"all"` |
|--------|---------------------|
| `kinds` | every direct child dir of `templates/kinds/` containing a `kind.json`. |
| `agents` | every `*.md` file directly under `templates/agents/`. |
| `skills` | every direct child dir of `templates/skills/` containing a `SKILL.md`. |
| `commands` | every `*.md` file directly under `templates/commands/`. |
| `hooks` | every `*.yaml` file directly under `templates/hooks/`. |

This mirrors `init`'s `_discover_kinds` / `_discover_agents`
([[s0021-artifacts-init-flow]] §13.4).

### 5.5 Validation

Manifest validation runs **before** any filesystem write. Errors
abort with exit 2 and an actionable message:

```
error: unknown agent 'qa-developer' in harness.agents.
       Catalogue contains: architect, author, developer, devrel,
       project-manager, researcher, technical-writer.
       Add the agent to artifacts/overrides/agents/<name>.md to
       use a project-specific spec.
```

The validator never silently drops unknowns — every name must
either resolve in the catalogue or in the override layer (§11).

## 6. Sync Command Surface (Scope Item 2)

### 6.1 Synopsis

```
artifacts sync [--check] [--dry-run] [--target NAME]
              [--force] [--json]
```

### 6.2 Modes

| Mode | Writes? | Exit codes |
|------|---------|------------|
| (default) | yes | 0 ok, 1 partial-failure, 2 usage, 3 vault-not-initialised. |
| `--check` | no | 0 clean, 1 drift detected, 2 usage, 3 vault-not-initialised. |
| `--dry-run` | no | 0 (would-succeed) / 1 (would-fail) / 2 usage. Output prefixes every action with `[would]`. |

`--check` and `--dry-run` are mutually exclusive — passing both
exits 2 with `error: --check and --dry-run are mutually exclusive`.

### 6.3 Flags

| Flag | Type | Default | Behaviour |
|------|------|---------|-----------|
| `--check` | flag | off | Validate on-disk state against the catalogue + override layer. No writes. |
| `--dry-run` | flag | off | Plan writes, print actions with `[would]`, do not execute. |
| `--target NAME` | repeatable str | (all enabled in manifest) | Restrict to a single harness target (`--target claude --target openstation`). Unknown name → exit 2. |
| `--force` | flag | off | Overwrite files that lack the managed marker, **only** when the file is in the lock file (i.e. once sync owned it). Refuses to clobber files outside the lock under any flag combination. |
| `--json` | flag | off | Emit the `SyncReport` (§7.5) as JSON to stdout. Suppresses the human Rich table. |

### 6.4 Default (Rich-table) output

```
Sync plan — 3 targets, 24 files

Target       Action           Path                                      Source
.openstation install-copy     .openstation/agents/architect.md          templates/agents/architect.md
.openstation install-copy     .openstation/agents/developer.md          templates/agents/developer.md
.openstation skip             .openstation/agents/qa.md                 overrides/openstation/agents/qa.md
.claude      install-link     .claude/agents/architect.md               .openstation/agents/architect.md
…
artifacts    install-copy     artifacts/kinds/task/ARTIFACT.md          templates/kinds/task/ARTIFACT.md

Summary: 22 installed, 1 skipped (override), 1 kept-foreign, 0 refused.
```

Columns and styling follow the `list` / `events` precedent
(CLAUDE.md `## CLI Conventions`). `--json` switches to JSONL,
one action per line.

### 6.5 Idempotency guarantee

For a fixed catalogue + manifest + override layer, running
`artifacts sync` twice in a row produces:

1. Identical on-disk byte content.
2. Identical lock file content.
3. A second-run summary of `0 installed, N skipped (already
   synced), 0 refused`.

Property 3 is the testable contract — any non-skip action on the
second run is a bug (§17.5).

### 6.6 Ordering

Sync planning produces a totally ordered action list:

1. **Validate** manifest (§5.5) and resolve `"all"` tokens.
2. **Load lock file** (`.artifacts-os/sync.lock`) if present.
3. **Discover catalogue** items for each subset.
4. **Discover overrides** (§11) and overlay them on the
   catalogue.
5. **Plan per-target**, in the order `targets.keys()` is declared
   in the manifest (preserves YAML insertion order; stable for
   reproducibility).
6. **For each target, plan per-asset-kind** in the order:
   agents → skills → commands → hooks → kinds (kinds last
   because kind installation also seeds the `artifacts/<kind>/`
   storage directories).
7. **Execute** (or print plan, in `--check` / `--dry-run`).
8. **Write lock file** atomically (post-execute, only in real
   mode and only if at least one write succeeded).

Ordering matters for two cases:

- **Symlink targets** — if a harness uses link mode pointing to
  another harness's file (today's `.claude/agents -> .openstation/agents`),
  the linked-from target must render first. The harness
  manifest (§8) declares `depends_on:` for this.
- **Storage directory creation** — kind installation creates
  `artifacts/<x-dir>/.gitkeep`; running kinds last avoids racing
  with `init`'s scaffold.

## 7. Catalogue Layout (Scope Item 3)

### 7.1 Wheel layout

```
src/artifacts_os/templates/
├── __init__.py                # empty (importlib.resources anchor — exists)
├── settings/                  # exists, unchanged
│   ├── basic.yaml
│   ├── standard.yaml
│   └── advanced.yaml
├── kinds/                     # exists, unchanged
│   ├── task/   { kind.json, ARTIFACT.md }
│   ├── note/   { kind.json, ARTIFACT.md }
│   ├── spec/   { kind.json, ARTIFACT.md }
│   ├── research/ { kind.json, ARTIFACT.md }
│   └── agent/  { kind.json, ARTIFACT.md }
├── agents/                    # exists, unchanged (9 specs at top of master tree)
│   ├── architect.md
│   ├── author.md
│   ├── developer.md
│   ├── devrel.md
│   ├── product-manager.md
│   ├── project-manager.md
│   ├── researcher.md
│   ├── security-engineer.md
│   └── technical-writer.md
├── skills/                    # NEW — migrates from src/.../ai/claude/skills/
│   ├── artifacts-os/   SKILL.md
│   ├── openstation-execute/    SKILL.md
│   ├── openstation-supervisor/ SKILL.md
│   └── release-changelog/      SKILL.md
├── commands/                  # NEW — migrates from src/.../ai/claude/commands/
│   ├── artifacts.create.md
│   ├── artifacts.kinds.md
│   ├── artifacts.list.md
│   ├── artifacts.list.open-tasks.md
│   ├── artifacts.show.md
│   ├── openstation.check.md
│   ├── openstation.create.md
│   …
│   └── openstation.verify.md  (26 files total — current count)
├── hooks/                     # NEW (M6 — reserved key in M1)
│   ├── auto-commit.yaml
│   └── …
└── harnesses/                 # NEW — per-target sync manifests (§8)
    ├── claude.yaml
    ├── openstation.yaml
    ├── opencode.yaml
    └── vault.yaml              # pseudo-harness for the artifacts/ vault itself (§8.5)
```

### 7.2 What moves where

| Today | After this spec |
|-------|-----------------|
| `src/artifacts_os/ai/claude/commands/*.md` | `src/artifacts_os/templates/commands/*.md` |
| `src/artifacts_os/ai/claude/skills/<ns>/SKILL.md` | `src/artifacts_os/templates/skills/<ns>/SKILL.md` |
| `artifacts/agents/*.md` (real files) | Becomes sync **output** rendered from `templates/agents/`. Project-specific `qa.md` migrates to override layer §14. |
| `artifacts/kinds/<name>/` (real dirs) | Becomes sync output rendered from `templates/kinds/`. |
| `.claude/agents/`, `.openstation/agents/`, `.opencode/agents/` (mix of real files + symlinks) | All become sync output. Symlink mirroring is replaced by either render-from-catalogue (copy mode) or render-symlink-into-catalogue (link mode), per-harness manifest (§8). |

The `src/artifacts_os/ai/` module is **not deleted** in M1: its
`install.py` is the implementation vehicle for the new sync
engine (generalised), and `body_loader.py` is unrelated. M2/M3
work absorbs the rest of `ai/claude/` into the new catalogue
sub-trees and removes the now-empty package.

### 7.3 `pyproject.toml` package-data

Add `skills/`, `commands/`, `hooks/`, and `harnesses/` to the
existing entry from [[s0021-artifacts-init-flow]] §13.2:

```toml
[tool.setuptools.package-data]
"artifacts_os.templates" = [
    "settings/*.yaml",
    "kinds/*/kind.json",
    "kinds/*/ARTIFACT.md",
    "agents/*.md",
    "skills/*/SKILL.md",
    "commands/*.md",
    "hooks/*.yaml",
    "harnesses/*.yaml",
]
```

### 7.4 Loader API

Extends the four loaders from [[s0021-artifacts-init-flow]] §13.3
with four new ones, all using `importlib.resources.files`:

```python
def _load_skill_template(name: str) -> str: ...
def _load_command_template(name: str) -> str: ...
def _load_hook_recipe(name: str) -> str: ...
def _load_harness_manifest(name: str) -> dict: ...

def _discover_skills() -> list[str]: ...
def _discover_commands() -> list[str]: ...
def _discover_hooks() -> list[str]: ...
def _discover_harnesses() -> list[str]: ...
```

Adding a new shipped item (e.g. a 6th agent) is a pure file-add
under the appropriate sub-tree — no registration list.

### 7.5 SyncReport

Extends the existing `ai.install.InstallReport` to cover the new
asset kinds. Field shape (Python):

```python
@dataclass
class SyncAction:
    target: str            # "claude" | "openstation" | "opencode" | "vault"
    kind: str              # "agent" | "skill" | "command" | "kind" | "hook" | "harness-manifest"
    source: Path           # resolved catalogue or override path
    dest: Path             # resolved on-disk path
    action: ActionKind     # see §7.6
    reason: str            # human-readable
    source_layer: Literal["catalogue", "override"]
    sha256_after: str | None  # post-render hash (None for "skip"/"refuse"/"keep-foreign")

@dataclass
class SyncReport:
    actions: list[SyncAction]
    drift: list[SyncAction]   # populated by --check; subset of actions with action == "drift"

    @property
    def installed(self) -> int: ...
    @property
    def skipped(self) -> int: ...
    @property
    def refused(self) -> int: ...
    @property
    def drifted(self) -> int: ...
```

### 7.6 Action kinds (extends `ai.install.ActionKind`)

| Action | When | Writes? |
|--------|------|---------|
| `install-link` | Mode link, target absent. | yes (symlink) |
| `install-copy` | Mode copy, target absent. | yes (file) |
| `replace-link` | Mode link, target exists as stale symlink. | yes |
| `update-copy` | Mode copy, target exists, content stale, has marker. | yes |
| `skip` | Target up to date (hash matches lock). | no |
| `refuse` | Target exists, no marker, not in lock. | no |
| `keep-foreign` | Target outside namespace (e.g. user's own command). | no |
| `remove` | Lock entry exists but catalogue + override no longer ship the item. | yes (unlink) |
| `drift` | `--check` only: target's on-disk hash differs from lock entry, or lock entry missing for a managed file. | no |

`drift` is a planning-only kind — it never reaches the executor.

## 8. Per-Harness Manifest Format (Scope Item 4)

### 8.1 Schema

Each file under `templates/harnesses/<name>.yaml` declares one
harness target. Example (`claude.yaml`):

```yaml
name: claude
root: .claude
default_enabled: true
marker_style: html             # html | yaml | json | python | none
depends_on: []                 # other harness names that must render first

# Asset → destination mapping.  Each entry is a logical asset kind
# from the catalogue, with a destination pattern (Python str.format)
# and an optional mode override.
maps:
  agents:
    catalogue_dir: agents
    dest_pattern: "agents/{name}.md"
    mode: link                 # link | copy
    items: "${manifest.agents}"
  skills:
    catalogue_dir: skills
    dest_pattern: "skills/{name}/SKILL.md"
    mode: link
    items: "${manifest.skills}"
  commands:
    catalogue_dir: commands
    dest_pattern: "commands/{name}.md"
    mode: link
    items: "${manifest.commands}"

# Runtime data — never touched (§12).
runtime_paths:
  - "settings.local.json"     # user's per-host overrides

# Static files copied verbatim (no per-item enumeration).
static:
  - source: "static/claude/settings.json"
    dest: "settings.json"
    mode: copy
    overridable: true
```

`${manifest.<key>}` is the only interpolation token in harness
manifests; it expands to the resolved subset from §5.4.

### 8.2 OpenStation manifest (`openstation.yaml`)

```yaml
name: openstation
root: .openstation
default_enabled: true
marker_style: html
depends_on: []

maps:
  agents:
    catalogue_dir: agents
    dest_pattern: "agents/{name}.md"
    mode: copy                 # OpenStation reads real files; symlinks OK but copy is safer for distribution
    items: "${manifest.agents}"
  skills:
    catalogue_dir: skills
    dest_pattern: "skills/{name}/SKILL.md"
    mode: copy
    items: "${manifest.skills}"
  commands:
    catalogue_dir: commands
    dest_pattern: "commands/{name}.md"
    mode: copy
    items: "${manifest.commands}"
  docs:                         # docs are static, not per-manifest
    catalogue_dir: docs
    dest_pattern: "docs/{name}.md"
    mode: copy
    items: all
  hooks:
    catalogue_dir: hooks
    dest_pattern: "hooks/{name}.yaml"
    mode: copy
    items: "${manifest.hooks}"

runtime_paths:
  - "state.db"
  - "state.db-shm"
  - "state.db-wal"
  - "events/*.jsonl"
  - "logs/**"
  - "openstation.yaml"          # consumer's own per-OS-host config

static: []
```

**R2** — the `docs:` map and the `static:` entries are
provisional; the researcher must enumerate the full
`.openstation/docs/` set and decide which are versioned with
artifacts-os vs. project-owned (CLAUDE.md `## Documentation
First`).

### 8.3 Claude manifest variant — symlink reuse

This repo today exploits the fact that `.claude/agents/` is
byte-identical to `.openstation/agents/` by symlinking the
whole directory. The harness manifest can preserve this via a
`reuse:` clause that links the entire mapped directory at the
harness root level:

```yaml
# claude.yaml (variant — agents reuse openstation)
maps:
  agents:
    reuse_from: openstation     # symlink .claude/agents -> .openstation/agents
    items: "${manifest.agents}"
```

`reuse_from:` is mutually exclusive with `catalogue_dir:`. Sync
emits one `install-link` action for the directory itself, no
per-item actions. Drift detection on the linked target is
performed on the *source* harness (here, `openstation`), not
twice.

**Decision**: `reuse_from` is **recommended** for `claude` →
`openstation` agents/skills/commands in this repo's render, but
**not required**. The shipped `claude.yaml` default uses
per-item link mode for clarity; the repo's manifest can override
via the override layer if reuse is preferred.

### 8.4 OpenCode manifest

Identical shape to Claude. Held until R6 closes (is OpenCode
actively used here, or residue?). The file ships in M1 with
`default_enabled: false`.

### 8.5 The `vault` pseudo-harness

`templates/harnesses/vault.yaml` describes the artifacts vault
itself as a render target. Maps `agents:` to `artifacts/agents/`,
`kinds:` to `artifacts/kinds/`. This is what eliminates today's
`artifacts/agents/` ≡ `templates/agents/` duplication.

The target is named **`vault`** (not `artifacts`) for two
reasons: it matches the existing `find_vault_root` terminology
in `docs/architecture.md`, and it avoids visual collision with
the `artifacts/` directory name and the `artifacts` CLI verb in
the `harness.targets:` block.

```yaml
name: vault
root: artifacts              # writes into <vault>/artifacts/
default_enabled: true        # the vault is always a render target
marker_style: yaml           # frontmatter comment line
maps:
  agents:
    catalogue_dir: agents
    dest_pattern: "agents/{name}.md"
    mode: copy
    items: "${manifest.agents}"
  kinds:
    catalogue_dir: kinds
    dest_pattern: "kinds/{name}/ARTIFACT.md"
    mode: copy
    items: "${manifest.kinds}"
  kind_schemas:
    catalogue_dir: kinds
    dest_pattern: "kinds/{name}.json"
    source_pattern: "kinds/{name}/kind.json"
    mode: copy
    items: "${manifest.kinds}"

runtime_paths:
  - "logs/**"
  - "events/**"
  - "tasks/**"                  # task content is user-owned, never managed
  - "specs/**"
  - "notes/**"
  - "research/**"
  - "alerts/**"
  - "overrides/**"              # the override layer itself is never re-rendered into the vault
```

The `runtime_paths:` for `vault` is broad because every data
sub-directory (`tasks/`, `specs/`, etc.) is user-authored
content. Sync only touches `agents/` and `kinds/`.

## 9. Managed-File Marker Convention (Scope Item 5)

### 9.1 Marker format

A single-line stamp containing four fields, comment-quoted per
file type:

```
artifacts-os:managed v1 src=<catalogue-relative-path> sha256=<hex>
```

Fields:

| Field | Required | Meaning |
|-------|----------|---------|
| `artifacts-os:managed` | yes | Discriminator; greppable. |
| `v1` | yes | Marker schema version. Bump when the marker format itself changes. |
| `src=<path>` | yes | Catalogue path the file derives from. Relative to `src/artifacts_os/templates/`. Used by sync to find the source on re-render. |
| `sha256=<hex>` | yes | SHA-256 of the file's content immediately after rendering (post-interpolation). 64 hex chars. The on-disk file's hash must match this — if not, the file was edited (drift). |

### 9.2 Comment styles per file type

| File type | Marker line | Position |
|-----------|-------------|----------|
| Markdown (`.md`) | `<!-- artifacts-os:managed v1 src=agents/architect.md sha256=… -->` | Line 1 if no frontmatter; line immediately after closing `---` of frontmatter if present. |
| YAML (`.yaml`, `.yml`) | `# artifacts-os:managed v1 src=harnesses/claude.yaml sha256=…` | Line 1. |
| JSON (`.json`) | (not supported inline; tracked in lock only) | n/a — JSON has no comment syntax. JSON files rely on the lock file (§10) alone for drift detection. |
| Python (rare — agent SDK glue) | `# artifacts-os:managed v1 src=… sha256=…` | Line 1 (or line 2 if `#!shebang`). |
| Shebang shell scripts (hooks) | `# artifacts-os:managed v1 src=… sha256=…` | Immediately after the shebang line. |

### 9.3 Frontmatter-aware insertion

For markdown files with YAML frontmatter (every agent spec and
every command), the marker is inserted on the line **after** the
closing `---`, never inside the frontmatter:

```markdown
---
kind: agent
name: architect
---
<!-- artifacts-os:managed v1 src=agents/architect.md sha256=… -->

# Architect
...
```

Rationale: the marker must not appear in `frontmatter.fields`
when parsed. Inserting after frontmatter preserves the existing
schema and makes the marker visible to humans editing the file.

### 9.4 What can and cannot carry a marker

| Can | Cannot |
|-----|--------|
| `.md` (markdown — agents, skills, commands, ARTIFACT.md) | `.json` (no comment syntax) |
| `.yaml` / `.yml` (settings, harness manifests, hooks) | `.db` / `.db-shm` / `.db-wal` (binary; runtime data anyway) |
| `.py` (rare; agent SDK files) | `.png` / `.svg` / other binaries (no markers ever) |
| `.sh` / `.bash` (after shebang) | `.jsonl` (runtime data anyway) |

For unmarkered file types (JSON, binary), the **lock file** is
the sole source of drift truth. `--check` reads the lock entry
and recomputes the hash directly.

### 9.5 Algorithm — overwrite vs. refuse vs. error

```
For each (source, dest) pair planned by sync:

  if dest does not exist:
    → install (link or copy)

  elif dest is a symlink:
    if symlink target resolves to source:
      → skip ("symlink up to date")
    elif mode == link:
      → replace-link
    elif mode == copy and --force and dest in lock:
      → install-copy (replace the symlink with a file)
    else:
      → refuse ("symlink to <other>; not managed by us")

  elif dest is a regular file:
    marker = read first non-empty non-frontmatter line
    if marker matches "artifacts-os:managed v<N> ...":
      stored_sha = sha256 field from marker
      actual_sha = sha256(dest)
      expected_sha = sha256(render(source))

      if actual_sha == expected_sha:
        → skip ("up to date")
      elif actual_sha == stored_sha:
        → update-copy ("catalogue changed; file unmodified")
      else:
        → refuse ("file edited; move customisations to overrides/")
        (with --force: → update-copy ("forced; user edits lost"))

    elif dest in lock file:
      → refuse ("managed previously; marker missing — likely concatenated. Move to overrides/ or restore marker.")

    else:
      → keep-foreign ("not managed by artifacts-os")
```

Compared with today's `ai/install.py :: _plan_action` (lines
162-247), this adds:

1. **Marker-based update-vs-refuse split** — today's logic
   refuses any content difference unless `--force`; the new
   logic distinguishes "catalogue moved forward, user file
   untouched" (auto-update) from "user edited" (refuse).
2. **Lock-file fallback** — files that lost their marker (e.g.
   stripped by an editor) are still recognised via the lock.
3. **Frontmatter-aware marker read** — `_plan_action` is byte-
   oriented today; the new path parses YAML frontmatter to
   locate the marker.

## 10. Lock File

### 10.1 Location and format

`./.artifacts-os/sync.lock` — YAML, vault-relative.

```yaml
# artifacts-os sync lock — generated by `artifacts sync`. Do not edit.
version: 1
generated_at: 2026-05-14T18:30:42Z
catalogue_version: 0.3.0           # artifacts_os.__version__ at sync time

files:
  - dest: .openstation/agents/architect.md
    target: openstation
    kind: agent
    source: templates/agents/architect.md
    source_layer: catalogue        # catalogue | override
    sha256: 8f2d…
    mode: copy
  - dest: .openstation/agents/qa.md
    target: openstation
    kind: agent
    source: overrides/openstation/agents/qa.md
    source_layer: override
    sha256: 1c4a…
    mode: copy
  - dest: .claude/agents/architect.md
    target: claude
    kind: agent
    source: templates/agents/architect.md
    source_layer: catalogue
    sha256: 8f2d…
    mode: link
    link_to: .openstation/agents/architect.md
  …
```

### 10.2 Atomic update

Lock is written via `os.replace` after every successful sync
run (the existing atomic-write pattern from CLAUDE.md
`## Coding Style`). Partial-failure runs (exit 1) still write
the lock — but only for the actions that succeeded; failed
actions are omitted (re-running picks them up).

### 10.3 Drift detection (`--check`)

For each entry in `files:`:

1. Stat `dest`. If absent → drift ("file removed").
2. Hash `dest`. If mismatch → drift ("file edited or stale").
3. Compare to current catalogue + override render. If the
   *planned* hash differs from the lock hash → drift
   ("catalogue advanced; re-run sync to update").

After iterating the lock, scan every target's mapped subdirs
for files that match the namespace prefix (`artifacts.*`,
`artifacts-*/SKILL.md`, etc.) but are not in the lock → drift
("orphan in managed slot").

### 10.4 Migration of pre-lock state

A vault with no lock file (e.g. this repo immediately after
M1 lands) treats the first `artifacts sync` as a bootstrap:
every existing managed file is matched by marker, and the lock
is constructed from the marker hashes. Files without a marker
and not in any catalogue are reported `keep-foreign` (preserves
the today's behaviour from `ai/install.py`).

## 11. Override Layer Resolution (Scope Item 6)

### 11.1 Directory layout

`<vault-root>/<harness.overrides_dir>/` — default
`artifacts/overrides/`:

```
artifacts/overrides/
├── agents/                              # full-replace overrides for the agents catalogue
│   └── qa.md                            # adds a new agent (not in catalogue)
├── kinds/                               # full-replace overrides for the kinds catalogue
│   └── note/
│       ├── kind.json                    # deep-merged into templates/kinds/note/kind.json
│       └── ARTIFACT.md                  # full-replaces templates/kinds/note/ARTIFACT.md
├── settings/                            # deep-merge tier with consumer additions
│   └── advanced.yaml
├── claude/                              # per-harness override sub-tree (mirrors harness root)
│   ├── settings.json                    # deep-merged with templates/static/claude/settings.json
│   └── commands/
│       └── project-specific.md          # adds a command not in catalogue
├── openstation/
│   └── docs/
│       └── project-handbook.md
└── artifacts/                           # vault-target overrides
    └── agents/
        └── qa.md                        # same file as agents/qa.md (added to both targets)
```

### 11.2 Lookup order

For a planned (target, kind, item) tuple, sync resolves the
source path as follows:

1. **Per-harness override** — `<overrides_dir>/<target>/<dest_pattern with item>` if present.
2. **Cross-harness override** — `<overrides_dir>/<catalogue_dir>/<item-relative-path>` if present.
3. **Catalogue** — `templates/<catalogue_dir>/<item-relative-path>`.

A file present in (1) or (2) shadows the catalogue. If both (1)
and (2) exist, (1) wins (more specific scope).

For kinds and agents that appear *only* in the override layer
(not in the catalogue), the item is treated as user-added and
permitted in `harness.kinds:` / `harness.agents:` lists. The
manifest validator (§5.5) checks override + catalogue union.

### 11.3 Merge semantics by file type (D8)

| File type | Strategy | Conflict behaviour |
|-----------|----------|---------------------|
| `.md` (agents, skills, commands, ARTIFACT.md) | Full-replace: override file replaces catalogue file verbatim. | n/a — replacement is total. |
| `.json` (kind schemas) | Deep-merge: override keys overwrite catalogue keys recursively. Lists are replaced (not concatenated) at any depth. | Override key with `null` value **deletes** the catalogue key (sentinel). |
| `.yaml` / `.yml` (settings, harness manifests, hooks) | Same as JSON. | Same as JSON. |
| `CLAUDE.md` / `AGENTS.md` (hybrid) | Fence-delimited zones (§11.4). | Managed zone replaced; user content between zones untouched. |

### 11.4 Fence-delimited zones

For hybrid files where managed convention and project text live
together, the catalogue ships zones marked with paired
HTML comments:

```markdown
# This Project

User intro paragraph (preserved).

<!-- artifacts-os:zone:start lifecycle -->
The vault lifecycle is: backlog → ready → in-progress → review
→ verified → done.  See `docs/lifecycle.md` for transitions.
<!-- artifacts-os:zone:end lifecycle -->

## Project-specific section

User content here (preserved).

<!-- artifacts-os:zone:start cli-conventions -->
New `artifacts` commands and flag changes must match...
<!-- artifacts-os:zone:end cli-conventions -->
```

Zones are **named** (`lifecycle`, `cli-conventions`) for two
reasons:

1. Sync can detect "zone present" without parsing position.
2. The catalogue can rename a zone in a future version; the
   migration path is "delete the old-named zone block, re-sync;
   the new-named zone appears in the catalogue position".

Algorithm:

```
for each zone in catalogue file:
    if zone name in target file:
        replace content between start/end markers
    else:
        append a new zone block at end of file
```

User content **outside** any zone is preserved byte-for-byte.

**R3** — the exact list of zones in this repo's `CLAUDE.md` is
TBD until the researcher classifies each section. Provisional
candidates: `lifecycle`, `cli-conventions`, `coding-style`,
`release` (Release section is project-specific in the parent
task's mind — keep it outside zones).

### 11.5 Override-layer marker

Files in the override layer **do not** carry a managed marker
in their own content. The override file is the user's source of
truth. The marker is applied only to the *rendered* file in the
harness target.

Rendered file marker reads `src=overrides/<path>` (vs.
`src=templates/<path>` for catalogue-only items) so the lock
file and `--check` can attribute drift correctly.

## 12. Runtime-Data Exclusion (Scope Item 7)

### 12.1 Exclusion mechanism

Each per-harness manifest declares `runtime_paths:` (§8) — a list
of glob patterns relative to the harness root. Sync:

1. **Never reads** these paths (no hash, no source comparison).
2. **Never writes** to these paths.
3. **Never reports** them as foreign (`keep-foreign` would
   suggest the user *could* opt-in; runtime data is opt-out
   by construction).

### 12.2 Canonical exclusions (shipped)

| Harness | `runtime_paths` |
|---------|-----------------|
| openstation | `state.db`, `state.db-shm`, `state.db-wal`, `events/*.jsonl`, `logs/**`, `openstation.yaml` |
| claude | `settings.local.json`, `chat-state/**` (if/when introduced) |
| opencode | (R6 — pending) |
| vault | `logs/**`, `events/**`, `tasks/**`, `specs/**`, `notes/**`, `research/**`, `alerts/**`, `overrides/**` |

### 12.3 Why deny-list, not allow-list (D9)

An allow-list ("sync only these files") breaks every time a new
runtime file appears under a managed root (e.g. when SQLite
added the `-shm` / `-wal` sidecars). A deny-list with explicit
patterns surfaces the omission as a CI failure (`state.db-shm`
appears as drift), forcing an explicit decision.

### 12.4 Override interaction

Override files **cannot** target a runtime path. If
`overrides/openstation/events/2026-05-14.jsonl` exists, the
manifest validator rejects it:

```
error: override target collides with runtime path:
       overrides/openstation/events/2026-05-14.jsonl matches
       openstation runtime_paths pattern 'events/*.jsonl'.
       Remove the override or change the runtime exclusion.
```

## 13. `init` Relationship (Scope Item 9)

### 13.1 Before this spec

`artifacts init` runs three prompts (tier / kinds / agents),
writes settings + kind bundles + agent specs into the vault,
and creates the `openstation -> artifacts` compat symlink
(optional). It does **not** populate `.claude/`, `.openstation/`,
`.opencode/`.

### 13.2 After this spec (D11)

`artifacts init` becomes a **manifest scaffolder + first sync**:

1. Walk the existing three-step prompt
   ([[s0021-artifacts-init-flow]] §10) — unchanged UX.
2. Write `artifacts.yaml` with a populated `harness:` block
   derived from the prompt answers:

   ```yaml
   harness:
     settings_tier: standard
     kinds: [task, note, spec]      # from Step 2
     agents: [architect, developer] # from Step 3 (none → [])
     skills: []                     # not surfaced in prompts in v1
     commands: all                  # default — every command
     hooks: []
     targets:
       claude: true                 # detected by .claude/ presence, or default-on
       openstation: true
       opencode: false
   ```

3. Write the seed `artifacts.yaml` from the chosen tier
   (`templates/settings/<tier>.yaml`).
4. **Call `artifacts sync` internally** — materialises kinds,
   agents, harness directories, and the lock file from the
   manifest.
5. Print the same summary line as today + the sync section's
   summary.

The prompt UX is identical; the difference is what runs
underneath. A consumer using `--template advanced --kinds all
--agents all --targets all -y` gets a complete dogfood-shaped
vault in one command.

### 13.3 New `init` flag — `--targets`

| Flag | Type | Default | Help |
|------|------|---------|------|
| `--targets CSV` | csv | (prompt or detected) | comma-separated harness targets to enable (e.g. `claude,openstation`); `none` to disable all |

When omitted in a TTY, init detects pre-existing target
directories (`.claude/`, etc.) and pre-fills the prompt
selection accordingly.

### 13.4 Backwards compatibility

- A vault initialised by the old `init` (pre-spec) has no
  `harness:` block. Running `artifacts sync` on such a vault
  exits 2 with:

  ```
  error: no harness manifest in artifacts.yaml.
         Run `artifacts init --add-harness-manifest` to inject
         a default harness: block derived from the on-disk state.
  ```

  The `--add-harness-manifest` flag is reserved in M1, implemented
  in M2 once the migration tooling matures.

- The `--openstation-compat` flag (current `init`) is preserved.
  Sync ignores the `openstation -> artifacts` symlink (it's not
  in any harness manifest).

## 14. Migration Plan for This Repo (Scope Item 8)

The dogfood migration is part of M1's verification: after the
sync engine and catalogue layout land, this repo's hand-
maintained `.claude/`, `.openstation/`, `.opencode/`,
`artifacts/agents/`, `artifacts/kinds/` must regenerate from
canonical sources with no content loss.

### 14.1 Pre-migration audit

Run `artifacts sync --check` against the pre-migration tree.
Expected output (sketch):

```
error: not initialised — artifacts.yaml has no harness: block.
       Drift inventory NOT computed.

Run `artifacts init --add-harness-manifest --dry-run` to preview
the default manifest.
```

The audit's purpose is to surface the **drift inventory** the
parent task §3 of the research sub-task enumerates. The audit
runs the rest of `--check`'s machinery against an inferred
manifest (every item in `templates/` set to "on") so we get a
classification of every file as catalogue / override-candidate /
project-specific / runtime / orphan.

### 14.2 Migration steps

Each step is a separate commit so the migration is auditable.

1. **Land the catalogue moves.** Copy
   `src/artifacts_os/ai/claude/commands/` →
   `src/artifacts_os/templates/commands/`. Copy
   `src/artifacts_os/ai/claude/skills/` →
   `src/artifacts_os/templates/skills/`. Update
   `pyproject.toml` package-data (§7.3). Leave the old
   paths as symlinks until step 7. **No on-disk render
   changes yet.**

2. **Write the harness manifests.** Land
   `templates/harnesses/{claude,openstation,opencode,artifacts}.yaml`
   (§8). Static data only.

3. **Land the sync engine.** Implement
   `src/artifacts_os/sync/` (planner, executor, marker
   reader/writer, lock reader/writer). Tests in
   `tests/sync/` per §17.

4. **Add the `harness:` block to `artifacts.yaml`.** Derive from
   the current dogfood state (every agent, every kind, every
   skill, every command currently real-or-symlinked in
   `.openstation/`):

   ```yaml
   harness:
     settings_tier: advanced     # this repo's current tier
     kinds: [task, note, spec, research, agent]
     agents: [architect, author, developer, devrel,
              product-manager, project-manager, researcher,
              security-engineer, technical-writer]
     skills: [artifacts-os, openstation-execute,
              openstation-supervisor, release-changelog]
     commands: all
     hooks: [auto-commit]        # from current openstation.yaml
     targets: { claude: true, openstation: true, opencode: true, vault: true }
   ```

5. **Route project-specific files to overrides.** Researcher's
   per-file classification (R4) drives this step. **Known
   targets** from a hand audit:

   | File | Today | Override path |
   |------|-------|----------------|
   | `artifacts/agents/qa.md` | real, no catalogue equivalent | `artifacts/overrides/agents/qa.md` |
   | `.openstation/openstation.yaml` (consumer fields) | hand-maintained | preserved as **runtime data** under openstation manifest's `runtime_paths`; not migrated. |
   | Any docs unique to this repo under `.openstation/docs/` | tracked by R2 | `artifacts/overrides/openstation/docs/<name>.md` |

   For each routed file: copy to override path, *do not delete
   the original*. The render step (7) overwrites the original
   via the override route.

6. **Delete the symlink web.** Remove `.claude/agents`,
   `.claude/commands`, `.claude/skills` symlinks. Remove
   `.opencode/agents`, `.opencode/commands`, `.opencode/skills`
   symlinks. Remove the per-file symlinks under
   `.openstation/agents/`, `.openstation/commands/`,
   `.openstation/skills/`. The directories themselves remain
   (sync will repopulate them).

   **Do not delete** `.openstation/state.db*`,
   `.openstation/events/*.jsonl`, `.openstation/openstation.yaml`,
   or any file matched by §12.2 runtime paths.

7. **Run `artifacts sync`.** This is the first non-init sync
   the repo has ever run. Expected outcome:

   - 9 agents × 3 targets (`claude`, `openstation`, `opencode`)
     = 27 agent files rendered.
   - 4 skills × 3 targets = 12 SKILL.md files.
   - 26 commands × 3 targets = 78 command files.
   - 5 kinds × 1 target (`vault`) = 5 ARTIFACT.md + 5
     kind.json.
   - 9 agents × 1 target (`vault`) = 9 agent files in
     `artifacts/agents/`.
   - `qa.md` and any other override-routed items rendered from
     `artifacts/overrides/` instead of the catalogue.
   - 1 lock file `.artifacts-os/sync.lock`.

   Commit. Verify `artifacts sync --check` exits 0.

8. **Delete the old AI install path.** Remove
   `src/artifacts_os/ai/claude/{commands,skills}/` (now
   shadowed by `templates/`). Keep `ai/install.py` until M2
   absorbs its remaining behaviour. Remove the
   `artifacts install`-related CLI commands once the
   migration is verified.

### 14.3 Rollback

Each step is a single commit. Rollback is `git revert` of
step N onward, then `git reset --hard HEAD` to clean any
sync output. The deletion in step 8 is the only irreversible
step from a "files removed" standpoint, and is deferred to
after step 7 verifies green for one full week of dogfooding.

### 14.4 Content-loss guarantee

The migration plan guarantees no content loss when every
file under `.claude/`, `.openstation/`, `.opencode/`,
`artifacts/agents/`, `artifacts/kinds/` is either:

- byte-equal to a catalogue file (after marker stamp), **or**
- byte-equal to an override file, **or**
- explicitly in a `runtime_paths:` pattern, **or**
- explicitly listed as deleted in step 6 (and recreated
  identically in step 7).

The researcher artefact's per-file classification (t0146 §2)
populates this proof; step 7's `sync --check` confirms it on
disk. The migration cannot proceed to step 8 until R4 closes.

## 15. Error-Message Catalogue

Every sync error message follows the pattern:

```
error: <one-line summary>.
       <one or two lines explaining what the user should do>.
       [optional: pointer to docs/spec/section]
```

### 15.1 Manifest-validation errors (exit 2)

| ID | Message |
|----|---------|
| E001 | `error: no harness manifest in artifacts.yaml. Add a 'harness:' block (see docs/sync.md) or run 'artifacts init --add-harness-manifest'.` |
| E002 | `error: unknown <kind\|agent\|skill\|command\|hook> '<name>' in harness.<key>. Catalogue contains: <list>. Add the item to artifacts/overrides/<dir>/<name>.<ext> to use a project-specific version.` |
| E003 | `error: unknown harness target '<name>' in harness.targets. Shipped harnesses: <list>.` |
| E004 | `error: harness.overrides_dir '<path>' collides with harness root '<harness>:<root>'. Pick a non-overlapping path.` |
| E005 | `error: override file '<path>' targets runtime path '<pattern>' in harness '<name>'. Remove the override or change the runtime exclusion.` |

### 15.2 Render / write errors (exit 1, accumulated)

| ID | Message |
|----|---------|
| E101 | `error: cannot read catalogue source '<path>': <reason>. The wheel may be corrupted; reinstall artifacts-os.` |
| E102 | `error: cannot write '<dest>': <reason>.` |
| E103 | `error: cannot deep-merge YAML '<override>' into '<catalogue>': conflicting types at key '<dotted-key>' (<type-a> vs <type-b>).` |
| E104 | `error: fence-delimited zone '<name>' opened but not closed in '<file>'. Hand-edit to balance markers or restore from backup.` |

### 15.3 Refusal warnings (exit 0 in plan, exit 1 in execute)

| ID | Message |
|----|---------|
| W201 | `refused: '<dest>' has been edited (sha256 mismatch). Move customisations to '<overrides_dir>/...' or pass --force to overwrite.` |
| W202 | `refused: '<dest>' has no managed marker but is in the lock. Restore the marker, move to overrides/, or run --force.` |
| W203 | `kept-foreign: '<dest>' is not in the artifacts-os namespace. Sync will not touch it.` |

### 15.4 Drift errors (exit 1 from `--check` only)

| ID | Message |
|----|---------|
| D301 | `drift: '<dest>' edited since last sync (sha256 differs from lock).` |
| D302 | `drift: '<dest>' removed since last sync (in lock but not on disk).` |
| D303 | `drift: '<dest>' added without sync (in managed slot but not in lock).` |
| D304 | `drift: '<dest>' catalogue advanced (current render would change). Run 'artifacts sync' to update.` |

## 16. Worked End-to-End Example

### 16.1 Fresh consumer

A new project `~/proj` with nothing in it.

```
$ cd ~/proj
$ artifacts init -y --template standard --kinds task,note,spec \
                 --agents architect,developer --targets claude,openstation,vault
Selected:
  template : standard
  kinds    : task, note, spec, agent  (agent kind auto-included for selected agents)
  agents   : architect, developer
  targets  : claude, openstation, vault

Writing files...
  ✓ artifacts.yaml
  ✓ artifacts/kinds/task.json
  ✓ artifacts/kinds/task/ARTIFACT.md
  ✓ artifacts/tasks/.gitkeep
  …
  ✓ artifacts/agents/architect.md
  ✓ artifacts/agents/developer.md

Running sync...
  ✓ .openstation/agents/architect.md       [link: templates/agents/architect.md]
  ✓ .openstation/agents/developer.md       [link: templates/agents/developer.md]
  ✓ .openstation/commands/artifacts.create.md   [link: templates/commands/artifacts.create.md]
  …
  ✓ .claude/agents/architect.md            [link: templates/agents/architect.md]
  ✓ .claude/agents/developer.md            [link: templates/agents/developer.md]
  …
  ✓ .artifacts-os/sync.lock

Initialised artifacts-os project: /home/user/proj
  3 kinds, 2 agents installed.
  Sync: 28 files installed across 3 targets (claude, openstation, vault).
```

`.artifacts-os/sync.lock` now exists. `.claude/agents/`,
`.openstation/agents/`, `artifacts/agents/` each contain
`architect.md` and `developer.md`. Every file has a managed
marker on line 5 (after frontmatter).

### 16.2 Override takes precedence

User wants a project-specific `developer` agent with one extra
constraint.

```
$ mkdir -p artifacts/overrides/agents
$ cp artifacts/agents/developer.md artifacts/overrides/agents/developer.md
$ # edit overrides/agents/developer.md — add a project-specific bullet
$ vi artifacts/overrides/agents/developer.md
$ artifacts sync
Sync plan — 1 file changed

Target       Action       Path                                 Source
.openstation update-copy  .openstation/agents/developer.md     overrides/agents/developer.md
.claude      update-copy  .claude/agents/developer.md          overrides/agents/developer.md
vault        update-copy  artifacts/agents/developer.md        overrides/agents/developer.md

Summary: 3 updated, 25 skipped (already synced), 0 refused.
```

The override file is now the source for every target's
`developer.md` render. The lock file's `source_layer` field
records `override` for these three entries.

### 16.3 Drift detected by `--check`

User hand-edits `.claude/agents/architect.md` (e.g. to test
something). CI runs `artifacts sync --check`:

```
$ artifacts sync --check
Drift detected — 1 file.

drift: .claude/agents/architect.md edited since last sync (sha256 differs from lock).

Exit 1.
```

Hand-fix: either move the edit into
`artifacts/overrides/claude/agents/architect.md` and re-sync,
or restore the file from the catalogue:

```
$ artifacts sync --target claude --force
✓ .claude/agents/architect.md   [restored from templates/agents/architect.md]
$ artifacts sync --check
Clean. 28 managed files match lock. Exit 0.
```

### 16.4 Runtime data survives

User's OpenStation session writes to
`.openstation/events/2026-05-14.jsonl` and
`.openstation/state.db`. CI later runs `artifacts sync` (not
just `--check`):

```
$ artifacts sync
Sync plan — 0 files changed (everything up to date).
Summary: 0 installed, 28 skipped, 0 refused.

Runtime paths (excluded from sync):
  .openstation/state.db, .openstation/state.db-shm, .openstation/state.db-wal,
  .openstation/events/*.jsonl, .openstation/logs/**,
  .openstation/openstation.yaml.
  These paths are never read or written by sync.
```

The state.db and the JSONL events are untouched. The reported
file count (28) matches the lock; runtime files are excluded
by construction.

### 16.5 Catalogue upgrade

User runs `pip install -U artifacts-os` and the new version
ships a tightened `architect.md` agent spec.

```
$ artifacts sync
Sync plan — 3 files changed (catalogue advanced).

Target       Action       Path                                  Source
.openstation update-copy  .openstation/agents/architect.md      templates/agents/architect.md
.claude      update-copy  .claude/agents/architect.md           templates/agents/architect.md
artifacts    update-copy  artifacts/agents/architect.md         templates/agents/architect.md

Summary: 3 updated (catalogue change), 25 skipped, 0 refused.
```

Because the on-disk `architect.md` files matched the *old*
marker hash (unmodified by the user), the algorithm in §9.5
selects `update-copy` (auto-update) rather than `refuse`. If
the user had edited the file, the same upgrade would emit
`refused` with the W201 message, and the user moves their
edits into the override layer to retain them across upgrades.

## 17. Test Plan

Tests live under `tests/sync/`. Each property has at least one
explicit test.

### 17.1 Manifest validation

- 17.1.1 Missing `harness:` block → exit 2 with E001.
- 17.1.2 Unknown agent name → exit 2 with E002 listing
  catalogue entries.
- 17.1.3 `"all"` expands to every catalogue entry.
- 17.1.4 `"none"` and `[]` are equivalent.
- 17.1.5 Override-only item (e.g. `qa.md`) is accepted.
- 17.1.6 Unknown harness target → exit 2 with E003.

### 17.2 Catalogue discovery

- 17.2.1 `_discover_kinds/agents/skills/commands` return sorted
  lists.
- 17.2.2 Loader works under editable install and built wheel
  (zipimport) — uses `importlib.resources.files`.
- 17.2.3 Harness manifest YAML round-trips through PyYAML
  (string keys, no integer-keyed maps).

### 17.3 Marker semantics

- 17.3.1 Markdown render places marker on line after closing
  `---` of frontmatter.
- 17.3.2 Markdown render with no frontmatter places marker on
  line 1.
- 17.3.3 YAML render places marker on line 1.
- 17.3.4 JSON file has no marker; lock is sole source of truth.
- 17.3.5 Marker `sha256` matches `sha256(content_after_marker)`.
- 17.3.6 Marker is removed and rewritten on `update-copy` (no
  stale marker survives a re-render).

### 17.4 Plan algorithm (§9.5)

- 17.4.1 Absent file → `install-link` or `install-copy`.
- 17.4.2 Marker present, hash matches → `skip`.
- 17.4.3 Marker present, file hash matches marker, catalogue
  advanced → `update-copy`.
- 17.4.4 Marker present, file hash differs from marker →
  `refuse` (with W201).
- 17.4.5 No marker, in lock → `refuse` (W202).
- 17.4.6 No marker, not in lock → `keep-foreign` (W203).
- 17.4.7 Symlink already correct → `skip`.
- 17.4.8 Symlink stale → `replace-link`.

### 17.5 Idempotency

- 17.5.1 Second sync run on unchanged state produces zero
  install/update actions.
- 17.5.2 `sync --check` on the lock-file state exits 0.
- 17.5.3 `sync --force` on the lock-file state still produces
  zero updates (force does not write redundantly).

### 17.6 Override layer

- 17.6.1 Override file shadows catalogue file: rendered hash
  matches override.
- 17.6.2 Override file rendered to every enabled target.
- 17.6.3 Per-harness override (`overrides/claude/agents/x.md`)
  beats cross-harness override (`overrides/agents/x.md`).
- 17.6.4 Override-only item appears in render even though no
  catalogue equivalent exists.
- 17.6.5 YAML override deep-merges into catalogue YAML
  (additive keys preserved, conflicting keys override-wins).
- 17.6.6 List in YAML is replaced (not concatenated).
- 17.6.7 Override-key with `null` value deletes the catalogue
  key.

### 17.7 Fence-delimited zones (§11.4)

- 17.7.1 Zone with start/end markers replaced; user content
  outside zones preserved.
- 17.7.2 Missing zone in target file → zone appended at end of
  file.
- 17.7.3 Unbalanced markers (`start` without `end`) → E104.
- 17.7.4 Multiple zones replaced in one pass.

### 17.8 Runtime exclusion (§12)

- 17.8.1 File matching `runtime_paths:` pattern never appears
  in plan.
- 17.8.2 Runtime file never reported as `keep-foreign`.
- 17.8.3 Override targeting a runtime path → E005.

### 17.9 Lock file

- 17.9.1 Lock is written atomically (`os.replace`).
- 17.9.2 Lock entries include `source_layer: catalogue` vs.
  `override` correctly.
- 17.9.3 Lock survives partial-failure run (only succeeded
  actions recorded).
- 17.9.4 Lock-less first run treats existing markered files
  as bootstrap and reconstructs entries from markers.
- 17.9.5 `--check` against missing lock → drift on every
  managed file (D303).

### 17.10 CLI surface

- 17.10.1 `artifacts sync` default exit code map: 0 / 1 / 2 / 3.
- 17.10.2 `--check` and `--dry-run` are mutually exclusive.
- 17.10.3 `--target NAME` repeatable; unknown name → E003.
- 17.10.4 `--json` switches to JSONL on stdout, no Rich.
- 17.10.5 Plan output uses the same Rich-table style as
  `artifacts list`.

### 17.11 Migration (§14)

- 17.11.1 `--add-harness-manifest --dry-run` produces a manifest
  derived from on-disk state without writing.
- 17.11.2 Pre-migration `sync --check` reports drift on every
  legacy file.
- 17.11.3 Post-migration `sync --check` is green for this
  repo's snapshot.

## 18. Surfaces

### 18.1 New public surfaces

| Surface | Contents |
|---------|----------|
| `artifacts.yaml :: harness:` (manifest schema) | §5 |
| `artifacts sync` CLI | §6 |
| `src/artifacts_os/templates/{skills,commands,hooks,harnesses}/` (catalogue) | §7 |
| `<vault>/artifacts/overrides/` (override layer) | §11 |
| `<vault>/.artifacts-os/sync.lock` (state) | §10 |
| `src/artifacts_os/sync/` (Python module) | §19 |

### 18.2 Surfaces this spec preserves

- `artifacts init` prompts and flags — extended, not replaced
  (§13).
- `Settings` extension pattern from
  [[s0010-core-settings-module-spec]] — `HarnessManifest` is a
  new `from_base` extension owned by `sync/`.
- `ai/install.py :: install`/`uninstall`/`list_installed`
  Python API — kept until M2 absorbs the call sites; then
  deprecated and removed.
- `ai/install.py` action vocabulary (`install-link` etc.) —
  extended (§7.6), not redefined.

### 18.3 Surfaces this spec drops (post-migration)

- `src/artifacts_os/ai/claude/commands/` — moved to
  `templates/commands/` (§7.2).
- `src/artifacts_os/ai/claude/skills/` — moved to
  `templates/skills/` (§7.2).
- Hand-maintained directory symlinks (`.claude/agents -> .openstation/agents`)
  — replaced by sync output (§8.3 reuse mode optional).
- The `artifacts install` CLI (existing today's AI install
  command) — deprecated by `artifacts sync`. Remove after
  one release cycle.

## 19. Module Layout

A new top-level Python module `src/artifacts_os/sync/` houses
the engine. Respects the dependency DAG from CLAUDE.md:
`core` → `sync` → `cli`.

```
src/artifacts_os/sync/
├── __init__.py            # public API: sync(), check(), SyncReport
├── README.md              # user-facing description (M1)
├── manifest.py            # HarnessManifest dataclass + from_base loader
├── catalogue.py           # template discovery + loader (extends importlib.resources usage)
├── overrides.py           # override-layer lookup + deep-merge
├── harness.py             # per-harness manifest loader + resolver
├── marker.py              # marker read/write/sha256
├── lock.py                # lock-file read/write/diff
├── planner.py             # plan algorithm (§9.5, ordering §6.6)
├── executor.py            # write actions (atomic, supports dry-run)
└── zones.py               # fence-delimited zone replace (§11.4)
```

Tests mirror this layout under `tests/sync/`.

### 19.1 Public API (`__init__.py`)

```python
from .manifest import HarnessManifest, load_harness_manifest
from .lock import SyncLock, load_lock, write_lock
from .planner import plan_sync, SyncPlan, SyncAction, ActionKind
from .executor import execute_plan, SyncReport
from .marker import MARKER_VERSION, read_marker, write_marker

def sync(
    vault: Path,
    *,
    check: bool = False,
    dry_run: bool = False,
    targets: list[str] | None = None,
    force: bool = False,
) -> SyncReport: ...

def check(vault: Path, *, targets: list[str] | None = None) -> SyncReport:
    """Equivalent to sync(vault, check=True, ...)."""
```

### 19.2 CLI entry point

`src/artifacts_os/cli/commands/sync.py` is a thin wrapper that
parses flags, calls `sync.sync(...)`, renders the
`SyncReport`, and maps exit codes.

## 20. Implementation Notes (for M1)

1. **Move the catalogue first.** Steps 1–2 of §14.2 are pure
   file moves; they break no contract. Do them in a single PR
   so `templates/` carries every item before the sync engine
   needs them.
2. **Build the planner before the executor.** The planner is
   testable in isolation (in-memory only). The executor is
   the only piece that touches disk.
3. **Reuse `ai/install.py` primitives.** `_sha256`,
   `_is_namespaced`, `_is_skill_namespace`, the `AssetAction`
   dataclass — port them to `sync/` rather than rewriting.
4. **Hash post-render.** D13 requires the marker hash to be
   over the post-interpolation byte stream. Tests in
   §17.3 verify the hash includes the *final* file content,
   not the catalogue source.
5. **Atomic writes everywhere.** CLAUDE.md `## Coding Style`:
   `O_CREAT | O_EXCL` for create, `os.replace` for update.
   The lock file follows the same rule.
6. **Defer hooks and zone-fences.** §11.4 (zones) and the
   `hooks:` subset can ship empty in M1 — they are M5/M6
   features. The keys must be reserved in the manifest schema
   from M1 so consumers don't have to re-migrate.
7. **Drift-CI workflow lands in M1.** A GitHub Actions job
   `sync-check` runs `artifacts sync --check` on every PR.
   Add to `.github/workflows/` alongside the existing test
   workflow.

## 21. Cross-References

- [[t0144-distributable-opinionated-harness-for-artifacts]] —
  parent feature task; carries user intent and milestone shape.
- [[t0145-spec-the-distributable-harness-model]] — producing
  task for this spec.
- [[t0146-research-harness-footprints-and-current]] — blocking
  research; closes the open R-marked items (§22).
- [[s0021-artifacts-init-flow]] — init flow this spec extends
  (manifest scaffolder + first sync).
- [[s0010-core-settings-module-spec]] — `Settings` extension
  pattern reused by `HarnessManifest`.
- [[s0025-artifact-events]] — managed-core + opt-in-reaction
  split precedent at the event layer (this spec mirrors at the
  file-tree layer).
- [[s0017-artifact-kinds-discovery-mechanism]] — kind discovery
  contract sync renders to.
- `src/artifacts_os/ai/install.py` — direct ancestor of the
  sync engine; primitives reused.
- `artifacts.yaml` and `.openstation/openstation.yaml` —
  consumer config sources extended.

## 22. Pending Research (R-items)

Items below cannot be promoted from `recommended` to `decided`
until [[t0146-research-harness-footprints-and-current]] closes.
None of them block the M1 sync foundation from starting (the
spec is implementable today using the recommended defaults),
but the spec status cannot move to `approved` until each is
either resolved or explicitly accepted as recommended.

| R | Question | Recommended default in this spec |
|---|----------|----------------------------------|
| R1 | Are slash-command formats compatible across Claude / OpenStation / OpenCode, or do we need per-harness command sub-dirs? | One canonical `templates/commands/` rendered into every enabled harness; if R1 finds incompatibility, split into `templates/commands/{claude,openstation,opencode}/` and adjust harness manifests. |
| R2 | Which `.openstation/docs/*.md` are project-owned vs. catalogue? | All present `.openstation/docs/` files ship via the OpenStation harness's `docs:` map (catalogue); project-owned exceptions move to override. |
| R3 | What zone names live in this repo's `CLAUDE.md`? | Provisional set: `lifecycle`, `cli-conventions`, `coding-style`, `release` (likely outside zones — see §11.4). |
| R4 | Per-file classification of `.claude/`, `.openstation/`, `.opencode/`, `artifacts/{agents,kinds}/` — which are managed vs. project-specific vs. runtime? | This spec's defaults; the migration step §14.2 (5) cannot proceed without the full table. |
| R5 | Schema-extension precedents (JSON Schema `allOf`, OpenAPI `$ref` overlays). | Use simple deep-merge for v1 (§11.3); revisit if R5 surfaces a clean ref-overlay model worth adopting. |
| R6 | Is `.opencode/` actively used here? Keep or drop from v1? | Ship `templates/harnesses/opencode.yaml` with `default_enabled: false`; consumer opts in. |

## 23. Status Transitions

This spec ships as `draft`. The lifecycle gate is:

- `draft → approved` — once R1–R6 are addressed (resolved or
  consciously accepted as recommended) and the user reviews
  the spec.
- Parent feature task [[t0144-...]] promotes
  `backlog → ready` after this spec is `approved` (per t0145's
  verification list).

The M1 implementation task can begin work in `draft` against
the recommended defaults; M2+ work waits on `approved`.
