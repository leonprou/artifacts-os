---
kind: spec
id: s0029
name: artbook-mvp-distribution-model
status: draft
task: "[[t0151-spec-the-artbook-model]]"
created: 2026-05-15
agent: architect
---

# Artbook MVP Distribution Model

> **Revision note — v2 (Schema Simplification, 2026-05-15).** This
> revision drops the per-book `type:` field and introduces a
> required per-book `dest:` field. Books are now pure
> `(name, src, dest)` records — no dispatch, no `_PLACEMENT`
> registry, no `UnknownBookTypeError`. The D20 walker and D18
> allowlist selection rules apply uniformly to every book. **D3**
> and **D8** are superseded by **D24** and **D25** respectively;
> see those entries for rationale. The rest of the spec
> (shallow-clone fetch, atomic writes, symlink handling, exit
> codes 0/1/2/3/4, local-mode auto-detect from D23) is
> unchanged. Field-level changes: `books[].src` is renamed to
> `books[].src`; `books[].dest` is added (required); `books[].type`
> is removed.

Specifies the **artbook** primitive for artifacts-os: a thin,
implementable model for pulling agent defaults from a remote git
repository on demand.

A **distro** is a git repository with an `artbook.yaml` manifest
at its root. The manifest lists **books** — named, typed bundles
that point at a file or folder inside the distro. The
`artbook` module inside artifacts-os reads the manifest, fetches
content from the distro's `main` branch, and writes files into the
consumer's project. The CLI exposes three verbs against this
model: `artifacts book list`, `artifacts book show <name>`, and
`artifacts book pull <name>`.

The MVP ships one book type — `agents` — and proves the
end-to-end loop. Every other axis (additional book types, update
/ diff / remove verbs, multi-distro, override layer, caching,
auth, lock files, version pinning, offline support, dogfood
migration of this repo's existing copies) is explicitly deferred.

This spec is a fresh, thinner document — not a revision of
[[s0028-distributable-harness-sync-model]]. s0028 designed a much
larger surface (catalogue inside the wheel, multi-target sync,
override layer, lock files, managed-file markers, drift
detection). The MVP scoped here keeps only what proves the user
story in [[t0150-artbook-distribution-model]]: pull one book type
from a remote repo and end up with working agents.

## 1. Background and Scope

### 1.1 Parent feature

[[t0150-artbook-distribution-model]] captures the user story:

> **As a** consumer of artifacts-os **I want** to pull
> artifacts-os's agent defaults from a remote distro repo with
> one command **so that** I don't have to copy-paste agent files
> into my project.

The parent task lists six "directions" (intent, not contract);
this spec turns them into a concrete design.

### 1.2 In scope (this spec)

1. The `artbook.yaml` schema — fields per book, required vs.
   optional, an example file. (§3)
2. The `artbook` Python module layout — package, public API,
   dataclasses. (§4)
3. The CLI surface for `artifacts book list / show / pull` —
   exact behaviour, output format, exit codes, and the
   local-vs-remote source resolution for `list` / `show` (D23).
   (§5)
4. Pull mechanics — fetch strategy, branch, no caching. (§6)
5. Local placement — `agents` book type → consumer path
   mapping; behaviour when files already exist. (§7)
6. A worked end-to-end example — fresh consumer, one pull,
   working agents. (§8)

### 1.3 Out of scope (deferred — each gets its own spec when its time comes)

- Book types other than `agents` (kinds, skills, commands,
  hooks).
- `artifacts book update` / `diff` / `remove` verbs.
- Multiple distros per project.
- Override layer for project-specific items.
- Private-distro authentication, lock files, version pinning,
  caching, offline support.
- Dogfood migration of this repo's existing parallel agent
  copies under `openstation/agents/`, `.openstation/agents/`,
  `.claude/agents/`, `src/artifacts_os/templates/agents/`.
- Third-party book authoring (authoring guide, validation of
  external distros beyond the MVP schema check).
- **Solving file replication on the distro side or the consumer
  side.** The MVP ships one replica from the distro (chosen via
  the book's `path`) to one destination on the consumer (per
  `_PLACEMENT`). Keeping `.claude/agents/` ≡ `.openstation/agents/`
  ≡ `artifacts/agents/` in sync is the consumer's responsibility
  (manual symlink farm, second `book pull` to a different
  destination in a later spec, or a future `book sync` verb).

## 2. Locked Decisions

| ID | Decision | Rationale (brief) |
|----|----------|-------------------|
| D1 | The distro manifest is a YAML file at the distro repo root named `artbook.yaml`. | Consistent with `artifacts.yaml` (the consumer's vault config); reuses PyYAML, already transitively present via `python-frontmatter`; one parser for all artifacts-os config; single canonical filename is greppable. |
| D2 | Per-book required fields: `name`, `type`, `path`. Optional: `description`, `files` (an explicit allowlist — see D18). Top-level `distro:` table has required `name`, optional `description`. Top-level `version:` is required and must equal `1` in this spec. | Minimum to identify a book, dispatch it to a handler, and find its content. The optional `files` field lets distro authors lock the exact contents they ship without renaming the directory. |
| D3 | ~~The MVP recognises one book type: `agents`. Any other `type` value aborts with `unknown book type '<x>'` (exit 1).~~ **Superseded by D24** — the `type:` field is removed entirely. | ~~Lock the dispatch table; new types land via new specs.~~ The dispatch table itself was the unnecessary complexity. |
| D4 | Fetch strategy: shallow git clone (`git clone --depth 1 --branch main <url> <tmpdir>`) into a process-scoped temp directory; tear down on command exit. | Works with any git host (GitHub, GitLab, self-hosted); no per-host HTTP-archive negotiation; no extra runtime dependency beyond `git` on PATH; trivial to reason about. |
| D5 | Always fetch from `main`. No branch / ref / tag override in v1. | One ref means no version-resolution logic; pinning is a deferred spec. |
| D6 | No caching. Every `list`, `show`, and `pull` invocation performs a fresh shallow clone. | Eliminates cache-invalidation logic; cost is bandwidth, not correctness; MVP. |
| D7 | The distro URL lives at `artbook.distro_url` (new top-level key in `artifacts.yaml`). No CLI flag override in v1. | Single configured source per project matches the "one distro" scope; matches the established `views:` / `cli:` / `hooks:` key pattern. |
| D8 | ~~The `agents` book type writes to **one** destination: `<vault_root>/.claude/agents/<file>.md`.~~ **Superseded by D25** — each book declares its own destination via the `dest:` field. | ~~Claude Code is the universal target for agent files in the artifacts-os ecosystem; `.claude/agents/` is what every Claude Code project reads from.~~ The replication policy (one destination per book, consumer-side cross-replica is out of scope) carries over to D25 verbatim. |
| D9 | When a destination file already exists, overwrite it without prompt or backup. **If the destination is a symlink, it is unlinked first and replaced with a regular file** (D19). Files in the destination that are not in the book are left untouched. | Lean MVP — no merge logic, no diff prompts. Unlinking preserves the consumer's invariant that `book pull`'s output is plain files, not links to surprising targets. Operator chose this in t0150 directions §6 and Q1/Q2 follow-ups. |
| D10 | CLI surface is `artifacts book <verb>` — a two-word command with `book` as a resource-namespace prefix and `list / show / pull` as verbs. | Conscious exception to CLAUDE.md's "flat verbs" guideline: `book` is a resource noun, not a streaming/paging mode variant. Mirrors the established `artifacts.list.open-tasks` dotted-namespace precedent in the command set. |
| D11 | The `artbook` Python module lives at `src/artifacts_os/artbook/`, peer to `core`, `cli`, `views`. Dependencies: `core` only. **No rendering inside `artbook`** — it returns dataclasses; rendering is the CLI command's job (D21). | Pure-logic module is easy to reason about and test. Keeps the layering: `core` → `views` → `cli, tui`; `artbook` slots in as a leaf with `core` only, while the CLI command at `cli/commands/book.py` is the integration point that imports both `artbook` and `views`. |
| D12 | YAML parsing uses PyYAML's `safe_load`. PyYAML is already a transitive dependency of `python-frontmatter`. | No new direct dependency; matches what `core/settings.py` and `views/` already use to parse `artifacts.yaml`. |
| D13 | Git invocation uses `subprocess.run(["git", ...], check=True, capture_output=True)` — no `GitPython` or similar library. | Avoids a new dependency; the surface is one command (`clone`). |
| D14 | Manifest validation runs **before** any clone or write. Unknown / malformed manifest → exit 1 with an actionable error. | Fail fast; do not perform side effects against an invalid distro. |
| D15 | Exit codes: 0 ok, 1 runtime error (fetch / parse / write failed, unknown book, unknown type, manifest version mismatch), 2 usage error, 3 vault not initialised, 4 distro URL not configured. | Mirrors the established `artifacts` CLI exit-code convention (0/1/2/3) with one MVP-specific addition (4) for the new failure mode. |
| D16 | A book's `src` (was `path` in v1) may point at any sub-tree of the distro repo. The repo is **not** required to organise content under a dedicated directory; `artbook.yaml` is a view over the existing repo, not a layout decree. | Lets an existing project repo become its own distro by adding one manifest file — no content duplication, no reorganisation. The same files can serve the project's own use and consumers of the artbook simultaneously. |
| D17 | The manifest carries a required top-level `version: 1` field. v1 clients reject `version != 1` with a clear "this client speaks artbook v1; manifest declares v<N>" error. | Cheap to add now, painful to retrofit later. Future schema migrations land without breaking older artbook clients. The check is one line; the field is one byte of overhead. |
| D18 | Each book entry accepts an optional `files: [<filename>, ...]` allowlist. When present, the agents handler ships **only** the files listed (each must exist under `book.src/`; missing files exit 1). When absent, the handler walks `book.src/` and ships all `*.md` files except `README.md` and dotfiles (D20). | Two ergonomic modes: (a) directory-is-the-book (omit `files`, rely on convention); (b) explicit lock-list (use `files`). Distro authors who add an unrelated file to the directory aren't surprised when it lands in consumers; consumers aren't surprised by drift when the distro author adds files. |
| D19 | The destination overwrite uses an unlink-then-write strategy: if a destination path is a symlink (or any non-regular file), it is removed and a regular file is written in its place. Atomic semantics via write-to-`*.tmp` + `os.replace`. | Following the symlink and writing through it would silently mutate the consumer's symlink target, which is surprising. Unlinking guarantees `book pull`'s output is a plain file the consumer can reason about. |
| D20 | The `agents` directory walker filters: include `*.md`; exclude `README.md` (case-insensitive) and any file starting with `.`. Sub-directories are ignored (non-recursive). | The agents convention across this ecosystem is a flat directory of `<slug>.md` files. `README.md` is a frequent distro-repo file that should never be shipped as an agent; dotfiles (`.gitkeep`, etc.) likewise. The filter is convention-driven; distro authors who need exact control use `files:` (D18). |
| D21 | The CLI command at `cli/commands/book.py` reuses `views.render_table` for default output (one column-spec list per verb) and `dataclasses.asdict` for `--json`. No bespoke rendering inside `artbook` or the command. | Same column / styling language as `artifacts list` and `artifacts events`. Saves ~120 lines of styling code and stays in lockstep with future view-layer improvements. `--json` keeps a clean separation: dataclasses are the source of truth, no Rich on the JSON path. |
| D22 | Introduce a base class `core.models.ItemMeta` — the minimal contract for "a record that can be rendered as a table row" — with a single overridable method `cell(key, default="")`. `ArtifactMeta` becomes `ArtifactMeta(ItemMeta)` and overrides `cell` to read from `frontmatter`. `views.render_table` is generalised from `Sequence[ArtifactMeta]` to `Sequence[ItemMeta]` and from `kind_def: KindDef \| None` to an explicit `status_colors: Mapping[str, str] \| None`. The existing artifact-flavoured call site at `cli/commands/list.py` is one line longer: it passes `status_colors=kind_def.meta.get("status_colors", {})`. | A named base class is cleaner than `Mapping[str, Any]`: explicit contract, dataclass-friendly, IDE-discoverable, can grow methods later (e.g. `format_hint`, `sort_key`) without breaking call sites. Matches the codebase's dataclass-based model style (CLAUDE.md `## Coding Style`). New renderable types (e.g. `BookRow`, `WriteActionRow` in the artbook CLI command) inherit from `ItemMeta` and rely on the default `cell` (attribute lookup) — no `frontmatter` plumbing required for non-artifact data. |
| D23 | `artifacts book list` and `artifacts book show` **auto-detect a local manifest**: when `<vault_root>/artbook.yaml` exists they parse it in place (no clone, no `artbook.distro_url` required). When it does not exist they fall through to a shallow clone of `artbook.distro_url` (the existing path). A new `--remote` flag forces the clone path even when a local manifest is present. `artifacts book pull` is **not** subject to auto-detect; it always clones the remote. | The Layout B dogfood pattern (§3.1) means a project repo *is* its own distro. Without auto-detect, distro authors cannot preview their own manifest from inside the repo without either configuring a synthetic `distro_url` or first pushing to git — both surprising. `--remote` is the explicit escape hatch for "show me what is *published*, not what's *on disk*". `pull` stays remote-only because a local-to-local pull would write a destination that may already be the source (the dogfood repo's `.claude/agents/` is symlinked to `<canonical>/agents/`); rewriting it is the dogfood migration scenario explicitly deferred in §1.3 / §7.2.1. The data layer needs no changes — `manifest.load_manifest(path)` already accepts any directory containing an `artbook.yaml`. |
| D24 | **The per-book `type:` field is removed.** Books are pure `(name, src, dest)` records. There is no per-type dispatch, no `_PLACEMENT` registry, and `UnknownBookTypeError` is deleted. The D20 walker (`*.md`, exclude `README.md` case-insensitive, exclude dotfiles, non-recursive) and the D18 allowlist apply uniformly to every book regardless of its semantic content. Supersedes D3. | Inventing a parallel `type` taxonomy (`agents`, `kinds`, `skills`, `commands`, `hooks`) duplicated the artifact `kind` system (`agent`, `task`, `research`, …) without reusing it. Two type systems is the bug. Dropping `type` reduces the schema to its actual content (source path, destination path, optional filename list), and any future kind-aware behavior (frontmatter validation, schema check on pull) can land as an additive optional `kind: <id>` annotation without breaking the v1 schema. Code shrinks: `_PLACEMENT`, `UnknownBookTypeError`, type-dispatch branches all go. |
| D25 | **Each book declares its consumer destination via a required `dest:` field** (vault-relative path). Placement is no longer code-side policy; it is per-book manifest data. **Safety guard**: `dest` must resolve under `vault_root` — manifest parsing rejects `..` segments, absolute paths, and anything whose resolved form falls outside the vault, with `ManifestError` (exit 1). The MVP keeps the one-destination-per-book rule from D8 (cross-replica replication is still out of scope, §7.2.1). Supersedes D8. | Hard-coding destinations in `_PLACEMENT` meant adding a new use case (`skills` → `.claude/skills/`, `commands` → `.claude/commands/`, etc.) required a Python change. Moving destinations to YAML aligns the manifest with the principle that the artbook is *data*. The vault-escape guard preserves the consumer-trust boundary that `_PLACEMENT`'s implicit whitelist provided: a malicious or careless distro cannot direct writes outside the consumer's project. Within the vault, the consumer is trusting the distro author (same trust they extend by setting `distro_url`). |
| D26 | **Books gain an optional `recurse: bool = False` field** for folder-of-folders sources. When `false` (default), the existing flat walker (D20) applies — `*.md` only, non-recursive, dotfile-excluded, `README.md`-excluded. When `true`, the walker treats each direct subdirectory of `src/` as a **unit** and ships its entire subtree to `dest/<unit>/...` preserving directory structure. In recurse mode the file-extension filter is dropped (all file types ship); exclusions are dotfiles + dotted directories + `__pycache__/` + `*.pyc`; loose files directly under `src/` (siblings of subdirectories) are silently ignored. `recurse: true` is **mutually exclusive with `files:`** (manifest validation rejects both being set on one book). The atomic-write semantics from D19 still apply per file. Additive schema change — manifest `version` stays `1`. | The skills source layout is `<skill_name>/SKILL.md` (plus optional `references/`, `scripts/`, etc.) — a folder-of-folders shape. The flat D20 walker ships nothing from `src/.../skills/` because it `iterdir()`s files only. Today this is worked around by listing each skill as its own book entry (Option 2a in n0014), which churns the manifest on every skill addition and loses the "one book, N units" framing. Recurse mode adds the smallest possible knob to handle the nested case: a single boolean. The expanded exclusion list (`__pycache__/`, `*.pyc`) reflects that recurse-mode sources are typically inside a Python package tree (`src/artifacts_os/ai/claude/skills/`); compiled artifacts must never ship. Dropping the `*.md`-only filter is necessary because skill folders carry `.py`, `.json`, and resource files that consumers need verbatim. The `files:` incompatibility is a simplification — combining a flat allowlist with recursion would require slash-bearing entries, breaking D20's "filenames are flat" invariant; if a recursive distro needs precise file control later, that lands in its own decision (`tree_files:` or similar). |
| D27 | **`artifacts book pull <name>` accepts optional positional `ITEM …` arguments to restrict the pull to a named subset of items.** For flat / allowlist books an item matches by filename stem (`architect`) or full filename (`architect.md`). For recurse books an item matches by unit folder name (`artifacts-os`); all files within the matching unit are included. When items are supplied and any item name is not found in the book, the command exits 1 **before writing any files** and prints the list of available items (directing the user to `book show <name>`). `--dry-run` and `--json` both respect the filter. When no items are supplied behaviour is unchanged — all files are pulled. The filtering is implemented in `artbook.placement.filter_entries_by_items`; the CLI resolves all entries first, validates item names, then passes the pre-filtered entry list to `copy_book` via the `preselected=` parameter. | Consumers often pull a book that ships many items but only need one or two. Without item-level selection the only workaround is a `files:` allowlist baked into the distro manifest — but that is a distro-side policy, not a consumer choice. Item-level selection pushes the selection decision to the consumer without changing the manifest or spawning extra book entries. The validate-before-write contract (any unknown item → abort, no partial writes) avoids ambiguous half-written states. Matching by stem *and* full filename eliminates a common friction point where the user must remember whether to include `.md`. Recurse-mode matching by unit name is consistent with how `book show` groups and presents recurse contents. |

## 3. Manifest Schema (Scope Item 1)

### 3.1 File location and format

The manifest is a YAML file at the **root** of the distro repo,
filename `artbook.yaml` (D1). UTF-8 encoded. Parsed with
`yaml.safe_load` (D12).

**Book content lives wherever it already lives in the repo** (D16).
The `artbook.yaml` manifest is a *view over* the repo, not a tree
structure the repo must adopt. Each book's `path` field is a
distro-relative pointer at where its content sits today — there
is no required `artbook/`, `books/`, or `dist/` directory.

**Layout A — a dedicated distro repo** (the simplest case; manifest
and content side by side):

```
artbook-defaults/
├── artbook.yaml          # the manifest
└── agents/               # one book's content
    ├── architect.md
    ├── developer.md
    └── …
```

**Layout B — a project repo doubling as its own distro** (the
dogfood pattern; content stays where the project already uses it):

```
artifacts-os/                       # this repo, hypothetically
├── artbook.yaml                    # adds 10 lines, ships the project's defaults
├── pyproject.toml
├── src/artifacts_os/...
├── tests/...
└── openstation/
    └── agents/                     # the book's content — already used by the project
        ├── architect.md
        ├── developer.md
        └── …
```

Layout B's `artbook.yaml` simply sets
`path: openstation/agents/` on the agents book. The repo continues
to use those files itself; consumers of the artbook see the same
files materialised at their own `.claude/agents/`. No duplication.

Either layout is supported with no code difference — the
`agents` handler (§7.3) walks `<clone_root>/<book.src>` regardless
of how deep that path is.

### 3.2 Schema (v2 — post-D24/D25)

Minimal — the directory-is-the-book mode (`files:` omitted):

```yaml
# artbook.yaml — distro manifest

version: 1                          # required — locks D17

distro:
  name: artifacts-os-defaults                       # required
  description: Default agents for artifacts-os consumers.  # optional

books:
  - name: agents                    # required — stable identity
    src: agents/                    # required — distro-relative source path
    dest: .claude/agents/           # required — vault-relative destination (D25)
    description: Default agent specs.  # optional
```

Explicit — the allowlist mode (`files:` present):

```yaml
version: 1

distro:
  name: artifacts-os-defaults

books:
  - name: agents
    src: openstation/agents/         # dogfood pattern from §3.1 Layout B
    dest: .claude/agents/
    description: Default agent specs.
    files:                           # optional allowlist (D18)
      - architect.md
      - author.md
      - developer.md
      - devrel.md
      - product-manager.md
      - project-manager.md
      - researcher.md
      - security-engineer.md
      - technical-writer.md
```

Folder-of-folders — the recurse mode (`recurse: true`, D26):

```yaml
version: 1

distro:
  name: artifacts-os

books:
  - name: skills
    src: src/artifacts_os/ai/claude/skills/   # parent of <skill_name>/SKILL.md units
    dest: .claude/skills/
    description: Skills that teach Claude how to use artifacts-os.
    recurse: true                             # each subdir is one unit; full subtree ships
```

For the source layout below:

```
src/artifacts_os/ai/claude/skills/
├── __init__.py                       # ignored (loose file at src/ root)
├── artifacts-os/
│   ├── SKILL.md
│   ├── __init__.py                   # ships (under a unit; recurse mode keeps all files)
│   └── __pycache__/                  # ignored (exclusion list)
└── release-changelog/
    ├── SKILL.md
    └── __init__.py
```

The pull writes:

```
<vault>/.claude/skills/
├── artifacts-os/
│   ├── SKILL.md
│   └── __init__.py
└── release-changelog/
    ├── SKILL.md
    └── __init__.py
```

### 3.3 Field semantics

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `version` | yes | int | Manifest schema version. Must be `1` in this spec. Any other value → exit 1 with `error: this artifacts-os version speaks artbook manifest v1; distro declares v<N>`. |
| `distro.name` | yes | str | Identity for human-readable output. No validation beyond non-empty. |
| `distro.description` | no | str | Free-form. Printed by `book list` if present. |
| `books` | yes | list | At least one book. Empty list → exit 1 `manifest has no books`. |
| `books[].name` | yes | str | Stable identity. Used as `<name>` argument for `book show / pull`. Must be unique within the manifest (duplicate → exit 1). |
| `books[].src` | yes | str | **Distro-relative source path** (was `path` in v1). Trailing `/` indicates a directory; no trailing `/` indicates a single file. May be any depth (`agents/`, `openstation/agents/`, `src/foo/bar/agents/`). Must resolve inside the clone (no `..` segments, no absolute paths — exit 1 on either). |
| `books[].dest` | yes | str | **Vault-relative destination path** (D25). Created on pull (`os.makedirs(exist_ok=True)`). Must resolve under `vault_root` (no `..`, no absolute, no escape via symlinks — exit 1 on any of these). Trailing `/` is conventional but not required. |
| `books[].description` | no | str | Free-form. Printed by `book show`. |
| `books[].files` | no | list[str] | Explicit allowlist of file names under `book.src/` (D18). When present, the pull ships **only** these files. Each must exist under the source; a missing file is exit 1. When **absent**, the pull walks `book.src/` and applies the D20 filter (`*.md` minus `README.md` case-insensitive minus dotfiles, non-recursive). Filenames are relative to `book.src`; no slashes (sub-directories rejected — D20 / Q4). Mutually exclusive with `recurse: true` (D26) — combined → exit 1. |
| `books[].recurse` | no | bool | **Folder-of-folders walker** (D26). Default `false` → flat D20 walker. When `true`: each direct subdirectory of `src/` is a unit; the unit's full subtree (all file types, any depth) ships to `dest/<unit>/...` preserving structure. Exclusions: dotfiles, dotted directories, `__pycache__/`, `*.pyc`. Files directly under `src/` (siblings of subdirectories) are silently ignored. Combining with `files:` is rejected (exit 1). |

The `type:` field that v1 required is no longer accepted; a
manifest carrying `type:` is rejected by the v2 parser
(`ManifestError: unknown field 'type' (removed in v2 — see D24)`).
This keeps consumers on v1 clients from silently dropping a field
the distro author thought was meaningful.

### 3.4 A multi-book distro is now schema-trivial (informational)

Because `dest` is per-book and `type` is gone, a multi-book
distro is mechanical. The hypothetical example v1 deferred to a
future spec is just a few more entries in v2:

```yaml
version: 1

distro:
  name: artifacts-os-defaults

books:
  - name: agents
    src: artifacts/agents/
    dest: .claude/agents/

  - name: skills
    src: src/artifacts_os/ai/claude/skills/
    dest: .claude/skills/

  - name: commands
    src: src/artifacts_os/ai/claude/commands/
    dest: .claude/commands/
```

No code change is required to support any of these — there is no
type registry to extend. The MVP ships only the `agents` book in
this repo's own `artbook.yaml`, but the schema imposes no such
limit; third-party distros may ship arbitrary books today.

If a future revision wants kind-aware behavior (e.g. validate
frontmatter against `artifacts/kinds/agent/kind.json` on pull), it
adds an optional `kind: agent` field at the book level — additive,
non-breaking, opt-in. The MVP does no such validation.

## 4. `artbook` Module Layout (Scope Item 2)

### 4.1 Package tree

```
src/artifacts_os/artbook/
├── __init__.py        # re-exports the public API (§4.4)
├── manifest.py        # YAML parsing → Manifest / Book dataclasses
├── fetch.py           # shallow-clone helper, tmpdir lifecycle
├── placement.py       # book-type → consumer path mapping
├── pull.py            # orchestration: fetch → place → write
├── settings.py        # ArtbookSettings (extends core, §4.5)
├── errors.py          # exception hierarchy
└── README.md          # module overview (writer's task, not architect's)
```

### 4.2 Dependencies

**The `artbook` module itself** (pure logic, no rendering):

- **Stdlib**: `subprocess`, `tempfile`, `shutil`, `pathlib`,
  `dataclasses`, `os`.
- **Third-party**: `yaml` (PyYAML) — already a transitive
  dependency via `python-frontmatter`; use `yaml.safe_load`.
- **Internal**: `artifacts_os.core` only — uses
  `find_vault_root`, `load_settings`, and the `Settings`
  extension pattern.
- **Must not import** from `views`, `cli`, `log`, `tui`, `ai`,
  `hooks`, `events`.

**The CLI command at `cli/commands/book.py`** is the integration
point and is permitted to import both `artbook` and `views`. It
calls:

- `artbook.read_manifest()`, `find_book()`, `pull_book()`,
  `destination_for()` for the data side.
- `views.render_table(rows, columns)` for default tabular
  output (D21).
- `dataclasses.asdict()` plus `json.dumps` / per-line JSONL for
  `--json` output.

PyYAML is already imported by `core/settings.py` and `views/`.
The new module reuses the same parser; no new entry in
`pyproject.toml :: dependencies` is required. (A defensive
`pip install pyyaml` is unnecessary because `python-frontmatter`
pins it.)

### 4.3 Dataclasses

```python
@dataclass(frozen=True)
class Book:
    name: str
    src: str                                 # distro-relative source path (was `path` in v1)
    dest: str                                # vault-relative destination path (D25)
    description: str | None = None
    files: tuple[str, ...] | None = None     # explicit allowlist (D18); None → directory walk + D20 filter
    recurse: bool = False                    # D26 — folder-of-folders walker; mutually exclusive with `files`

@dataclass(frozen=True)
class Manifest:
    version: int                             # always 1 in this spec (D17)
    name: str                                # distro.name
    description: str | None
    books: tuple[Book, ...]

@dataclass(frozen=True)
class WrittenFile:
    source: Path                             # absolute path inside the clone
    destination: Path                        # absolute path in the consumer's project
    overwritten: bool                        # True if the destination existed before write
    was_symlink: bool                        # True if the destination was a symlink before unlinking (D19)

@dataclass(frozen=True)
class PullReport:
    book: Book
    written: tuple[WrittenFile, ...]
    distro_url: str
    distro_sha: str                          # the cloned commit's short SHA, for the report
```

### 4.4 Public API

Exported from `artifacts_os.artbook.__init__`:

| Symbol | Signature | Purpose |
|--------|-----------|---------|
| `Book` | dataclass | Per-book record from the manifest. |
| `Manifest` | dataclass | Parsed manifest. |
| `WrittenFile` | dataclass | One write record. |
| `PullReport` | dataclass | Outcome of `pull_book`. |
| `read_manifest` | `(distro_url: str) -> tuple[Manifest, Path]` | Shallow-clones the distro into a tmpdir, parses `artbook.yaml`, validates `version == 1`, returns the manifest plus the clone root. Caller owns tmpdir teardown. |
| `find_book` | `(manifest: Manifest, name: str) -> Book` | Lookup by name. Raises `UnknownBookError` if missing. |
| `pull_book` | `(book: Book, clone_root: Path, vault_root: Path) -> PullReport` | Copies the book's content from the clone into the consumer's vault per §7. Honours `book.files` allowlist (D18) when set, else applies the D20 walker. Overwrites existing files (D9); unlinks symlinks first (D19). |
| `destination_for` | `(book: Book, vault_root: Path) -> Path` | Returns `vault_root / book.dest`. The dest field was already validated at parse time to resolve under `vault_root` (D25); this function is now a trivial join. (In v2 the function is retained only as a convenience seam — callers may also inline `vault_root / book.dest`.) |
| `ArtbookError` | exception | Base class. |
| `ManifestError` | exception | Parse / validation failure (includes `version != 1`, missing required field, duplicate book name, `files` entry not found, sub-path in `files`, `dest` escapes vault, unrecognised field `type` from v1). |
| `FetchError` | exception | git clone failure. |
| `UnknownBookError` | exception | `book.name` not in manifest. |
| `DistroNotConfiguredError` | exception | `artifacts.yaml :: artbook.distro_url` missing or empty. |

`UnknownBookTypeError` (v1) is **removed** in v2 — there is no
type dispatch to fail.

The two-step `read_manifest → pull_book` split (rather than a
single `pull_book_by_name(url, name, vault)` god-function) lets
the CLI's `list` and `show` commands share the clone step
without re-fetching for `pull`. Even with D6 ("no caching")
across invocations, a single CLI invocation that lists then
shows then pulls would still clone three times — but each
invocation is a separate process. Within one invocation, the
two-step split prevents redundant clones in tests and future
batch operations.

### 4.5 Settings extension

```python
# src/artifacts_os/artbook/settings.py
from dataclasses import dataclass
from artifacts_os.core import Settings

@dataclass(frozen=True)
class ArtbookSettings:
    distro_url: str | None

    @classmethod
    def from_base(cls, base: Settings) -> "ArtbookSettings":
        raw = base.raw.get("artbook", {}) or {}
        return cls(distro_url=raw.get("distro_url") or None)
```

Pattern matches [[s0010-core-settings-module-spec]] (`from_base`
classmethod, no coupling to `core`'s release cycle). CLI calls
`ArtbookSettings.from_base(load_settings(root))` and raises
`DistroNotConfiguredError` if `distro_url` is `None`.

### 4.6 Errors

```
ArtbookError                          (base)
├── ManifestError                     (YAML parse, missing key, version != 1, validation, dest escapes vault, removed v1 fields)
├── FetchError                        (git clone failed)
├── UnknownBookError                  (name not in manifest)
└── DistroNotConfiguredError          (artbook.distro_url missing)
```

`UnknownBookTypeError` was removed in v2 along with the
`type:` field (D24).

All inherit from `ArtbookError`. The CLI maps each to an exit
code per §5.5.

## 5. CLI Surface (Scope Item 3)

### 5.1 Synopsis

```
artifacts book list                [--json] [--remote]
artifacts book show <name>         [--json] [--remote]
artifacts book pull <name>         [--json] [--dry-run]
```

The `book` keyword introduces a resource namespace; the three
verbs operate on that namespace. This is a conscious exception
to CLAUDE.md's "flat verbs" rule, justified in D10.

`--remote` (D23) is available on `list` and `show` only; `pull`
is always remote (§5.4.1).

### 5.1.1 Rendering — reuse `views.render_table` (D21 / D22)

The default (non-`--json`) output of every `book` verb is a Rich
table in the same column / styling language as `artifacts list`
and `artifacts events`. The rendering machinery is **not**
reimplemented inside `artbook`; the CLI command at
`cli/commands/book.py` calls `views.render_table(...)` directly,
the same way `cli/commands/list.py` does for artifacts.

`--json` output bypasses `render_table` entirely: it calls
`dataclasses.asdict(...)` on the relevant dataclass(es) and
emits JSON / JSONL directly. No views machinery needed.

### 5.1.2 `ItemMeta` base class (D22 — precursor refactor)

Today `views.render_table` is hardcoded to `list[ArtifactMeta]`
and reaches into `item.frontmatter[col.key]`. To let `book` (and
any future verb) render non-artifact records with the same
machinery, we introduce a base class:

```python
# core/models.py

@dataclass(frozen=True)
class ItemMeta:
    """Base class for any record that can be rendered as a table row.

    The renderer reads cell values via `cell(key)`. The default
    implementation reads from dataclass attributes (suits most rows).
    Subclasses override `cell` only when the cell-value source is not
    the subclass's own fields (e.g. `ArtifactMeta` reads from
    ``self.frontmatter``).
    """

    def cell(self, key: str, default: Any = "") -> Any:
        return getattr(self, key, default)


@dataclass(frozen=True)
class ArtifactMeta(ItemMeta):
    id: str
    name: str
    kind: str
    path: Path
    frontmatter: dict[str, Any]
    # ...existing fields...

    def cell(self, key: str, default: Any = "") -> Any:
        return self.frontmatter.get(key, default)
```

And the renderer's new signature:

```python
# views/_views.py
def render_table(
    items: Sequence[ItemMeta],
    columns: list[FieldSpec],
    *,
    status_colors: Mapping[str, str] | None = None,
) -> Table:
    table = Table()
    for col in columns:
        table.add_column(col.label)

    colors = status_colors or {}
    for item in items:
        row: list[Any] = []
        for col in columns:
            raw = item.cell(col.key, "")
            cell_str = format_field(raw, col.fmt)
            if col.key == "status" and cell_str in colors:
                row.append(Text(cell_str, style=colors[cell_str]))
            else:
                row.append(cell_str)
        table.add_row(*row)
    return table
```

The existing artifact-flavoured call site at
`cli/commands/list.py` changes by one line — it pulls
`status_colors` out of `kind_def` and passes it explicitly:

```python
# cli/commands/list.py — before
table = views.render_table(items, columns, kind_def=kind_def)

# cli/commands/list.py — after
status_colors = kind_def.meta.get("status_colors", {}) if kind_def else {}
table = views.render_table(items, columns, status_colors=status_colors)
```

All other current callers are unaffected; behavior is preserved.

### 5.1.3 New `ItemMeta` subclasses for the `book` commands

The CLI command introduces three small projection types — one per
verb — under `cli/commands/book.py` (or a sibling
`book_rows.py`). They inherit from `ItemMeta` and rely on the
default `cell` implementation (attribute lookup), so no
`frontmatter` plumbing is needed for book data:

```python
# cli/commands/book.py (or book_rows.py)

@dataclass(frozen=True)
class BookRow(ItemMeta):
    name: str
    src: str        # FieldSpec key matches attribute name
    dest: str
    description: str = ""


@dataclass(frozen=True)
class BookContentRow(ItemMeta):
    """One file under a book's path, as shown by `book show`."""
    filename: str


@dataclass(frozen=True)
class WriteActionRow(ItemMeta):
    """One file write, as shown by `book pull`."""
    action: str          # "write" | "overwrite" | "[would] write" | "[would] overwrite"
    destination: str
    was_symlink: bool = False
```

`artbook` returns `Book`, `Manifest`, `WrittenFile`, `PullReport`
(per §4.3) — purely logical dataclasses with no rendering
awareness. The CLI command projects them into the `ItemMeta`
subclasses above before calling `views.render_table`.

### 5.1.4 Worked pseudocode — `book list`

```python
# cli/commands/book.py — list verb (simplified)
def _run_list(args, root, settings):
    arts = ArtbookSettings.from_base(settings)
    if not arts.distro_url:
        raise DistroNotConfiguredError()

    with tempfile.TemporaryDirectory() as td:
        manifest, clone_root = artbook.read_manifest(
            arts.distro_url, clone_into=Path(td),
        )
        sha = _git_short_sha(clone_root)

        if args.json:
            print(json.dumps({
                "distro": {
                    "name": manifest.name,
                    "description": manifest.description,
                    "url": arts.distro_url,
                    "sha": sha,
                },
                "books": [dataclasses.asdict(b) for b in manifest.books],
            }))
            return 0

        rows = [
            BookRow(
                name=b.name,
                src=b.src,
                dest=b.dest,
                description=b.description or "",
            )
            for b in manifest.books
        ]
        columns = [
            FieldSpec(key="name", label="Name"),
            FieldSpec(key="src", label="Source"),
            FieldSpec(key="dest", label="Destination"),
            FieldSpec(key="description", label="Description"),
        ]
        console.print(_header(manifest, arts.distro_url, sha))
        console.print(views.render_table(rows, columns))
        console.print(f"\n{len(rows)} book{'s' if len(rows) != 1 else ''}.")
        return 0
```

`book show` and `book pull` follow the same pattern: project
artbook dataclasses → `ItemMeta` subclasses → `render_table`. For
`pull`, the status-colours mapping (`{"write": "green",
"overwrite": "yellow", "error": "red"}`) is passed through
`status_colors=` to colour the `Action` column the same way kind
status colours work today.

### 5.1.5 Source resolution: local vs. remote (D23)

`book list` and `book show` choose their manifest source via a
three-step resolution:

1. **`--remote` set?** → fetch path (D4): shallow-clone
   `artbook.distro_url`. If `distro_url` is unset, exit 4.
2. **`<vault_root>/artbook.yaml` exists?** → **local mode**: call
   `artbook.manifest.load_manifest(vault_root)` directly. No
   clone, no tmpdir, no `distro_url` requirement.
3. **Else** → remote path (same as step 1).

`book pull` skips this resolution and goes straight to the
remote path (§5.4.1).

The data layer needs no API changes. `manifest.load_manifest(Path)`
already accepts any directory containing an `artbook.yaml`; the
local code path simply hands it the vault root instead of a
clone root.

**Local-mode failure semantics**

- Local manifest exists but is malformed / version mismatch →
  exit 1 with the local path in the error message. **No silent
  fallback to remote** — that would mask author bugs.
- Local mode does not produce a `distro_sha` — the manifest is
  the working tree, not a committed snapshot. Reports / JSON
  output omit `sha` and add `"source": "local"` (§5.2 / §5.3
  examples).

**Why not auto-detect for `pull` too?**

`book pull` writes `<book.src>/*` → `<destination>/*` per §7.
In a Layout B repo, `book.src` is `artifacts/agents/` (or
similar working-tree location) and the destination is
`<vault_root>/.claude/agents/` — which in this very repo is a
symlink farm pointing back at `<vault_root>/openstation/agents/`
or `<vault_root>/artifacts/agents/`. A local-mode pull would
unlink those symlinks (D19) and replace them with regular
files, which is exactly the dogfood-migration scenario s0029
§1.3 explicitly defers. Keeping `pull` remote-only makes its
semantics unambiguous and leaves dogfood migration to its own
spec.

For "what would pull do" inspection from inside the distro,
`--dry-run` is the answer; it just needs a configured
`distro_url`.

**`--remote` rationale**

The override exists for one purpose: "I'm in the distro repo,
but I want to see what consumers will get when they pull from
the published `main` branch — not what's on my working tree."
This is the only case where local and remote can disagree.

### 5.2 `artifacts book list`

Resolves the manifest source per §5.1.5: local
`<vault_root>/artbook.yaml` when present (and `--remote` not set),
otherwise a shallow clone of `artbook.distro_url`. Parses the
manifest and prints one row per book.

**Default Rich-table output — remote mode:**

```
Distro: artifacts-os-defaults — Default agents for artifacts-os consumers.
URL:    https://github.com/example/artbook-defaults @ a1b2c3d

Name    Source   Destination       Description
agents  agents/  .claude/agents/   Default agent specs.

1 book.
```

**Default Rich-table output — local mode (D23):**

The `URL:` line is replaced by `Source:` pointing at the
working-tree manifest. No SHA is reported (the source is the
checkout, not a commit).

```
Distro: artifacts-os — Default agents shipped by artifacts-os for consumers of the library.
Source: local artbook.yaml (working tree)

Name    Source             Destination       Description
agents  artifacts/agents/  .claude/agents/   Default agent specs (architect, developer, researcher, etc.).

1 book.
```

**`--json` output — remote mode (one JSON object):**

```json
{
  "distro": {
    "name": "artifacts-os-defaults",
    "description": "Default agents for artifacts-os consumers.",
    "url": "https://github.com/example/artbook-defaults",
    "sha": "a1b2c3d",
    "source": "remote"
  },
  "books": [
    {
      "name": "agents",
      "src": "agents/",
      "dest": ".claude/agents/",
      "description": "Default agent specs."
    }
  ]
}
```

**`--json` output — local mode:**

`url` and `sha` are omitted; `source` flips to `"local"` and a
`manifest_path` (vault-relative) is included.

```json
{
  "distro": {
    "name": "artifacts-os",
    "description": "Default agents shipped by artifacts-os for consumers of the library.",
    "source": "local",
    "manifest_path": "artbook.yaml"
  },
  "books": [
    {
      "name": "agents",
      "src": "artifacts/agents/",
      "dest": ".claude/agents/",
      "description": "Default agent specs (architect, developer, researcher, etc.)."
    }
  ]
}
```

### 5.3 `artifacts book show <name>`

Resolves the manifest source per §5.1.5, parses the manifest,
resolves the book by name, and renders its details. In **local
mode** the book's contents are walked from the working tree
(`<vault_root>/<book.src>/`); in **remote mode** they are walked
from the shallow clone.

The output additionally lists the files the consumer would
receive on `pull`:

- If the book declares `files: [...]` (D18), those are the
  contents.
- Otherwise the handler walks `book.src/` and applies the D20
  convention filter (`*.md` minus `README.md` minus dotfiles).

**Default Rich-table output — remote mode:**

```
Book:        agents
Source:      agents/
Destination: .claude/agents/
Description: Default agent specs.

Distro:      artifacts-os-defaults
URL:         https://github.com/example/artbook-defaults @ a1b2c3d

Contents (9 files):
  architect.md
  author.md
  developer.md
  devrel.md
  product-manager.md
  project-manager.md
  researcher.md
  security-engineer.md
  technical-writer.md
```

**Default Rich-table output — local mode (D23):**

The `URL:` line is replaced by `Manifest:` pointing at the
working-tree manifest. Otherwise identical.

```
Book:        agents
Source:      artifacts/agents/
Destination: .claude/agents/
Description: Default agent specs (architect, developer, researcher, etc.).

Distro:      artifacts-os
Manifest:    local artbook.yaml (working tree)

Contents (10 files):
  architect.md
  author.md
  developer.md
  devrel.md
  product-manager.md
  project-manager.md
  qa.md
  researcher.md
  security-engineer.md
  technical-writer.md
```

**`--json` output — remote mode:**

```json
{
  "book": {
    "name": "agents",
    "src": "agents/",
    "dest": ".claude/agents/",
    "description": "Default agent specs."
  },
  "distro": {
    "name": "artifacts-os-defaults",
    "url": "https://github.com/example/artbook-defaults",
    "sha": "a1b2c3d",
    "source": "remote"
  },
  "contents": [
    "architect.md", "author.md", "developer.md", "devrel.md",
    "product-manager.md", "project-manager.md", "researcher.md",
    "security-engineer.md", "technical-writer.md"
  ]
}
```

The `"destination"` top-level key from v1 is removed — the
destination is already in `book.dest`. JSON output now matches
the dataclass exactly via `dataclasses.asdict(book)`.

**`--json` output — local mode:**

`url` and `sha` are omitted; `source` flips to `"local"` and
`manifest_path` (vault-relative) is included.

```json
{
  "book": {
    "name": "agents",
    "src": "artifacts/agents/",
    "dest": ".claude/agents/",
    "description": "Default agent specs (architect, developer, researcher, etc.)."
  },
  "distro": {
    "name": "artifacts-os",
    "source": "local",
    "manifest_path": "artbook.yaml"
  },
  "contents": [
    "architect.md", "author.md", "developer.md", "devrel.md",
    "product-manager.md", "project-manager.md", "qa.md",
    "researcher.md", "security-engineer.md", "technical-writer.md"
  ]
}
```

### 5.4 `artifacts book pull <name>`

Reads `artbook.distro_url`, clones the distro, parses the
manifest, resolves the book, copies the book's content into the
destination per §7, **overwriting any existing files** (D9).
Files in the destination that are **not** in the book are
**not** touched.

`--dry-run` plans the writes but does not perform them. Output
prefixes each line with `[would]`.

**Default Rich-table output (success):**

```
Pulling book 'agents' from artifacts-os-defaults @ a1b2c3d…

Action  Destination
write   .claude/agents/architect.md
write   .claude/agents/author.md
write   .claude/agents/developer.md
write   .claude/agents/devrel.md
write   .claude/agents/product-manager.md
write   .claude/agents/project-manager.md
write   .claude/agents/researcher.md
write   .claude/agents/security-engineer.md
write   .claude/agents/technical-writer.md

Summary: 9 written (0 overwritten, 9 new).
```

When destinations already exist, the `Action` column reads
`overwrite` and the summary's split changes accordingly:

```
Summary: 9 written (9 overwritten, 0 new).
```

**`--json` output (one JSONL line per write + final summary line):**

```jsonl
{"action": "write", "destination": ".claude/agents/architect.md", "overwritten": false}
{"action": "write", "destination": ".claude/agents/author.md", "overwritten": false}
…
{"summary": {"written": 9, "overwritten": 0, "new": 9}, "distro": {"url": "https://github.com/example/artbook-defaults", "sha": "a1b2c3d"}, "book": "agents"}
```

#### 5.4.1 `pull` is always remote (D23)

Unlike `list` / `show`, `pull` does **not** auto-detect a local
manifest. It always clones `artbook.distro_url`. Rationale is in
D23 and §5.1.5: a local pull in a Layout B repo would unlink the
symlink farm at the destination and replace it with regular
files — the dogfood migration scenario explicitly deferred in
§1.3 / §7.2.1.

If `artbook.distro_url` is unset, `pull` exits 4 even when a
local `artbook.yaml` exists. The error message hints at
`book list` / `book show` (which work locally) as alternatives
for inspection.

### 5.5 Exit codes

| Code | Condition |
|------|-----------|
| 0 | Success. |
| 1 | Runtime error: clone failed, manifest parse / validation failed (local **or** remote, including `dest` escapes vault and v1 `type:` field present), unknown book name, write failed. The error message identifies which. (v1 also listed "unknown book type" here; removed in v2 along with the `type:` field — see D24.) |
| 2 | Usage error: bad flag, missing required positional, `--dry-run` on a non-`pull` verb, `--remote` on `pull` (always remote already). |
| 3 | Vault not initialised (`artifacts.yaml` not found by `find_vault_root`). |
| 4 | `artbook.distro_url` missing or empty in `artifacts.yaml`. Per D23 this only fires when **no** local `artbook.yaml` is present at the vault root **and** the verb requires remote resolution. `list` / `show` running in local mode never trip this; `pull` always does when `distro_url` is unset; `list --remote` / `show --remote` do when `distro_url` is unset regardless of local manifest presence. |

### 5.6 Error message conventions

Errors print to stderr in the established artifacts-os format:

```
error: <one-line cause>
       <one-line remediation hint>
```

Examples:

```
error: artbook.distro_url not configured in artifacts.yaml
       Add `artbook.distro_url: <git-url>` to artifacts.yaml.

error: book 'kinds' not found in distro 'artifacts-os-defaults'
       Available books: agents.

error: book 'agents' dest '../../../etc/cron.d/' escapes the vault root
       The dest field must resolve to a path inside the vault.

error: book 'agents' has removed field 'type' (v1)
       Drop the field — v2 derives placement from `dest:`.

error: git clone failed (exit 128)
       URL: https://github.com/example/artbook-defaults
       stderr: fatal: Authentication failed for ...
```

Local-mode-specific (D23):

```
error: failed to parse local artbook.yaml at /path/to/repo/artbook.yaml
       this artifacts-os version speaks artbook manifest v1; distro declares v2
       Pass --remote to inspect the published distro instead.

error: artbook.distro_url not configured in artifacts.yaml
       Add `artbook.distro_url: <git-url>` to artifacts.yaml.
       (A local artbook.yaml is present — `book list` and `book show`
       work without --remote; `book pull` requires distro_url.)
```

## 6. Pull Mechanics (Scope Item 4)

### 6.1 Strategy choice — shallow clone

The MVP fetches via:

```python
subprocess.run(
    ["git", "clone", "--depth", "1", "--branch", "main",
     "--single-branch", distro_url, str(tmpdir)],
    check=True,
    capture_output=True,
    text=True,
)
```

**Alternatives considered:**

| Option | Verdict | Why |
|--------|---------|-----|
| Full clone (no `--depth 1`) | Rejected | Bandwidth waste; v1 needs only the tip of main. |
| HTTP archive (`git archive` via GitHub/GitLab REST) | Rejected for MVP | Per-host protocol differences; would need adapters for GitHub vs. GitLab vs. self-hosted; adds a runtime HTTP client dependency. |
| Sparse checkout | Rejected | More setup complexity than full shallow clone; the win (skipping non-book files) is small because distros are expected to be tiny. |
| `pip install`-style wheel | Rejected | Forces every distro to publish a package; the user story is "point at a git URL". |

**Chosen**: shallow clone wins because (a) it works against every
git host with no per-host code, (b) `git` is a universal CLI
dependency we already assume (the artifacts-os repo lives in
git), (c) zero new Python dependencies, (d) trivial to teach a
contributor.

### 6.2 Branch — always `main`

The clone always uses `--branch main` (D5). No CLI flag, no
manifest field, no `artifacts.yaml` override for the ref.

Why: pinning is its own design space (refs vs. tags vs.
commit SHAs vs. semver). MVP excludes it (t0150 out-of-scope).
Distros that don't use `main` as the default branch are
incompatible with the MVP; the spec for `update` / `diff`
introduces ref selection.

### 6.3 Caching — none

Every CLI invocation performs a fresh shallow clone into a new
`tempfile.TemporaryDirectory()` and tears it down on exit (D6).

Implications:

- `artifacts book list` → 1 clone.
- `artifacts book show <name>` → 1 clone.
- `artifacts book pull <name>` → 1 clone.

The tmpdir lifecycle is owned by a single context manager in the
CLI command (`with tempfile.TemporaryDirectory() as td:`). The
`read_manifest` and `pull_book` API functions accept the clone
root as a parameter so the CLI can clone once per invocation and
hand the same root to both calls (avoiding a redundant clone
within one invocation — see §4.4).

### 6.4 Tmpdir layout

```
/tmp/artbook-XXXXXX/
├── artbook.yaml
└── <book.src>/...        # only the cloned content; nothing else
```

The tmpdir is removed unconditionally on CLI exit, including on
error (the `TemporaryDirectory` context manager handles cleanup
in `__exit__`).

### 6.5 Failure handling

- **Clone failure** (non-zero exit from `git clone`) → raise
  `FetchError` carrying `returncode`, `stderr`. CLI exits 1
  with the message from §5.6.
- **Manifest missing in clone** → raise `ManifestError("artbook.yaml
  not found at distro root")`.
- **Manifest version mismatch** (`version != 1`) → raise
  `ManifestError("this artifacts-os version speaks artbook
  manifest v1; distro declares v<N>")`. The check runs before
  any other field validation so an outdated client never
  partially interprets a future schema.
- **Manifest parse error** (YAML syntax, missing required field,
  duplicate book name, `..` in path, `files` entry containing `/`,
  `files` entry not present under `book.src`) → raise
  `ManifestError` with the offending location.
- **Unknown book name** at `find_book` → raise `UnknownBookError`.
- **dest escapes vault** (e.g. `..` segment, absolute path) at
  `parse_manifest` → raise `ManifestError` (D25 / §7.1.1).
- **dest resolves outside vault** at write time (defense in depth
  against symlink-target tricks) → raise `ArtbookError`.

The MVP performs no retries. Transient network errors require
the operator to re-run the command.

### 6.6 Determinism notes

- The clone targets a fresh tmpdir each invocation, so no stale
  state can leak across runs.
- The reported `distro_sha` (`git rev-parse --short HEAD` after
  clone) lets reports be reproduced when the distro publishes a
  follow-up commit.
- File system writes use the established core idiom:
  `O_CREAT | O_EXCL` then `os.replace`-style atomic rename when
  overwriting (no torn writes). When overwriting, the
  destination directory must already exist or be created with
  `os.makedirs(exist_ok=True)`.

## 7. Local Placement (Scope Item 5)

### 7.1 Per-book `dest:` (D25, supersedes the `_PLACEMENT` table)

Each book carries its own consumer destination as a string in
the manifest:

```yaml
books:
  - name: agents
    src: agents/
    dest: .claude/agents/
```

The placement helper is now a one-line join after parse-time
validation:

```python
def destination_for(book: Book, vault_root: Path) -> Path:
    """Return the on-disk destination for *book* under *vault_root*.

    The dest field was validated at manifest-parse time to be a
    safe vault-relative path (D25, §7.1.1). No further checks here.
    """
    return vault_root / book.dest
```

There is no per-type registry, no dispatch, no
`UnknownBookTypeError`. Every book — whether it carries
agents, skills, commands, or anything else a future distro
author ships — flows through the same code path.

### 7.1.1 The vault-escape safety guard

Because `dest` is now manifest-controlled (was code-controlled
in v1), the parser must enforce that it cannot direct writes
outside the consumer's project. The rule, applied during
`manifest.parse_manifest()`:

```python
def _validate_dest(name: str, dest: str) -> None:
    """Reject dest fields that escape the vault root."""
    if not dest or not isinstance(dest, str):
        raise ManifestError(f"book '{name}' dest must be a non-empty string")
    if dest.startswith("/"):
        raise ManifestError(
            f"book '{name}' dest '{dest}' is absolute; "
            "dest must be vault-relative"
        )
    if ".." in Path(dest).parts:
        raise ManifestError(
            f"book '{name}' dest '{dest}' contains '..'; "
            "dest must not escape the vault root"
        )
```

A run-time defense-in-depth check at write time (in
`_atomic_write`) also confirms that the resolved destination is
under `vault_root.resolve()`, guarding against pathological
symlink-target tricks that a static string check cannot catch:

```python
def _ensure_inside_vault(dst: Path, vault_root: Path) -> None:
    real_dst = dst.resolve()
    real_root = vault_root.resolve()
    if not real_dst.is_relative_to(real_root):
        raise ArtbookError(
            f"refusing to write outside vault: {dst} → {real_dst}"
        )
```

The pair (parse-time string check + write-time resolved check)
gives the same trust boundary that `_PLACEMENT`'s implicit
whitelist provided in v1, while letting the destination be
data-driven.

### 7.2 Conventional destinations (informational, non-binding)

Although `dest` is per-book and free-form, conventional values
exist for the common cases. Distro authors are encouraged to use
them so consumers' tooling integrates without surprise:

| Book content | Conventional `dest:` | Why |
|--------------|----------------------|-----|
| Claude agents | `.claude/agents/` | Where Claude Code reads agent specs from. |
| Claude skills | `.claude/skills/` | Where Claude Code reads skills from. |
| Claude commands | `.claude/commands/` | Where Claude Code reads slash commands from. |
| Hooks scripts | `.claude/hooks/` | Where Claude Code looks for harness hooks. |
| Artifact kinds | `artifacts/kinds/` | artifacts-os kind definitions. |

None of these are enforced. A distro that wants to ship agents
to `agents/` (no `.claude/` prefix) or anywhere else may do so;
the consumer signs up for that placement when they set
`artbook.distro_url`. Convention is a recommendation, not a rule.

### 7.2.1 The MVP does not solve replication (carried over from D8)

artifacts-os ecosystems often replicate the same agent files
across `.claude/agents/`, `.openstation/agents/`,
`artifacts/agents/`, and sometimes `src/.../templates/agents/`
(this repo does). **The MVP does not address this.** Each book
writes to **one** destination (its `dest:` field) and leaves
cross-replica consistency to the consumer.

This is a deliberate scope cut, mirrored on both sides:

- **Distro side**: a distro repo that has the same content in
  multiple places chooses **one** as the source via
  `artbook.yaml :: books[].src`. Whichever path the manifest
  names is the canonical replica for consumers; the others are
  ignored by `book pull`. (Authors who *do* want consumers to
  receive the content in multiple destinations can list the
  book twice with the same `src` and different `dest` values —
  the v2 schema allows it. The MVP test suite covers single-
  destination; multi-destination is incidentally supported but
  not exercised.)
- **Consumer side**: `book pull` writes only to `book.dest`. If
  the consumer wants the same content at additional locations,
  they wire it themselves (symlink, second copy, etc.) — outside
  the MVP.

A future `book sync` / multi-destination spec is no longer needed
just to support this; the schema covers it. What is still
deferred is **consumer-side configuration** (e.g. an
`artifacts.yaml :: artbook.dest_overrides` map that lets the
consumer redirect a book's destination without re-publishing the
distro).

### 7.3 Universal copy rules (was: agents-specific)

In v1 the copy handler was indexed by `book.type` and the only
implementation was `_copy_agents`. With `type` gone (D24), there
is exactly **one** copy strategy and it applies to every book.
It selects the files to ship per D18 / D20 and writes each one
through the unlink-then-write atomic sequence per D19:

```python
_EXCLUDE_NAMES = {"readme.md"}                       # case-insensitive (D20)
_RECURSE_EXCLUDE_DIRS = {"__pycache__"}              # D26
_RECURSE_EXCLUDE_SUFFIXES = {".pyc", ".pyo"}         # D26


def _select_files(src_dir: Path, book: Book) -> list[tuple[Path, Path]]:
    """Return [(absolute_source, relative_to_dest), ...] for the book.

    Three modes:
      - D18 allowlist (`book.files` set)              → flat, explicit
      - D20 flat walker (default, `recurse=False`)    → `*.md`, top-level only
      - D26 recurse walker (`recurse=True`)           → folder-of-folders, all files
    """
    if book.files is not None:
        # D18 — explicit allowlist; every name must exist as a file under src_dir.
        out: list[tuple[Path, Path]] = []
        for name in book.files:
            if "/" in name or "\\" in name:
                raise ManifestError(
                    f"book '{book.name}' files entry '{name}' contains a path separator; "
                    "files entries are flat filenames relative to book.src."
                )
            candidate = src_dir / name
            if not candidate.is_file():
                raise ManifestError(
                    f"book '{book.name}' files entry '{name}' not found at {candidate}"
                )
            out.append((candidate, Path(name)))
        return out

    if book.recurse:
        # D26 — folder-of-folders. For each subdirectory of src_dir, walk
        # the entire subtree and yield (abs_file, relative_path_from_src_dir).
        # Loose files at src_dir's root are silently ignored.
        out = []
        for unit in sorted(src_dir.iterdir()):
            if not unit.is_dir():
                continue
            if unit.name.startswith(".") or unit.name in _RECURSE_EXCLUDE_DIRS:
                continue
            for src_file in sorted(unit.rglob("*")):
                if not src_file.is_file():
                    continue
                # Skip anything under an excluded directory at any depth.
                if any(p.startswith(".") or p in _RECURSE_EXCLUDE_DIRS
                       for p in src_file.relative_to(src_dir).parts[:-1]):
                    continue
                if src_file.name.startswith("."):
                    continue
                if src_file.suffix.lower() in _RECURSE_EXCLUDE_SUFFIXES:
                    continue
                out.append((src_file, src_file.relative_to(src_dir)))
        return out

    # D20 — flat walker: *.md, exclude README.md (case-insensitive) and dotfiles.
    out = []
    for src_file in sorted(src_dir.iterdir()):
        if not src_file.is_file():
            continue
        if src_file.suffix != ".md":
            continue
        if src_file.name.startswith("."):
            continue
        if src_file.name.lower() in _EXCLUDE_NAMES:
            continue
        out.append((src_file, Path(src_file.name)))
    return out


def _copy_book(clone_root: Path, book: Book, dest: Path, vault_root: Path) -> Iterable[WrittenFile]:
    """Universal copy handler — applies to every book in v2 (D24)."""
    src_dir = clone_root / book.src
    if not src_dir.is_dir():
        raise ManifestError(
            f"book '{book.name}' src '{book.src}' is not a directory in the distro"
        )
    dest.mkdir(parents=True, exist_ok=True)
    for src_file, rel_path in _select_files(src_dir, book):
        dest_file = dest / rel_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)   # D26 — recurse may create nested dirs
        _ensure_inside_vault(dest_file, vault_root)   # §7.1.1 defense-in-depth (still per-file)
        yield _atomic_write(src_file, dest_file)


def _atomic_write(src: Path, dst: Path) -> WrittenFile:
    """Unlink-then-write per D19; atomic via *.tmp + os.replace."""
    was_symlink = dst.is_symlink()
    existed = dst.exists() or was_symlink  # is_symlink() doesn't imply exists() for broken links
    if was_symlink or (dst.exists() and not dst.is_file()):
        # Symlink or other non-regular file → unlink first.
        dst.unlink()
    elif dst.is_dir():
        raise ArtbookError(
            f"destination {dst} is a directory; refusing to overwrite"
        )
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)
    return WrittenFile(
        source=src,
        destination=dst,
        overwritten=existed,
        was_symlink=was_symlink,
    )
```

Notes:

- Selection: when `book.files` is set the allowlist is the
  source of truth (D18); when absent the D20 walker applies the
  convention filter (`*.md`, exclude `README.md` case-insensitive,
  exclude dotfiles).
- The walker is **opinionated to markdown**. Non-`.md` files are
  silently skipped. Distro authors shipping non-markdown content
  (e.g. JSON kind definitions, Python hooks) use the `files:`
  allowlist, which ignores extensions entirely. This is a
  deliberate trade-off: walker mode optimises for the common case
  (agents/skills/commands as markdown); other cases pay the cost
  of an explicit list.
- Sub-directories are **not** recursed by the D20 flat walker
  (`recurse: false`, default). Allowlist entries cannot contain
  `/` (D20 / Q4). The walker ships flat directories of
  `<slug>.md` files. Folder-of-folders content (e.g. skills,
  kinds) uses **`recurse: true`** (D26) instead, which ships
  each direct subdirectory as a unit and preserves its internal
  structure under `dest/<unit>/...`. The recurse walker keeps
  all file types (no `*.md`-only filter), excludes
  `__pycache__/`, `*.pyc`, `*.pyo`, dotfiles, and dotted
  directories.
- The write is `shutil.copyfile` (content only) — no permission
  preservation, no exec bits, no extended attributes. The MVP's
  primary content is plain markdown.
- **Atomicity**: write to `<dest>.tmp` then `os.replace` to
  `<dest>`. Robust against interrupt mid-write and against
  partial reads from a concurrent process.
- **Symlink handling (D19)**: when the destination is a symlink
  (broken or not), it is unlinked **before** the `*.tmp` is
  written. The replacement is a regular file. `WrittenFile.was_symlink`
  records the prior state for the report.

### 7.4 What happens to existing files (D9 / D19)

| Pre-existing destination state | MVP behaviour |
|--------------------------------|---------------|
| Destination file does not exist | Write new file. `WrittenFile.overwritten = False`, `was_symlink = False`. |
| Destination file exists, same content | Overwrite anyway. `WrittenFile.overwritten = True`. (No content compare in MVP — keeps the code simple; perf cost is one re-write per identical file.) |
| Destination file exists, different content | Overwrite. `WrittenFile.overwritten = True`. **No backup, no `.orig` sidecar, no prompt.** |
| Destination is a symlink (any target) | **Unlink the symlink, then write a regular file** (D19). `WrittenFile.was_symlink = True`. The symlink's target is **not** mutated. |
| Destination is a broken symlink | Same as live symlink — unlink, then write a regular file. `was_symlink = True`. |
| Destination is a directory | Hard error. Raise `ArtbookError`; exit 1. (A directory where the MVP expects a file is a structural mismatch the user must resolve.) |
| Destination parent directory does not exist | Created with `os.makedirs(exist_ok=True)`. |
| File present in destination but not in book | **Left alone.** The MVP does not delete extras. Cleanup is part of a future `book update` / `remove` spec. |

### 7.5 No staging

The MVP writes directly to the destination — there is no
"stage then commit" two-step. Half-written state is possible if
the process is killed mid-pull (one file may be old, another
new). The operator's recovery is to re-run `artifacts book
pull agents`, which is idempotent given a stable distro tip
(§5.4 / §6.6).

## 8. Worked End-to-End Example (Scope Item 6)

### 8.1 Setup — a fresh consumer

A fresh repo `my-project/` with no agents installed:

```
my-project/
├── README.md
└── (no .claude/, no artifacts.yaml)
```

The consumer has `artifacts-os` (this library) installed via
`pip install artifacts-os`.

### 8.2 Step 1 — initialise the vault

```
$ cd my-project
$ artifacts init
✓ Wrote artifacts.yaml (tier: standard)
✓ Wrote CLAUDE.md
✓ Created artifacts/ vault tree
```

After `init`, the project root has an `artifacts.yaml` that the
artbook module will extend.

### 8.3 Step 2 — configure the distro URL

The consumer edits `artifacts.yaml` and adds:

```yaml
# artifacts.yaml (excerpt — only the new block shown)
artbook:
  distro_url: https://github.com/example/artbook-defaults
```

(Future ergonomic improvement, out of scope for this spec: an
`artifacts init` flag like `--artbook-url=<url>` to write this
key on first run.)

### 8.4 Step 3 — list available books

```
$ artifacts book list
Distro: artifacts-os-defaults — Default agents for artifacts-os consumers.
URL:    https://github.com/example/artbook-defaults @ a1b2c3d

Name    Source   Destination       Description
agents  agents/  .claude/agents/   Default agent specs.

1 book.
```

Internally:

1. CLI reads `artbook.distro_url` from `artifacts.yaml` →
   `https://github.com/example/artbook-defaults`.
2. CLI calls `artbook.read_manifest(url)` which:
   a. Creates `tempfile.TemporaryDirectory()` →
      `/tmp/artbook-abc123/`.
   b. Runs `git clone --depth 1 --branch main --single-branch
      https://github.com/example/artbook-defaults /tmp/artbook-abc123`.
   c. Reads `/tmp/artbook-abc123/artbook.yaml`, runs
      `yaml.safe_load`, validates `version == 1`.
   d. Returns `Manifest(version=1, ...)` + `Path("/tmp/artbook-abc123")`.
3. CLI runs `git rev-parse --short HEAD` inside the clone for
   the SHA, then renders the Rich table.
4. CLI exits 0; the context manager removes the tmpdir.

### 8.5 Step 4 — inspect a book

```
$ artifacts book show agents
Book:        agents
Source:      agents/
Destination: .claude/agents/
Description: Default agent specs.

Distro:      artifacts-os-defaults
URL:         https://github.com/example/artbook-defaults @ a1b2c3d

Contents (9 files):
  architect.md
  author.md
  developer.md
  devrel.md
  product-manager.md
  project-manager.md
  researcher.md
  security-engineer.md
  technical-writer.md
```

Internally: same as `list`, plus `find_book(manifest, "agents")`
and either (a) honouring the book's `files` allowlist (D18) when
set, or (b) a non-recursive walk of `<clone>/agents/` with the
D20 filter (`*.md` minus `README.md` minus dotfiles). The
`Destination` is read directly from `book.dest` (D25).

### 8.6 Step 5 — pull the book

```
$ artifacts book pull agents
Pulling book 'agents' from artifacts-os-defaults @ a1b2c3d…

Action  Destination
write   .claude/agents/architect.md
write   .claude/agents/author.md
write   .claude/agents/developer.md
write   .claude/agents/devrel.md
write   .claude/agents/product-manager.md
write   .claude/agents/project-manager.md
write   .claude/agents/researcher.md
write   .claude/agents/security-engineer.md
write   .claude/agents/technical-writer.md

Summary: 9 written (0 overwritten, 9 new).
```

After the pull, the project tree is:

```
my-project/
├── README.md
├── artifacts.yaml
├── CLAUDE.md
├── artifacts/...
└── .claude/
    └── agents/
        ├── architect.md
        ├── author.md
        ├── developer.md
        ├── devrel.md
        ├── product-manager.md
        ├── project-manager.md
        ├── researcher.md
        ├── security-engineer.md
        └── technical-writer.md
```

### 8.7 Step 6 — verify working agents

Opening the project in Claude Code surfaces all nine agent
specs from `.claude/agents/`. They are immediately usable —
e.g. invoking the `developer` agent or the `researcher` agent
from a Claude session resolves their spec from `.claude/agents/`,
matching the parent-task verification item ("a test repo with no
existing agent files runs `artifacts book pull agents` and ends
up with working agents").

### 8.8 Re-running `pull` is safe

```
$ artifacts book pull agents
…
Summary: 9 written (9 overwritten, 0 new).
```

The second run overwrites every file (no content-compare
shortcut in MVP — D9 / §7.4) and reports 9 overwrites. The
project tree is byte-identical to the first run's output as
long as the distro's `main` has not advanced.

## 9. Future Work (informational, not part of MVP)

Each item below is **deferred to its own spec** and should not
shape the MVP code more than the seams listed in §10.

- `artifacts book update <name>` — re-pull only changed files,
  with a diff summary.
- `artifacts book diff <name>` — show local vs. distro
  divergence without writing.
- `artifacts book remove <name>` — delete the destination of a
  previously pulled book.
- ~~Additional book types (`kinds`, `skills`, `commands`,
  `hooks`) — each adds a placement entry plus a copy handler.~~
  **Resolved by D24** — additional content shapes ship as
  additional book entries with their own `src`/`dest`; no
  library changes required.
- Optional `kind:` annotation for kind-aware pull (frontmatter
  validation against `artifacts/kinds/<id>/kind.json`). Additive
  to the v2 schema; non-breaking.
- Multi-distro per project — list of distros, per-book
  selection of source distro.
- Override layer — consumer-owned files that survive `pull` and
  override per-name.
- Private-distro auth (token-based git auth, SSH keys).
- Version pinning (manifest-level `ref:` or
  `artifacts.yaml`-level pin).
- Lock files (`.artbook.lock`) capturing exact SHAs of last
  pull.
- Caching of recent clones (optional opt-in to amortise
  bandwidth).
- Offline support and bundled distros.
- Dogfood migration: move this repo's `openstation/agents/`
  and its symlink farm to be sync output from a self-hosted
  distro.
- Third-party book authoring guide.

## 10. Implementation Seams for Future Specs

The MVP code should make the following extensions cheap when
their own specs land:

| Future need | MVP seam |
|-------------|----------|
| ~~New book types~~ | **No longer needed.** With `type` dropped (D24), any "book type" is just another book entry with its own `src`/`dest`. Distro authors add books without library changes. |
| Kind-aware behavior on pull (optional frontmatter validation, schema enforcement) | Additive optional `kind: <id>` field at book level — opt-in, non-breaking. The `Book` dataclass gains a `kind: str \| None = None` field; pull dispatches through a small registry only when `kind` is set. |
| Pull-time diff | `_copy_book` already yields `WrittenFile(overwritten=..., was_symlink=...)`; a future diff step inspects this stream. |
| Lock file | `PullReport.distro_sha` and `WrittenFile` records are already structured for persistence. |
| Caching | The `read_manifest → pull_book` split (§4.4) accepts an already-populated `clone_root`; a cache layer would supply that root instead of cloning fresh. |
| Multi-distro | `PullReport.distro_url` already in the report; adding a list of `(url, manifest)` is mechanical. |
| Same content to multiple destinations | Already supported in v2: list the book twice with the same `src` and different `dest`. The MVP test suite covers single-destination; multi-destination is incidentally allowed. A future ergonomic improvement is `dest: [path1, path2]` syntactic sugar. |
| Consumer-side dest override | Add `artbook.dest_overrides: {<book-name>: <path>}` to `artifacts.yaml`; consult before applying `book.dest`. The vault-escape guard (§7.1.1) applies to overrides too. |
| Schema migrations | `Manifest.version` and the v1 check in `read_manifest` give the version gate. The v1→v2 transition demonstrated this — v2 rejects the removed `type:` field with a clear error rather than silently mis-parsing. |
| Manifest format change | `manifest.py` isolates `yaml.safe_load`; swapping for another parser touches one module. |
| New tabular output (any verb, any future kind) | `views.render_table` accepts any `Sequence[ItemMeta]` after the D22 refactor. New renderable types inherit from `ItemMeta` and (in 99% of cases) rely on the default attribute-lookup `cell` — no `frontmatter` plumbing required. No copy-paste of Rich styling. |
| Local-mode pull (deferred dogfood migration) | The CLI's local-vs-remote resolution (D23 / §5.1.5) is already factored into `list` / `show`. Lifting `pull` into the same resolver is mechanical once dogfood migration is specified — read `manifest.load_manifest(vault_root)`, run `_copy_book` over a working-tree source. The data layer needs no API change. |
| Source resolution beyond local/remote (cache, mirror, override) | The two-step resolver in §5.1.5 (`--remote` flag → manifest source → parse) is small; extending it to a registry of source providers is a one-file change. |
| Per-unit pull granularity in recurse mode (D26) | `recurse: true` ships all units of a book; future `artifacts book pull skills/<unit>` selects one. The placement layer already returns `(src, rel_path)` pairs; the CLI would just filter the iterator by `rel_path.parts[0] == <unit>`. No data-layer change needed. |
| Recurse-mode allowlist (`tree_files:`) | D26 makes `recurse` and `files:` mutually exclusive. A future `tree_files: [<unit>/<file>, ...]` field (or simply allowing `/` in `files:` when `recurse=true`) lifts that restriction with one schema edit and one parser branch. |

No code in the MVP commits to a contradiction with any of the
above — the goal is "easy to extend", not "hard to remove".

## 11. Verification Mapping

This spec addresses every t0151 verification item:

- [x] Spec written and committed under `openstation/specs/`
      (this file).
- [x] All six scope items addressed:
      1. `artbook.yaml` schema → §3.
      2. `artbook` module layout → §4.
      3. CLI surface → §5 (incl. local-vs-remote resolution
         §5.1.5 / D23).
      4. Pull mechanics → §6.
      5. Local placement → §7.
      6. Worked example → §8.
- [x] Worked example: §8 walks a fresh consumer end-to-end from
      `init` through `pull` to verified working agents in
      `.claude/agents/`.
- [x] Out-of-scope items explicitly listed → §1.3, §9.
- [ ] Architect promotes spec to `review` for owner approval —
      pending after this spec lands.

## 12. References

- Parent task: [[t0150-artbook-distribution-model]] (user story,
  MVP cut, out-of-scope list).
- This spec's task: [[t0151-spec-the-artbook-model]].
- Inventory: [[n0011-distributable-harness-layers-inventory]],
  [[n0012-distributable-harness-layers-to-merge]].
- Earlier (broader) spec: [[s0028-distributable-harness-sync-model]]
  — reference only; this MVP is a fresh, thinner document.
- Settings extension pattern:
  [[s0010-core-settings-module-spec]].
- CLI conventions: `CLAUDE.md :: ## CLI Conventions`.
