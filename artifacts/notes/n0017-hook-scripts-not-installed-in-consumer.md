---
id: n0017
name: hook-scripts-not-installed-in-consumer
kind: note
status: open
created: 2026-05-18
summary: >
  openstation.yaml references bin/hooks/* scripts that are never copied into
  the consumer project, causing post-transition hook failures on first use.
---

## Context

Integration session: elephant-words project (`/Users/leonid/Documents/elephant-words`).

User ran `os st t0004` and selected `ready`. The status transition succeeded and the task
was written, but immediately after:

```
/bin/sh: bin/hooks/auto-start: No such file or directory
error: hook failed: bin/hooks/auto-start (exit 127)
```

The full session flow:

```
t0004-add-game-designer-agent: current status is backlog
  1) ready
  2) rejected
select> 1
✓ t0004-add-game-designer-agent: backlog → ready
info: updated /Users/leonid/Documents/elephant-words/openstation/tasks/t0004-add-game-designer-agent.md
/bin/sh: bin/hooks/auto-start: No such file or directory
error: hook failed: bin/hooks/auto-start (exit 127)
```

## Root Cause

`openstation.yaml` in elephant-words has four post-transition hooks configured:

```yaml
hooks:
  StatusTransition:
  - matcher: '*→done'
    command: bin/hooks/auto-commit
    phase: post
  - matcher: '*→review'
    command: bin/hooks/auto-verify
    phase: post
  - matcher: '*→ready'
    command: bin/hooks/auto-start
    phase: post
  - matcher: '*→done'
    command: bin/hooks/auto-unblock
    phase: post
```

All four commands use a relative path (`bin/hooks/`). The hook dispatch in
`openstation/hooks/dispatch.py` executes them with `subprocess.Popen(command, shell=True)`
using the process's working directory — i.e., the project root.

The hook scripts live in the `open-station` *source repo* at
`/Users/leonid/workspace/os/open-station/bin/hooks/` but are **never copied** to
the consumer project during `openstation init` or any other setup step.

Confirmed: `ls /Users/leonid/Documents/elephant-words/bin/` → `no bin dir` before fix.

## Fix Applied (Consumer Side)

Manually copied the four referenced hooks from the open-station source and made them executable:

```bash
mkdir -p /Users/leonid/Documents/elephant-words/bin/hooks
cp /Users/leonid/workspace/os/open-station/bin/hooks/auto-{start,commit,verify,unblock} \
   /Users/leonid/Documents/elephant-words/bin/hooks/
chmod +x /Users/leonid/Documents/elephant-words/bin/hooks/*
```

Files now present at paths matching `openstation.yaml` configuration.

## Classification

**artifacts-os fix** — escalate to product (`pdm`).

This is not a consumer misconfiguration. The `openstation.yaml` is presumably
generated or templated by openstation itself (it pre-existed in elephant-words),
and a new adopter has no documented path to obtain the hook scripts it references.

## Signal for Product

Three distinct papercuts bundled in this one failure:

1. **Silent install gap** — `openstation init` creates `.openstation/`, `.claude/`,
   and `openstation/` directories but does not create `bin/hooks/`. The hook scripts
   that `openstation.yaml` references are never materialized in the consumer project.

2. **Error message obscures cause** — `/bin/sh: bin/hooks/auto-start: No such file or
   directory` followed by `error: hook failed` gives the user no hint that these scripts
   were supposed to be installed. A better message: `hook script not found — run
   openstation init to install bin/hooks/`.

3. **Post-hook failure vs. success confusion** — The transition *succeeded* (status was
   written, ✓ line printed, info line printed) but then `error:` appears. The UX suggests
   the whole command failed when only the post-hook did. Exit code / terminal color should
   distinguish "transition succeeded, post-hook failed" from "transition aborted by pre-hook".

4. **No cross-project sharing** — The canonical hook scripts live in the open-station
   source repo. There is no package-level path resolution, no `OS_OPENSTATION_HOME`
   env var, and no `openstation hook <name>` subcommand. Every consumer project must
   carry its own copy. This makes hook updates (bug fixes to `auto-commit`, etc.) a
   manual sync across all consumer projects.

   Confirmed: `openstation/hooks/dispatch.py` passes `OS_TASK_NAME`, `OS_OLD_STATUS`,
   `OS_NEW_STATUS`, `OS_TASK_FILE`, `OS_VAULT_ROOT` to hooks — no install-path variable.

## Out of Scope (Not Designing)

Not proposing a fix mechanism here. Options (absolute path resolution, bundled hook
installer, `openstation doctor` suggestion) are for architect + product to weigh.

---

## Resolution (2026-05-24)

Closed by [[s0032-hooks-via-artbook-distribution]] §8 and
[[t0184-add-artbook-kind-hook-book]].

Hooks are now distributable as artbook books with `kind: hook`.  A distro
declares its hook registry once:

```yaml
- name: os-hooks
  src: artifacts/hooks/
  kind: hook
```

Consumers run `artifacts book pull os-hooks` to land the full bundle
directories (manifest + sibling scripts) under their `artifacts/hooks/`.
They activate hooks explicitly via `artifacts hooks promote <slug>`; the
`.active/` directory survives subsequent re-pulls.

The original failure mode (script referenced in `openstation.yaml` but
absent in consumer) no longer applies: scripts ship inside the bundle,
and the bundle is what gets pulled.

**Evidence:** `tests/integration/test_hooks_via_artbook.py` — end-to-end
test covering author → pull → list → promote → fire → re-pull → still fires,
including assertions on `hook.pulled` events and `hook.fired` payloads
carrying `source: "bundle"`.
