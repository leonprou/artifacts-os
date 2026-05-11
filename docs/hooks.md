# Hooks

Hooks are the opt-in reactive layer: declarative rules in `artifacts.yaml`
that fire shell commands, desktop notifications, or file writes whenever the
vault emits a matching event. The always-on event stream (JSONL audit log and
`artifacts events` CLI) is a separate, independent facility — see
[events.md](events.md). Hooks extend that stream with side-effects; they
do not replace it.

---

## How hooks work

Every CRUD operation emits an event. The hook loader reads the `hooks:` list
from `artifacts.yaml`, matches each hook against the event type and payload,
and runs the action. Two phases are available:

- **`post` (default)** — runs after the file is written. Failures are warned
  to stderr but never abort the operation.
- **`pre`** — runs before the file is written. A `blocking: true` pre-hook
  that fails raises `BlockedByPreHook` and aborts the operation.

Hooks are evaluated in declaration order. Hook meta-events (`hook.fired`,
`hook.failed`) are emitted for each run; a reentrancy guard prevents
catch-all hooks from recursing into themselves.

The full YAML schema (all matcher keys, action fields, env vars) is in
[settings.md § Hooks Section](settings.md#hooks-section).

---

## Worked Examples

### 1. Desktop notification on status change (user workflow)

Send a macOS/Linux notification whenever a task moves to `review`:

```yaml
# artifacts.yaml
hooks:
  - name: notify-review
    matcher:
      event: artifact.status_changed
      kind: task
      after: review
    action:
      type: notify
      title: "Review needed: $ART_STEM"
      body: "Task $ART_ID is waiting for review"
```

`$ART_STEM` and `$ART_ID` are expanded from the `ART_*` environment variables
that hooks receive. On macOS this uses `osascript`; on Linux `notify-send`;
falls back to a terminal bell when no notification daemon is available.

### 2. Agent self-assign via shell hook

An agent script polls for tasks it owns. With hooks it can react immediately:
when a task is created with `assignee: developer`, the agent's inbox script
runs.

```yaml
hooks:
  - name: developer-inbox
    matcher:
      event: artifact.created
      kind: task
      fields.assignee: developer
    action:
      type: shell
      command: "bin/developer-inbox $ART_STEM"
      timeout: 10
```

`bin/developer-inbox` receives the full `ART_*` environment and can read the
artifact at `$ART_PATH` or call `artifacts show $ART_STEM` directly.

### 3. External async runtime via catch-all file-drop

An external service (e.g. a webhook relay) watches a drop directory for new
JSON files. Use a catch-all `file-drop` hook to write every post-phase event
there:

```yaml
hooks:
  - name: drop-all
    matcher:
      event: "*"
    action:
      type: file-drop
      path: "artifacts/.notifications/{event}-{ts}.json"
      payload: full
```

The file name is expanded using `{event}`, `{ts}`, `{kind}`, `{id}`
substitutions. `payload: full` writes the complete event record; `payload:
summary` writes only `event`, `kind`, `id`, `ts`.

The relay process watches `artifacts/.notifications/` (e.g. via `inotifywait`
or `FSEvents`) and forwards payloads to its queue.

### 4. Blocking pre-hook: lint before create

Prevent a malformed task from being written at all:

```yaml
hooks:
  - name: lint-task
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

Because `phase: pre` and `blocking: true`, a non-zero exit from `bin/lint-task`
raises `BlockedByPreHook` and the artifact is never created. Non-blocking
pre-hooks (the default) warn to stderr but allow the operation through.

---

## Environment Variables

Every hook action receives these variables:

| Variable | Content |
|----------|---------|
| `ART_EVENT` | Event type string (e.g. `artifact.status_changed`) |
| `ART_KIND` | Artifact kind |
| `ART_ID` | Artifact ID (e.g. `t0042`) |
| `ART_NAME` | Artifact slug |
| `ART_STEM` | Full stem (`id-name` for numbered kinds) |
| `ART_PATH` | Absolute path to the artifact file |
| `ART_VAULT_ROOT` | Vault root directory |
| `ART_BEFORE_STATUS` | Status before transition (status-change events) |
| `ART_AFTER_STATUS` | Status after transition |
| `ART_CHANGED` | Comma-joined list of changed frontmatter keys |
| `ART_TS` | ISO 8601 UTC timestamp of the event |
| `ART_PAYLOAD_JSON` | Full event payload as JSON (escape hatch) |

---

## Key Patterns

**Narrow matchers first.** Broad catch-all hooks (`event: "*"`) fire on
`hook.fired` / `hook.failed` too — they are shielded by a reentrancy guard
but still impose per-event overhead. Match on `kind` and `event` whenever
possible.

**Pre-hooks for invariants, post-hooks for reactions.** Pre-hooks add
latency to every matched CRUD call. Use them only for hard constraints
(linting, quota checks). Notifications, logging, and async handoffs belong
in post-hooks.

**One hook, one concern.** The YAML list is evaluated in order; split
unrelated concerns into separate named hooks rather than embedding
conditionals in a shell script.

**Cache invalidation.** The hook loader caches `artifacts.yaml` per vault
root. If you edit `artifacts.yaml` while the process is running, call
`artifacts_os.hooks.loader.invalidate_cache()` to force a reload, or restart
the process.

---

## Cross-References

- Full matcher key and action field reference — [settings.md § Hooks Section](settings.md#hooks-section)
- Event types and payload fields — [events.md](events.md)
- Design rationale, invariants, phase semantics — `s0025-artifact-events`
