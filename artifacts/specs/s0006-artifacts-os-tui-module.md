---
kind: spec
name: artifacts-os-tui-module
status: draft
created: 2026-04-20
task: "[[0001-migrate-docs-specs-to-openstation]]"
agent: manual
id: s0006
---

# artifacts-os: tui Module

High-level spec for `artifacts_os.tui`.

## Purpose

Interactive terminal browser over vault artifacts. Lets users navigate,
filter, and inspect artifacts without leaving the terminal. Complements
`cli` (batch/scriptable) with a live, keyboard-driven interface.

## Dependencies

- `artifacts_os` (core)
- `artifacts_os.views` — column layout and field formatting
- `rich>=13`
- `textual>=0.50`

## Entry Point

```python
from artifacts_os.tui import run_browser

run_browser(registry)  # blocks until user quits
```

Also exposable as a CLI sub-command (`artifacts tui`) once the `cli`
module supports it.

## Screen Model

Two screens in the initial version:

### Browser Screen (default)

Displays a filterable, scrollable list of artifacts.

| Area | Content |
|------|---------|
| Header | App name, active kind, active filter summary |
| Body | Artifact table using `views.render_table` column layout |
| Footer | Key binding hints |

**Interactions:**

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move selection |
| `Enter` | Open Detail screen for selected artifact |
| `f` | Open filter bar (kind, status, assignee) |
| `ESC` | Clear filter / go back |
| `q` | Quit |
| `/` | Search (partial name match) |
| `r` | Refresh (re-scan vault) |

### Detail Screen

Displays full artifact content for the selected item.

| Area | Content |
|------|---------|
| Header | Artifact id, kind, status |
| Body | Frontmatter fields table + markdown body (scrollable) |
| Footer | Key binding hints |

**Interactions:**

| Key | Action |
|-----|--------|
| `ESC` / `b` | Back to Browser |
| `↑` / `↓` | Scroll body |
| `e` | Open in `$EDITOR` (suspends TUI, resumes on exit) |

## Column Layout

Browser columns come from `views.default_columns(kind_def)` which reads
`KindDef.meta["columns"]`. The filter bar populates from
`KindDef.statuses` (for status filter) and `KindDef.meta` filterable
fields (schema TBD in views spec).

## Scope Boundary

- **In:** screen navigation, keyboard interaction, live vault refresh,
  artifact browsing and inspection
- **Out:** editing artifact content (delegates to `$EDITOR`), running
  agents, argument parsing

## Deferred

| Item | Notes |
|------|-------|
| Filter bar field schema | Blocked on `views` columns/filters spec |
| Markdown body rendering in Detail | Evaluate `rich.Markdown` vs raw text |
| Status-change action from TUI | Requires `actions` module or direct `update` call |
| Multi-pane layout | Post-MVP |
