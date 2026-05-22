---
created: 2026-05-22
id: n0018
kind: note
name: hooks-via-artbook-design-brainstorm
---

## Context

Session brainstorm (2026-05-22) designing how hook scripts get shared
between artifacts-os consumer projects via the existing artbook
distribution mechanism. Triggered by [[n0017-hook-scripts-not-installed-in-consumer]]
(elephant-words integration revealed `bin/hooks/auto-*` scripts referenced
in `openstation.yaml` are never installed in consumer projects).

Scope clarification surfaced early: this brainstorm targets
**artifacts-os hooks** (declarative `hooks:` list in `artifacts.yaml`,
dispatched by `src/artifacts_os/hooks/`). OpenStation hooks are out of
scope for the implementation task but the design is constrained by
"OpenStation must be able to leverage the same mechanism later" — that
requirement does substantial work in the design.

Related: [[n0017-hook-scripts-not-installed-in-consumer]],
[[s0029-artbook-mvp-distribution-model]],
[[s0031-artbook-post-pull-artifact-promotion]],
[[n0015-artbook-promotion-mechanism-design-brainstorm]],
`docs/hooks.md`, `docs/events.md`, `docs/artbook.md`.

## The gap we identified

Today a working hook in a consumer project is **two things glued
together**:

1. A declarative matcher + action entry in `artifacts.yaml` `hooks:`
   (artifacts-os) or `openstation.yaml` `hooks:` (OpenStation).
2. A script the action references (e.g. `bin/hooks/auto-commit`).

The YAML travels with the project. The scripts don't. Artbook ships
agents and skills happily — agents are inert markdown, skills are
multi-file folders shipped via `recurse: true`. **Hooks have no
distribution story.** Each consumer must hand-copy scripts from the
upstream source repo and re-author the YAML to point at them.

The deeper papercut: the matcher and the script live in two places.
Even if you copy the script in, you still have to author the
matcher YAML separately. Two artifacts to keep in sync, one
distributed, the other manually authored.

## Framings considered (diverged before converging)

| Framing | Shape | Verdict |
|---|---|---|
| A — Scripts-only book | artbook ships scripts to `.claude/hooks/`; consumer hand-authors YAML matchers | Solves transport, not the deeper papercut — config still drifts from scripts. Rejected as MVP-but-not-useful. |
| B — Scripts + YAML-snippet bundle | artbook ships scripts AND patches the consumer's `artifacts.yaml` on pull | UX right, mechanism wrong. YAML merging is hostile (comments lost, ordering churn, user overrides clobbered). Rejected. |
| C-thin — Hook is one markdown file, inline action only | Single `.md` with matcher + inline action in frontmatter | Works for `notify` / `file-drop` / one-liner shell. **Fails for substantial scripts** like OpenStation's `auto-commit` — can't reasonably embed a 50-line script in YAML frontmatter (no shellcheck, escaping hazards, no reuse, no `+x`, hostile diffs). |
| C-fat — Hook is one markdown file, script in body | Frontmatter for matcher; markdown body IS the script | Awkward — markdown body hostile to script editing, no `chmod +x` story, can't have helpers. |
| D — Hook is a directory bundle | Manifest (`<name>.md`) + sibling `action.sh` in a directory | Handles tiny inline hooks and substantial scripts equally well. Scripts stay as real files with `+x`, shellcheck, helpers. **Chosen.** |
| E — Self-describing scripts (frontmatter in comments) | Scripts carry matcher in comment header; no separate manifest | Comment-header parsing brittle and language-specific. Rejected. |

## Locked direction

### 1. Hooks are first-class artifacts

`kind: hook`, slug-as-ID (non-numbered, like agents/skills), no status
set (degenerate — hooks aren't work items). Hook kind registered at
`artifacts/kinds/hook/kind.json`.

This makes `artifacts list --kind hook`, `artifacts show <hook>`,
wikilinks, and the events stream all work for free.

### 2. Storage layout: directory-per-artifact (Option A)

```
artifacts/hooks/
  auto-commit/                 # the artifact's storage unit IS the directory
    auto-commit.md             # manifest (the "artifact file")
    action.sh                  # +x sibling
  notify-review/
    notify-review.md           # inline-only — single file in a dir
```

The hook kind is the **first artifact kind whose storage unit is a
directory, not a file**. This is declared explicitly in the kind
schema (see point 3), not by magic.

C-thin survives under Option A as the "manifest with no siblings"
case — the directory has one file and that's fine. The slight ceremony
of always-`mkdir` is preferable to a mixed file-or-directory rule that
complicates the loader and the artbook walker.

### 3. Directory storage is a kind-declarable property

Extend `kind.json` schema with new fields:

```json
{
  "x-dir": "hooks",
  "x-storage": "directory",
  "x-manifest-name": "{slug}.md",
  "x-numbered": false,
  ...
}
```

`core.create` reads `x-storage` and either writes a single file
(default) or `mkdir + write manifest` (when `x-storage: directory`).
This mechanism is **the directory-kinds primitive**, not a hook
special case.

### 4. Skills should also become a kind using the same mechanism

Skills today are shipped via artbook `recurse: true` but are not
registered as a `kind`. They have no `artifacts/kinds/skill/kind.json`,
no `--kind skill` for `create`, no `artifacts list --kind skill`.
They're content shipped at the transport layer, not first-class
artifacts.

The `x-storage: directory` primitive built for hooks unlocks
skills-as-kind for free. **Recommended as a sibling task**, not part
of the hooks task — same mechanism, two consumers, mutually validating.

### 5. Pull = canonical landing; activation is external state

Hooks land in `artifacts/hooks/` on `artifacts book pull`. They are
**inert** until promoted. The loader does not fire pulled-but-unpromoted
hooks.

Promotion state lives **outside the artifact frontmatter** (no
`enabled:` field). Two flavors considered:

| Flavor | Mechanism | Verdict |
|---|---|---|
| 1 — Filesystem symlinks | Symlink in `artifacts/hooks/.active/<name>` points at the registry entry | **Chosen.** Mirrors existing artbook `promote:` mechanism. No YAML mutation. Cross-host parity is free (both loaders scan the same `.active/`). |
| 2 — Config list | `artifacts.yaml` has `hooks.active: [name1, name2]` | Re-introduces YAML editing on every promote/demote. Cross-host requires the second host to read another system's config. Rejected. |

The key property: **re-pull preserves activation.** Re-pulling
overwrites `artifacts/hooks/auto-commit/` (D9: overwrite-no-prompt),
but the symlink in `.active/` still resolves to the same path. The
consumer's "yes I want this to fire" decision survives distro refresh.

**Why external state is correct:** the registry artifact is
distro-owned (refreshed by pull); the activation state is
consumer-owned (set by `artifacts hook promote`). Mixing them in
frontmatter would clobber the consumer's choice on every re-pull.

### 6. `.active/` is tracked in git

Hooks are project behavior, not local developer preference. PR review
sees activation changes. CI behavior is consistent across developers.
A developer disabling a hook locally is a change worth reviewing.

### 7. Matcher schema: events vocabulary as lingua franca

Both hosts express matchers in the artifacts-os events vocabulary:

```yaml
matcher:
  event: artifact.status_changed
  kind: task
  after: done
  fields.assignee: developer
```

Rationale: OpenStation status transitions ARE artifact-status-change
events at the substrate (both systems observe the same frontmatter
mutation). OpenStation's native `*→done` syntax predated the events
system; the events vocabulary subsumes it and gives OpenStation hooks
more matcher power (`kind:`, `fields.X:`) than they have today.

The `host:` field stays but its job is **declaring action context**,
not discriminating matcher vocabulary. `host: openstation` means
"this action assumes OpenStation CLI / env on PATH"; a loader can
refuse to fire it in a vault without OpenStation set up.

### 8. Scope: artifacts-os mechanism only; OpenStation adopts later

The artifacts-os feature task ships:

- Directory-storage kinds (`x-storage: directory` primitive)
- Hook kind + manifest schema
- `artifacts/hooks/.active/` promotion mechanism
- artifacts-os loader scans `.active/`, fires only `host: artifacts-os` matches
- New `hook` book type for artbook
- CLI verbs: `artifacts hook promote/demote/list/show`

OpenStation adoption is a separate task **in the OpenStation repo**,
on OpenStation's timeline, with its own architect spec. Decoupling
the two means:

- Different codebases ship independently
- Artifacts-os mechanism is proven end-to-end by artifacts-os hooks first
- OpenStation adopts a validated design, not a speculative one

### 9. `artifacts create --kind hook` writes manifest only (MVP)

```bash
artifacts create --kind hook "auto-commit" \
  --host openstation \
  --fields 'matcher.event=artifact.status_changed' \
           'matcher.after=done'
# creates: artifacts/hooks/auto-commit/auto-commit.md
# operator manually adds:
#   touch artifacts/hooks/auto-commit/action.sh
#   chmod +x artifacts/hooks/auto-commit/action.sh
```

`--attach <path>` flag for sibling files is a **fast-follow**, not
MVP. The MVP create UX is: write the manifest, operator authors
scripts manually with their normal editor.

### 10. Legacy `artifacts.yaml hooks:` list — soft-deprecate

Keep loading the legacy list for back-compat. Emit a deprecation
warning at load time pointing operators at the new directory-based
form. No forced cutover. Migration tool is optional fast-follow.

## Strawman manifest

```markdown
---
id: auto-commit
kind: hook
name: auto-commit
host: openstation
matcher:
  event: artifact.status_changed
  after: done
action:
  type: shell
  command: ./action.sh
  timeout: 30
  phase: post
---

Auto-commits the artifact change after a transition to `done`.
Generates a conventional-commit message from the artifact ID.
```

Sibling: `artifacts/hooks/auto-commit/action.sh` (executable shell
script, normal file with `+x`).

## Strawman CLI

```bash
artifacts book pull os-hooks        # registry lands in artifacts/hooks/
artifacts hook list                 # table: id | host | matcher | active?
artifacts hook show auto-commit     # manifest + sibling files
artifacts hook promote auto-commit  # creates symlink in .active/
artifacts hook demote auto-commit   # removes symlink
```

Naming: `promote/demote` matches existing artbook vocabulary
(operators already learned `promote:` for agents).

## Strawman artbook `hook` book type

```yaml
books:
  - name: os-hooks
    type: hook
    src: artifacts/hooks/
    description: OpenStation lifecycle hooks (auto-commit, auto-verify, ...).
    # no promote: — hook books explicitly do not auto-activate
```

The defining property of `type: hook` books: **canonical landing, no
auto-promote.** Contrast with agents which auto-promote-on-pull
because they're inert. Hooks are executable; activation is an
explicit operator step.

## Open contract questions (defer to architect spec)

1. **`.active/` directory name** — `.active/` (dotfile-hidden,
   colocated with registry) is the prior. Alternatives: `active/`,
   `.enabled/`. Architect's call.
2. **`x-storage` shape** — `x-storage: directory` is the prior.
   Alternatives: `x-multi-file: true`, `x-bundle: true`. Pick the name
   that reads best in kind.json.
3. **`x-manifest-name` template default** — `{slug}.md` is the
   prior. Skills might want `SKILL.md` to match Claude Code's
   convention; the template enables this.
4. **Sibling file resolution rule** — manifest references
   (`command: ./action.sh`) resolved relative to the manifest's
   directory. Document explicitly.
5. **Stale-symlink cleanup** — when registry shrinks but `.active/`
   symlinks persist, `artifacts hook list` warns; `artifacts hook
   promote` refuses to create new symlinks against missing registry
   entries. `artifacts hook list --prune` removes dangling symlinks.
6. **Migration tool for legacy `hooks:` list** — optional one-shot
   converter splits each YAML entry into a bundle. Fast-follow.
7. **`--attach <path>` flag for `create`** — fast-follow, MVP ships
   manifest-only.
8. **`host:` enum** — start with `[artifacts-os, openstation]`;
   declare unknown values as extension points (don't reject — warn).
9. **Skill-as-kind sibling task** — separate task, same mechanism,
   parallel implementation. Architect spec for directory-storage
   kinds covers both consumers.
10. **artbook book type `type: hook`** — does it need any other
    semantic differences from existing book types (e.g. extra
    metadata in the manifest schema)?
11. **Auto-promote vs no-promote for consumer-authored hooks** —
    when an operator runs `artifacts create --kind hook`, does the
    new hook auto-promote (presence in `.active/`) or land
    unpromoted? Prior: unpromoted (consistent with distro behavior;
    operator runs `promote` explicitly).
12. **Combined spec vs split spec** — one spec for "directory-storage
    kinds + hook kind + promotion + CLI," or two specs in sequence.
    Architect's call; weak prior toward one combined spec because the
    directory-storage design wants to be validated against the hooks
    use case in the same document.

## Things explicitly out of scope (MVP)

- OpenStation adoption (sibling task in OpenStation repo)
- Skills-as-kind migration (sibling task in artifacts-os repo)
- `--attach` flag for `artifacts create`
- One-shot migration tool for legacy `artifacts.yaml hooks:` list
- Per-host matcher vocabularies (events syntax is the lingua franca)
- Trust posture for executable distro content (checksums, signing,
  inspection-before-promote) — promotion gate is the trust step;
  cryptographic verification deferred
- Multi-tool `host:` adoption beyond `artifacts-os` and `openstation`
- Auto-promotion of consumer-authored hooks (explicit promote
  required for both distro-pulled and locally-authored)

## Implementation dependency tree (informational)

```
spec: directory-storage kinds + hooks-as-artifact + promotion
  ↓
impl: x-storage kind primitive in core/cli                (track 1)
  ↓
impl: hook kind, loader, .active/, promote/demote verbs   (track 1)
  ↓
impl: hook book type in artbook                           (track 1)
  ↓
[separate] impl: skills-as-kind (uses x-storage primitive)
[separate] impl: OpenStation adoption (in OpenStation repo)
```

Tracks 1's stages are sequential. Skills-as-kind and OpenStation
adoption can start once the directory-storage primitive lands; they
don't block each other.

## Why this is worth doing

- Closes the n0017 papercut at the root, not the surface.
- Establishes directory-storage as a kind primitive (pays off skills
  debt simultaneously).
- Unifies the hook model across artifacts-os and OpenStation without
  coupling their codebases or release cycles.
- Treats hooks as artifacts — full CLI surface, events, wikilinks —
  not as YAML-list configuration.
- The consumer's activation decisions survive distro refreshes
  cleanly (external promotion state).
