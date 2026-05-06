---
kind: task
id: t0112
name: collapse-agent-aliases-list-to
type: feature
status: done
assignee: developer
owner: user
created: 2026-05-06
started: 2026-05-06
completed: 2026-05-06
---

# Collapse Agent Aliases List To Single Alias Field

## User story

**As an** agent author writing or reading an agent spec,
**I want** the agent kind to expose a single optional `alias` field
instead of an `aliases` list,
**so that** the frontmatter matches the way agents are actually
named in practice — one canonical shorthand or none — and the
contract stops promising flexibility nobody uses.

## Why

Every agent under `artifacts/agents/` carries either zero or one
alias today, and has done since the kind was introduced:

- `architect: [arch]`, `developer: [dev]`, `researcher: [res]`,
  `devrel: [dr]`, `technical-writer: [tw]`,
  `project-manager: [pm]`, `product-manager: [pdm]`
- `author`, `security-engineer` — empty

The list syntax (`aliases: [pdm]`) pays for plural shape that the
data never spends. Short forms are namespace-collision-prone by
design — there is one good shorthand per agent, and the long
canonical name carries the rest of the disambiguation. "One
alias" is a real constraint, not a coincidence.

This is also a low-stakes moment to make the change: the field
has **no live consumers** today. No resolver maps `pdm →
product-manager`; `validate.py` only allow-lists the key, and
`artifacts.yaml` lists it as a column in the `agents` view.
Migrating now is rename-and-edit, not refactor-the-resolver.

Pre-1.0, before any harness logic depends on the plural shape, is
the right window.

## Directions

*Intent, not contract — `architect` may refine before/while
specifying, and may decide whether a spec sub-task is warranted
given the small surface.*

- **Rename `aliases` (YAML list) → `alias` (scalar string),
  optional.** Agents without an alias omit the field entirely
  rather than carrying `alias:` with empty value.
- **Clean break, no tolerant deprecation window.** The field has
  no live consumers and the repo is pre-1.0 — accepting both
  shapes for a release would be overkill. Update every agent in
  the same change.
- **Touch list (non-exhaustive — architect/developer to confirm):**
  - `artifacts/kinds/agent/ARTIFACT.md` — kind contract / field
    table / skeleton example.
  - `src/artifacts_os/templates/kinds/agent/ARTIFACT.md` — same,
    bundled template copy.
  - `artifacts/agents/*.md` — all nine current agents.
  - `src/artifacts_os/templates/agents/*.md` — all nine bundled
    templates.
  - `src/artifacts_os/core/validate.py` — built-in field
    allow-list (`aliases` → `alias`).
  - `artifacts/artifacts.yaml` — the `agents` view's `columns:
    name,aliases,description` → `name,alias,description`.
  - Any references in `docs/`, `.openstation/docs/`, or task
    bodies that document the field shape.
- **No new resolver behavior in this task.** Whether the harness
  ever resolves `pdm → product-manager` is a separate decision;
  this task only collapses the schema.
- **Docs travel with the change.** The kind contract
  (`artifacts/kinds/agent/ARTIFACT.md` and the bundled template
  copy) and any prose under `docs/` or `.openstation/docs/` that
  references the field shape must land in the same change as the
  agent files — not as a follow-up. Per repo policy, doc updates
  accompany API/schema changes in the same commit.

## Open questions

1. **Architect spec sub-task — yes or no?** The change is small
   (rename + scalar conversion across a closed set of files), no
   algorithm, no API surface change. Architect call: spec it if
   the touch list or the validate.py interaction warrants it,
   otherwise hand straight to `developer`.
2. **Anything in the AI/harness layer planning to use the plural
   shape?** Quick check before the change lands. If a planned
   feature already assumed multi-alias fallback, surface it now
   rather than rediscover it later.
3. **`agents` view column header.** After rename, the column
   still reads cleanly as `alias`. No header customization
   needed unless `artifacts list` rendering looks odd — flag if
   so.

## Sub-tasks

To be decided by `architect` on first read — see Open questions
#1. Default expectation: no spec sub-task; this task is sized
for a single implementer pass once architect confirms.

## Findings

Renamed `aliases` (YAML list) → `alias` (scalar string) across the full touch list. **Premise correction:** the task spec claimed the field had no live consumers, but the external `openstation` package (v0.20.1) reads `aliases` in `run.py::resolve_agent_alias` to map shortcuts (`dev → developer`). The harness IS a live consumer. After verifying `os run dev` failed post-rename, the user opted for a temporary compatibility shim: keep both fields in agent files until openstation is updated.

**Final state of the rename:**
- `artifacts/agents/*.md` (9 files) — agents with shortcuts now have **both** `alias: x` (canonical, new) and `aliases: [x]` (legacy, harness-compat). `author` and `security-engineer` remain field-less.
- `src/artifacts_os/templates/agents/*.md` (9 files) — same dual-field shape.
- `artifacts/kinds/agent/ARTIFACT.md` — field table documents `alias` (scalar, optional) as the canonical key.
- `src/artifacts_os/templates/kinds/agent/ARTIFACT.md` — same.
- `src/artifacts_os/core/validate.py` — `_BUILTIN_FIELDS` allow-lists **both** `alias` and `aliases` (with a comment pointing back to t0112) so neither field generates an unknown-key warning.
- `artifacts/artifacts.yaml` — `agents` view columns: `name,alias,description` (renders the new canonical column).

**Verification results:**
- All 9 agents pass `artifacts validate --kind agent` with no warnings.
- `artifacts list --kind agent` renders `alias` column with expected values.
- `openstation run dev --dry-run` correctly resolves `dev → developer` (regression fix confirmed).
- 15 validate tests pass; 622/626 of the wider suite pass (4 pre-existing `test_release_changelog_skill.py` failures unrelated).

**Compromise:** the "clean break" goal in the spec is **not** achieved — `aliases` lives on as a shim. Removing it requires either (a) updating `openstation` to read `alias` instead, then bumping the dependency, or (b) accepting the harness regression. Flagged for follow-up below.

## Downstream

- **Update `openstation` package to read `alias` (scalar)** — the
  external harness at `~/.local/lib/python3.12/site-packages/openstation/run.py`
  (source likely at `~/workspace/os/open-station/`) currently reads
  the deprecated `aliases` list in `discover_agents` /
  `resolve_agent_alias` / `format_agents_table`. Once it reads
  `alias` (and continues tolerating `aliases` for one release for
  external consumers), the shim in this repo can be removed.
- **Drop `aliases` from agent files and `_BUILTIN_FIELDS`** — once
  the dependency above ships, file a follow-up task to delete
  every `aliases: [x]` line and tighten `validate.py` back to
  `alias`-only. That is the original intent of t0112.
- **Spec premise audit** — the t0112 spec asserted "no live
  consumers" without auditing the external `openstation` package.
  Future schema-rename tasks should check both `artifacts_os`
  (this repo) **and** `openstation` (the harness) for field
  consumers before claiming a clean break.

## Progress

### 2026-05-06 — developer
> time: 14:15

Completed rename: aliases→alias across all agent files, kind contract, templates, validate.py, and artifacts.yaml. All 9 agents validate clean; artifacts list renders alias column correctly.

### 2026-05-06 — developer
> time: 14:30

User reported `os run dev` broken post-rename. Root cause: external `openstation` package reads `aliases` (list) in `run.py::resolve_agent_alias` to resolve shortcuts; my rename collapsed the field. Per user direction (option 3), restored `aliases: [x]` alongside `alias: x` in all agent files and templates as a temporary harness-compat shim. Updated `validate.py` to allow both keys. Verified `os run dev → developer` resolves again. Findings + Downstream sections updated to flag the openstation follow-up needed before the shim can be dropped.

## Verification

- `artifacts/agents/*.md` — every agent uses `alias: <name>` (or
  omits the field). No file contains the key `aliases`.
- `src/artifacts_os/templates/agents/*.md` and
  `src/artifacts_os/templates/kinds/agent/ARTIFACT.md` — same
  shape as the live copies.
- `artifacts/kinds/agent/ARTIFACT.md` — field table and skeleton
  document `alias` (scalar, optional). No reference to a list
  form except, optionally, a one-line migration note.
- Any references in `docs/` or `.openstation/docs/` that mention
  the agent `aliases` field have been updated to `alias`. Doc
  changes ship in the same commit as the schema/agent changes.
- `artifacts validate <agent-name> --kind agent` passes for every
  agent (no warnings about an unknown `aliases` field).
- `artifacts list --kind agent` renders an `alias` column with
  the expected values; agents without an alias show empty.
- `artifacts/artifacts.yaml` — `agents` view's columns updated.
- `grep -R "aliases" src/ artifacts/kinds artifacts/agents docs/`
  returns no matches that refer to the agent field (CLI command
  aliases under `cli/` are a different concept and remain
  untouched).
