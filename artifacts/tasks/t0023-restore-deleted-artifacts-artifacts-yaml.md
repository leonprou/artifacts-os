---
kind: task
id: t0023
name: restore-deleted-artifacts-artifacts-yaml
type: implementation
status: done
assignee: developer
owner: project-manager
created: 2026-04-26
priority: urgent
summary: >
  Restore the artifacts/artifacts.yaml vault marker that was
  accidentally deleted in commit b1d2fec, breaking the artifacts
  CLI in this repo.
started: 2026-04-26
completed: 2026-04-26
---

# Restore Deleted `artifacts/artifacts.yaml` Vault Marker

## Background

Commit `b1d2fec` ("upgrade architect and project-manager to opus-4-7,
add auto-commit hook") deleted `artifacts/artifacts.yaml` with the
note *"vault marker relocated"*. **No relocation actually
happened** — the code still treats `artifacts/artifacts.yaml` as
the vault marker:

- `src/artifacts_os/core/vault.py:11,15` — `find_vault_root` walks up
  looking for `artifacts/artifacts.yaml`
- `src/artifacts_os/cli/commands/init.py:104,116,135` — `init`
  refuses if it exists, creates it on bootstrap, and prints the
  path in the success output
- `CLAUDE.md` documents `artifacts/artifacts.yaml` as the marker

Result: every CLI command in this repo now fails with
`error: not in an artifacts-os project`. This is the only file the
deletion affected — the other changes in `b1d2fec` (agent model
upgrades, auto-commit hook, `bin/os-dispatch`) are legitimate and
must stay.

This is a one-file restore, not a code change.

## Root cause hypothesis

The auto-commit hook introduced in the same commit may have been
overzealous, or the human committer believed the marker had been
moved when it had not. Either way, the fix is to put the file back.

---

## Requirements

### 1. Restore the file

```bash
git checkout 8ea0105 -- artifacts/artifacts.yaml
```

Commit `8ea0105` is the commit that originally added the marker.
The file content is exactly:

```yaml
layout_version: 1

project:
  name: "artifacts-os"
  created: "2026-04-20"
```

If `git checkout` against the historical commit is unavailable,
write the same content directly.

### 2. Verify nothing else is broken

Confirm the rest of the codebase still treats this path as the
marker — no code or doc claims a different location. A quick grep:

```bash
grep -rn "artifacts.yaml" src/ docs/ CLAUDE.md .openstation/docs/ artifacts/specs/
```

All hits should reference `artifacts/artifacts.yaml`. If anything
points at a different path, raise it as a follow-up — do **not**
silently change it in this task.

### 3. Commit

A single atomic commit:

```
fix: restore artifacts/artifacts.yaml vault marker

The marker was accidentally deleted in b1d2fec ("vault marker
relocated") but no relocation was made — find_vault_root and
init still reference this path. Restoring the file unblocks the
artifacts CLI in this repo.
```

---

## Out of Scope

- Investigating or patching the auto-commit hook (`bin/hooks/auto-commit`)
  that may have caused the over-broad deletion. File a separate
  task if root cause warrants it.
- Relocating the vault marker. If a future relocation is desired,
  it is a deliberate, larger change that updates `vault.py`, `init.py`,
  `CLAUDE.md`, and the design doc together — not this hot-fix.
- Re-verifying t0020/t0021/t0022 — they completed before the
  deletion and are not affected.

---

## Verification

- [ ] `artifacts/artifacts.yaml` exists with the expected 5-line content
- [ ] `git log -- artifacts/artifacts.yaml` shows continuity (re-add commit on top of `8ea0105` add and `b1d2fec` delete)
- [ ] `artifacts kinds` (run from this repo root) executes successfully and prints the kinds table
- [ ] `artifacts list -k task -q` (or any other CLI command) no longer prints `error: not in an artifacts-os project`
- [ ] `pytest` — full suite passes
- [ ] No other files were modified in the fix commit
- [ ] `grep -rn "artifacts.yaml" src/ docs/ CLAUDE.md` shows only references to `artifacts/artifacts.yaml` (no stale alternate path)

## Progress

### 2026-04-26 — developer
> time: 22:47

Restored artifacts/artifacts.yaml via git checkout 8ea0105; all 150 tests pass; CLI unblocked; commit d95f9c4.

## Findings

Restored `artifacts/artifacts.yaml` via `git checkout 8ea0105 -- artifacts/artifacts.yaml`. The file content matches the spec exactly (5 lines, `layout_version: 1`, project name/created). Commit `d95f9c4` contains exactly one file change. All 150 tests pass and the `artifacts kinds` / `artifacts list` CLI commands work correctly. Grep confirms every reference in `src/`, `docs/`, `CLAUDE.md`, and specs still points to `artifacts/artifacts.yaml` — no stale alternate paths.

## Verification Report

*Verified: 2026-04-26 by project-manager*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `artifacts/artifacts.yaml` exists with expected 5-line content | PASS | `cat` shows `layout_version: 1` + project block, 5 lines exactly |
| 2 | `git log` shows add → delete → re-add continuity | PASS | `8ea0105` (add) → `b1d2fec` (delete) → `d95f9c4` (re-add) |
| 3 | `artifacts kinds` runs successfully | PASS | Prints the 4-kind table; no error output |
| 4 | CLI no longer prints "not in an artifacts-os project" | PASS | `artifacts list -k task -q` returns task names |
| 5 | `pytest` — full suite passes | PASS | 150 passed in 3.21s |
| 6 | No other files modified in the fix commit | PASS | `d95f9c4` stat: `artifacts/artifacts.yaml | 5 +++++  1 file changed` |
| 7 | Grep shows only `artifacts/artifacts.yaml` references | PASS | All hits in `src/`, `docs/`, `CLAUDE.md` use the canonical path |

### Summary

7 passed, 0 failed. CLI is unblocked. Ready for `done`.
