---
kind: task
id: t0182
name: add-hook-kind-and-bundle
type: implementation
status: done
assignee: developer
owner: architect
parent: "[[t0178-ship-hooks-via-artbook-distribution]]"
depends_on:
  - "[[t0181-add-directory-storage-primitive-to]]"
created: 2026-05-22
started: 2026-05-24
completed: 2026-05-24
---

# Add Hook Kind, Bundle-Aware Loader, `.active/` Promotion + CLI Verbs

## Requirements

Implement [[s0032-hooks-via-artbook-distribution]] §3 + §4 + §6 +
§7 — the full hooks-as-artifacts module: kind registration,
bundle-aware loader with host dispatch, `.active/` promotion
mechanism, and the four `artifacts hooks …` CLI verbs.

**Scope merged from former t0183** (cancelled — PM decomposition
trim, 2026-05-24): the loader and promotion mechanism are one
coherent deliverable — the loader alone leaves a non-shippable
half-state with no way to activate anything. Single review pass,
single domain (`src/artifacts_os/hooks/` + `cli/commands/hooks.py`).

### Kind registration (§3)

- Add `artifacts/kinds/hook/` with `kind.json` (per §3.1 — sets
  `x-storage: directory`, `x-manifest-name: "{slug}.md"`,
  `x-numbered: false`, `x-columns`, full property schema for
  `kind`, `name`, `host`, `matcher`, `action`, `phase`,
  `blocking`, `timeout`) and the matching `ARTIFACT.md`.
- Manifest schema is enforced by the existing matcher/action
  validators reused from `src/artifacts_os/hooks/loader.py`
  (`_is_valid_matcher_key`, `action_from_config`) — do not
  duplicate validation logic.
- Sibling-file path resolution (§3.4 / D106): relative paths in
  `action.command` resolve against the manifest's parent
  directory at load time. Legacy yaml-list hooks keep the
  vault-root resolution rule (document the divergence in
  `docs/hooks.md`).

### Bundle-aware loader + host dispatch (§6)

- Loader split: rename existing path to `load_hooks_from_yaml`;
  add `load_hooks_from_active` that reads `.active/*` symlinks
  (or `.json` stub fallback), validates the resolved manifest
  is inside `artifacts/hooks/` (reject path escape with
  `BundleError`), parses frontmatter, and produces in-memory
  `Hook` records with `source="bundle"`.
- `load_hooks` returns yaml entries first, then bundle entries
  sorted by slug. Yaml entries are implicitly treated as
  `host: artifacts-os`; bundle entries respect their declared
  `host:`.
- Host dispatch (§6.2): bundle hooks with `host == "artifacts-os"`
  enter the fire-list; reserved foreign hosts (`openstation`)
  are loaded + listed but never fired; unknown hosts log a
  one-line warning once per process and are skipped from the
  fire-list (per D113).
- Legacy deprecation (§6.4 / D114): on first `load_hooks` call
  where the yaml list is non-empty, print the deprecation
  notice once to stderr. Suppress when
  `ARTIFACTS_HOOKS_LEGACY_QUIET=1`.
- Reentrancy + cache: confirm `_notify_active` guard and
  `_hooks_cache` / `invalidate_cache()` extend to bundle hooks
  unchanged.

### `.active/` promotion mechanism (§4)

- Promote semantics (§4.2):
  - Resolve `<slug>` against canonical registry; error 1 if no
    bundle.
  - `mkdir -p artifacts/hooks/.active/`.
  - `os.symlink('../<slug>/<manifest_name>',
    '<.active>/<slug>')`; OSError fallback writes a `.json`
    stub `{"target": "../<slug>/…"}` (mirror s0031 stub
    policy).
  - Idempotent if symlink already exists with same target.
  - Divergent target → error 1 unless `--force`.
  - Emit `hook.promoted` event.
- Demote semantics: unlink `.active/<slug>` if present (no-op
  otherwise), emit `hook.demoted`.
- `.active/` is tracked in git (D109) — ensure project
  `.gitignore` doesn't exclude it; test harness creates and
  reads it correctly.
- Re-pull preservation (§4.3): `.active/` is invisible to the
  artbook state file — confirm by inspecting how the artbook
  state writer is scoped (no change required here if it's
  bundle-write-only; document the contract).

### CLI verbs (§7)

Live in `src/artifacts_os/cli/commands/hooks.py`. All flat,
default Rich table, `-j` for JSON, top-level filter flags, per
CLAUDE.md conventions:

- `artifacts hooks list [--host HOST] [--active | --inactive]
  [--source yaml|bundle] [--tail [N]] [-j] [--prune
  [--dry-run]]`. Columns: `name`, `host`, `active`, `phase`,
  `event`, `source`. `active` value: `yes` | `dangling` | `no`.
- `artifacts hooks show <slug> [-j]`: manifest frontmatter table
  + sibling files (path, `+x`, size) + resolved active state +
  tail of recent `hook.fired`/`hook.failed` (last 5 default).
- `artifacts hooks promote <slug> [--force] [-j]`.
- `artifacts hooks demote <slug> [-j]`.
- `--prune` removes `.active/` entries whose target does not
  resolve, emits `hook.demoted` with `reason: "prune"`,
  supports `--dry-run`.
- Exit codes (§7.5): 0 success, 1 user error (unknown slug,
  divergent promote without `--force`), 2 configuration error
  (broken manifest, malformed `.active/`), 3 filesystem error
  (permissions).

### Events catalogue

- Add `hook.skipped`, `hook.promoted`, `hook.demoted` to
  `ALL_EVENT_TYPES` in `artifacts_os.events.catalog`.
- `hook.pulled` constant also lands here (emission in t0184) so
  the catalogue is complete before the artbook hook book ships.
- `hook.skipped` emitted from the loader for missing-target /
  parse-error / escape-attempt cases (one event per skipped
  slug per `notify()` cycle).
- Extend `hook.fired` / `hook.failed` payloads with an optional
  `source:` key (`"yaml"` | `"bundle"`).

### Tests

- Hook kind registers; `artifacts list --kind hook` returns
  pulled bundles (use t0181 directory walker).
- Bundle manifest parses; relative `action.command` resolves
  against bundle dir; absolute paths pass through.
- Loader merges yaml + bundle, sorted; host dispatch fires
  artifacts-os only.
- Foreign host (`openstation`) is loaded + listed, never fired.
- Unknown host (`jira-bot`) is skipped + warns once.
- Legacy deprecation notice prints once per process; respects
  `ARTIFACTS_HOOKS_LEGACY_QUIET=1`.
- `hook.skipped` event fires for missing target, parse error,
  and escape-attempt.
- Path-escape attempt (`..` outside `artifacts/hooks/`) is
  rejected.
- `hook.fired` / `hook.failed` payloads carry `source:`.
- Promote creates symlink with correct relative target.
- Promote idempotent on same target.
- Promote on divergent target without `--force` → exit 1; with
  `--force` → succeeds.
- Demote unlinks; no-op on absent slug.
- OSError stub fallback path (mock or `chmod`-restricted
  fixture); loader recognises both symlink and stub forms.
- `hooks list` table renders with `active` column.
- `hooks list --active` / `--inactive` / `--source` filters work.
- `hooks list -j` JSON shape stable.
- `hooks show <slug>` renders and `-j` JSON shape stable;
  sibling-file listing accurate.
- `hooks list --prune` removes dangling entries and emits
  `hook.demoted` with `reason: "prune"`; `--dry-run` is inert.
- Events `hook.promoted` / `hook.demoted` emitted at documented
  sites.

### Docs

- `docs/hooks.md` — new bundle form, `source:` distinction,
  sibling-file resolution divergence (bundle vs yaml), §
  "Promoting hooks" covering `.active/` model and
  promote/demote/show/list/prune flows, re-pull preservation
  guarantee, pointer to legacy migration story (no migration
  tool ships in MVP).
- `src/artifacts_os/cli/README.md` — new verbs and JSON
  schemas.

### Out of scope

Artbook `kind: hook` field, distro shipping the `os-hooks` book,
`hook.pulled` event *emission* (constant lands here, emission
lands in t0184), end-to-end integration test (lives in t0184).

## Progress

### 2026-05-24 19:15:17 — Incomplete run (r0195)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$2.28, turns=51

## Verification

- [ ] `artifacts/kinds/hook/{kind.json, ARTIFACT.md}` registered;
      `artifacts list --kind hook` returns bundles.
- [ ] Loader reads `.active/*` symlinks (and `.json` stubs),
      resolves manifest path, validates inside
      `artifacts/hooks/`, parses frontmatter through existing
      validators.
- [ ] Host dispatch fires `artifacts-os` only; reserved foreign
      hosts loaded + listed + not fired; unknown hosts warn once
      per process.
- [ ] Yaml-list deprecation notice prints once to stderr;
      `ARTIFACTS_HOOKS_LEGACY_QUIET=1` suppresses it.
- [ ] `hook.skipped`, `hook.promoted`, `hook.demoted`,
      `hook.pulled` added to `ALL_EVENT_TYPES`. `hook.skipped`
      emitted on missing-target / parse-error / escape-attempt.
- [ ] `hook.fired` / `hook.failed` payloads carry optional
      `source:` (`yaml` | `bundle`).
- [ ] Path-escape attempt outside `artifacts/hooks/` raises
      `BundleError` and is logged + skipped.
- [ ] Sibling-file resolution (D106) tested for `./action.sh`,
      `action.sh`, `helpers/x.sh`, `/abs/path`, `bin/foo`.
- [ ] `artifacts hooks promote <slug>` creates relative symlink
      `.active/<slug> -> ../<slug>/<manifest>`; idempotent;
      divergent target errors without `--force`.
- [ ] `artifacts hooks demote <slug>` unlinks; no-op on absent.
- [ ] OSError stub fallback writes `.json` with `target` field;
      loader recognises both forms.
- [ ] `artifacts hooks list` renders the documented columns;
      `active` is `yes` / `dangling` / `no`; filters
      (`--host`, `--active`, `--inactive`, `--source`,
      `--tail`) work; `-j` JSON is stable.
- [ ] `artifacts hooks show <slug>` renders frontmatter +
      sibling files + active state + recent events; `-j`
      stable.
- [ ] `artifacts hooks list --prune` removes dangling `.active/`
      entries and emits `hook.demoted` with `reason: "prune"`;
      `--dry-run` makes no FS changes.
- [ ] Exit codes match §7.5 (0/1/2/3).
- [ ] `.active/` survives a hook-book re-pull contract
      documented (full end-to-end fixture lives in t0184).
- [ ] `docs/hooks.md` updated (bundle form, resolution
      divergence, § "Promoting hooks") and `cli/README.md`
      updated.
- [ ] `pytest` green; t0181 regression tests still pass.
