# Settings

`artifacts-os` reads project configuration from `artifacts/artifacts.yaml`
at the vault root. `core` parses the global section and stores the full YAML
document so that other modules can extract their own sections without
coupling to the library's release cycle.

---

## Public API

```python
from artifacts_os.core import (
    load_settings,           # parse artifacts.yaml → Settings
    Settings,                # base dataclass
    ProjectConfig,           # project identity (name, alias)
    UnsupportedSchemaVersion, # raised for missing / unknown layout_version
)
```

### `load_settings(path: Path) -> Settings`

Reads and parses the YAML file at *path*.

Raises `UnsupportedSchemaVersion` if `layout_version` is absent or not in
the supported set (currently `{1}`). Raises `KeyError` if the `project`
section is absent.

### `Settings`

Fields: `layout_version: int`, `project: ProjectConfig`, `raw: dict` (full parsed YAML; default `{}`).

### `ProjectConfig`

Fields: `name: str` (required), `alias: str | None` (default `None`).

---

## Worked Example

```python
from artifacts_os.core import find_vault_root, load_settings

root = find_vault_root()
if root is None:
    raise RuntimeError("No artifacts vault found")

settings = load_settings(root / "artifacts" / "artifacts.yaml")

print(settings.project.name)       # "my-project"
print(settings.layout_version)     # 1
print(settings.raw.get("views"))   # raw views section, or None
```

---

## Extension Pattern

Modules that own their own settings section subclass `Settings` and add a
`from_base` classmethod that reads their section from `base.raw`:

```python
from dataclasses import dataclass
from artifacts_os.core import Settings, load_settings

@dataclass(kw_only=True)
class MySettings(Settings):
    my_value: str = "default"

    @classmethod
    def from_base(cls, base: Settings) -> "MySettings":
        section = base.raw.get("my_module") or {}
        return cls(
            layout_version=base.layout_version,
            project=base.project,
            raw=base.raw,
            my_value=section.get("value", "default"),
        )

# Usage
base = load_settings(root / "artifacts" / "artifacts.yaml")
settings = MySettings.from_base(base)
```

`views` ships the canonical implementation of this pattern —
`ViewsSettings.from_base` reads the `views` and `default_views` top-level
keys out of `base.raw`. See
[../src/artifacts_os/views/README.md](../src/artifacts_os/views/README.md)
for the full `ViewsSettings` API.

To compose settings from multiple modules, chain the `from_base` calls:

```python
combined = RunSettings.from_base(ViewsSettings.from_base(base))
```

Or define a single subclass that reads all relevant sections at once.

---

## Views Section

The `views` and `default_views` top-level keys configure named views for
`artifacts list --view`. Views pre-bundle filters, columns, and sort order
so common queries become a single flag.

```yaml
layout_version: 1
project:
  name: my-project

views:
  active:
    columns: id,name,status,assignee   # columns shown in table mode
    filters:
      status: ready                    # pre-filter by status
      assignee: alice                  # post-discovery equality filter
    sort: name                         # ascending; prefix with "-" for descending

default_views:
  task: active   # auto-applies "active" view when --kind task is given
```

**Usage:**

```bash
# Explicit view
artifacts list --view active

# Auto-bound view (fires when --kind task is passed)
artifacts list --kind task

# Explicit flag overrides view filter for that key only
artifacts list --view active --status done
```

`ViewsSettings.from_base` parses these sections from `base.raw`. See
[../src/artifacts_os/cli/README.md](../src/artifacts_os/cli/README.md)
for the full precedence model, error handling, and `-j`/`-q` contract.

Run `artifacts views` to list every defined view from the command line; see
[`cli/README.md`](../src/artifacts_os/cli/README.md) for the full reference.

---

## Schema Versioning

`artifacts.yaml` must begin with `layout_version: 1`. Any other value (or
its absence) causes `load_settings` to raise `UnsupportedSchemaVersion`.

The supported set is `{1}`. Future versions will be added here when the
schema changes in a backward-incompatible way.

---

## Cross-References

- Architecture overview — [architecture.md](architecture.md)
- `views` settings extension — [../src/artifacts_os/views/README.md](../src/artifacts_os/views/README.md)
- Authoritative spec: `s0010-core-settings-module-spec`
