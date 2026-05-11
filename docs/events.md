# Events

The events module is the always-on observability layer for an artifacts vault.
Every CRUD operation — create, update, status change, validate — appends one
JSON line to a daily JSONL file under `artifacts/logs/events/`. No
configuration is required; the stream is active as soon as `artifacts_os` is
installed. Consumers range from the `artifacts events` CLI to external scripts
that tail the file directly. For the *reactive* layer (running shell commands
or sending notifications in response to events), see [hooks.md](hooks.md).

---

## Event Catalog

Six event types are defined. The catalog is closed — new types require a spec
revision (see `s0025-artifact-events`).

| Event type | When it fires | Key payload fields |
|------------|---------------|--------------------|
| `artifact.created` | After a new artifact file is written | `kind`, `id`, `name`, `stem`, `path`, `fields` |
| `artifact.updated` | After frontmatter is updated | `kind`, `id`, `name`, `stem`, `path`, `changed`, `before`, `after`, `fields` |
| `artifact.status_changed` | After a `status` transition (subset of `updated`) | `kind`, `id`, `name`, `stem`, `path`, `before`, `after`, `fields` |
| `artifact.validated` | After `validate_one` / `validate_many` runs | `kind`, `id`, `stem`, `path`, `result` (`"pass"` \| `"fail"`), `issues` |
| `hook.fired` | After a hook action completes successfully | `hook`, `matcher`, `action`, `duration_ms`, `phase` |
| `hook.failed` | After a hook action raises | `hook`, `matcher`, `action`, `phase`, `blocking`, `error`, `duration_ms` |

### JSONL record shape

Every line written to disk is:

```json
{"ts": "2026-05-11T10:23:01+00:00", "event": "artifact.created",
 "kind": "task", "id": "t0042", "name": "fix-login-bug",
 "stem": "t0042-fix-login-bug", "path": "/my-vault/artifacts/tasks/t0042-fix-login-bug.md",
 "fields": {"status": "ready", "assignee": "developer"}}
```

`ts` is ISO 8601 with UTC offset. The remaining keys are the payload for that
event type (see the catalog table above). Pre-phase events are never written to
disk — only post-phase records appear in the JSONL files.

### Storage layout

```
artifacts/logs/events/
  2026-05-11.jsonl
  2026-05-12.jsonl
  ...
```

One file per UTC day, append-only. The directory is created automatically on
first write. Path is configurable via the `events.dir` key in `artifacts.yaml`
— see [settings.md § Events Section](settings.md#events-section).

---

## `artifacts events` CLI Reference

```
artifacts events [--since DATE] [--event TYPE] [--tail [N]] [--follow] [--json]
artifacts events tail [...]    # hidden backward-compat alias
```

Default output is a Rich table with columns `ts`, `event`, `kind`, `artifact`.
`--json` / `-j` switches to raw JSONL, one record per line.

### Flags

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--since DATE` | | all dates | Show events from this date forward (`YYYY-MM-DD`) |
| `--event TYPE` | `-e` | all types | Filter by event type; may be repeated |
| `--tail [N]` | | off | Show only the last N events from the snapshot. Bare `--tail` defaults to 50. `--tail 0` shows nothing. Without `--tail`, all matching events are shown old→new. |
| `--follow` | `-f` | off | Continuously stream new entries as they are appended |
| `--json` | `-j` | off | Output raw JSONL instead of a Rich table |

`--tail` applies to the initial snapshot only; `--follow` then streams
everything new without a cap.

The `events tail` form (e.g. `artifacts events tail --follow`) is a hidden
backward-compatible alias. The `tail` token is stripped by argv preprocessing
before argparse sees it; all flags behave identically.

There is no `--limit` flag — use `--tail` instead.

### Examples

```bash
# Last 20 events across all types
artifacts events --tail 20

# Watch the stream live (Ctrl-C to stop)
artifacts events --follow

# Status changes only, last 7 days, as JSONL
artifacts events --since 2026-05-05 --event artifact.status_changed --json

# All hook failures ever
artifacts events --event hook.failed

# Follow, filter to a single kind, pipe to jq
artifacts events --follow --event artifact.created --json | jq '.id'
```

---

## Worked Example: Consuming the stream from Python

An external script that reads yesterday's and today's events and counts them by
type:

```python
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from artifacts_os import find_vault_root

root = find_vault_root()
events_dir = root / "artifacts" / "logs" / "events"

counts: Counter = Counter()
for day in [date.today() - timedelta(1), date.today()]:
    log = events_dir / f"{day.isoformat()}.jsonl"
    if not log.exists():
        continue
    for line in log.read_text().splitlines():
        if line.strip():
            record = json.loads(line)
            counts[record["event"]] += 1

for event_type, n in counts.most_common():
    print(f"{n:4d}  {event_type}")
```

---

## Public API

The event constants are importable if you need to compare event types in code:

```python
from artifacts_os.events.catalog import (
    ARTIFACT_CREATED,        # "artifact.created"
    ARTIFACT_UPDATED,        # "artifact.updated"
    ARTIFACT_STATUS_CHANGED, # "artifact.status_changed"
    ARTIFACT_VALIDATED,      # "artifact.validated"
    HOOK_FIRED,              # "hook.fired"
    HOOK_FAILED,             # "hook.failed"
    ALL_EVENT_TYPES,         # frozenset of all six
)
```

To register a custom emitter that fires on every event (e.g. for real-time
forwarding to an external system):

```python
from artifacts_os.core.events import register_emitter, unregister_emitter

def my_emitter(event: str, payload: dict) -> None:
    # payload always contains _phase stripped out; only post-phase calls reach here
    print(f"{event}: {payload.get('id', '')}")

register_emitter(my_emitter)

# Clean up (e.g. in tests)
unregister_emitter(my_emitter)
```

Emitter failures are caught and printed to stderr — they never propagate out
of a CRUD call (invariant I1 from `s0025-artifact-events`).

---

## Cross-References

- Reactive layer (hooks) — [hooks.md](hooks.md)
- Events + hooks configuration in `artifacts.yaml` — [settings.md](settings.md)
- `artifacts events` is one of the reference CLI commands — [../src/artifacts_os/cli/README.md](../src/artifacts_os/cli/README.md)
- Design rationale and invariants — `s0025-artifact-events`
- CLI surface alignment — `s0027-align-events-cli-with-list`
