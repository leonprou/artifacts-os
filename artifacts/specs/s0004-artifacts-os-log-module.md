---
kind: spec
name: artifacts-os-log-module
status: final
version: 2
created: 2026-04-20
updated: 2026-05-10
task: "[[0001-migrate-docs-specs-to-openstation]]"
agent: manual
id: s0004
---

# artifacts-os: log Module

> **Superseded sections:** The event-type table previously documented in
> § "Event Types" below (`artifact.created`, `artifact.updated`, etc.) is
> now the authoritative wire format defined in
> [[s0025-artifact-events]] § C1. `Logger` / `LogReader` API is
> unchanged by that spec. This spec retains its full Logger / LogReader
> surface; only the event-type schema cross-reference moves to `s0025`.

High-level spec for `artifacts_os.log`.

## Purpose

Write and read structured JSONL records for artifact operations and agent
runs. Provides a lightweight audit trail without a database dependency.
Consumed primarily by `ai` (run records) and optionally by `cli`
(operation logging).

## Dependencies

- `artifacts_os` (core) — `ArtifactMeta` for type hints only
- stdlib only (`json`, `pathlib`, `datetime`) — no external deps

## Public API

```python
from artifacts_os.log import (
    Logger,    # writes JSONL entries to a log file
    LogReader, # reads and filters entries from a log file
    LogEntry,  # dataclass: ts, event, payload
)
```

## Key Concepts

### LogEntry

```python
@dataclass
class LogEntry:
    ts: str          # ISO 8601 timestamp
    event: str       # event name (see Event Types below)
    payload: dict    # arbitrary key/value data
```

### Logger

Appends one JSON object per line to a target file. Thread-safe via
file-level locking (or append-only writes, which are atomic on most
POSIX filesystems for small writes).

```python
class Logger:
    def __init__(self, path: Path) -> None: ...
    def write(self, event: str, **payload) -> None: ...
```

### LogReader

Reads a JSONL file and returns filtered `LogEntry` objects.

```python
class LogReader:
    def __init__(self, path: Path) -> None: ...
    def read(
        self,
        *,
        event: str | None = None,   # filter by event name
        since: str | None = None,   # ISO 8601; exclude entries before
        limit: int | None = None,   # return at most N entries (latest)
    ) -> list[LogEntry]: ...
```

## Event Types (initial set)

| Event | Written by | Key payload fields |
|-------|-----------|-------------------|
| `artifact.created` | `store.create` (optional) | `kind`, `id`, `path` |
| `artifact.updated` | `store.update` (optional) | `kind`, `id`, `fields` |
| `run.started` | `ai.AgentRunner` | `task`, `agent`, `mode` |
| `run.completed` | `ai.AgentRunner` | `task`, `exit_code`, `cost`, `turns` |
| `run.failed` | `ai.AgentRunner` | `task`, `error` |

Core (`store`) does not write log entries by default — callers pass a
`Logger` instance if they want logging. `ai` always writes run events.

## File Location Convention

Log files live in `artifacts/logs/`. One file per task (named after
the task stem) for run logs; one file for general operation logs. The
exact naming convention is the caller's responsibility — `log` is
location-agnostic.

## Scope Boundary

- **In:** JSONL write/read, entry filtering, event schema
- **Out:** log file naming, log rotation, display/formatting (that's `views` or `cli`)
