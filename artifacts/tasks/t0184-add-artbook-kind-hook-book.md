---
kind: task
id: t0184
name: add-artbook-kind-hook-book
type: implementation
status: backlog
assignee: developer
owner: architect
parent: "[[t0178-ship-hooks-via-artbook-distribution]]"
depends_on:
  - "[[t0182-add-hook-kind-and-bundle]]"
created: 2026-05-22
---

# Add Artbook Kind Hook Book Type And Pull Pipeline

## Requirements

Implement [[s0032-hooks-via-artbook-distribution]] §8: the
artbook `kind: hook` book field, the pull pipeline that emits
`hook.pulled`, and the distro's own `os-hooks` book entry.

- Manifest parser (`src/artifacts_os/artbook/manifest.py`):
  - Accept a new top-level `kind:` field on a book entry
    (string enum, closed; MVP allows only `"hook"`). Unknown
    `kind:` values → `ManifestError` (D116).
  - `kind: hook` ⇒ set a `kind = "hook"` field on the `Book`
    dataclass; auto-set `recurse: true` if omitted (D118);
    reject explicit `recurse: false` → `ManifestError`.
  - `kind: hook` + `promote:` → `ManifestError` with the exact
    wording from D117: "book '<name>' has `kind: hook`; hook
    books cannot declare `promote:` — activation is an
    explicit operator step".
  - Preserve the existing v1 `type:` rejection verbatim — do
    not relax it. The new `kind:` field is parsed
    independently.
- Pull pipeline:
  - A `kind: hook` book lands bundle directories from `src`
    into canonical landing (defaults to `artifacts/hooks/`).
  - Each bundle is written verbatim (manifest + siblings).
  - After all bundles are written for a book, emit a single
    `hook.pulled` event with `book` (name), `written`,
    `overwritten`, `removed` (slug lists).
  - `--no-promote` CLI flag is accepted for uniformity but is
    a no-op against hook books (promotion is never auto for
    hook books).
- Artifacts-os distro's own `artbook.yaml` (project root) gains
  the `os-hooks` book pointing at `artifacts/hooks/` (worked
  example in §8.3):

  ```yaml
  - name: os-hooks
    src: artifacts/hooks/
    kind: hook
    description: artifacts-os lifecycle hooks (auto-commit,
      auto-verify, …).
  ```

  Note: this lands the registry but does not ship any actual
  hooks yet — the bundle directories under
  `artifacts/hooks/` can be empty or carry one demo bundle for
  the integration test. The actual `auto-commit` / `auto-verify`
  migration from `bin/hooks/` is a follow-up (not blocking).

- End-to-end integration test
  (`tests/integration/test_hooks_via_artbook.py`):
  - Set up two fixture vaults: `source` (with one bundle under
    `artifacts/hooks/demo/`) and `consumer` (fresh).
  - `consumer$ artifacts book pull os-hooks` lands the bundle.
  - `consumer$ artifacts hooks list` shows it as `active: no`.
  - `consumer$ artifacts hooks promote demo` activates.
  - Trigger the matching artifact event in consumer → demo
    bundle's `action.sh` fires (assert via output file or
    captured event payload).
  - Re-run `pull` in consumer → bundle overwritten but
    `.active/demo` symlink preserved → next event still fires
    the (refreshed) bundle.
  - Assert `hook.pulled` events emitted on each pull and that
    `hook.fired` payload carries `source: "bundle"`.
- Docs:
  - `docs/artbook.md` — new § "Hook Books" section covering
    the `kind:` field, the `recurse:` auto-set, the
    `promote:` rejection, and the worked `os-hooks` example.
  - `docs/events.md` — list the four new hook events
    (`hook.promoted`, `hook.demoted`, `hook.pulled`,
    `hook.skipped`) and the `source:` key on
    `hook.fired`/`hook.failed`.
  - `docs/hooks.md` — close the loop with a § "Distributing
    hooks via artbook" section linking to `docs/artbook.md`.
- Closes [[n0017-hook-scripts-not-installed-in-consumer]] — note
  the resolution in n0017 and the integration test as the
  evidence.

## Verification

- [ ] Artbook parser accepts `kind: hook` on a book entry;
      auto-sets `recurse: true`; rejects explicit
      `recurse: false`; rejects `promote:` with the §8.1
      error wording; rejects unknown `kind:` values; preserves
      v1 `type:` rejection.
- [ ] `artifacts book pull <hook-book>` writes bundle
      directories verbatim and emits `hook.pulled` once per
      book with `written`/`overwritten`/`removed` slug lists.
- [ ] Re-pull overwrites bundle dirs but does not touch
      `.active/`; previously-promoted hooks remain active.
- [ ] artifacts-os distro `artbook.yaml` declares `os-hooks`
      pointing at `artifacts/hooks/` (book entry parses and
      pulls cleanly into a fresh consumer fixture).
- [ ] `tests/integration/test_hooks_via_artbook.py` end-to-end
      test passes: author → pull → list → promote → fire →
      re-pull → still fires.
- [ ] `docs/artbook.md` § "Hook Books", `docs/events.md`, and
      `docs/hooks.md` § "Distributing hooks via artbook"
      updated.
- [ ] [[n0017-hook-scripts-not-installed-in-consumer]]
      annotated with the resolution + link to the integration
      test.
- [ ] `pytest` green; full suite including t0181 + t0182 tests
      passes.
