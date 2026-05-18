# `artifacts init` — Two-Stage Init Flow

The `artifacts init` command bootstraps a new artifacts-os vault through
a two-stage selection flow: a settings tier step, followed by one multi-select
prompt per book in a configured distro. See spec `s0030-books-driven-init-flow`
for the full rationale.

## Synopsis

```
artifacts init [DIRECTORY] [--template TIER]
               [--distro URL] [--book NAME[:ITEMS]] ...
               [--force] [-y] [--dry-run] [--openstation-compat]
```

## The Two Stages

### Stage 1 — Settings tier (always runs)

Chooses one of two settings tiers, written as `artifacts.yaml`.

| Tier | Content |
|------|---------|
| `minimal` | Mandatory header + three lifecycle views (`active`, `ready`, `done`). |
| `standard` (default) | Adds per-type task slices, per-kind landing views, `default_views` block, and cross-kind `recent` view. |

Tiers are **strictly additive** — `standard` is a superset of `minimal`.

### Stage 2..N — Book loop (only when distro configured)

When `--distro` or `$ARTIFACTS_DISTRO_URL` is set, each book declared in
the distro manifest gets a single multi-select prompt (or is pulled
non-interactively with `-y`/`--book`). Books are looped in manifest
declaration order.

```
Book 'agents' (9 items) — comma-separated numbers, '*' for all, '-' for none:
  1) architect        [default]
  2) author           [default]
  ...

Choice [*]:
```

### No-distro fallback (D2)

When no `--distro` and no `$ARTIFACTS_DISTRO_URL`:

1. Stage 1 runs (settings tier → writes `artifacts.yaml`).
2. The bundled `artifacts-os` skill is written to
   `artifacts/skills/artifacts-os/SKILL.md` (canonical), then
   promoted via symlink to `.claude/skills/artifacts-os/SKILL.md`.
   The promotion is recorded in `artifacts/.artbook/state.json`
   under a synthetic book entry `artifacts-os-skill`.
3. Init exits.

No kinds, no agents. The vault is intentionally minimal — the user
grows it later by configuring `artbook.distro_url` and running
`artifacts book pull`, or by re-running `artifacts init --distro <url> --force`.

## Transcripts

### Transcript A — No-distro interactive (D2 fallback)

```
$ art init

Settings tier (1 of 1):
  1) minimal      — header + lifecycle views (active / ready / done)
  2) standard     — adds per-type slices, default_views, cross-kind 'recent'

Choice [2]: ⏎

Selected:
  template : standard

Writing files...
  ✓ artifacts.yaml
  ✓ artifacts/skills/artifacts-os/SKILL.md
  ✓ .claude/skills/artifacts-os/SKILL.md (→ ../../artifacts/skills/artifacts-os/SKILL.md)

Initialised artifacts-os project: /path/to/proj
```

One selection step. The bundled skill is written to the canonical
location under `artifacts/skills/` and promoted via symlink into
`.claude/skills/`. The promotion is tracked in
`artifacts/.artbook/state.json`.

### Transcript B — Distro-configured interactive (D1 + book loop)

```
$ art init --distro https://github.com/leonprou/artifacts-os

Settings tier (1 of N):
  1) minimal      — header + lifecycle views (active / ready / done)
  2) standard     — adds per-type slices, default_views, cross-kind 'recent'

Choice [2]: ⏎

Selected:
  template : standard
  distro   : https://github.com/leonprou/artifacts-os

Writing files...
  ✓ artifacts.yaml

Fetching distro manifest…

Book 'agents' (9 items) — comma-separated numbers, '*' for all, '-' for none:
  1) architect        [default]
  2) author           [default]
  ...

Choice [*]: 1,3,9 ⏎
  ✓ agents: 3 files written

Book 'skills' (2 items) — comma-separated numbers, '*' for all, '-' for none:
  1) artifacts-os         [default]
  2) release-changelog    [default]

Choice [*]: ⏎
  ✓ skills: 2 files written

Initialised artifacts-os project: /path/to/proj
```

The bundled `.claude/skills/artifacts-os/SKILL.md` is **not** installed
from the bundle — when a distro is configured, the distro is authoritative
for all skill content (Q4).

### Transcript C — Non-interactive (bare -y and fully-flagged distro)

#### C.1 Bare `-y` — D6 fallback

```
$ art init -y

Selected:
  template : standard

Writing files...
  ✓ artifacts.yaml
  ✓ artifacts/skills/artifacts-os/SKILL.md
  ✓ .claude/skills/artifacts-os/SKILL.md (→ ../../artifacts/skills/artifacts-os/SKILL.md)

Initialised artifacts-os project: /path/to/proj
```

#### C.2 Fully-flagged distro

```
$ art init --distro https://github.com/leonprou/artifacts-os -y \
       --book agents:architect,developer \
       --book skills:artifacts-os

Selected:
  template : standard
  distro   : https://github.com/leonprou/artifacts-os
  books    : agents (2 items), skills (1 item)

Writing files...
  ✓ artifacts.yaml

Fetching distro manifest…
  ✓ agents: 2 files written
  ✓ skills: 1 file written

Initialised artifacts-os project: /path/to/proj
```

## Prompt Format

Single-choice (Stage 1):

```
Settings tier (1 of 1):
  1) minimal      — header + lifecycle views (active / ready / done)
  2) standard     — adds per-type slices, default_views, cross-kind 'recent'

Choice [2]: <enter>
```

Multi-select (per-book prompt):

```
Book 'agents' (9 items) — comma-separated numbers, '*' for all, '-' for none:
  1) architect    [default]
  2) author       [default]
  ...

Choice [*]: <enter>
```

Input formats accepted:
- Empty → defaults
- `*` → all
- `-` → none
- `1,3,5` → items by number
- `architect,developer` → items by name
- `1,developer` → mixed numbers and names

## Non-TTY Behaviour

| stdin TTY? | `--template` set? | Distro? | `--book` / `-y`? | Result |
|-----------|------------------|---------|------------------|--------|
| yes | any | any | any | Prompt for un-flagged steps |
| no | yes | no | any | Run non-interactively |
| no | yes | yes | yes (`-y` or `--book`) | Run non-interactively |
| no | any | any | (insufficient) | **Exit 2** with error |
| no | any | any | `-y` | Use defaults for all steps |

## Variable Interpolation

The settings template is written with three placeholders substituted at
init time (`str.replace` only — no Jinja):

| Token | Value |
|-------|-------|
| `{{project_name}}` | First `# H1` from `CLAUDE.md` (if present and not literally `Artifacts OS`); otherwise the target directory name. |
| `{{project_alias}}` | Lowercased first word of `project_name`, alphanumeric only, max 8 chars. |
| `{{created}}` | `datetime.date.today().isoformat()` |

## Existing-File Guard

Every write target is checked individually:

- File does not exist → write.
- File exists, no `--force` → skip with `⊘` marker.
- File exists, `--force` → overwrite with `(overwritten)` suffix.

The top-level guard (`artifacts.yaml` already exists) triggers
exit 2 unless `--force` is supplied.

## Error Handling

| Failure mode | Behaviour | Exit code |
|---|---|---|
| Manifest invalid (`ManifestError`) | Fail before any book pulls. | 2 |
| `git clone` failure (`FetchError`) — CLI `--distro` | Fail before any book pulls. | 2 |
| `git clone` failure — env `$ARTIFACTS_DISTRO_URL` | Fail with error, vault preserved. | 1 |
| `--book` references unknown book or item | Fail before any book pulls. | 2 |
| Per-book failure | Log error, skip book, continue loop. | 1 (at end) |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All writes succeeded (or `--dry-run`). |
| 1 | At least one file or book failed; others succeeded. |
| 2 | Usage error: bad flag, already-initialised without `--force`, non-TTY without `-y`/flags, manifest/clone failure with explicit `--distro`. |
| 3 | Target directory does not exist and parent is not writable. |

## Bundled Resources

Settings templates live under `src/artifacts_os/templates/settings/` and
are read via `importlib.resources.files("artifacts_os.templates")`.

The bundled skill lives at `src/artifacts_os/ai/claude/skills/artifacts-os/`
and is read via `importlib.resources.files("artifacts_os.ai.claude.skills")`.

Both ship inside the wheel — no network fetch required.

```
src/artifacts_os/
├── templates/settings/
│   ├── minimal.yaml
│   └── standard.yaml
└── ai/claude/skills/artifacts-os/
    └── SKILL.md
```
