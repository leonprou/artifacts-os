# Migration Guide

## v0.3.0 — Vault Marker Relocation

Starting with v0.3.0, the vault marker file has moved from
`artifacts/artifacts.yaml` to `artifacts.yaml` (project root,
sibling of the `artifacts/` data directory).

### Why

The marker now lives next to `pyproject.toml`, `CLAUDE.md`, and
other top-level project config files, where it is immediately
visible.  The doubled `artifacts/artifacts.yaml` token is
eliminated from call sites and documentation.

### Manual migration procedure

For each existing vault, run:

```bash
cd <vault-root>
git mv artifacts/artifacts.yaml ./artifacts.yaml
git commit -m "chore: relocate artifacts.yaml to project root"
```

That is the entire migration.  The contents of `artifacts.yaml`
are byte-identical before and after the move — no edits to the
YAML body are required.

### Verification

```bash
artifacts list --kind task
```

The command should print the same list it did before the move.

If it errors with "not in an artifacts-os vault", the marker is
not at `<vault-root>/artifacts.yaml` — re-check the path.

### Backward compatibility

This is a **hard cutover** (pre-1.0).  The legacy location
`artifacts/artifacts.yaml` is no longer recognised.  Existing
vaults must be migrated with the one-line procedure above.
