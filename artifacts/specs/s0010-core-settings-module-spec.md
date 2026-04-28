---
kind: spec
id: s0010
name: core-settings-module-spec
status: draft
task: "[[t0024-spec-core-settings-module-supersede]]"
created: 2026-04-26
---

# artifacts-os: core.Settings

Spec for the settings facility owned by `artifacts_os.core`. Settings
parsing — reading the project settings file, validating its schema,
and producing a typed `Settings` tree — lives inside `core` rather
than in a sibling `config` module. This consolidates I/O for the
project artifacts vault (vault discovery, kinds loading, init-time
YAML writes, and now settings parsing) under a single module.

Supersedes: `s0009-artifacts-os-config-module`. See that spec for
the prior split-module design and decision history.

## Purpose

Load the project settings file from disk (`artifacts.yaml` at the
vault root), validate its `layout_version`, and return a typed
`Settings` dataclass that contains **only** what `core` itself uses
(`layout_version`, `project`) plus the raw remainder of the parsed
YAML (`raw`). Other modules — including library modules like `views`
and downstream consumers like OpenStation — **extend `Settings`**
to add their own typed fields. Each module owns its own subclass
and its own parser.

`core` owns the loader because:

- `core` already discovers the vault root (`find_vault_root`) and
  loads `kinds/` definitions; settings live alongside.
- `init` already writes `artifacts.yaml` from `core`; reading it
  back belongs in the same module.
- Folding the loader into `core` removes the need for a sibling
  `config` module and keeps the dependency DAG narrow.

## Design Principle: Settings Is a Base; Modules Extend It

`artifacts_os` is a library. Each module has its own configuration
needs. Rather than having `core` know the schema for every module's
section, the spec follows a layered model:

- **`core.Settings`** is the base dataclass. It contains only the
  fields `core` itself reads (`layout_version`, `project`) plus a
  raw view of the YAML document (`raw`).
- **Module-specific subclasses** (e.g. `views.ViewsSettings`,
  consumer-defined `RunSettings`) extend `Settings`, add their own
  typed fields, and provide a `from_base(base: Settings) -> Self`
  parser that reads the relevant section out of `base.raw`.

The DAG stays clean: `core` never imports from `views` or any
consumer, because it never references their settings classes.
Each module owns its section end-to-end: dataclass definition,
parser, and (eventually) writer.

## Public API

```python
from artifacts_os.core import (
    load_settings,                # (path: Path) -> Settings
    UnsupportedSchemaVersion,     # ValueError subclass
)

from artifacts_os.core.models import (
    Settings,           # base dataclass — extend in other modules
    ProjectConfig,      # project: name, alias
)
```

`load_settings` and `UnsupportedSchemaVersion` are exported from
the `core` package root. The base `Settings` dataclass and
`ProjectConfig` live in `core.models` alongside `KindDef` and
`ArtifactMeta`. There is no `artifacts_os.config` module — imports
must use `core` / `core.models`.

`ViewConfig`, `ViewsConfig`, and `ViewsSettings` are owned by the
`views` module (see s0007 for their definitions).

### `load_settings(path: Path) -> Settings`

1. Read and parse the YAML file at `path`.
2. Check `layout_version`; raise `UnsupportedSchemaVersion` if
   the version is missing or not in the supported set.
3. Construct `ProjectConfig` from the `project` section
   (required).
4. Store the entire parsed YAML document as `raw: dict[str, Any]`
   on the returned `Settings`. Module-specific subclasses read
   their sections from this dict.
5. Return the populated `Settings`.

`core` does not parse `views`, `default_views`, or any other
section. It does not validate keys outside `project`. It does
not coerce types within `raw`.

### Dataclasses

```python
@dataclass
class ProjectConfig:
    name: str
    alias: str | None = None

@dataclass(kw_only=True)
class Settings:
    layout_version: int
    project: ProjectConfig
    raw: dict[str, Any] = field(default_factory=dict)
```

`kw_only=True` lets subclasses add required fields cleanly without
fighting Python's "non-default after default" dataclass rule.

## Extension Pattern

Each module that wants typed access to its own section defines a
`Settings` subclass:

```python
# views/models.py
@dataclass(kw_only=True)
class ViewsSettings(Settings):
    views: ViewsConfig | None = None  # owned by `views`

    @classmethod
    def from_base(cls, base: Settings) -> "ViewsSettings":
        return cls(
            layout_version=base.layout_version,
            project=base.project,
            raw=base.raw,
            views=_parse_views(base.raw.get("views"),
                               base.raw.get("default_views")),
        )
```

Callers wire the loader and the extension parser together:

```python
from artifacts_os.core import load_settings
from artifacts_os.views import ViewsSettings

base = load_settings(path)
settings = ViewsSettings.from_base(base)
settings.views.views["active"].columns
```

A consumer that adds its own section follows the same pattern
without coupling to the library's release cycle:

```python
# consumer side
@dataclass(kw_only=True)
class RunSettings(Settings):
    run: RunConfig | None = None

    @classmethod
    def from_base(cls, base: Settings) -> "RunSettings": ...
```

If a consumer needs multiple sections at once it can either compose
them — `RunSettings.from_base(ViewsSettings.from_base(base))` — or
define a single subclass that adds all the fields it cares about.
The library does not prescribe one or the other.

## Section Ownership Convention

Each module owns one or more top-level keys end-to-end: the
dataclass(es) for that section, its parser, and (eventually) its
writer. `core` parses nothing it doesn't own.

| Module    | Owns top-level key(s)         | Subclass                |
|-----------|-------------------------------|-------------------------|
| `core`    | `layout_version`, `project`   | `Settings` (base)       |
| `views`   | `views`, `default_views`      | `ViewsSettings`         |
| consumer  | `<their key(s)>`              | their own `Settings` subclass |

The convention is **structural, not enforced** — `Settings.raw`
is plain data and any caller can read any field. Following the
convention keeps a write API tractable: each module persists only
its own subtree.

### "Global" — Narrow Definition

The global section is intentionally narrow:

```yaml
layout_version: 1
project:
  name: "..."
  alias: "..."
```

Only schema-versioning and project identity are global. Every
other top-level key belongs to a specific module's subclass.

## Schema Versioning

The settings file must contain `layout_version: <int>` at the top
level. The current supported version is **1**.

Handling rules:

| Condition                    | Behaviour                                                          |
|------------------------------|--------------------------------------------------------------------|
| `layout_version` absent      | Raise `UnsupportedSchemaVersion("missing layout_version")`         |
| `layout_version: 1`          | Proceed normally                                                   |
| `layout_version: N` (N > 1)  | Raise `UnsupportedSchemaVersion(f"unsupported version {N}")`       |

`UnsupportedSchemaVersion` is a plain `ValueError` subclass defined
in `core` and re-exported from `artifacts_os.core`. Callers catch
it and surface a user-facing error before exiting.

`core` validates only `layout_version` and `project`. Schema
validation for other sections is the responsibility of the module
that owns them — each module is free to raise its own errors when
parsing its subtree.

## Library-Defined Schema (core only)

The portion of `artifacts.yaml` typed by `core`:

```yaml
layout_version: 1           # required; int
project:                    # required
  name: "<project>"         # required; str
  alias: "<alias>"          # optional; str
```

That is the entire surface `core.load_settings` types. Other
sections (`views`, `default_views`, anything consumer-defined)
are present in `Settings.raw` but untyped at the `core` layer.

For the `views` section schema, see s0007.

## Module Dependency

The DAG is unchanged from the existing architecture:

```
core → views → cli, tui
core → log   → ai
```

`core` parses settings into a `Settings` base. `views`, `cli`,
`tui`, etc. import `Settings` from `core.models` and define
their own subclasses. `core` must not import from `views`, `cli`,
`tui`, `log`, `ai`, or any consumer.

Entry points (`cli`, `tui`, downstream applications) are
responsible for chaining `load_settings` with whichever module
subclasses they need.

## Scope Boundary

- **In:** YAML file I/O, `layout_version` validation, typed
  construction of `ProjectConfig`, preservation of the full
  parsed document on `Settings.raw`, definition of the base
  `Settings` dataclass that other modules extend, error
  reporting (`UnsupportedSchemaVersion`).
- **Out:**
  - **Write API** — deferred (see Future Work).
  - Parsing or typing any section other than `project`.
  - Defining module-specific dataclasses
    (`ViewConfig`, `ViewsConfig`, etc.) — those live in their
    owning module.
  - Argument parsing (owned by `cli`).
  - Filter application (owned by the `core` list/query path,
    not by `load_settings`).
  - Rendering (owned by `views`).
  - Hook execution.
  - Business logic of any kind.

## Future Work

A write API will be specified in a follow-up when a real
write-consumer task lands (e.g. an `init`-time settings update
or a generic `set` command). The guiding principle for that
future spec:

> Modules persist only their own subtree.

Each module's `Settings` subclass is responsible for serialising
its own section back to YAML; `core` writes the global subtree;
no module touches another module's keys. The runtime enforcement
model (single writer per section vs. cooperative merging vs.
key-scoped write helpers) is left open for the future spec to
decide. Recording the principle here ensures the convention
isn't lost between now and that work.
