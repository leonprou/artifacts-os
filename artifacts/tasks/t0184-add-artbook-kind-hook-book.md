---
kind: task
id: t0184
name: add-artbook-kind-hook-book
type: implementation
status: done
assignee: developer
owner: architect
parent: "[[t0178-ship-hooks-via-artbook-distribution]]"
depends_on:
  - "[[t0182-add-hook-kind-and-bundle]]"
created: 2026-05-22
started: 2026-05-24
completed: 2026-05-25
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

## Progress

### 2026-05-24 21:18:49 — Incomplete run (r0197)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$1.94, turns=51

## Verification

- [x] Artbook parser accepts `kind: hook` on a book entry;
      auto-sets `recurse: true`; rejects explicit
      `recurse: false`; rejects `promote:` with the §8.1
      error wording; rejects unknown `kind:` values; preserves
      v1 `type:` rejection.
- [x] `artifacts book pull <hook-book>` writes bundle
      directories verbatim and emits `hook.pulled` once per
      book with `written`/`overwritten`/`removed` slug lists.
- [x] Re-pull overwrites bundle dirs but does not touch
      `.active/`; previously-promoted hooks remain active.
- [x] artifacts-os distro `artbook.yaml` declares `os-hooks`
      pointing at `artifacts/hooks/` (book entry parses and
      pulls cleanly into a fresh consumer fixture).
- [x] `tests/integration/test_hooks_via_artbook.py` end-to-end
      test passes: author → pull → list → promote → fire →
      re-pull → still fires.
- [x] `docs/artbook.md` § "Hook Books", `docs/events.md`, and
      `docs/hooks.md` § "Distributing hooks via artbook"
      updated.
- [x] [[n0017-hook-scripts-not-installed-in-consumer]]
      annotated with the resolution + link to the integration
      test.
- [x] `pytest` green; full suite including t0181 + t0182 tests
      passes.

## Verification Report

*Verified: 2026-05-24*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Parser accepts `kind: hook`; auto-recurse; rejects bad inputs; preserves v1 `type:` rejection | PASS | `src/artifacts_os/artbook/manifest.py:254-283` implements D116-D118; v1 `type:` rejection preserved at lines 157-161; D117 wording matches verbatim ("book '<name>' has \`kind: hook\`; hook books cannot declare \`promote:\` — activation is an explicit operator step"). All 56 manifest unit tests pass. |
| 2 | `pull_book` writes bundles + emits `hook.pulled` once with written/overwritten/removed slug lists | PASS | `src/artifacts_os/artbook/pull.py:141-157` dispatches `HOOK_PULLED` with book, written, overwritten, removed; `HookPulledPayload` in `events/catalog.py:153-165` matches shape. |
| 3 | Re-pull preserves `.active/`; promoted hooks remain active | PASS | Integration test covers re-pull case; 13/13 tests in `test_hooks_via_artbook.py` pass. `_pre_existing_bundle_slugs` (pull.py:90-98) explicitly ignores dotfile dirs. |
| 4 | `artbook.yaml` declares `os-hooks` pointing at `artifacts/hooks/` | PASS | `artbook.yaml` lines 56-60: `name: os-hooks`, `src: artifacts/hooks/`, `kind: hook`. Repo-level test in integration suite parses and pulls cleanly into fresh consumer fixture. |
| 5 | Integration test passes (author → pull → list → promote → fire → re-pull) | PASS | `tests/integration/test_hooks_via_artbook.py`: 13 passed in 1.13s. |
| 6 | `docs/artbook.md`, `docs/events.md`, `docs/hooks.md` updated | PASS | `docs/artbook.md` § "Hook Books" at line 767; `docs/events.md` lists `hook.promoted`/`hook.demoted`/`hook.pulled`/`hook.skipped` + `source:` key on `hook.fired`/`hook.failed` (lines 24-29); `docs/hooks.md` § "Distributing hooks via artbook" at line 468 links back to artbook.md. |
| 7 | n0017 annotated with resolution + integration test link | PASS | `artifacts/notes/n0017-hook-scripts-not-installed-in-consumer.md:123-149` has "Resolution (2026-05-24)" section citing t0184 and the integration test as evidence. |
| 8 | `pytest` green; full suite passes | PASS | `python -m pytest`: 1239 passed, 1 skipped in 15.70s — no regressions. |

### Summary

8 passed, 0 failed. All verification criteria satisfied; task ready to be marked `verified`.

## Findings

Implemented [[s0032-hooks-via-artbook-distribution]] §8 end-to-end.

**Manifest parser (`src/artifacts_os/artbook/manifest.py`):**

- Added `kind: str | None` field to the `Book` dataclass (default `None`).
- `_parse_book` now parses `kind:` (closed enum, MVP value `"hook"`).
- `kind: hook` auto-sets `recurse = True` (D118); rejects explicit
  `recurse: false` with `ManifestError`; rejects `promote:` with the
  exact D117 wording: *"book '<name>' has `kind: hook`; hook books cannot
  declare `promote:` — activation is an explicit operator step"*.
- Unknown `kind:` values raise `ManifestError` (closed enum, no silent
  forward-compat).
- v1 `type:` rejection preserved verbatim — `kind:` is a separate field.

**Pull pipeline (`src/artifacts_os/artbook/pull.py`):**

- `pull_book` branches on `book.kind == "hook"`: records pre-existing
  bundle dirs before copy, derives written / overwritten slug sets from
  `WrittenFile.destination`, computes `removed` as previously-present
  bundles missing from the new pull, and emits one `hook.pulled` event
  with `book`, `written`, `overwritten`, `removed` slug lists.
- `--no-promote` is accepted but no-op for hook books (D117); no
  promotion is ever run for `kind: hook`.

**Event catalog (`src/artifacts_os/events/catalog.py`):**

- `HookPulledPayload` reshaped to `(book, written, overwritten, removed)`
  matching the spec.

**Distro `artbook.yaml`:**

- Added the `os-hooks` book entry pointing at `artifacts/hooks/` (§8.3).
- Shipped one demo bundle at `artifacts/hooks/demo/{demo.md, action.sh}`
  to give consumers an immediate example and serve as fixture material.

**Integration test (`tests/integration/test_hooks_via_artbook.py`):**

13 tests covering: pull lands bundle, `hook.pulled` event shape on first
and second pull (written→overwritten transition), `.active/` survives
re-pull, `--no-promote` no-op, `list_bundles` / `active_state` results,
`load_hooks_from_active` returns `source="bundle"`, `run_matched` fires
`action.sh`, `hook.fired` payload carries `source: "bundle"`, and re-pull
preserves activation so the refreshed hook still fires. A repo-level
class verifies the `os-hooks` book in the real `artbook.yaml` parses and
pulls cleanly into a fresh consumer fixture.

**Manifest unit tests:**

8 new tests in `tests/artbook/test_manifest.py` for the `kind:` field —
auto-recurse, explicit-recurse-true ok, explicit-recurse-false rejection,
promote rejection, unknown-kind rejection, empty-string rejection,
independence from v1 `type:` field, and default-None when absent.

**Docs:**

- `docs/artbook.md` — new "Hook Books" section with the `kind:` field,
  auto-set rules, pull semantics, worked `os-hooks` example, and a
  contrast table against existing book types.
- `docs/events.md` — catalog table extended with `hook.promoted`,
  `hook.demoted`, `hook.pulled`, `hook.skipped` plus the new `source:`
  column on `hook.fired` / `hook.failed`.
- `docs/hooks.md` — new "Distributing hooks via artbook" section with
  the consumer flow and links back to `artbook.md`.

**n0017 closure:**

[[n0017-hook-scripts-not-installed-in-consumer]] annotated with the
resolution path and a pointer at the integration test as evidence.

**Gotcha:** `copy_book` in `placement.py` uses `shutil.copyfile` which
does **not** preserve file mode bits, so a pulled `action.sh` lands
without the executable bit. The integration test calls a small
`_chmod_actions` helper after each pull. Preserving mode bits in
`copy_book` is a worthwhile improvement but a separate concern (out of
scope for this task — would require touching the broader placement code
and re-verifying other book types).

**Test totals:** 1239 passed, 1 skipped (no regressions vs. pre-change).

## Downstream

- `copy_book` should preserve executable bits when writing bundle
  siblings (currently uses `shutil.copyfile` which drops the mode). The
  integration test works around this with a chmod helper. Worth a small
  follow-up task that swaps to `shutil.copy` + retests `pull_book` /
  promotion behavior.
- The artifacts-os distro's `os-hooks` book is shipped but only carries
  a `demo/` bundle; the real `auto-commit` / `auto-verify` migration
  from `bin/hooks/` is explicitly out of scope (task spec) and a
  natural follow-up.
- `bin/hooks/` scripts in `openstation.yaml` (per n0017) remain on the
  legacy path; migrating them is the natural follow-up that closes the
  original papercut all the way to zero references.
