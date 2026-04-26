---
kind: spec
id: s0009
name: artifacts-os-config-module
status: draft
task: "[[t0016-re-scope-s0007-views-spec]]"
created: 2026-04-26
---

# artifacts-os: config Module

Spec for `artifacts_os.config`. This module owns settings-file I/O,
validation, and schema versioning. It produces typed config objects
that other modules consume. It never applies business logic — that
stays in `core`, `views`, `cli`, etc.

Source reference: `~/workspace/open-station/.openstation/openstation.yaml`

## Purpose

Load the project settings file from disk, validate its structure and
schema version, and return a single `Settings` dataclass whose nested
sections are typed. Per-section parsing uses private helpers local to
`config` (e.g. `_parse_view` for view entries).

## Decision: Where Views Config Lives

**Decision: `artifacts.yaml` absorbs all config (option a — single file).**

Rationale:
- Mirrors the reference `openstation.yaml` exactly; one file holds
  `project`, `hooks`, `run`, `views`, `default_views`, `defaults`,
  and `layout_version`.
- Fewer files to discover — callers know the vault root and load
  one file unconditionally.
- `find_vault_root` already locates `artifacts/artifacts.yaml`; no
  additional discovery logic is needed.

`artifacts/artifacts.yaml` will be extended with `views`,
`default_views`, and any other top-level sections as projects need them.

## Public API

```python
from artifacts_os.config import (
    Settings,           # root dataclass
    ProjectConfig,      # project: name, alias
    RunConfig,          # run: detached_backend, tmux (TmuxConfig)
    TmuxConfig,         # run.tmux: mode, target_session
    ViewsConfig,        # views: dict[str, ViewConfig]; default_views: dict[str, str]
    load_settings,      # (path: Path) -> Settings
)
```

### `load_settings(path: Path) -> Settings`

1. Read and parse the YAML file at `path`.
2. Check `layout_version`; raise `UnsupportedSchemaVersion` if
   the version is not in the supported set.
3. Construct each section's dataclass from the parsed dict,
   applying defaults for absent keys.
4. For the `views` section, construct `ViewConfig` via the private
   `_parse_view(dict)` helper local to `config` for each named view entry.
5. Return the populated `Settings`.

### Dataclasses

```python
@dataclass
class TmuxConfig:
    mode: str           # e.g. "window"
    target_session: str # e.g. "os"

@dataclass
class RunConfig:
    detached_backend: str  # e.g. "tmux"
    tmux: TmuxConfig | None = None

@dataclass
class ViewsConfig:
    views: dict[str, ViewConfig]         # name → ViewConfig (parsed by _parse_view)
    default_views: dict[str, str]        # kind → view name

@dataclass
class ProjectConfig:
    name: str
    alias: str | None = None

@dataclass
class Settings:
    layout_version: int
    project: ProjectConfig
    run: RunConfig | None = None
    views: ViewsConfig | None = None
```

`ViewConfig` is defined in `artifacts_os.core.models` — `config`
imports it from there. `config` does not define its own view dataclass.
See the "Module Dependency" section below for the rationale.

## Module Dependency

`config` depends only on `core`. It is consumed by `cli` and `tui`.
`views` is a parallel sibling — neither imports from the other.

```
core → config → cli, tui
core → views  → cli, tui
core → log    → ai
```

`config` must not import from `views`, `cli`, `tui`, `log`, or `ai`.

### Rationale: `ViewConfig` in `core`

`ViewConfig` is a pure data shape — no I/O, no rendering logic — consumed
by both `config` (which parses view entries from YAML) and `views` (which
resolves column layouts; see s0007). Placing it in `core.models` alongside `KindDef`
and `ArtifactMeta` keeps it accessible to both modules without creating a
`config → views` or `views → config` dependency. The addition is small
enough to land at implementation time; no separate `core` spec rewrite is
required. `ViewConfig` will be added to `core/models.py` with the
following fields:

```python
@dataclass
class ViewConfig:
    columns: str                    # comma-separated field spec string
    filters: dict[str, Any]         # key/value equality filters; default {}
    sort: str | None = None         # optional field name; prefix "-" for descending
```

## Schema Versioning

The settings file must contain `layout_version: <int>` at the top
level. The current supported version is **1**.

Handling rules:

| Condition | Behaviour |
|-----------|-----------|
| `layout_version` absent | Raise `UnsupportedSchemaVersion("missing layout_version")` |
| `layout_version: 1` | Proceed normally |
| `layout_version: N` (N > 1) | Raise `UnsupportedSchemaVersion(f"unsupported version {N}")` |

`UnsupportedSchemaVersion` is a plain `ValueError` subclass defined
in `config`. Callers (`cli`, `tui`) catch it and display a user-facing
error before exiting.

## Full Settings File Schema

Documented from the reference `openstation.yaml`:

```yaml
layout_version: 1           # required; int

project:                    # required
  name: "artifacts-os"      # required; str
  alias: "ao"               # optional; str

run:                        # optional section
  detached_backend: tmux    # str; only "tmux" supported initially
  tmux:
    mode: window            # str
    target_session: os      # str

views:                      # optional; named view map
  <name>:
    columns: "id,name,status"   # required; comma-separated field spec string
    filters:                     # optional; key/value equality map
      <field>: <value>
    sort: field_name             # optional; prefix "-" for descending

default_views:              # optional; kind → view name
  <kind>: <view-name>

defaults:                   # optional; per-command defaults
  show:
    editor: true            # bool; open editor after show
```

Unrecognised top-level keys are ignored (forward-compatible reads).
Unrecognised keys within a section are also ignored.

## Scope Boundary

- **In:** file I/O, YAML parsing, schema version validation, typed
  dataclass construction, error reporting for bad schema
- **Out:** argument parsing (`cli`), filter application (`core`),
  rendering (`views`), hook execution, business logic of any kind
