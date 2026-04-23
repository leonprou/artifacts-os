# `artifacts_os.core`

Storage, discovery, and registry for artifacts-os. This is the
foundational layer; all other modules depend on it.

For architecture details see
`artifacts/specs/s0002-artifacts-os-architecture.md` and
`artifacts/specs/s0005-artifacts-os-module-system.md`.

---

## Public API

```python
from artifacts_os.core import (
    # vault
    find_vault_root,
    # registry
    Registry,
    # CRUD
    create, get, update,
    # discovery
    list_artifacts, resolve, search,
    # models
    Artifact, ArtifactMeta, KindDef,
    # errors
    ArtifactError, NotFoundError, AmbiguousError, ValidationError,
)
```

### Models

| Class | Description |
|---|---|
| `KindDef` | Describes an artifact kind: directory, ID prefix, numbering, allowed statuses, JSON Schema. |
| `ArtifactMeta` | Lightweight view populated from frontmatter only (no body read). |
| `Artifact` | Full artifact — extends `ArtifactMeta` with `body: str`. |

### CRUD (`store.py`)

| Function | Signature | Description |
|---|---|---|
| `create` | `(registry, kind, title, *, body="", fields=None) → Artifact` | Create and atomically write a new artifact file. |
| `get` | `(registry, ref, *, kind=None) → Artifact` | Resolve ref, read file, return full `Artifact`. |
| `update` | `(registry, ref, *, status=None, fields=None) → Artifact` | Merge frontmatter updates; body preserved verbatim. |

### Discovery (`discover.py`)

| Function | Signature | Description |
|---|---|---|
| `list_artifacts` | `(registry, *, kind=None, status=None, tag=None) → list[ArtifactMeta]` | List artifacts, optionally filtered. |
| `resolve` | `(registry, query, *, kind=None) → Path` | Resolve a query to a single `Path`. Raises `NotFoundError` or `AmbiguousError`. |
| `search` | `(registry, query, *, kind=None) → list[ArtifactMeta]` | Like `resolve` but returns all matches without raising. |

`resolve` applies match strategies in priority order: exact stem →
prefixed ID (`t42` → `t0042`) → numeric (`0042-*`) → partial stem.

### Registry (`registry.py`)

`Registry` merges caller-provided `KindDef` objects with vault-defined
kinds loaded from `openstation/types/*.json`.

```python
Registry(kinds: list[KindDef], root: Path | None = None)
```

| Method | Description |
|---|---|
| `get(kind) → KindDef` | Look up a kind by name. Raises `ValueError` if unknown. |
| `all() → list[KindDef]` | All registered kinds. |
| `for_dir(dir_name) → KindDef | None` | Find the kind that owns a given directory. |

### Vault (`vault.py`)

```python
find_vault_root(start: Path | None = None) → Path | None
```

Walks up from `start` (default: `cwd`) until a directory containing
`.openstation/` is found. Returns it, or `None`.

### Errors (`errors.py`)

| Exception | CLI exit | Meaning |
|---|---|---|
| `ArtifactError` | 1 | Base exception. |
| `ValidationError` | 2 | Frontmatter failed schema or status validation. |
| `NotFoundError` | 3 | No artifact matches the query. |
| `AmbiguousError` | 4 | Query matched multiple artifacts. |

---

## Usage Examples

```python
from pathlib import Path
from artifacts_os.core import Registry, KindDef, create, get, update, list_artifacts

# 1. Set up a registry with a custom kind
task_kind = KindDef(
    name="task",
    dir="tasks",
    prefix="t",
    numbered=True,
    statuses=["backlog", "ready", "in-progress", "review", "done"],
)
registry = Registry(kinds=[task_kind], root=Path("/path/to/vault"))

# 2. Create an artifact
artifact = create(registry, "task", "Fix login bug", body="## Details\n…")
print(artifact.id)    # e.g. "t0001"
print(artifact.name)  # e.g. "t0001-fix-login-bug"

# 3. Read it back
loaded = get(registry, "t0001")
print(loaded.body)

# 4. Update frontmatter (body unchanged)
updated = update(registry, "t0001", status="in-progress", fields={"assignee": "alice"})

# 5. List and filter
tasks = list_artifacts(registry, kind="task", status="ready")
for t in tasks:
    print(t.name, t.status)
```

---

## Constraints

**Atomic writes** — `create` uses `O_CREAT | O_EXCL` to claim a new
file, preventing races when multiple processes allocate IDs
concurrently. `update` writes to a `.tmp` sibling then calls
`os.replace` so readers never see a partial file.

**No peer imports** — `core` may not import from `views`, `cli`, `tui`,
`log`, or `ai`. The dependency DAG flows outward from `core` only.

**`update` is frontmatter-only** — the body is always preserved
verbatim; pass `body` to `create`, not `update`.
