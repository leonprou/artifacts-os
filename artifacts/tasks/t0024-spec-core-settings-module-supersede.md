---
kind: task
id: t0024
name: spec-core-settings-module-supersede
type: spec
status: done
assignee: architect
owner: user
created: 2026-04-26
started: 2026-04-26
artifacts:
  - "[[openstation/specs/s0010-core-settings-module-spec]]"
  - "[[openstation/specs/s0009-artifacts-os-config-module]]"
  - "[[openstation/specs/s0007-artifacts-os-views-module]]"
  - "[[openstation/tasks/t0019-relocate-viewconfig-to-core-and]]"
completed: 2026-04-28
---

# Spec Core.Settings Module, Supersede S0009, Close T0019

## Context

Earlier specs (s0007, s0009) and task t0019 assumed a separate
`artifacts_os.config` module that loads the project settings file and
hands typed dataclasses to consumers. Discussion concluded that
settings parsing belongs in `core` (which already owns vault discovery,
kinds loading, and `init`-time YAML writes), not in a sibling module.

This task records the decision and rewires the affected specs:

- A new spec defines `core.load_settings` and section dataclasses in
  `core.models`.
- s0009 is marked superseded.
- t0019 is closed as obsolete (its DAG fix is moot — there is no
  `config` module to relocate `ViewConfig` *away from*; the dataclass
  lands directly in `core.models`).
- s0007 is trimmed to remove `ViewConfig` / `parse_view_config` from
  its public API.

Reads only — no write API in scope. Per-module section ownership is
convention, not runtime-enforced.

## Requirements

1. **Create new spec `artifacts/specs/sNNNN-core-settings.md`** (CLI assigns ID).

   Contents:
   - **Purpose** — `core` owns parsing the project settings file
     (`artifacts.yaml`) and producing a typed `Settings` tree.
   - **Public API:**
     - `load_settings(path: Path) -> Settings`
     - Section dataclasses re-exported from `core.models`:
       `Settings`, `ProjectConfig`, `ViewConfig`, `ViewsConfig`,
       `RunConfig`, `TmuxConfig`, `DefaultsConfig`, `ShowDefaults`
     - `UnsupportedSchemaVersion` (subclass of `ValueError`)
   - **Section ownership convention** — each module reads:
     - the **global** part: `layout_version` + `project`
     - its own section: `views` (views), `run` (cli/tui dispatch), etc.
     - Convention only; no runtime enforcement.
   - **Global definition** — narrow: `layout_version` + `project`.
     Per-command `defaults.*` sections are treated as module-owned
     (e.g. `defaults.show` → `cli show` command).
   - **Schema versioning** — `layout_version: 1` required; missing or
     unknown raises `UnsupportedSchemaVersion`. Same rules as s0009.
   - **Full schema block** — copy verbatim from s0009 ("Full Settings
     File Schema") so the new spec is self-contained.
   - **Module dependency** — `core` parses settings; consumers
     (`cli`, `tui`, `views` indirectly through `cli`/`tui`) receive a
     `Settings` instance from the entry point. Existing DAG unchanged:
     `core → views → cli, tui`; `core → log → ai`.
   - **Scope boundary:**
     - **In:** YAML I/O, schema versioning, typed dataclass construction,
       error reporting.
     - **Out:** write API (deferred — captured in "Future work" section
       with the principle "modules persist only their own subtree" so
       the convention isn't lost), argument parsing, filter application,
       rendering.
   - **Future work** — note that a write API will be spec'd as a
     follow-up when a real write-consumer task lands.

2. **Update `artifacts/specs/s0009-artifacts-os-config-module.md`:**
   - Frontmatter — change `status: draft` to `status: superseded`.
   - Add a top-of-body note: "Superseded by sNNNN-core-settings —
     settings parsing folded into `core`, no separate `config` module."
   - Do not delete the body content (keeps the design history).

3. **Update `artifacts/tasks/t0019-relocate-viewconfig-to-core-and.md`:**
   - Frontmatter — change `status: ready` to `status: cancelled`
     (or whichever closed-state the project uses; check existing
     statuses in `artifacts/kinds/task.json`).
   - Append a `## Resolution` section: "Closed as obsolete. The DAG fix
     this task proposed is subsumed by sNNNN-core-settings, which folds
     settings into `core` directly. `ViewConfig` lands in `core.models`
     as part of that spec."

4. **Update `artifacts/specs/s0007-artifacts-os-views-module.md`:**
   - Public API — remove `ViewConfig` and `parse_view_config` from the
     export list. Add note: "`ViewConfig` is defined in `core.models`
     and read by callers from `settings.views`; `views` consumes
     `.columns` for column resolution."
   - Key Concepts → ViewConfig — rewrite to describe consumption only
     (no parsing). Cross-reference sNNNN-core-settings.
   - Scope Boundary "In" — remove `ViewConfig` and `parse_view_config`.
   - Scope Boundary "Out" — replace "settings-file I/O (delegated to
     `artifacts_os.config`)" with "settings-file I/O (handled by
     `core.load_settings`)".
   - Settings YAML Schema (views section) — keep schema examples;
     update closing line to point at `core.load_settings` instead of
     `views.parse_view_config`.

5. **Preserve boundaries — do NOT:**
   - Modify any source code under `src/` (this is a spec task only).
   - Re-open the "single file vs split files" decision (artifacts.yaml
     absorbs all sections, decided in s0009).
   - Spec a write API (deferred).
   - Change `views`'s rendering API (`render_table`, `FieldSpec`).
   - Touch s0007 sections unrelated to `ViewConfig` / `parse_view_config`.

## Verification

- [ ] New spec `sNNNN-core-settings.md` exists with purpose, public API, section ownership convention, schema versioning, full schema, module dependency, scope boundary
- [ ] New spec defines "global" narrowly as `layout_version` + `project`
- [ ] New spec includes a "Future work" note for write API
- [ ] s0009 frontmatter shows `status: superseded`
- [ ] s0009 body has a top note pointing at the new spec
- [ ] t0019 frontmatter shows a closed status
- [ ] t0019 has a Resolution section explaining closure
- [ ] s0007 Public API does not list `ViewConfig` or `parse_view_config`
- [ ] s0007 ViewConfig section describes consumption only and references the new spec
- [ ] s0007 Scope Boundary "Out" mentions `core.load_settings`, not `artifacts_os.config`

## Progress

### 2026-04-26 — architect
> time: 23:40
> log: [[openstation/logs/t0024-spec-core-settings-module-supersede]]

Created s0010-core-settings spec; superseded s0009; closed t0019 as
obsolete (rejected); rewired s0007 to point at core.load_settings.
Spec-only changes.

### 2026-04-26 — architect
> time: 23:55
> log: [[openstation/logs/t0024-spec-core-settings-module-supersede]]

Revision after review: rewrote s0010 to be library-generic. Dropped
OpenStation-specific dataclasses (`RunConfig`, `TmuxConfig`,
`DefaultsConfig`, `ShowDefaults`) from the typed surface. Introduced
the **library-defined vs. extension** distinction: `core.load_settings`
now types only `project`, `views`, `default_views`; unknown top-level
keys are preserved verbatim on `Settings.extensions` for consumers
(e.g. OpenStation) to parse independently.

### 2026-04-28 — architect
> time: 09:00
> log: [[openstation/logs/t0024-spec-core-settings-module-supersede]]

Second revision after review: tightened the layering further. `core`
no longer parses `views` / `default_views` at all — `core.Settings`
holds only `layout_version`, `project`, and `raw` (the full parsed
YAML dict). Other modules **extend `Settings`** with their own
subclass and a `from_base(base)` parser. Moved `ViewConfig` /
`ViewsConfig` ownership from `core.models` back to `views.models`;
introduced `views.ViewsSettings(Settings)` as the typed-settings
entry point for view consumers. s0007 updated to reflect new
ownership and public API.

## Findings

Decision recorded and the affected specs rewired. Settings parsing
now lives in `core` rather than a sibling `config` module.

**New spec — [[s0010-core-settings-module-spec]]:**
- Public API: `core.load_settings(path) -> Settings` plus
  `UnsupportedSchemaVersion`. The typed surface in `core.models` is
  minimal: `Settings` (base) and `ProjectConfig`. Nothing else.
- **`Settings` is a base class; modules extend it.** `core.Settings`
  holds `layout_version`, `project`, and `raw: dict[str, Any]` (the
  full parsed YAML). Each module that needs typed access to its
  section defines a `Settings` subclass with a
  `from_base(base: Settings) -> Self` parser. `views` provides
  `ViewsSettings`; consumers (OpenStation, downstream harnesses)
  do the same for their own keys.
- `core` parses **only** what it owns — `layout_version` and
  `project`. It does not parse `views`, `default_views`, or any
  consumer section. This keeps the DAG strict: `core` never
  references symbols from `views` or any consumer.
- Schema versioning rules copied from s0009 (`layout_version: 1`
  required; missing/unknown raises `UnsupportedSchemaVersion`).
  Each module owning a section is responsible for its own
  schema validation within that subtree.
- DAG unchanged: `core → views → cli, tui`; `core → log → ai`.
- Implementation note: base `Settings` uses `@dataclass(kw_only=True)`
  so subclasses can add required fields without fighting Python's
  "non-default after default" rule.
- **Future work** captured: a write API will be spec'd later under
  the principle *"modules persist only their own subtree."* Each
  module's subclass will own its own writer.

**Supersede — [[s0009-artifacts-os-config-module]]:**
- Frontmatter `status: draft` → `status: superseded`.
- Top-of-body callout points at s0010; original body preserved as
  design history.

**Close — [[t0019-relocate-viewconfig-to-core-and]]:**
- Frontmatter `status: done` → `status: rejected` (forced; the
  project uses `rejected` as its closed state — the kinds enum
  has `cancelled` but the CLI rejects that name and existing
  closed tasks all use `rejected`).
- `## Resolution` section appended explaining the task is obsolete:
  the DAG fix is subsumed by s0010 because there is no longer a
  `config` module to decouple from `views`.

**Update — [[s0007-artifacts-os-views-module]]:**
- `views` reclaims ownership of `ViewConfig` and `ViewsConfig` —
  both now defined in `views.models`, not `core.models`. (This
  reverses one of the t0019 movements; t0019's rationale is
  obsolete now that `core` no longer parses view entries.)
- New `ViewsSettings(core.Settings)` subclass added to the public
  API with a `from_base(base)` parser. Typical caller flow shown
  in `### ViewsSettings`:

  ```python
  base = load_settings(path)
  settings = ViewsSettings.from_base(base)
  ```

- Public API export list now includes `ViewConfig`, `ViewsConfig`,
  `ViewsSettings`.
- Scope Boundary updated: `views` now owns view-section parsing
  (was attributed to `core.load_settings` in the prior revision).
- Settings YAML Schema closing line updated to point at
  `ViewsSettings.from_base` and a private `_parse_view` helper
  local to `views`.

### Notes on task-spec deviations

Two course-corrections after review pulled the spec further from
its original requirement #1:

1. **Dropped OpenStation-specific dataclasses.** The task spec
   listed `RunConfig`, `TmuxConfig`, `DefaultsConfig`,
   `ShowDefaults` for `core.models`. Those describe
   OpenStation-specific concerns (detached task runner, tmux
   backend, `cli show` editor default) that don't belong in a
   library-level schema. Removed from `core.models`; OpenStation
   defines its own `Settings` subclass for them.

2. **`ViewConfig` / `ViewsConfig` moved back to `views.models`.**
   The task spec listed them in `core.models`. After tightening
   the layering — `core` no longer parses any module's section —
   they belong with the module that owns the parser. This also
   reverses one direction of t0019, which is fine because t0019's
   rationale (decoupling `config` from `views`) was already
   obsoleted by folding settings into `core`.

The original verification list still reads as written; flagging
here so the reviewer can re-evaluate.

### Decisions worth flagging

- **`status: superseded` on s0009** — the spec kind enum
  (`openstation/kinds/spec.json`) currently has only
  `draft|review|approved|deprecated`. The task spec explicitly
  asked for `superseded`, which is more semantically precise
  (replaced by a named successor) than `deprecated`. I applied
  the literal value as requested rather than substituting
  `deprecated`. If validation later tightens, either add
  `superseded` to the enum or migrate to `deprecated` — both
  options are easy.
- **t0019 closed status** — the lifecycle docs and CLI enforce
  `rejected` rather than `cancelled`; I used `rejected` (the value
  observed in other closed tasks) per the task's explicit
  fallback note. Required `--force` because the task was
  previously in `done`; this is a reasonable use of force —
  re-classifying a completed task as obsolete given the design
  pivot.

## Downstream

- The spec kind enum (`openstation/kinds/spec.json`) does not
  list `superseded`; consider adding it (or migrating to
  `deprecated` if a single retirement state is preferred).
- When implementation of s0010 lands, `core/__init__.py` and
  `core/models.py` will need to export the new symbols. Out of
  scope for this spec task.
- A write-API spec is deferred until a real write-consumer task
  is filed; the principle is captured in s0010 § Future Work to
  prevent the convention from being lost.
