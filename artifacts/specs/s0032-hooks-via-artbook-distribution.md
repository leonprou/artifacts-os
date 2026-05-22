---
kind: spec
id: s0032
name: hooks-via-artbook-distribution
status: draft
task: "[[t0179-spec-hooks-via-artbook-distribution]]"
created: 2026-05-22
agent: architect
---

# Hooks-Via-Artbook Distribution + Directory-Storage Kinds

Locks the technical contract for the parent feature
[[t0178-ship-hooks-via-artbook-distribution]], built on the design
brainstorm [[n0018-hooks-via-artbook-design-brainstorm]].

This is a **combined spec** (D12 below). It defines, end-to-end:

1. A new `x-storage: directory` primitive for artifact kinds whose
   storage unit is a directory bundle rather than a single file.
2. A new `kind: hook` registered against that primitive, with a
   manifest schema, the directory-bundle layout, and the loader
   contract.
3. The `.active/` symlink promotion mechanism — operator-owned
   activation state that survives a re-pull of the registry.
4. The CLI surface for `artifacts hook list|show|promote|demote`
   plus integration with the existing `artifacts list --kind hook`.
5. A new artbook book type — declared via a new manifest field —
   that carries hook registries from a distro to a consumer.
6. The catalogue of events the new mechanism emits.
7. The legacy `artifacts.yaml hooks:` coexistence policy and
   soft-deprecation path.

Scope (D8 from n0018): artifacts-os mechanism only. OpenStation
adoption, skills-as-kind migration, cryptographic trust posture,
the `--attach` create flag, and a one-shot migration tool are
explicitly **out of scope** for the parent task; they are flagged
as fast-follows or sibling tasks where relevant.

---

## 1. Locked Decisions

The decisions below are numbered `D101…` to avoid collision with
the parent decision tables in s0029 and s0031.

| ID | Decision | Rationale |
|----|----------|-----------|
| D101 | Hook is a first-class artifact kind: `kind: hook`, non-numbered, slug-as-ID. | Matches `agent` kind shape (n0018 §1); gives `artifacts list --kind hook`, wikilinks, events for free. |
| D102 | Storage unit is a directory bundle (Option A from n0018 §2): `artifacts/hooks/<slug>/<slug>.md` + arbitrary sibling files. | Inline-only and substantial-script hooks share one storage shape (n0018 framings table, row D). |
| D103 | Directory storage is declared by a new `x-storage` kind property, not hard-coded for `hook`. | Same primitive must serve skills next (n0018 §4); generic mechanism beats a hook special case. |
| D104 | `x-storage` field shape: `"x-storage": "directory"` (single string, two known values: `file` default and `directory`). | Reads well in `kind.json` next to existing `x-dir`, `x-numbered`. Stringly-typed leaves room for `bundle` or `recursive-directory` later without rename. |
| D105 | Manifest filename template: `x-manifest-name: "{slug}.md"` default; `{slug}`, `{id}`, `{name}`, `{stem}` substitutions allowed. | Lets skills declare `SKILL.md` later without code change (n0018 open question 3). |
| D106 | Sibling-file path resolution rule: action `command:` and other manifest-side path fields resolve relative to the **manifest's containing directory** (not vault root, not CWD). | Bundle is portable; copying the directory anywhere keeps internal references intact. |
| D107 | Activation lives outside the manifest, as a filesystem symlink in `artifacts/hooks/.active/<slug>`. | Pull (distro-owned) and activation (consumer-owned) cannot share a frontmatter field without re-pull clobbering operator choice (n0018 §5). |
| D108 | `.active/` directory name: literal `.active/` (dotfile-prefixed, sibling to bundle dirs). | Dotfile shields the directory from naive `--kind hook` walks; sibling-of-bundles keeps both pieces in one git subtree. |
| D109 | `.active/` is tracked in git. | Hooks are project behaviour; activation changes are PR-reviewable, CI-consistent (n0018 §6). |
| D110 | Symlink target shape: relative symlink pointing at the **manifest file**, not the bundle directory. Form: `artifacts/hooks/.active/auto-commit -> ../auto-commit/auto-commit.md`. | Loader can find both manifest (target) and bundle (`target.parent`) with one `os.readlink`. Relative form survives vault relocation (consistent with `promote:` symlinks, s0031). |
| D111 | Stale-symlink policy: `artifacts hook list` warns inline; `artifacts hook promote` refuses against a missing target; `artifacts hook list --prune` removes dangling entries. The loader silently skips a broken symlink and emits a `hook.skipped` event (see §5). | Stale symlinks are a guaranteed consequence of registry refresh; they must not abort the loader nor be invisible. |
| D112 | Loader dispatch: artifacts-os loader fires only hooks whose `host:` value is `artifacts-os` (case-sensitive). Other `host:` values are loaded and listed but never fired by this loader. | n0018 §7 — `host:` declares action context, not matcher vocabulary. OpenStation's loader will fire `host: openstation` against the same `.active/` tree. |
| D113 | `host:` enum policy: open set with a soft warning for unknown values. Reserved values: `artifacts-os`, `openstation`. The artifacts-os loader logs a one-line warning on first load for any other `host:` value (e.g. `host: jira-bot`) and skips firing them. | Open set unblocks third-party hosts; warning surfaces typos (`openstaion` → no fire, no error otherwise). |
| D114 | Legacy `artifacts.yaml hooks:` entries continue to load and fire. A single deprecation notice is printed once per process to stderr when the list is non-empty. No forced cutover, no migration tool in MVP. | n0018 §10 — soft deprecation. The list-form predates this spec and is already documented (`docs/hooks.md`). |
| D115 | `artifacts create --kind hook` writes the manifest only. No sibling files, no `--attach` flag. Operator authors `action.sh` (or similar) manually. | n0018 §9 — MVP UX. `--attach` is a fast-follow. |
| D116 | Artbook book type for hook registries is declared by a new top-level book field `kind: hook` (mapping form), distinct from the v1 `type:` field that v2 already rejects. | Existing v2 parser rejects any `type:` key on books (manifest.py § `_parse_book` D24 reject). Introducing `type:` again would either require relaxing that rule (regression risk) or live with a clash. `kind:` is a fresh field with a closed enum (`hook` only in MVP) and is forward-compatible with future book kinds. |
| D117 | `kind: hook` books opt out of promotion. The parser raises `ManifestError` if a `kind: hook` book declares `promote:`. | n0018 §8 + §pull = inert. The whole point of hook books is "canonical landing, operator promotes via `artifacts hook promote`, never on pull". |
| D118 | `kind: hook` books use the recurse walker semantics (one bundle directory per direct subdirectory of `src`), and the parser auto-sets `recurse: true` if omitted. Explicit `recurse: false` raises `ManifestError`. | Hook bundles are folder-of-folders by definition. Auto-set spares distro authors a redundant line; explicit-false catches mistakes. |
| D119 | Locally-authored hooks are **never auto-promoted**. Promotion is always an explicit `artifacts hook promote <slug>` step regardless of whether the hook was pulled or hand-written. | n0018 §5 — pull is inert. Treating hand-written hooks differently would be a surprise; the consumer's "yes I want this to fire" decision deserves the same explicit gesture either way. |
| D120 | Spec scope: combined single spec covering directory-storage primitive + hook kind + `.active/` mechanism + CLI + book type. | n0018 §12 weak prior; combined doc lets the developer execute against one contract without cross-spec drift. Sub-tasks (§9) decompose it for execution but share one spec. |

The 12 contract questions from n0018 "Open contract questions"
are answered in §10 below, each cross-referenced to the relevant
D101–D120 row above.

---

## 2. Directory-Storage Kinds Primitive

### 2.1 `kind.json` extensions

Two new optional fields are added to the `kind.json` schema. Both
are no-ops on existing kinds (default to the file-storage shape).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `x-storage` | string enum | `"file"` | Storage unit shape. `"file"` (existing behaviour, single `.md` per artifact) or `"directory"` (bundle directory per artifact; manifest filename derived from `x-manifest-name`). |
| `x-manifest-name` | string template | `"{slug}.md"` | Only consulted when `x-storage: directory`. Template for the manifest file inside the bundle directory. Substitutions: `{slug}` (always available), `{id}`, `{name}` (alias of `{slug}`), `{stem}` (`{id}-{slug}` for numbered, `{slug}` for non-numbered). |

Validation rules (applied in `Registry._load_vault_kinds`):

- Unknown `x-storage` value → `ValidationError` at load time.
- `x-manifest-name` set on a kind without `x-storage: directory` →
  `ValidationError` (signals a likely authoring mistake; the
  default is `{slug}.md` so explicit setting on a file kind has
  no use).
- Manifest template substitutions referencing unknown tokens →
  `ValidationError` at load time (fail fast, before any artifact
  is created).

`KindDef` (in `src/artifacts_os/core/models.py`) gains two
matching fields:

```python
@dataclass
class KindDef:
    # … existing fields …
    storage: str = "file"          # "file" | "directory"
    manifest_name: str = "{slug}.md"
```

The registry sets both from `kind.json`. Existing code that
treats every kind as file-shaped continues to work because the
default is `"file"`.

### 2.2 `core.create` directory mode

`store.create` branches on `kd.storage`:

| `kd.storage` | Behaviour |
|--------------|-----------|
| `"file"` (default) | Existing path: `mkdir <kind.dir>; write {stem}.md`. Unchanged. |
| `"directory"` | New path: `mkdir <kind.dir>/<stem>/; write <kind.dir>/<stem>/<manifest_name>`. |

Atomic-write semantics are preserved: the manifest is created
with `O_CREAT | O_EXCL` inside the freshly-`mkdir`-ed bundle dir.
Race on `mkdir` is handled by the same retry loop used for
numbered-id allocation today (`exist_ok=True` on the outer
directory, `O_EXCL` on the manifest path).

Returned `Artifact.path` is the **manifest file path**, not the
bundle directory. Callers that need the bundle dir derive it as
`path.parent`. The events stream emits `path = <manifest path>`,
consistent with file-kind events.

### 2.3 Discovery and listing

`discover.iter_artifacts` (and downstream `list`, `show`, `tree`)
must walk one level deeper for directory kinds:

- File kind: `artifacts/<dir>/*.md`.
- Directory kind: `artifacts/<dir>/*/<manifest_name>` after
  substituting `{slug}`/`{stem}` per directory name. Bundle
  directories whose manifest is missing are silently skipped
  (warning at most once per `list` invocation), preventing a
  half-authored bundle from breaking discovery.

A bundle directory whose name begins with `.` (e.g. `.active/`)
is always excluded from `--kind hook` discovery. This is the
only structural use of dot-prefixed bundle names; the rule is
documented in `docs/adding-a-kind.md` § "Directory Storage" and
applies uniformly to any kind that opts into `x-storage: directory`.

### 2.4 Update / delete

- `core.update` (frontmatter-only) is unchanged: it edits the
  manifest file's frontmatter. Body is preserved verbatim per
  existing invariant.
- Delete is **not** added by this spec. The MVP rule: bundle
  directories are removed manually with `rm -rf
  artifacts/hooks/<slug>/`; `.active/` symlinks dangle and are
  removed by `artifacts hook list --prune` (D111). A future
  `artifacts delete` verb would handle both kinds uniformly.

---

## 3. Hook Kind

### 3.1 Registration

A new `artifacts/kinds/hook/` folder is added with both
`kind.json` and `ARTIFACT.md`. The kind ships in the artifacts-os
distro's `kinds` book (existing book in `artbook.yaml`); consumers
that already pull `kinds` receive the hook kind automatically on
their next `artifacts book pull kinds`.

`artifacts/kinds/hook/kind.json`:

```json
{
  "x-dir": "hooks",
  "x-prefix": "",
  "x-numbered": false,
  "x-storage": "directory",
  "x-manifest-name": "{slug}.md",
  "x-columns": ["name", "host", "active", "matcher"],
  "title": "Hook",
  "type": "object",
  "required": ["kind", "name", "host", "matcher", "action"],
  "properties": {
    "kind":   { "type": "string", "const": "hook" },
    "name":   { "type": "string", "description": "Slug; also the bundle directory name." },
    "host":   { "type": "string", "description": "Loader that should fire this hook (e.g. 'artifacts-os', 'openstation')." },
    "matcher": {
      "type": "object",
      "description": "Event-matcher object — same vocabulary as artifacts.yaml hooks: matcher.",
      "additionalProperties": true
    },
    "action": {
      "type": "object",
      "description": "Action contract — same shape as artifacts.yaml hooks: action.",
      "required": ["type"],
      "additionalProperties": true
    },
    "phase":    { "enum": ["pre", "post"], "default": "post" },
    "blocking": { "type": "boolean", "default": false },
    "timeout":  { "type": "integer", "default": 30 }
  }
}
```

`ARTIFACT.md` follows the standard contract (`docs/adding-a-kind.md`)
with a `description` field that distinguishes hook from agent /
skill (verb: "Defines a reactive rule…", trigger: "use when a
declarative matcher + action must be shipped together").

### 3.2 Bundle layout

```
artifacts/hooks/
  auto-commit/
    auto-commit.md             # manifest (frontmatter + optional prose body)
    action.sh                  # +x sibling; referenced by manifest action.command
  notify-review/
    notify-review.md           # inline-only — no siblings
  lint-task/
    lint-task.md
    lint-task.py               # +x sibling
    helpers.py                 # non-+x helper sourced by lint-task.py
  .active/                     # operator-managed symlinks (see §4)
    auto-commit -> ../auto-commit/auto-commit.md
```

The manifest body is freeform markdown. The loader reads only the
frontmatter (`matcher`, `action`, `phase`, `blocking`, `timeout`,
`host`); the body is operator-facing documentation.

### 3.3 Manifest schema

Frontmatter contract:

```yaml
---
kind: hook
name: auto-commit
host: openstation
matcher:
  event: artifact.status_changed
  after: done
action:
  type: shell
  command: ./action.sh        # resolved relative to manifest dir (D106)
  timeout: 30
phase: post
blocking: false
---
```

Fields:

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `kind` | yes | `"hook"` | Discriminator. |
| `name` | yes | string | Slug. Must equal bundle directory name. |
| `host` | yes | string | Loader dispatch (D112). |
| `matcher` | yes | mapping | Same matcher key vocabulary as `artifacts.yaml` `hooks[].matcher` (see `src/artifacts_os/hooks/loader.py` `_VALID_MATCHER_KEYS`). |
| `action` | yes | mapping | Same action shape as `artifacts.yaml` `hooks[].action`. `action.command` paths beginning with `./` or relative are resolved per D106. |
| `phase` | no | `"pre"` \| `"post"` | Default `"post"`. |
| `blocking` | no | boolean | Default `false`. Only meaningful when `phase: pre`. |
| `timeout` | no | integer (seconds) | Default 30. |

Validation: same matcher/action validators that `load_hooks` uses
today (`_is_valid_matcher_key`, `action_from_config`) are reused
verbatim. The directory-bundle path does not duplicate validation
logic; it constructs an in-memory `Hook` dataclass and pushes it
through the existing pipeline.

### 3.4 Sibling file resolution (D106)

When `action.command` is a relative path (does not begin with `/`,
does not begin with `$`), it is resolved relative to the manifest
file's parent directory at load time. The resolved absolute path
is passed to the action runner.

Examples (manifest at `artifacts/hooks/auto-commit/auto-commit.md`):

| `command:` in manifest | Resolved path |
|------------------------|---------------|
| `./action.sh` | `<vault>/artifacts/hooks/auto-commit/action.sh` |
| `action.sh` | `<vault>/artifacts/hooks/auto-commit/action.sh` |
| `helpers/run.sh` | `<vault>/artifacts/hooks/auto-commit/helpers/run.sh` |
| `/usr/local/bin/foo` | `/usr/local/bin/foo` (absolute, unchanged) |
| `bin/global-thing` | `<vault>/artifacts/hooks/auto-commit/bin/global-thing` (relative ⇒ bundle-local) |

A legacy `artifacts.yaml` hook continues to resolve commands
relative to the **vault root** (its existing behaviour); the
divergence is documented in `docs/hooks.md`.

---

## 4. Activation: `.active/` Promotion Mechanism

### 4.1 Layout (D107, D108, D110)

```
artifacts/hooks/
  auto-commit/             ← canonical bundle (distro-owned)
    auto-commit.md
    action.sh
  .active/                 ← activation state (consumer-owned)
    auto-commit -> ../auto-commit/auto-commit.md
```

Each entry in `.active/` is a relative symlink from the slug to
the manifest file. The slug is the symlink filename, never the
manifest's slug field (which is read but not trusted for naming).

`.active/` is created on demand by `artifacts hook promote`. It
is tracked in git (D109). The directory is excluded from
`--kind hook` listings (§2.3).

### 4.2 Promote / demote semantics

`artifacts hook promote <slug>`:

1. Resolve `<slug>` against the canonical registry
   (`artifacts/hooks/<slug>/<manifest_name>` must exist). If
   absent: error 2, "no hook bundle named '<slug>'".
2. `mkdir -p artifacts/hooks/.active/`.
3. `os.symlink('../<slug>/<manifest_name>', '<.active>/<slug>')`
   with the same OSError fallback policy as `promote:` symlinks
   (s0031): on `OSError`, fall back to a `.json` stub file
   containing `{"target": "../<slug>/…"}`. The loader recognises
   both forms.
4. Emit `hook.promoted` event (§5).
5. Exit 0; print a one-line summary.

If the symlink already exists and points at the same target:
no-op, exit 0 (idempotent).

If it exists and points elsewhere: error 1, "hook <slug> already
promoted to <existing-target>; demote first or use `--force`".

`artifacts hook demote <slug>`:

1. If `.active/<slug>` does not exist: no-op, exit 0.
2. `os.unlink('.active/<slug>')`.
3. Emit `hook.demoted` event.
4. Exit 0.

### 4.3 Re-pull preservation

`artifacts book pull <hook-book>` (D116) overwrites bundle
directories under `artifacts/hooks/`. It does **not** touch
`artifacts/hooks/.active/`. The artbook state file
(`artifacts/.artbook/state.json`, s0031 §3) records files
written under the bundle dirs only; `.active/` is invisible to
the pull pipeline.

Consequence: if a re-pull removes a bundle that was previously
promoted, the `.active/<slug>` symlink becomes dangling. The
loader skips it (D111) and emits `hook.skipped`; the operator
sees the warning on next `artifacts hook list` and runs
`--prune` or re-creates the bundle.

### 4.4 Concurrency

Promote and demote are filesystem-atomic (single `symlink` /
`unlink` call). Concurrent invocations are serialised at the
syscall layer; no lock file is added.

---

## 5. Events Emitted

The events catalogue gains four hook-mechanism events on top of
the existing `hook.fired` / `hook.failed`. All are post-phase
(written to the JSONL stream) and dispatched through
`core.events._dispatch`.

| Event type | When it fires | Key payload fields |
|------------|---------------|--------------------|
| `hook.promoted` | After `.active/<slug>` symlink is created (or stub file written on OSError fallback). | `hook` (slug), `bundle_path`, `manifest_path`, `mode` (`symlink` \| `stub`) |
| `hook.demoted` | After `.active/<slug>` is removed. | `hook` (slug), `bundle_path`, `manifest_path` |
| `hook.pulled` | After a `kind: hook` book finishes writing its bundles. Emitted once per book pull, with the list of slugs written/overwritten. | `book` (name), `written` (list of slugs), `overwritten` (list of slugs), `removed` (list of slugs that were in the previous pull's state but absent now) |
| `hook.skipped` | When the loader encounters a `.active/` entry pointing at a missing or unparseable manifest. Emitted once per `notify()` cycle per skipped slug. | `hook` (slug), `link_path`, `reason` (`missing-target` \| `parse-error`) |

Existing `hook.fired` / `hook.failed` semantics are preserved; the
new directory-bundle hooks reuse the same dispatch path. Payloads
for `hook.fired` / `hook.failed` gain an optional `source` key
(`"yaml"` for legacy `artifacts.yaml` hooks, `"bundle"` for
directory hooks) so downstream consumers can distinguish the
two forms.

The catalogue gate stays closed (s0025 § C2): the four new event
types are added to `artifacts_os.events.catalog.ALL_EVENT_TYPES`
in the same commit as the loader changes. Adding any further
events requires a spec revision.

---

## 6. Loader Contract

### 6.1 Sources merged at load time

The hook loader (`src/artifacts_os/hooks/loader.py`) loads hooks
from two sources, in this fixed order:

1. **Legacy YAML list** — `artifacts.yaml` `hooks:` (existing
   `load_hooks` path, D114). Each entry yields a `Hook` with
   `source="yaml"`.
2. **Bundle registry** — `artifacts/hooks/.active/*` symlinks.
   Each entry yields a `Hook` with `source="bundle"`. Walk:
   - For each non-dotfile entry in `.active/`, read the symlink
     target (or stub `target` field on fallback).
   - Resolve to an absolute manifest path; if it does not exist
     or is not readable, emit `hook.skipped` and continue.
   - Parse the manifest frontmatter through the existing matcher
     / action validators (`_is_valid_matcher_key`,
     `action_from_config`).
   - If `host` is not `"artifacts-os"`, the hook is **loaded and
     listed** (so `artifacts hook list` shows it) but **not added
     to the fire-list** for this loader (D112). The `host:` value
     is preserved on the in-memory `Hook` and surfaced in the
     `hook.skipped`-style metadata for `artifacts hook list
     --filter active=true`.

Merge order matters only for `artifacts hook list` display; for
the matcher engine, the two sources are flattened into one list
and evaluated in declaration order (yaml entries first, then
bundle entries sorted by slug).

### 6.2 Host dispatch (D112, D113)

```
load_hooks(root) ->
  for hook in yaml_hooks(root):
      yield hook                                 # source=yaml, host implicit "artifacts-os"
  for slug in sorted(walk_active(root)):
      hook = read_bundle(slug)
      if hook.host == "artifacts-os":
          yield hook                             # this loader fires it
      elif hook.host in {"openstation", …}:
          # known foreign host — skip silently in fire-list, list visibly
          skip_fire(hook)
      else:
          warn_once_per_host(hook.host)
          skip_fire(hook)
```

YAML-list hooks have no `host:` field; they are implicitly
treated as `host: artifacts-os` for back-compat. This is the
**only** privileged behaviour the yaml form retains.

### 6.3 Symlink resolution

Resolution sequence for one `.active/` entry:

1. Read the link target via `os.readlink`. If the entry is a
   plain file ending in `.json` (OSError-fallback stub), parse
   it and use the `target` field as the link target string.
2. Join the target string to `.active/`'s parent
   (`artifacts/hooks/`) using `Path` semantics. The resolved
   path must lie under `artifacts/hooks/` — any path that
   escapes raises `BundleError` and the loader skips with
   reason `escape-attempt`.
3. Verify the resolved path ends in `<manifest_name>` after
   template substitution. Other targets are rejected.
4. Read the manifest file; pass its frontmatter to the
   existing parser.

### 6.4 Legacy coexistence (D114)

`load_hooks` continues to emit the existing
`load_hooks_from_yaml` (renamed for clarity) plus a new
`load_hooks_from_active` call. The public entry point
`notify()` (the registered emitter) is unchanged in signature;
it now matches against the union of both sources.

A single deprecation notice is printed to stderr at most once
per process when the yaml list is non-empty:

```
warning: artifacts.yaml `hooks:` list is deprecated.
         Migrate each entry to a bundle under artifacts/hooks/<slug>/
         and promote it with `artifacts hook promote <slug>`.
         See docs/hooks.md § "Migrating from the legacy hooks list".
```

The notice is suppressible by `ARTIFACTS_HOOKS_LEGACY_QUIET=1`
for CI / scripted environments. No migration tool ships in MVP;
the optional one-shot converter from n0018 open-question 6 is a
fast-follow.

### 6.5 Reentrancy and cache

The existing `_notify_active` reentrancy guard and the
`_hooks_cache` / `invalidate_cache()` mechanism extend to bundle
hooks without change. The cache key remains the vault root; both
yaml and bundle sources are re-read on `invalidate_cache()`.

---

## 7. CLI Surface

All verbs are flat (CLAUDE.md CLI conventions), default to a
Rich table, accept `-j` for JSON, and place filter flags at the
top level. The verbs live in a new
`src/artifacts_os/cli/commands/hook.py`.

### 7.1 `artifacts hook list`

```
artifacts hook list [--host HOST] [--active | --inactive]
                    [--source yaml|bundle] [--tail [N]] [-j]
```

Default columns: `name`, `host`, `active`, `phase`, `event`,
`source`. The `active` column is `yes` if `.active/<slug>` exists
and resolves; `dangling` if the symlink exists but the target is
missing; `no` otherwise. The `source` column is `yaml` or
`bundle`.

| Flag | Default | Effect |
|------|---------|--------|
| `--host HOST` | (all) | Filter by `host:` value (repeatable). |
| `--active` | off | Show only hooks whose `.active/` symlink resolves. |
| `--inactive` | off | Show only hooks without an `.active/` symlink. Mutually exclusive with `--active`. |
| `--source {yaml,bundle}` | (both) | Restrict to one source. |
| `--tail [N]` | off (default 50 with bare flag) | Universal "last N" primitive; applied after filters, slice on the displayed table. |
| `-j` / `--json` | off | One JSON object per hook to stdout, one per line. Schema documented in `cli/README.md`. |

`artifacts list --kind hook` is a strict subset: it shows the
five built-in artifact columns (`id`, `name`, `host`, etc.) using
the `x-columns` declared in `hook/kind.json` (D101). The two
commands compose: `list --kind hook` is the artifact-shaped view
of the same data; `hook list` is the lifecycle-shaped view that
adds `active`, `source`, and the dangling-target colouring.

### 7.2 `artifacts hook show <slug>`

```
artifacts hook show <slug> [-j]
```

Default output (Rich): manifest frontmatter as a key/value table,
a section listing the bundle's sibling files (path + `+x` flag
+ size), the resolved active state, and a tail of the most recent
`hook.fired` / `hook.failed` events from the events stream
(default last 5). `-j` returns a single JSON object with the
same fields.

### 7.3 `artifacts hook promote <slug>` / `demote <slug>`

```
artifacts hook promote <slug> [--force] [-j]
artifacts hook demote  <slug> [-j]
```

Semantics in §4.2. `--force` on promote replaces an existing
divergent symlink without erroring. `-j` returns
`{"ok": true, "slug": "...", "target": "...", "mode": "symlink|stub"}`.

### 7.4 `artifacts hook list --prune`

```
artifacts hook list --prune [--dry-run] [-j]
```

Removes any `.active/` entry whose target does not resolve to a
manifest file. With `--dry-run`, prints the list it would remove
but performs no filesystem changes. Emits a `hook.demoted` event
per removed entry (with a `reason: "prune"` payload key).

### 7.5 Exit codes

Aligned with the rest of the CLI: 0 success, 1 user error
(unknown slug, divergent promote without `--force`), 2
configuration error (broken manifest, malformed `.active/`), 3
filesystem error (permissions). Documented in
`src/artifacts_os/cli/README.md`.

---

## 8. Artbook `kind: hook` Book Type

### 8.1 Manifest field

Adds a single optional field on each book entry in
`artbook.yaml`:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `kind` | string enum | (unset → generic book) | Closed enum, MVP: `"hook"` only. Declares the book ships a hook registry. |

Parser (`src/artifacts_os/artbook/manifest.py`):

- `kind: hook` ⇒ set a `kind = "hook"` field on the `Book`
  dataclass; auto-set `recurse: true` if omitted (D118);
  reject explicit `recurse: false` (`ManifestError`).
- `kind: hook` + `promote:` ⇒ `ManifestError` (D117): "book
  '<name>' has `kind: hook`; hook books cannot declare
  `promote:` — activation is an explicit operator step".
- Unknown `kind:` values ⇒ `ManifestError` (closed enum;
  forward-compat handled by spec revision, not silent
  acceptance).
- `kind:` is **not** to be confused with the v1 `type:` field
  (D116). The existing rejection of `type:` is preserved
  verbatim; the new `kind:` field is parsed independently.

### 8.2 Pull semantics

A `kind: hook` book pulls bundle directories from `src` into
canonical landing (defaults to `artifacts/hooks/`, exactly the
canonical default per s0029 D37 since `basename(src)` is
typically `hooks`). The pull pipeline writes each bundle
verbatim (manifest + siblings) and emits one `hook.pulled`
event per book (§5).

Promotion is **disabled** for hook books at the manifest level
(D117). The CLI `--no-promote` flag remains accepted for
uniformity but is a no-op against hook books.

### 8.3 Worked example — `artifacts-os` distro

```yaml
# artifacts-os artbook.yaml (post-spec)
books:
  - name: agents
    src: artifacts/agents/
    promote: .claude/agents/
    description: Default agent specs.

  - name: kinds
    src: artifacts/kinds/
    description: Standard artifact kinds (task, note, spec, research, agent, hook).
    recurse: true

  - name: os-hooks
    src: artifacts/hooks/
    kind: hook                         # ← new
    description: artifacts-os lifecycle hooks (auto-commit, auto-verify, …).
    # promote: forbidden (D117); recurse: true is auto-set (D118)
```

A consumer running `artifacts book pull os-hooks` receives every
bundle directory under `src` in their `artifacts/hooks/`, no
activation. They follow up with `artifacts hook list`
(see what's available) and `artifacts hook promote auto-commit`
(activate the ones they want). A subsequent re-pull overwrites
the bundles but leaves their `.active/auto-commit` symlink
intact (§4.3).

### 8.4 Contrast with existing book types

| Property | `agents` (default) | `kinds` (default + `recurse`) | `os-hooks` (`kind: hook`) |
|----------|-------------------|-------------------------------|---------------------------|
| Walker | flat | recurse | recurse (auto-set) |
| Canonical landing | `artifacts/<basename(src)>/` | same | same |
| `promote:` allowed? | yes | yes (typically omitted) | **no — ManifestError** |
| Auto-activate on pull? | n/a (inert content) | n/a | **no — explicit operator step required** |
| Required follow-up? | none | none | `artifacts hook promote <slug>` per hook to activate |

The defining property of `kind: hook` is the **absence** of
auto-promote and the requirement of an explicit `hook promote`
step. Everything else reuses existing book infrastructure.

---

## 9. Implementation Sub-Task Decomposition

The parent feature [[t0178-ship-hooks-via-artbook-distribution]]
is decomposed into the four implementation sub-tasks below. They
must land in this order — each depends on the previous.

| Order | Sub-task slug | Scope | Verification anchors (parent) |
|-------|---------------|-------|-------------------------------|
| 1 | `add-directory-storage-primitive` | Implement §2 in full: `x-storage` + `x-manifest-name` in `kind.json`; `KindDef.storage` / `manifest_name`; branch in `core.create`; branch in `discover.iter_artifacts`; tests for both file and directory kinds; `docs/adding-a-kind.md` § "Directory Storage" written. | "Directory-storage primitive lands under `core` and is exercised by an in-repo test kind." |
| 2 | `add-hook-kind-and-loader` | Implement §3 + §6: `artifacts/kinds/hook/{kind.json, ARTIFACT.md}`; loader merges yaml + `.active/` sources; host dispatch; legacy deprecation notice; events `hook.skipped`. New `hook.fired`/`hook.failed` `source:` key. `docs/hooks.md` updated. | "Hook kind registers; loader fires bundle hooks for `host: artifacts-os` and silently skips others; legacy yaml list still fires with deprecation warning." |
| 3 | `add-active-promotion-and-cli` | Implement §4 + §7: `.active/` symlink mechanism; `artifacts hook list|show|promote|demote|--prune`; events `hook.promoted` / `hook.demoted` / `hook.pulled` (the last is wired by sub-task 4 but the event constant lands here); JSON output; CLI README section. | "`artifacts hook promote` survives a hook-book re-pull; `artifacts hook list --prune` removes stale symlinks." |
| 4 | `add-artbook-hook-book-type` | Implement §8: `kind:` field in `artbook.yaml`; parser updates and ManifestError messages; pull-pipeline emits `hook.pulled`; `docs/artbook.md` updated; the `artifacts-os` distro's own `artbook.yaml` gains the `os-hooks` book pointing at `artifacts/hooks/`. | "`artifacts book pull os-hooks` lands inert bundles; `artifacts hook list` shows them; re-pull preserves `.active/` state." |

Cross-cutting verification (lifted to the parent task once the
spec is approved):

- [ ] All four sub-tasks done and merged.
- [ ] End-to-end demo in `tests/integration/test_hooks_via_artbook.py`:
      author hook in source repo → `book pull` in fresh consumer
      → `hook promote` → CRUD event fires the hook → re-pull
      preserves `.active/`.
- [ ] `docs/hooks.md`, `docs/artbook.md`, `docs/adding-a-kind.md`,
      `docs/events.md` updated.
- [ ] `n0017-hook-scripts-not-installed-in-consumer` closed by
      the demo.

---

## 10. Open Contract Questions (resolved)

Each of the 12 questions enumerated in t0179's requirements is
answered below. Question 11 ("auto-promote for locally-authored
hooks") and 12 ("combined-vs-split spec decision") are the two
that extend n0018's original list of 10.

| # | Question | Resolution | Cross-ref |
|---|----------|-----------|-----------|
| 1 | `.active/` naming | `.active/` (literal, dotfile-prefixed, sibling to bundles). | D108 |
| 2 | `x-storage` field shape | `"x-storage": "directory"` (single string, enum `{file, directory}`). | D104 |
| 3 | `x-manifest-name` template default | `"{slug}.md"`; substitutions `{slug}`, `{id}`, `{name}`, `{stem}`. | D105 |
| 4 | Sibling file resolution rule | Relative paths in `action.command` resolve against the manifest's parent directory. | D106, §3.4 |
| 5 | Stale-symlink cleanup | List warns, promote refuses, loader silently skips and emits `hook.skipped`, `--prune` removes. | D111, §5, §7.4 |
| 6 | Legacy `hooks:` migration tool scope | No tool in MVP. Soft deprecation notice (once per process, suppressible). Optional fast-follow. | D114, §6.4 |
| 7 | `--attach` flag treatment | Deferred. MVP `artifacts create --kind hook` writes manifest only. | D115 |
| 8 | `host:` enum policy | Open set; reserved values `{artifacts-os, openstation}`; warn once per unknown value; never reject. | D112, D113 |
| 9 | Skills-as-kind sibling relationship | Skills migration is a separate task; this spec deliberately makes the directory-storage primitive (§2) reusable by skills without code change. Skills task will set `x-storage: directory`, `x-manifest-name: "SKILL.md"`, and consume the same `kind.json` extension. | D103 (mechanism), §2.1 (template), n0018 §4 |
| 10 | Artbook book-type semantic differences | New `kind: hook` field; opts out of promotion; auto-sets `recurse: true`; rejects `promote:`; emits `hook.pulled` on pull. Otherwise reuses generic book infrastructure. | D116–D118, §8 |
| 11 | Auto-promote policy for locally-authored hooks | Never auto-promote, regardless of origin (pulled or hand-written). The consumer's "yes I want this to fire" decision is always explicit via `artifacts hook promote`. | D119, §4 |
| 12 | Combined vs. split spec decision | Combined single spec (this document). Decomposition for execution lives in §9, not as separate specs. | D120 |

---

## 11. Out of Scope

Carried forward verbatim from n0018 §12 "Out of scope (per
n0018)" for the parent task t0178:

- OpenStation adoption of the new mechanism (separate task in the
  OpenStation repo; OpenStation's loader will reuse this spec
  unchanged).
- Skills-as-kind migration (sibling task; same primitive, see Q9).
- Cryptographic trust posture for distros (no signing, no
  attestation in MVP — out of scope across the parent feature).
- `--attach <path>` flag for `artifacts create --kind hook`
  (fast-follow; see D115).
- One-shot migration tool for `artifacts.yaml hooks:` → bundles
  (fast-follow; see D114).
- `artifacts delete --kind hook <slug>` verb (§2.4) — future
  generic delete mechanism, not hook-specific.

---

## 12. Cross-References

- Source brainstorm — [[n0018-hooks-via-artbook-design-brainstorm]]
- Triggering papercut — [[n0017-hook-scripts-not-installed-in-consumer]]
- Artbook MVP — [[s0029-artbook-mvp-distribution-model]]
- Artbook promotion — [[s0031-artbook-post-pull-artifact-promotion]]
- Promotion mechanism brainstorm — [[n0015-artbook-promotion-mechanism-design-brainstorm]]
- Existing hooks docs — `docs/hooks.md`
- Events catalogue (gate at `s0025-artifact-events`) — `docs/events.md`
- Kind-folder contract — `docs/adding-a-kind.md`
- CLI conventions — `CLAUDE.md` § "CLI Conventions"
- Parent feature task — [[t0178-ship-hooks-via-artbook-distribution]]
