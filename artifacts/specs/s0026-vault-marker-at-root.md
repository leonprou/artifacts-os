---
kind: spec
id: s0026
name: vault-marker-at-root
status: draft
task: "[[t0131-move-artifacts-yaml-to-project]]"
created: 2026-05-10
agent: architect
---

# Vault Marker at Project Root

Relocate the vault-marker file from `artifacts/artifacts.yaml`
to `./artifacts.yaml` (project root, sibling of `artifacts/`).
The `artifacts/` directory continues to hold artifact data
(`tasks/`, `specs/`, `agents/`, `kinds/`, `notes/`, …); only the
marker file moves up one level.

Producing task: [[t0132-spec-for-vault-marker-at]].
Parent feature: [[t0131-move-artifacts-yaml-to-project]].

## 1. Background and Cross-References

- **Current marker** — `<vault-root>/artifacts/artifacts.yaml`,
  probed by `find_vault_root` in
  `src/artifacts_os/core/vault.py`. The directory and the
  config share the same `artifacts` token, which is awkward
  visually and at the call site
  (`root / "artifacts" / "artifacts.yaml"` — the word
  appears twice).
- **Parent task** — [[t0131-move-artifacts-yaml-to-project]] —
  captures user-level intent. Item 5 of that task explicitly
  delegates the backward-compat decision to this spec; pre-1.0
  hard cutover is permitted if justified.
- **Sibling specs** —
  - [[s0021-artifacts-init-flow]] §10.4–10.6 worked transcripts
    show `✓ artifacts/artifacts.yaml` lines that this spec
    rewrites.
  - [[s0010-core-settings-module-spec]] defines `load_settings`
    and the `Settings` extension pattern; the path argument
    moves but the API is unchanged.
- **Superseded predecessor pair** —
  [[t0133-feat-relocate-artifacts-yaml-to]] and
  [[t0134-spec-relocate-vault-marker-to]] (both `rejected`) —
  earlier framing of the same change. This spec replaces them.

## 2. Goals

1. Make the vault-marker visible at a glance — at the project
   root next to `pyproject.toml` and `CLAUDE.md`, where every
   other top-level project config lives.
2. Eliminate the doubled `artifacts/artifacts.yaml` token from
   call sites and docs.
3. Land in the smallest number of atomic PRs that keep the
   tree green throughout.
4. Keep every public API and CLI surface unchanged except for
   the literal path string the marker resolves to.

## 3. Non-Goals

- **No marker rename.** The file is still `artifacts.yaml`.
  `vault.yaml`, `project.yaml`, `.artifactsrc` etc. are
  separate decisions — out of scope here.
- **No schema change.** The contents of `artifacts.yaml`
  (`layout_version`, `project`, `views`, `default_views`,
  `cli`, `hooks`, `events`) are byte-identical before and
  after the move. Existing files continue to load.
- **No flatten of `artifacts/`.** Artifact data continues to
  live under `<vault-root>/artifacts/<kind>/`. Flattening to
  `<vault-root>/<kind>/` is its own discussion (see §10).
- **No automatic migration helper.** The migration is a single
  `mv`; a CLI command is more code than the operation
  warrants. See §6 for the documented manual procedure.
- **No multi-vault discovery.** `find_vault_root` continues to
  return at most one vault root, the nearest one walking up
  from CWD.
- **No dual-recognition of the legacy path.** Pre-1.0; see §5
  for the trade-off.

## 4. Locked Decisions Summary

| ID  | Decision | Rationale (brief) |
|-----|----------|-------------------|
| D1  | Marker lives at `<vault-root>/artifacts.yaml`. `artifacts/` continues to hold artifact data. | Top-level config matches every other ecosystem (`pyproject.toml`, `Cargo.toml`, …). Keeping `artifacts/` as data-only removes the doubled token. |
| D2  | "Vault root" = the directory containing the marker — unchanged in semantics from today. `find_vault_root` returns this directory. | Every consumer already composes `root / "artifacts" / kd.dir`. Keeping the return value's role identical means none of those call sites change. |
| D3  | Backward compatibility: **hard cutover.** The legacy `artifacts/artifacts.yaml` location is no longer recognised. | Pre-1.0; no public users yet. Dual-recognition adds a code path that would later need a deprecation sweep, and would blur the "marker is at the root" mental model the change is designed to establish. |
| D4  | Migration is **documented manual procedure** (one `mv`). No `artifacts migrate` helper in v1. | One-time per-vault step; a CLI command is overkill. Reconsider if user feedback shows the doc-only path causes friction. |
| D5  | Build sequence is **two atomic PRs** — Code-and-self-vault (PR1), Documentation sweep (PR2). | Code-only and this-repo's-vault must change together (find_vault_root, fixtures, init, this repo's marker — all interlocked). Docs are pure prose and tolerate a one-PR lag. |
| D6  | Resolution algorithm walks parents looking for `<candidate>/artifacts.yaml` as a regular file. The directory `<candidate>/artifacts/` (which exists in this repo) does **not** match because `is_file()` is false on a directory. | Avoids any name-collision footgun. The check is type-strict, not glob-strict. |
| D7  | Inside-`artifacts/` CWD case still resolves: walk-up passes through `artifacts/` → matches at the parent. | The original concern that "CWD inside `artifacts/` may dead-end at `artifacts/artifacts.yaml`" disappears under D1 — there is no marker inside `artifacts/` to mis-match. |
| D8  | Test fixtures (`make_vault` in three conftests) write `<root>/artifacts.yaml` and continue to create `<root>/artifacts/<x-dir>/`. | The fixture is the test surface for vault construction; updating it propagates the new layout to every test that uses it. |

## 5. New Layout

### 5.1 After the change — canonical paths

```
<vault-root>/
├── artifacts.yaml          ← the marker (NEW location)
├── artifacts/              ← artifact data (unchanged)
│   ├── kinds/
│   │   ├── task.json
│   │   ├── task/ARTIFACT.md
│   │   └── …
│   ├── tasks/
│   ├── specs/
│   ├── notes/
│   ├── agents/
│   ├── research/
│   └── logs/
│       └── events/
├── pyproject.toml          ← (sibling — example of what the
├── CLAUDE.md               ←   marker now sits next to)
└── README.md
```

### 5.2 "Vault root" — definition

The **vault root** is the directory that contains
`artifacts.yaml` as a regular file. This is the value
`find_vault_root` returns. Every consumer that today writes
`root / "artifacts" / kd.dir` (registry, discover, store,
events log path, kinds catalog, etc.) continues to do so
unchanged — the only thing that moves is the marker, and only
the call sites that read or write *the marker file itself*
need editing.

This definition deliberately keeps "vault root" identical in
role to its pre-change meaning: it is still the top of the
project tree, not the `artifacts/` subdirectory. Promoting
`artifacts/` to "the vault" was considered and rejected (§10
Trade-offs).

### 5.3 What does **not** move

| Path / Concept | Before | After |
|----------------|--------|-------|
| Artifact storage roots | `<root>/artifacts/<x-dir>/` | `<root>/artifacts/<x-dir>/` |
| Kind schemas + ARTIFACT.md | `<root>/artifacts/kinds/<name>{.json, /ARTIFACT.md}` | unchanged |
| Event log directory | `<root>/artifacts/logs/events/` | unchanged |
| `Registry.root` value | vault root | vault root |
| `find_vault_root` return type | `Path \| None` | `Path \| None` |

The `Settings` dataclass, `load_settings(path)` signature,
extension pattern (`from_base`), kinds-catalog API, and CLI
command surface are all byte-identical before and after.

## 6. Resolution Algorithm — `find_vault_root`

### 6.1 Before (current)

```python
# src/artifacts_os/core/vault.py
def find_vault_root(start: Path | None = None) -> Path | None:
    current = Path(start) if start is not None else Path.cwd()
    current = current.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "artifacts" / "artifacts.yaml").is_file():
            return candidate
    return None
```

### 6.2 After (this spec)

```python
# src/artifacts_os/core/vault.py
def find_vault_root(start: Path | None = None) -> Path | None:
    """Walk up from start (default: CWD) until a directory
    containing ``artifacts.yaml`` is found. Returns the
    directory or None."""
    current = Path(start) if start is not None else Path.cwd()
    current = current.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "artifacts.yaml").is_file():
            return candidate
    return None
```

The change is one segment: drop the inner `"artifacts"` from
the probe path. The walk-up shape, return type, and `None`
fallback are unchanged.

### 6.3 Edge cases

| CWD | Resolution | Returns |
|-----|------------|---------|
| `<root>/` | first candidate matches | `<root>` |
| `<root>/artifacts/` | candidate `artifacts/` has no `artifacts/artifacts.yaml`; parent `<root>` matches | `<root>` |
| `<root>/artifacts/specs/` | candidates `specs/` → no, `artifacts/` → no, `<root>` → match | `<root>` |
| `<root>/src/artifacts_os/cli/` | climbs through `cli/` → `artifacts_os/` → `src/` → `<root>` matches | `<root>` |
| outside any vault | every candidate fails up to filesystem root | `None` |

The "candidate `artifacts/` has no `artifacts/artifacts.yaml`"
note is important: the `artifacts/` directory has the same
name as the marker file, but `Path.is_file()` returns `False`
on a directory, so the check is type-safe by construction.
This is the key point of D6.

### 6.4 Worktree behaviour

`find_vault_root` operates on filesystem paths and is unaware
of git worktrees. Its behaviour after the move is identical to
before in worktrees — if the worktree contains
`<wt-root>/artifacts.yaml`, the worktree is the vault root; if
not, the search continues up the tree. The `.openstation/`
worktree-symlink mechanism (per
`.openstation/docs/worktrees.md`) is orthogonal.

## 7. Settings Loading Impact

Every call site in `src/` that constructs the marker path
must change in lock-step. The complete list, derived by `rg
"artifacts/artifacts\.yaml"` on `src/`:

| File | Line | Today | Becomes |
|------|------|-------|---------|
| `src/artifacts_os/core/vault.py` | 11, 15 | docstring + `candidate / "artifacts" / "artifacts.yaml"` | docstring + `candidate / "artifacts.yaml"` |
| `src/artifacts_os/cli/__init__.py` | 56 | `Path(root) / "artifacts" / "artifacts.yaml"` | `Path(root) / "artifacts.yaml"` |
| `src/artifacts_os/cli/__init__.py` | 72 | same | same |
| `src/artifacts_os/cli/commands/init.py` | 419 | `target / "artifacts" / "artifacts.yaml"` (already-init guard) | `target / "artifacts.yaml"` |
| `src/artifacts_os/cli/commands/init.py` | 539 | `_do_write(target / "artifacts" / "artifacts.yaml", …)` | `_do_write(target / "artifacts.yaml", …)` |
| `src/artifacts_os/hooks/loader.py` | 85 | `root / "artifacts" / "artifacts.yaml"` | `root / "artifacts.yaml"` |
| `src/artifacts_os/ai/install.py` | 301 | `(target / "artifacts" / "artifacts.yaml").is_file()` | `(target / "artifacts.yaml").is_file()` |

In addition, **string references** in source-level docstrings,
help text, and error messages — none of which affect runtime
resolution but all of which read incorrectly after the move:

| File | Line | Action |
|------|------|--------|
| `src/artifacts_os/core/vault.py` | 11 | Update docstring path. |
| `src/artifacts_os/cli/commands/views.py` | 21 | Update embedded error string `"artifacts/artifacts.yaml"` → `"artifacts.yaml"`. |
| `src/artifacts_os/events/settings.py` | 3 | Module docstring — already says `"artifacts.yaml"` (no path qualifier); leave as-is. |
| `src/artifacts_os/hooks/settings.py` | 3 | Same — already says `"artifacts.yaml"`; leave as-is. |
| `src/artifacts_os/cli/settings.py` | 3 | Same. |

`load_settings(path)` in `src/artifacts_os/core/settings.py`
is **unchanged**. It is path-agnostic — callers pass the
resolved path. The change is at every call site, not in the
loader.

`from_base(base: Settings)` extensions
(`ViewsSettings.from_base`, `CliSettings.from_base`,
`HooksSettings.from_base`, `EventsSettings.from_base`,
`RunSettings.from_base`) are **unchanged**. They consume
`base.raw`, not a path.

## 8. `artifacts init` Flow

### 8.1 Reconciliation with `s0021`

`s0021-artifacts-init-flow` §10.4–10.6 show worked transcripts
that hard-code `✓ artifacts/artifacts.yaml`. After this spec
those lines become `✓ artifacts.yaml`. The rest of `s0021` —
tier selection, kinds/agents prompts, exit codes, dry-run,
`--force` semantics — is unchanged. This spec **amends** s0021
§10 transcripts and §14.2 example output rather than
superseding s0021.

### 8.2 Empty-directory case

```
$ mkdir my-vault && cd my-vault
$ artifacts init -y
Selected:
  template : standard
  kinds    : task, note, spec
  agents   : (none)

Writing files...
  ✓ artifacts.yaml                          ← NEW location
  ✓ artifacts/kinds/task.json
  ✓ artifacts/kinds/task/ARTIFACT.md
  ✓ artifacts/tasks/.gitkeep
  ✓ artifacts/kinds/note.json
  ✓ artifacts/kinds/note/ARTIFACT.md
  ✓ artifacts/notes/.gitkeep
  ✓ artifacts/kinds/spec.json
  ✓ artifacts/kinds/spec/ARTIFACT.md
  ✓ artifacts/specs/.gitkeep

Initialised artifacts-os project: /abs/path/to/my-vault
```

The only change vs. the s0021 transcript is the first write
line. Every subsequent write is unchanged.

### 8.3 Existing-project (re-init) case

```
$ artifacts init -y                # in an already-initialised vault
error: already initialised at /abs/path; pass --force to re-init in place
$ artifacts init -y --force
Writing files...
  ✓ artifacts.yaml (overwritten)
  ⊘ artifacts/kinds/task.json (exists, skipped — this file is per-file-locked)
  …
```

The already-init guard (s0021 §14.2) probes
`<target>/artifacts.yaml` instead of
`<target>/artifacts/artifacts.yaml`. Per-file guards on every
other write are unchanged.

### 8.4 `--openstation-compat` symlink

The `openstation -> artifacts` symlink (s0021 §17.2) is
unaffected. It points at the data directory, not at the
marker.

## 9. Backward Compatibility Decision

### 9.1 Options evaluated

| ID | Option | Pro | Con |
|----|--------|-----|-----|
| (a) | **Hard cutover.** `find_vault_root` checks only the new location. Legacy `artifacts/artifacts.yaml` is invisible. | Simplest mental model. No code rot from a deprecated probe path. Init's already-init guard reflects the new reality precisely. | Existing vaults stop working until migrated. |
| (b) | **Dual recognition.** Probe new first, fall back to legacy with a `DeprecationWarning`. Remove the fallback in a later release. | Existing vaults keep working untouched. Operator gets a printed reminder. | Adds a code branch and a fixture matrix (each test site needs both layouts). The deprecation removal is a second migration of equal cost. Pre-1.0 buys nothing operationally. |
| (c) | **Migration-only.** Detect the legacy layout and refuse with a pointer to the migration steps. | Loud failure prevents silent partial breakage. | Same code-branch cost as (b) without the win of "it just works". |

### 9.2 Pick: **(a) hard cutover** (D3)

Rationale:

1. **Pre-1.0 status.** Per parent task t0131 §5: "Pre-1.0,
   hard cutover is fine if justified." The project has no
   PyPI release with a marker dependency.
2. **Migration is mechanical.** One `mv`; see §6.3. The cost
   of running it in any vault that exists today is seconds.
3. **Code-branch hygiene.** Dual recognition would land a
   `_legacy_check` branch in `find_vault_root` plus matching
   handling in `init` and `ai/install`. Each branch creates
   a future sweep we already know we'll do.
4. **Mental-model integrity.** The change's whole point is
   "the marker lives at the project root." A fallback that
   silently honours the old location erodes that.

### 9.3 Failure modes after the cut

A user with an unmigrated vault sees:

```
$ artifacts list
error: not in an artifacts-os vault (no artifacts.yaml found
       walking up from /current/path).

If your vault was created before <release-tag>, see the
migration note: <link to docs/migration.md>.
```

The error message is updated to reference the migration doc
(see §11). The current error string lives in
`src/artifacts_os/cli/__init__.py` (the path that surfaces
"not in a vault" today) — the implementing task updates it.

## 10. Trade-Offs

### 10.1 Trade-off — `<root>/` vs `artifacts/` as "vault root"

| Pick | Pro | Con |
|------|-----|-----|
| **`<root>/` (this spec)** | Zero-touch to every `root / "artifacts" / kd.dir` consumer. `Registry.root`, discover, store, events log all keep working. | Concept of "vault" overlaps with "project" — a project is a vault. |
| `<root>/artifacts/` | "The vault is one folder" — clean conceptual encapsulation. | Every consumer changes to use `root / kd.dir` directly. Far more code churn. The marker would be a sibling of the vault, not inside it — strange. |

**Pick:** `<root>/`. The cost of moving every consumer is a
poor exchange for a conceptual rename, especially when D1
already eliminates the naming clash.

### 10.2 Trade-off — Flat vault vs `artifacts/`-nested data

| Pick | Pro | Con |
|------|-----|-----|
| **Nested under `artifacts/` (this spec)** | Status quo for data layout. `default_kinds` dirs (`tasks/`, `specs/`, …) stay namespaced. No risk of collision with the project's own `tasks/` or `specs/` directories used for other purposes. | One extra directory level. |
| Flat at `<root>/<kind>/` | Tighter visual layout. | Collides with any project that already has a `tasks/` or `specs/` directory. Promotion of every storage path to top-level is a breaking change at every call site. |

**Pick:** keep nested. Out of scope per §3 — flat-vault would
need its own spec.

### 10.3 Trade-off — Hard cutover vs dual-recognition window

Already covered in §9.1. **Pick:** hard cutover (D3).

### 10.4 Trade-off — Migration helper vs documented `mv`

| Pick | Pro | Con |
|------|-----|-----|
| **Documented `mv` (this spec)** | Zero new CLI code. Migration is one operator action, fully reversible. | User must read the doc. No automatic detection of the legacy layout. |
| `artifacts migrate` helper | Detects, dry-runs, executes. Less footgun. | New subcommand, new tests, new failure modes. For a one-time per-vault op, low ROI. |

**Pick:** docs. Reconsider only if user reports show the
doc-only path is causing friction — adding a helper later is
a pure addition, not a breaking change.

## 11. Migration Story

### 11.1 Manual procedure (operator-facing)

For each vault:

```
cd <vault-root>
git mv artifacts/artifacts.yaml ./artifacts.yaml
git commit -m "chore: relocate artifacts.yaml to project root"
```

That is the entire migration. No edits to the YAML body, no
follow-up sweeps. After this, `find_vault_root` (post-spec)
resolves correctly.

### 11.2 Verification (operator-facing)

```
$ artifacts list --kind task
# should print the same list it did before the mv
```

If the command errors with "not in an artifacts-os vault",
the marker is not at `<vault-root>/artifacts.yaml` — re-check
the path.

### 11.3 Documentation home

The procedure lives in **a new** `docs/migration.md` (created
by the implementing task). The existing-vault error message
(§9.3) links to it. `CHANGELOG.md` includes a one-line entry
under the release that ships the change, pointing to the same
doc.

### 11.4 This repo's own vault

This repo migrates as part of the implementing task's PR1
(see §13). Concretely:

```
git mv artifacts/artifacts.yaml ./artifacts.yaml
```

…goes in the same commit as the `find_vault_root` change.

## 12. Documentation Update Checklist

Every reference to the legacy marker path that the
implementing task must rewrite. Derived from
`rg "artifacts/artifacts\.yaml"` on `docs/`, `src/**/README.md`,
`CLAUDE.md`, and `README.md`:

### 12.1 Top-level

| File | Reference |
|------|-----------|
| `CLAUDE.md` | line 12 (intro), line 101 (Settings section) |
| `README.md` | line 24 (locate-the-vault example) |

### 12.2 `docs/`

| File | Reference |
|------|-----------|
| `docs/settings.md` | lines 3, 14, 48, 81, 358, 490 |
| `docs/init-flow.md` | lines 19, 123 (top-level guard) |
| `docs/adding-a-kind.md` | lines 257, 508 |
| `docs/creating-an-artifact.md` | line 5 |

### 12.3 Per-module READMEs

| File | Reference |
|------|-----------|
| `src/artifacts_os/core/README.md` | lines 42, 154, 182, 201, 215 |
| `src/artifacts_os/views/README.md` | lines 270, 338 |
| `src/artifacts_os/cli/README.md` | lines 47, 92, 93, 262, 322, 326, 336, 349, 350, 365, 367, 371, 390, 440, 660, 817, 901 (most are `artifacts.yaml` already; only the qualified `artifacts/artifacts.yaml` instances need editing) |

### 12.4 Skills and AI command files

| File | Reference |
|------|-----------|
| `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` | line 3 (description string), line 50 |
| `src/artifacts_os/ai/claude/commands/artifacts.create.md` | lines 22, 42 |

### 12.5 Specs (cross-references)

`s0021-artifacts-init-flow` references
`artifacts/artifacts.yaml` in §1 (Background), §4 D1, §10
worked transcripts, §14.2 worked example, §17.1 surface
table, §17.2 preserves list, and §19 cross-refs. The
implementing task updates these in place — `s0021` is not
superseded, only amended on the marker-path strings.

### 12.6 What stays as-is

- Strings like "the `artifacts.yaml` file" or "your
  `artifacts.yaml`" with no `artifacts/` prefix — already
  correct; no edit needed.
- Module-package docstrings in `events/settings.py`,
  `hooks/settings.py`, `cli/settings.py` — already say
  `"artifacts.yaml"` without a path qualifier (§7).

The implementing task's PR2 lands every entry in §§12.1–12.5
in one commit.

## 13. Build Sequence

Two ordered, independently-shippable steps. Each is one PR.

### 13.1 PR1 — Code + this repo's vault + tests

Single atomic PR. Splitting further requires either a
dual-recognition middle state (rejected per §9) or a
known-broken intermediate commit (forbidden by repo
hygiene).

Files touched:

1. `src/artifacts_os/core/vault.py` — the `find_vault_root`
   probe (one-line code change + docstring).
2. `src/artifacts_os/cli/__init__.py` — two read-side path
   constructions (lines 56, 72).
3. `src/artifacts_os/cli/commands/init.py` — already-init
   guard (line 419) + write target (line 539).
4. `src/artifacts_os/hooks/loader.py` — settings-path
   construction (line 85).
5. `src/artifacts_os/ai/install.py` — vault-validity probe
   (line 301).
6. `src/artifacts_os/cli/commands/views.py` — embedded error
   message (line 21).
7. `tests/core/conftest.py` — `make_vault` writes
   `<root>/artifacts.yaml` and creates `<root>/artifacts/`
   for kind data (line 43 + the `.mkdir` above it).
8. `tests/cli/conftest.py` — same change to its `make_vault`
   factory (line 51).
9. `tests/ai/conftest.py` — same (line 15).
10. Every test-file with an inline
    `(root / "artifacts" / "artifacts.yaml").write_text(...)`
    — see §14.2. Bulk `sed` is acceptable; the resulting
    pattern is `(root / "artifacts.yaml").write_text(...)`.
11. `artifacts/artifacts.yaml` — `git mv` to
    `./artifacts.yaml`.
12. `CHANGELOG.md` — release entry (one-liner) under the
    next minor version.
13. `docs/migration.md` — new file, content per §11.1–11.2.

PR1 ships green: `pytest` passes after the bulk fixture
update, `artifacts list` works in this repo's own checkout
after the `git mv`.

### 13.2 PR2 — Documentation sweep

Files touched:

1. Every entry in §§12.1–12.5 (top-level docs, per-module
   READMEs, skills, AI command files, `s0021` amendments).
2. The new error-message pointer to `docs/migration.md`
   added in PR1 (line referenced from §9.3) — verified in
   PR2 by spot-checking that the doc link resolves.

PR2 has no functional risk; it is pure prose. The split lets
PR1's review be focused on the resolution-algorithm change
without docs noise, and lets PR2 be reviewed quickly as a
prose audit.

### 13.3 Optional PR3 — `docs/migration.md` polish

If the migration doc grows beyond the simple `mv` (e.g. to
add an `artifacts migrate` helper after user feedback, see
§10.4), that is a separate task with its own spec — not
folded into this build sequence.

## 14. Tests / Fixtures Impact

### 14.1 Fixtures

The three `make_vault` factories are the test-side
constructor. Each writes the marker today as
`<root>/artifacts/artifacts.yaml`. After PR1:

```python
# tests/core/conftest.py — example shape
def _make(kinds=None) -> tuple[Path, Registry]:
    root = tmp_path / "vault"
    root.mkdir(parents=True)
    (root / "artifacts.yaml").write_text("layout_version: 1\n")
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    ks = kinds if kinds is not None else _default_kinds()
    for kd in ks:
        (root / "artifacts" / kd.dir).mkdir(parents=True, exist_ok=True)
    return root, Registry(ks, root=root)
```

The mkdir of `<root>/artifacts/` moves below the marker
write because `<root>` itself must exist before either
operation; the kinds-storage subdirectory creation is
unchanged.

### 14.2 Inline fixture sites

Tests that bypass the factory and write the marker inline —
roughly **40 occurrences** spread across:

```
tests/cli/conftest.py
tests/cli/test_init.py
tests/cli/test_settings.py
tests/cli/test_list_meta.py
tests/cli/test_list_views.py
tests/cli/test_list_layout.py
tests/cli/test_list_schema_flags.py
tests/cli/test_list_children.py
tests/cli/test_views_cmd.py
tests/cli/test_create_kind_default.py
tests/cli/test_create_kind_aware_help.py
tests/cli/test_register_kinds.py
tests/core/conftest.py
tests/core/test_vault.py
tests/core/test_settings.py
tests/core/test_kinds_catalog.py
tests/core/test_list_artifacts_filters.py
tests/core/test_store.py
tests/core/test_graph.py
tests/views/test_views_settings.py
tests/hooks/test_loader.py
tests/events/test_e2e.py
tests/events/test_store_integration.py
tests/ai/conftest.py
tests/ai/test_init_integration.py
tests/ai/test_body_loader.py
```

The sweep pattern is mechanical:
`(<expr> / "artifacts" / "artifacts.yaml")` →
`(<expr> / "artifacts.yaml")`.

The implementing task does not need to enumerate every
occurrence in its task spec — the pattern is unambiguous and
a single grep over the diff catches a stray miss.

### 14.3 New tests required

Add to `tests/core/test_vault.py` (the `find_vault_root`
test module):

1. **CWD == `<root>`** → returns `<root>`.
2. **CWD == `<root>/artifacts`** → returns `<root>` (the
   parent matches; the legacy `artifacts/artifacts.yaml`
   would have matched on this candidate before — now it
   correctly resolves to the parent).
3. **CWD == `<root>/artifacts/specs`** → returns `<root>`.
4. **No marker anywhere up the tree** → returns `None`.
5. **Legacy layout only** (`<root>/artifacts/artifacts.yaml`
   exists, `<root>/artifacts.yaml` does not) → returns
   `None`. Pins the hard-cutover decision (D3).

### 14.4 No tests removed

Existing `test_vault.py` cases continue to pass once the
fixture writes the marker at `<root>/artifacts.yaml`. The
walk-up behaviour they assert is unchanged at the algorithm
level.

## 15. Worked Example — Before vs After

### 15.1 Tree

**Before:**

```
my-vault/
├── artifacts/
│   ├── artifacts.yaml          ← marker
│   ├── kinds/
│   ├── tasks/
│   └── specs/
├── pyproject.toml
└── CLAUDE.md
```

**After:**

```
my-vault/
├── artifacts.yaml              ← marker (NEW)
├── artifacts/
│   ├── kinds/
│   ├── tasks/
│   └── specs/
├── pyproject.toml
└── CLAUDE.md
```

### 15.2 Resolution walk

CWD = `my-vault/artifacts/specs/`.

**Before** — `find_vault_root` walks:

```
candidate = my-vault/artifacts/specs/
   probe: my-vault/artifacts/specs/artifacts/artifacts.yaml ⇒ no
candidate = my-vault/artifacts/
   probe: my-vault/artifacts/artifacts/artifacts.yaml ⇒ no
candidate = my-vault/
   probe: my-vault/artifacts/artifacts.yaml ⇒ YES → return my-vault/
```

**After** — same CWD:

```
candidate = my-vault/artifacts/specs/
   probe: my-vault/artifacts/specs/artifacts.yaml ⇒ no
candidate = my-vault/artifacts/
   probe: my-vault/artifacts/artifacts.yaml ⇒ no  (file moved)
candidate = my-vault/
   probe: my-vault/artifacts.yaml ⇒ YES → return my-vault/
```

The number of candidates examined and the eventual return
value are identical. Only the probe filename inside each
candidate changes.

### 15.3 Settings load

**Before:**

```python
root = find_vault_root()                                  # my-vault
settings = load_settings(root / "artifacts" / "artifacts.yaml")
```

**After:**

```python
root = find_vault_root()                                  # my-vault
settings = load_settings(root / "artifacts.yaml")
```

Same return value, same `Settings` instance — only the
path argument changed.

## 16. Out of Scope (Made Explicit)

The spec deliberately defers:

1. **Marker rename.** `artifacts.yaml` could become
   `vault.yaml` or `.artifactsrc`; not relevant to the
   relocation change. Out of scope.
2. **Schema changes.** No keys added, removed, renamed, or
   re-typed inside the file. Out of scope.
3. **Flat-vault layout.** Promoting `tasks/`, `specs/`, etc.
   to project root. See §10.2. Out of scope.
4. **Multi-vault projects.** A single project containing
   multiple vault roots. `find_vault_root` continues to
   return the nearest match. Out of scope.
5. **Automatic migration helper.** See §10.4. Out of scope
   for v1; revisit on user feedback.
6. **Backward-compat warning window.** See §9. Out of scope
   given pre-1.0 status.
7. **Worktree-aware migration.** Linked worktrees that share
   the primary vault's `.openstation/` symlink already
   resolve through that mechanism; the marker move does not
   touch worktree wiring. Out of scope.

## 17. Verification

The producing task ([[t0132-spec-for-vault-marker-at]]) lists
the verification checklist this spec must satisfy. Mapping:

- **New layout precise / vault-root unambiguous** → §5
- **`find_vault_root` before/after pseudocode + edge cases** →
  §6
- **Every call-site in `src/` enumerated** → §7
- **`artifacts init` post-change behaviour reconciled with
  s0021** → §8
- **Backward-compat decision picked + justified** → §9, D3
- **Migration plan concrete** → §11
- **Doc/README update checklist exhaustive** → §12
- **Test fixture impact called out** → §14
- **Worked example before/after tree + resolution walk** →
  §15
- **Out-of-scope section** → §16
- **Build sequence ordered + independently-shippable** →
  §13
