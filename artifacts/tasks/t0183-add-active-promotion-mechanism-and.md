---
kind: task
id: t0183
name: add-active-promotion-mechanism-and
type: implementation
status: rejected
assignee: developer
owner: architect
parent: "[[t0178-ship-hooks-via-artbook-distribution]]"
depends_on:
  - "[[t0182-add-hook-kind-and-bundle]]"
created: 2026-05-22
---

# Add .Active Promotion Mechanism And Hook CLI Verbs

> **Cancelled (2026-05-24)** — scope folded into
> [[t0182-add-hook-kind-and-bundle]] by PM decomposition trim.
> The loader (§6) and `.active/` mechanism (§4) form one
> coherent deliverable — splitting them leaves a non-shippable
> half-state (loader can read bundles but nothing can be
> activated). Verification items below were merged verbatim
> into t0182's checklist.

## Requirements

Implement [[s0032-hooks-via-artbook-distribution]] §4 + §7: the
`.active/` symlink promotion mechanism and the four `artifacts
hook …` CLI verbs.

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
- Demote semantics (§4.2): unlink `.active/<slug>` if present
  (no-op otherwise), emit `hook.demoted`.
- `.active/` is tracked in git (D109) — add to project
  `.gitignore` allowlist if needed; ensure the test harness
  creates and reads it correctly.
- CLI verbs (§7) live in
  `src/artifacts_os/cli/commands/hooks.py`. All flat, default
  Rich table, `-j` for JSON, top-level filter flags, per
  CLAUDE.md conventions:
  - `artifacts hooks list [--host HOST] [--active | --inactive]
    [--source yaml|bundle] [--tail [N]] [-j] [--prune
    [--dry-run]]`. Columns: `name`, `host`, `active`,
    `phase`, `event`, `source`. `active` value: `yes` |
    `dangling` | `no`.
  - `artifacts hooks show <slug> [-j]`: manifest frontmatter
    table + sibling files (path, `+x`, size) + resolved
    active state + tail of recent `hook.fired`/`hook.failed`
    (last 5 default).
  - `artifacts hooks promote <slug> [--force] [-j]`.
  - `artifacts hooks demote <slug> [-j]`.
- `--prune` removes `.active/` entries whose target does not
  resolve, emits `hook.demoted` with `reason: "prune"`, supports
  `--dry-run`.
- Events: add `hook.promoted`, `hook.demoted` to
  `ALL_EVENT_TYPES`. (`hook.pulled` event constant also lands
  here even though it's emitted in t0184 — so the catalogue is
  complete before the artbook hook book ships.)
- Exit codes (§7.5): 0 success, 1 user error (unknown slug,
  divergent promote without `--force`), 2 configuration error
  (broken manifest, malformed `.active/`), 3 filesystem error
  (permissions).
- Re-pull preservation (§4.3): `.active/` is invisible to the
  artbook state file — confirm by inspecting how the artbook
  state writer is scoped (no change required here if it's
  bundle-write-only; document the contract).
- Tests:
  - Promote creates symlink with correct relative target.
  - Promote idempotent on same target.
  - Promote on divergent target without `--force` → exit 1;
    with `--force` → succeeds.
  - Demote unlinks; no-op on absent slug.
  - OSError stub fallback path (mock or `chmod`-restricted
    fixture).
  - `hooks list` table renders with `active` column (`yes` /
    `dangling` / `no`).
  - `hooks list --active` / `--inactive` / `--source` filters.
  - `hooks list -j` JSON shape stable.
  - `hooks show <slug>` renders and `-j` JSON shape stable;
    sibling-file listing accurate (path + `+x` + size).
  - `hooks list --prune` removes dangling entries and emits
    `hook.demoted` with `reason: "prune"`; `--dry-run` is
    inert.
  - Events `hook.promoted` / `hook.demoted` emitted at the
    documented sites.
- Docs: add a § "Promoting hooks" section to `docs/hooks.md`
  covering the `.active/` model, promote/demote/show/list/prune
  flows, divergent-target behaviour, and the re-pull
  preservation guarantee. Update `src/artifacts_os/cli/README.md`
  with the new verbs and JSON schemas.

Out of scope: artbook `kind: hook` field, distro shipping the
`os-hooks` book, `hook.pulled` event *emission* (constant lands
here, emission lands in t0184).

## Verification

- [ ] `artifacts hooks promote <slug>` creates relative symlink
      `.active/<slug> -> ../<slug>/<manifest>`; idempotent;
      divergent target errors without `--force`.
- [ ] `artifacts hooks demote <slug>` unlinks; no-op on absent.
- [ ] OSError stub fallback writes `.json` with `target`
      field; loader (from t0182) recognises both forms.
- [ ] `artifacts hooks list` renders the documented columns;
      `active` is `yes` / `dangling` / `no`; filters
      (`--host`, `--active`, `--inactive`, `--source`,
      `--tail`) work; `-j` JSON is stable.
- [ ] `artifacts hooks show <slug>` renders frontmatter +
      sibling files + active state + recent events; `-j`
      stable.
- [ ] `artifacts hooks list --prune` removes dangling
      `.active/` entries and emits `hook.demoted` with
      `reason: "prune"`; `--dry-run` makes no FS changes.
- [ ] `hook.promoted`, `hook.demoted`, `hook.pulled` added to
      `ALL_EVENT_TYPES`. (`hook.pulled` emission in t0184.)
- [ ] Exit codes match §7.5 (0/1/2/3).
- [ ] `.active/` survives a hook-book re-pull (test fixture:
      pull → promote → re-pull → verify `.active/` intact).
- [ ] `docs/hooks.md` § "Promoting hooks" and
      `cli/README.md` updated.
- [ ] `pytest` green; t0181 + t0182 regression tests still
      pass.
