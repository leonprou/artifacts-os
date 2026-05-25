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

## Bundle Form (hook bundles)

> **Recommended form for new hooks.** The `artifacts.yaml hooks:` list is
> deprecated; see [Migrating from the legacy hooks list](#migrating-from-the-legacy-hooks-list).

A hook bundle is a directory under `artifacts/hooks/<slug>/` that contains a
manifest file (`<slug>.md`) and any sibling scripts or helpers the action needs.
Bundles are registered in git alongside your artifacts and survive distro re-pulls
unchanged.

### Bundle layout

```
artifacts/hooks/
  auto-commit/
    auto-commit.md        # manifest (frontmatter + optional prose)
    action.sh             # +x sibling; referenced by action.command
  notify-review/
    notify-review.md      # inline-only — no siblings
  lint-task/
    lint-task.md
    lint-task.py          # +x sibling
    helpers.py            # non-+x helper sourced by lint-task.py
  .active/                # operator-managed activation state (see "Promoting hooks")
    auto-commit -> ../auto-commit/auto-commit.md
```

### Manifest frontmatter

```yaml
---
kind: hook
name: auto-commit
host: artifacts-os            # artifacts-os | openstation | <custom>
matcher:
  event: artifact.status_changed
  after: done
action:
  type: shell
  command: ./action.sh        # relative paths resolve against the bundle dir
  timeout: 30
phase: post
blocking: false
---

Body text is operator-facing documentation and is ignored by the loader.
```

### Sibling-file path resolution

When `action.command` is a relative path (does not start with `/`), it is
resolved against the **manifest's parent directory** at load time.

| `command:` in manifest | Resolved path |
|------------------------|---------------|
| `./action.sh` | `<vault>/artifacts/hooks/<slug>/action.sh` |
| `action.sh` | `<vault>/artifacts/hooks/<slug>/action.sh` |
| `helpers/run.sh` | `<vault>/artifacts/hooks/<slug>/helpers/run.sh` |
| `/usr/local/bin/foo` | `/usr/local/bin/foo` (absolute — unchanged) |

**Divergence from the legacy yaml form:** `artifacts.yaml` hooks resolve
relative commands against the **vault root** (their historical behaviour).
Bundle hooks resolve against the bundle directory instead. This means the
same relative path has different meanings in the two forms. When migrating
a hook, adjust any relative paths in `action.command` to be bundle-relative.

### `source:` distinction

The `hook.fired` and `hook.failed` events carry an optional `source` key:

| Value | Meaning |
|-------|---------|
| `"yaml"` | Hook loaded from `artifacts.yaml hooks:` list (legacy) |
| `"bundle"` | Hook loaded from `artifacts/hooks/.active/` (bundle form) |

Use `source` in `artifacts events --filter hook.fired` output or downstream
consumers to tell the two forms apart.

### Host dispatch

The `host:` field in the manifest controls which loader fires the hook:

| `host:` value | behaviour |
|--------------|-----------|
| `artifacts-os` | This loader fires the hook. |
| `openstation` | Loaded and listed in `artifacts hooks list`; **never fired** by artifacts-os. |
| Any other value | Loaded and listed; a one-line warning is printed once per process; never fired. |

Legacy `artifacts.yaml` hooks have no `host:` field and are implicitly treated
as `host: artifacts-os`.

---

## Promoting hooks

Bundles must be *promoted* before they fire. Promotion creates a symlink in
`artifacts/hooks/.active/` that the loader reads. The `.active/` directory is
tracked in git so activation choices are PR-reviewable.

```bash
# See all available bundles and their activation state.
artifacts hooks list

# Activate a bundle (creates .active/my-hook → ../my-hook/my-hook.md).
artifacts hooks promote my-hook

# Deactivate without deleting the bundle.
artifacts hooks demote my-hook

# Inspect a bundle — frontmatter, sibling files, recent events.
artifacts hooks show my-hook

# Remove dangling .active/ entries (targets deleted by a re-pull).
artifacts hooks list --prune
```

### Promote / demote semantics

**`artifacts hooks promote <slug> [--force]`**

1. Verifies that `artifacts/hooks/<slug>/<slug>.md` exists.
2. Creates `artifacts/hooks/.active/<slug>` → `../<slug>/<slug>.md` (relative symlink).
3. Idempotent: if the symlink already points at the same target, exits 0 with
   "already active: …".
4. Divergent target: exits 1 with an error unless `--force` is given, in which
   case the old entry is replaced.
5. Emits `hook.promoted` event.

On systems where symlinks are not supported, `promote` falls back to a `.json`
stub file `{"target": "../<slug>/…"}` which the loader also understands.

**`artifacts hooks demote <slug>`**

Removes `artifacts/hooks/.active/<slug>` (or the `.json` stub). No-op when
not active. Emits `hook.demoted` event.

### Re-pull preservation

`artifacts book pull <hook-book>` writes bundle directories under
`artifacts/hooks/` but never touches `artifacts/hooks/.active/`. Activation
state survives a re-pull intact.

If a re-pull removes a bundle that was promoted, the `.active/<slug>` symlink
becomes dangling. The loader silently skips it and emits `hook.skipped`; run
`artifacts hooks list --prune` to clean up.

### Stale symlink policy

| Scenario | Behaviour |
|----------|-----------|
| `artifacts hooks list` | Shows `dangling` in the `active` column |
| `artifacts hooks promote` | Refuses to promote against a missing target |
| `artifacts hooks list --prune` | Removes all dangling entries; emits `hook.demoted` with `reason: "prune"` |
| Loader (`notify()`) | Silently skips; emits `hook.skipped` |

---

## `artifacts hooks` CLI

All verbs output a Rich table by default; add `-j` / `--json` for JSON output.

### `hooks list`

```
artifacts hooks list [--host HOST] [--active | --inactive]
                     [--source yaml|bundle] [--tail [N]] [-j]
                     [--prune [--dry-run]]
```

Default columns: `name`, `host`, `active`, `phase`, `event`, `source`.

`active` values: `yes` (symlink resolves), `dangling` (target missing), `no`
(no `.active/` entry).

| Flag | Effect |
|------|--------|
| `--host HOST` | Filter by `host:` value |
| `--active` | Show only hooks whose `.active/` entry resolves |
| `--inactive` | Show only hooks without a resolving `.active/` entry |
| `--source yaml\|bundle` | Restrict to one source |
| `--tail [N]` | Show last N results (default 50 with bare flag) |
| `-j` | JSON array output |
| `--prune` | Remove dangling `.active/` entries |
| `--dry-run` | With `--prune`: show what would be removed without removing it |

**JSON shape (`-j`):**

```json
[
  {
    "name": "auto-commit",
    "host": "artifacts-os",
    "phase": "post",
    "blocking": false,
    "timeout": 30,
    "source": "bundle",
    "active": "yes",
    "matcher": {"event": "artifact.status_changed"}
  }
]
```

### `hooks show <slug>`

```
artifacts hooks show <slug> [-j]
```

Renders: manifest frontmatter table, sibling-file listing (path, `+x`, size),
resolved active state, and a tail of the last 5 `hook.fired` / `hook.failed`
events from the JSONL log.

**JSON shape (`-j`):**

```json
{
  "frontmatter": {"kind": "hook", "name": "auto-commit", …},
  "active": "yes",
  "siblings": [{"path": "action.sh", "executable": true, "size": 120}],
  "recent_events": [{"event": "hook.fired", "hook": "auto-commit", …}]
}
```

### `hooks promote <slug> [--force]`

```
artifacts hooks promote <slug> [--force] [-j]
```

Creates `.active/<slug>` → `../<slug>/<slug>.md`. See [Promote / demote
semantics](#promote--demote-semantics).

**JSON shape (`-j`):**

```json
{"slug": "auto-commit", "active_path": "…/.active/auto-commit",
 "target": "../auto-commit/auto-commit.md",
 "was_stub": false, "was_idempotent": false}
```

### `hooks demote <slug>`

```
artifacts hooks demote <slug> [-j]
```

Removes the `.active/<slug>` entry. No-op when not active.

**JSON shape (`-j`):**

```json
{"slug": "auto-commit", "removed": true}
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | User error (unknown slug, divergent promote without `--force`) |
| `2` | Configuration error (broken manifest, malformed `.active/`) |
| `3` | Filesystem error (permissions) |

---

## Migrating from the legacy hooks list

The `artifacts.yaml hooks:` list is deprecated. The deprecation notice is
printed once to stderr on first load when the list is non-empty; set
`ARTIFACTS_HOOKS_LEGACY_QUIET=1` to suppress it.

To migrate a yaml-defined hook to a bundle:

1. `artifacts create --kind hook my-hook-name`
   (or create `artifacts/hooks/my-hook/my-hook.md` manually).
2. Copy your `matcher:` and `action:` blocks into the manifest frontmatter;
   add `host: artifacts-os`.
3. If `action.command` was a vault-root-relative path (e.g. `bin/foo`), move
   the script into the bundle directory and update `command: ./bin/foo`
   (or `command: bin/foo`).
4. `artifacts hooks promote my-hook`
5. Remove the entry from `artifacts.yaml hooks:`.

No automated migration tool ships in this release.

---

## Cross-References

- Full matcher key and action field reference — [settings.md § Hooks Section](settings.md#hooks-section)
- Event types and payload fields — [events.md](events.md)
- Bundle kind registration — `artifacts/kinds/hook/kind.json`
- Artbook distribution for hooks — [artbook.md](artbook.md)
- Design rationale, invariants, phase semantics — `s0025-artifact-events`
- Hooks-via-artbook spec — `s0032-hooks-via-artbook-distribution`

---

## Distributing hooks via artbook

Hooks can be shipped from a distro to consumers using an artbook book entry
with `kind: hook`.  This is the recommended path for distributing
project-wide hooks (e.g. `auto-commit`, `auto-verify`).

```yaml
# artbook.yaml in the distro
books:
  - name: os-hooks
    src: artifacts/hooks/
    kind: hook
    description: Project lifecycle hooks.
```

Effects of `kind: hook`:

- `recurse: true` is auto-set; each direct subdirectory of `src` becomes a
  bundle landing under the consumer's `artifacts/hooks/<slug>/`.
- `promote:` is forbidden — activation is consumer-owned.
- One `hook.pulled` event is emitted per book per pull.
- `.active/` is never touched by pull, so previously promoted hooks survive
  a re-pull intact.

Consumer flow:

```bash
artifacts book pull os-hooks            # land the bundles (inert)
artifacts hooks list                    # see what's available
artifacts hooks promote auto-commit     # activate (creates .active/auto-commit)
artifacts book pull os-hooks            # re-pull — bundle refreshed, .active/ preserved
```

See [artbook.md § Hook Books](artbook.md#hook-books) for the full
manifest reference and `s0032-hooks-via-artbook-distribution` for the
design.
