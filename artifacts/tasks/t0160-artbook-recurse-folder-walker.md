---
kind: task
id: t0160
name: artbook-recurse-folder-walker
type: implementation
status: done
assignee: developer
owner: user
parent: "[[t0150-artbook-distribution-model]]"
created: 2026-05-15
started: 2026-05-15
completed: 2026-05-15
---

# Artbook Recurse Folder Walker (D26)

## Goal

Implement **D26** in [[s0029-artbook-mvp-distribution-model]] — a
`recurse: bool = False` field on `Book` that makes the artbook
walker descend `src/`'s direct subdirectories and ship each unit's
subtree intact. Enables the skills book to land as **one** entry
instead of N entries.

## Why

The skills source layout is `<skill_name>/SKILL.md` (folder-of-folders).
The current flat walker (D20) returns zero files from `src/.../skills/`
because it `iterdir()`s files only. Today the workaround is one book
entry per skill (Option 2a in [[n0014-books-integration-roadmap]]),
which churns the manifest on every skill addition. D26 collapses the
manifest to a single `name: skills` entry that auto-picks-up new
units.

## Scope

Five surfaces. Tests follow each.

### Manifest parser (`src/artifacts_os/artbook/manifest.py`)

1. Add `recurse: bool = False` to the `Book` dataclass.
2. Parse `recurse:` from YAML. Reject non-bool values with a clear
   `ManifestError`.
3. Reject the combination `recurse: true` + `files: [...]` —
   mutually exclusive (D26). Error: "book '<name>' cannot set
   both `recurse: true` and `files:`".

### Placement (`src/artifacts_os/artbook/placement.py`)

4. Change `_select_files` return type from `list[Path]` to
   `list[tuple[Path, Path]]` — each entry is
   `(absolute_source, path_relative_to_src_dir)`. Existing flat
   walker and allowlist branches return `(file, Path(file.name))`.
5. Add the D26 recurse branch when `book.recurse` is `True`:
   - Enumerate direct subdirectories of `src_dir`. Skip dotfiles
     (`.foo`), dotted directories (`.git`), and names in
     `_RECURSE_EXCLUDE_DIRS = {"__pycache__"}`.
   - For each unit, `rglob("*")` and yield every regular file,
     skipping at any depth: dotfiles, dotted directories,
     `__pycache__/`, and files with suffixes in
     `_RECURSE_EXCLUDE_SUFFIXES = {".pyc", ".pyo"}`.
   - Loose files directly under `src_dir/` (siblings of
     subdirectories) are silently ignored.
   - `rel_path` = `src_file.relative_to(src_dir)`.
6. Update `_copy_book` to consume `(src, rel)` tuples:
   - Compute `dest_file = dest / rel`.
   - `dest_file.parent.mkdir(parents=True, exist_ok=True)` before
     writing (recurse may need nested dirs).
   - Per-file vault-escape guard remains (write-time `is_relative_to`
     check, D25).

### CLI surface (`src/artifacts_os/cli/commands/book.py`)

7. `book list` — when a book has `recurse=True`, render a small
   marker next to its name or in the Description column (e.g.
   prepend `(recurse) ` to Description). Implementation choice;
   keep it lightweight.
8. `book show` — for recurse books, group the Contents listing by
   unit:

   ```
   Contents (2 units, 4 files):

     artifacts-os/
       SKILL.md
       __init__.py

     release-changelog/
       SKILL.md
       __init__.py
   ```

   For non-recurse books, the existing flat listing is unchanged.
9. `--json` output for `book show` on recurse books — `contents`
   becomes a list of unit objects:

   ```json
   "contents": [
     {"unit": "artifacts-os", "files": ["SKILL.md", "__init__.py"]},
     {"unit": "release-changelog", "files": ["SKILL.md", "__init__.py"]}
   ]
   ```

   For non-recurse books, `contents` stays a flat list of filenames.
10. `--json` output for `book list` — include the `recurse` field on
    each book object so callers can branch.

### Local distro manifest

11. Replace the two existing skill entries (`skill-artifacts-os`,
    `skill-release-changelog`) in this repo's `artbook.yaml` with a
    single `skills` book using `recurse: true`:

    ```yaml
    - name: skills
      src: src/artifacts_os/ai/claude/skills/
      dest: .claude/skills/
      description: Skills that teach Claude how to use artifacts-os.
      recurse: true
    ```

12. Verify with `artifacts book show skills` and
    `artifacts book pull skills --dry-run` that the recurse walker
    finds the two existing units and excludes `__pycache__/`.

### Tests

13. `tests/artbook/test_manifest.py` — recurse parsing, default
    `False`, rejection of non-bool values, rejection of
    `recurse + files`.
14. `tests/artbook/test_placement.py` — recurse walker over a
    synthetic folder-of-folders fixture: ships nested files,
    preserves relative paths, excludes `__pycache__/` and `*.pyc`,
    ignores loose root files, descends multiple levels deep within
    a unit.
15. `tests/artbook/test_pull.py` — end-to-end recurse pull writes
    nested files to the expected destinations; atomic-write +
    overwrite semantics unchanged.
16. `tests/cli/test_book.py` — `book show` grouped output for
    recurse mode; `--json` shape; `book list` recurse marker.

## Out of scope

- Per-unit pull (`artifacts book pull skills/<unit>`) — §10 seam,
  separate task.
- `tree_files:` allowlist that combines with `recurse` — §10 seam.
- Walk depth > 1 unit-level (e.g. `<category>/<name>/SKILL.md`).

## Depends on

- [[t0158-implement-artbook-v2-schema]] — v2 schema (`src`/`dest`,
  no `type:`) is the foundation D26 extends.

## Downstream

- [[n0014-books-integration-roadmap]] — Phase 2 decision is
  superseded once D26 lands; the manifest collapses to one
  `skills` book.

## Verification

- [x] `Book.recurse` defaults to `False`; v1-shaped manifests
      (no `recurse:`) parse without changes.
- [x] Manifest parser rejects `recurse: 1` / `recurse: "true"`
      with a non-bool error.
- [x] Manifest parser rejects `recurse: true` combined with
      `files: [...]` with a clear mutual-exclusion error.
- [x] Placement walker over a recurse-mode fixture ships nested
      files, preserves relative paths, and excludes
      `__pycache__/`, `*.pyc`, dotfiles, and loose root files.
- [x] `book show skills` renders the grouped unit/file view.
- [x] `book show skills --json` returns the unit-grouped
      `contents` shape; `book list --json` includes `recurse` on
      each book.
- [x] This repo's `artbook.yaml` collapses to a single `skills`
      book; `artifacts book show skills` lists 2 units and
      `__pycache__` is absent from the output.
- [x] `pytest tests/artbook/ tests/cli/test_book.py` passes
      (97/97 — original 78 still green + 19 new D26 cases).

## Verification Report

*Verified: 2026-05-15*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `Book.recurse` defaults to `False`; v1 manifests parse unchanged | PASS | `manifest.py:39` declares `recurse: bool = False`; parser only reads `recurse` when key is present (`manifest.py:120`). |
| 2 | Parser rejects non-bool `recurse` values | PASS | `manifest.py:121-127` checks `isinstance(raw_recurse, bool)` and raises `ManifestError`. |
| 3 | Parser rejects `recurse: true` + `files:` combination | PASS | `manifest.py:130-134` raises mutual-exclusion `ManifestError`. |
| 4 | Recurse walker preserves relative paths and excludes `__pycache__/`, `*.pyc`, dotfiles, loose root files | PASS | `placement.py:86-111` implements the spec branch with `_RECURSE_EXCLUDE_DIRS` and `_RECURSE_EXCLUDE_SUFFIXES` filters; `tests/artbook/test_placement.py` has 19 recurse references covering each rule. |
| 5 | `book show skills` renders grouped unit/file view | PASS | Live `artifacts book show skills` output: "Contents (2 units, 4 files):" followed by `artifacts-os/` and `release-changelog/` groups; rendering at `book.py:318-343`. |
| 6 | `book show --json` returns unit-grouped `contents`; `book list --json` includes `recurse` | PASS | Live JSON: `"contents": [{"unit": "artifacts-os", "files": ["SKILL.md", "__init__.py"]}, ...]`; `book list --json` includes `"recurse": true` on the skills book and `"recurse": false` on others (via `dataclasses.asdict`). |
| 7 | `artbook.yaml` collapses to a single `skills` book; 2 units, no `__pycache__` | PASS | `artbook.yaml:45-49` is a single `skills` entry with `recurse: true`; live `book show skills` lists exactly the `artifacts-os` and `release-changelog` units, with `__pycache__` absent from output. |
| 8 | `pytest tests/artbook/ tests/cli/test_book.py` passes 97/97 | PASS | Live run: `97 passed in 3.82s`. |

### Summary

8 passed, 0 failed. All verification criteria confirmed against the implementation, live CLI output, and the full test suite.

## References

- Spec: [[s0029-artbook-mvp-distribution-model]] §3.2, §3.3, §4.3, §7.3, **D26**
- Parent: [[t0150-artbook-distribution-model]]
- Roadmap context: [[n0014-books-integration-roadmap]] Phase 2
