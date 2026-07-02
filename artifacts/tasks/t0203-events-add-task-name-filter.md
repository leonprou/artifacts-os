---
created: 2026-06-11
id: t0203
kind: task
name: events-add-task-name-filter
owner: user
priority: medium
status: backlog
type: feature
---

# events: add --task <name> filter

## Why

Filed from openstation Phase 2 M5 (events delegation, open-station
`[[t0471-m5-events-delegation-delegate-to]]`). Downstream spec ref:
open-station `s2068-openstation-module-system` § 4c / FQ #3.

openstation implements per-task event filtering as a post-process
wrapper (`cli/commands/events.py`) because `artifacts events` lacks
a task filter. Native support removes the wrapper.

## Requirements

- `artifacts events list --task <name>` filters events to those
  whose `task` field matches (exact or id-prefix, consistent with
  `show` resolution).
- Works with `--follow` as well.

## Verification

- [ ] `artifacts events list --task <existing-task>` returns only
      that task's events.
- [ ] Filter composes with the existing `--type` flag.
