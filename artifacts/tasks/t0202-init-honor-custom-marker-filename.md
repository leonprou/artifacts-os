---
created: 2026-06-11
id: t0202
kind: task
name: init-honor-custom-marker-filename
owner: user
priority: high
status: backlog
type: feature
---

# init: honor custom marker filename (env or --marker-name flag)

## Why

Filed from openstation Phase 2 (downstream consumer). **Priority:
HIGH — a correctness gap, not just ergonomics.** Authoritative
downstream spec: open-station `s2068-openstation-module-system`
§ 13.4 (v4).

`artifacts init` always writes `artifacts.yaml` at the vault root
and ignores `ARTIFACTS_MARKER_FILENAME` (observed in v0.4.0).
Downstream projects that embed artifacts-os under a different
settings filename (openstation uses `openstation.yaml`) must rename
the marker after the subprocess returns — a fragile post-init hack.

**Motivating regression:** open-station
`[[t0473-m7-init-delegation-wrapper-over]]` (M7 init delegation) —
its verify report found `openstation init` produced `artifacts.yaml`
at root instead of the configured marker; the env var was set on the
subprocess but upstream ignored it, forcing a post-subprocess rename
in the openstation overlay.

## Requirements

- `artifacts init` honors `ARTIFACTS_MARKER_FILENAME` env var
  **or** a `--marker-name <filename>` flag (flag preferred; env
  acceptable).
- Discovery (`find_root`) honors the same override so init and
  discovery agree.

## Verification

- [ ] `ARTIFACTS_MARKER_FILENAME=custom.yaml artifacts init` (or
      `artifacts init --marker-name custom.yaml`) produces
      `custom.yaml`, not `artifacts.yaml`.
- [ ] Discovery finds a vault marked with the custom filename.
