# `artifacts init` — Three-Step Init Flow

The `artifacts init` command bootstraps a new artifacts-os vault through
three independent selection steps: settings tier, kinds, and agents. Each
step can be driven by a flag (to skip it) or an interactive prompt (on a
TTY). See spec `s0021-artifacts-init-flow` for the full rationale.

## Synopsis

```
artifacts init [DIRECTORY] [--template TIER] [--kinds CSV] [--agents CSV]
               [--force] [-y] [--dry-run] [--openstation-compat]
```

## The Three Steps

### Step 1 — Settings tier

Chooses one of two settings tiers, written as `artifacts/artifacts.yaml`.

| Tier | Content |
|------|---------|
| `minimal` | Mandatory header + three lifecycle views (`active`, `ready`, `done`). |
| `standard` (default) | Adds per-type task slices, per-kind landing views, `default_views` block, and cross-kind `recent` view. |

Tiers are **strictly additive** — `standard` is a superset of `minimal`.

### Step 2 — Kinds

Multi-select from the bundled catalogue. Installed files per kind:

```
artifacts/kinds/<name>.json          # JSON schema
artifacts/kinds/<name>/ARTIFACT.md   # body template
artifacts/<x-dir>/.gitkeep           # storage directory sentinel
```

| Kind | Default | Storage dir |
|------|---------|-------------|
| `task` | ✓ | `artifacts/tasks/` |
| `note` | ✓ | `artifacts/notes/` |
| `spec` | ✓ | `artifacts/specs/` |
| `research` | — | `artifacts/research/` |
| `agent` | — (auto-included with agents) | `artifacts/agents/` |

### Step 3 — Agents

Multi-select from the bundled catalogue. Installed files per agent:

```
artifacts/agents/<name>.md
```

Default: none. Available: `architect`, `author`, `developer`, `researcher`,
`technical-writer`.

**Agent-kind coupling (D10):** selecting any agent automatically adds the
`agent` kind to the Step 2 selection (even if Step 2 was driven by a flag
that omitted it). The summary line notes `(agent kind auto-included for
selected agents)`.

## Prompt Format

Single-choice (Step 1):

```
Settings tier (1 of 3):
  1) minimal      — header + lifecycle views (active / ready / done)
  2) standard     — adds per-type slices, default_views, cross-kind 'recent'

Choice [2]: <enter>
```

Multi-select (Steps 2 and 3):

```
Kinds (2 of 3) — comma-separated numbers, '*' for all, '-' for none:
  1) task      [default]
  2) note      [default]
  3) spec      [default]
  4) research
  5) agent

Choice [1,2,3]: <enter>
```

Input formats accepted:
- Empty → defaults
- `*` → all
- `-` → none
- `1,3,5` → items by number
- `task,spec` → items by name
- `1,spec` → mixed numbers and names

## Non-TTY Behaviour

| stdin TTY? | All three flags? | `-y`? | Result |
|-----------|-----------------|-------|--------|
| yes | any | any | Prompt for un-flagged steps |
| no | yes | any | Run non-interactively |
| no | no | yes | Use defaults for un-flagged steps |
| no | no | no | **Exit 2** with error |

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

The top-level guard (`artifacts/artifacts.yaml` already exists) triggers
exit 2 unless `--force` is supplied.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All writes succeeded (or `--dry-run`). |
| 1 | At least one file failed to write; others succeeded. |
| 2 | Usage error: bad flag, already-initialised without `--force`, non-TTY without `-y`/all-flags, missing bundled template. |
| 3 | Target directory does not exist and parent is not writable. |

## Bundled Templates

Templates live under `src/artifacts_os/templates/` and are read via
`importlib.resources.files("artifacts_os.templates")`. They ship inside
the wheel — no network fetch, no external install cache required.

```
src/artifacts_os/templates/
├── settings/minimal.yaml
├── settings/standard.yaml
├── kinds/{task,note,spec,research,agent}/kind.json
├── kinds/{task,note,spec,research,agent}/ARTIFACT.md
└── agents/{architect,author,developer,researcher,technical-writer}.md
```

Adding a kind or agent template is a pure file addition — no registration
list needs updating.
