---
kind: task
id: t0181
name: add-directory-storage-primitive-to
type: implementation
status: done
assignee: developer
owner: architect
parent: "[[t0178-ship-hooks-via-artbook-distribution]]"
created: 2026-05-22
started: 2026-05-22
completed: 2026-05-24
---

# Add Directory-Storage Primitive To Core

## Requirements

Implement [[s0032-hooks-via-artbook-distribution]] §2 in full —
the generic directory-storage kind primitive that the hook kind
(and later skills-as-kind) will consume.

- Add `x-storage` (enum `"file" | "directory"`, default `"file"`)
  and `x-manifest-name` (string template, default `"{slug}.md"`)
  to the `kind.json` schema.
- Extend `KindDef` with matching `storage: str = "file"` and
  `manifest_name: str = "{slug}.md"` fields; populate from
  `kind.json` in `Registry._load_vault_kinds` with the
  validation rules from §2.1 (unknown `x-storage` value,
  `x-manifest-name` on a non-directory kind, unknown template
  tokens → `ValidationError`).
- Branch `core.create` on `kd.storage`: file path unchanged,
  directory path does `mkdir <kind.dir>/<stem>/; write
  <kind.dir>/<stem>/<manifest_name>` with the same `O_EXCL`
  atomicity guarantees (§2.2). Return `Artifact.path` =
  manifest file path (not bundle dir).
- Branch `discover.iter_artifacts` to walk one level deeper for
  directory kinds (§2.3): `artifacts/<dir>/*/<manifest_name>`,
  excluding any bundle directory whose name begins with `.`
  (e.g. `.active/`). Half-authored bundles missing a manifest
  are silently skipped with at most one warning per `list`
  invocation.
- `core.update` (frontmatter-only) is unchanged — verify with a
  test that an existing directory-kind manifest's frontmatter
  can be updated and the body preserved.
- Tests:
  - File-kind regression test (existing kinds keep working).
  - Directory-kind creation test using a test-only kind in
    `tests/fixtures/`.
  - Discovery test for nested manifests + `.`-prefixed exclusion.
  - Registry validation tests for the three new error cases.
- Docs: add a § "Directory Storage" section to
  `docs/adding-a-kind.md` covering the two new `kind.json`
  fields, the template substitutions, and the bundle layout
  contract. No mention of hooks yet — this section documents
  the primitive, not its first consumer.

Out of scope here: the hook kind itself, the loader, `.active/`,
CLI verbs, artbook integration. Those are t0182–t0184.

## Findings

Implementation was already complete when this task was picked up. All six
deliverables from the requirements were in place:

- **`KindDef`** (`src/artifacts_os/core/models.py`): `storage: str = "file"` and
  `manifest_name: str = "{slug}.md"` fields added with correct defaults.
- **Registry validation** (`src/artifacts_os/core/registry.py`): `_load_vault_kinds`
  rejects unknown `x-storage` values, `x-manifest-name` on non-directory kinds,
  and unknown template tokens — all three as `ValidationError` at load time.
- **`core.create`** (`src/artifacts_os/core/store.py`): branches on `kd.storage`;
  directory path does `mkdir <bundle>; write <bundle>/<manifest>` with `O_EXCL`
  atomicity; returns `Artifact.path` = manifest file.
- **`discover.iter_artifacts`** (`src/artifacts_os/core/discover.py`): `_iter_kind_paths`
  walks one level deeper for directory kinds, excludes `.`-prefixed bundle dirs,
  warns at most once per invocation for half-authored bundles.
- **Tests** (`tests/core/test_directory_storage.py`): 21 tests covering all
  required cases; fixture kind at `tests/fixtures/kinds/widget/`.
- **Docs** (`docs/adding-a-kind.md`): `§ "Directory Storage"` section covers both
  `kind.json` fields, all template substitutions, and bundle layout contract.

Full test suite: **1156 passed, 1 skipped** — no regressions.

## Verification

- [x] `kind.json` schema documents `x-storage` and
      `x-manifest-name`; loader rejects unknown `x-storage`
      values, `x-manifest-name` on a file kind, and unknown
      template tokens (3 distinct `ValidationError` tests).
- [x] `KindDef.storage` and `KindDef.manifest_name` populated
      from `kind.json`; defaults preserved for all existing
      kinds (no migration of `agent`/`task`/`spec`/`note`/etc.
      kind files).
- [x] `core.create` writes a directory-kind bundle correctly:
      `mkdir + write manifest at <kind.dir>/<stem>/<manifest>`,
      `Artifact.path` returned is the manifest file.
- [x] `discover.iter_artifacts` finds directory-kind artifacts
      via one-level-deeper walk and excludes any
      `.`-prefixed bundle directory.
- [x] `core.update` works on a directory-kind manifest
      (frontmatter changes only; body preserved).
- [x] `docs/adding-a-kind.md` has a § "Directory Storage"
      section explaining the two fields, substitutions, and
      bundle layout.
- [x] `pytest` green; no regressions in existing file-kind
      tests.

## Verification Report

*Verified: 2026-05-24*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `kind.json` schema + 3 loader rejection cases | PASS | `registry.py` validates `x-storage` enum, `x-manifest-name` on non-directory kinds, unknown template tokens via `_KNOWN_STORAGE_VALUES` / `_KNOWN_TEMPLATE_TOKENS`. Tests: `test_registry_unknown_x_storage_raises`, `test_registry_manifest_name_on_file_kind_raises`, `test_registry_unknown_template_token_raises` (all pass). |
| 2 | `KindDef.storage` / `manifest_name` populated; defaults preserved | PASS | `models.py` `KindDef` has `storage: str = "file"` and `manifest_name: str = "{slug}.md"`. `registry.py` reads `x-storage` / `x-manifest-name` from schema. `test_file_kind_defaults` confirms existing `task` kind retains `storage="file"`, `manifest_name="{slug}.md"`. |
| 3 | `core.create` directory branch + `Artifact.path` = manifest | PASS | `store.py` branches on `kd.storage == "directory"`: creates `bundle_dir`, opens manifest with `O_CREAT \| O_EXCL`, returns artifact with `path = manifest_path`. Tests: `test_create_directory_kind_non_numbered`, `test_create_directory_kind_numbered`, `test_create_directory_kind_numbered_increments`, `test_create_directory_kind_collision_raises`, `test_create_directory_kind_body_written` (all pass). |
| 4 | `discover.iter_artifacts` walks deeper, excludes `.`-prefixed | PASS | `discover.py` `_iter_kind_paths` has directory-storage branch that iterates `subdir.iterdir()`, skips dirs starting with `.`, builds manifest path. Tests: `test_discovery_finds_directory_kind_artifacts`, `test_discovery_excludes_dot_prefixed_bundle_dirs`, `test_discovery_skips_half_authored_bundle_with_warning`, `test_discovery_warns_at_most_once_per_list_invocation` (all pass). |
| 5 | `core.update` on directory manifest preserves body | PASS | `core.update` is path-agnostic (uses `resolve()` + `os.replace`); no changes needed. Tests: `test_update_directory_kind_manifest_frontmatter`, `test_update_directory_kind_manifest_preserves_body` (both pass). |
| 6 | `docs/adding-a-kind.md` § "Directory Storage" | PASS | `docs/adding-a-kind.md` lines 391–471 contain a § "Directory Storage" section covering both `kind.json` fields (table at 401–404), template substitutions (table at 408–413), and bundle layout contract (diagram + bullets at 424–449). No mention of hooks. |
| 7 | `pytest` green, no regressions | PASS | Full suite: **1156 passed, 1 skipped** (verified by running `pytest`). `test_directory_storage.py` alone: 21/21 pass. |

### Summary

7 passed, 0 failed. All verification criteria for the directory-storage primitive are met; the task is ready to be marked verified.
