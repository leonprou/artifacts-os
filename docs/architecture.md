# Architecture

`artifacts-os` is a Python library for storing, discovering, and managing
structured markdown artifacts. It is composed of eight modules with a strict
one-way dependency DAG; no module may import from a peer or downstream module.

---

## Public API Entry Points

`artifacts_os` (top-level package) re-exports the most commonly used symbols:

```python
from artifacts_os import (
    # vault / registry
    find_vault_root, Registry, KindDef,

    # CRUD
    create, get, update,

    # discovery
    list_artifacts, resolve, search,

    # models
    Artifact, ArtifactMeta,

    # errors
    ArtifactError, NotFoundError, AmbiguousError, ValidationError,
)
```

Settings and validation symbols live in `artifacts_os.core` and must be
imported from there directly:

```python
from artifacts_os.core import (
    # settings
    load_settings, Settings, ProjectConfig, UnsupportedSchemaVersion,

    # validation
    validate_one, validate_many, ValidationIssue, ValidationResult,
)
```

---

## Module Map

| Module | Status | Responsibility |
|--------|--------|---------------|
| `core` | shipped | Vault location, storage, discovery, registry, settings, validation |
| `views` | shipped | Formatting layer — column layout, Rich table rendering |
| `cli` | shipped | `artifacts` console script — argument parsing, command dispatch |
| `events` | shipped | Event catalog + always-on JSONL audit stream (spec: s0025) |
| `hooks` | shipped | Opt-in declarative reactions — shell, notify, file-drop (spec: s0025) |
| `log` | stub | JSONL operation log (spec: s0004) |
| `tui` | stub | Interactive terminal browser (spec: s2065) |
| `ai` | stub | Agent context and execution (spec: s2066) |

---

## Dependency DAG

```
core
├── events
│   └── hooks
│       └── ai
├── views
│   ├── cli
│   └── tui
└── log
    └── ai
```

Each module may import from its listed ancestors only. No peer imports
across branches are permitted. `cli` depends on both `core` and `views`.
`events` and `hooks` both depend on `core` only; `hooks` depends on `events`
for the catalog types. `core` never imports from any downstream module.

---

## Design Principles

**Atomic writes.** `create` uses `O_CREAT | O_EXCL` to prevent races on
new files; `update` uses `os.replace` (rename) for safe in-place updates.

**Body immutability.** `update` is frontmatter-only — the artifact body is
always preserved verbatim. Callers that need to modify the body write the
file directly.

**No mocking in tests.** Every test operates on a real temp-dir vault via
the `make_vault` fixture and `tmp_path`. No file-system mocking.

**Typed models.** All data structures are `@dataclass`es with full type
annotations (`KindDef`, `ArtifactMeta`, `Artifact`, `Settings`).

**Caller-owned kind definitions.** `artifacts-os` never populates
`KindDef.meta` — callers define columns, status colours, and any other
display conventions. The library reads those keys by convention; it does
not prescribe them.

---

## Cross-References

- Settings extension pattern — [settings.md](settings.md)
- Adding a new artifact kind — [adding-a-kind.md](adding-a-kind.md)
- Events stream and CLI reference — [events.md](events.md)
- Hooks reactive layer — [hooks.md](hooks.md)
- `views` public API — [../src/artifacts_os/views/README.md](../src/artifacts_os/views/README.md)
- `cli` command reference — [../src/artifacts_os/cli/README.md](../src/artifacts_os/cli/README.md)
- Authoritative specs: `s2060-artifacts-os-architecture`, `s2061-artifacts-os-module-system`
