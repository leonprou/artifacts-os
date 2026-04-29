# `artifacts_os.core`

Storage, discovery, and registry for artifacts-os. This is the
foundational layer; all other modules depend on it.

For architecture details see specs `s2060-artifacts-os-architecture`
and `s2061-artifacts-os-module-system`, or
[docs/architecture.md](../../../../docs/architecture.md).

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
    # settings
    load_settings, Settings, ProjectConfig, UnsupportedSchemaVersion,
    # models
    Artifact, ArtifactMeta, KindDef,
    # validation
    validate_one, validate_many, ValidationIssue, ValidationResult,
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
| `Settings` | Base settings dataclass parsed from `artifacts.yaml`. Designed for extension by other modules. |
| `ProjectConfig` | Project identity section: `name` (required) and `alias` (optional). |

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
kinds loaded from `artifacts/kinds/*.json`.

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
`artifacts/artifacts.yaml` is found. Returns it, or `None`.

### Errors (`errors.py`)

| Exception | CLI exit | Meaning |
|---|---|---|
| `ArtifactError` | 1 | Base exception. |
| `ValidationError` | 2 | Frontmatter failed schema or status validation. |
| `NotFoundError` | 3 | No artifact matches the query. |
| `AmbiguousError` | 4 | Query matched multiple artifacts. |

### Validation (`validate.py`)

| Function / Class | Description |
|---|---|
| `validate_one(meta, registry) → ValidationResult` | Validate frontmatter of a single `ArtifactMeta`. Pure; no I/O. |
| `validate_many(metas, registry) → list[ValidationResult]` | Validate a list of artifacts; returns one result per artifact. |
| `ValidationIssue` | Single issue: `field`, `message`, `fixable`, `severity` (`"error"` or `"warning"`). |
| `ValidationResult` | Per-artifact result: `name`, `kind`, `issues`. Properties: `.errors`, `.warnings`, `.valid`. |

`validate_one` checks (in order): `kind` present and registered → required fields present → status
in allowed set → ID format → JSON Schema constraints → unknown fields (as warnings). Schema
validation requires `jsonschema`; skipped silently if not installed.

---

### Settings (`settings.py`)

`core` owns the project settings file (`artifacts.yaml` at the vault
root) end-to-end: vault discovery, kinds loading, init-time YAML
writes, and runtime parsing all live in this module.

```python
load_settings(path: Path) -> Settings
```

Reads the YAML file at *path*, validates `layout_version`, builds a
`ProjectConfig` from the required `project` section, and returns a
populated `Settings` whose `raw` field holds the full parsed
document. `core` does not parse, type, or validate sections it does
not own (e.g. `views`, `default_views`, consumer-defined keys) —
those live in `Settings.raw` for extension subclasses to read.

```python
from pathlib import Path
from artifacts_os.core import load_settings

base = load_settings(Path("artifacts/artifacts.yaml"))
base.layout_version    # 1
base.project.name      # "my-project"
base.project.alias     # "mp" or None
base.raw["views"]      # untyped — owned by views module
```

#### `Settings` — base for extension

`Settings` is a `kw_only=True` dataclass intentionally designed as a
**base class** that other modules subclass. Fields: `layout_version: int`,
`project: ProjectConfig`, `raw: dict` (full parsed YAML; default `{}`).
The base contains only what `core` itself reads:

Each module owns one or more top-level keys of `artifacts.yaml`
end-to-end — the dataclass(es) for that section, its parser, and
(eventually) its writer. `core` parses nothing it does not own.

| Module    | Owns top-level key(s)         | Subclass                      |
|-----------|-------------------------------|-------------------------------|
| `core`    | `layout_version`, `project`   | `Settings` (base)             |
| `views`   | `views`, `default_views`      | `ViewsSettings`               |
| consumer  | `<their key(s)>`              | their own `Settings` subclass |

A module subclass adds its own typed fields and a
`from_base(base: Settings) -> Self` parser that reads the relevant
section from `base.raw`. See `views.ViewsSettings` for the
canonical example, and `s0010-core-settings-module-spec` for the
full extension pattern (including how consumers chain or compose
multiple subclasses).

The convention is **structural, not enforced** — `Settings.raw` is
plain data and any caller can read any field. Following the
convention keeps the eventual write API tractable.

#### Schema versioning

The settings file must contain `layout_version: <int>` at the top
level. The current supported version is **1**.

| Condition                    | Behaviour                                                          |
|------------------------------|--------------------------------------------------------------------|
| `layout_version` absent      | Raise `UnsupportedSchemaVersion("missing layout_version")`         |
| `layout_version: 1`          | Proceed normally                                                   |
| `layout_version: N` (N > 1)  | Raise `UnsupportedSchemaVersion(f"unsupported version {N}")`       |

`UnsupportedSchemaVersion` is a `ValueError` subclass exported from
`artifacts_os.core`. Callers catch it and surface a user-facing
error before exiting. `core` validates only `layout_version` and
`project`; schema validation for other sections is the
responsibility of the module that owns them.

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
