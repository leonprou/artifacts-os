---
kind: task
id: t0174
name: document-artbook-promotion-mechanism
type: documentation
status: done
assignee: technical-writer
owner: user
parent: "[[t0169-add-post-pull-artifact-promotion]]"
created: 2026-05-18
started: 2026-05-18
completed: 2026-05-18
---

# Document Artbook Promotion Mechanism

## Goal

Document the post-pull artifact promotion mechanism introduced by [[s0031-artbook-post-pull-artifact-promotion]] across the package's user-facing and consumer-facing docs. This is **S4** from § 6 of s0031.

The spec is the source of truth; this task translates it into the four touch-points an operator encounters when reading the docs: the artbook author guide, the consumer behaviour reference, the init flow, and the settings reference.

## Scope

Per § 5.3 of [[s0031]]:

### `docs/artbook.md` — major rewrite

- **New § Promotion (author guide).**
  - The `promote:` field (string shorthand vs single object form).
  - Default mode (`symlink` with automatic copy fallback).
  - When to set `mode: copy` explicitly (tool reads inode metadata, etc.).
  - Worked example mirroring § 4.1 of [[s0031]]: a book with `promote:` and the resulting on-disk shape.
- **New § Consumer behaviour.**
  - `--no-promote` flag on `book pull` and `init`.
  - `artbook.promotion: disabled` setting in `artifacts.yaml`.
  - `artbook.promote_mode: symlink | copy` setting.
  - Precedence rule (flag > setting > default).
  - The new `artifacts book promote [BOOK]` verb (`--clean`, `--dry-run`, `--json`).
- **New § Migration.**
  - How to convert a manifest authored against the pre-spec v1 shape (`dest: .claude/agents/`) to the canonical-landing + promote shape.
  - The worked artifacts-os migration from § 4.3 of [[s0031]] as the canonical before/after example.
  - Note that v1 schema is unchanged — no version bump, just tightened semantics.
- **Rewrite existing "Destination patterns" section.** The current doc presents `dest: .claude/agents/` as the standard pattern; under [[s0031]] D28 that pattern raises `ManifestError`. Replace those rows with the `(dest: artifacts/…, promote: .claude/…)` pattern.

### `docs/init-flow.md` — D2 transcript update

- Update the "No-distro fallback" / D2 section to show the new behaviour from [[s0031]] D40: the bundled `artifacts-os` skill writes to `artifacts/skills/artifacts-os/SKILL.md` (canonical) **and** is promoted to `.claude/skills/artifacts-os/SKILL.md` (symlink). The synthetic-book entry appears in `artifacts/.artbook/state.json`.
- Remove any prior copy that describes D2 as writing direct to `.claude/skills/`.

### `docs/settings.md` — new keys

- Document `artbook.promotion` (`enabled` default | `disabled`).
- Document `artbook.promote_mode` (`None` default | `symlink` | `copy`).
- Cross-reference `--no-promote` and the precedence rule with `docs/artbook.md`.
- Validation behaviour: invalid values raise `SettingsError` per [[s0031]] D39.

### `README.md`

- One-line pointer in the artbook quickstart section noting that distros now ship with `promote:` declarations and that consumers get tool-shaped views automatically.

## Out of scope

- Code changes — those belong to t0173 (engine + CLI) and the S5 sub-task (distro migration + init D2).
- The spec itself ([[s0031]]) — already the source of truth; do not duplicate decision rationale in user docs, link to it instead.
- `docs/artbook.md` examples that use multi-tool / list-form `promote:` — D29 defers that to a future spec.

## Dependencies

- This task does **not** strictly depend on t0173 landing; the spec is the source of truth and docs can be drafted directly against it.
- However, the developer working t0173 may surface implementation details that warrant doc clarification (e.g. exact error message wording, exact JSON shape of `book promote --json`). The tech writer should sync with the developer once t0173 reaches review to confirm doc copy matches the shipped surface.

## Progress

### 2026-05-18 — technical-writer
> time: 09:07

Documented promotion mechanism across docs/artbook.md (new §§ Promotion, Consumer behaviour, Migration; rewrote Destination patterns), docs/init-flow.md (D2 canonical+promote transcripts), docs/settings.md (artbook.promotion + artbook.promote_mode keys), README.md (promote: pointer + artbook.md added to index)

## Findings

Updated four documentation touch-points to cover the post-pull artifact promotion mechanism (spec `s0031-artbook-post-pull-artifact-promotion`):

- **`docs/artbook.md`** — Rewrote the leading anatomy example, updated the book entry fields table (`dest` is now optional/canonical-only, `promote` added), rewrote "Destination patterns" to show `ManifestError` on non-canonical `dest:` and the new `(dest: artifacts/…, promote: .claude/…)` pattern. Updated the artifacts-os distro example to the post-migration YAML. Fixed "No-distro fallback" prose and "What gets written" list in the Consumer Quickstart section. Added three new sections: **§ Promotion** (author guide: string/object form, symlink default with copy fallback, when to use copy, worked example, state tracking), **§ Consumer behaviour** (`--no-promote`, `artbook.promotion`, `artbook.promote_mode`, precedence rule, `artifacts book promote` verb reference), and **§ Migration** (before/after diff of the artifacts-os distro, per-book migration table, schema note).
- **`docs/init-flow.md`** — Updated "No-distro fallback (D2)" description and both D2 transcripts (Transcript A and C.1) to show the canonical write + promotion symlink path. No leftover references to direct-to-`.claude/` writes.
- **`docs/settings.md`** — Extended the Artbook Section to document `artbook.promotion` and `artbook.promote_mode` with type, default, validation behaviour, precedence rule, and cross-reference to `docs/artbook.md`.
- **`README.md`** — Added a `promote:` pointer paragraph in the Init section, added a distro init example (`--distro` flag), added `docs/artbook.md` to the Documentation index, updated "three-step" → "two-stage" references.

## Downstream

- The developer landing t0173 (engine + CLI) should verify that error message wording in the implementation matches the doc copy (specifically the `ManifestError` text reproduced in "Destination patterns" and "§ Migration").
- Once t0173 ships, confirm the exact JSON shape emitted by `artifacts book promote --json` and update the `--json` note in `§ Consumer behaviour` if needed.
- The `docs/artbook.md` "No-distro fallback" prose in the Consumer Quickstart section notes the state.json synthetic-book entry; verify the `artifacts-os-skill` synthetic book name matches the implementation when t0173+S5 land.

## Verification

- [x] `docs/artbook.md` has new sections covering Promotion (author guide), Consumer behaviour, Migration.
- [x] The "Destination patterns" section no longer presents `dest: .claude/…` as a valid pattern; replaced with `(dest: artifacts/…, promote: .claude/…)`.
- [x] A reader can produce a working v1 `artbook.yaml` with `promote:` by reading `docs/artbook.md` alone (no need to open the spec).
- [x] The migration section walks an operator through converting a pre-spec v1 manifest to the new shape end-to-end.
- [x] `docs/init-flow.md` D2 section reflects the canonical + promote behaviour from D40; no leftover copy describing direct-to-`.claude/` writes.
- [x] `docs/settings.md` documents `artbook.promotion` and `artbook.promote_mode` with precedence cross-references.
- [x] `README.md` artbook quickstart mentions `promote:` (one line).
- [x] All wikilinks resolve (`[[s0031-...]]`, `[[t0169-...]]`).

## Verification Report

*Verified: 2026-05-18*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | `docs/artbook.md` has new sections covering Promotion, Consumer behaviour, Migration | PASS | `## Promotion` at L444, `## Consumer behaviour` at L568, `## Migration` at L661 in `docs/artbook.md` |
| 2 | "Destination patterns" no longer presents `dest: .claude/…` as valid; uses `(dest: artifacts/…, promote: .claude/…)` | PASS | `docs/artbook.md` L137–170 shows `dest:` must resolve under `artifacts/`, explicit `ManifestError` example for `.claude/agents/`, table uses canonical `dest` + `promote` columns |
| 3 | Reader can produce a working v1 `artbook.yaml` with `promote:` from `docs/artbook.md` alone | PASS | L15–67 anatomy includes `promote:` example; L444–565 § Promotion documents string + object form, default mode, worked example, state tracking |
| 4 | Migration section walks an operator end-to-end through converting a pre-spec v1 manifest | PASS | `docs/artbook.md` L661–763 includes before/after artifacts-os YAML diff, per-book migration table, schema note explaining no version bump |
| 5 | `docs/init-flow.md` D2 section reflects canonical + promote behaviour; no leftover direct-to-`.claude/` writes | PASS | L46–59 D2 description writes canonical + symlink; Transcript A L65–87 and C.1 L135–148 both show canonical write + symlink promotion; remaining `.claude/skills/artifacts-os` mentions are symlink targets only |
| 6 | `docs/settings.md` documents `artbook.promotion` and `artbook.promote_mode` with precedence cross-references | PASS | L504–540 documents both keys with type/default/validation, precedence rule (3-tier), and cross-reference to `docs/artbook.md#consumer-behaviour` |
| 7 | `README.md` artbook quickstart mentions `promote:` (one line) | PASS | `README.md` L68–78 describes `promote:` declarations and pointer to `docs/artbook.md`; entry added to Documentation index at L129 |
| 8 | All wikilinks resolve (`[[s0031-...]]`, `[[t0169-...]]`) | PASS | `artifacts/specs/s0031-artbook-post-pull-artifact-promotion.md` and `artifacts/tasks/t0169-add-post-pull-artifact-promotion.md` both exist |

### Summary

8 passed, 0 failed. All verification criteria met — task ready to transition to `verified`.

## References

- Parent spec: [[s0031-artbook-post-pull-artifact-promotion]] § 4.1–4.3 (worked transcripts), § 5.3 (documentation change list).
- Parent feature: [[t0169-add-post-pull-artifact-promotion]].
- Sibling implementation: [[t0173]] — the engine + CLI; surface that this task documents.
- Spec ancestors: [[s0029-artbook-mvp-distribution-model]] (current artbook author guide is built around s0029), [[s0030-books-driven-init-flow]] (D2 fallback origin).
- Files: `docs/artbook.md`, `docs/init-flow.md`, `docs/settings.md`, `README.md`.
