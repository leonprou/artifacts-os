---
kind: kind
name: hook
description: >
  A hook bundle: a directory containing a manifest (the slug .md file)
  and optional sibling scripts or helpers. Hooks subscribe to vault events
  and run actions (shell commands, notifications, file writes) when the
  matcher conditions are satisfied.
agent: manual
---

# Hook Kind

Hook bundles live under `artifacts/hooks/<slug>/`. Each bundle contains:

- **`<slug>.md`** — the manifest file (frontmatter: kind, name, host, matcher, action, phase, blocking, timeout).
- Optional sibling files — shell scripts, helpers, or any supporting assets.
  Relative `action.command` paths resolve against this directory at load time.

## Directory layout

```
artifacts/hooks/
  my-hook/
    my-hook.md        # manifest
    action.sh         # sibling script (optional)
    helpers/
      util.sh         # nested helper (optional)
```

## Activation

A hook bundle must be *promoted* to `.active/` before it fires:

```bash
artifacts hooks promote my-hook
```

This creates `artifacts/hooks/.active/my-hook` → `../my-hook/my-hook.md`.

To stop firing a hook without deleting the bundle:

```bash
artifacts hooks demote my-hook
```

See `docs/hooks.md` for the full bundle form, promotion model, and CLI reference.
