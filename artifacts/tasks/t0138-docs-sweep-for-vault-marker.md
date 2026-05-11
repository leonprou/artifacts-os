---
kind: task
id: t0138
name: docs-sweep-for-vault-marker
type: documentation
status: done
assignee: technical-writer
owner: user
parent: "[[t0131-move-artifacts-yaml-to-project]]"
depends_on:
  - "[[t0137-implement-vault-marker-relocation-per]]"
created: 2026-05-10
started: 2026-05-10
completed: 2026-05-11
---

# Docs Sweep for Vault-Marker Relocation (PR2)

## Requirements

Execute **PR2 of the build sequence** from
[[artifacts/specs/s0026-vault-marker-at-root]] §13.2 — the
prose-only documentation sweep that follows the code change
in [[t0137-implement-vault-marker-relocation-per]].

Pure prose. No source code, no tests, no CLI behaviour
changes. The PR is reviewable as a doc audit.

### Scope (in)

Every reference to the literal `artifacts/artifacts.yaml`
must be rewritten to either `artifacts.yaml` (when
unqualified) or `<vault-root>/artifacts.yaml` (when the
prose needs to indicate it is at the project root). The
exhaustive list lives in s0026 §12; reproduced here for
convenience:

#### Top-level

- `CLAUDE.md` (lines 12, 101)
- `README.md` (line 24)

#### `docs/`

- `docs/settings.md` (lines 3, 14, 48, 81, 358, 490)
- `docs/init-flow.md` (lines 19, 123)
- `docs/adding-a-kind.md` (lines 257, 508)
- `docs/creating-an-artifact.md` (line 5)

#### Per-module READMEs

- `src/artifacts_os/core/README.md` (lines 42, 154, 182,
  201, 215)
- `src/artifacts_os/views/README.md` (lines 270, 338)
- `src/artifacts_os/cli/README.md` — every qualified
  `artifacts/artifacts.yaml` instance (lines 47, 262, 660,
  817, 901). Bare `artifacts.yaml` references (most of
  cli/README.md) are already correct.

#### Skills and AI command files

- `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`
  (lines 3, 50)
- `src/artifacts_os/ai/claude/commands/artifacts.create.md`
  (lines 22, 42)

#### Spec amendments

- `artifacts/specs/s0021-artifacts-init-flow.md` —
  amend in place (not supersede). Sections to touch:
  §1 (Background), §4 D1, §10.4–10.6 worked transcripts,
  §14.2 worked example, §17 surfaces, §19 cross-refs.

### Scope (out)

- Code or test changes. Those landed in t0137.
- New documentation pages beyond `docs/migration.md`
  (which t0137 creates).
- Renaming the marker file. Out of scope per s0026 §16.

### Implementation pattern

Single mechanical sweep:

```
rg -l 'artifacts/artifacts\.yaml' \
    docs/ \
    src/artifacts_os/*/README.md \
    src/artifacts_os/ai/claude/ \
    artifacts/specs/s0021-artifacts-init-flow.md \
    CLAUDE.md README.md
```

Every file in that list gets one prose-aware edit pass. Most
are trivial substitutions; the s0021 transcripts and
prose-y sentences require a brief read to keep meaning
intact (e.g. "find a directory containing
`artifacts/artifacts.yaml`" → "find a directory containing
`artifacts.yaml`").

## Findings

Mechanical prose sweep complete. Every literal `artifacts/artifacts.yaml` reference in the scope set has been rewritten to `artifacts.yaml`.

**Files changed (11 doc files):**
- `CLAUDE.md` — "Artifact Storage" block + Settings section (2 occurrences)
- `README.md` — Quick Start comment (1 occurrence)
- `docs/settings.md` — intro line + 4 code-block `load_settings` calls
- `docs/init-flow.md` — settings tier description + existing-file guard (2 occurrences)
- `docs/adding-a-kind.md` — Optional Follow-Up section (1 occurrence)
- `docs/creating-an-artifact.md` — opening prerequisite (1 occurrence)
- `src/artifacts_os/core/README.md` — vault discovery description + worked example (2 occurrences)
- `src/artifacts_os/views/README.md` — worked example `load_settings` call (1 occurrence)
- `src/artifacts_os/cli/README.md` — auto-discovery prose, views section, code comment, init description, `artifacts views` description, `cli` section intro (6 occurrences)
- `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` — trigger description (1 occurrence)
- `artifacts/specs/s0021-artifacts-init-flow.md` — §1 Background, §4 D1, §10.4–10.6 transcripts, §14.2 example, §17, §19 (10 occurrences via `replace_all`)

**Intentionally untouched:** `docs/migration.md` (describes the old→new migration path; old references are correct there) and `artifacts/specs/s0026-vault-marker-at-root.md` (historical references).

**Note:** Line 835 of s0021 contains `if (target / "artifacts" / "artifacts.yaml").is_file()` — a Python code snippet with separate string arguments, not a literal `artifacts/artifacts.yaml` path. Not in grep scope; left as-is.

## Progress

### 2026-05-10 — technical-writer
> time: 19:02

Completed docs sweep: replaced all literal `artifacts/artifacts.yaml` references across CLAUDE.md, README.md, docs/ (settings.md, init-flow.md, adding-a-kind.md, creating-an-artifact.md), src/artifacts_os/*/README.md, SKILL.md, and s0021 spec amendment. Zero matches remain in scope files. docs/migration.md intentionally retains old path references.

## Verification

- [ ] `rg 'artifacts/artifacts\.yaml' docs/ src/ CLAUDE.md README.md`
      returns zero matches in tracked files (excluding
      `artifacts/specs/s0026-vault-marker-at-root.md`
      itself, which references the legacy path
      historically).
- [ ] `s0021-artifacts-init-flow` worked transcripts show
      the new path in §10.4–10.6.
- [ ] `CLAUDE.md`'s "Artifact Storage" intro reflects the
      new layout.
- [ ] No code or test files modified — `git diff --stat`
      shows only `*.md` files (and the spec amendment).
- [ ] Doc links in `docs/migration.md` still resolve.
