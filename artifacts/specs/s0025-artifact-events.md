---
kind: spec
id: s0025
name: artifact-events
status: draft
task: "[[t0130-spec-for-artifact-events-with]]"
created: 2026-05-07
---

# Artifact Events

A two-layer reactive surface for `artifacts-os` vault operations:
an **always-on event stream** that records what happened, and an
**opt-in subscriber layer** that lets agents, users, and external
apps react. Both live in the existing `log/` module, never block
CRUD operations, and configure per-vault from `artifacts.yaml`.

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
   our Python API.

OpenStation already proves the value of this with its
`events`/`hooks` split (`.openstation/docs/events.md`,
`.openstation/docs/hooks.md`). The same shape applies cleanly to
`artifacts-os` — telemetry is always on; reactions are
declarative, opt-in, and bounded.

The hard constraints:

- Emission must never break a CRUD operation.
- Subscribers must never silently corrupt the vault — failures
  default to warnings, opt-in to blocking.
- The work must respect the dependency DAG (`core → log → ai`).
  `core/store.py` cannot import `log`.
- Subscriber config must live on disk so external apps and agents
  can read the same source of truth.

## Architecture

Two parallel layers built on a shared dispatch point in `core`:

```
                     ┌──────────────────────────┐
                     │  core/store.py           │
                     │  create() / update()     │
                     └─────────────┬────────────┘
                                   │ _dispatch(event_type, **payload)
                                   ▼
                ┌───────── core/events.py ─────────┐
                │  registered emitters (callables) │
                │  failures → warn, never raise    │
                └────────┬───────────────┬─────────┘
                         │               │
                         ▼               ▼
              ┌──────────────────┐  ┌──────────────────────────┐
              │ log/stream.py    │  │ log/subscribers.py        │
              │  always-on       │  │  opt-in, declarative      │
              │  JSONL daily     │  │  matchers + actions       │
              │  ./logs/events/  │  │  (shell / notify / file)  │
              └──────────────────┘  └──────────────────────────┘
```

### Runtime Flow — `store.create`

```
validate kind / schema / fields
─── pre-subscribers fire ───            ← opt-in; failure aborts only if blocking=true
write file (O_CREAT | O_EXCL)
parse final artifact
─── core/events._dispatch("artifact.created", …) ───
        │
        ├── log/stream.append(...)      ← always-on, JSONL
        └── log/subscribers.notify(...) ← post-phase, async-by-default
```

`update` follows the same shape with `artifact.updated`. The body
write is the irrevocable point — pre-subscribers run **before**
it, post-subscribers and the stream append run **after**.

### Layer Separation

| Aspect | Event stream (`log/stream.py`) | Subscribers (`log/subscribers.py`) |
|--------|-------------------------------|-------------------------------------|
| Purpose | Framework telemetry | User/agent-defined reactions |
| Configuration | Always on, no config | `artifacts.yaml` `subscribers:` key |
| Can block CRUD | Never | Only when `blocking: true` (pre-phase) |
| Failure impact | stderr warning | Pre-blocking: abort; otherwise warning |
| Output | `artifacts/logs/events/YYYY-MM-DD.jsonl` | stdout/stderr, OS notification, file drop |
| Audience | External apps tailing the file | Agents and users running the vault |
| Schema | Documented event catalog (this spec) | Same payload, plus matcher filters |

The event stream is the source of truth; subscribers are a
filter-and-react view on top of the same dispatch call. A failed
subscriber never prevents a stream entry. A failed stream append
prints a warning and does not block subscribers.

### Module Placement Decision

The work folds into `log/` rather than introducing a new module.
See **DD-1** for the trade-off analysis. The `log/` module's
existing scope (JSONL operation log, `s0004-artifacts-os-log-module`)
already covers the always-on stream — events.md in OpenStation
takes the same shape. Subscribers extend that scope with a
declarative reaction layer, keeping the dependency DAG intact:

```
core ─┬─ views ─┬─ cli
      │         └─ tui
      └─ log    ─┬─ ai
                 (events/, stream/, subscribers/ all live here)
```

`core/events.py` (new) holds only the registration table and the
non-throwing dispatch function. It has zero dependencies on `log`.
`log` registers its emitters at import time. `core` works fine
without `log` imported (no events fire, no subscribers run, CRUD
is unaffected).

### Decoupling Pattern — Registered Emitters

`core` cannot import `log` (DAG violation). The dispatch must
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

`log/__init__.py` calls `register_emitter(stream.append)` and
`register_emitter(subscribers.notify)` on first import. Tests can
register a capturing emitter without touching `log`.

### Invariants

| # | Invariant |
|---|-----------|
| I1 | A failed emitter never propagates — `_dispatch` catches every exception. |
| I2 | The stream entry is independent of subscriber outcomes — both run, both fail or succeed independently. |
| I3 | `core` imports nothing from `log`. |
| I4 | Pre-phase subscribers are the **only** mechanism that can abort a CRUD operation, and only when explicitly marked `blocking: true`. |
| I5 | The event payload schema is closed — adding fields requires bumping `artifact_events_version` in `artifacts.yaml`. |

## Components

| # | Component | Location | Purpose |
|---|-----------|----------|---------|
| C1 | Event catalog | This spec § Event Catalog | Closed enumeration of event types and payload schemas |
| C2 | Dispatcher | `src/artifacts_os/core/events.py` | Registration table, non-throwing dispatch |
| C3 | Stream writer | `src/artifacts_os/log/stream.py` | Always-on JSONL append to `artifacts/logs/events/YYYY-MM-DD.jsonl` |
| C4 | Subscriber loader | `src/artifacts_os/log/subscribers.py` | Parse `subscribers:` from `artifacts.yaml`, match events, run actions |
| C5 | Subscriber actions | `src/artifacts_os/log/actions.py` | Shell, notify, file-drop action runners |
| C6 | Settings extension | `src/artifacts_os/log/settings.py` | `LogSettings.from_base` reads `subscribers:` and `events:` sections |
| C7 | Core integration points | `src/artifacts_os/core/store.py` (modified) | Two `_dispatch` call sites in `create` / `update` |
| C8 | CLI tail command | `src/artifacts_os/cli/commands/events.py` | `artifacts events tail` for human inspection |

### C1 — Event Catalog

The catalog is closed. New event types require a spec revision
and a `version` bump in the on-disk frontmatter of every entry.

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
post-update frontmatter for subscribers that prefer the complete
view.

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

#### `subscriber.fired` / `subscriber.failed`

Audit trail for the subscriber layer itself, mirroring
OpenStation's `hook_fired` / `hook_failed`. These give external
tools a record of subscriber activity without subscribers needing
to log themselves.

```json
{
  "ts": "2026-05-07T14:35:13+03:00",
  "event": "subscriber.fired",
  "subscriber": "notify-on-review",
  "matcher": {"event": "artifact.updated", "kind": "task", "after.status": "review"},
  "action": {"type": "notify", "title": "Review needed: $ART_NAME"},
  "duration_ms": 42,
  "phase": "post"
}
```

```json
{
  "ts": "2026-05-07T14:35:13+03:00",
  "event": "subscriber.failed",
  "subscriber": "lint-before-create",
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
    file is written. Subscribers marked `blocking: true` may raise
    `BlockedByPreSubscriber`, which DOES propagate. All other errors
    are swallowed exactly like `_dispatch`."""
    from artifacts_os.core.errors import BlockedByPreSubscriber
    for fn in _emitters:
        try:
            fn(event, payload)
        except BlockedByPreSubscriber:
            raise
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"warning: pre-emitter failed: {e!r}\n")
```

A new exception `BlockedByPreSubscriber(ArtifactError)` lives in
`core/errors.py`. CLI maps it to a non-zero exit code (proposed:
`EXIT_BLOCKED = 11`).

### C3 — Stream Writer (`log/stream.py`)

```python
# src/artifacts_os/log/stream.py
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

Uses stdlib only (`json`, `pathlib`, `datetime`) — consistent
with the `log/` module's stdlib-only constraint.

### C4 — Subscriber Loader (`log/subscribers.py`)

The subscriber loader is the user-facing reactive surface. It
mirrors OpenStation's hook loader (`docs/hooks.md` § Architecture)
in shape:

```python
# Public API
def load_subscribers(root: Path) -> list[Subscriber]: ...
def match(subs: list[Subscriber], event: str, payload: dict, *, phase: str) -> list[Subscriber]: ...
def run_matched(matched: list[Subscriber], event: str, payload: dict) -> None: ...
def notify(event: str, payload: dict) -> None:
    """Top-level emitter — registered with core.events.register_emitter."""
```

A `Subscriber` is a frozen dataclass:

```python
@dataclass(frozen=True)
class Subscriber:
    name: str
    matcher: Matcher           # parsed from yaml
    action: Action             # union — Shell | Notify | FileDrop
    phase: str                 # "pre" | "post" (default "post")
    blocking: bool             # only meaningful for phase="pre"
    timeout: int               # seconds (default 30)
```

`notify()` filters subscribers by event + matcher, then invokes
each action. Ordering is declaration order (yaml array index).
Failures emit a `subscriber.failed` event via `core.events`.
Successes emit `subscriber.fired`.

### C5 — Action Types (`log/actions.py`)

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

Extension path: subscribers with `type: notify` may set
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

The full action-type registry is open for extension via a
documented contract — new types are added by registering with
`actions.register("name", ActionClass)`. Third-party extension
is **not** supported in v1 (see § Out of Scope).

### C6 — Settings Extension

`LogSettings` follows the established extension pattern
(see `docs/settings.md`):

```python
@dataclass(kw_only=True)
class LogSettings(Settings):
    subscribers: list[SubscriberConfig] = field(default_factory=list)
    events_dir: Path | None = None  # default: artifacts/logs/events/
    events_enabled: bool = True

    @classmethod
    def from_base(cls, base: Settings) -> "LogSettings":
        ...
```

YAML schema lives under two top-level keys: `events` (always-on
stream tuning) and `subscribers` (the opt-in list).

```yaml
layout_version: 1
project:
  name: my-project

events:
  enabled: true                       # default true; set false to disable stream
  dir: artifacts/logs/events          # override directory if needed

subscribers:
  - name: notify-on-review
    matcher:
      event: artifact.updated
      kind: task
      after.status: review
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

Empty `events:` and missing `subscribers:` are both valid (means
"defaults" / "no subscribers").

### Matcher Schema

Matchers are a flat dict. Every key uses an AND across keys; a
list value uses OR within the key (mirrors the multi-value filter
shape from `s0023`).

| Matcher key | Source | Example |
|-------------|--------|---------|
| `event` | top-level event type | `artifact.updated` |
| `kind` | payload `kind` | `task`, `[task, spec]` |
| `id` | payload `id` | `t0042` |
| `name` | payload `name` (slug) | `fix-the-bug` |
| `stem` | payload `stem` | `t0042-fix-the-bug` |
| `path.*` | glob on payload `path` | `artifacts/tasks/*` |
| `fields.<key>` | post-update frontmatter | `fields.assignee: developer` |
| `before.<key>` | pre-update value | `before.status: ready` |
| `after.<key>` | post-update value | `after.status: review` |
| `changed` | list membership | `changed: [status]` |
| `result` | from `artifact.validated` | `result: fail` |

Unknown matcher keys raise `ValidationError` at config load time.

### Phases

| Phase | Fires | Failure default | Can block? |
|-------|-------|-----------------|------------|
| `pre` | Before the file is written / replaced | warn | only if `blocking: true` |
| `post` (default) | After the file is on disk | warn | never |

Pre-phase subscribers see the **proposed** payload — `before` and
`after` reflect what *would* be written. They run inside the
`_dispatch_pre` call and may raise `BlockedByPreSubscriber` to
abort. Post-phase subscribers see the persisted payload.

### C7 — Core Integration Points

Two minimal modifications to `core/store.py`:

```python
# create (after schema validation, BEFORE write)
events._dispatch_pre("artifact.created", kind=kind, ..., fields=proposed_fm)
# ... atomic write ...
events._dispatch("artifact.created", kind=kind, ..., fields=final_fm, path=str(path))

# update (after frontmatter merge, BEFORE replace)
events._dispatch_pre("artifact.updated", kind=kind, ..., before=diff_before, after=diff_after, fields=proposed_fm)
# ... os.replace ...
events._dispatch("artifact.updated", kind=kind, ..., before=diff_before, after=diff_after, fields=final_fm)
```

`_dispatch` is a no-op when no emitters are registered — `core`
adds two function calls and one new file. No new dependencies.

### C8 — CLI Tail Command

```
artifacts events tail [--since DATE] [--event TYPE] [--follow]
```

Reads the daily JSONL files via `log.LogReader` (per `s0004`),
filters by event type or timestamp, optionally follows. Useful
for human inspection and as the primary discovery surface for the
audit trail.

## Configuration

Subscribers receive event context via `ART_`-prefixed environment
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
| `ART_BEFORE_STATUS` | only on `artifact.updated` | `ready` |
| `ART_AFTER_STATUS` | only on `artifact.updated` | `review` |
| `ART_CHANGED` | comma-joined list | `status,assignee` |
| `ART_PAYLOAD_JSON` | full payload as JSON | `{"kind":"task",...}` |

`ART_PAYLOAD_JSON` is the escape hatch — any field not in the
flat namespace is reachable via `jq` or shell parsing.

## Worked Examples

### Audience 1 — Agent Reaction

The `architect` agent self-assigns when a new spec-typed task
appears. Configured in `artifacts.yaml`:

```yaml
subscribers:
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

The architect agent itself doesn't need to poll — the subscriber
runs the CLI which updates the artifact, which fires
`artifact.updated`, which the architect's session loop already
watches via `artifacts events tail --event artifact.updated`.

### Audience 2 — User-Defined CLI Hook

User wants a desktop notification whenever any task moves to
`review`, plus a terminal bell for tasks they own:

```yaml
subscribers:
  - name: notify-review-ready
    matcher:
      event: artifact.updated
      kind: task
      after.status: review
    action:
      type: notify
      title: "Review needed: $ART_NAME"
      body: "Task $ART_ID is ready for review"

  - name: bell-on-my-review
    matcher:
      event: artifact.updated
      kind: task
      after.status: review
      fields.owner: leonid
    action:
      type: notify
      mechanism: bell
```

Both fire on the same transition; the second piggy-backs on the
first because both are post-phase and non-blocking.

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

## Design Decisions

### DD-1: Fold into `log/` rather than a sibling module

**Choice:** Add `stream.py`, `subscribers.py`, `actions.py`, and
`settings.py` under `src/artifacts_os/log/`. Reuse `log/`'s
stdlib-only constraint and existing dependency edge.

**Alternatives considered:**

| Option | Pros | Cons |
|--------|------|------|
| **A. Fold into `log/` (chosen)** | Reuses JSONL infrastructure; respects DAG; one settings extension; matches `s0004` scope; minimal new surface area | Grows `log/` from "writer + reader" to "writer + reader + dispatch + subscribers" — bigger module |
| B. New `events/` sibling module | Cleaner separation of concerns; named after what it does | Adds a new node to the DAG (where? under `core` like `log`?); duplicates `log/`'s JSONL writer; two settings extensions for a closely-related feature |
| C. Inside `core/` | Zero registration plumbing | Violates DAG philosophy — subscribers shell out, which is a side-effect concern, not a storage concern; bloats `core` |

**Trade-off:** Option B is the conceptually cleanest split, but
the practical cost (new module, duplicate JSONL handling, new
settings class) outweighs the cosmetic win when the stream and
subscribers share 90% of their dispatch logic. `log/`'s docstring
gets a one-line scope expansion: "Writes operation logs and the
event stream; loads subscribers."

### DD-2: YAML-only subscribers (no Python entry points)

**Choice:** Subscribers are declared in `artifacts.yaml`. Custom
behaviour goes in shell scripts the subscriber invokes.

**Alternative:** Allow subscribers to specify a Python entry
point (e.g. `action: { type: python, target: my_pkg:my_handler }`)
loaded via `importlib`.

| Aspect | YAML-only (chosen) | YAML + Python entry points |
|--------|--------------------|----------------------------|
| External app contract | Same single source of truth (yaml) | Subscriber list is yaml + arbitrary Python — external apps need to know both |
| Sandboxing | Trivially scoped via subprocess + ART_ env | Python runs in-process — must trust the source, can corrupt vault |
| Discovery | One file to read | Plus a Python import graph to walk |
| Power | Bounded by what shell can express (high in practice) | Higher — can hold state, share code |
| `artifacts-os` install footprint | Zero new deps | Adds plugin lifecycle, version pinning concerns |

**Trade-off:** YAML-only loses some convenience for power users
who would rather write Python than shell. It wins everywhere else
— audit, sandbox, install simplicity, and the "external app can
read the same config" requirement. Power users compose the same
behaviour via shell calls into Python (`python -m my_pkg.handler`)
without us owning the loading model.

### DD-3: Pre-phase blocking is opt-in per subscriber

**Choice:** Default `blocking: false` for `phase: pre`. A
subscriber must explicitly set `blocking: true` to abort a CRUD
call. Post-phase subscribers cannot block at all.

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
Subscribers cannot define new event types.

**Alternative:** Open catalog where any caller can `_dispatch("my.custom.event", ...)`.

**Trade-off:** Closing the catalog gives external apps a stable
contract — they can rely on the JSONL schema documented here.
Open catalogs invite drift and undocumented payloads. The cost is
flexibility for power users, mitigated by the action-type
extension point (see C5) which lets subscribers compose new
behaviour without inventing event types.

## Verification

| # | Component | Criterion |
|---|-----------|-----------|
| V1 | C1 | Every event type listed has a JSON schema with `ts`, `event`, and event-specific fields. |
| V2 | C2 | `_dispatch` swallows every emitter exception and prints to stderr (test: register an emitter that raises, observe no exception, observe stderr). |
| V3 | C2 | `core` does not import `log` (test: `ast`-walk of `core/*.py` for `import artifacts_os.log` returns empty). |
| V4 | C3 | Stream writer creates `artifacts/logs/events/YYYY-MM-DD.jsonl` and appends one valid JSON line per dispatch. |
| V5 | C3 | Stream writer failure (read-only filesystem) prints warning, returns, does not raise. |
| V6 | C4 | Loader rejects unknown matcher keys, missing `name`, missing `action.type`, and empty `subscribers:` lists with `[]` (treats `[]` as no-op). |
| V7 | C4 | `subscriber.fired` and `subscriber.failed` events appear in the JSONL stream after each subscriber run. |
| V8 | C5 | All three action types (`shell`, `notify`, `file-drop`) round-trip via `artifacts.yaml` and execute correctly on the test platform. |
| V9 | C5 | `notify` falls back to terminal bell when no notification daemon is available. |
| V10 | C7 | `store.create` and `store.update` succeed with no subscribers configured (default behaviour, zero overhead beyond two no-op `_dispatch` calls). |
| V11 | C7 | A pre-phase subscriber with `blocking: true` that exits non-zero aborts the CRUD operation and leaves the file unchanged. |
| V12 | C7 | A pre-phase subscriber with `blocking: false` that exits non-zero prints a warning, fires `subscriber.failed`, and the CRUD operation completes. |
| V13 | C7 | A post-phase subscriber that exits non-zero never affects the CRUD outcome. |
| V14 | C8 | `artifacts events tail --since YYYY-MM-DD` returns events from that date forward; `--follow` streams new entries. |
| V15 | All | The three worked examples (agent, user, app) work end-to-end against a test vault. |

## Build Sequence

Implementation order — each step is independently testable:

1. **C2 dispatcher** — `core/events.py` with `register_emitter`,
   `unregister_emitter`, `_dispatch`, `_dispatch_pre`, plus the
   `BlockedByPreSubscriber` exception in `core/errors.py`.
2. **C7 core integration** — wire two `_dispatch` calls into
   `store.create` and `store.update`. Tests pass with no
   registered emitters (no behaviour change).
3. **C3 stream writer** — `log/stream.py`. Register on `log`
   import. Verify JSONL file is created on first event.
4. **C8 CLI tail** — `cli/commands/events.py`. Confirms the
   stream is reachable end-to-end.
5. **C6 settings extension** — `LogSettings.from_base` parsing
   `events:` and `subscribers:` from `artifacts.yaml`.
6. **C5 actions** — implement `shell`, `notify`, `file-drop`.
   Each with platform-fallback tests.
7. **C4 subscriber loader** — `log/subscribers.py` parsing,
   matching, dispatch. Wire `notify` into
   `core.events.register_emitter` on `log` import.
8. **Audit-trail events** — emit `subscriber.fired` /
   `subscriber.failed` from C4.
9. **Verification harness** — three end-to-end tests covering
   each worked-example audience.

## Relationship to `log/` and `s0004`

The current `s0004-artifacts-os-log-module` spec defines `Logger`,
`LogReader`, and an event-type list with `artifact.created`,
`artifact.updated`, plus run events. It explicitly notes that
`store` does **not** write log entries by default.

This spec **extends** `s0004` rather than replacing it. After
this work lands:

- `Logger` and `LogReader` keep their public API unchanged.
- The event types listed in `s0004` Table § "Event Types" become
  the authoritative wire format defined here in C1 (this spec
  takes precedence on schema; `s0004` gets a cross-reference
  pointer).
- `store.create` and `store.update` *do* emit events by default
  via `_dispatch` — `s0004`'s "core does not write log entries by
  default" statement is updated to reflect that emission is now a
  two-line core concern, while logging remains opt-in for
  callers using `Logger` directly.
- New files `stream.py`, `subscribers.py`, `actions.py`,
  `settings.py` join `writer.py` (Logger) and `reader.py`
  (LogReader) under `src/artifacts_os/log/`.

The implementing task should bump `s0004` to `version: 2`,
mark it `final`, and add a "Superseded sections" pointer at the
top to the relevant sections of this spec. The
`src/artifacts_os/log/__init__.py` docstring updates its
`Implementation spec` reference to point to this spec for the
event/subscriber surface and keeps the Logger/Reader pointer to
`s0004`.

## Out of Scope

This spec deliberately does **not** cover:

- **Remote / webhook delivery.** No HTTP, no message queues, no
  cloud notification services. Subscribers can shell out to
  `curl` if they need this.
- **Durable retry semantics.** A failed subscriber fires once,
  emits `subscriber.failed`, and is done. No backoff, no DLQ, no
  delivery guarantees beyond "best-effort, locally synchronous".
- **Cross-vault event federation.** Events are scoped to the
  vault they originate in. Multi-vault dashboards aggregate at
  the file-system layer.
- **Async / threaded subscribers.** All subscribers run
  synchronously in the calling process. A long-running
  subscriber blocks the CRUD call (post-phase) or the dispatch
  call (pre-phase). Use `&` / `nohup` in the shell action if you
  need backgrounding.
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
- **Subscriber dry-run / test mode.** Diagnostics for
  misconfigured subscribers are out of scope; users debug via
  the JSONL stream and `subscriber.failed` events.

A follow-up implementation task picks up the build sequence
defined above. A separate task for any of the deferred items can
reference this spec's Out of Scope section as the boundary
condition.

## Cross-References

- `s0004-artifacts-os-log-module` — `Logger`/`LogReader` API
  this spec extends.
- `s0005-artifacts-os-module-system` — module DAG and `log/`
  scope.
- `s0002-artifacts-os-architecture` — atomic-write invariants
  and `store` contracts.
- `s0008-artifact-validate-command` — source of
  `artifact.validated` events.
- `s0010-core-settings-module-spec` — `Settings` extension
  pattern used by `LogSettings`.
- `s0023-multi-value-filters` — list-as-OR matcher semantics.
- `.openstation/docs/events.md` — prior art for the always-on
  event stream design.
- `.openstation/docs/hooks.md` — prior art for the subscriber /
  hook configuration model.
