---
name: artifacts.list.open-tasks
description: List open (ready) tasks, sorted by name.
---

Shows all tasks with `status: ready`, sorted alphabetically. Equivalent to
`artifacts list --kind task --status ready`, but uses the `open-tasks` view
so columns and sort order are always in sync with `artifacts.yaml`.

```bash
artifacts list --view open-tasks
```
