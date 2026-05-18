---
kind: task
id: t0173
name: implement-artbook-promotion-engine-and
type: implementation
status: done
assignee: developer
owner: user
parent: "[[t0169-add-post-pull-artifact-promotion]]"
created: 2026-05-18
started: 2026-05-18
---

# Implement Artbook Promotion Engine And Cli

## Goal

Implement the **engine and CLI surface** for the post-pull artifact promotion mechanism specified in [[s0031-artbook-post-pull-artifact-promotion]]. This task collapses **S1 + S2 + S3** from § 6 of s0031 into one coherent delivery, because S1 in isolation is parser-only with no behaviour to test, and S2 produces a function with no caller until pull.py wires it. Landing the three together gives the first PR where the promotion engine is exercised end-to-end against a synthetic manifest, with the CLI levers in place.

After this task lands, the artifacts-os distro's own `artbook.yaml` is **not yet migrated** and the init D2 fallback is **not yet rewritten** — those are S5 and ship the user-visible feature. This task ships the machinery.

## Scope

### Manifest schema (S1) — `src/artifacts_os/artbook/manifest.py`

- Schema **stays at `version: 1`** (D28). No bump. No back-compat shim.
- `books[].dest` becomes **optional**. When omitted, compute default per **D37**: `dest = "artifacts/" + Path(src.rstrip("/")).name + "/"`.
- When `dest:` is set, apply **canonical-only** check (D28): must resolve under `<vault_root>/artifacts/`. Otherwise raise `ManifestError`:
  > `book '<name>' dest: '<path>' is not under 'artifacts/'. dest: is canonical-only — move tool-specific paths to promote:`
- Existing vault-escape guard (D25 — relative, no `..`) still applies to explicit `dest:`.
- Add `_parse_promote` accepting **string shorthand** or **single object form** per **D29**:
  - String: `promote: .claude/agents/` → `Promote(target=".claude/agents/", mode=None)`.
  - Object: `promote: { target, mode: symlink|copy }`. `target` required; `mode` optional (None means "fall through to per-vault or built-in default" — D30).
  - `target` goes through vault-escape guard (relative, no `..`) but **not** canonical-only (`promote:` exists to land outside `artifacts/`).
  - Reject: neither-string-nor-mapping shapes, empty strings/mappings, lists, invalid `mode`, missing `target` in object form — all `ManifestError`.
- Validation order per **D38**: version → distro.name → books non-empty → per-book (name/src → src relative/no-`..` → dest if set (relative, no-`..`, escape, canonical-only) → dest default if absent → promote if set → files/recurse exclusivity). Strictly fail-fast; **no `Manifest.warnings` field**.
- Emit new `Promote` dataclass on `Book`.

### Placement + state (S2)

- **`src/artifacts_os/artbook/state.py` (new)**
  - `read_state(vault_root) -> dict` — read `artifacts/.artbook/state.json`; absent file returns empty `{"version": 1, "promotions": {}}`.
  - `write_state(vault_root, state)` — atomic write via tmp + `os.replace`.
  - Hash helpers for copy-mode entries (`hashlib.sha256` of canonical content).
  - Schema accepts both string-form (symlink entries) and object-form `{path, hash}` (copy entries) on read; emits the appropriate shape on write per D32.
- **`src/artifacts_os/artbook/placement.py`**
  - Add `promote_book(book, vault_root, *, mode_override, state) -> PromotionReport`.
  - **Symlink mode** — relative symlink from promote target to canonical file (e.g. `.claude/agents/architect.md → ../../artifacts/agents/architect.md`). Per D30, relative links survive vault relocation.
  - **Copy mode** — atomic write-through-tmp + `os.replace`.
  - **Automatic fallback** — when symlink mode is requested and `os.symlink` raises `OSError`, fall back to copy for that file; log once per book pull per D30.
  - **Idempotency + stale cleanup** (D32):
    - Read previous `state.promotions[<book.name>]`.
    - Stale set = previously-promoted files not in current canonical entries.
    - For each stale path: `lstat` → only remove if it's a symlink pointing at the canonical tree (`os.readlink`), or a regular file whose content hash matches the recorded hash. Never delete user-modified or unrelated files.
  - **Re-emit** every current canonical file as a promotion write. Symlink mode: unlink-then-symlink if target is owned (symlink to canonical, or hash-equal file); warn-and-skip if user-modified. Copy mode: always overwrites.
  - Per-file **vault-escape guard** on each promote target.
  - **Per-promotion `mode` > per-vault `mode` > default `symlink`** precedence (D30). `mode_override` parameter carries the resolved per-vault default.
- **`src/artifacts_os/artbook/pull.py`**
  - `pull_book` calls `promote_book` after canonical writes complete (D36 — strict post-step; canonical failure aborts before promotion).
  - Promotion failures are non-fatal-for-canonical but record on the report; final exit code is `1` if any promotion file failed (D36).
  - Extend `PullReport` with `promotion: PromotionReport | None` and `promotion_skipped_reason: str | None` ('flag' | 'setting' | None) per D33.
- **`PromotedFile`, `PromotionReport`** dataclasses in `placement.py` per D33.
- **`src/artifacts_os/artbook/errors.py`** — add `PromotionError(ArtbookError)`.
- **`src/artifacts_os/artbook/__init__.py`** — re-export `Promote`, `PromotedFile`, `PromotionReport`, `promote_book`.

### CLI + settings (S3)

- **`src/artifacts_os/artbook/settings.py`**
  - `ArtbookSettings` gains:
    - `promotion: str` — `'enabled'` (default) or `'disabled'` (D31).
    - `promote_mode: str | None` — `None` (default), `'symlink'`, or `'copy'` (D30).
  - Validation per **D39** raised at `from_base` time as `SettingsError` (case-sensitive values; absent `promote_mode` ⇒ `None` sentinel).
- **`src/artifacts_os/cli/commands/book.py`**
  - Add `--no-promote` flag to `book pull` subparser. One-shot opt-out per D31; wins over `artbook.promotion: disabled` setting. Records `promotion_skipped_reason='flag'` on the report.
  - When `artbook.promotion: disabled` is set and `--no-promote` is absent, skip promotion with reason `'setting'`.
  - Add new subverb `artifacts book promote [BOOK]` per **D34**:
    - No `BOOK` → re-run promotion for every book in the manifest that has a `promote:` field.
    - With `BOOK` → re-run promotion for that book only.
    - `--clean` → ignore existing `state.promotions[<book>]` and rebuild from current canonical content.
    - `--dry-run` → print planned writes/cleanups, no filesystem changes.
    - `--json` → emit `PromotionReport` as JSON.
    - `--no-promote` is **not** valid on this verb (it *is* the promote step).
    - Verb does not clone and does not modify canonical content.
  - Render `PromotionReport` in default-table mode (canonical writes block + promotion writes block, mirroring the § 4.1 transcript format) and JSON mode.
- **`src/artifacts_os/cli/README.md`** — add a short section on `--no-promote` and the new `book promote` verb.

### Tests

- **`tests/artbook/test_manifest.py`**
  - `version: 1` manifest with no `dest:` → resolved `Book.dest` matches D37 default for representative `src` values (`artifacts/agents/`, `src/skills/`, `kinds/`).
  - `version: 1` manifest with `dest: .claude/agents/` → `ManifestError` with canonical-only message.
  - Existing valid v1 manifests with `dest:` under `artifacts/` still parse.
  - `promote:` accepts string shorthand and object form; rejects unknown modes, missing `target`, empty target, lists, neither-string-nor-mapping.
  - `promote.target` outside `artifacts/` is permitted; outside vault or with `..` is rejected.
  - Validation is fail-fast; no `warnings` field on `Manifest`.
- **`tests/artbook/test_placement.py`**
  - `promote_book` symlink path — relative links to canonical tree.
  - `promote_book` copy path — atomic write, hash recorded.
  - Symlink fallback when `os.symlink` raises (monkeypatch `os.symlink` to raise `OSError`).
  - Idempotent re-promote (no spurious writes, byte-stable state file).
  - Stale-target cleanup — both symlink-ownership-by-readlink and copy-ownership-by-hash variants.
  - User-modified target is preserved (recorded in `skipped`, never deleted).
- **`tests/artbook/test_state.py` (new)**
  - State-file round-trip. Backwards-compat read of string-form entries. Hash record for copy mode. Atomic write (interrupt mid-write leaves valid prior state).
- **`tests/artbook/test_pull_integration.py` (new)**
  - End-to-end pull with promote on a tmp distro fixture.
  - Pull with `--no-promote`; canonical writes happen, state file untouched.
  - Pull with `artbook.promotion: disabled`; same as above with `reason='setting'`.
  - Re-pull idempotency.
  - Pull after upstream removes an item → stale promotion target cleaned up.
- **`tests/cli/test_book.py`**
  - `--no-promote` on `pull` (flag precedence over setting).
  - `book promote` (positional, `--clean`, `--dry-run`, `--json`).
  - `book promote --no-promote` rejected with usage error.
  - `artbook.promote_mode: copy` flips default; per-promotion `mode:` still wins.

### Spec-side bookkeeping

- **`artifacts/specs/s0029-artbook-mvp-distribution-model.md`** — add Revision note at top per § 5.5 of s0031: schema stays at `version: 1`, v1 semantics tightened in place, `dest:` canonical-only, `promote:` added in [[s0031]], D17/D24/D26/D27 carry over unchanged, no back-compat shim.

## Out of scope (deferred to later sub-tasks)

- **S4 — Documentation.** `docs/artbook.md` (author/consumer guide rewrite, deprecate `dest: .claude/…` row), `docs/init-flow.md` (D2 transcript update), `docs/settings.md` (new keys), `README.md` (one-line pointer).
- **S5 — Distro migration + init D2.** `artbook.yaml` (repo root) rewrite per § 4.3 of s0031, `cli/commands/init.py` rewrite of `_install_bundled_skill` to use the synthetic `Book` + `promote_book` path (D40), `tests/cli/test_init.py` for the new D2 behaviour.

Until S5 lands, the promotion engine has no real-world caller — the only exercise is the synthetic integration tests in `tests/artbook/test_pull_integration.py` against a tmp distro fixture.

## Progress

### 2026-05-18 00:29:52 — Incomplete run (r0180)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$2.24, turns=51


### 2026-05-18 08:52:07 — Incomplete run (r0181)

**Stop reason:** Non-zero exit code (8)
**Stats:** cost=$4.63, turns=51

## Verification

### Schema
- [x] `version: 1` manifest with no `dest:` parses; resolved `Book.dest` matches D37 default for `src` ∈ {`artifacts/agents/`, `src/skills/`, `kinds/`}.
- [x] `version: 1` manifest with `dest: .claude/agents/` raises `ManifestError` carrying the canonical-only message.
- [x] Existing valid v1 manifests with `dest:` under `artifacts/` continue to parse.
- [x] `promote:` string shorthand → `Promote(target=<path>, mode=None)`.
- [x] `promote:` object form with `target` + optional `mode` parses; unknown modes / missing target / empty target / lists / neither-string-nor-mapping all raise `ManifestError`.
- [x] `promote.target` outside `artifacts/` permitted; outside vault or with `..` rejected.
- [x] Validation is strictly fail-fast (D38 order); no `Manifest.warnings` field.

### Engine
- [x] `promote_book` symlink mode emits relative links pointing at the canonical tree (e.g. `../../artifacts/agents/architect.md`).
- [x] `promote_book` copy mode writes hash-equal files; hash recorded in state.
- [x] Symlink → copy fallback engages when `os.symlink` raises `OSError`; logged once per book pull.
- [x] Re-pull is byte-stable (idempotent canonical + idempotent state file).
- [x] Stale-target cleanup respects ownership: symlink-by-readlink, copy-by-hash. User-modified files preserved.
- [x] State file round-trips; accepts both string-form and object-form entries on read; emits the appropriate shape per mode.
- [x] Promotion failure is non-fatal-for-canonical; final exit code is `1` when any promotion file failed (D36).
- [x] `PullReport.promotion` is `None` when book has no `promote:` or promotion was skipped; `promotion_skipped_reason` distinguishes the two.

### CLI + settings
- [x] `book pull --no-promote` skips promotion; canonical writes succeed; report records `reason='flag'`.
- [x] `artbook.promotion: disabled` in `artifacts.yaml` skips promotion on every `book pull`; report records `reason='setting'`.
- [x] `--no-promote` wins when both are set (per D31 precedence).
- [x] `book promote BOOK` re-runs promotion against current canonical content; no clone, no canonical writes.
- [x] `book promote --clean` rebuilds `state.promotions[<book>]` from scratch.
- [x] `book promote --dry-run` makes no filesystem changes.
- [x] `book promote --json` emits a structured `PromotionReport`.
- [x] `book promote --no-promote` rejected with a usage error.
- [x] `artbook.promote_mode: copy` flips the default mode; per-promotion `promote.mode:` still wins (D30 precedence).
- [x] Invalid `artbook.promotion` / `artbook.promote_mode` values raise `SettingsError` per D39.

### Process
- [x] s0029 has the new Revision note at the top per § 5.5.
- [x] `pytest tests/artbook tests/cli/test_book.py` passes.
- [x] `cli/README.md` documents `--no-promote` and the new `book promote` verb.

## References

- Parent spec: [[s0031-artbook-post-pull-artifact-promotion]] §§ 3 (D28–D40), 4.1–4.2 (transcripts), 5.1 (file change list), 6 S1/S2/S3.
- Parent feature: [[t0169-add-post-pull-artifact-promotion]].
- Sibling spec task (delivered): [[t0170-spec-the-artbook-promotion-mechanism]].
- Predecessor spec: [[s0029-artbook-mvp-distribution-model]] (D17/D24/D25/D26/D27 carry over; D8 strengthened by D28).
- Touched modules: `src/artifacts_os/artbook/{manifest,placement,pull,settings,errors,state}.py`, `src/artifacts_os/cli/commands/book.py`, `src/artifacts_os/cli/README.md`.

## Blocks

- **S5 (distro migration + init D2)** — once this lands, S5 can migrate `artbook.yaml` to use `promote:` and rewrite `_install_bundled_skill` to use the engine via a synthetic `Book`.

## Does not block

- **S4 (documentation)** — can ship in parallel; documents the surface this task introduces.
