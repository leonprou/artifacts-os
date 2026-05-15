---
assignee: developer
created: 2026-05-15
id: t0162
kind: task
name: book-pull-item-level-filtering
owner: user
status: done
type: implementation
---

# Book Pull Item-Level Filtering

## Requirements

1. `artifacts book pull <name>` with no items pulls all files — existing behaviour unchanged.
2. `artifacts book pull <name> item1 item2 …` pulls only the matching items.
3. For **flat books**: item matches by filename stem (`architect`) or full filename (`architect.md`).
4. For **recurse books**: item matches by unit folder name (`artifacts-os`, `task`) — all files within the matching unit are included.
5. If any item name is not found in the book, the command errors before writing any files and prints the list of available items (directing the user to `book show <name>`).
6. `--dry-run` respects the item filter.
7. `--json` output respects the item filter.
8. `book show` and `book list` are unchanged — they remain the discovery mechanism.
9. Update `s0029-artbook-mvp-distribution-model` with a new decision entry documenting item-level consumer selection.
10. Update `docs/artbook.md` — add an "Item selection" subsection under the consumer/pull section.
11. Update `cli/README.md` `book pull` synopsis to `artifacts book pull <name> [ITEM …]` and document item semantics per walker mode.

## Verification

- [ ] `artifacts book pull agents` pulls all agent files (regression)
- [ ] `artifacts book pull agents architect developer` writes only `architect.md` and `developer.md`
- [ ] `artifacts book pull agents architect.md` (with extension) works the same as without
- [ ] `artifacts book pull skills artifacts-os` writes only the `artifacts-os/` unit subtree
- [ ] `artifacts book pull kinds task note` writes only `task/` and `note/` units
- [ ] `artifacts book pull agents nonexistent` exits with error and lists available items, writes nothing
- [ ] `--dry-run` with items shows only the filtered planned writes
- [ ] `--json` with items emits only records for filtered files
- [ ] `s0029` has a new decision entry for item-level selection
- [ ] `docs/artbook.md` documents `book pull <name> [items]` with flat vs recurse examples
- [ ] `cli/README.md` synopsis and prose updated