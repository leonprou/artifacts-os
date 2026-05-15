---
assignee: architect
created: 2026-05-15
id: t0151
kind: task
name: spec-the-artbook-model
owner: user
parent: '[[t0150-artbook-distribution-model]]'
status: done
type: spec
started: 2026-05-15
artifacts:
  - "[[openstation/specs/s0029-artbook-mvp-distribution-model]]"
  - "[[openstation/notes/n0013-artbook-book-command-user-manual]]"
completed: 2026-05-15
---

# Spec The Artbook Model

## Goal

Produce the design spec for the artbook MVP — minimal but implementable.

## Scope

1. **`artbook.toml` schema** — fields per book, required vs. optional, one example file.
2. **`artbook` module layout** — Python package under `src/artifacts_os/artbook/`; public API for reading manifests, fetching content, writing files.
3. **CLI surface** — exact behaviour, output format, exit codes for `artifacts book list / show / pull`.
4. **Pull mechanics** — pick one fetch strategy and document why; always fetch from `main`; no caching.
5. **Local placement** — book-type → harness path mapping for the agents book; what happens when files already exist (lean: overwrite without prompt).
6. **Worked end-to-end example** — fresh consumer configures a distro URL, runs `artifacts book pull agents`, ends up with working agents.

## Inputs

- Parent feature task [[t0150-artbook-distribution-model]] — user story, MVP cut, out-of-scope.
- [[n0011-distributable-harness-layers-inventory]] and [[n0012-distributable-harness-layers-to-merge]] — content inventory.
- [[s0028-distributable-harness-sync-model]] — earlier spec; reference for context, but MVP spec is a fresh thinner document, not a revision.

## Out of scope for this spec

`update` / `diff` / `remove`, multi-distro, override layer, private-distro auth, lock files, version pinning, caching, offline support, dogfood migration, third-party book authoring. Each gets its own spec when its time comes.

## Deliverable

A spec under `artifacts/specs/` concrete enough to implement the MVP from. Includes the worked example.

## Verification

- [x] Spec written and committed under `artifacts/specs/`
- [x] All six scope items addressed
- [x] Worked example: fresh consumer pulls the agents book and ends up with working agents
- [x] Out-of-scope items explicitly listed in the spec
- [x] Architect promotes spec to `review` for owner approval

## Verification Report

*Verified: 2026-05-15*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec written and committed under `artifacts/specs/` | PASS | `artifacts/specs/s0029-artbook-mvp-distribution-model.md` exists (1329 lines, 56 KB). Frontmatter `kind: spec`, `task: [[t0151-spec-the-artbook-model]]`, `agent: architect`. File is currently untracked in git — staging/commit is the owner's next step but the artifact itself is written in the correct location. |
| 2 | All six scope items addressed | PASS | Section headings explicitly tag each scope item: §3 Manifest Schema (Scope Item 1), §4 `artbook` Module Layout (Scope Item 2), §5 CLI Surface (Scope Item 3), §6 Pull Mechanics (Scope Item 4), §7 Local Placement (Scope Item 5), §8 Worked End-to-End Example (Scope Item 6). §11 Verification Mapping cross-references each. |
| 3 | Worked example: fresh consumer pulls the agents book and ends up with working agents | PASS | §8 walks through 8 sub-steps (8.1 setup → 8.8 re-run safety) for a fresh `my-project/` repo. Result tree (§8.6) shows 9 agent files at `.claude/agents/{architect,author,developer,devrel,product-manager,project-manager,researcher,security-engineer,technical-writer}.md`; §8.7 confirms agents are immediately usable in Claude Code. |
| 4 | Out-of-scope items explicitly listed in the spec | PASS | §1.3 ("Out of scope (deferred)") enumerates 8 deferred areas: non-`agents` book types, `update`/`diff`/`remove` verbs, multi-distro, override layer, private auth/lock files/versioning/caching/offline, dogfood migration, third-party authoring, and the no-replication contract (D8). |
| 5 | Architect promotes spec to `review` for owner approval | PASS | Task frontmatter `status: review`; progress entry 2026-05-15T00:11+0300 records the promotion ("promoting task to `review`"). |

### Summary

5 passed, 0 failed. All verification criteria satisfied; task is ready to transition to `verified`.

## Findings

Produced spec [[s0029-artbook-mvp-distribution-model]] — a fresh,
thinner design (not a revision of [[s0028-distributable-harness-sync-model]]).

**Key design decisions** (all locked in spec §2):

- **D1 — Manifest format**: YAML file named `artbook.yaml` at distro
  repo root. Uses PyYAML's `safe_load` — already a transitive
  dependency via `python-frontmatter`; consistent with
  `artifacts.yaml`.
- **D2 — Schema**: Top-level `[distro]` table (`name` required,
  `description` optional). Per-book required: `name`, `type`,
  `path`; optional: `description`.
- **D3 — One book type**: MVP recognises only `type = "agents"`.
  Anything else is a hard error.
- **D4 — Fetch strategy**: `git clone --depth 1 --branch main
  --single-branch <url> <tmpdir>`. Chosen over HTTP-archive
  download (per-host adapters needed), full clone (bandwidth
  waste), sparse checkout (more complex than the win is worth),
  or wheel install (forces packaging on every distro). Universal
  host support, no new Python deps, trivial mental model.
- **D6 — No caching**: every CLI invocation does a fresh clone
  into a `TemporaryDirectory` torn down on exit. Within one
  invocation, `read_manifest` and `pull_book` share the clone via
  a `clone_root: Path` parameter so list+show+pull from one
  command don't re-clone.
- **D7 — Distro URL config**: new top-level `artbook.distro_url`
  key in `artifacts.yaml`. No CLI flag override in v1.
- **D8 — Placement**: `agents` book writes to
  `<vault>/.claude/agents/`. Chosen because Claude Code is the
  universal target for agent specs; OpenStation-specific or
  multi-target placement is out of scope.
- **D9 — Overwrite policy**: pre-existing destination files are
  overwritten unconditionally — no prompts, no backups, no diff.
  Files in destination but not in the book are left alone (MVP
  does not delete extras).
- **D10 — CLI shape**: `artifacts book <verb>` — conscious
  exception to CLAUDE.md's "flat verbs" rule, justified because
  `book` is a resource noun namespace, not a streaming/paging
  variant. Three verbs: `list`, `show`, `pull`.
- **D11 — Module location**: `src/artifacts_os/artbook/` — peer
  to `core`, `cli`, `views`. Depends only on `core`; must not
  import from `views`, `cli`, `log`, `tui`, `ai`, `hooks`,
  `events`.
- **D15 — Exit codes**: 0 ok, 1 runtime error (fetch / parse /
  unknown book), 2 usage, 3 vault-not-initialised, 4
  distro-URL-not-configured.
- **D16 — Book content placement in the distro is unconstrained**:
  `artbook.yaml` is a view over the repo, not a layout decree. A
  book's `path` may point at any sub-tree (e.g.
  `openstation/agents/`), so an existing project repo can become
  its own distro by adding one manifest file — no content
  duplication, no reorganisation. Two example layouts in §3.1:
  Layout A (dedicated distro repo) and Layout B (project repo
  doubling as its own distro).
- **D17 — Manifest schema versioning**: required top-level
  `version: 1` field. Clients that don't speak v1 reject the
  manifest with a clear error; future schema migrations land as
  v2 without breaking older clients.
- **D18 — Optional explicit file allowlist per book**: the book
  entry may carry a `files: [...]` array naming exactly which
  files to ship. When present, that list is the source of truth;
  when absent, the agents handler walks the directory and applies
  D20's convention filter.
- **D19 — Symlink at destination is unlinked first**: if the
  destination path is a symlink (broken or live), `book pull`
  unlinks it before writing a regular file. The symlink target is
  never mutated. `WrittenFile.was_symlink` records the prior
  state for the report.
- **D20 — Agents directory walker convention**: include `*.md`;
  exclude `README.md` (case-insensitive) and dotfiles; ignore
  sub-directories (non-recursive). Distro authors who need exact
  control use D18's `files` allowlist instead.

**Worked example (§8)** walks a fresh consumer's project through
`artifacts init` → edit `artifacts.yaml` → `book list` → `book
show agents` → `book pull agents`, ending with 9 agent files at
`.claude/agents/*.md` ready for Claude Code to consume.

**User manual** ([[n0013-artbook-book-command-user-manual]]) — a
practical guide for consumers and distro authors covering setup,
the three verbs (with realistic terminal sessions for each),
distro authoring (Layout A vs Layout B, `files:` allowlist),
exit-code reference, FAQ, and a quick-reference cheat sheet.

**Implementation seams (§10)** keep the design open for the
deferred features: new book types extend `_PLACEMENT`; lock files
hook the existing `PullReport.distro_sha`; caching slots into the
`read_manifest`/`pull_book` split; multi-distro extends the
manifest tuple.

## Downstream

- **Implementation task** — `artbook` module + CLI command +
  tests. Estimate: ~500 LoC + tests. Decomposable into:
  (a) `artbook` module proper (manifest, fetch, placement, pull,
  settings, errors); (b) `artifacts book` CLI command (parser,
  three sub-verbs, Rich rendering, `--json`); (c) tests with a
  fixture distro repo (created in `tmp_path` using `git init`,
  per existing test patterns).
- **`artbook.distro_url` setting** needs documentation in
  `docs/settings.md` once implemented.
- **`docs/cli.md`** (if/when it exists) gains a `book` section
  documenting the namespaced sub-commands as a precedented
  exception to the "flat verbs" rule.
- **Future spec**: `book update` / `diff` / `remove` — likely
  the next iteration after MVP lands.
- **Future spec**: multi-target placement (`.claude/agents/` +
  `.openstation/agents/` + `artifacts/agents/`) once the MVP
  pull loop is dogfooded.

## Progress

- 2026-05-15T00:11+0300 — architect: produced
  [[s0029-artbook-mvp-distribution-model]]; fresh thinner spec,
  all six scope items addressed; promoting task to `review`.
- 2026-05-15T00:35+0300 — architect: refined spec per owner
  feedback. Added D16 to lock that book content can live anywhere
  in the distro repo — `artbook.toml` is a view over the repo, not
  a layout decree. §3.1 now shows two layouts: dedicated distro
  repo (A) and project repo doubling as its own distro (B).
- 2026-05-15T00:50+0300 — architect: Q1 resolved by owner — MVP
  explicitly does not solve file replication on either side. D8
  expanded to make the single-source, single-destination contract
  explicit; §1.3 out-of-scope list grows one item; §7.2.1 added to
  spell out the principle and the future extension seam
  (`_PLACEMENT[type]: str` → `list[str]` when a multi-destination
  spec lands).
- 2026-05-15T01:55+0300 — architect: created
  [[n0013-artbook-book-command-user-manual]] — practical guide
  for end users (setup, three verbs with realistic terminal
  sessions, error reference, FAQ) and distro authors (Layout A
  vs Layout B, `files:` allowlist, schema reference). Attached
  to the task as an artifact.
- 2026-05-15T01:50+0300 — architect: D22 refined per owner —
  introduce `core.models.ItemMeta` base class (with overridable
  `cell(key, default)` method) instead of a generic
  `Mapping[str, Any]`. `ArtifactMeta` becomes `ArtifactMeta(ItemMeta)`
  and overrides `cell` to read from `frontmatter`; new renderable
  types (`BookRow`, `BookContentRow`, `WriteActionRow`) inherit
  from `ItemMeta` and use the default attribute-lookup `cell` —
  no `frontmatter` plumbing for non-artifact data. `render_table`
  now takes `Sequence[ItemMeta]` and an explicit `status_colors`
  param (extracted from `kind_def` at the call site, one extra
  line in `cli/commands/list.py`).
- 2026-05-15T01:35+0300 — architect: owner pointed out the
  rendering is just tables and asked whether the core/views layer
  can be reused. Right call — added D21 and D22 to the spec:
  (D21) `cli/commands/book.py` reuses `views.render_table` for
  default output and `dataclasses.asdict` for `--json`; the
  `artbook` module itself stays pure-logic (D11 reaffirmed). (D22)
  small precursor refactor generalises `views.render_table` to
  accept `Sequence[ItemMeta]` where `ItemMeta` is a new base class
  in `core.models` — `ArtifactMeta(ItemMeta)` overrides `cell` to
  read from `frontmatter`; new renderable types (`BookRow`,
  `BookContentRow`, `WriteActionRow`) inherit from `ItemMeta` and
  rely on default attribute-lookup `cell`. Updated §5.1.1 — §5.1.4
  show the `ItemMeta` hierarchy, the renderer's new signature, and
  worked pseudocode. The artifact-flavoured `render_table` call
  site at `cli/commands/list.py` changes by one line (pulling
  `status_colors` out of `kind_def`).
- 2026-05-15T01:15+0300 — architect: Q2-Q5 resolved by owner.
  Spec changes:
  (Q2 / D19) destination overwrite unlinks symlinks first and
  writes a regular file; symlink target is never mutated;
  `WrittenFile.was_symlink` records the prior state.
  (Q3 / D1, D12, D17) manifest format switched from TOML to YAML
  (`artbook.yaml`) — consistent with `artifacts.yaml`, reuses
  PyYAML (already transitive via `python-frontmatter`), no new
  dependency. Required top-level `version: 1` field locks the
  schema version; clients reject `version != 1` with a clear
  error.
  (Q4 / D20) agents handler is non-recursive; sub-directories of
  `book.path` are ignored; `files` entries cannot contain `/`.
  (Q5 / D18, D20) two ergonomic modes for content selection:
  optional `files: [...]` allowlist on the book entry (explicit
  lock), or convention walker (`*.md` minus `README.md` minus
  dotfiles). Distro authors choose; the handler honours whichever
  is set.