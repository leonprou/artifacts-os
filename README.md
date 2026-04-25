# artifacts-os

Python library for storing, discovering, and managing structured markdown artifacts (tasks, specs, agents, research) in a vault directory.

## Install

```bash
pip install artifacts-os
```

Editable install with dev dependencies:

```bash
pip install -e ".[dev]"
```

Optional extras: `views` (Rich rendering), `cli`, `tui` (Textual browser), `log`, `ai`, `all`.

## Quick Start

```python
from artifacts_os import find_vault_root, Registry, KindDef, create, get, list_artifacts

# Locate the vault (walks up from CWD looking for artifacts/artifacts.yaml)
root = find_vault_root()

# Define artifact kinds
kinds = [
    KindDef(name="task", dir="tasks", prefix="t", numbered=True,
            statuses=["backlog", "ready", "in-progress", "done"],
            schema={}, meta={}),
    KindDef(name="agent", dir="agents", prefix="", numbered=False,
            statuses=[], schema={}, meta={}),
]
registry = Registry(kinds, root=root)

# Create an artifact
artifact = create(registry, "task", "Fix the login bug")
print(artifact.id)   # t0001

# List artifacts
tasks = list_artifacts(registry, kind="task", status="ready")

# Read a single artifact
task = get(registry, "t0001")
print(task.body)
```

## CLI

```bash
artifacts list --kind task --status ready
artifacts show t0001
artifacts create "My new task" --kind task
artifacts status t0001 in-progress
```

## Project Structure

```
src/artifacts_os/
  __init__.py    # re-exports core public API
  core/          # storage, discovery, registry (fully implemented)
  views/         # column layout, rendering (stub — spec: s0002)
  log/           # JSONL operation log (stub — spec: s0005)
  cli/           # argument parsing, command dispatch (stub)
  tui/           # interactive terminal browser (stub)
  ai/            # agent context and execution (stub)
tests/           # mirrors src/; uses tmp_path + make_vault fixture, no mocking
artifacts/specs/ # architecture and module specs
```

## Development

```bash
pip install -e ".[dev]"

pytest                            # run all tests
pytest tests/core/test_store.py  # run a single file
```

Coding conventions:
- Full type annotations on all public functions
- Dataclasses for models (`KindDef`, `ArtifactMeta`, `Artifact`)
- Atomic writes: `O_CREAT | O_EXCL` for create, `os.replace` for update
- No mocking in tests — all tests operate on real temp-dir vaults

## Architecture

See `artifacts/specs/` for deep dives:

- [`s0002-artifacts-os-architecture.md`](artifacts/specs/s0002-artifacts-os-architecture.md) — module contracts, storage model, public API
- [`s0005-artifacts-os-module-system.md`](artifacts/specs/s0005-artifacts-os-module-system.md) — module inventory, dependency DAG, extensibility model
