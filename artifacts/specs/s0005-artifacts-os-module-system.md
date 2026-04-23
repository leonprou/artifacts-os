---
kind: spec
name: artifacts-os-module-system
status: final
created: 2026-04-20
task: "[[0001-migrate-docs-specs-to-openstation]]"
agent: manual
id: s0005
---

# artifacts-os Module System

Defines the extensibility model for `artifacts-os`: how optional modules
are structured, packaged, and composed. Companion to the core architecture
spec (`artifacts-os-architecture.md`).

---

## Decisions Log

| # | Question | Decision |
|---|----------|----------|
| 1 | Package model | One package; modules are subpackages (`artifacts_os.<module>`) |
| 2 | Extensibility | Official modules only — no third-party plugin protocol |
| 3 | `actions` module | Deferred — not in initial scope |
| 4 | Inter-module config | `KindDef.meta` dict; each module documents the keys it reads |
| 5 | `views` columns/filters | Separate spec required before implementation |

---

## Module Inventory

| Module | Subpackage | Purpose | Extras key |
|--------|-----------|---------|------------|
| **core** | `artifacts_os.core` | Storage, discovery, registry | *(always installed)* |
| **views** | `artifacts_os.views` | Column layout, field specs, rendering config | `views` |
| **log** | `artifacts_os.log` | Structured JSONL operation log | `log` |
| **cli** | `artifacts_os.cli` | Argument parsing, command dispatch | `cli` |
| **tui** | `artifacts_os.tui` | Interactive terminal browser | `tui` |
| **ai** | `artifacts_os.ai` | Agent context loading and execution | `ai` |

---

## Dependency DAG

```
core  ──────────────────────────────────┐
  │                                      │
  ├── views  (rich)                      │
  │     ├── cli   (no extra deps)        │
  │     └── tui   (textual)             │
  │                                      │
  └── log    (stdlib only)               │
        └── ai    (backend TBD) ─────────┘
```

Rules:
- `core` has no module dependencies.
- `views` depends on `core` only (plus `rich`).
- `cli` depends on `core` + `views`.
- `tui` depends on `core` + `views` (plus `textual`).
- `log` depends on `core` only (stdlib, no extra deps).
- `ai` depends on `core` + `log`; agent backend deps are TBD and will
  be specced separately.
- No module imports from a peer module unless that peer is listed as a
  declared dependency above.

---

## Package Structure

```
artifacts-os/
  src/
    artifacts_os/
      __init__.py        # re-export shim — exposes core public API (see artifacts-os-architecture.md)

      core/
        __init__.py      # core public API: Registry, Artifact, KindDef, errors, …
        models.py
        errors.py
        frontmatter.py
        registry.py
        ids.py
        store.py
        discover.py
        vault.py

      views/
        __init__.py      # public API: FieldSpec, render_table, ViewConfig
        fields.py        # FieldSpec dataclass, parse_field_specs, format_field
        table.py         # render_table (rich-backed)
        config.py        # ViewConfig, load_views (reads from settings YAML)

      log/
        __init__.py      # public API: Logger, LogReader, LogEntry
        writer.py        # Logger — appends JSONL entries
        reader.py        # LogReader — reads and filters entries

      cli/
        __init__.py      # main() entry point
        commands/
          list_.py       # openstation list
          show.py        # openstation show
          create.py      # openstation create
          status.py      # openstation status
          verify.py      # openstation verify
          agents.py      # openstation agents

      tui/
        __init__.py      # run_browser() entry point
        app.py           # Textual App subclass
        screens/
          browser.py     # artifact list screen
          detail.py      # artifact detail screen

      ai/
        __init__.py      # public API: AgentRunner, build_context
        context.py       # build_context — assembles task prompt/context
        runner.py        # AgentRunner — invokes agent backend

  tests/
    core/
    views/
    log/
    cli/
    tui/
    ai/

  pyproject.toml
```

---

## `pyproject.toml` Extras

```toml
[project.optional-dependencies]
views = ["rich>=13"]
log   = []
cli   = ["rich>=13"]
tui   = ["rich>=13", "textual>=0.50"]
ai    = []              # backend deps TBD
dev   = [
    "pytest>=8",
    "rich>=13",
    "textual>=0.50",
]
all   = [
    "rich>=13",
    "textual>=0.50",
]
```

`cli` lists `rich` directly (rather than depending on the `views` extra)
because pip extras do not support intra-package extra-to-extra references
in all build backends. Both `cli` and `views` declare `rich>=13`
independently.

---

## Inter-Module Contract: `KindDef.meta`

`KindDef.meta` is the primary channel through which callers pass
module-specific configuration. Core never reads `meta`. Each module
documents the keys it consumes.

### Ownership

Each module owns a namespace of `meta` keys:

| Module | Key prefix |
|--------|-----------|
| `views` | `views.*` or flat (see views spec) |
| `ai` | `ai.*` |
| `tui` | `tui.*` (if distinct from views) |

The exact key schema for `views` is **deferred** — see
"Deferred Deliverables" below.

### Example (illustrative, not final)

```python
KindDef(
    name="task",
    dir="tasks",
    prefix="t",
    numbered=True,
    statuses=["backlog", "ready", ...],
    schema={},
    meta={
        # consumed by views module (schema TBD)
        "columns": ["id", "status", "assignee", "name"],
        "status_colors": {
            "done": "green", "failed": "red", "in-progress": "yellow"
        },
        # consumed by ai module (schema TBD)
        "ai": {
            "context_sections": ["Requirements", "Context"],
        },
    },
)
```

---

## Per-Module Scope

### `views`

**Purpose:** Produce renderable representations of artifact data for
display in `cli` and `tui`. Does not emit output itself — returns
strings or rich renderables.

**Public API:**

```python
from artifacts_os.views import (
    FieldSpec,          # dataclass: key, format, label
    parse_field_specs,  # (str) -> list[FieldSpec]
    format_field,       # (value, fmt) -> str
    render_table,       # (items, columns, *, kind_def) -> rich.Table | str
    ViewConfig,         # dataclass: columns, filters, sort
    load_views,         # (settings_path) -> dict[str, ViewConfig]
)
```

**Scope boundary:** `views` defines _what_ to show and _how to format_
it. It does not handle argument parsing, I/O, or user interaction.

**Deferred:** Column/filter schema, `ViewConfig` contract, named view
loading from settings YAML — see "Deferred Deliverables".

---

### `log`

**Purpose:** Write and read structured JSONL records for agent runs and
artifact operations.

**Public API:**

```python
from artifacts_os.log import (
    Logger,     # writes JSONL entries to a file
    LogReader,  # reads and filters entries
    LogEntry,   # dataclass: timestamp, event, payload
)
```

**`Logger`:**

```python
class Logger:
    def __init__(self, path: Path) -> None: ...
    def write(self, event: str, **payload) -> None:
        # Appends {"ts": ISO8601, "event": event, **payload} as JSONL
```

**`LogReader`:**

```python
class LogReader:
    def __init__(self, path: Path) -> None: ...
    def read(
        self,
        *,
        event: str | None = None,
        since: str | None = None,  # ISO8601
        limit: int | None = None,
    ) -> list[LogEntry]: ...
```

No external dependencies. Uses stdlib `json`, `pathlib`, `datetime`.

---

### `cli`

**Purpose:** Expose `artifacts-os` capabilities as a command-line tool.
Parses arguments, calls core + views, prints output.

**Entry point:**

```toml
[project.scripts]
artifacts = "artifacts_os.cli:main"
```

**Commands (initial set):**

| Command | Core function(s) used |
|---------|-----------------------|
| `list [--kind] [--status] [--fields]` | `list_artifacts` + `views.render_table` |
| `show <ref> [--kind]` | `get` |
| `create <title> [--kind] [--fields]` | `create` |
| `status <ref> <new-status>` | `update` |
| `verify [--all] [--kind]` | `list_artifacts` + frontmatter checks |
| `agents [list\|show]` | `list_artifacts(kind="agent")` / `get` |

**Error handling:** catches `NotFoundError`, `AmbiguousError`,
`ValidationError`; maps to exit codes per `artifacts-os-architecture.md` error hierarchy.

**No lifecycle logic** — `cli` does not implement transition validation,
date auto-set, or sub-task promotion. Those remain in OpenStation until
`actions` is specced.

---

### `tui`

**Purpose:** Interactive terminal browser over vault artifacts.

**Entry point:**

```python
from artifacts_os.tui import run_browser

run_browser(registry)   # blocks until user exits
```

**Screens (initial):**

| Screen | Content |
|--------|---------|
| Browser | Filterable artifact list using `views` column layout |
| Detail | Full artifact content (frontmatter + body) |

Depends on `textual` + `views`. Rendering config reads from
`KindDef.meta` via the same `views` column schema.

Internal architecture (Textual app structure) is an implementation
detail — not specced here.

---

### `ai`

**Purpose:** Load task context and invoke an agent to execute it.

**Public API:**

```python
from artifacts_os.ai import (
    build_context,  # (registry, task_ref) -> str
    AgentRunner,    # run(registry, task_ref, *, interactive, logger) -> int
)
```

**`build_context`:** Reads the task `Artifact`, extracts sections
named in `KindDef.meta["ai"]["context_sections"]` (default:
`["Requirements", "Context", "Verification"]`), and returns a
formatted prompt string.

**`AgentRunner`:** Invokes the configured agent backend (subprocess or
SDK — TBD in a separate spec). Optionally writes run records to a
`Logger`. Returns exit code.

**Backend:** Agent backend selection, auth, and invocation protocol are
deferred — TBD in the `ai` module spec.

---

## Deferred Deliverables

| Item | Blocked on | Notes |
|------|-----------|-------|
| `views` columns/filters schema (`KindDef.meta` keys, `ViewConfig` contract, named view loading) | This spec | Separate spec; blocks `cli` and `tui` implementation |
| `ai` backend design (Claude CLI vs SDK, auth, streaming) | This spec | Separate spec |
| `tui` screen layout and interaction model | `views` spec | Separate spec |
| `actions` module | Strategic decision | Deferred indefinitely |

---

## What Does Not Move into Modules

These remain in OpenStation and are not candidates for `artifacts-os`
modules at this time:

| Concern | Lives in |
|---------|---------|
| Task lifecycle transitions + validation | `openstation/tasks.py` |
| Hook execution | `openstation/hooks.py` |
| Session tracking (state.db) | `openstation/sessions.py` |
| Alert scheduling and connectors | `openstation/alerts.py` |
| Rich status colouring (OpenStation palette) | `openstation/ui.py` |
