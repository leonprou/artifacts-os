# artifacts-os Design

**Date:** 2026-04-20  
**Status:** approved  
**Author:** Leon Prouger

---

## Overview

Extract OpenStation's artifact storage layer into a standalone Python
package called `artifacts-os`. The package owns kind definitions,
frontmatter parsing, ID generation, file creation, discovery, and
resolution. OpenStation depends on it as a local editable install and
extends it with display and operational metadata.

**Goals:**
- **Reuse** — other projects can use the same artifact primitives
- **Separation of concerns** — storage layer is independently testable
- **Extensibility** — vault owners add custom kinds by dropping a JSON
  schema file; no code required

---

## Repository Layout

`artifacts-os` lives as a sibling directory to `open-station`:

```
~/workspace/
  open-station/      # existing repo
  artifacts-os/      # new package
```

OpenStation declares the dependency in `pyproject.toml`:

```toml
dependencies = [
    "artifacts-os",
    ...
]
```

Local development uses an editable install:

```bash
pip install -e ../artifacts-os
```

---

## Package Layout

```
artifacts-os/
  src/
    artifacts_os/
      __init__.py          # public API re-exports
      models.py            # KindDef, ArtifactMeta, Artifact
      errors.py            # ArtifactError, NotFoundError, AmbiguousError, ValidationError
      frontmatter.py       # parse/dump via python-frontmatter
      registry.py          # Registry class — merges caller kinds + vault kinds/
      ids.py               # next_prefixed_id, slugify, validate_slug
      store.py             # create, get, update (atomic writes)
      discover.py          # list_artifacts, resolve, search
      vault.py             # find_vault_root (marker-based)
  pyproject.toml
  tests/
```

`artifacts-os` ships **no built-in kind schemas**. It is kind-agnostic.
Callers (e.g. OpenStation) define their own kinds as `KindDef` objects
in code and pass them to the `Registry`. Vault owners extend with
custom JSON schemas dropped in `artifacts/kinds/`.

---

## Vault Structure

`artifacts-os` is opinionated about layout. The vault marker is
`artifacts/artifacts.yaml` at the project root; `find_vault_root` walks up
the directory tree until it finds it.

```
<project>/
  artifacts/
    artifacts.yaml       # vault marker
    tasks/               # NNNN-slug.md  (prefix: t)
    specs/               # NNNN-slug.md  (prefix: s)
    research/            # NNNN-slug.md  (prefix: r)
    notes/               # NNNN-slug.md  (prefix: n)
    alerts/              # NNNN-slug.md  (prefix: a)
    agents/              # slug.md       (no prefix, no number)
    kinds/               # user-defined kind schemas (*.json)
```

---

## Kind Definitions

### Code-defined (primary)

Callers define kinds as `KindDef` objects directly in Python and pass
them to `Registry`. This is how OpenStation registers its built-in
kinds (task, spec, research, note, alert, agent) — no JSON files
required.

```python
from artifacts_os import Registry, KindDef

registry = Registry([
    KindDef(name="task",     dir="tasks",    prefix="t", numbered=True,
            statuses=["backlog", "ready", "in-progress", "review",
                      "verified", "done", "failed", "rejected"]),
    KindDef(name="agent",    dir="agents",   prefix="",  numbered=False,
            statuses=[]),
    KindDef(name="research", dir="research", prefix="r", numbered=True,
            statuses=[]),
    # ...
], root=root)  # root triggers vault kinds/ scan on top
```

### Vault-defined (extensibility)

Vault owners add custom kinds by dropping a JSON Schema file in
`artifacts/kinds/`. The `Registry` merges these on top of the
caller-provided kinds when `root` is given. Vault schemas can also
override a caller-provided kind by using the same `name`.

JSON schemas use `x-` extension fields to control storage behaviour:

| Extension field | Type | Meaning |
|---|---|---|
| `x-prefix` | string | ID prefix (`"c"` → `c0001`); empty = no prefix |
| `x-numbered` | bool | `true` = `NNNN-slug.md`; `false` = `slug.md` |
| `x-dir` | string | Subdirectory under `artifacts/` |

**Statuses** are extracted from `properties.status.enum` at load time.
Kinds with no `status` property have `statuses: []`.

---

## Extensibility — Custom Kinds

Vault owners add a kind by dropping a JSON schema file in
`artifacts/kinds/`. No Python required.

**Example — `artifacts/kinds/changelog.json`:**

```json
{
  "x-prefix": "c",
  "x-numbered": true,
  "x-dir": "changelogs",
  "type": "object",
  "required": ["kind", "name"],
  "properties": {
    "kind":    { "const": "changelog" },
    "name":    { "type": "string" },
    "version": { "type": "string" }
  },
  "additionalProperties": true
}
```

`Registry` merges vault-defined kinds on top of the caller-provided
kinds. A vault schema with the same name as a caller-provided kind
overrides it entirely — enabling full customisation without forking.

---

## Data Models

```python
@dataclass
class KindDef:
    name: str            # "task"
    dir: str             # "tasks"
    prefix: str          # "t" (empty string for agents)
    numbered: bool       # True = NNNN-slug, False = slug-only
    statuses: list[str]  # [] if kind has no status concept
    schema: dict         # full JSON Schema dict
    meta: dict           # caller-defined extras; library never reads this

@dataclass
class ArtifactMeta:
    """Lightweight metadata from frontmatter only. Used for listing."""
    id: str              # "t0042" or "researcher" (agents)
    kind: str            # "task"
    name: str            # slug: "fix-the-bug"
    title: str           # human-readable title
    status: str | None
    tags: list[str]
    created: str         # ISO date string
    path: Path
    frontmatter: dict    # all raw frontmatter fields

@dataclass
class Artifact(ArtifactMeta):
    """Full artifact including body. Used for get/create/update."""
    body: str
```

The `meta: dict` slot on `KindDef` is where OpenStation attaches
`default_columns`, `renderer`, `filterable_by`, and custom `discover`.
The library never reads `meta`.

---

## Error Hierarchy

Exceptions replace the current `(path, error_msg, exit_code)` tuple
returns throughout OpenStation. The CLI layer catches them and maps to
exit codes.

```python
class ArtifactError(Exception):    # base; exit code 1
class NotFoundError(ArtifactError): pass   # exit code 3
class AmbiguousError(ArtifactError): pass  # exit code 4
class ValidationError(ArtifactError): pass # exit code 2
```

---

## Public API

```python
from artifacts_os import (
    # Vault
    find_vault_root,     # (start: Path) -> Path

    # Registry
    Registry,            # Registry(kinds: list[KindDef], root: Path | None = None)
                         #   .get(kind: str) -> KindDef
                         #   .all() -> list[KindDef]

    # CRUD
    create,              # (registry, kind, title, *, body="", fields={}) -> Artifact
    get,                 # (registry, ref, *, kind=None) -> Artifact
    list_artifacts,      # (registry, *, kind=None, status=None, tag=None) -> list[ArtifactMeta]
    update,              # (registry, ref, *, status=None, fields={}) -> Artifact
    search,              # (registry, query, *, kind=None) -> list[ArtifactMeta]
    resolve,             # (registry, query, *, kind=None) -> Path

    # Models
    Artifact, ArtifactMeta, KindDef,

    # Errors
    ArtifactError, NotFoundError, AmbiguousError, ValidationError,
)
```

`Registry(kinds, root=root)` — builds from caller-provided `KindDef`
objects, then scans `root/artifacts/kinds/*.json` and merges any
vault-defined kinds on top. Pass `root=None` to skip vault scanning.

`resolve` accepts prefixed IDs (`t42`, `t0042`), full stems
(`0042-fix-the-bug`), agent names (`researcher`), and partial slug
matches. Returns `Path` on success; raises `NotFoundError` or
`AmbiguousError` on failure.

---

## OpenStation Integration

### registry.py

```python
from dataclasses import replace
from artifacts_os import load_registry

_DISPLAY: dict[str, dict] = {
    "task": {
        "default_columns": ["id", "status", "assignee", "owner", "name"],
        "renderer": "task",
        "filterable_by": ["status", "assignee", "type", "owner"],
        "discover": discover_tasks,
    },
    "research": {
        "default_columns": ["id", "name", "summary"],
        "renderer": "artifact",
        "filterable_by": ["type"],
    },
    # ... other kinds
}

def build_registry(root: Path) -> dict:
    base = load_registry(root)
    return {
        name: replace(kd, meta=_DISPLAY.get(name, {}))
        for name, kd in base.items()
    }
```

### artifacts.py / tasks.py

Discovery, resolution, and creation logic delegates to `artifacts_os`:

```python
from artifacts_os import list_artifacts, resolve, create

# Before (OpenStation)
artifacts = discover_artifacts(root, kind=kind)
path, err, code = resolve_artifact(root, query)

# After
artifacts = list_artifacts(root, kind=kind)
path = resolve(root, query, kind=kind)   # raises on failure
```

### CLI error handling

```python
try:
    path = resolve(root, query)
except NotFoundError as e:
    core.err(str(e))
    return core.EXIT_NOT_FOUND
except AmbiguousError as e:
    core.err(str(e))
    return core.EXIT_AMBIGUOUS
```

---

## Dependencies

`artifacts-os` dependencies are minimal:

```toml
dependencies = [
    "python-frontmatter>=1.1",
    "jsonschema>=4.23",
]
```

`python-frontmatter` replaces OpenStation's hand-rolled YAML parser.
`jsonschema` validates frontmatter against kind schemas on create/update.

Git auto-commit (from the PoC) is **not included** — OpenStation manages
its own git operations.

---

## What Moves vs What Stays

### Moves to `artifacts-os`

| Current location | Destination |
|---|---|
| `core.parse_frontmatter`, `extract_body`, `parse_multiline_value` | `artifacts_os.frontmatter` |
| `core.next_prefixed_id` | `artifacts_os.ids` |
| `registry.ArtifactKind` | `artifacts_os.models.KindDef` |
| `artifacts.create_artifact_file` | `artifacts_os.store` |
| `artifacts.discover_artifacts` | `artifacts_os.discover` |
| `artifacts.resolve_artifact`, `resolve_artifact_for_kind` | `artifacts_os.discover` |
| `registry.resolve_any` | `artifacts_os.discover` |

### Stays in OpenStation

| Module | Reason |
|---|---|
| `registry.py` | OpenStation-specific `REGISTRY` + display metadata |
| `cli.py` | CLI parsing, argument handling, exit codes |
| `ui.py` | Rich rendering, table formatters, status colouring |
| `tasks.py` | Lifecycle transitions, task-specific discovery |
| `alerts.py` | Alert-specific discovery and scheduling logic |
| `sessions.py`, `hooks.py`, `run.py` | Agent execution, no artifact storage concern |
| `core.py` (exit codes, lifecycle) | OpenStation domain constants |
