---
kind: spec
name: artifacts-os-ai-module
status: draft
created: 2026-04-20
task: "[[0001-migrate-docs-specs-to-openstation]]"
agent: manual
id: s0001
---

# artifacts-os: ai Module

High-level spec for `artifacts_os.ai`.

## Purpose

Load structured task context from the vault and invoke an AI agent to
execute it. Bridges the artifact storage layer (`core`) with agent
execution backends. Writes run records to `log`.

## Dependencies

- `artifacts_os` (core)
- `artifacts_os.log`
- Agent backend deps: **TBD** (see Deferred)

## Public API

```python
from artifacts_os.ai import (
    build_context,  # (registry, task_ref, *, sections) -> str
    AgentRunner,    # .run(registry, task_ref, **opts) -> int
    RunRecord,      # dataclass: task, agent, mode, exit_code, cost, turns
)
```

## Key Concepts

### `build_context`

Reads the full `Artifact` for `task_ref` and assembles a context string
for injection into the agent's prompt.

```python
def build_context(
    registry: Registry,
    task_ref: str,
    *,
    sections: list[str] | None = None,  # body sections to include
) -> str:
```

`sections` defaults to `KindDef.meta["ai"]["context_sections"]` for the
task's kind, falling back to `["Requirements", "Context", "Verification"]`.

The returned string includes:
- Frontmatter fields as structured key/value pairs
- Selected body sections, preserved as markdown

### `AgentRunner`

Invokes the configured backend with a task context. Writes `run.started`,
`run.completed`, and `run.failed` log entries via a `Logger`.

```python
class AgentRunner:
    def __init__(
        self,
        backend: AgentBackend,       # abstraction over Claude CLI / SDK / other
        logger: Logger | None = None,
    ) -> None: ...

    def run(
        self,
        registry: Registry,
        task_ref: str,
        *,
        interactive: bool = False,
        dry_run: bool = False,
    ) -> int: ...                    # returns exit code
```

### `AgentBackend` (protocol)

```python
class AgentBackend(Protocol):
    def invoke(
        self,
        context: str,
        *,
        interactive: bool,
        dry_run: bool,
    ) -> int: ...
```

Concrete backends are registered separately. Initial target: Claude CLI
subprocess. Backend selection and configuration are deferred.

### `RunRecord`

```python
@dataclass
class RunRecord:
    task: str
    agent: str
    mode: str          # "interactive" | "autonomous"
    started: str       # ISO 8601
    finished: str | None
    exit_code: int | None
    cost: float | None
    turns: int | None
```

`RunRecord` is populated from log entries by `LogReader` — it is not
stored separately.

## `KindDef.meta` keys consumed by `ai`

```python
meta = {
    "ai": {
        "context_sections": ["Requirements", "Context", "Verification"],
        # future: "prompt_prefix", "allowed_tools", etc.
    }
}
```

## Scope Boundary

- **In:** context assembly, backend invocation, run logging
- **Out:** lifecycle transition after run (status update stays with
  the agent itself or a future `actions` module), agent spec authoring,
  session persistence (that's the backend's concern)

## Deferred

| Item | Notes |
|------|-------|
| Backend implementation (Claude CLI vs SDK) | Separate spec; is the primary open question for this module |
| Auth / credential handling | Depends on backend |
| Streaming output capture | Depends on backend |
| `allowed-tools` injection | From task frontmatter into backend invocation |
| Multi-task orchestration | Post-MVP |
