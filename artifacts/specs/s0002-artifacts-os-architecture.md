---
kind: spec
name: artifacts-os-architecture
status: final
created: 2026-04-20
task: "[[0001-migrate-docs-specs-to-openstation]]"
agent: manual
id: s0002
---

# artifacts-os Architecture Spec

Concrete implementation architecture for the `artifacts-os` Python package.
Supersedes the design sketch in `docs/plans/2026-04-20-artifacts-os-design.md`
where they conflict — treat this file as the authoritative implementation
reference.

---

## Decisions Log

| # | Question | Decision |
|---|----------|----------|
| 1 | Vault discovery | Pure walk-up — no git dependency |
| 2 | `KindDef.numbered` vs `KindDef.prefix` | Keep both explicit |
| 3 | `update` scope | Frontmatter only; merge semantics |
| 4 | `list_artifacts` / `resolve` / `search` | All three in public API; grep-based |
| 5 | Wikilink stripping | Caller's concern — library returns raw strings |
| 6 | `ArtifactMeta.id` source | Frontmatter `id:` field (written by `create`) |

---

## Repository Layout

```
~/workspace/
  open-station/      # existing repo
  artifacts-os/      # new package (sibling directory)
    src/
      artifacts_os/
        __init__.py
        models.py
        errors.py
        frontmatter.py
        registry.py
        ids.py
        store.py
        discover.py
        vault.py
    tests/
    pyproject.toml
```

---

## `pyproject.toml`

```toml
[project]
name = "artifacts-os"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "python-frontmatter>=1.1",
    "jsonschema>=4.23",
]

[project.optional-dependencies]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

OpenStation local install:

```bash
pip install -e ../artifacts-os
```

OpenStation `pyproject.toml` dependency entry:

```toml
dependencies = [
    "artifacts-os",
    ...
]
```

---

## Module Contracts

### `vault.py`

```python
def find_vault_root(start: Path | None = None) -> Path | None:
    """Walk up from start (default: CWD) looking for a directory
    that contains .openstation/. Returns the first match or None."""
```

Implementation: iterate `start, start.parent, start.parent.parent, …`
until `(candidate / ".openstation").is_dir()` or we hit the filesystem
root. No git calls.

---

### `errors.py`

```python
class ArtifactError(Exception): pass      # base; CLI maps to exit code 1
class NotFoundError(ArtifactError): pass  # exit code 3
class AmbiguousError(ArtifactError): pass # exit code 4
class ValidationError(ArtifactError): pass # exit code 2 (schema / status)
```

`AmbiguousError` messages include the list of candidate paths so callers
can surface them directly.

---

### `models.py`

```python
@dataclass
class KindDef:
    name: str         # "task"
    dir: str          # "tasks" — subdirectory under artifacts/
    prefix: str       # "t"; empty string for kinds with no prefix (agents)
    numbered: bool    # True → NNNN-slug.md; False → slug.md
    statuses: list[str]  # [] when kind has no status concept
    schema: dict      # full JSON Schema dict; {} skips validation
    meta: dict        # caller-defined extras; library never reads this


@dataclass
class ArtifactMeta:
    """Lightweight view populated from frontmatter only (no body read)."""
    id: str           # from frontmatter `id:` field
    kind: str         # from frontmatter `kind:` field
    name: str         # from frontmatter `name:` field (slug)
    title: str        # first H1 from body; falls back to name
    status: str | None
    tags: list[str]
    created: str      # ISO date string or "" if absent
    path: Path
    frontmatter: dict # raw PyYAML-parsed frontmatter (all fields)


@dataclass
class Artifact(ArtifactMeta):
    """Full artifact including body text."""
    body: str
```

**`title` derivation:** `create` and `get` scan the body for the first
line matching `^#\s+(.+)` and use that as `title`. If no H1 is present,
`title = name`. This is the only place the body is read for `ArtifactMeta`
construction; `list_artifacts` and `search` do not read bodies (they set
`title = name` for performance).

---

### `frontmatter.py`

```python
def parse(text: str) -> tuple[dict, str]:
    """Parse a markdown file into (frontmatter_dict, body_str).
    Uses python-frontmatter. Body is the text after the closing ---.
    Returns ({}, text) if no frontmatter block is present."""

def dump(meta: dict, body: str) -> str:
    """Serialize (frontmatter_dict, body) back to a markdown string.
    Uses python-frontmatter (PyYAML under the hood).
    Keys are written in insertion order."""
```

`parse` returns raw PyYAML output — lists are Python lists, strings are
strings. Wikilink strings (e.g. `"[[0042-fix-bug]]"`) remain as-is.
Callers strip them if needed.

---

### `ids.py`

```python
def next_prefixed_id(directory: Path, prefix: str) -> str:
    """Scan directory for .md files matching ^{prefix}(\d+)-, return
    "{prefix}{max+1:04d}". Returns "{prefix}0001" when no matches exist.
    Files not starting with prefix are ignored."""

def slugify(text: str, max_words: int = 5) -> str:
    """Lowercase, replace non-[a-z0-9] runs with hyphens, take first
    max_words hyphen-separated tokens, strip leading/trailing hyphens."""

def validate_slug(slug: str) -> bool:
    """Return True iff slug matches ^[a-z0-9]+(-[a-z0-9]+)*$."""
```

---

### `registry.py`

```python
class Registry:
    def __init__(
        self,
        kinds: list[KindDef],
        root: Path | None = None,
    ) -> None:
        """Build registry from caller-provided KindDef list.
        If root is given, scan root/artifacts/types/*.json and merge
        vault-defined kinds on top (same name → caller kind is replaced).
        root is stored and used by store/discover functions."""

    @property
    def root(self) -> Path | None: ...

    def get(self, kind: str) -> KindDef:
        """Raise ValueError if kind is unknown."""

    def all(self) -> list[KindDef]:
        """Return all registered KindDef objects."""

    def for_dir(self, dir_name: str) -> KindDef | None:
        """Look up a KindDef by its directory name. Returns None if not found."""
```

**Vault-defined kind loading** (`root` given):

1. Glob `root/artifacts/types/*.json`.
2. For each JSON file, read and parse as JSON Schema.
3. Extract storage fields:
   - `x-prefix` → `prefix` (default `""`)
   - `x-numbered` → `numbered` (default `True`)
   - `x-dir` → `dir` (required; raise `ValidationError` if absent)
   - Filename stem → `name`
   - `properties.status.enum` → `statuses` (default `[]`)
4. Build `KindDef(schema=full_json, meta={})`.
5. Merge into the caller-provided kinds map (last write wins on name
   collision — vault overrides caller).

If `root` is `None`, no scanning occurs. All file I/O functions
(`create`, `get`, `update`, `list_artifacts`, `resolve`, `search`)
require `registry.root` to be set; they raise `RuntimeError` if it is
`None`.

---

### `store.py`

#### `create`

```python
def create(
    registry: Registry,
    kind: str,
    title: str,
    *,
    body: str = "",
    fields: dict = {},
) -> Artifact:
```

Steps:

1. `kd = registry.get(kind)` — raises `ValueError` on unknown kind.
2. `slug = slugify(title)` — raise `ValidationError` if empty.
3. Determine `id` and filename:
   - `numbered=True`: `id = next_prefixed_id(subdir, kd.prefix)` →
     filename `{id}-{slug}.md`; retry up to 5× on `EEXIST`.
   - `numbered=False`: `id = slug` → filename `{slug}.md`; raise
     `FileExistsError` on collision (no retry).
4. Build frontmatter dict: `{"kind": kind, "id": id, "name": name,
   **fields}` where `name = id` for numbered kinds (e.g. `"t0042"`) is
   **wrong** — see note below.
5. Validate frontmatter against `kd.schema` using `jsonschema.validate`.
   Skip validation when `kd.schema == {}`.
6. Serialise with `frontmatter.dump` and write atomically:
   `O_CREAT | O_EXCL | O_WRONLY`.
7. Parse and return `Artifact`.

**`name` field clarification:** For numbered kinds the `name` frontmatter
field is `"{id}-{slug}"` (e.g. `"t0042-fix-the-bug"`), matching the
filename stem. For non-numbered kinds `name = slug` (e.g. `"researcher"`).
This matches OpenStation's existing convention.

#### `get`

```python
def get(
    registry: Registry,
    ref: str,
    *,
    kind: str | None = None,
) -> Artifact:
```

Calls `resolve(registry, ref, kind=kind)` → `path`. Reads file, calls
`frontmatter.parse`, builds and returns `Artifact` (including body).
Derives `title` from first H1 in body.

#### `update`

```python
def update(
    registry: Registry,
    ref: str,
    *,
    status: str | None = None,
    fields: dict = {},
) -> Artifact:
```

Steps:

1. `path = resolve(registry, ref)`.
2. Read and parse file.
3. Determine `kind` from frontmatter, look up `kd`.
4. If `status` is given and `kd.statuses` is non-empty, validate that
   `status in kd.statuses`; raise `ValidationError` otherwise.
5. Merge: `new_fm = {**existing_fm, **fields}`. If `status` given,
   `new_fm["status"] = status`.
6. Validate merged frontmatter against `kd.schema` (skip if `{}`).
7. Write atomically: serialise with `frontmatter.dump`, write to
   `{path}.tmp`, then `os.replace(tmp, path)` (POSIX atomic rename).
8. Parse and return updated `Artifact`.

`update` is frontmatter-only. Body is preserved verbatim — read in step 2,
written back unchanged in step 7.

---

### `discover.py`

All three functions scan the filesystem. No index. For `list_artifacts`
and `search`, frontmatter is read but body is not (performance). `title`
is set to `name` for these functions.

#### `list_artifacts`

```python
def list_artifacts(
    registry: Registry,
    *,
    kind: str | None = None,
    status: str | None = None,
    tag: str | None = None,
) -> list[ArtifactMeta]:
```

- If `kind` given, scan only `registry.root/artifacts/{kd.dir}/`.
- If `kind=None`, scan all registered kind directories.
- For each `.md` file: parse frontmatter, apply filters.
- `status` filter: `fm.get("status") == status`.
- `tag` filter: `tag in fm.get("tags", [])`.
- Returns sorted by `path`.

#### `resolve`

```python
def resolve(
    registry: Registry,
    query: str,
    *,
    kind: str | None = None,
) -> Path:
```

Match strategies applied in order across the target directory/directories.
First strategy that produces exactly one match wins. Strategies:

1. **Exact stem:** `{dir}/{query}.md` exists.
2. **Prefixed short/full ID:** query matches `^([a-z]+)(\d+)$` →
   expand to `{letters}{digits:04d}` → find files with stem starting
   `{expanded}-` or stem `== expanded`.
3. **Old-style numeric:** query is all digits → `{query.zfill(4)}-*` or
   `{kind_prefix}{query.zfill(4)}-*`.
4. **Partial stem:** `query in stem` for all files in directory.

After all strategies, if total matches = 1 → return `Path`.
If 0 → raise `NotFoundError`. If > 1 → check for exact stem winner
among matches; if unique exact → return it; otherwise raise
`AmbiguousError` with candidate list.

When `kind=None`, iterate all registered kind directories; first
directory that yields a single unambiguous match wins.

#### `search`

```python
def search(
    registry: Registry,
    query: str,
    *,
    kind: str | None = None,
) -> list[ArtifactMeta]:
```

Same match strategies as `resolve`, but returns all matches as
`list[ArtifactMeta]` instead of raising on ambiguity. Returns `[]`
if no matches. Does not raise `NotFoundError` or `AmbiguousError`.

---

## Public API (`__init__.py`)

```python
from artifacts_os.vault import find_vault_root
from artifacts_os.registry import Registry
from artifacts_os.store import create, get, update
from artifacts_os.discover import list_artifacts, resolve, search
from artifacts_os.models import Artifact, ArtifactMeta, KindDef
from artifacts_os.errors import (
    ArtifactError, NotFoundError, AmbiguousError, ValidationError
)

__all__ = [
    "find_vault_root",
    "Registry",
    "create", "get", "update",
    "list_artifacts", "resolve", "search",
    "Artifact", "ArtifactMeta", "KindDef",
    "ArtifactError", "NotFoundError", "AmbiguousError", "ValidationError",
]
```

---

## Test Strategy

- **Framework:** pytest with `tmp_path` fixture.
- **No mocking** — all tests operate on real temp-dir vault structures.
- **Fixture helper** `make_vault(tmp_path, kinds)` creates the
  `.openstation/` marker and `artifacts/{kind.dir}/` directories,
  returns a `Registry`.
- **Coverage targets by module:**

| Module | Key cases |
|--------|-----------|
| `vault.py` | found at CWD, found ancestor, not found |
| `ids.py` | empty dir → 0001, existing files, prefix isolation |
| `frontmatter.py` | round-trip, no frontmatter, PyYAML types |
| `store.create` | numbered, non-numbered, collision retry, schema failure |
| `store.update` | merge, invalid status, body preserved |
| `store.get` | H1 title extraction, no-H1 fallback |
| `discover.list_artifacts` | all kinds, single kind, status filter |
| `discover.resolve` | each match strategy, not-found, ambiguous |
| `discover.search` | multiple matches, zero matches |
| `registry` | vault types/ scan, caller override, vault override |

---

## OpenStation Integration (summary)

OpenStation keeps its own `registry.py` with display metadata. It builds
a `Registry` by passing `KindDef` objects to `artifacts_os.Registry` and
attaches display config in the `meta` dict (which the library never reads).

```python
from artifacts_os import Registry, KindDef

_KINDS = [
    KindDef(name="task", dir="tasks", prefix="t", numbered=True,
            statuses=["backlog","ready","in-progress","review",
                      "verified","done","failed","rejected"],
            schema={}, meta={"renderer": "task", ...}),
    KindDef(name="agent", dir="agents", prefix="", numbered=False,
            statuses=[], schema={}, meta={"renderer": "artifact"}),
    # ...
]

def build_registry(root: Path) -> Registry:
    return Registry(_KINDS, root=root)
```

CLI error handling maps library exceptions to exit codes:

```python
try:
    path = resolve(registry, query)
except NotFoundError as e:
    core.err(str(e)); return core.EXIT_NOT_FOUND
except AmbiguousError as e:
    core.err(str(e)); return core.EXIT_AMBIGUOUS
```

---

## What Does Not Move to `artifacts-os`

| Stays in OpenStation | Reason |
|---|---|
| `registry.py` display metadata | OpenStation-specific columns, renderers |
| `cli.py` | Argument parsing, exit codes |
| `ui.py` | Rich tables, status colouring |
| `tasks.py` lifecycle logic | Transition rules, date field auto-set |
| `alerts.py` discovery | Alert-specific scheduling and connector fields |
| `sessions.py`, `run.py`, `hooks.py` | Agent execution — no artifact storage concern |
| `core.py` exit codes, lifecycle constants | OpenStation domain |
