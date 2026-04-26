---
assignee: developer
created: 2026-04-25
id: t0015
kind: task
name: replace-openstation-vault-marker-with-artifacts-yaml
owner: user
started: 2026-04-25
status: done
summary: 'Drop .openstation/ as the vault marker and openstation.yaml as config. Use
  artifacts.yaml at the project root instead.

  '
type: feature
---

# Replace .openstation/ Vault Marker with artifacts.yaml

## Background

The `.openstation/` directory was used as the vault marker because the
artifacts-os vault shared the directory with the openstation task management
tool. Now that storage lives in `artifacts/` directly, we no longer need
`.openstation/` for anything. Using it as a marker couples us to an external
tool we shouldn't depend on.

The new marker: a single `artifacts.yaml` file at the project root.

## What changes and what doesn't

**Changes:**
- Vault detection: look for `artifacts.yaml` file instead of `.openstation/` dir
- `init`: create `artifacts.yaml` instead of `.openstation/openstation.yaml`; stop creating `.openstation/` dir
- All test fixtures that `mkdir(".openstation")` → write a minimal `artifacts.yaml`

**Does not change:**
- `artifacts/` as the storage root (already correct from t0014)
- The `openstation → artifacts` symlink in `init` — keep it; the external openstation CLI tool still needs it for task management

## artifacts.yaml format

Same content as the current `openstation.yaml`, just at a new path:

```yaml
layout_version: 1

project:
  name: "<project-name>"
  alias: "<alias>"

defaults:
  show:
    editor: true
```

---

## Requirements

### 1. `src/artifacts_os/core/vault.py`

Change `find_vault_root` to look for `artifacts.yaml` file instead of `.openstation/` dir:

```python
# before
if (candidate / ".openstation").is_dir():
# after
if (candidate / "artifacts.yaml").is_file():
```

Update the docstring to match.

### 2. `src/artifacts_os/cli/commands/init.py`

- Already-initialised check: `(target / ".openstation").is_dir()` → `(target / "artifacts.yaml").is_file()`
- Remove the `.openstation/` dir creation block entirely
- Write `artifacts.yaml` at `target / "artifacts.yaml"` instead:
  ```python
  (target / "artifacts.yaml").write_text(
      _default_settings(name, alias), encoding="utf-8"
  )
  ```
- Keep the `openstation → artifacts` symlink creation unchanged
- Update print output: replace `.openstation/openstation.yaml` line with `artifacts.yaml`

### 3. Tests

**`tests/core/test_vault.py`** (lines 7, 12)
- `(tmp_path / ".openstation").mkdir()` → `(tmp_path / "artifacts.yaml").write_text("")`

**`tests/core/conftest.py`** (line 42)
- `(root / ".openstation").mkdir(parents=True)` → `(root / "artifacts.yaml").write_text("")`

**`tests/core/test_store.py`** (line 48)
- Same replacement

**`tests/core/test_registry.py`** (lines 42, 66, 81, 89)
- Same replacement

**`tests/cli/conftest.py`** (line 37)
- Same replacement

**`tests/cli/test_init.py`**
- Line 15: `assert (tmp_path / ".openstation").is_dir()` → `assert (tmp_path / "artifacts.yaml").is_file()`
- Line 16: remove assertion for `.openstation/openstation.yaml`
- Lines 43, 54: `(... / ".openstation" / "openstation.yaml").read_text()` → `(... / "artifacts.yaml").read_text()`
- Line 64: `assert (target / ".openstation").is_dir()` → `assert (target / "artifacts.yaml").is_file()`

### 4. Docs

**`docs/2026-04-20-artifacts-os-design.md`**
- Layout diagram: replace `.openstation/  # vault marker` with `artifacts.yaml    # vault marker`
- Prose: update `find_vault_root` description from `.openstation/` to `artifacts.yaml`

**`artifacts/specs/s0002-artifacts-os-architecture.md`**
- `find_vault_root` docstring: `.openstation/` → `artifacts.yaml`
- Walk loop condition: update to `(candidate / "artifacts.yaml").is_file()`
- `make_vault` fixture doc: `.openstation/` marker → `artifacts.yaml`

**`README.md`**
- Line 24 comment: `.openstation/` → `artifacts.yaml`

**`CLAUDE.md`**
- Vault marker row: `.openstation/openstation.yaml` → `artifacts.yaml`

---

## Verification

- [ ] `find_vault_root` detects a vault by presence of `artifacts.yaml`, not `.openstation/` dir
- [ ] `artifacts init` creates `artifacts.yaml` at the project root
- [ ] `artifacts init` does NOT create a `.openstation/` directory
- [ ] `artifacts init` still creates the `openstation → artifacts` symlink
- [ ] Already-initialised check uses `artifacts.yaml`
- [ ] All test fixtures write `artifacts.yaml` instead of creating `.openstation/` dir
- [ ] `tests/cli/test_init.py` assertions match new layout
- [ ] All tests pass: `pytest`
- [ ] `docs/2026-04-20-artifacts-os-design.md` updated
- [ ] `artifacts/specs/s0002-artifacts-os-architecture.md` updated
- [ ] `README.md` updated
- [ ] `CLAUDE.md` vault marker row updated
- [ ] No remaining `.openstation` references in `src/` or `tests/`