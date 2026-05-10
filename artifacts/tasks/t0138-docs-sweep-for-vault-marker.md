---
kind: task
id: t0138
name: docs-sweep-for-vault-marker
type: documentation
status: backlog
assignee: technical-writer
owner: user
parent: "[[t0131-move-artifacts-yaml-to-project]]"
depends_on:
  - "[[t0137-implement-vault-marker-relocation-per]]"
created: 2026-05-10
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
