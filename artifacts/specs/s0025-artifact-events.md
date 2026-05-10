---
kind: spec
id: s0025
name: artifact-events
status: draft
version: 2
task: "[[t0130-spec-for-artifact-events-with]]"
created: 2026-05-07
updated: 2026-05-10
---

# Artifact Events

A two-layer reactive surface for `artifacts-os` vault operations:
an **always-on event stream** that records what happened, and an
**opt-in hook layer** that lets agents, users, and external apps
react. The two concerns live in two new sibling modules —
`events/` (catalog + audit stream) and `hooks/` (reactive
layer) — under `core/`. Hooks run synchronously, in-process,
and never block CRUD by default. Async execution (queues,
workers, retries) is delegated to external modules via a
catch-all hook; `artifacts-os` ships no queue and no worker.

## Problem

`artifacts-os` today has no reactive surface. Agents read state
on demand, the CLI returns one-shot output, and external tools
must poll `artifacts/` to detect change. Three concrete needs are
unmet:

1. **Agents** want to react when a sibling artifact changes
   (e.g. an `architect` notices a new `task:spec`-typed task and
   self-assigns).
2. **Users** want light-touch automations — desktop notifications
   on long-running validations, terminal bells on review-ready
   tasks, ad-hoc shell hooks for personal workflows.
3. **External apps** (dashboards, schedulers, sync tools) want a
   durable, append-only stream they can tail without coupling to
   our Python API, and a way to plug a downstream async runtime
   in via a single subscription point.

OpenStation already proves the value of this with its
`events`/`hooks` split (`.openstation/docs/events.md`,
`.openstation/docs/hooks.md`). The same shape applies cleanly to
`artifacts-os` — telemetry is always on; reactions are
declarative, opt-in, and bounded.

The hard constraints:

- Emission must never break a CRUD operation.
- Hooks must never silently corrupt the vault — failures default
  to warnings, opt-in to blocking.
- The work must respect the dependency DAG. `core/store.py`
  cannot import outward.
- Hook config must live on disk so external apps and agents can
  read the same source of truth.
- Async execution semantics (queues, retries, DLQ, worker
  lifecycle) are out of scope — bound externally via a catch-all
  hook.

## Architecture

Two parallel layers built on a shared dispatch shim in `core`:

```
                     ┌──────────────────────────┐
                     │  core/store.py           │
                     │  create() / update()     │
                     └─────────────┬────────────┘
                                   │ _dispatch(event, **payload)
                                   ▼
                ┌────────  core/events.py  ────────┐
                │  registration shim (DAG glue)    │
                │  _emitters list, _dispatch,      │
                │  _dispatch_pre — non-throwing    │
                └────────┬───────────────┬─────────┘
                         │               │
                         ▼               ▼
              ┌──────────────────┐  ┌──────────────────────────┐
              │ events/          │  │ hooks/                   │
              │  catalog         │  │  loader                  │
              │  payload dcls    │  │  matchers                │
              │  stream.py       │  │  actions: shell, notify, │
              │  → JSONL daily   │  │           file-drop      │
              └──────────────────┘  └──────────────────────────┘
                                                │
                                                ▼  (Audience 4)
                                       ┌────────────────────┐
                                       │ external async     │
                                       │ runtime — owns its │
                                       │ queue + worker     │
                                       └────────────────────┘
```

### Runtime Flow — `store.create`

```
validate kind / schema / fields
─── pre-hooks fire ───                  ← opt-in; failure aborts only if blocking=true
write file (O_CREAT | O_EXCL)
parse final artifact
─── core/events._dispatch("artifact.created", …) ───
        │
        ├── events/stream.append(...)   ← always-on, JSONL
        └── hooks/notify(...)           ← post-phase, sync, in-process
```

`update` follows the same shape with `artifact.updated`. When
`status` is in `changed`, a derived `artifact.status_changed`
event is dispatched immediately after `artifact.updated`. The
body write is the irrevocable point — pre-hooks run **before**
it, post-hooks and the stream append run **after**.

### Layer Separation

| Aspect | Event stream (`events/stream.py`) | Hooks (`hooks/`) |
|--------|-----------------------------------|-------------------|
| Purpose | Framework telemetry | User/agent-defined reactions |
| Configuration | Always on, defaults overridable | `artifacts.yaml` `hooks:` key |
| Can block CRUD | Never | Only when `blocking: true` (pre-phase) |
| Failure impact | stderr warning | Pre-blocking: abort; otherwise warning |
| Output | `artifacts/logs/events/YYYY-MM-DD.jsonl` | stdout/stderr, OS notification, file drop, external command |
| Audience | External apps tailing the file | Agents and users running the vault |
| Schema | Documented event catalog (this spec) | Same payload, plus matcher filters |

The event stream is the source of truth; hooks are a
filter-and-react view on top of the same dispatch call. A failed
hook never prevents a stream entry. A failed stream append prints
a warning and does not block hooks.

### Module Layout

This spec introduces **two new sibling modules** under `core/`,
leaving `log/` (per `s0004`) untouched:

```
core ─┬─ events ─┬─ hooks ─── ai
      ├─ views ─┬─ cli
      │        └─ tui
      └─ log    ─── ai          (unchanged — Logger/LogReader per s0004)
```

| Module | Owns |
|--------|------|
| `core/events.py` | DAG-glue registration shim — `register_emitter`, `_dispatch`, `_dispatch_pre`. Knows zero specific event types. |
| `events/` | Event catalog (payload dataclasses, type constants), always-on JSONL stream writer, settings extension. Auto-registers on import. |
| `hooks/` | Hook loader, matcher engine, action runners (shell / notify / file-drop), settings extension. Auto-registers on import. |
| `log/` | **Unchanged.** `Logger` + `LogReader` per `s0004` — opt-in operational logging API for callers, distinct from the events stream. |

`core` works fine without `events` or `hooks` imported (no events
fire, no hooks run, CRUD is unaffected). Importing `events`
enables the audit stream; importing `hooks` enables reactions.
Both register independently with `core.events`.

See **DD-1** for the trade-off vs folding into `log/`.

### Decoupling Pattern — Registered Emitters

`core` cannot import outward (DAG violation). The dispatch must
therefore go *out* of core via a registration callable:

```python
# core/events.py
_emitters: list[Callable[[str, dict], None]] = []

def register_emitter(fn: Callable[[str, dict], None]) -> None:
    _emitters.append(fn)

def _dispatch(event: str, **payload) -> None:
    for fn in _emitters:
        try:
            fn(event, payload)
        except Exception as e:
            sys.stderr.write(f"warning: emitter failed: {e}\n")
```

`events/__init__.py` calls `register_emitter(stream.append)`.
`hooks/__init__.py` calls `register_emitter(notify)`. Tests can
register a capturing emitter without touching either module.

### Invariants

| # | Invariant |
|---|-----------|
| I1 | A failed emitter never propagates — `_dispatch` catches every exception. |
| I2 | The stream entry is independent of hook outcomes — both run, both fail or succeed independently. |
| I3 | `core` imports nothing from `events/`, `hooks/`, or `log/`. |
| I4 | Pre-phase hooks are the **only** mechanism that can abort a CRUD operation, and only when explicitly marked `blocking: true`. |
| I5 | The event payload schema is closed — adding fields requires bumping `version` in this spec's frontmatter and the catalog module. |
| I6 | `artifact.status_changed` fires **only** as a derivative of `artifact.updated` when `status` is in `changed`; it never fires alone. |

## Components

| # | Component | Location | Purpose |
|---|-----------|----------|---------|
| C1 | Event catalog | `src/artifacts_os/events/catalog.py` | Closed enumeration of event types and payload dataclasses |
| C2 | Dispatcher (DAG shim) | `src/artifacts_os/core/events.py` | Registration table, non-throwing dispatch |
| C3 | Stream writer | `src/artifacts_os/events/stream.py` | Always-on JSONL append to `artifacts/logs/events/YYYY-MM-DD.jsonl` |
| C4 | Hook loader | `src/artifacts_os/hooks/loader.py` | Parse `hooks:` from `artifacts.yaml`, match events, run actions |
| C5 | Hook actions | `src/artifacts_os/hooks/actions.py` | `shell`, `notify`, `file-drop` action runners |
| C6 | Settings extensions | `src/artifacts_os/events/settings.py`, `src/artifacts_os/hooks/settings.py` | `EventsSettings.from_base`, `HooksSettings.from_base` |
| C7 | Core integration points | `src/artifacts_os/core/store.py` (modified) | `_dispatch` call sites in `create` / `update`, plus the `artifact.status_changed` derivative |
| C8 | CLI tail command | `src/artifacts_os/cli/commands/events.py` | `artifacts events tail` for human inspection |

### C1 — Event Catalog

The catalog is closed. New event types require a spec revision
and a `version` bump in this spec's frontmatter.

Two universal fields appear on every event:

| Field | Type | Description |
|-------|------|-------------|
| `ts` | string | ISO 8601 timestamp with timezone offset |
| `event` | string | Event type identifier (one of the values below) |

#### `artifact.created`

Emitted after a new artifact file is written and parsed.

```json
{
  "ts": "2026-05-07T14:32:01+03:00",
  "event": "artifact.created",
  "kind": "task",
  "id": "t0042",
  "name": "fix-the-bug",
  "stem": "t0042-fix-the-bug",
  "path": "artifacts/tasks/t0042-fix-the-bug.md",
  "fields": {
    "status": "backlog",
    "assignee": "developer",
    "parent": "[[t0040-auth-feature]]"
  }
}
```

`fields` carries the **persisted frontmatter only**, exactly as
written to disk. No body content. Wikilinks remain as-is.

#### `artifact.updated`

Emitted after `update` completes (file replaced atomically).

```json
{
  "ts": "2026-05-07T14:35:12+03:00",
  "event": "artifact.updated",
  "kind": "task",
  "id": "t0042",
  "name": "fix-the-bug",
  "stem": "t0042-fix-the-bug",
  "path": "artifacts/tasks/t0042-fix-the-bug.md",
  "changed": ["status"],
  "before": {"status": "ready"},
  "after":  {"status": "in-progress"},
  "fields": { "...full new frontmatter..." }
}
```

`changed` lists the keys whose values differ between the
pre-update and post-update frontmatter. `before` and `after`
carry the diffed key/value pairs only. `fields` carries the full
post-update frontmatter for hooks that prefer the complete view.

#### `artifact.status_changed`

A **derived** event. Fires immediately after `artifact.updated`
whenever `status` is in `changed`. Never fires alone (I6).

```json
{
  "ts": "2026-05-07T14:35:12+03:00",
  "event": "artifact.status_changed",
  "kind": "task",
  "id": "t0042",
  "name": "fix-the-bug",
  "stem": "t0042-fix-the-bug",
  "path": "artifacts/tasks/t0042-fix-the-bug.md",
  "before": "ready",
  "after": "in-progress",
  "fields": { "...full new frontmatter..." }
}
```

`before` and `after` are scalar strings here (the status value),
not dicts as in `artifact.updated`. Two emissions per status
update is the cost; the gain is matchers like
`event: artifact.status_changed, after: review` instead of
`event: artifact.updated, changed: [status], after.status: review`.

#### `artifact.validated`

Emitted by `validate_one` and `validate_many` (per
`s0008-artifact-validate-command`). Captures the outcome
regardless of pass/fail.

```json
{
  "ts": "2026-05-07T14:36:00+03:00",
  "event": "artifact.validated",
  "kind": "task",
  "id": "t0042",
  "stem": "t0042-fix-the-bug",
  "path": "artifacts/tasks/t0042-fix-the-bug.md",
  "result": "fail",
  "issues": [
    {"path": "$.assignee", "code": "missing", "message": "required field"}
  ]
}
```

`result` is `pass` or `fail`. `issues` is empty on pass.

#### `hook.fired` / `hook.failed`

Audit trail for the hook layer itself, mirroring OpenStation's
`hook_fired` / `hook_failed`. These give external tools a record
of hook activity without hooks needing to log themselves.

```json
{
  "ts": "2026-05-07T14:35:13+03:00",
  "event": "hook.fired",
  "hook": "notify-on-review",
  "matcher": {"event": "artifact.status_changed", "kind": "task", "after": "review"},
  "action": {"type": "notify", "title": "Review needed: $ART_NAME"},
  "duration_ms": 42,
  "phase": "post"
}
```

```json
{
  "ts": "2026-05-07T14:35:13+03:00",
  "event": "hook.failed",
  "hook": "lint-before-create",
  "matcher": {"event": "artifact.created", "kind": "task"},
  "action": {"type": "shell", "command": "bin/lint-task $ART_PATH"},
  "phase": "pre",
  "blocking": true,
  "error": "exit 1: lint failed",
  "duration_ms": 1200
}
```

The catalog **deliberately omits** `artifact.deleted` —
`artifacts-os` has no delete operation today (per `store.py`).
When delete lands, this spec gets a new event type and a version
bump.

### C2 — Dispatcher (`core/events.py`)

```python
# src/artifacts_os/core/events.py
from __future__ import annotations
from typing import Callable
import sys

EmitterFn = Callable[[str, dict], None]

_emitters: list[EmitterFn] = []

def register_emitter(fn: EmitterFn) -> None:
    """Register an emitter. Each emitter is invoked for every dispatch.
    Order is registration order. Re-registration is allowed (creates a duplicate)."""
    _emitters.append(fn)

def unregister_emitter(fn: EmitterFn) -> None:
    """Remove the first matching registration (no-op if absent).
    Used by tests to clean up."""
    try:
        _emitters.remove(fn)
    except ValueError:
        pass

def _dispatch(event: str, **payload) -> None:
    """Fire `event` to every registered emitter. Failures are caught,
    warned to stderr, and otherwise swallowed — `_dispatch` must never
    propagate an exception out of a CRUD call."""
    for fn in _emitters:
        try:
            fn(event, payload)
        except Exception as e:  # noqa: BLE001 — invariant I1
            sys.stderr.write(f"warning: events emitter failed: {e!r}\n")

def _dispatch_pre(event: str, **payload) -> None:
    """Pre-phase dispatch — used by `create` / `update` *before* the
    file is written. Hooks marked `blocking: true` may raise
    `BlockedByPreHook`, which DOES propagate. All other errors are
    swallowed exactly like `_dispatch`."""
    from artifacts_os.core.errors import BlockedByPreHook
    for fn in _emitters:
        try:
            fn(event, payload)
        except BlockedByPreHook:
            raise
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"warning: pre-emitter failed: {e!r}\n")
```

A new exception `BlockedByPreHook(ArtifactError)` lives in
`core/errors.py`. CLI maps it to a non-zero exit code (proposed:
`EXIT_BLOCKED = 11`).

`core/events.py` knows zero specific event types — it is opaque
glue. The catalog (payload dataclasses, event-type constants)
lives in `events/catalog.py` and is imported only by emitters.

### C3 — Stream Writer (`events/stream.py`)

```python
# src/artifacts_os/events/stream.py
def append(event: str, payload: dict, *, root: Path | None = None) -> None:
    """Append one JSON line to artifacts/logs/events/YYYY-MM-DD.jsonl.
    Falls back to find_vault_root() if root is None.
    Failure prints a warning and returns — never raises."""
```

Behaviour:

- Resolves `root` from `find_vault_root()` if not given.
- Builds the JSON record: `{"ts": now_iso(), "event": event, **payload}`.
- Ensures `artifacts/logs/events/` exists (`mkdir -p`).
- Opens the daily file in `"a"` mode and writes one line.
- Catches every exception, prints a warning, returns.

Uses stdlib only (`json`, `pathlib`, `datetime`).
`events/__init__.py` calls `core.events.register_emitter(append)`
on first import — opt-out via `events.disabled = True` in
settings.

### C4 — Hook Loader (`hooks/loader.py`)

The hook loader is the user-facing reactive surface. It mirrors
OpenStation's hook loader (`docs/hooks.md` § Architecture) in
shape:

```python
# Public API
def load_hooks(root: Path) -> list[Hook]: ...
def match(hooks: list[Hook], event: str, payload: dict, *, phase: str) -> list[Hook]: ...
def run_matched(matched: list[Hook], event: str, payload: dict) -> None: ...
def notify(event: str, payload: dict) -> None:
    """Top-level emitter — registered with core.events.register_emitter."""
```

A `Hook` is a frozen dataclass:

```python
@dataclass(frozen=True)
class Hook:
    name: str
    matcher: Matcher           # parsed from yaml
    action: Action             # union — Shell | Notify | FileDrop
    phase: str                 # "pre" | "post" (default "post")
    blocking: bool             # only meaningful for phase="pre"
    timeout: int               # seconds (default 30)
```

`notify()` filters hooks by event + matcher, then invokes each
action. Ordering is declaration order (yaml array index).
Failures emit a `hook.failed` event via `core.events`. Successes
emit `hook.fired`.

### C5 — Action Types (`hooks/actions.py`)

Three baseline action types ship in v1. Each is a dataclass with
a `run(payload, env)` method:

#### `shell`

```yaml
action:
  type: shell
  command: "bin/notify-review.sh"
  timeout: 30
```

Runs via `subprocess.Popen(['/bin/sh', '-c', cmd])`. Inherits
parent stdio. Environment variables follow the `ART_` namespace
(see § Configuration). Exit code 0 = success; anything else =
failure.

#### `notify`

```yaml
action:
  type: notify
  title: "Task ready: $ART_NAME"
  body: "Status changed to $ART_AFTER_STATUS"
  sound: false
```

Cross-platform desktop notification baseline:

| Platform | Mechanism |
|----------|-----------|
| macOS | `osascript -e 'display notification "$body" with title "$title"'` |
| Linux | `notify-send "$title" "$body"` (libnotify; falls back to terminal bell) |
| Windows | PowerShell `New-BurntToastNotification` (falls back to terminal bell) |
| Fallback | Write `\a` to stderr (terminal bell) |

The implementation tries the platform's preferred command via
`shutil.which`; if absent, falls back to the bell. Failure (no
display, no DBus session) prints a warning and continues.

Extension path: hooks with `type: notify` may set
`mechanism: bell | desktop | osc9 | file` to pin the surface. The
default is `auto` (try desktop, fall back to bell).

#### `file-drop`

```yaml
action:
  type: file-drop
  path: "artifacts/.notifications/{event}-{ts}.json"
  payload: full   # or "summary"
```

Writes the event payload to a file. Useful for external apps that
poll a directory rather than tail the JSONL stream. `path` may
contain `{event}`, `{ts}`, `{kind}`, `{id}` substitutions.

The full action-type registry is open for in-tree extension via a
documented contract — new types are added by registering with
`actions.register("name", ActionClass)`. Third-party plugin
loading is **not** supported in v1 (see § Out of Scope).

### C6 — Settings Extensions

Two extensions, one per new module — each follows the established
extension pattern (see `docs/settings.md`).

```python
# events/settings.py
@dataclass(kw_only=True)
class EventsSettings(Settings):
    enabled: bool = True
    dir: Path | None = None  # default: artifacts/logs/events/

    @classmethod
    def from_base(cls, base: Settings) -> "EventsSettings": ...

# hooks/settings.py
@dataclass(kw_only=True)
class HooksSettings(Settings):
    hooks: list[HookConfig] = field(default_factory=list)

    @classmethod
    def from_base(cls, base: Settings) -> "HooksSettings": ...
```

YAML schema lives under two top-level keys: `events` (always-on
stream tuning) and `hooks` (the opt-in list).

```yaml
layout_version: 1
project:
  name: my-project

events:
  enabled: true                       # default true; set false to disable stream
  dir: artifacts/logs/events          # override directory if needed

hooks:
  - name: notify-on-review
    matcher:
      event: artifact.status_changed
      kind: task
      after: review
    action:
      type: notify
      title: "Review needed: $ART_NAME"

  - name: lint-before-create
    phase: pre
    blocking: true
    matcher:
      event: artifact.created
      kind: task
    action:
      type: shell
      command: "bin/lint-task $ART_PATH"
      timeout: 30
```

Empty `events:` and missing `hooks:` are both valid (means
"defaults" / "no hooks").

### Matcher Schema

Matchers are a flat dict. Every key uses an AND across keys; a
list value uses OR within the key (mirrors the multi-value filter
shape from `s0023`). The matcher value `"*"` on the `event` key
matches any event (catch-all — see Audience 4).

| Matcher key | Source | Example |
|-------------|--------|---------|
| `event` | top-level event type | `artifact.updated`, `"*"` |
| `kind` | payload `kind` | `task`, `[task, spec]` |
| `id` | payload `id` | `t0042` |
| `name` | payload `name` (slug) | `fix-the-bug` |
| `stem` | payload `stem` | `t0042-fix-the-bug` |
| `path.*` | glob on payload `path` | `artifacts/tasks/*` |
| `fields.<key>` | post-update frontmatter | `fields.assignee: developer` |
| `before.<key>` | pre-update value (`artifact.updated`) | `before.status: ready` |
| `after.<key>` | post-update value (`artifact.updated`) | `after.status: review` |
| `before` | scalar pre-value (`artifact.status_changed`) | `before: ready` |
| `after` | scalar post-value (`artifact.status_changed`) | `after: review` |
| `changed` | list membership | `changed: [status]` |
| `result` | from `artifact.validated` | `result: fail` |

Unknown matcher keys raise `ValidationError` at config load time.

### Phases

| Phase | Fires | Failure default | Can block? |
|-------|-------|-----------------|------------|
| `pre` | Before the file is written / replaced | warn | only if `blocking: true` |
| `post` (default) | After the file is on disk | warn | never |

Pre-phase hooks see the **proposed** payload — `before` and
`after` reflect what *would* be written. They run inside the
`_dispatch_pre` call and may raise `BlockedByPreHook` to abort.
Post-phase hooks see the persisted payload.

### C7 — Core Integration Points

Two minimal modifications to `core/store.py`. The
`artifact.status_changed` derivative fires from inside `update`
when applicable — it is dispatched *after* `artifact.updated`.

```python
# create (after schema validation, BEFORE write)
events._dispatch_pre("artifact.created", kind=kind, ..., fields=proposed_fm)
# ... atomic write ...
events._dispatch("artifact.created", kind=kind, ..., fields=final_fm, path=str(path))

# update (after frontmatter merge, BEFORE replace)
events._dispatch_pre("artifact.updated", kind=kind, ..., before=diff_before, after=diff_after, fields=proposed_fm)
# ... os.replace ...
events._dispatch("artifact.updated", kind=kind, ..., before=diff_before, after=diff_after, fields=final_fm)
if "status" in changed_keys:
    events._dispatch(
        "artifact.status_changed",
        kind=kind, id=id_, name=name, stem=stem, path=path,
        before=diff_before["status"], after=diff_after["status"],
        fields=final_fm,
    )
```

`_dispatch` is a no-op when no emitters are registered — `core`
adds three function calls and one new file. No new dependencies.

### C8 — CLI Tail Command

```
artifacts events tail [--since DATE] [--event TYPE] [--follow]
```

Reads the daily JSONL files via a thin reader in `events/`,
filters by event type or timestamp, optionally follows. Useful
for human inspection and as the primary discovery surface for the
audit trail.

## Configuration

Hooks receive event context via `ART_`-prefixed environment
variables (parallel to OpenStation's `OS_` convention):

| Variable | Source | Example |
|----------|--------|---------|
| `ART_EVENT` | event type | `artifact.updated` |
| `ART_KIND` | payload `kind` | `task` |
| `ART_ID` | payload `id` | `t0042` |
| `ART_NAME` | payload `name` (slug) | `fix-the-bug` |
| `ART_STEM` | payload `stem` | `t0042-fix-the-bug` |
| `ART_PATH` | absolute path to artifact | `/proj/artifacts/tasks/t0042-fix-the-bug.md` |
| `ART_VAULT_ROOT` | vault root | `/proj` |
| `ART_BEFORE_STATUS` | only on `artifact.updated` / `artifact.status_changed` | `ready` |
| `ART_AFTER_STATUS` | only on `artifact.updated` / `artifact.status_changed` | `review` |
| `ART_CHANGED` | comma-joined list (`artifact.updated`) | `status,assignee` |
| `ART_PAYLOAD_JSON` | full payload as JSON | `{"kind":"task",...}` |

`ART_PAYLOAD_JSON` is the escape hatch — any field not in the
flat namespace is reachable via `jq` or shell parsing. It is also
the primary contract for the external-async-runtime integration
(Audience 4).

## Worked Examples

### Audience 1 — Agent Reaction

The `architect` agent self-assigns when a new spec-typed task
appears. Configured in `artifacts.yaml`:

```yaml
hooks:
  - name: architect-claims-spec-tasks
    matcher:
      event: artifact.created
      kind: task
      fields.type: spec
      fields.assignee: ""           # only unassigned
    action:
      type: shell
      command: |
        artifacts update "$ART_STEM" --fields '{"assignee": "architect"}'
```

The architect agent itself doesn't need to poll — the hook runs
the CLI which updates the artifact, which fires `artifact.updated`
and `artifact.status_changed` (if status changed), which the
architect's session loop already watches via
`artifacts events tail --event artifact.updated`.

### Audience 2 — User-Defined CLI Hook

User wants a desktop notification whenever any task moves to
`review`, plus a terminal bell for tasks they own:

```yaml
hooks:
  - name: notify-review-ready
    matcher:
      event: artifact.status_changed
      kind: task
      after: review
    action:
      type: notify
      title: "Review needed: $ART_NAME"
      body: "Task $ART_ID is ready for review"

  - name: bell-on-my-review
    matcher:
      event: artifact.status_changed
      kind: task
      after: review
      fields.owner: leonid
    action:
      type: notify
      mechanism: bell
```

Both fire on the same transition; the second piggy-backs on the
first because both are post-phase and non-blocking. The
`artifact.status_changed` matcher is shorter than the equivalent
`artifact.updated` form would be.

### Audience 3 — External App Tailing the Stream

A dashboard tails `artifacts/logs/events/*.jsonl` and renders a
live activity feed. No `artifacts-os` dependency required:

```bash
# external app code (any language)
tail -F artifacts/logs/events/$(date -u +%F).jsonl | \
    while IFS= read -r line; do
        echo "$line" | jq -r '"\(.ts) \(.event) \(.stem // .id)"'
    done
```

Or via the shipped CLI:

```bash
artifacts events tail --follow --event artifact.created --event artifact.updated
```

The JSONL contract is the public interface for external apps —
the schema is documented in C1 and is closed (additions require a
spec revision and version bump).

### Audience 4 — External Async Runtime via Catch-All Hook

An external module (e.g. a job-runner service, a workflow
engine, an LLM-orchestration layer) plugs into `artifacts-os` by
registering one catch-all hook. It owns its own queue, worker
pool, retry/DLQ semantics, and concurrency controls.
`artifacts-os` makes a single guarantee: the hook fires once per
event with the full payload as JSON.

```yaml
hooks:
  - name: forward-all-to-async-runtime
    matcher:
      event: "*"
    action:
      type: shell
      command: |
        my-async-runtime enqueue \
          --event "$ART_EVENT" \
          --payload "$ART_PAYLOAD_JSON"
      timeout: 5
```

The hook does the bare minimum (enqueue + return) so the calling
CRUD doesn't observe latency. All durability, retry, and
concurrency lives downstream:

```
artifacts-os                 my-async-runtime (separate process)
─────────────                ────────────────────────────────────
core/store.update
  └─ _dispatch
       └─ hook fires
            └─ shell: my-async-runtime enqueue ◄── O(append) to runtime's queue
                              │                    runtime is a daemon / cron / k8s job
                              ▼
                       (runtime's worker pool)
                       - retries
                       - DLQ
                       - concurrency
                       - long-running jobs
                       - network calls
```

The runtime can match on `$ART_EVENT` for routing, dispatch by
kind/status/result, and persist its own job state without any
coupling to `artifacts-os` internals. This is the canonical async
integration pattern — `artifacts-os` ships no queue or worker
because every credible substrate (Redis, NATS, file spool,
SQLite, k8s Jobs, Temporal) has different operational tradeoffs
that belong in the runtime, not the library.

## Design Decisions

### DD-1: Three sibling modules (`events/`, `hooks/`, `log/`)

**Choice:** Split the work into two new sibling modules under
`core/`: `events/` for catalog and audit stream, `hooks/` for the
reactive layer. Leave `log/` exactly as `s0004` specifies. Add a
tiny `core/events.py` registration shim for DAG-respecting
dispatch.

**Alternatives considered:**

| Option | Pros | Cons |
|--------|------|------|
| **A. Three modules (chosen)** | Each module owns one concept; matches OpenStation's events/hooks split at module granularity; external app docs point at `events/` alone; `s0004`'s `log/` scope is preserved verbatim | Higher boilerplate — three settings extensions, two new module dirs |
| B. Fold events + hooks into `log/` | One new module surface; reuses `log/`'s stdlib-only constraint | `log/` scope grows from "Logger + LogReader" to "Logger + LogReader + dispatch + audit stream + hooks"; hides the events → hooks dependency at the file level; mixes opt-in operational logging (Logger API) with always-on framework telemetry (audit stream) |
| C. One omnibus `reactive/` module | Fewer module dirs than A | Mixes framework telemetry with user-defined reactions in one namespace; harder to document for external apps |
| D. Inside `core/` | Zero registration plumbing | Violates DAG philosophy — hooks shell out, which is a side-effect concern, not a storage concern; bloats `core` |

**Trade-off:** A has higher boilerplate but each concern lives in
exactly one place. Audit-stream tail commands point at `events/`,
hook authoring docs point at `hooks/`, and `s0004`'s `log/` scope
stays exactly as specified — Logger remains opt-in operational
logging for callers, distinct from the always-on event stream.
The cosmetic cost of one extra directory pales against the
conceptual clarity for users, agents, and external apps.

(This is a v2 reversal of v1's "fold into log/" choice. The v1
analysis weighted module-count cost too heavily; the conceptual
overlap between Logger and the event stream proved illusory —
they share JSONL as a substrate but solve different problems.)

### DD-2: YAML-only hooks (no Python entry points)

**Choice:** Hooks are declared in `artifacts.yaml`. Custom
behaviour goes in shell scripts the hook invokes.

**Alternative:** Allow hooks to specify a Python entry point
(e.g. `action: { type: python, target: my_pkg:my_handler }`)
loaded via `importlib`.

| Aspect | YAML-only (chosen) | YAML + Python entry points |
|--------|--------------------|----------------------------|
| External app contract | Same single source of truth (yaml) | Hook list is yaml + arbitrary Python — external apps need to know both |
| Sandboxing | Trivially scoped via subprocess + `ART_` env | Python runs in-process — must trust the source, can corrupt vault |
| Discovery | One file to read | Plus a Python import graph to walk |
| Power | Bounded by what shell can express (high in practice) | Higher — can hold state, share code |
| `artifacts-os` install footprint | Zero new deps | Adds plugin lifecycle, version pinning concerns |

**Trade-off:** YAML-only loses some convenience for power users
who would rather write Python than shell. It wins everywhere else
— audit, sandbox, install simplicity, and the "external app can
read the same config" requirement. Power users compose the same
behaviour via shell calls into Python (`python -m my_pkg.handler`)
without us owning the loading model.

### DD-3: Pre-phase blocking is opt-in per hook

**Choice:** Default `blocking: false` for `phase: pre`. A hook
must explicitly set `blocking: true` to abort a CRUD call.
Post-phase hooks cannot block at all.

**Alternative:** Pre-phase always blocks on failure (mirrors
OpenStation's `pre` hook behaviour exactly).

**Trade-off:** OpenStation's pre-hooks always block, but
`artifacts-os` is a library, not a CLI-first tool. A library that
silently rejects writes because of a misconfigured pre-hook is
hostile to embedders. Making blocking opt-in keeps the default
safe while preserving the gate-keeping use case for callers who
explicitly want it. The library's invariant ("emission must never
break a CRUD operation") is preserved by default; opting into
breaking it is loud and intentional.

### DD-4: Closed event catalog

**Choice:** Adding a new event type requires a spec revision.
Hooks cannot define new event types.

**Alternative:** Open catalog where any caller can `_dispatch("my.custom.event", ...)`.

**Trade-off:** Closing the catalog gives external apps a stable
contract — they can rely on the JSONL schema documented here.
Open catalogs invite drift and undocumented payloads. The cost is
flexibility for power users, mitigated by the action-type
extension point (see C5) which lets hooks compose new behaviour
without inventing event types.

### DD-5: Async execution is delegated, not in-tree

**Choice:** `artifacts-os` ships only synchronous, in-process
hooks. Async fan-out (queues, retries, DLQ, worker pools) is
out-of-tree, integrated via a catch-all hook that hands events to
an external runtime (Audience 4).

**Alternatives considered:**

| Option | Pros | Cons |
|--------|------|------|
| **A. External runtime via catch-all hook (chosen)** | Zero queue/worker code in the library; users pick whatever substrate fits (Redis, NATS, file spool, SQLite, k8s Jobs, Temporal); operational concerns stay where they belong | One process boundary added per event; users must run their own runtime |
| B. File-spool queue + `artifacts hooks tick` worker shipped in-tree | Self-contained — no external runtime needed | Library owns operational concerns (retry, DLQ, concurrency) it has no business owning; substrate choice is fixed; expands install footprint |
| C. SQLite-backed queue + worker | Better atomicity than file spool | One new dep; same scope-creep argument as B |
| D. Redis / NATS / external broker | Industry-standard substrates | Hard dependency on external infra; out of scope per library philosophy |

**Trade-off:** A pushes a process boundary onto users who want
async, but every credible async substrate has different
operational tradeoffs that belong in the runtime, not the
library. Shipping any in-tree queue forces our choice on every
embedder, and shipping multiple is a maintenance burden the
project shouldn't carry. The catch-all hook is a one-line
integration; the runtime side is exactly as complex as the user
needs it to be.

## Verification

| # | Component | Criterion |
|---|-----------|-----------|
| V1 | C1 | Every event type listed has a JSON schema with `ts`, `event`, and event-specific fields. |
| V2 | C2 | `_dispatch` swallows every emitter exception and prints to stderr (test: register an emitter that raises, observe no exception, observe stderr). |
| V3 | C2 | `core` does not import `events/`, `hooks/`, or `log/` (test: `ast`-walk of `core/*.py` for upward imports returns empty). |
| V4 | C3 | Stream writer creates `artifacts/logs/events/YYYY-MM-DD.jsonl` and appends one valid JSON line per dispatch. |
| V5 | C3 | Stream writer failure (read-only filesystem) prints warning, returns, does not raise. |
| V6 | C4 | Loader rejects unknown matcher keys, missing `name`, missing `action.type`, and treats empty `hooks: []` as no-op. |
| V7 | C4 | `hook.fired` and `hook.failed` events appear in the JSONL stream after each hook run. |
| V8 | C5 | All three action types (`shell`, `notify`, `file-drop`) round-trip via `artifacts.yaml` and execute correctly on the test platform. |
| V9 | C5 | `notify` falls back to terminal bell when no notification daemon is available. |
| V10 | C7 | `store.create` and `store.update` succeed with no hooks configured (default behaviour, zero overhead beyond no-op `_dispatch` calls). |
| V11 | C7 | A pre-phase hook with `blocking: true` that exits non-zero aborts the CRUD operation and leaves the file unchanged. |
| V12 | C7 | A pre-phase hook with `blocking: false` that exits non-zero prints a warning, fires `hook.failed`, and the CRUD operation completes. |
| V13 | C7 | A post-phase hook that exits non-zero never affects the CRUD outcome. |
| V14 | C7 | `artifact.status_changed` is dispatched immediately after `artifact.updated` whenever `status` is in `changed`, and never otherwise (I6). |
| V15 | C8 | `artifacts events tail --since YYYY-MM-DD` returns events from that date forward; `--follow` streams new entries. |
| V16 | All | The four worked examples (agent, user, app, async runtime) work end-to-end against a test vault. |

## Build Sequence

Implementation order — each step is independently testable:

1. **C2 dispatcher** — `core/events.py` with `register_emitter`,
   `unregister_emitter`, `_dispatch`, `_dispatch_pre`, plus the
   `BlockedByPreHook` exception in `core/errors.py`.
2. **C7 core integration** — wire `_dispatch` calls into
   `store.create` and `store.update`, plus the
   `artifact.status_changed` derivative. Tests pass with no
   registered emitters (no behaviour change).
3. **C1 catalog + C3 stream** — `events/catalog.py` (payload
   dataclasses, type constants) and `events/stream.py` (JSONL
   writer). Register on `events` import. Verify JSONL file is
   created on first event.
4. **C8 CLI tail** — `cli/commands/events.py`. Confirms the
   stream is reachable end-to-end.
5. **C6 settings extensions** — `EventsSettings` and
   `HooksSettings` parsing `events:` and `hooks:` from
   `artifacts.yaml`.
6. **C5 actions** — implement `shell`, `notify`, `file-drop`
   under `hooks/actions.py`. Each with platform-fallback tests.
7. **C4 hook loader** — `hooks/loader.py` parsing, matching,
   dispatch. Wire `notify` into `core.events.register_emitter`
   on `hooks` import.
8. **Audit-trail events** — emit `hook.fired` / `hook.failed`
   from C4.
9. **Verification harness** — four end-to-end tests covering
   each worked-example audience (including the async-runtime
   integration).

## Relationship to `log/` and `s0004`

The current `s0004-artifacts-os-log-module` spec defines `Logger`,
`LogReader`, and an event-type list with `artifact.created`,
`artifact.updated`, plus run events. It explicitly notes that
`store` does **not** write log entries by default.

This spec **does not modify** `s0004`'s `log/` scope. `Logger`,
`LogReader`, and the operational log surface remain exactly as
specified. The events surface (catalog + audit stream) lives in
a separate new `events/` module, and the reactive layer lives in
`hooks/`.

After this work lands:

- `Logger` and `LogReader` keep their public API unchanged.
- The event-type list documented in `s0004` § "Event Types"
  becomes the authoritative wire format defined here in C1
  (this spec takes precedence on schema; `s0004` gets a
  cross-reference pointer).
- `store.create` and `store.update` *do* emit events by default
  via `_dispatch` — `s0004`'s "core does not write log entries by
  default" statement is updated to reflect that emission is now a
  two-line core concern routed through `core/events.py`, while
  the operational log (Logger API) remains opt-in for callers.
- New module dirs created by this work:
  - `src/artifacts_os/events/{__init__.py, catalog.py, stream.py, settings.py}`
  - `src/artifacts_os/hooks/{__init__.py, loader.py, matcher.py, actions.py, settings.py}`
- Existing `src/artifacts_os/log/` files are **untouched**.

The implementing task should bump `s0004` to `version: 2`,
mark it `final`, and add a "Superseded sections" pointer at the
top to the relevant sections of this spec — its Logger/LogReader
API is unchanged.

## Out of Scope

This spec deliberately does **not** cover:

- **In-tree async / queued execution.** Hooks run synchronously
  in the calling process. For async fan-out, queue-based workers,
  retry semantics, DLQ, and worker pool management, delegate to
  an external module bound via a catch-all hook (see Audience 4
  worked example and DD-5). `artifacts-os` ships no queue, no
  worker, and no retry primitives.
- **Remote / webhook delivery.** No HTTP, no message queues, no
  cloud notification services. Hooks can shell out to `curl` if
  they need this, or hand off to an external runtime per
  Audience 4.
- **Durable retry semantics.** A failed hook fires once, emits
  `hook.failed`, and is done. No backoff, no DLQ, no delivery
  guarantees beyond "best-effort, locally synchronous".
- **Cross-vault event federation.** Events are scoped to the
  vault they originate in. Multi-vault dashboards aggregate at
  the file-system layer.
- **Threaded hooks.** All hooks run synchronously in the calling
  process. A long-running hook blocks the CRUD call (post-phase)
  or the dispatch call (pre-phase). Use `&` / `nohup` in the
  shell action if you need fire-and-forget locally — for
  anything heavier, use Audience 4.
- **Third-party action plugins.** Action types are registered
  in-tree only. Out-of-tree action types are deferred to a
  follow-up spec — the registry is structured to accommodate
  them, but the loading model is not specified here.
- **Event stream rotation / compaction.** Daily files grow
  unbounded; users manage retention themselves. A future
  `artifacts events compact` command may land separately.
- **Schema-validated payloads at emit time.** The catalog is
  documented in C1 and trusted at the call site (parallel to
  OpenStation's `events.emit`). Validation lives in the spec, not
  the code path.
- **Hook dry-run / test mode.** Diagnostics for misconfigured
  hooks are out of scope; users debug via the JSONL stream and
  `hook.failed` events.

A follow-up implementation task picks up the build sequence
defined above. A separate task for any of the deferred items can
reference this spec's Out of Scope section as the boundary
condition.

## Cross-References

- `s0004-artifacts-os-log-module` — `Logger`/`LogReader` API
  this spec leaves untouched (cross-references the event-type
  table only).
- `s0005-artifacts-os-module-system` — module DAG, into which
  this spec adds two new sibling modules (`events/`, `hooks/`).
- `s0002-artifacts-os-architecture` — atomic-write invariants
  and `store` contracts.
- `s0008-artifact-validate-command` — source of
  `artifact.validated` events.
- `s0010-core-settings-module-spec` — `Settings` extension
  pattern used by `EventsSettings` and `HooksSettings`.
- `s0023-multi-value-filters` — list-as-OR matcher semantics.
- `.openstation/docs/events.md` — prior art for the always-on
  event stream design.
- `.openstation/docs/hooks.md` — prior art for the hook
  configuration model.
