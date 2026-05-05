---
kind: spec
id: s0020
name: release-changelog-skill-contract
status: review
task: "[[t0105-spec-generic-release-skill-contract]]"
created: 2026-05-05
agent: architect
---

# Generic, Task-Aware Release-Changelog Skill — Contract

Locks the contract for a single `release-changelog` skill that
replaces both today's project-specific copies (`artifacts-release` in
artifacts-os, `release-changelog` in OpenStation) by reading project
shape from a structured section of `CLAUDE.md` and enriching each
changelog entry with the originating task's intent
(`name`, `type`, `parent`, `## Goal`, `## Findings`).

**Scope: design only.** Implementation is filed as a follow-up
sub-task of [[t0104-generic-release-skill-uses-tasks]] once this
spec reaches `approved`.

## 1. Background and Cross-References

- **Parent task** — [[t0104-generic-release-skill-uses-tasks]] —
  user story, scope-of-intent, and out-of-scope markers. This spec
  is its first decomposition step.
- **Producing task** — [[t0105-spec-generic-release-skill-contract]]
  — verification checklist this spec must satisfy.
- **Direct ancestor (artifacts-os)** —
  `src/artifacts_os/ai/claude/skills/artifacts-release/SKILL.md` —
  shipped by [[t0100-set-up-release-flow-and]]. Workflow shape
  carries forward; the hard-coded module → category map does not.
- **Direct ancestor (OpenStation)** —
  `~/workspace/os/open-station/.openstation/skills/release-changelog/SKILL.md`
  — same workflow shape, different domain map. Engaged for parity
  only; OpenStation adoption is a downstream task.
- **Wheel-borne install plumbing** —
  [[t0096-ship-artifacts-os-skill-md]]. The `install.py` walker
  installs every `src/artifacts_os/ai/claude/skills/<dir>/SKILL.md`
  the package ships. This spec assumes that mechanism and adds one
  new directory to it.
- **Existing CLAUDE.md** — `CLAUDE.md` at repo root. This spec
  proposes an additional `## Release` section; existing sections
  remain untouched.
- **OpenStation task contract** — `artifacts/tasks/<id>-<slug>.md`
  files with frontmatter (`id`, `name`, `type`, `parent`, …) and
  body sections (`## Goal`, `## Findings`). This spec consumes the
  contract; it does not extend it.

## 2. Goals and Non-Goals

### 2.1 Goals

1. **One generic skill** — `release-changelog` — project-agnostic
   in shape, ships from the artifacts-os wheel, runs in any vault
   that has `artifacts/artifacts.yaml`.
2. **`CLAUDE.md` as the project contract** — domain category list,
   path → category map, release checklist, and exclusions all
   declared in a structured `## Release` section the skill parses.
3. **Task enrichment by default** — for every commit that carries a
   `(tNNNN)` trailer, the skill reads the corresponding task file
   and uses `name` + `## Findings` (or `## Goal`) to compose the
   bullet, instead of the bare commit subject.
4. **Layer isolation** — the skill is a read-only consumer of
   `artifacts/tasks/`; never writes, never edits frontmatter,
   never appends to the JSONL log.
5. **Graceful fallbacks** — every fallback path (missing trailer,
   missing task file, empty task body) emits a draft and surfaces
   the gap in the present-for-review step. The skill never fails.
6. **Clean migration** — `artifacts-release` is removed from the
   package and replaced by `release-changelog` in a single
   release; `artifacts ai install` (and `artifacts init`) prune
   the orphan vault directory automatically.
7. **Backwards-compatible CHANGELOG** — the entry format
   (`## v<VERSION>` + H3 categories + bold-em-dash bullets) is
   preserved verbatim. The Step 0 idempotency check works against
   today's `CHANGELOG.md` files.

### 2.2 Non-Goals

- **OpenStation adoption.** OpenStation will adopt this skill as a
  downstream task once artifacts-os ships it. This spec only
  documents the contract OpenStation will consume.
- **Changes to the release workflow** (`.github/workflows/release.yml`
  and PyPI Trusted Publisher config). Out of scope.
- **Changes to commit conventions.** The `(tNNNN)` trailer is
  already de-facto standard; this spec does not introduce it.
- **Multi-file skill packages.** The skill body fits in one
  `SKILL.md`.
- **New Python imports in artifacts-os.** The skill is agent-layer
  instructions; the implementation sub-task introduces no new
  module dependencies.
- **AI module changes.** `install.py` may need a one-line addition
  to permit the new skill namespace; that is a small mechanical
  change owned by the implementation sub-task, not a design
  question for this spec.
- **A separate config file** (`artifacts/release.yaml`,
  `docs/release.md`). Rejected in D1.

## 3. Locked Decisions Summary

| ID  | Decision |
|-----|----------|
| D1  | Project shape lives **inline** in `CLAUDE.md` under a structured `## Release` section. No separate config file. |
| D2  | The skill parses `## Release` by H2 heading match plus four well-known H3 subsections: `### Domain Categories`, `### File Path Mapping`, `### Checklist`, `### Exclusions` (optional). |
| D3  | Task-trailer extraction uses the regex `\(\s*t(\d{4,})(?:\s*,\s*t(\d{4,}))*\s*\)` applied to the commit subject; all captured IDs are retained. |
| D4  | Task files are located by walking up from CWD to the `artifacts/artifacts.yaml` vault marker, then globbing `artifacts/tasks/t<id>-*.md`. The skill does **not** import `artifacts_os` Python modules. |
| D5  | Task-body field precedence for the bullet description: `## Findings` first; `## Goal` if `## Findings` absent; commit subject if both absent. The bullet headline always uses the task `name` (frontmatter), regardless of body fallback. |
| D6  | Multi-trailer commit (`(t0099, t0100)`): title the bullet with the first ID's task name; co-referenced IDs render inline as `(also t0100)`. |
| D7  | Sub-task collapse: if a parent and any of its sub-tasks both have commits in the release range, the sub-tasks collapse into sub-bullets under the parent's bullet. If the parent has no commits in range, sub-tasks render flat — no synthetic parent line. |
| D8  | Fallbacks never fail the skill. Every fallback (missing trailer, missing task file, empty task body, malformed `## Release` section) is surfaced in the Step 6 present-for-review summary. The single exception (D14) is a missing/malformed `## Release` section, which halts before Step 3 with a clear error. |
| D9  | Skill canonical home: artifacts-os package, source at `src/artifacts_os/ai/claude/skills/release-changelog/SKILL.md`, installed to `<vault>/.claude/skills/release-changelog/SKILL.md` via the t0096 wheel-borne `install.py` walker. |
| D10 | Migration: clean swap. The `artifacts-release` skill directory is removed from the package; `artifacts ai install` (and `artifacts init`) detects the orphan vault directory and prunes it on the next run. No alias, no deprecation window — the old skill has not had time to develop external users. |
| D11 | OpenStation adoption is a downstream task. This spec defines the contract OpenStation will consume; OpenStation's existing `.openstation/skills/release-changelog/SKILL.md` is untouched until that downstream task lands. |
| D12 | The CHANGELOG entry format (H2 version heading, summary paragraph, H3 categories, `- **bold name** — description.` bullets) is preserved verbatim from the artifacts-release skill. The Step 0 idempotency check (`grep -q '^## v<VERSION>' CHANGELOG.md`) carries forward. |
| D13 | Path → category mapping uses **longest-prefix match wins**. A `fix:` commit-prefix override routes to the `Fix` category regardless of path; `chore:` is excluded by default unless an exclusion entry whitelists it. |
| D14 | A missing or malformed `## Release` section in `CLAUDE.md` is a **hard error**: the skill halts after Step 1 with a message naming the missing/malformed subsection. Rationale: without project shape there is nothing to draft; failing fast is better than emitting an unstructured fallback. |

### D1 — `CLAUDE.md` as the project-shape carrier

**Choice:** inline `## Release` section in `CLAUDE.md`. **Rejected:**
pointer from `CLAUDE.md` to a dedicated `artifacts/release.yaml` or
`docs/release.md`.

Rationale:

- Every artifacts-os-managed project already has `CLAUDE.md` —
  inline keeps the contract discoverable to the agent that runs
  the skill without adding a new file convention.
- The pointer model adds a layer of indirection without buying
  expressive power; YAML and markdown both already represent the
  three needed shapes (list, table, ordered list).
- One file is easier to keep in sync. Reviewers updating module
  layout or release process see the categories and checklist in
  the same place they edit module references in
  `## Project Structure`.
- A separate file would force the skill to grow a path-resolution
  step (relative to repo root? relative to vault? configurable?);
  inline avoids it.

The cost: `CLAUDE.md` grows ~40 lines. Acceptable.

### D2 — `## Release` subsection grammar

The skill parses by H2 heading match (`## Release` — case- and
whitespace-sensitive) and four well-known H3 subsections:

- `### Domain Categories` — bullet list. Each line is
  `- **<Name>** — <one-line note>`. Order is the rendering order
  in the final changelog (most-impactful first). The trailing note
  is documentation only; the skill ignores it.
- `### File Path Mapping` — a markdown table with two columns,
  `Path prefix` and `Category`. Path prefixes are matched against
  changed-file paths from `git diff-tree`. **Longest-prefix match
  wins** (D13). A category referenced here MUST exist in
  `### Domain Categories`; otherwise the skill flags the mismatch
  in the present-for-review step (not a hard error — the line
  routes to `Architecture` as a fallback bucket).
- `### Checklist` — an ordered (numbered) list. Each line is one
  imperative step. Step 8 of the skill renders these literally.
  Variables are spelled `<VERSION>` and `<TAG>`; the skill
  substitutes them at draft time. (No other variables are
  recognised.)
- `### Exclusions` *(optional)* — bullet list. Two forms:
  `- path: <glob>` and `- subject: <regex>`. Commits matching any
  exclusion are dropped before categorisation.

Section order inside `## Release` is not enforced; the skill finds
each H3 by name. Anything else inside `## Release` (notes, prose,
extra subsections) is ignored.

Rationale: H2/H3 + tables + bullet/numbered lists is the same
grammar `## Project Structure` and `## Common Commands` already
use. Authors do not learn a new mini-language; reviewers can
diff-read the section like any other doc.

### D3 — Task-trailer regex

```
\(\s*t(\d{4,})(?:\s*,\s*t(\d{4,}))*\s*\)
```

Anchored by parentheses, applied to the commit subject (line 1).
Captures every ID in the parens. Padding around commas and inside
parens is tolerated. The regex requires 4+ digits to match the
project's NNNN convention and avoid false positives on common
parenthesised tokens like `(t1)` test labels.

The skill applies the regex once per commit subject; trailers
appearing in the body are ignored (commit subjects are the
canonical place per project convention).

### D4 — Task-file resolution

```
1. Walk up from CWD until a directory contains `artifacts/artifacts.yaml`.
   That directory is <vault-root>.
2. For each captured ID (e.g. `t0099`), glob:
   `<vault-root>/artifacts/tasks/t0099-*.md`
3. Exactly one match → load. Zero matches → flag missing-task fallback.
   Two or more → flag ambiguous-task fallback (use the first; warn).
```

The skill **does not** invoke `python -c "import artifacts_os"`.
Rationale: the skill is agent-layer instructions, not Python code;
adding a Python entry point couples skill execution to whether
the host has artifacts-os installed and on `PATH`. Globbing keeps
the skill standalone and matches OpenStation's path conventions
(its tasks live at `artifacts/tasks/<id>-*.md` too once it adopts
artifacts-os).

### D5 — Body-field precedence for description

```
description = task.findings_section()      # if present, non-empty
           or task.goal_section()          # else, if present, non-empty
           or commit.subject_after_prefix  # else, fallback (flagged)
```

`## Findings` is preferred because it represents the task's
**outcome** — what changed, what landed — which is exactly what a
changelog reader wants. `## Goal` is preferred over a bare commit
subject because it captures intent at task-creation time; commit
subjects often elide context.

When `## Findings` exists, the skill takes its **first paragraph**
(up to the next blank line). Multi-paragraph findings are summarised
to one sentence by the agent during drafting; the spec does not
prescribe the exact summarisation rule beyond "first paragraph as
input".

The bullet **headline** is always the task `name` (slug rendered
as Title Case With Spaces) — it is taken from frontmatter, never
from body fallbacks. Frontmatter is always present (else the task
file would not load).

### D6 — Multi-trailer commits

A commit subject like `feat: refactor X (t0099, t0100)` produces
one bullet:

```
- **<Title for t0099>** — <description from t0099 findings/goal>. (also t0100)
```

The first ID drives the headline and description; co-referenced
IDs append `(also tNNNN)` markers in the bullet text. Rationale:
choosing the first ID is unambiguous and matches existing commit
conventions (the primary task is conventionally listed first).

If t0100 also has commits in range that do **not** mention t0099,
those commits render their own bullets normally.

### D7 — Sub-task / parent collapse

The skill builds a parent → sub-tasks index from the `parent`
frontmatter field of every task referenced in the range. Then:

- If a parent task `tP` has commits in the range AND a sub-task
  `tC` (`tC.parent == tP`) also has commits in the range: render
  one bullet for `tP`, with `tC`'s bullet collapsed under it as a
  sub-bullet (two-space indent).
- If `tP` has no commits in range but `tC` does: render `tC` as a
  flat bullet, no synthetic parent line. Rationale: without a
  parent commit there is nothing to anchor the sub-bullet to;
  inventing a parent line would invent content not in the release.
- Sub-task transitivity (grandchildren, great-grandchildren) is
  flattened to one level: the deepest existing parent in the
  range owns the bullet, and every descendant collapses under it.
  Two-level nesting is the maximum.

This rule lets the changelog reflect work decomposition without
duplicating bullets when a feature lands across an architect spec
+ a developer implementation that share a parent.

### D8 — Fallback flagging

Each fallback emits a flag line in the Step 6 present-for-review
summary, grouped under a "Fallbacks" sub-heading. Format:

```
Fallbacks:
- <commit-hash> "<subject>": no (tNNNN) trailer — used commit subject.
- <commit-hash> "<subject>": task t0123 referenced but file missing — used commit subject.
- <commit-hash> "<subject>": task t0124 has no `## Findings` or `## Goal` — used commit subject.
```

The skill always emits a draft. The reviewer decides whether each
flagged commit deserves a manual edit before approving Step 7.

### D9 — Skill location

Source path in artifacts-os repo:
`src/artifacts_os/ai/claude/skills/release-changelog/SKILL.md`

Install path in any vault after `artifacts ai install`:
`<vault>/.claude/skills/release-changelog/SKILL.md`

Implementation note (informational, not part of the contract): the
existing `_SKILL_NS_PREFIX = "artifacts-"` filter in `install.py`
must be widened to permit a non-`artifacts-`-prefixed skill
directory shipped by the package. The mechanism is unchanged; only
the namespace allowlist grows. The implementation sub-task owns
the change.

### D10 — Migration: clean swap

In one release of artifacts-os:

1. Add `src/artifacts_os/ai/claude/skills/release-changelog/SKILL.md`.
2. Remove `src/artifacts_os/ai/claude/skills/artifacts-release/`.
3. Extend `install.py` so its `uninstall()` and `list_installed()`
   handle the new namespace, and so a stale
   `<vault>/.claude/skills/artifacts-release/SKILL.md` symlink
   gets pruned on the next `artifacts ai install` run (it will be
   detected as an owned symlink whose source is gone).

No alias, no deprecation window. Rationale: `artifacts-release`
was added in [[t0100-set-up-release-flow-and]] and has not been
exercised externally; the cost of the alias machinery exceeds the
benefit of a deprecation period that no user will observe.

### D11 — OpenStation adoption (downstream)

OpenStation's `.openstation/skills/release-changelog/SKILL.md`
is **not** modified by the artifacts-os migration. When
OpenStation later adopts artifacts-os as a runtime dependency and
runs `artifacts init` against its vault, the artifacts-os skill
installs at `<openstation-vault>/.claude/skills/release-changelog/SKILL.md`.
The OpenStation team chooses, in a separate task, whether to:

- delete the vendored copy and rely on the shipped skill, or
- keep both, accepting that the shipped skill will load first
  because `.claude/skills/` outranks `.openstation/skills/` in
  OpenStation's harness (the resolution rule is OpenStation's, not
  this spec's).

This spec records the contract; the OpenStation cutover is filed
as a separate downstream task in the OpenStation repo per the
parent task's § "Out of scope".

### D12 — CHANGELOG.md backwards compatibility

The skill emits the same shape today's `artifacts-release` and
OpenStation's `release-changelog` produce:

```
## v<VERSION>

<Summary paragraph.>

### <Category>

- **<Headline>** — <description>.
```

Step 0's idempotency check (`grep -q '^## v<VERSION>' CHANGELOG.md`)
works against historical entries. The new skill never reformats
existing entries; it only inserts a new entry immediately after the
`# Changelog` heading.

### D13 — Path → category routing rules

Routing precedence (first match wins; later rules act as overrides):

1. **Exclusions** (D2 `### Exclusions`). Excluded commits are
   dropped before categorisation.
2. **`fix:` prefix override.** Any commit whose conventional
   prefix is `fix:` routes to `Fix`, regardless of path.
3. **Longest-prefix match** against `### File Path Mapping`. The
   commit's most-changed file path (by line count from
   `git diff-tree --numstat`) supplies the path; the longest
   matching prefix wins. Ties are broken alphabetically (stable).
4. **Architecture fallback.** A commit whose path matches no
   prefix routes to `Architecture` (must always be a category in
   `### Domain Categories`). The mismatch is flagged in Step 6.

`refactor:` and `test:` commits follow the path-mapping rules;
the agent decides at draft time whether to keep or omit each per
the existing skill rules (no behaviour change from
`artifacts-release`).

### D14 — Hard error on missing/malformed `## Release`

If `CLAUDE.md` is absent, missing `## Release`, missing any
required H3 (`### Domain Categories`, `### File Path Mapping`,
`### Checklist`), or has malformed table rows in
`### File Path Mapping`, the skill halts after Step 1 with:

```
release-changelog: cannot draft — CLAUDE.md is missing the `## Release` section
(or it is malformed). Required H3s: Domain Categories, File Path Mapping, Checklist.
See `<artifacts-os-docs-link>` for the contract.
```

Rationale: without project shape there is no defensible default —
hard-coding categories per project is exactly the duplication
this skill is removing. Better to fail loudly with a fix-up
pointer than to draft from a guess.

## 4. Skill Engagement Table

How the workflow steps of the two existing skills carry forward.
`LOCK` = preserved verbatim. `LOCK-WITH-EDIT` = preserved in
shape, edited per the cited decision. `REJECT` = dropped or
replaced.

### 4.1 `artifacts-release` (artifacts-os)

| Step | Verdict | Notes |
|------|---------|-------|
| When to Use, Prerequisites | LOCK | Verbatim. |
| Step 0 — Idempotency Check | LOCK | Same `grep -q '^## v<VERSION>'` regex (D12). |
| Step 1 — Determine Release Range | LOCK | Same `git tag --sort=-v:refname \| head -1` flow. |
| Step 2 — Collect Commits | LOCK-WITH-EDIT | Also extract `(tNNNN)` trailers per commit (D3). |
| Step 3a — Parse conventional prefix | LOCK | Same prefix table. |
| Step 3b — Hard-coded module → category map | REJECT | Replaced by the parser of `CLAUDE.md` `## Release` (D1, D2, D13). |
| Step 4 — Draft format (`## v…`, H3 categories, bold-em-dash bullets) | LOCK | Bullets enriched per D5 / D6 / D7. |
| Step 5 — Version Recommendation | LOCK | Same major/minor/patch table. |
| Step 6 — Present for Review | LOCK-WITH-EDIT | Adds the Fallbacks summary block (D8). |
| Step 7 — Write to CHANGELOG.md | LOCK | Same insertion rule. |
| Step 8 — Release Checklist | LOCK-WITH-EDIT | Steps now read from `### Checklist` in `CLAUDE.md` (D2). |
| "What This Skill Does NOT Do" | LOCK-WITH-EDIT | Adds: never mutates `artifacts/tasks/`, never appends to the JSONL log. |

### 4.2 `release-changelog` (OpenStation)

| Step | Verdict | Notes |
|------|---------|-------|
| Step 0 / 1 / 2 / 3a / 4 / 5 / 6 / 7 | LOCK | Same shape as artifacts-release; preserved. |
| Step 3b — OpenStation-specific path map (`bin/openstation`, `agents/`, …) | REJECT | Replaced by `CLAUDE.md` `## Release` (D1). |
| Step 8 — OpenStation-specific checklist (`OPENSTATION_VERSION` in install.sh) | REJECT | Replaced by the project-declared checklist (D2). |
| File location at `.openstation/skills/release-changelog/SKILL.md` | REJECT | Skill now ships from artifacts-os and installs to `.claude/skills/release-changelog/` (D9, D11). |

## 5. Surfaces

### 5.1 Skill file

- **Source:** `src/artifacts_os/ai/claude/skills/release-changelog/SKILL.md`
- **Frontmatter:**
  ```yaml
  ---
  name: release-changelog
  description: Generate a task-aware changelog entry for a new release from conventional commits, the producing tasks, and the project's `## Release` section in CLAUDE.md.
  user-invocable: false
  ---
  ```
- **Body:** the eight-step workflow with the per-step
  modifications recorded in § 4.1.
- **Install target:** `<vault>/.claude/skills/release-changelog/SKILL.md`
  (managed by `src/artifacts_os/ai/install.py`).

### 5.2 `CLAUDE.md` `## Release` contract

The artifacts-os repo's `CLAUDE.md` gains the section below
verbatim. Every other artifacts-os-managed project authors its
own copy following the same grammar.

```markdown
## Release

The `release-changelog` skill reads this section to draft a new
release entry. Edit the tables and checklist when modules or
release flow change.

### Domain Categories

Listed most-impactful first. The skill emits an H3 subsection per
category that has entries in the release range. Empty categories
are omitted.

- **Architecture** — cross-cutting structural changes
- **Core** — `src/artifacts_os/core/`
- **Views** — `src/artifacts_os/views/`
- **CLI** — `src/artifacts_os/cli/`
- **TUI** — `src/artifacts_os/tui/`
- **AI** — `src/artifacts_os/ai/`
- **Log** — `src/artifacts_os/log/`
- **Install** — packaging and installer changes
- **Fix** — any commit with a `fix:` conventional prefix

### File Path Mapping

Longest-prefix match wins. A commit's category is determined by
its most-changed file's prefix; the `fix:` commit prefix overrides
the path mapping and routes to `Fix`.

| Path prefix | Category |
|-------------|----------|
| `src/artifacts_os/core/` | Core |
| `src/artifacts_os/views/` | Views |
| `src/artifacts_os/cli/` | CLI |
| `src/artifacts_os/tui/` | TUI |
| `src/artifacts_os/ai/` | AI |
| `src/artifacts_os/log/` | Log |
| `pyproject.toml` | Install |
| `setup.py` | Install |
| `install.sh` | Install |

### Checklist

The skill renders Step 8 from this list. `<VERSION>` is
substituted at draft time.

1. Update `version` in `pyproject.toml` to `<VERSION>`.
2. Write the CHANGELOG entry (the skill does this in Step 7).
3. Commit with subject `chore: release v<VERSION>`.
4. Push to `main` — CI handles the tag, GitHub Release, and
   PyPI publish.

### Exclusions

- subject: `^Merge `
- path: `.editorconfig`
- path: `.github/dependabot.yml`
```

### 5.3 `install.py` namespace allowlist (informational)

The implementation sub-task widens `_SKILL_NS_PREFIX` (or the
equivalent allowlist) to permit `release-changelog/` as a shipped
skill directory in addition to `artifacts-os/`. This is mechanical
and not part of the contract; it is recorded here so the
implementing developer does not re-derive the question.

## 6. Test Plan

Grouped by the property each test verifies. The implementation
sub-task pulls this section verbatim into its work plan.

### 6.1 Layer isolation

- The skill performs zero writes to `artifacts/tasks/` —
  pre/post directory hash is identical after a full skill run on
  a vault with task references.
- The skill performs zero writes to `artifacts/log/*.jsonl` —
  same hash check.
- The skill performs zero writes outside `CHANGELOG.md`,
  `pyproject.toml`, and the working-tree commits it produces in
  Step 8.

### 6.2 End-to-end enrichment

- Drafting the next release on artifacts-os `main` (with the
  skill installed and `## Release` populated per § 5.2)
  produces an entry that names the producing task by `name` for
  every commit carrying a `(tNNNN)` trailer. The bullet headline
  is the task name, not the commit subject.
- For a task with `## Findings`, the bullet description is
  drawn from the Findings section's first paragraph. For a task
  with only `## Goal`, it is drawn from the Goal section.

### 6.3 Fallbacks (must not fail)

- A commit with no `(tNNNN)` trailer renders a bullet whose
  headline is derived from the commit subject. The commit appears
  in the Step 6 Fallbacks summary.
- A commit with a `(t9999)` trailer where the task file does not
  exist renders a fallback bullet from the commit subject and
  surfaces a `task t9999 referenced but file missing` line in the
  Fallbacks summary.
- A commit referencing a task whose body has neither `## Findings`
  nor `## Goal` renders a fallback bullet from the commit subject
  and surfaces an `empty body` line in the Fallbacks summary.

### 6.4 Hard error on `CLAUDE.md` malformed

- A `CLAUDE.md` with no `## Release` section halts the skill
  after Step 1 with the D14 error message. No partial draft is
  written.
- A `## Release` section missing `### File Path Mapping` halts
  with a message naming the missing subsection.
- A `### File Path Mapping` table with a category that does not
  appear in `### Domain Categories` does **not** halt — the
  commit routes to `Architecture` and the mismatch is flagged in
  Step 6 (per D13's Architecture fallback rule).

### 6.5 Multi-trailer and parent/sub-task collapse

- A commit with `(t0099, t0100)` produces one bullet headlined by
  t0099's name with `(also t0100)` inline.
- A range containing one commit referencing parent t0104 and one
  referencing sub-task t0105 (where t0105.parent == t0104)
  produces one bullet for t0104 with t0105 collapsed underneath
  as a sub-bullet.
- A range containing only sub-task t0105 (no parent commit)
  renders t0105 as a flat bullet — no synthetic t0104 line.

### 6.6 Migration

- After `pip install --upgrade artifacts-os && artifacts ai install`
  in a vault that previously had `<vault>/.claude/skills/artifacts-release/SKILL.md`,
  the orphan symlink is pruned and `<vault>/.claude/skills/release-changelog/SKILL.md`
  exists.
- An invocation of the (now-removed) `artifacts-release` skill
  surface fails with a clear "skill not found" error from the
  harness — no silent execution of stale content.

### 6.7 Idempotency and CHANGELOG compatibility

- Running the skill against a `CHANGELOG.md` that already has the
  target `## v<VERSION>` heading triggers the Step 0 prompt
  (regenerate-or-skip), per current `artifacts-release` behaviour.
- The new skill's emitted entry parses through the same
  `## v<VERSION>` heading regex on subsequent runs (round-trip).

## 7. Cross-References

- [[t0104-generic-release-skill-uses-tasks]] — parent task.
- [[t0105-spec-generic-release-skill-contract]] — producing task.
- [[t0096-ship-artifacts-os-skill-md]] — wheel-borne install
  plumbing this spec rides.
- [[t0100-set-up-release-flow-and]] — shipped the
  `artifacts-release` skill that this spec replaces.
- `src/artifacts_os/ai/claude/skills/artifacts-release/SKILL.md` —
  direct ancestor; engaged in § 4.1.
- `~/workspace/os/open-station/.openstation/skills/release-changelog/SKILL.md`
  — sibling reference; engaged in § 4.2.
- `src/artifacts_os/ai/install.py` — install walker that grows a
  namespace entry per § 5.3.
- `CLAUDE.md` — the file that gains the `## Release` section in
  § 5.2.

## 8. Implementation Notes

Pre-populates the follow-up implementation sub-task's scope:

1. Author `src/artifacts_os/ai/claude/skills/release-changelog/SKILL.md`
   per § 4.1, § 5.1, and the test plan in § 6.
2. Add the `## Release` section to artifacts-os `CLAUDE.md`
   verbatim per § 5.2.
3. Remove `src/artifacts_os/ai/claude/skills/artifacts-release/`.
4. Widen the `install.py` skill namespace allowlist to permit
   `release-changelog/` (§ 5.3). Keep the existing conflict
   policy (same-content skip, owned-symlink replace, …)
   unchanged.
5. Add tests per § 6 — preference for `tmp_path` + `make_vault`
   fixtures; no mocking of git or filesystem.
6. Update `docs/` if any module-level reference to
   `artifacts-release` exists; verify no stale wikilinks remain.
