---
kind: spec
id: s0030
name: books-driven-init-flow
status: draft
task: "[[t0166-spec-the-books-driven-init]]"
created: 2026-05-16
agent: architect
---

# Books-Driven `artifacts init` Flow

> **Revision (2026-05-18):** D2 (no-distro fallback) is amended by
> [[s0031-artbook-post-pull-artifact-promotion]] D40 to flow through
> canonical + promote instead of writing directly to `.claude/skills/`.
> The bundled skill now lands at `artifacts/skills/artifacts-os/` (canonical)
> and is symlinked into `.claude/skills/artifacts-os/` via `promote_book`.
> See s0031 §5.1 and §3 D40 for the updated contract.

Specifies the technical contract for the rewritten
`artifacts init` selection flow in which **books** are the only
selection unit beyond Step 1 (settings tier). Replaces today's
three independent bundled prompts (settings → kinds → agents)
plus the appended Step 4 (distro books) with a single, uniform
two-stage flow:

```
Step 1: Settings tier               (single choice — minimal / standard)
Step 2..N: For each book in distro  (multi-select items, default = all)
```

When no distro is configured, Step 1 runs alone and init
installs the bundled `artifacts-os` skill into
`.claude/skills/artifacts-os/` as the bare-minimum bootstrap.

This spec is the technical contract for
[[t0165-init-selection-driven-by-books]] (user-level intent).
It builds on [[s0029-artbook-mvp-distribution-model]] (artbook
distro model) and [[s0021-artifacts-init-flow]] (the original
three-step init flow, now superseded).

---

## 1. Background and Cross-References

### 1.1 Parent intent

[[t0165-init-selection-driven-by-books]] captures the user
story: there should be one catalogue and one selection model.
Today's `init` asks the operator the same questions twice — once
against the bundled `templates/kinds/` and `templates/agents/`
catalogues baked into the wheel, and again against the distro's
`kinds` and `agents` books. The two answers can disagree;
worst-case, Step 4's `kinds` book silently overwrites the kind
files Steps 2/3 just wrote.

### 1.2 Direct ancestors

- **[[s0021-artifacts-init-flow]]** — defined the original
  three-step bundled flow. §5 (CLI surface), §6 (settings tier),
  §7 (kinds), §8 (agents) are superseded by this spec. §3
  (non-goals), §9 (write order), §10 (re-init / `--force`),
  §11.1 (`--openstation-compat` symlink) are preserved.
- **[[s0029-artbook-mvp-distribution-model]]** — defines the
  artbook distro model that books-as-selection-unit relies on.
  No changes proposed to s0029.
- **[[t0163-artifacts-init-artbook-distro-integration]]** —
  introduced today's Step 4 (distro). This spec consolidates
  the two-catalogue flow Step 4 grafted onto Steps 2/3 into a
  single uniform loop.

### 1.3 Code touched

- `src/artifacts_os/cli/commands/init.py` — the entire
  selection flow is rewritten. Settings interpolation,
  per-file write helpers, dry-run, `--force`, and the
  `--openstation-compat` symlink survive verbatim.
- `src/artifacts_os/templates/{kinds,agents}/` — **deleted**
  (see §6.1).
- `src/artifacts_os/templates/settings/` — unchanged. Step 1
  still reads `minimal.yaml` / `standard.yaml` from this path.
- `src/artifacts_os/ai/claude/skills/artifacts-os/` — promoted
  to a packaged-wheel resource; copied into the consumer vault
  in the no-distro fallback path.
- `pyproject.toml` — wheel-artifact globs adjusted (§6.3).
- `docs/artbook.md`, `docs/init-flow.md`,
  `src/artifacts_os/cli/README.md` — updated to reflect the
  two-stage flow (§6.4).
- `tests/cli/test_init.py` — rewritten against the new flow
  (§7.5).

---

## 2. Goals

1. Eliminate the two-catalogue mismatch by making **books the
   only selection unit beyond Step 1**.
2. Preserve a useful, zero-distro bootstrap path: a fresh `art
   init` with no distro still produces a working vault and the
   `artifacts-os` skill that teaches Claude how to operate it.
3. Keep `-y`, `--force`, `--dry-run`, and `--openstation-compat`
   semantics unchanged — operators relying on these flags in
   CI scripts see no behavioural surprises beyond the removal
   of `--kinds` / `--agents`.
4. Make the new flag surface non-interactive-friendly so
   scripted init runs against a distro can specify exactly
   which books and items to pull without prompts.

## 3. Non-Goals

- **No replacement for the bundled `kinds` / `agents`
  templates.** Once a project moves past the no-distro
  fallback, it pulls those from a distro. The artifacts-os
  repo (publishing itself as its own distro per `artbook.yaml`)
  remains the canonical source.
- **No new per-book manifest fields** (`init:`, `default:`,
  etc.). Distro authors who need a book opt-out wait for a
  follow-up spec; the MVP loops every book in declaration
  order with all items defaulted-selected.
- **No backwards-compat shim** for `--kinds` / `--agents`. They
  are removed cleanly; release notes warn (Q7).
- **No changes to `book list` / `book show` / `book pull`.**
  Those CLI verbs are unchanged.

---

## 4. Locked Decisions (D1–D6, verbatim from t0166)

These were settled by the user during brainstorming. Restated
here verbatim — the spec records them and designs around them.

### D1 — Flow shape

```
Step 1: Settings tier               (single choice: minimal / standard)
Step 2..N: For each book in distro: (only when a distro is configured)
            multi-select prompt for items, default = all
```

Two stages, nothing else. No standalone "kinds" prompt; no
standalone "agents" prompt.

### D2 — No-distro fallback = templates stage only + bundled skill

When neither `--distro` nor `$ARTIFACTS_DISTRO_URL` is set:

- Run Step 1 only (settings tier → write `artifacts.yaml`).
- Install the bare-minimum bootstrap: the **artifacts-os
  skill** (currently
  `src/artifacts_os/ai/claude/skills/artifacts-os/`) into
  `.claude/skills/artifacts-os/`.
- Exit.

No kinds are installed. No agents are installed. The vault is
intentionally **empty but functional** — the user grows it
later by configuring `artbook.distro_url` and running
`artifacts book pull`, or by re-running `artifacts init
--distro <url> --force`.

The bundled artifacts-os skill is the only piece of
opinionated content the package itself ships into the vault.

### D3 — Per-book prompt = single multi-select

Each book in the distro gets the same prompt UX as today's
kinds/agents step (`_prompt_multi_step`), defaults to all
items:

```
Book 'agents' (11 items) — comma-separated numbers, '*' for all, '-' for none:
  1) architect  [default]
  2) author     [default]
  ...
Choice [*]:
```

One round-trip per book. No separate "all / select / none"
gate.

### D4 — Settings tier stays bundled

Step 1 keeps its current source: bundled
`src/artifacts_os/templates/settings/{minimal,standard}.yaml`.
The tier is **not** a book and does not move into the distro
manifest.

### D5 — `--force` re-prompts every book

A re-init on an existing vault with `--force` re-runs every
prompt (including the book loop) from scratch and overwrites
all matching files. No "skip books with items already
present" optimisation — predictable beats clever.

### D6 — `-y` with no distro installs the D2 defaults

`-y` means "accept defaults non-interactively", not "do
nothing". With no `--distro` and no `$ARTIFACTS_DISTRO_URL`,
`art init -y` runs the D2 fallback exactly: writes
`artifacts.yaml` for the default tier (`standard`) and
installs the bundled `artifacts-os` skill into
`.claude/skills/artifacts-os/`. No prompts, no kinds, no
agents — the same payload the interactive no-distro path
produces, just without the tier question. Don't overthink
it; the common case wins.

---

## 5. Open-Question Decisions (Q1–Q7)

For each open question in t0166, the spec records an explicit
decision and rationale. Each decision is the one to implement.

### Q1 — Flag-surface disposition

**Decision Q1.a — Delete `--kinds` and `--agents` in the same
release that ships this flow.**

Rationale:
- Under D2 there is no surface for these flags to write to —
  the bundled `templates/kinds/` and `templates/agents/`
  directories are deleted (Q2).
- A deprecation shim would have to map `--kinds task` to "pull
  the `task` item from the *distro's* `kinds` book", which is
  ambiguous if the distro doesn't ship that exact item, doesn't
  ship a `kinds` book at all, or ships it under a different
  name. The mapping is unsafe in the general case.
- The flags are recent (introduced by [[s0021-artifacts-init-flow]]
  in [[t0108-spec-artifacts-init-flow-with]]); no long-lived CI
  scripts can claim grandfathered surface. Release notes are
  sufficient mitigation.

Concretely: drop both `--kinds` and `--agents` from
`register()`; delete `_parse_csv_flag`, `_load_kind_*`,
`_load_agent_template`, `_discover_kinds`, `_discover_agents`,
`_DEFAULT_KINDS`, `_DEFAULT_AGENTS`, and the D10 "auto-include
agent kind" branch. Tests that exercise these flags are
removed.

**Decision Q1.b — Add a new non-interactive item-filter flag:
`--book` (repeatable, format `NAME[:ITEM[,ITEM...]]`).**

Replaces and generalises today's `--books CSV`:

| Form                                              | Meaning                                         |
|---------------------------------------------------|-------------------------------------------------|
| `--book agents`                                   | Pull every item from book `agents`.             |
| `--book agents:architect,developer`               | Pull only `architect` and `developer` items.    |
| `--book skills:artifacts-os --book commands`      | Mix: filtered `skills`, full `commands`.        |
| (no `--book` flag, distro configured)             | Pull every book, every item — same as `-y`.     |

Rules:

- `--book` is **repeatable**; each token names exactly one
  book.
- The `:` separator disambiguates book-name vs item; items
  inside are comma-separated. No nested escape rules. (The
  alternative `--books NAME:ITEM,ITEM NAME:ITEM,ITEM` from
  t0166 is rejected because the shell quoting cost outweighs
  the one-flag savings.)
- An item not present in the book → init exits 2 before
  cloning further state (consistent with `book pull`'s
  pre-write item validation from
  [[s0029-artbook-mvp-distribution-model]]).
- A book name not present in the manifest → init exits 2 with
  available names listed (matches today's `--books` error).
- `--book` without `--distro` (and without
  `$ARTIFACTS_DISTRO_URL`) is a usage error (exit 2).

**Rejected alternative — keep `--books CSV` and add
`--book-items NAME=ITEM,ITEM`.** Two flags is more surface
than one; `--book NAME[:items]` covers both filter modes with
a single mental model. Backwards-compat is not a constraint
(t0163 is recent and the bundled `--books` users are
internal).

### Q2 — Migration of `src/artifacts_os/templates/{kinds,agents}/`

**Decision Q2 — Delete both directories outright in the same
release.**

Rationale:
- D2 removes every code path that reads them. Under the
  no-distro fallback, no kinds/agents are installed. Under the
  distro path, the distro is authoritative.
- The artifacts-os repo itself already publishes these files
  via its own `artbook.yaml` (the `kinds` and `agents` books).
  Consumers who want the canonical artifacts-os defaults
  configure `artbook.distro_url: https://github.com/leonprou/artifacts-os`
  and `art book pull`. No duplication needed.
- Keeping a "self-distro" copy in `src/artifacts_os/templates/`
  to support offline init is overkill: `book pull` is online
  by design (no caching, see s0029 §6); a synchronous bundled
  copy would have to be re-validated against the wheel build
  to stay in sync. Net negative.

Files deleted:

- `src/artifacts_os/templates/kinds/{agent,note,research,spec,task}/`
- `src/artifacts_os/templates/agents/*.md` (9 files)

Loader code deleted (from `src/artifacts_os/cli/commands/init.py`):

- `_load_kind_schema`
- `_load_kind_artifact`
- `_load_agent_template`
- `_discover_kinds`
- `_discover_agents`
- `_parse_csv_flag`
- `_DEFAULT_KINDS`
- `_DEFAULT_AGENTS`
- The D10 agent-kind auto-include block

Wheel-artifact globs deleted from `pyproject.toml`:

- `"src/artifacts_os/templates/kinds/*/kind.json"`
- `"src/artifacts_os/templates/kinds/*/ARTIFACT.md"`
- `"src/artifacts_os/templates/agents/*.md"`

Note: `src/artifacts_os/templates/settings/*.yaml` is **kept** —
Step 1 still reads from it (D4).

### Q3 — Bundled skill location and packaging

**Decision Q3 — Read the bundled skill via `importlib.resources`
from the package install location, not the source tree. Package
it explicitly in the wheel.**

Loader pattern (mirrors today's `_load_settings_template`):

```python
def _bundled_skill_root() -> Traversable:
    from importlib.resources import files
    return files("artifacts_os.ai.claude.skills").joinpath("artifacts-os")
```

`importlib.resources.files("artifacts_os.ai.claude.skills")`
resolves through the `skills` Python package; the `artifacts-os`
subdirectory is a non-package subdir reached via the
`Traversable.joinpath` operator. Its dash-in-name is tolerated
because we never import it as a Python module.

**Walker for the bundled skill install (no-distro fallback only).**
Walk the Traversable recursively and write every file to
`{target}/.claude/skills/artifacts-os/{rel}`. Apply the same
exclusion rules that the D26 recurse walker uses for the same
unit during `book pull`:

| Excluded | Why |
|----------|-----|
| `__init__.py` (and nested) | Python packaging artifact — not part of the skill contract |
| `__pycache__/` | Python build cache |
| `*.pyc`, `*.pyo` | Python compiled bytecode |
| dotfiles | Convention |

This guarantees the install is byte-identical to what
`artifacts book pull skills artifacts-os` from the artifacts-os
distro would produce (assuming the distro's skill source is the
same tree). The two paths converge on the same content; an
operator who later switches from no-distro to distro gets no
surprise diff.

**Packaging.** `pyproject.toml` adds:

```toml
[tool.hatch.build.targets.wheel]
artifacts = [
    "src/artifacts_os/templates/settings/*.yaml",
    # NEW — bundled skill (D2 fallback payload)
    "src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md",
]
```

Globbing `**/*.md` is rejected: hatchling globs are not
recursive and we want explicit wheel manifest entries. As the
skill grows new files, they're added one-by-one to this list —
a single point of failure with a deterministic surface area.
If the skill ever needs many non-`.md` non-`.py` files (e.g.
scripts, sample data), this list expands rather than turning
into a wildcard.

The skill's `__init__.py` is **not** excluded from packaging
(hatchling needs it to recognise the directory) but **is**
excluded from the install walk (per the exclusion table
above), so the consumer's `.claude/skills/artifacts-os/`
contains only `SKILL.md` (and any future non-Python files).

### Q4 — Distro skill collision

**Decision Q4 — Skip the bundled-skill install when any
distro is configured. The bundled skill is installed only on
the D2 fallback path.**

Rationale:
- The bundled skill is a *bootstrap*, not a baseline. When a
  distro is configured, the distro is authoritative.
- Last-write-wins would create a transient window during init
  where `.claude/skills/artifacts-os/SKILL.md` contains the
  package's bundled copy, then the distro's `skills` book pulls
  a different version over it. Debugging "which copy did init
  leave?" is harder than "init wrote what the distro said".
- If the operator deselects `artifacts-os` from the distro's
  `skills` book in the per-book prompt (D3), the bundled copy
  would *remain* — a hidden state leak. Always-distro avoids
  this entirely.
- If the distro doesn't ship the artifacts-os skill at all,
  the consumer ends up without it. They can either include it
  in their distro (one-time author task) or run `art book pull
  skills artifacts-os` against the artifacts-os repo's own
  distro URL. Both are explicit user actions; init is not the
  place to disagree with the operator's distro choice.

Concretely: the bundled-skill install runs **only** inside
the D2 branch. The distro branch (D1) goes straight from
Step 1 to the book loop.

### Q5 — Book ordering and per-book init opt-out

**Decision Q5.a — Books loop in `artbook.yaml` declaration
order** (`manifest.books` from `read_manifest`). Confirmed and
documented; no sort, no special precedence rules.

**Decision Q5.b — No new per-book manifest fields in this
spec.** Distro authors who need to opt a book out of init's
loop or change its default item set wait for a follow-up.
The spec leaves the door open by reserving the field names
`init:` (boolean, default `true`) and `default:` (list of
item names, default `*`) for a future revision of
`s0029-artbook-mvp-distribution-model`.

Rationale:
- The MVP scope is "fix the two-catalogue mismatch", not
  "add a distro-author DSL". Adding fields without a
  concrete consumer is speculative.
- The simplest workaround for an author who wants a book
  excluded from init: move the items out of the manifest until
  init scope solidifies, or document "pull this book manually
  with `art book pull <name>` after init".

### Q6 — Error semantics during the book loop

**Decision Q6 — Two-tier error handling, matches today's
`_run_distro_step`:**

| Failure mode                                       | Behaviour                                                                          | Exit code |
|----------------------------------------------------|------------------------------------------------------------------------------------|-----------|
| Manifest invalid (`ManifestError` at `read_manifest`) | Fail before any book pulls; print `error: distro manifest invalid: <msg>`.       | 2         |
| `git clone` failure (`FetchError`)                  | Fail before any book pulls; print `error: git clone failed …`. Vault preserved.    | 2         |
| `--book` references unknown book/item              | Fail before any book pulls; print `error: …; Available: …`.                        | 2         |
| Per-book failure (empty `src`, vault-escape `dest`, etc.) | Log error, skip the book, **continue the loop**. Init exits non-zero at end. | 1         |

The "continue the loop on per-book failure" choice preserves
the property that one bad book in a multi-book distro doesn't
strand the operator's vault in a half-initialised state — they
get every other book and a clear failure list. This matches the
behaviour [[t0163]] introduced for Step 4; no change.

Concretely: errors raised inside the book loop are caught,
printed to stderr, and accumulated; `had_error` flips to True
and init's exit code is 1. The book that failed is reported
but the next book proceeds.

### Q7 — Backward compatibility and release notes

**Decision Q7 — Breaking change in the next minor; release
notes flag four migration points.**

| Affected surface                              | Old behaviour                                                | New behaviour                                                                                  |
|-----------------------------------------------|--------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| `art init --kinds CSV` / `--agents CSV`       | Selected from bundled templates.                             | Removed; init prints `unknown option: --kinds` and exits 2. Use `--distro` + `--book` instead. |
| `art init --books CSV`                        | Wholesale book selection.                                    | Removed; replaced by repeatable `--book NAME[:items]`. Same wholesale form via `--book NAME`.  |
| `art init` with no `--distro` (interactive)   | Walks Steps 1 → 2 → 3; installs bundled kinds + agents.      | Walks Step 1 only; installs bundled `artifacts-os` skill. No kinds, no agents.                 |
| `art init` with no `--distro` (`-y`)          | Same as interactive but defaulted.                           | Settings tier `standard` + bundled skill. No kinds, no agents.                                 |

Docs/examples updated in the same release (see §6.4). Distro
authors are unaffected — `artbook.yaml` schema is unchanged.

Pre-release announcement copy should highlight: "If you relied
on `art init` installing the standard task/note/spec kinds
without a distro, configure
`artbook.distro_url: https://github.com/leonprou/artifacts-os`
and run `art init --distro <url> -y` instead. Or run `art book
pull kinds` after a no-distro init."

---

## 6. Migration Inventory

Every file that changes in the implementation. Cross-referenced
to the implementation sub-task that touches it (§7).

### 6.1 Source code (`src/`)

| Path                                                                        | Change           | Sub-task |
|-----------------------------------------------------------------------------|------------------|----------|
| `src/artifacts_os/cli/commands/init.py`                                     | Rewrite (§4–§5)  | I1       |
| `src/artifacts_os/templates/kinds/agent/`                                   | Delete           | I2       |
| `src/artifacts_os/templates/kinds/note/`                                    | Delete           | I2       |
| `src/artifacts_os/templates/kinds/research/`                                | Delete           | I2       |
| `src/artifacts_os/templates/kinds/spec/`                                    | Delete           | I2       |
| `src/artifacts_os/templates/kinds/task/`                                    | Delete           | I2       |
| `src/artifacts_os/templates/agents/architect.md`                            | Delete           | I2       |
| `src/artifacts_os/templates/agents/author.md`                               | Delete           | I2       |
| `src/artifacts_os/templates/agents/developer.md`                            | Delete           | I2       |
| `src/artifacts_os/templates/agents/devrel.md`                               | Delete           | I2       |
| `src/artifacts_os/templates/agents/product-manager.md`                      | Delete           | I2       |
| `src/artifacts_os/templates/agents/project-manager.md`                      | Delete           | I2       |
| `src/artifacts_os/templates/agents/researcher.md`                           | Delete           | I2       |
| `src/artifacts_os/templates/agents/security-engineer.md`                    | Delete           | I2       |
| `src/artifacts_os/templates/agents/technical-writer.md`                     | Delete           | I2       |
| `src/artifacts_os/templates/settings/minimal.yaml`                          | Unchanged        | —        |
| `src/artifacts_os/templates/settings/standard.yaml`                         | Unchanged        | —        |
| `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`                   | Unchanged        | —        |
| `src/artifacts_os/ai/claude/skills/artifacts-os/__init__.py`                | Unchanged        | —        |

### 6.2 Packaging

| Path             | Change                                                                                              | Sub-task |
|------------------|-----------------------------------------------------------------------------------------------------|----------|
| `pyproject.toml` | Remove `templates/kinds/*` and `templates/agents/*.md` globs; add `ai/claude/skills/artifacts-os/SKILL.md`. | I3       |

### 6.3 Tests

| Path                          | Change                                                                                    | Sub-task |
|-------------------------------|-------------------------------------------------------------------------------------------|----------|
| `tests/cli/test_init.py`      | Rewrite: delete kinds/agents flag tests; rewrite distro tests for the new `--book` flag.  | I5       |
| `tests/cli/conftest.py` (if any) | Update fixtures that materialise bundled kinds/agents in vault scaffolds.                | I5       |

### 6.4 Docs

| Path                                          | Change                                                                                                                                       | Sub-task |
|-----------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|----------|
| `docs/init-flow.md`                           | Rewrite. Two-stage flow, D2 fallback, transcripts mirroring §7.                                                                              | I4       |
| `docs/artbook.md`                             | Update "Consumer Quickstart — `artifacts init --distro`" section. Drop references to Steps 2/3 (kinds, agents); show the new book loop.      | I4       |
| `src/artifacts_os/cli/README.md`              | Update `init` section: drop `--kinds`/`--agents`, document `--book`, list the two-stage selection flow in `description=…`.                   | I4       |
| `CHANGELOG.md` / release notes for next minor | Q7 migration table.                                                                                                                          | I6       |

---

## 7. Worked Transcripts

The three transcripts the t0166 verification checklist requires.

### 7.1 Transcript A — No-distro interactive (D2)

Fresh directory, no `--distro` flag, no `$ARTIFACTS_DISTRO_URL`.

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
  ✓ .claude/skills/artifacts-os/SKILL.md

Initialised artifacts-os project: /path/to/proj
$ tree
.
├── artifacts.yaml
└── .claude
    └── skills
        └── artifacts-os
            └── SKILL.md
```

The user is told `1 of 1` (not `1 of 3` like today) — under D2
there is exactly one selection step. The `.claude/skills/`
install is the only opinionated content from the package.

### 7.2 Transcript B — Distro-configured interactive (D1 + D3)

Fresh directory with `--distro https://github.com/leonprou/artifacts-os`
(or `$ARTIFACTS_DISTRO_URL` set). Distro manifest declares four
books in order: `agents`, `commands`, `skills`, `kinds`.

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
  3) developer        [default]
  4) devrel           [default]
  5) product-manager  [default]
  6) project-manager  [default]
  7) researcher       [default]
  8) security-engineer [default]
  9) technical-writer [default]

Choice [*]: 1,3,9 ⏎
  ✓ agents: 3 files written

Book 'commands' (3 items) — comma-separated numbers, '*' for all, '-' for none:
  1) artifacts.create  [default]
  2) artifacts.list    [default]
  3) artifacts.show    [default]

Choice [*]: ⏎
  ✓ commands: 3 files written

Book 'skills' (2 items) — comma-separated numbers, '*' for all, '-' for none:
  1) artifacts-os         [default]
  2) release-changelog    [default]

Choice [*]: ⏎
  ✓ skills: 2 files written

Book 'kinds' (5 items) — comma-separated numbers, '*' for all, '-' for none:
  1) agent     [default]
  2) note      [default]
  3) research  [default]
  4) spec      [default]
  5) task      [default]

Choice [*]: 2,4,5 ⏎
  ✓ kinds: 3 files written

Initialised artifacts-os project: /path/to/proj
```

Notes:

- The `Settings tier (1 of N)` header dynamically displays the
  total number of steps once the manifest is read. (The
  manifest is fetched after Step 1, so this label is computed
  before the prompt — see §8.2 for the alternate
  implementation if pre-fetching is undesirable.)
- The bundled `.claude/skills/artifacts-os/SKILL.md` is **not**
  installed: Q4 — under a distro the bundled-skill install is
  skipped. The distro's `skills` book installs `artifacts-os`
  if the operator keeps it selected.
- Books are looped in manifest declaration order (Q5.a).
- Item validation, per-book item filtering, and atomic writes
  inherit from `pull_book` (s0029 §6); init does not duplicate
  that logic.

### 7.3 Transcript C — Non-interactive (D6 and `--book`)

Two variants on a single transcript: bare `-y` (no distro) and
fully-flagged distro pull.

#### 7.3.1 Bare `-y` — D6 fallback

```
$ art init -y

Selected:
  template : standard

Writing files...
  ✓ artifacts.yaml
  ✓ .claude/skills/artifacts-os/SKILL.md

Initialised artifacts-os project: /path/to/proj
```

Identical payload to Transcript A but no prompts.

#### 7.3.2 Fully-flagged distro

```
$ art init --distro https://github.com/leonprou/artifacts-os -y \
       --book agents:architect,developer \
       --book skills:artifacts-os \
       --book commands

Selected:
  template : standard
  distro   : https://github.com/leonprou/artifacts-os
  books    : agents (2 items), skills (1 item), commands (all)

Writing files...
  ✓ artifacts.yaml

Fetching distro manifest…
  ✓ agents: 2 files written
  ✓ skills: 1 file written
  ✓ commands: 3 files written

Initialised artifacts-os project: /path/to/proj
```

The `kinds` book is **not** pulled — it was not listed in any
`--book` flag.

When `--book` is mixed with `-y`:

- `-y` does **not** override `--book`; the flags are
  composable. `-y` resolves the *settings tier* prompt
  (chooses `standard`); `--book` resolves the *book loop*.
- With `-y` and no `--book` flag at all, every book is pulled
  with every item (D6 + Q1.b "no `--book` flag, distro
  configured" row).

---

## 8. Implementation Sketches

### 8.1 Flow control in `run(args)`

```python
def run(args) -> int:
    target = Path(args.directory).resolve()
    _validate_target(target)

    # Resolve distro URL: CLI > env > none.
    distro_url, distro_source = _resolve_distro(args)
    book_specs = _parse_book_flags(args, distro_url)  # list[BookSpec]
    is_tty = sys.stdin.isatty()

    _check_non_tty_guard(args, is_tty, distro_url, book_specs)
    _check_init_guard(target, args.force)

    # ── Step 1: settings tier (always runs) ─────────────────────
    tier = _resolve_tier(args, is_tty)
    _write_settings(target, tier, distro_url, ...)

    if distro_url is None:
        # ── D2 fallback ──────────────────────────────────────────
        _install_bundled_skill(target, force=args.force, dry_run=args.dry_run)
        return _finalise(target, ...)

    # ── D1 + D3: book loop ───────────────────────────────────────
    return _run_book_loop(
        distro_url, book_specs, target,
        yes=args.yes, dry_run=args.dry_run, is_tty=is_tty, force=args.force,
    )
```

Key invariants:

- `artifacts.yaml` is **always** written before any book pull
  or skill install. Carry over the `req 7` invariant from t0163.
- Per-file `_do_write` (existing helper) is reused unchanged.
- The non-TTY guard now checks: `is_tty || -y || (no distro
  and tier-flag) || (distro and book_specs cover the whole
  loop)`. Simpler than today because there are fewer step
  flags.

### 8.2 Book-count header in Transcript B

Two options for the `Settings tier (1 of N)` header:

1. **Pre-fetch manifest before Step 1.** Clone happens first
   (one extra round-trip in the no-cancel case). Header shows
   exact N.
2. **Defer the count.** Header reads `Settings tier (1 of ?):`;
   the question-mark resolves after the manifest is fetched.

Recommendation: **Option 1**. The clone is short (`git clone
--depth 1`) and happens anyway; reordering it before Step 1
means the operator sees clone failures *before* answering any
prompts, which is friendlier. The cost is that a typo'd
`--distro` URL fails before the tier prompt — that's the right
order to discover it.

If the manifest fetch fails, init falls through to the D2
fallback **only if** `--distro` came from `$ARTIFACTS_DISTRO_URL`
(silently usable fallback for environment-default convenience).
A CLI-supplied `--distro` failure is fatal — the operator
asked for it explicitly.

> **Decision (sub-q of Q6 / D2 boundary):** Env-supplied distro
> URL failure → fall back to D2 with a stderr warning.
> CLI-supplied `--distro` failure → exit 2.

### 8.3 `--book NAME[:items]` parser

```python
@dataclass(frozen=True)
class BookSpec:
    name: str
    items: list[str] | None  # None = pull-all

def _parse_book_flags(args, distro_url: str | None) -> list[BookSpec] | None:
    raw_flags: list[str] = args.book or []
    if not raw_flags:
        return None  # interactive or -y default
    if distro_url is None:
        _err("--book requires --distro or $ARTIFACTS_DISTRO_URL")
        return None
    specs: list[BookSpec] = []
    for token in raw_flags:
        name, sep, items_raw = token.partition(":")
        items = (
            [i.strip() for i in items_raw.split(",") if i.strip()]
            if sep else None
        )
        if not name:
            _err(f"invalid --book value: {token!r}")
            return None
        specs.append(BookSpec(name=name, items=items))
    return specs
```

Argparse registration uses `action="append"` so `--book` is
naturally repeatable.

### 8.4 Bundled-skill walker

```python
def _install_bundled_skill(target: Path, *, force: bool, dry_run: bool) -> None:
    from importlib.resources import files

    root = files("artifacts_os.ai.claude.skills").joinpath("artifacts-os")
    dest_root = target / ".claude" / "skills" / "artifacts-os"

    for entry in _walk_resource(root):
        rel = entry.relative_to(root)
        if _excluded_from_bundle(rel):
            continue
        _do_write(dest_root / rel, entry.read_text(encoding="utf-8"))


def _excluded_from_bundle(rel_path: Path) -> bool:
    parts = rel_path.parts
    if parts and parts[0] == "__pycache__":
        return True
    if any(p.startswith(".") for p in parts):
        return True
    name = rel_path.name
    return (
        name == "__init__.py"
        or name.endswith(".pyc")
        or name.endswith(".pyo")
    )
```

`_walk_resource` recurses an `importlib.resources.abc.Traversable`
yielding leaf files. Standard implementation: iterate
`root.iterdir()`, recurse on directories, yield files.

---

## 9. Verification (mirrors t0166's checklist with concrete checks)

- [ ] **D1 flow shape:** `art init --distro <url>` walks one
      settings prompt then one prompt per declared book, in
      declaration order. No standalone "kinds" or "agents"
      prompt.
- [ ] **D2 no-distro fallback:** `art init` (no `--distro`, no
      env var) writes `artifacts.yaml` and
      `.claude/skills/artifacts-os/SKILL.md` and exits zero.
      No kinds, no agents.
- [ ] **D3 per-book prompt:** Each book prompt is a single
      multi-select with `*` (all items) as the default.
- [ ] **D4 settings tier bundled:** Step 1 reads from
      `src/artifacts_os/templates/settings/{tier}.yaml`.
- [ ] **D5 `--force`:** Re-init on an initialised vault with
      `--force` re-prompts every step and every book; matching
      files are overwritten.
- [ ] **D6 `-y` fallback:** `art init -y` (no distro) produces
      identical files to the interactive default path with no
      prompts.
- [ ] **Q1.a flags deleted:** `art init --kinds task` exits 2
      with `unrecognized arguments`.
- [ ] **Q1.b `--book`:** Repeatable; `NAME` selects whole book;
      `NAME:item,item` filters; unknown book/item exits 2 before
      cloning further.
- [ ] **Q2 bundled-templates deletion:** `src/artifacts_os/templates/kinds/`
      and `src/artifacts_os/templates/agents/` do not exist in
      the source tree or the built wheel.
- [ ] **Q3 wheel packaging:** Installing the wheel into a fresh
      virtualenv and running `art init` writes a non-empty
      `.claude/skills/artifacts-os/SKILL.md`.
- [ ] **Q4 distro-skill skip:** `art init --distro <url>` does
      not write `.claude/skills/artifacts-os/SKILL.md` from the
      bundle; whatever lands there comes from the distro's
      `skills` book.
- [ ] **Q5.a book order:** Reordering books in `artbook.yaml`
      reorders the prompts.
- [ ] **Q6 error handling:** Manifest error / clone failure exits 2
      pre-pull; per-book failure logs and continues with
      remaining books; init exits 1 at end.
- [ ] **Q7 docs updated:** `docs/init-flow.md`, `docs/artbook.md`
      § Consumer Quickstart, and `src/artifacts_os/cli/README.md`
      § init reflect the new flow with at least one transcript
      per branch (D1, D2, fully-flagged).

---

## 10. Implementation Sub-Task Breakdown

The project-manager creates these once this spec is approved.
Sub-tasks are decoupled and parallelisable except where noted.

| ID | Title                                          | Touches                                                                       | Depends on |
|----|------------------------------------------------|-------------------------------------------------------------------------------|------------|
| I1 | Rewrite `init` command for books-driven flow   | `src/artifacts_os/cli/commands/init.py`                                       | I3         |
| I2 | Delete bundled `kinds/` and `agents/` templates | `src/artifacts_os/templates/{kinds,agents}/`                                  | I1         |
| I3 | Repackage bundled skill in wheel manifest      | `pyproject.toml`                                                              | —          |
| I4 | Update consumer docs                           | `docs/init-flow.md`, `docs/artbook.md`, `src/artifacts_os/cli/README.md`      | I1         |
| I5 | Rewrite init test suite                        | `tests/cli/test_init.py`, fixtures                                            | I1         |
| I6 | Release notes / changelog entry                | `CHANGELOG.md` (or release process notes)                                     | I1, I4     |

Estimated complexity (rough):

- **I1**: Medium. Refactor `run()` flow control, add
  `_parse_book_flags`, `_install_bundled_skill`,
  `_walk_resource`. Carry over `_do_write`,
  `_prompt_multi_step`, `_prompt_single_step` unchanged.
- **I2**: Trivial. `git rm -r` the two directories.
- **I3**: Trivial. One-line addition to `pyproject.toml`,
  one-line deletion of obsolete globs. Smoke-test by building
  the wheel and inspecting the manifest.
- **I4**: Medium. Three doc files; copy Transcripts A–C
  verbatim into `docs/init-flow.md`.
- **I5**: Large. Existing `tests/cli/test_init.py` has 77+
  tests; the kinds/agents half is deleted, the distro half is
  rewritten for `--book`, and new tests for the D2 skill
  install are added.
- **I6**: Trivial. Q7 migration table.

---

## 11. Risks

- **Bundled-skill wheel packaging regressed.** A wheel built
  without the SKILL.md leads to `art init` writing an empty
  skill dir. Mitigation: I5 adds a test that imports the
  resource and asserts non-empty content; CI runs against the
  built wheel, not the source tree.
- **`importlib.resources.files` on hyphenated subdirs.**
  Empirically supported via `joinpath`, but worth a defensive
  test in I5 (`test_bundled_skill_root_resolves`).
- **Operators relying on Steps 2/3 today.** This is a breaking
  change. Mitigation: Q7 release notes, prominent CHANGELOG
  entry, and the post-release first-bug-report should
  surface fast.
- **Distro authors who omitted a `kinds` book** assuming the
  bundled defaults would fill in. After this spec lands, those
  consumers get a vault with no `kinds/` at all. Mitigation:
  the migration note in §6.4 / Q7 calls this out explicitly,
  and the artifacts-os repo itself continues to ship a `kinds`
  book that any distro can reference (or copy from).
