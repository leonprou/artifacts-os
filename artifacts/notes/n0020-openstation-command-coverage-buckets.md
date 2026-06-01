---
created: 2026-06-01
id: n0020
kind: note
name: openstation-command-coverage-buckets
---

Bucket sort of every `openstation` CLI command by how well existing
`artifacts-os` modules cover it. Companion to
[[r0001-openstation-integration-audit]] (architectural shape) and
[[n0019-openstation-views-as-commands-vs]] (flat-verb vs grouped-verb
surface). This note focuses on **command-by-command** coverage, not
module-level overlap.

## Three buckets

- **Simple** — artifacts modules already cover the data + mechanism;
  openstation command is a thin wrapper / kind-scoped translation.
- **Medium** — mechanism is in place; openstation-specific schema or
  small core extension required.
- **Hard** — no analogue, or implementation would break artifacts'
  architectural rules ("no lifecycle in `cli`", layered DAG, library-
  not-daemon shape).

## Simple — covered today

Every command here maps onto an existing artifacts primitive. The
data model is identical; only the verb shape may differ.

| openstation | artifacts mechanism |
|---|---|
| `list` / `ls` (`--kind`, `--status`, `--assignee`, `--fields`, `--view`) | `artifacts list` — same flag vocabulary, plus richer layouts (`tree`, prune modes). "active" status default is just a default `views:` filter. |
| `agents {list, show, create}` | `artifacts list/show/create --kind agent` |
| `artifacts {list, show}` | `artifacts list/show` (kind filter for non-task) |
| `research / specs / notes / tasks {list, show, create}` + positional shorthand | `artifacts list/show/create --kind <X>`; positional shorthand collapses into `artifacts show <name>` (kind-agnostic resolver) |
| `show` / `sh` (without `--blocks`) | `artifacts show` — same `--json` / `--editor` surface |
| `create` / `new` (basic frontmatter + body) | `artifacts create` — `core.store.create` writes frontmatter+body atomically |
| `verify` (`--all`, `--fix`, `--dry-run`) | `artifacts verify` — `core.validate.validate_one/many` with fixable hints |
| `events {list, follow}` (`--type`, `--task`, `--since`, `--limit`) | `artifacts events` — closed catalogue + `--follow` / `--tail` / `--since` / `--event`. Identical CLI shape. |
| `hooks {list, show, enable, disable}` | `kind: hook` + `artifacts/hooks/.active/` + `artifacts hooks` CLI (s0032 shipped) |
| `alerts create` (storage half only) | `artifacts create --kind alert`; `--connector-type` / `--schedule` are frontmatter pass-through |
| `init` | `artifacts init --openstation-compat` — books-driven flow lands settings + agents + skills via promotion |

## Medium — needs a small extension

Mechanism is there; openstation-specific contract or vocabulary must
be expressed somewhere before the command is a thin wrapper.

| openstation | What's already there | Extension required |
|---|---|---|
| `create` with `--parent` / `--depends-on` / `--type` / `--owner` | `artifacts create` writes any frontmatter; `--parent` already backlinks `subtasks` atomically | Workflow rules (subtask blocking, parent auto-promotion) live openstation-side, *or* express as `phase: pre` hook on `artifact.created` |
| `show --blocks` | `artifacts show` | Add `core.discover.reverse_lookup(field, target)` — inverse-dependency query over `depends_on` / `parent`. Self-contained core helper. |
| `status` / `st` (transition mechanics only) | `artifacts status` shipped; per-property state shipped (t0186/t0187); `transitions_for` API landed | Encode openstation's transition graph in `task/kind.json` (declarative-transitions design is in flight). `--reason` on `failed` becomes a kind-schema "required field on transition" rule. |
| `bugs` / type-scoped flat verbs | `artifacts views <name>` runs a view; aliases work today | Flat-verb surfacing — see [[n0019-openstation-views-as-commands-vs]]. Strategy fork, not a hard blocker. |
| `hooks run TASK FROM TO` (manual trigger by transition) | hook loader, actions, `.active/` shipped | openstation's `StatusTransition` matcher vocabulary registered on the openstation host loader; no artifacts change needed |
| `alerts {pause, resume, done}` | `kind: alert` is just an artifact | Collapses into `artifacts status <name> <new>` once the alert kind declares its transition graph. Same Medium category as `status`. |
| `logs` (per-task JSONL tail / follow / format) | Daily-JSONL streaming + `--follow` / `--tail` primitive shipped in `events` module | `log/` is still a stub (s0004 / s2063). Either flesh out `log/` to reuse events streaming primitives, or keep openstation-side until log/ ships. |
| `cc-sessions` | nothing artifact-shaped — it's a Claude Code log-file inspector | Doesn't break anything; could live alongside `log/` once that stub fleshes out, or stay openstation-side. |

## Hard — architecturally out of scope

Workflow / operational concerns artifacts deliberately does not own.

| openstation | Why it doesn't fit |
|---|---|
| `status` *workflow rules* (parent-blocks-ready, owner=user vs agent, review→verified ownership, failed→requires-reason) | These are workflow policy above the transition graph. `core.transitions` declares legal transitions; *who* can transition and *what side-effects fire* is openstation lifecycle, not artifacts. |
| `run` (agent launch) | `ai/` is a stub (s2066) and intentionally so. tmux/detached, `--budget`/`--turns`/`--max-tasks`, `--editor`, `--worktree`, mode auto-detect — none of this is artifact CRUD. |
| `sessions` / `ss` (+ `state.db`, `--attach`, `--resume`, `--kill`, `--gc`) | SQLite-backed runtime state, process lifecycle, tmux attach. Would force a database dependency on `core`. **Architecturally incompatible.** |
| `alerts` *dispatch* half (heartbeat firing, connector clients: slack / telegram / github / internal) | Communication backends + scheduler. Not artifact concerns. The *storage* half is Simple; the *dispatch* is Hard. |
| `heartbeat` (cron-driven due-reminder processor) | Same — scheduler + connector dispatch. Long-running daemon-shaped behavior; artifacts is library-shaped. |
| `doctor` / `dr` (installation health, `--fix`, `--force`) | 675-LOC openstation-specific diagnostic playbook (CLAUDE.md state, `.claude/` symlinks, `.openstation/state.db`, worktree config). No useful generalization. |
| `run-complete` | Internal openstation run-lifecycle hook (suppressed in `--help`). |
| `self-update` | `pip install --upgrade` — not artifacts territory. Listed for completeness. |

## Surface-shape sidebar (grouped vs flat)

openstation uses **subparser groups** liberally
(`os agents {list, show, create}`, `os hooks {list, show, run, …}`,
`os alerts {list, create, show, pause, resume, done}`, etc.).
artifacts-os bans nested subcommands per its own CLI Conventions:

> Flat verbs — one-word top-level verb, no nested subcommands.
> Streaming, paging, and mode variants belong as flags on the verb.

The Simple-bucket bet is: openstation keeps its grouped surface
user-facing and **translates to flat artifacts verbs internally**:

| openstation user-facing | artifacts call underneath |
|---|---|
| `os agents list` | `artifacts list --kind agent` |
| `os agents show X` | `artifacts show X --kind agent` |
| `os agents create X` | `artifacts create X --kind agent` |
| `os hooks enable N` | `artifacts hooks enable N` (already flat in artifacts) |
| `os alerts pause X` | `artifacts status X paused --kind alert` (after declarative transitions) |

Operators see grouped verbs; openstation calls flat artifacts under
the hood. No artifacts-side bend of the flat-verb rule needed.

## Two extension points that collapse Medium → Simple

If the goal is to maximize "Simple" coverage, two small additions to
artifacts do most of the work:

1. **`core.discover.reverse_lookup(field, target)`** — unblocks
   `show --blocks` and any future "what depends on X" query.
   Self-contained, no architectural impact.
2. **Declarative transition graph + required-field rules in
   `kind.json`** — already in flight (t0186 / t0187 shipped,
   `transitions_for` API landed). Lets openstation express its
   lifecycle (and alert status verbs) in the task / alert kind
   schemas rather than in code.

## Bucket counts

| Bucket | Surface count | Approximate openstation LOC affected |
|---|---|---|
| Simple | ~11 surfaces | Most of the discovery/CRUD/rendering openstation re-implements (~3,500 LOC per r0001) |
| Medium | ~8 surfaces | Small per-surface; mostly schema work + a few core helpers |
| Hard | ~7 surfaces | The ~40% openstation-specific value (lifecycle, runs, alerts dispatch, doctor) — stays openstation-side by design |

The Simple + Medium buckets line up with r0001's "delete or thin out"
list. The Hard bucket lines up with r0001's "keep entirely on the
openstation side" list. Nothing new contradicts the audit.

## Sources

- `openstation <cmd> --help` for every top-level verb (snapshot
  2026-06-01)
- [[r0001-openstation-integration-audit]] — module-level coverage
  matrix and integration shape
- [[n0019-openstation-views-as-commands-vs]] — flat-verb vs grouped-
  verb surface analysis
- `src/artifacts_os/cli/commands/` — current artifacts CLI surface
- `CLAUDE.md` → "CLI Conventions" — flat-verb rule