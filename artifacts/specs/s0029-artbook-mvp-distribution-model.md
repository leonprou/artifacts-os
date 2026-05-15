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
   exact behaviour, output format, exit codes. (§5)
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
| D3 | The MVP recognises one book type: `agents`. Any other `type` value aborts with `unknown book type '<x>'` (exit 1). | Lock the dispatch table; new types land via new specs. |
| D4 | Fetch strategy: shallow git clone (`git clone --depth 1 --branch main <url> <tmpdir>`) into a process-scoped temp directory; tear down on command exit. | Works with any git host (GitHub, GitLab, self-hosted); no per-host HTTP-archive negotiation; no extra runtime dependency beyond `git` on PATH; trivial to reason about. |
| D5 | Always fetch from `main`. No branch / ref / tag override in v1. | One ref means no version-resolution logic; pinning is a deferred spec. |
| D6 | No caching. Every `list`, `show`, and `pull` invocation performs a fresh shallow clone. | Eliminates cache-invalidation logic; cost is bandwidth, not correctness; MVP. |
| D7 | The distro URL lives at `artbook.distro_url` (new top-level key in `artifacts.yaml`). No CLI flag override in v1. | Single configured source per project matches the "one distro" scope; matches the established `views:` / `cli:` / `hooks:` key pattern. |
| D8 | The `agents` book type writes to **one** destination: `<vault_root>/.claude/agents/<file>.md`. | Claude Code is the universal target for agent files in the artifacts-os ecosystem; `.claude/agents/` is what every Claude Code project reads from. The MVP explicitly does **not** solve file replication on the consumer side — if a consumer also wants agents at `.openstation/agents/` or `artifacts/agents/`, that is their responsibility (manual copy, symlink farm, or a deferred spec). Same principle applies on the distro side: a repo with internal replication (`openstation/agents/` ≡ `.openstation/agents/` ≡ `.claude/agents/`) chooses **one** as the canonical source via `artbook.yaml :: books[].path`. |
| D9 | When a destination file already exists, overwrite it without prompt or backup. **If the destination is a symlink, it is unlinked first and replaced with a regular file** (D19). Files in the destination that are not in the book are left untouched. | Lean MVP — no merge logic, no diff prompts. Unlinking preserves the consumer's invariant that `book pull`'s output is plain files, not links to surprising targets. Operator chose this in t0150 directions §6 and Q1/Q2 follow-ups. |
| D10 | CLI surface is `artifacts book <verb>` — a two-word command with `book` as a resource-namespace prefix and `list / show / pull` as verbs. | Conscious exception to CLAUDE.md's "flat verbs" guideline: `book` is a resource noun, not a streaming/paging mode variant. Mirrors the established `artifacts.list.open-tasks` dotted-namespace precedent in the command set. |
| D11 | The `artbook` Python module lives at `src/artifacts_os/artbook/`, peer to `core`, `cli`, `views`. Dependencies: `core` only. **No rendering inside `artbook`** — it returns dataclasses; rendering is the CLI command's job (D21). | Pure-logic module is easy to reason about and test. Keeps the layering: `core` → `views` → `cli, tui`; `artbook` slots in as a leaf with `core` only, while the CLI command at `cli/commands/book.py` is the integration point that imports both `artbook` and `views`. |
| D12 | YAML parsing uses PyYAML's `safe_load`. PyYAML is already a transitive dependency of `python-frontmatter`. | No new direct dependency; matches what `core/settings.py` and `views/` already use to parse `artifacts.yaml`. |
| D13 | Git invocation uses `subprocess.run(["git", ...], check=True, capture_output=True)` — no `GitPython` or similar library. | Avoids a new dependency; the surface is one command (`clone`). |
| D14 | Manifest validation runs **before** any clone or write. Unknown / malformed manifest → exit 1 with an actionable error. | Fail fast; do not perform side effects against an invalid distro. |
| D15 | Exit codes: 0 ok, 1 runtime error (fetch / parse / write failed, unknown book, unknown type, manifest version mismatch), 2 usage error, 3 vault not initialised, 4 distro URL not configured. | Mirrors the established `artifacts` CLI exit-code convention (0/1/2/3) with one MVP-specific addition (4) for the new failure mode. |
| D16 | A book's `path` may point at any sub-tree of the distro repo. The repo is **not** required to organise content under a dedicated directory; `artbook.yaml` is a view over the existing repo, not a layout decree. | Lets an existing project repo become its own distro by adding one manifest file — no content duplication, no reorganisation. The same files can serve the project's own use and consumers of the artbook simultaneously. |
| D17 | The manifest carries a required top-level `version: 1` field. v1 clients reject `version != 1` with a clear "this client speaks artbook v1; manifest declares v<N>" error. | Cheap to add now, painful to retrofit later. Future schema migrations land without breaking older artbook clients. The check is one line; the field is one byte of overhead. |
| D18 | Each book entry accepts an optional `files: [<filename>, ...]` allowlist. When present, the agents handler ships **only** the files listed (each must exist under `book.path/`; missing files exit 1). When absent, the handler walks `book.path/` and ships all `*.md` files except `README.md` and dotfiles (D20). | Two ergonomic modes: (a) directory-is-the-book (omit `files`, rely on convention); (b) explicit lock-list (use `files`). Distro authors who add an unrelated file to the directory aren't surprised when it lands in consumers; consumers aren't surprised by drift when the distro author adds files. |
| D19 | The destination overwrite uses an unlink-then-write strategy: if a destination path is a symlink (or any non-regular file), it is removed and a regular file is written in its place. Atomic semantics via write-to-`*.tmp` + `os.replace`. | Following the symlink and writing through it would silently mutate the consumer's symlink target, which is surprising. Unlinking guarantees `book pull`'s output is a plain file the consumer can reason about. |
| D20 | The `agents` directory walker filters: include `*.md`; exclude `README.md` (case-insensitive) and any file starting with `.`. Sub-directories are ignored (non-recursive). | The agents convention across this ecosystem is a flat directory of `<slug>.md` files. `README.md` is a frequent distro-repo file that should never be shipped as an agent; dotfiles (`.gitkeep`, etc.) likewise. The filter is convention-driven; distro authors who need exact control use `files:` (D18). |
| D21 | The CLI command at `cli/commands/book.py` reuses `views.render_table` for default output (one column-spec list per verb) and `dataclasses.asdict` for `--json`. No bespoke rendering inside `artbook` or the command. | Same column / styling language as `artifacts list` and `artifacts events`. Saves ~120 lines of styling code and stays in lockstep with future view-layer improvements. `--json` keeps a clean separation: dataclasses are the source of truth, no Rich on the JSON path. |
| D22 | Introduce a base class `core.models.ItemMeta` — the minimal contract for "a record that can be rendered as a table row" — with a single overridable method `cell(key, default="")`. `ArtifactMeta` becomes `ArtifactMeta(ItemMeta)` and overrides `cell` to read from `frontmatter`. `views.render_table` is generalised from `Sequence[ArtifactMeta]` to `Sequence[ItemMeta]` and from `kind_def: KindDef \| None` to an explicit `status_colors: Mapping[str, str] \| None`. The existing artifact-flavoured call site at `cli/commands/list.py` is one line longer: it passes `status_colors=kind_def.meta.get("status_colors", {})`. | A named base class is cleaner than `Mapping[str, Any]`: explicit contract, dataclass-friendly, IDE-discoverable, can grow methods later (e.g. `format_hint`, `sort_key`) without breaking call sites. Matches the codebase's dataclass-based model style (CLAUDE.md `## Coding Style`). New renderable types (e.g. `BookRow`, `WriteActionRow` in the artbook CLI command) inherit from `ItemMeta` and rely on the default `cell` (attribute lookup) — no `frontmatter` plumbing required for non-artifact data. |

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
`agents` handler (§7.3) walks `<clone_root>/<book.path>` regardless
of how deep that path is.

### 3.2 Schema

Minimal — the directory-is-the-book mode (`files:` omitted):

```yaml
# artbook.yaml — distro manifest

version: 1                          # required — locks D17

distro:
  name: artifacts-os-defaults                       # required
  description: Default agents for artifacts-os consumers.  # optional

books:
  - name: agents                    # required — stable identity
    type: agents                    # required — dispatch token
    path: agents/                   # required — file or folder, distro-relative
    description: Default agent specs.  # optional
```

Explicit — the allowlist mode (`files:` present):

```yaml
version: 1

distro:
  name: artifacts-os-defaults

books:
  - name: agents
    type: agents
    path: openstation/agents/        # dogfood pattern from §3.1 Layout B
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

### 3.3 Field semantics

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `version` | yes | int | Manifest schema version. Must be `1` in this spec. Any other value → exit 1 with `error: this artifacts-os version speaks artbook manifest v1; distro declares v<N>`. |
| `distro.name` | yes | str | Identity for human-readable output. No validation beyond non-empty. |
| `distro.description` | no | str | Free-form. Printed by `book list` if present. |
| `books` | yes | list | At least one book. Empty list → exit 1 `manifest has no books`. |
| `books[].name` | yes | str | Stable identity. Used as `<name>` argument for `book show / pull`. Must be unique within the manifest (duplicate → exit 1). |
| `books[].type` | yes | str | Dispatch token. MVP recognises `agents`. Unknown → exit 1 `unknown book type '<x>'`. |
| `books[].path` | yes | str | Distro-relative path. Trailing `/` indicates a directory; no trailing `/` indicates a single file. May be any depth (`agents/`, `openstation/agents/`, `src/foo/bar/agents/`). Path must resolve inside the clone (no `..` segments, no absolute paths — exit 1 on either). |
| `books[].description` | no | str | Free-form. Printed by `book show`. |
| `books[].files` | no | list[str] | Explicit allowlist of file names under `book.path/` (D18). When present, the handler ships **only** these files. Each must exist under the path; a missing file is exit 1. When **absent**, the handler walks `book.path/` and applies the convention filter from D20 (`*.md` minus `README.md` minus dotfiles). Filenames are relative to `book.path`; no slashes (sub-directories rejected — D20 / Q4). |

### 3.4 Example with the future in mind (informational)

Future book types are out of scope here, but the schema is
designed to accommodate them by adding new `type` values and
their handlers. Example of how a multi-book distro would look
in a later spec:

```yaml
version: 1

distro:
  name: artifacts-os-defaults

books:
  - name: agents
    type: agents
    path: agents/

  - name: kinds
    type: kinds       # not in MVP
    path: kinds/

  - name: skills
    type: skills      # not in MVP
    path: skills/
```

The MVP rejects everything except `type: agents`. The schema
above is illustrative only.

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
    type: str                                # "agents" in MVP; future values dispatched in placement
    path: str                                # distro-relative; trailing "/" → directory
    description: str | None = None
    files: tuple[str, ...] | None = None     # explicit allowlist (D18); None → directory walk + D20 filter

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
| `destination_for` | `(book: Book, vault_root: Path) -> Path` | The placement directory for `book` under `vault_root`. Raises `UnknownBookTypeError` for unrecognised types. |
| `ArtbookError` | exception | Base class. |
| `ManifestError` | exception | Parse / validation failure (includes `version != 1`, missing required field, duplicate book name, `files` entry not found, sub-path in `files`). |
| `FetchError` | exception | git clone failure. |
| `UnknownBookError` | exception | `book.name` not in manifest. |
| `UnknownBookTypeError` | exception | `book.type` has no placement handler. |
| `DistroNotConfiguredError` | exception | `artifacts.yaml :: artbook.distro_url` missing or empty. |

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
├── ManifestError                     (YAML parse, missing key, version != 1, validation)
├── FetchError                        (git clone failed)
├── UnknownBookError                  (name not in manifest)
├── UnknownBookTypeError              (type not in placement table)
└── DistroNotConfiguredError          (artbook.distro_url missing)
```

All inherit from `ArtbookError`. The CLI maps each to an exit
code per §5.5.

## 5. CLI Surface (Scope Item 3)

### 5.1 Synopsis

```
artifacts book list                [--json]
artifacts book show <name>         [--json]
artifacts book pull <name>         [--json] [--dry-run]
```

The `book` keyword introduces a resource namespace; the three
verbs operate on that namespace. This is a conscious exception
to CLAUDE.md's "flat verbs" rule, justified in D10.

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
    type: str       # FieldSpec key matches attribute name
    path: str
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
                type=b.type,
                path=b.path,
                description=b.description or "",
            )
            for b in manifest.books
        ]
        columns = [
            FieldSpec(key="name", label="Name"),
            FieldSpec(key="type", label="Type"),
            FieldSpec(key="path", label="Path"),
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

### 5.2 `artifacts book list`

Reads `artbook.distro_url` from `artifacts.yaml`, clones the
distro, parses `artbook.yaml`, prints one row per book.

**Default Rich-table output:**

```
Distro: artifacts-os-defaults — Default agents for artifacts-os consumers.
URL:    https://github.com/example/artbook-defaults @ a1b2c3d

Name    Type    Path     Description
agents  agents  agents/  Default agent specs.

1 book.
```

**`--json` output (one JSON object):**

```json
{
  "distro": {
    "name": "artifacts-os-defaults",
    "description": "Default agents for artifacts-os consumers.",
    "url": "https://github.com/example/artbook-defaults",
    "sha": "a1b2c3d"
  },
  "books": [
    {
      "name": "agents",
      "type": "agents",
      "path": "agents/",
      "description": "Default agent specs."
    }
  ]
}
```

### 5.3 `artifacts book show <name>`

Reads `artbook.distro_url`, clones the distro, parses the
manifest, resolves the book by name, and renders its details.

For a book of `type: agents`, the output additionally lists the
agents the consumer would receive on `pull`:

- If the book declares `files: [...]` (D18), those are the
  contents.
- Otherwise the handler walks `book.path/` and applies the D20
  convention filter (`*.md` minus `README.md` minus dotfiles).

**Default Rich-table output:**

```
Book:        agents
Type:        agents
Path:        agents/
Description: Default agent specs.

Distro:      artifacts-os-defaults
URL:         https://github.com/example/artbook-defaults @ a1b2c3d

Destination: .claude/agents/

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

**`--json` output:**

```json
{
  "book": {
    "name": "agents",
    "type": "agents",
    "path": "agents/",
    "description": "Default agent specs."
  },
  "distro": {
    "name": "artifacts-os-defaults",
    "url": "https://github.com/example/artbook-defaults",
    "sha": "a1b2c3d"
  },
  "destination": ".claude/agents/",
  "contents": [
    "architect.md", "author.md", "developer.md", "devrel.md",
    "product-manager.md", "project-manager.md", "researcher.md",
    "security-engineer.md", "technical-writer.md"
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

### 5.5 Exit codes

| Code | Condition |
|------|-----------|
| 0 | Success. |
| 1 | Runtime error: clone failed, manifest parse / validation failed, unknown book name, unknown book type, write failed. The error message identifies which. |
| 2 | Usage error: bad flag, missing required positional, `--dry-run` on a non-`pull` verb. |
| 3 | Vault not initialised (`artifacts.yaml` not found by `find_vault_root`). |
| 4 | `artbook.distro_url` missing or empty in `artifacts.yaml`. |

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

error: unknown book type 'kinds' for book 'kinds'
       This artifacts-os version supports: agents.

error: git clone failed (exit 128)
       URL: https://github.com/example/artbook-defaults
       stderr: fatal: Authentication failed for ...
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
└── <book.path>/...        # only the cloned content; nothing else
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
  `files` entry not present under `book.path`) → raise
  `ManifestError` with the offending location.
- **Unknown book name** at `find_book` → raise `UnknownBookError`.
- **Unknown book type** at `destination_for` → raise
  `UnknownBookTypeError`.

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

### 7.1 Book-type → destination table

| Book type | Destination (relative to vault root) | Created if missing? |
|-----------|--------------------------------------|---------------------|
| `agents`  | `.claude/agents/`                    | yes (`os.makedirs(exist_ok=True)`) |

The placement table is hardcoded in
`src/artifacts_os/artbook/placement.py`:

```python
_PLACEMENT: dict[str, str] = {
    "agents": ".claude/agents",
}

def destination_for(book: Book, vault_root: Path) -> Path:
    try:
        rel = _PLACEMENT[book.type]
    except KeyError as exc:
        raise UnknownBookTypeError(book.type) from exc
    return vault_root / rel
```

### 7.2 Why `.claude/agents/` for the `agents` book

- `.claude/agents/` is the directory Claude Code reads agent
  specs from. Every project that uses Claude Code has it.
- It is independent of OpenStation. A consumer using only
  Claude Code (no OpenStation) gets a working result.
- Existing projects that maintain agents elsewhere (this repo
  ships agents at `openstation/agents/` and symlinks
  `.claude/agents → .openstation/agents`) are unaffected — the
  MVP is for fresh consumers; dogfood migration is out of
  scope.

### 7.2.1 The MVP does not solve replication (D8)

artifacts-os ecosystems often replicate the same agent files
across `.claude/agents/`, `.openstation/agents/`,
`artifacts/agents/`, and sometimes `src/.../templates/agents/`
(this repo does). **The MVP does not address this.** It writes
to **one** destination and leaves cross-replica consistency to
the consumer.

This is a deliberate scope cut, mirrored on both sides:

- **Distro side**: a distro repo that has agents in multiple
  places chooses **one** as the source via `artbook.yaml ::
  books[].path`. Whichever path the manifest names is the
  canonical replica for consumers; the others are ignored by
  `book pull`.
- **Consumer side**: `book pull` writes to one place
  (`.claude/agents/` for the agents book). If the consumer
  wants the same content at `.openstation/agents/` or
  `artifacts/agents/`, they wire it themselves (symlink, second
  copy, etc.) — outside the MVP.

A future `book sync` / multi-destination spec can extend
`_PLACEMENT[type]` from `str` to `list[str]` and emit a write per
destination. The MVP keeps the value a `str` to avoid premature
generality.

### 7.3 Copy rules for the `agents` book type

The `agents` handler expects `book.path` to resolve to a
directory in the clone. It selects the files to ship per D18 / D20
and writes each one through the unlink-then-write atomic write
sequence per D19:

```python
_EXCLUDE_NAMES = {"readme.md"}     # case-insensitive (D20)

def _select_files(src_dir: Path, book: Book) -> list[Path]:
    """Return the source files to ship, per D18 (allowlist) or D20 (walker)."""
    if book.files is not None:
        # D18 — explicit allowlist; every name must exist as a file under src_dir.
        out = []
        for name in book.files:
            if "/" in name or "\\" in name:
                raise ManifestError(
                    f"book '{book.name}' files entry '{name}' contains a path separator; "
                    "files entries are flat filenames relative to book.path."
                )
            candidate = src_dir / name
            if not candidate.is_file():
                raise ManifestError(
                    f"book '{book.name}' files entry '{name}' not found at {candidate}"
                )
            out.append(candidate)
        return out
    # D20 — walker: *.md, exclude README.md (case-insensitive) and dotfiles, non-recursive.
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
        out.append(src_file)
    return out


def _copy_agents(clone_root: Path, book: Book, dest: Path) -> Iterable[WrittenFile]:
    src_dir = clone_root / book.path
    if not src_dir.is_dir():
        raise ManifestError(
            f"book '{book.name}' path '{book.path}' is not a directory in the distro"
        )
    dest.mkdir(parents=True, exist_ok=True)
    for src_file in _select_files(src_dir, book):
        dest_file = dest / src_file.name
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
  convention filter.
- Non-`.md` files in the agents directory are silently skipped
  by the walker; the allowlist mode ignores file extensions
  (a distro author who insists on `.markdown` files can list
  them).
- Sub-directories of the agents directory are **not** recursed
  by the walker. Allowlist entries cannot contain `/` (D20 /
  Q4). MVP agents are a flat directory of `<slug>.md` files.
- The write is `shutil.copyfile` (content only) — no permission
  preservation, no exec bits, no extended attributes. Agent
  files are plain markdown.
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

Name    Type    Path     Description
agents  agents  agents/  Default agent specs.

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
Type:        agents
Path:        agents/
Description: Default agent specs.

Distro:      artifacts-os-defaults
URL:         https://github.com/example/artbook-defaults @ a1b2c3d

Destination: .claude/agents/

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
`Destination` is rendered via `destination_for(book, vault_root)`.

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
- Additional book types (`kinds`, `skills`, `commands`,
  `hooks`) — each adds a placement entry plus a copy handler.
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
| New book types | Extend `_PLACEMENT` and add a `_copy_<type>` function. |
| Per-type copy strategies | Replace `_copy_agents` with a strategy lookup keyed on `book.type`. |
| Pull-time diff | `_copy_agents` already yields `WrittenFile(overwritten=..., was_symlink=...)`; a future diff step inspects this stream. |
| Lock file | `PullReport.distro_sha` and `WrittenFile` records are already structured for persistence. |
| Caching | The `read_manifest → pull_book` split (§4.4) accepts an already-populated `clone_root`; a cache layer would supply that root instead of cloning fresh. |
| Multi-distro | `PullReport.distro_url` already in the report; adding a list of `(url, manifest)` is mechanical. |
| Multi-destination per type | `_PLACEMENT[type]` is `str` today; widen to `list[str]` and emit one write per destination. `WrittenFile` already carries the destination, so the report layer is unchanged. |
| Schema migrations | `Manifest.version` and the v1 check in `read_manifest` give the version gate. v2 lands as a parallel parser keyed on the `version` field. |
| Manifest format change | `manifest.py` isolates `yaml.safe_load`; swapping for another parser touches one module. |
| New tabular output (any verb, any future kind) | `views.render_table` accepts any `Sequence[ItemMeta]` after the D22 refactor. New renderable types inherit from `ItemMeta` and (in 99% of cases) rely on the default attribute-lookup `cell` — no `frontmatter` plumbing required. No copy-paste of Rich styling. |

No code in the MVP commits to a contradiction with any of the
above — the goal is "easy to extend", not "hard to remove".

## 11. Verification Mapping

This spec addresses every t0151 verification item:

- [x] Spec written and committed under `openstation/specs/`
      (this file).
- [x] All six scope items addressed:
      1. `artbook.yaml` schema → §3.
      2. `artbook` module layout → §4.
      3. CLI surface → §5.
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
