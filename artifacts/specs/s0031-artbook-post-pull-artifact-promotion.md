---
kind: spec
id: s0031
name: artbook-post-pull-artifact-promotion
status: draft
task: "[[t0170-spec-the-artbook-promotion-mechanism]]"
created: 2026-05-17
agent: architect
---

# Artbook Post-Pull Artifact Promotion Mechanism

Specifies the **post-pull artifact promotion mechanism** for
artbook distros — the technical contract for the parent feature
[[t0169-add-post-pull-artifact-promotion]].

Books pull into a **single canonical location** under `artifacts/…`
and the CLI runs a tool-agnostic **promotion** step that
additionally surfaces the pulled content at one or more
consumer-tool-shaped locations declared in the distro manifest
(e.g. `.claude/agents/`). The CLI never special-cases any tool;
"supporting Claude" means the artifacts-os repo ships a
Claude-flavoured distro.

This spec resolves the eight open questions raised in
[[n0015-artbook-promotion-mechanism-design-brainstorm]] and
amends [[s0029-artbook-mvp-distribution-model]]. The manifest
schema **stays at `version: 1`** — v1 has not been published
beyond this repo, so the change tightens v1's semantics in
place rather than bumping. The new rules: `dest:` is
canonical-only (must resolve under `artifacts/`), `dest:` is
optional with a sensible default, and `promote:` is added as
the way to surface book content in tool-shaped consumer
locations. There is no back-compat shim — the only existing
v1 manifest in the ecosystem is the artifacts-os repo's own
`artbook.yaml`, and it is migrated in the same commit as the
schema change (see § 4.3).

---

## 1. Background and Cross-References

### 1.1 The gap

After [[s0029]] + [[s0030]] landed, the artifacts-os distro's
`agents` book declares `dest: .claude/agents/`. Result: after
`book pull agents`, agents land **only** in `.claude/agents/`.
The consumer's `artifacts/agents/` is empty even though `agent`
is a first-class artifact kind. `artifacts list --kind agent`
returns nothing on a freshly-initialised vault. Claude can see
the agents; the artifacts CLI cannot.

The same shape recurs for any dual-purpose content (agents,
skills, kinds). Today's single-`dest` model forces the distro
author to pick one view at the expense of the other.

### 1.2 Parent intent

[[t0169-add-post-pull-artifact-promotion]] captures the user
story:

> **As a** user pulling a distro book **I want** the pulled
> content to land in its canonical `artifacts/…` location *and*
> automatically surface in any tool-specific consumer location
> the distro declares (e.g. `.claude/agents/`) **so that** the
> artifacts CLI and the consuming tool both see the same content
> without me running a second copy/symlink step.

### 1.3 Direct ancestors

- [[n0015-artbook-promotion-mechanism-design-brainstorm]] —
  produced L1–L5 and the eight open questions resolved here.
- [[s0029-artbook-mvp-distribution-model]] — current artbook
  manifest schema (v1). This spec **tightens v1's semantics
  in place** (no version bump — v1 has not been published
  beyond this repo): `dest:` becomes optional with a canonical
  default and canonical-only constraint when set; `promote:`
  is added. D24 carries over unchanged; D8 / D25 are
  strengthened (`dest:` is now canonical-only); new decisions
  D28–D40 amend the schema and add the promotion pipeline.
- [[s0030-books-driven-init-flow]] — the no-distro D2 fallback
  is amended (Q8 below).
- [[t0167-implement-books-driven-init-flow]] — D2 currently
  writes `.claude/skills/artifacts-os/` direct; this spec
  redirects it through canonical + promote (Q8 / D40).

### 1.4 Code touched

| File | Change shape |
|---|---|
| `src/artifacts_os/artbook/manifest.py` | Add `promote:` parsing (string or object), make `dest` optional with default mirroring `src` under `artifacts/`, **reject `dest:` outside `artifacts/`** (canonical-only). Version stays `1`. No back-compat shim; the only existing v1 manifest (this repo's `artbook.yaml`) is migrated in the same commit. |
| `src/artifacts_os/artbook/placement.py` | Add `promote_book` (post-write step), state-file read/write, idempotent symlink/copy logic, stale-target cleanup. |
| `src/artifacts_os/artbook/pull.py` | Call `promote_book` from `pull_book` after the canonical copy. Extend `PullReport` with promotion results. |
| `src/artifacts_os/artbook/settings.py` | Add `promotion: enabled \| disabled` and `promote_mode: symlink \| copy` consumer overrides. |
| `src/artifacts_os/artbook/state.py` (new) | Read/write `artifacts/.artbook/state.json` — tracks previously-promoted targets per book for idempotent re-pull + stale-target cleanup. |
| `src/artifacts_os/cli/commands/book.py` | Add `--no-promote` to `book pull`. Add new verb `artifacts book promote [BOOK]` for explicit re-run. |
| `src/artifacts_os/cli/commands/init.py` | Wire `--no-promote` through init. Update D2 fallback to write canonical + promote (Q8 / D40). |
| `artbook.yaml` (repo root) | Migrate to canonical-landing shape: `agents`, `commands`, `skills` get `promote:` lines; `kinds` stays canonical-only. |
| `docs/artbook.md` | Author guide: `promote:` field, mode default, opt-out. Consumer guide: `--no-promote`, `artbook.promotion`, `artbook.promote_mode`, the `book promote` verb. |
| `tests/artbook/test_manifest.py` | `promote:` parsing (string/object), optional `dest:` default, vault-escape on promote target. |
| `tests/artbook/test_placement.py` | Symlink mode + fallback, copy mode, idempotent re-pull, stale-target cleanup, state file round-trip. |
| `tests/cli/test_book.py` | `--no-promote`, `artifacts book promote`. |
| `tests/cli/test_init.py` | D2 fallback writes canonical + promotes. |
| `tests/artbook/test_pull_integration.py` (new) | End-to-end pull with promote + opt-out + re-pull. |

---

## 2. Locked Foundations (L1–L5, verbatim from brainstorm)

These were settled by the user in
[[n0015-artbook-promotion-mechanism-design-brainstorm]] §
"Locked direction". They are foundational; nothing in §3 below
contradicts them.

### L1 — Canonical landing under `artifacts/…`

Books pull into `artifacts/…` by default, mirroring `src:`.
`dest:` becomes optional. The vault's canonical view of book
content is always under `artifacts/`.

### L2 — Distro-author owns promotion config (option α)

A new `promote:` field per book in `artbook.yaml` declares the
tool-shaped consumer location. Distros are self-installing —
zero consumer config required to consume a promotion-using
distro.

### L3 — CLI is tool-agnostic

`promote:` is just a vault-relative path string. The CLI doesn't
special-case `.claude/`, `.cursor/`, or any other tool
convention. "Supporting Claude" means the artifacts-os repo ships
a Claude-flavoured distro; the CLI itself learns nothing about
Claude.

### L4 — Tool-flavoured distros are the scaling unit

Multi-tool support (Cursor, Codex, etc.) is delivered by
**writing more distros**, not by adding tool-specific CLI
features. MVP scope is Claude-flavoured artifacts-os distro
only. Transformers / shape conversion (e.g. Codex's `AGENTS.md`
aggregation) are explicitly deferred.

### L5 — Promotion runs implicitly after pulls

Every `book pull` and every `init` book step runs promotion as a
post-step. The operator does not need an explicit verb for the
common case.

---

## 3. Decisions (D28–D40)

Numbered to continue from [[s0029]] D27. Each decision states
the choice, the rationale, and the rejected alternatives. The
mapping to brainstorm question numbers (Q1–Q8) is given in each
heading.

### D28 — `dest:` semantics: strict, canonical-only, no back-compat (Q1)

**Decision.** Manifest schema stays at `version: 1`. v1 has
not been published beyond this repo, so v1's semantics are
**tightened in place** rather than bumped:

1. `version: 1` remains the required version (D17 unchanged).
2. `books[].dest` becomes **optional**. When set, it **must**
   resolve under `<vault_root>/artifacts/` — any `dest:` outside
   `artifacts/` raises `ManifestError` at parse time
   ("`book '<name>' dest: '<path>' is not under 'artifacts/'.
   dest: is canonical-only — move tool-specific paths to
   promote:`"). The vault-escape guard from D25 still applies
   on top (no `..`, no absolute paths).
3. When `dest:` is omitted, the default is
   `artifacts/<basename(src)>/` per D37 — the canonical mirror
   of `src:` under the vault's `artifacts/` tree.
4. `books[].promote` is a new optional field (D29) that
   declares the tool-shaped consumer location (the role
   `dest:` used to play for tool views).
5. **No back-compat shim, no deprecation warning, no version
   bump.** The only existing v1 manifest in the ecosystem is
   the artifacts-os repo's own `artbook.yaml`; it is migrated
   in the same commit as the schema change (§ 4.3). Any
   third-party manifest authored against the looser pre-spec
   v1 simply fails to validate until it is updated.

**Rationale.** Two facts make the strict-in-place path
strictly simpler than a version bump:

- v1 has not been published beyond this repo. There is no
  installed base of third-party distros to break; the schema
  is effectively still in development.
- The user explicitly directed that back-compat is not
  required.

Given those two facts, the choice is between:

- *Strict in v1* — one parser change (add canonical-only
  check). No second code path, no warnings surface, no
  version-gate plumbing.
- *Strict in v2* — bump the version gate, write a v2 parser,
  remove the v1 path. Same end state, more LOC churn, and the
  version-bump signal communicates "incompatible change to a
  shipped surface" — which is misleading when v1 was never
  shipped.

Strict in v1 is the smaller change with the same outcome.

**Rejected alternatives.**

- *v2 bump (the previous draft of this decision).* Misleading
  signal — v1 was never published, so bumping suggests
  breaking changes against a shipped surface that doesn't
  exist. Adds parser plumbing for no gain.
- *Lenient back-compat (an earlier draft).* Explicitly
  rejected by the user — adds warning plumbing and a
  permanent legacy code path for no benefit given the
  ecosystem size.
- *Default `dest: artifacts/<book.name>/` (using `name` rather
  than `src` basename).* Rejected because the recurse walker
  preserves `src/` subdirectory shape (per D26); the canonical
  mirror should mirror the source layout the walker already
  uses. In every realistic case (books named after their
  content type), basename and name produce the same default.

### D29 — `promote:` shape: string shorthand or object form (Q2)

**Decision.** Single-target promotion. `promote:` accepts
**either** a string shorthand **or** a single object form.
Lists are deferred to a follow-up spec.

```yaml
# Shorthand — promote target only; mode comes from per-vault default (D30).
- name: agents
  src: artifacts/agents/
  promote: .claude/agents/

# Object form — explicit per-promotion mode override (D30).
- name: skills
  src: artifacts/skills/
  promote:
    target: .claude/skills/
    mode: copy        # 'symlink' (default) or 'copy'
```

**Schema constraints (parser-enforced).**

| Field | Type | Required | Notes |
|---|---|---|---|
| `target` | string | yes (object form) | Vault-relative path. Same escape guard as `dest:` — rejected if absolute or contains `..` (raise `ManifestError`). |
| `mode` | string | no | `symlink` (default) or `copy`. Any other value raises `ManifestError`. |

A `promote:` value that is neither a string nor a mapping
raises `ManifestError`. Empty string / empty mapping likewise
rejected. When `promote:` is absent the book is **canonical
only** (no promotion).

**Rationale.** A string + single object covers every concrete
distro shape we've identified (Claude agents, Claude skills,
Claude commands, future Cursor rules). The list form's only
identified use case — one book promoting to multiple tools
simultaneously — collides with L4: the scaling unit is
**tool-flavoured distros**, not multi-tool books. Adding list
parser complexity today buys a scenario L4 explicitly defers.
Adding it later is an additive parser change; removing it later
would be breaking.

**Rejected alternatives.**

- *List of strings / objects.* See above — defers cleanly to a
  future spec when a real multi-tool distro shape exists.
- *Object form only, no string shorthand.* Forces every
  promotion to spell out `target:` and `mode:` even when both
  use the per-vault defaults. The shorthand is the 95% case in
  the artifacts-os distro and any tool-flavoured derivative.

### D30 — Promotion mode: symlink default with copy fallback (Q3)

**Decision.** The default promotion mode is **`symlink`**.

- **Per-promotion override** — `promote.mode: copy` in the
  manifest forces copy mode for that book regardless of the
  vault default.
- **Per-vault override** — `artbook.promote_mode: copy` in
  `artifacts.yaml` overrides the **default** mode for that
  vault; per-promotion `mode:` still wins.
- **Automatic fallback** — when `mode: symlink` is requested
  (manifest default or per-vault default) and the underlying
  filesystem raises `OSError` on `os.symlink` (Windows without
  developer mode, some FAT mounts, Docker volumes with
  symlink restrictions), the CLI falls back to copy mode for
  that file and logs once per book pull:

  > `book 'agents' promotion: symlinks not supported on this
  > filesystem; using copy mode. Set artbook.promote_mode: copy
  > in artifacts.yaml to silence this notice.`

- **Mode precedence** (highest wins):
  1. Per-promotion `promote.mode` (manifest, distro-author).
  2. Per-vault `artbook.promote_mode` (consumer override).
  3. Default `symlink` (with automatic copy fallback).

**Symlink target shape.** A `symlink` promotion at
`.claude/agents/architect.md` points at the canonical file at
`artifacts/agents/architect.md` via a **relative** symlink
(`../../artifacts/agents/architect.md` from
`.claude/agents/`). Relative links survive vault relocation
(rename of the vault directory) which absolute links do not.

**Granularity.** Promotion is **per-file**, not per-directory.
Per-directory symlinks would simplify recurse-mode promotion
but break under partial-pull (consumer pulls `agents` book with
`--book agents:architect`), would shadow user-added local files
in the target directory, and complicate stale-target cleanup
(D32). Per-file matches D26 walker output exactly: every
canonical write produces exactly one promotion write.

**Rationale.** Symlinks are the right default on POSIX (zero
extra bytes, edit-in-place flows through to the consumer view,
single source of truth at write time). Copy fallback is
unavoidable on Windows without dev mode. A consumer-facing
override is needed for Windows users who don't want a per-file
warning on every pull, and for operators on shared filesystems
where symlinks confuse tooling. Per-promotion override gives
the distro author the final say when a particular target
*must* be a copy (e.g., a future tool that reads the file's
inode metadata).

**Rejected alternatives.**

- *Default `copy`.* Doubles disk bytes for every promoted file
  on POSIX — wasted for the 95% case to avoid a warning that
  affects the 5% case (Windows). Editing the canonical file
  doesn't flow through to the consumer view, surprising
  authors of tool-flavoured distros.
- *Reflink / hardlink default.* Filesystem-dependent (reflinks
  need btrfs/xfs); hardlinks break cross-device promotions and
  make editing footguns silent.
- *No fallback (hard error on Windows without symlink rights).*
  Forces every Windows operator to either enable dev mode or
  set the per-vault override before init; rejected for
  ergonomic reasons.

### D31 — Consumer opt-out: both flag and setting (Q4)

**Decision.** Both levers, layered:

1. **Per-vault setting** — `artbook.promotion: enabled |
   disabled` in `artifacts.yaml`. Default: `enabled`.
   Persistent opt-out — once set, every `book pull` and every
   `init` book step skips the promotion phase.
2. **Per-invocation flag** — `--no-promote` on `artifacts book
   pull` and `artifacts init`. One-shot, overrides the setting
   for the current invocation only. There is no
   `--with-promote` complement (the setting already provides
   the persistent-enable lever; the flag exists only to skip).
3. **Precedence.** `--no-promote` always wins. With the flag
   absent, `artbook.promotion` decides.

When promotion is skipped, the canonical write under
`artifacts/…` still happens — only the post-step is disabled.
The `PullReport` records `promotion_skipped: True` and the
reason (`flag` or `setting`) for telemetry / display.

**Rationale.** The flag and the setting address different
operators:

- The flag is the operator who wants a one-off "canonical-only"
  pull (e.g., to debug what the distro actually shipped).
- The setting is the operator who runs a tool stack the
  distro's promotions don't apply to (e.g., a CLI-only project
  with no editor integration) and doesn't want
  `.claude/agents/` to appear in their tree on every pull.

Both are real; both cost almost nothing to implement (the
implementation is one decision branch in `pull_book`); shipping
both avoids a future "could you also add the other one" issue.

**Rejected alternatives.**

- *Flag only.* Forces operators with persistent opt-out
  preference to set up a shell alias or `.envrc` — bad
  ergonomics.
- *Setting only.* No way to do a one-off canonical pull for
  debugging without temporarily editing `artifacts.yaml`.
- *Neither (no opt-out).* Tool-agnostic CLI shouldn't force a
  tool view on operators.

### D32 — Idempotency and stale-target cleanup (Q6)

**Decision.** Promotion is **idempotent** across repeated `book
pull` runs. Stale promotion targets are **cleaned up** on every
re-pull.

**Mechanism — state file.** Each promotion run records its
output set in a vault-local sidecar:

```
artifacts/.artbook/state.json
```

Schema:

```json
{
  "version": 1,
  "promotions": {
    "agents": {
      "mode": "symlink",
      "target_root": ".claude/agents/",
      "files": [
        ".claude/agents/architect.md",
        ".claude/agents/developer.md",
        ".claude/agents/researcher.md"
      ]
    },
    "skills": {
      "mode": "copy",
      "target_root": ".claude/skills/",
      "files": [
        ".claude/skills/artifacts-os/SKILL.md",
        ".claude/skills/release-changelog/SKILL.md"
      ]
    }
  }
}
```

All paths are vault-relative. The file is written atomically
(write-to-`*.tmp` + `os.replace`).

**On `book pull <name>` (with promotion enabled).**

1. Resolve the canonical entries (same `_select_files` walker
   as today; D20/D26).
2. Write canonical files under `artifacts/…` (atomic
   write-through-tmp + `os.replace`, identical to D19).
3. Read `artifacts/.artbook/state.json` (empty dict if absent).
4. Look up `promotions[<book.name>]`:
   - If present: compute **stale set** = previously-promoted
     files **not** in the current canonical entries. For each
     stale path:
     - `lstat` it; **only remove if it is a symlink pointing at
       the canonical tree** (`os.readlink` resolves under
       `<vault>/artifacts/`) **or** a regular file whose
       content matches the prior canonical content (hash-equal
       to the recorded canonical hash; see "Hash record"
       below). Otherwise leave it alone (user-modified).
     - This guarantees we never delete a user-edited file or
       an unrelated file that happened to share the target
       directory.
   - If absent: no cleanup; this is the first promotion.
5. Re-emit the promotion for every current canonical file:
   - **Symlink mode**: `unlink` existing target file (if it
     exists and is a symlink pointing at the canonical tree),
     `os.symlink` to the relative canonical path. If the
     existing target is a regular file whose content matches
     the new canonical: unlink-then-symlink (replace, idempotent
     re-pull on a vault where the promotion was previously a
     copy and the mode flipped). If it is a regular file that
     does *not* match: warn and skip (`use --force to
     overwrite`; behaviour mirrors D19 unlink-then-write but
     defaulted to safe on promotion).
   - **Copy mode**: atomic write-through-tmp + `os.replace` —
     always overwrites with the canonical content, regardless
     of prior state. Equivalent to D19 semantics on the
     canonical write but applied to the promotion target.
6. Persist the new state to
   `artifacts/.artbook/state.json` (atomic).
7. Return a `PromotionReport` (D33) listing every promoted file
   plus the cleaned-up stale set.

**Hash record (copy-mode stale detection).** The state file
records each copy-mode promotion's source hash
(`hashlib.sha256` of canonical file content). On stale-target
detection in copy mode, `state.files[X].hash` is compared
against the current content of `X`. Hashes recorded only for
copy mode; symlink mode uses `os.readlink` to verify ownership
and needs no hash.

Augmented schema (showing the hash field):

```json
"files": [
  {"path": ".claude/skills/artifacts-os/SKILL.md",
   "hash": "sha256:f3a1…"}
]
```

The schema accepts both shapes (string or `{path, hash}`) on
read; on write, copy-mode entries always emit the object form,
symlink-mode entries emit the string form for compactness.

**Re-pull when promotion is disabled.** When `--no-promote` is
in effect, the canonical write still happens. The state file
is **not** modified. The next pull with promotion re-enabled
will pick up where the last promotion-enabled pull left off
(stale cleanup against the recorded state, not against the
current target dir).

**`artifacts book promote --clean`.** Operators who want the
state file reset (e.g., after manually deleting a promotion
target and wanting the next pull to re-create it cleanly) can
run `artifacts book promote --clean <BOOK>` (D34) to ignore the
recorded state and rebuild it from the current canonical
content.

**Rationale.** A sidecar state file is the only approach that
correctly distinguishes "files artbook promoted" from "files
the user / another tool dropped into the same directory". The
target directories (`.claude/agents/`, `.claude/skills/`) are
shared spaces — `.claude/agents/` may contain user-authored
local agents, and we must never touch them. Hash-equal
detection is the minimum safety check that lets copy-mode
cleanup distinguish "this is still the file we wrote" from
"the user edited this".

**Rejected alternatives.**

- *No cleanup (leave stale targets).* Silently lies to the
  operator after the distro removes an item — the consumer
  still sees the old promotion. Hard to discover.
- *Cleanup by walking the target dir and removing anything not
  in the current canonical set.* Nukes user-authored content
  in shared directories. Unsafe.
- *No state file; track ownership by a special filename
  prefix (`__artbook__architect.md`).* Visible to the consuming
  tool; not all tools (Claude included) cope with arbitrary
  prefixes; aesthetic regression for the distro author.
- *State file at `~/.artifacts-os/state/…` (user-scoped).*
  Splits state across machines; doesn't survive vault-only
  backups. Vault-local is the right scope.

### D33 — `PromotionReport` and `PullReport` extension

**Decision.** Promotion produces a `PromotionReport`
dataclass; `PullReport` is extended with a `promotion:
PromotionReport | None` field.

```python
@dataclass(frozen=True)
class PromotedFile:
    """One promotion write."""
    canonical: Path        # absolute path under artifacts/…
    target: Path           # absolute path under the promotion target
    mode: str              # 'symlink' or 'copy'
    overwritten: bool      # True if target existed before write
    fallback: bool         # True if symlink requested but fell back to copy


@dataclass(frozen=True)
class PromotionReport:
    """Outcome of a promote step for one book."""
    book: Book
    target_root: Path           # absolute path of the promotion target dir
    mode: str                   # effective mode (symlink/copy)
    promoted: tuple[PromotedFile, ...]
    cleaned: tuple[Path, ...]   # stale targets removed this run
    skipped: tuple[Path, ...]   # user-modified targets we declined to overwrite
    fallback_count: int         # files where symlink → copy fallback occurred


@dataclass(frozen=True)
class PullReport:
    """Outcome of a pull_book call. (extended from §4.3)"""
    book: Book
    written: tuple[WrittenFile, ...]            # canonical writes (unchanged)
    promotion: PromotionReport | None           # NEW — None if no promote/promotion disabled
    promotion_skipped_reason: str | None        # 'flag' | 'setting' | None — NEW
    distro_url: str
    distro_sha: str
```

**Rationale.** Existing call sites (CLI display, future TUI)
need structured access to the promotion result distinct from
the canonical writes. Folding promotion into `PullReport.written`
loses the canonical-vs-promotion distinction. `None`
`promotion` cleanly represents both "book has no `promote:`
field" and "promotion was skipped"; the optional
`promotion_skipped_reason` distinguishes the two for display.

### D34 — Verb naming: `promote` is the field and the verb (Q7)

**Decision.** The manifest field is `promote:` (D29). The CLI
re-run verb is `artifacts book promote [BOOK]`.

**`artifacts book promote` semantics.**

- With no `BOOK`: re-runs promotion for every book in the
  distro manifest that has a `promote:` field. Re-uses the
  current canonical content under `artifacts/…` (no clone, no
  pull).
- With `BOOK` positional: re-runs promotion for that book only.
- `--clean`: ignores the existing state file's `promotions[<book>]`
  entry and rebuilds it from scratch.
- `--no-promote` is **not** valid on `book promote` (the verb
  is the promote step itself).
- `--dry-run` is supported (prints planned writes /
  cleanups, makes no changes).
- `--json` emits the `PromotionReport` as JSON.

The verb does **not** clone the distro and does **not** modify
canonical content. It is purely a "re-emit the canonical
content into the promotion targets" operation.

**Rationale.**

- *"promote"* reads well in both author and consumer contexts.
  Author: "this book is **promoted** to `.claude/agents/`."
  Consumer: "`book promote` re-applies the promotion step."
  Mirrors the `s0029` style of CLI verbs that double as
  manifest field meanings.
- *"mount"* (file-system overloaded), *"expose"* (API-flavoured),
  *"link"* (too narrow — implies symlink only), *"surface"*
  (unfamiliar CLI verb) — all rejected.
- An explicit re-run verb costs ~50 lines of CLI plumbing
  (parser registration + dispatch) once the promotion logic is
  factored out for `pull_book`. The cost-benefit is favourable:
  it's the obvious recovery verb when an operator changes the
  per-vault mode setting (D30) or restores a vault from a backup
  where the promotion target is missing or corrupted.

**Rejected alternatives.**

- *No explicit verb (only implicit `book pull`).* Forces a full
  re-clone every time an operator wants to re-emit promotions,
  which is wasteful and noisy.
- *Verb at top level — `artifacts promote BOOK`.* Inconsistent
  with the `artifacts book <verb>` namespace established by
  s0029 D10.

### D35 — User-authored content stays canonical-only at MVP (Q5)

**Decision.** Promotion runs at **book-pull time only**.
`artifacts create --kind agent <name>` writes to
`artifacts/agents/<name>.md` and **does not** auto-promote.
The distro's promotion rules are **not** persisted into
`artifacts.yaml` at init.

A user-authored agent ends up canonical-only. To make it
visible to a Claude-flavoured tool, the operator either:

1. Symlinks / copies the file manually, **or**
2. Re-runs `artifacts book promote agents` after authoring (if
   the operator has set up a per-vault override that says "the
   `agents` book promotion target covers all canonical agents,
   not just the ones the distro shipped" — explicitly out of
   scope here), **or**
3. Waits for a follow-up spec that introduces auto-promotion
   for user-authored content.

**Rationale.** Auto-promoting on `artifacts create` is a
separate concern from the pull-time fan-out this spec
addresses:

- It requires a different design surface (a kind → promotion
  rule mapping persisted in the vault, populated by init from
  the distro's `promote:` declarations).
- It interacts with `artifacts create` write semantics (atomic
  write + promotion in one go vs. write first, promote second).
- It needs a new opt-out lever for users who don't want every
  `artifacts create --kind agent` to scatter writes across the
  vault.

Tackling it in this spec triples the surface; deferring it
keeps the MVP focused. The follow-up spec can land additively
(an opt-in `artifacts.yaml.kinds.<kind>.promote: <path>` table
populated at init — exact shape TBD by that spec).

**Rejected alternatives.**

- *Bake promotion rules at init.* As above — too much surface
  for one spec.
- *Auto-promote unconditionally on `artifacts create`.* No
  opt-out lever; surprising for users not running a
  Claude-flavoured tool stack.

### D36 — Promotion ordering and atomicity

**Decision.** Promotion is a strict post-step. The canonical
writes happen first, finish completely, and only then does
promotion start. Promotion writes are individually atomic per
D19's write-through-tmp + `os.replace` pattern (for copies) and
unlink-then-symlink (for symlinks).

**Failure semantics.**

- A failure during canonical writes aborts the pull entirely.
  Promotion does not run.
- A failure during promotion (e.g., disk full mid-symlink, or
  an unwritable target dir) is **logged and recorded** in the
  `PromotionReport`, and the pull continues with the next file.
  At the end of the promotion pass:
  - If any promotion file failed: exit code is `1` (runtime
    error); the canonical writes still succeeded.
  - The state file is updated with whatever promotions *did*
    succeed; the next re-pull will retry the failed entries.
- Promotion never modifies canonical content.

**Rationale.** The canonical writes are the source of truth;
they must succeed before promotion can run, and they must
remain intact even if promotion partially fails. Treating
promotion failures as non-fatal-for-canonical (but exit-1) lets
operators recover by re-running `book promote` after fixing the
underlying issue, without losing the canonical pull.

### D37 — Default `dest:` resolution for canonical mirror

**Decision.** When `dest:` is omitted from a book entry, the
default is computed at parse time as:

```
dest = "artifacts/" + Path(src.rstrip("/")).name + "/"
```

Examples:

| `src` | Default `dest` |
|---|---|
| `artifacts/agents/` | `artifacts/agents/` |
| `artifacts/agents` | `artifacts/agents/` |
| `src/skills/` | `artifacts/skills/` |
| `kinds/` | `artifacts/kinds/` |
| `src/artifacts_os/ai/claude/skills/` | `artifacts/skills/` |

The trailing slash is normalised in `Book.dest` (always
present). The resolved default goes through the same
vault-escape guard as an explicit `dest:` (D25).

**Rationale.** Using the basename of `src` rather than `book.name`
matches the recurse-walker's directory shape (D26) for the
common case where books are named after their content type.
For pathological cases (e.g., a book named `core-agents`
sourcing `artifacts/agents/`), the operator who wants the
canonical mirror at `artifacts/core-agents/` can still set
`dest:` explicitly.

### D38 — Validation order in manifest parsing

**Decision.** Manifest parsing applies these checks in order
(extending [[s0029]] § 3.2). Each rule that fails raises
`ManifestError` with an actionable message and stops parsing:

1. `version: 1` (D17 — unchanged; no bump per D28).
2. `distro.name` present and non-empty (D2 — unchanged).
3. `books` is a non-empty list (D2 — unchanged).
4. For each book entry:
   a. Required `name`, `src` (D2 — `dest` is no longer
      required at this stage; D28).
   b. `src` is relative, no `..` (D2 — unchanged).
   c. If `dest:` is set: relative, no `..`, vault-escape guard
      (D25 — unchanged), **plus canonical-only check** —
      `dest:` must resolve under `artifacts/` or
      `ManifestError` ("`book '<name>' dest: '<path>' is not
      under 'artifacts/'. dest: is canonical-only — move
      tool-specific paths to promote:`").
   d. If `dest:` is **not** set: compute default per D37; the
      computed default is *not* re-validated against the escape
      guard (it's always under `artifacts/`).
   e. If `promote:` is set: parse string or object per D29;
      `promote.target` goes through the same vault-escape guard
      as `dest:` (but **not** the canonical-only constraint —
      `promote:` exists precisely to land outside `artifacts/`).
   f. `files:` vs `recurse:` mutual exclusion (D26 —
      unchanged).

Validation is strictly fail-fast. The `Manifest` dataclass
gains no `warnings` field — there is no non-fatal feedback
path under the tightened v1 semantics (the lenient
back-compat warning from an earlier draft is removed).

**Rationale.** Keeping all validation in the parser (rather
than scattering it across `pull_book` / `promote_book`) means a
single `parse_manifest(data)` call returns either a valid
`Manifest` or an actionable error. With no lenient path
(D28), every shape constraint is a hard error — simpler,
more predictable, and forces distros to migrate cleanly
rather than accumulate warnings.

### D39 — `artbook.promotion` and `artbook.promote_mode` settings

**Decision.** `ArtbookSettings` is extended with two optional
fields:

```python
@dataclass(frozen=True)
class ArtbookSettings:
    distro_url: str | None
    promotion: str            # 'enabled' (default) | 'disabled'
    promote_mode: str | None  # None (use distro/manifest default) | 'symlink' | 'copy'
```

YAML:

```yaml
artbook:
  distro_url: https://github.com/my-org/artbook-defaults
  promotion: disabled              # opt out persistently (D31)
  promote_mode: copy               # override default mode for this vault (D30)
```

Validation rules (raised at `from_base` time as
`SettingsError`):

- `promotion` must be `enabled` or `disabled` (case-sensitive).
- `promote_mode` must be `symlink` or `copy` (case-sensitive)
  or absent.

Defaults: `promotion="enabled"`, `promote_mode=None`.

**Rationale.** Two narrow, named fields are more discoverable
than a single `promote: {...}` table. They follow the
established `artbook.distro_url` shape (one key per concern).
The `promote_mode: None` sentinel cleanly expresses "no
per-vault override; defer to per-promotion / per-distro
default."

### D40 — D2 fallback uses canonical + promote (Q8)

**Decision.** [[t0167]]'s D2 fallback (no-distro init) installs
the bundled `artifacts-os` skill via the same canonical +
promote pipeline as a distro book — not direct-to-`.claude/`.

**Updated D2 behaviour.**

1. Step 1 (settings tier) writes `artifacts.yaml` as today.
2. `_install_bundled_skill` is rewritten to:
   - Copy the bundled skill resource to
     `artifacts/skills/artifacts-os/SKILL.md` (canonical).
   - Run `promote_book` against a **synthetic Book**
     constructed in-memory with:
     ```python
     Book(
         name="artifacts-os-skill",
         src="(bundled)",
         dest="artifacts/skills/",
         promote=Promote(target=".claude/skills/", mode="symlink"),
         recurse=True,
         files=None,
     )
     ```
     The synthetic book is **not** persisted to any manifest;
     it exists only inside the init code path so the promotion
     pipeline can be reused.
3. State-file tracking (D32) records the bundled skill's
   promotion under `promotions["artifacts-os-skill"]`. A
   subsequent `artifacts init --distro <url> --force` that
   pulls a `skills` book from the distro will replace this
   entry (the synthetic book name will not collide with a
   distro-shipped `skills` book; the synthetic-book entry's
   stale targets get cleaned up correctly on the first
   distro-driven pull).

**Rationale.** Uniformity: one and only one path for content
that ends up in `.claude/`. Authoring a special-case write
path inside `init.py` would re-duplicate the D19 atomic-write
+ promotion logic already factored out into `placement.py` and
the new `promote_book`. The synthetic-book wrapper is the
smallest possible shim that lets the promotion pipeline see a
single source — the bundled skill resource — without inventing
an alternate "skip the canonical step" branch.

**Rejected alternatives.**

- *Keep D2 special (direct write to `.claude/skills/`).*
  Duplicates promotion logic and breaks the principle that
  `artifacts/skills/` is the canonical landing for skills.
  Worse: `artifacts list --kind skill` (when that view lands)
  returns nothing on a fresh D2 install.
- *D2 writes canonical only, no promote.* Leaves Claude with
  no skill installed — defeats the whole point of D2 (give
  Claude enough to teach the user how to grow the vault).

---

## 4. Worked Transcripts

Three end-to-end scenarios. All three assume a fresh consumer
project initialised against the artifacts-os distro (post-D40
migration) and `artbook.distro_url` set in `artifacts.yaml`.

### 4.1 Transcript A — `book pull agents` with promote

`artbook.yaml` (the artifacts-os distro, post-migration; see
§ 4.3 for the full migration):

```yaml
version: 1
distro:
  name: artifacts-os
  description: Default agents shipped by artifacts-os for consumers of the library.
books:
  - name: agents
    src: artifacts/agents/
    # dest omitted — canonical default = artifacts/agents/
    promote: .claude/agents/
    description: Default agent specs (architect, developer, researcher, etc.).
```

Consumer `artifacts.yaml`:

```yaml
artbook:
  distro_url: https://github.com/artifacts-os/artifacts-os
```

Command:

```bash
$ artifacts book pull agents
```

Output:

```
Cloning https://github.com/artifacts-os/artifacts-os@main…
Loaded distro 'artifacts-os' at f3a1c0.
Pulling book 'agents' (10 items)…

  Canonical writes (artifacts/agents/):
    + architect.md
    + author.md
    + developer.md
    + devrel.md
    + integrator.md
    + product-manager.md
    + project-manager.md
    + qa.md
    + researcher.md
    + security-engineer.md

  Promotion (.claude/agents/, symlink → ../../artifacts/agents/):
    + architect.md
    + author.md
    + developer.md
    + devrel.md
    + integrator.md
    + product-manager.md
    + project-manager.md
    + qa.md
    + researcher.md
    + security-engineer.md

Wrote 10 canonical files, 10 promotion targets. Done.
State: artifacts/.artbook/state.json updated.
```

Vault tree after:

```
<vault>/
├── artifacts.yaml
├── artifacts/
│   ├── .artbook/
│   │   └── state.json
│   └── agents/
│       ├── architect.md
│       ├── developer.md
│       └── …
└── .claude/
    └── agents/
        ├── architect.md → ../../artifacts/agents/architect.md
        ├── developer.md → ../../artifacts/agents/developer.md
        └── …
```

`state.json` after:

```json
{
  "version": 1,
  "promotions": {
    "agents": {
      "mode": "symlink",
      "target_root": ".claude/agents/",
      "files": [
        ".claude/agents/architect.md",
        ".claude/agents/author.md",
        ".claude/agents/developer.md",
        ".claude/agents/devrel.md",
        ".claude/agents/integrator.md",
        ".claude/agents/product-manager.md",
        ".claude/agents/project-manager.md",
        ".claude/agents/qa.md",
        ".claude/agents/researcher.md",
        ".claude/agents/security-engineer.md"
      ]
    }
  }
}
```

Verification:

```bash
$ artifacts list --kind agent
ID  Name              Status
─── ────────────────  ──────
…   architect         (no status — kind agent is non-numbered)
…   developer
…   …

$ ls -la .claude/agents/architect.md
.claude/agents/architect.md -> ../../artifacts/agents/architect.md
```

Both the artifacts CLI and Claude Code see the same content.

### 4.2 Transcript B — pull with promotion disabled

Setup: same as 4.1, but the consumer has explicitly opted out
of promotion. Two equivalent ways to express this.

**Variant B1 — per-vault setting (persistent).**

Consumer `artifacts.yaml`:

```yaml
artbook:
  distro_url: https://github.com/artifacts-os/artifacts-os
  promotion: disabled
```

Command:

```bash
$ artifacts book pull agents
```

Output:

```
Cloning https://github.com/artifacts-os/artifacts-os@main…
Loaded distro 'artifacts-os' at f3a1c0.
Pulling book 'agents' (10 items)…

  Canonical writes (artifacts/agents/):
    + architect.md
    + …                                          # (10 files)

  Promotion: skipped (artbook.promotion: disabled in artifacts.yaml).

Wrote 10 canonical files, 0 promotion targets. Done.
```

Vault tree after (note: no `.claude/agents/`):

```
<vault>/
├── artifacts.yaml
└── artifacts/
    └── agents/
        ├── architect.md
        └── …
```

`state.json` is not written (no promotion ran).

**Variant B2 — per-invocation flag (one-off).**

Same consumer `artifacts.yaml` as 4.1 (no `promotion:` key —
defaults to enabled), but the operator wants a canonical-only
pull for this one invocation:

```bash
$ artifacts book pull agents --no-promote
```

Output:

```
Cloning https://github.com/artifacts-os/artifacts-os@main…
Loaded distro 'artifacts-os' at f3a1c0.
Pulling book 'agents' (10 items)…

  Canonical writes (artifacts/agents/):
    + architect.md
    + …                                          # (10 files)

  Promotion: skipped (--no-promote on command line).

Wrote 10 canonical files, 0 promotion targets. Done.
```

Subsequent invocations without `--no-promote` re-enable
promotion against the current canonical state (D32: state file
is untouched while `--no-promote` is in effect, so the next
promotion-enabled pull behaves as if the previous run promoted
the same files).

### 4.3 Transcript C — artifacts-os distro `artbook.yaml` migration

The artifacts-os repo's own `artbook.yaml` is the worked
migration example. Before / after diff:

**Before** (today, v1 with non-canonical `dest:`):

```yaml
version: 1
distro:
  name: artifacts-os
  description: Default agents shipped by artifacts-os for consumers of the library.
books:
  - name: agents
    src: artifacts/agents/
    dest: .claude/agents/                # ← non-canonical
    description: Default agent specs (architect, developer, researcher, etc.).

  - name: commands
    src: src/artifacts_os/ai/claude/commands/
    dest: .claude/commands/              # ← non-canonical
    description: Slash commands for artifacts CLI.

  - name: skills
    src: src/artifacts_os/ai/claude/skills/
    dest: .claude/skills/                # ← non-canonical
    description: Skills that teach Claude how to use artifacts-os.
    recurse: true

  - name: kinds
    src: artifacts/kinds/
    dest: artifacts/kinds/               # ← already canonical
    description: Standard artifact kinds (task, note, spec, research, agent).
    recurse: true
```

**After** (post-migration, v1 with canonical landing + promote — same `version: 1`, tightened semantics):

```yaml
version: 1
distro:
  name: artifacts-os
  description: Default agents shipped by artifacts-os for consumers of the library.
books:
  - name: agents
    src: artifacts/agents/
    # dest omitted — canonical default = artifacts/agents/
    promote: .claude/agents/
    description: Default agent specs (architect, developer, researcher, etc.).

  - name: commands
    src: src/artifacts_os/ai/claude/commands/
    dest: artifacts/commands/            # explicit — src basename differs from canonical name
    promote: .claude/commands/
    description: Slash commands for artifacts CLI.

  - name: skills
    src: src/artifacts_os/ai/claude/skills/
    dest: artifacts/skills/              # explicit — same reason
    promote: .claude/skills/
    description: Skills that teach Claude how to use artifacts-os.
    recurse: true

  - name: kinds
    src: artifacts/kinds/
    # dest omitted — canonical default = artifacts/kinds/
    # promote omitted — kinds are canonical-only (no Claude target)
    description: Standard artifact kinds (task, note, spec, research, agent).
    recurse: true
```

Migration notes per book:

| Book | Change |
|---|---|
| `agents` | `dest: .claude/agents/` removed → defaults to `artifacts/agents/`. `promote: .claude/agents/` added. Pulled files now land at both `artifacts/agents/` (canonical) and `.claude/agents/` (promote symlink). |
| `commands` | `src` is `src/artifacts_os/ai/claude/commands/`; the canonical default would be `artifacts/commands/` per D37. Explicit `dest: artifacts/commands/` is identical to the default — kept for clarity. `promote: .claude/commands/` added. |
| `skills` | Same pattern. `dest: artifacts/skills/` explicit; `promote: .claude/skills/` added. |
| `kinds` | `dest: artifacts/kinds/` was already canonical; the migration drops it (default suffices) but no `promote:` is added — kinds have no tool-specific consumer (D29: absent `promote` ⇒ canonical-only). |

A first-time pull against the post-migration distro from a
fresh vault writes 4 canonical directories and 3 promotion
target directories. A re-pull is idempotent: no canonical
content changes hash; symlink promotions are recreated
identically; `state.json` is rewritten with the same content
(byte-identical except for the timestamp inside the artbook
state writer — see § 6).

---

## 5. Migration — Files That Change

Comprehensive list. Reviewer reads § 1.4 for the one-line
summary; this section is the implementation cheat-sheet.

### 5.1 Source code

| Path | Change |
|---|---|
| `src/artifacts_os/artbook/manifest.py` | `_REQUIRED_VERSION` stays `1` (no bump per D28). `_parse_book`: make `dest` optional + apply D37 default; **add canonical-only check on explicit `dest:` (must resolve under `artifacts/`)**; add `_parse_promote` for string/object form (D29); emit `Promote` dataclass on the `Book`. No `Manifest.warnings` field — validation is strictly fail-fast (D38). |
| `src/artifacts_os/artbook/placement.py` | Add `promote_book(book, vault_root, *, mode_override, state)`; symlink + copy paths; idempotent re-write; per-file vault-escape guard on promote targets. |
| `src/artifacts_os/artbook/state.py` (new) | `read_state(vault_root) -> dict`, `write_state(vault_root, state)` atomic, schema-version handling. Hash helpers for copy-mode entries. |
| `src/artifacts_os/artbook/pull.py` | `pull_book` calls `promote_book` after canonical writes (D36); returns extended `PullReport` (D33). Add `promotion_skipped_reason` plumbing. |
| `src/artifacts_os/artbook/settings.py` | `ArtbookSettings` gains `promotion` (default `"enabled"`) and `promote_mode` (default `None`). Validation per D39. |
| `src/artifacts_os/artbook/errors.py` | Add `PromotionError(ArtbookError)`; `SettingsError` (or extend existing) for D39 invalid values. |
| `src/artifacts_os/artbook/__init__.py` | Re-export `Promote`, `PromotedFile`, `PromotionReport`, `promote_book`. |
| `src/artifacts_os/cli/commands/book.py` | Add `--no-promote` to `pull` subparser; register new `promote` subverb (positional `BOOK`, `--clean`, `--dry-run`, `--json`). Render `PromotionReport` in default-table and JSON modes. |
| `src/artifacts_os/cli/commands/init.py` | Replace direct `.claude/skills/` write in `_install_bundled_skill` with a canonical-write + synthetic-book `promote_book` call (D40). Plumb `--no-promote` through the init flow. |
| `src/artifacts_os/cli/README.md` § book | Document `--no-promote` and the new `book promote` verb. |

### 5.2 Distro manifest

| Path | Change |
|---|---|
| `artbook.yaml` (repo root) | Migrate per § 4.3: `agents` / `commands` / `skills` drop their `.claude/…` `dest:` in favour of canonical `dest:` + explicit `promote:`; `kinds` simplifies. Update the leading comment block to point at this spec. |

### 5.3 Documentation

| Path | Change |
|---|---|
| `docs/artbook.md` | Add § Promotion (author guide): `promote:` field, string vs object form, default mode, the fallback rule. Add § Consumer behaviour: `--no-promote`, `artbook.promotion`, `artbook.promote_mode`. Add § Migration: how to convert a manifest authored against the pre-spec v1 shape using the worked example from § 4.3. **Rewrite the existing "Destination patterns" table** — `dest: .claude/…` is no longer valid (canonical-only per D28); replace those rows with the `(dest: artifacts/…, promote: .claude/…)` pattern. |
| `docs/init-flow.md` § "No-distro fallback" | Update D2 transcript to show the canonical write + promotion. |
| `docs/settings.md` | Document `artbook.promotion` and `artbook.promote_mode`. |
| `README.md` | One-line note in the artbook quickstart pointing at `promote:`. |

### 5.4 Tests

| Path | Change |
|---|---|
| `tests/artbook/test_manifest.py` | Optional-`dest` default per D37. **Explicit `dest:` outside `artifacts/` rejected with `ManifestError` (canonical-only).** `promote:` parsing — string, object, invalid mode, missing target, lists rejected. Vault-escape on promote target. Version gate still `1` (D17 unchanged). |
| `tests/artbook/test_placement.py` | `promote_book` symlink path. `promote_book` copy path. Symlink fallback when `os.symlink` raises. Idempotent re-promote. Stale-target cleanup (symlink + copy variants). User-modified target is preserved (skipped + recorded). |
| `tests/artbook/test_state.py` (new) | State-file round-trip. Backwards-compat read (string-form entries from older state). Hash record for copy mode. Atomic write. |
| `tests/artbook/test_pull_integration.py` (new) | End-to-end pull-with-promote on a tmp distro fixture. Pull with `--no-promote`. Pull with `artbook.promotion: disabled`. Re-pull idempotency. Pull after upstream removes an item → stale promotion target cleaned. |
| `tests/cli/test_book.py` | `--no-promote` on `pull`. New `book promote` verb (positional + `--clean` + `--dry-run` + `--json`). |
| `tests/cli/test_init.py` | D2 fallback writes both `artifacts/skills/artifacts-os/SKILL.md` and `.claude/skills/artifacts-os/SKILL.md` (and the state file records the synthetic book). |

### 5.5 Spec-side

| Path | Change |
|---|---|
| `openstation/specs/s0029-artbook-mvp-distribution-model.md` | Add a Revision note at the top pointing at this spec (`s0031`): "Schema stays at `version: 1`; v1 semantics tightened in place. D8 / D25 strengthened — `dest:` is canonical-only (must resolve under `artifacts/`); `dest:` is now optional with a canonical default. New decisions D28–D40 add the `promote:` field and the post-pull promotion pipeline. D17 / D24 / D26 / D27 carry over unchanged. No back-compat shim; the artifacts-os distro is migrated in the same commit." |
| `openstation/specs/s0030-books-driven-init-flow.md` | Add a Revision note that D2 (no-distro fallback) is amended by `s0031` D40 to flow through canonical + promote. |

---

## 6. Implementation Sub-Task Breakdown

Suggested decomposition for `project-manager` to create from
after this spec is approved. Five sub-tasks, sized so each
ships as a single coherent PR. Sequence runs roughly top-to-
bottom — earlier sub-tasks block later ones at the boundaries
called out.

### S1 — Manifest schema: canonical-only `dest:`, `promote:`

**Scope.**

- `manifest.py` — D28 (canonical-only `dest:`, optional with
  default) + D29 + D37 + D38; new `Promote` dataclass.
  Version stays `1`.
- `__init__.py` re-exports.
- `tests/artbook/test_manifest.py` updates.
- Revision note on `openstation/specs/s0029-artbook-mvp-distribution-model.md`.

**Verification.**

- `version: 1` manifest with no `dest:` resolves canonical
  default per D37.
- `version: 1` manifest with `dest:` outside `artifacts/`
  (e.g., `.claude/agents/`) raises `ManifestError` —
  canonical-only message.
- `promote:` accepts string and object forms; rejects invalid
  mode, list-of-promotions, malformed target.
- Existing valid v1 manifests with `dest:` already under
  `artifacts/` continue to parse.

**Blocks.** S2 (placement needs the new `Book.promote` shape).

### S2 — Placement + state: `promote_book`, state file, idempotency

**Scope.**

- `placement.py` — `promote_book`, symlink + copy paths,
  per-file vault-escape, fallback handling.
- `state.py` (new) — read/write, atomic, hash helpers.
- `pull.py` — call `promote_book` after canonical writes;
  extended `PullReport` (D33); promotion failure semantics
  (D36).
- `tests/artbook/test_placement.py` + `tests/artbook/test_state.py`.

**Verification.**

- Symlink mode emits relative links pointing at the canonical
  tree.
- Copy mode writes hash-equal files; stale cleanup respects
  the hash record.
- Symlink fallback on filesystems that raise `OSError` on
  `os.symlink`.
- State file round-trips; absent state file is treated as empty
  promotions map.
- Re-pull is idempotent; removed-upstream item is cleaned up.

**Blocks.** S3 (CLI surface), S5 (init D2).

### S3 — CLI: `--no-promote` and `book promote` verb

**Scope.**

- `cli/commands/book.py` — `--no-promote` on `pull`; new
  `promote` subverb (positional, `--clean`, `--dry-run`,
  `--json`).
- `settings.py` — `ArtbookSettings.promotion`,
  `ArtbookSettings.promote_mode` (D39).
- `tests/cli/test_book.py`.
- `cli/README.md` section update.

**Verification.**

- `book pull --no-promote` skips promotion and records the
  reason on the report.
- `book promote AGENTS` re-runs promotion without cloning;
  `--clean` rebuilds state.
- Setting `artbook.promotion: disabled` skips promotion on
  every pull; flag overrides.
- Setting `artbook.promote_mode: copy` flips the default; the
  per-promotion override still wins.

**Blocks.** None (S4 is doc-only; S5 only depends on S2).

### S4 — Documentation

**Scope.**

- `docs/artbook.md` — § Promotion (author), § Consumer
  behaviour, § Migration (the worked § 4.3 example).
- `docs/init-flow.md` — updated D2 transcript.
- `docs/settings.md` — new keys.
- `README.md` — one-line pointer.

**Verification.**

- Reviewer can produce a working `artbook.yaml` with `promote:`
  by reading `docs/artbook.md` alone.
- The migration section walks an operator through converting a
  manifest authored against the pre-spec v1 shape (`dest:
  .claude/…`) to the new canonical + promote shape without
  consulting this spec.

**Blocks.** None.

### S5 — Distro migration (artifacts-os) + init D2 fallback

**Scope.**

- `artbook.yaml` (repo root) migration per § 4.3.
- `cli/commands/init.py` — D40 D2 fallback rewrite (synthetic
  book + `promote_book`).
- `tests/cli/test_init.py` + `tests/artbook/test_pull_integration.py`.

**Verification (end-to-end on a clean vault).**

- `artifacts init -y` (no distro) writes both
  `artifacts/skills/artifacts-os/SKILL.md` (canonical) and
  `.claude/skills/artifacts-os/SKILL.md` (symlink → canonical).
  `state.json` records the synthetic book.
- `artifacts init --distro <local-clone-of-this-repo> -y`
  produces `artifacts/agents/` + `.claude/agents/` (symlinked),
  same for commands and skills, and canonical-only `artifacts/kinds/`.
- `artifacts list --kind agent` returns 10 agents on the same
  fresh vault.
- A second `book pull agents` is byte-for-byte idempotent.

**Blocks.** None — final integration sub-task.

---

## 7. Out of Scope (Deferred)

Restated from the task spec for the reviewer's reference. None
of these may surface in the implementation sub-tasks:

- Multi-tool distros (Cursor, Codex). Deferred per L4; handled
  by writing more distros, not CLI changes.
- Transformers / shape conversion (e.g. Codex's `AGENTS.md`).
- Auto-promotion of user-authored content created via
  `artifacts create` (D35). Follow-up spec when needed.
- Per-vault override of an individual promotion target (e.g.
  consumer redirects `agents` promote from `.claude/agents/`
  to `.cursor/agents/`). Achievable today by writing a
  Cursor-flavoured distro per L4.
- List-form `promote:` (multiple targets per book). Deferred
  per D29.
- Re-architecting `kinds` to be tool-aware.
- Manifest version bump (v1 → v2). The schema change is
  delivered as a strict tightening of v1's semantics in place
  (D28). A future spec may bump to v2 when v1 has shipped
  publicly and the next set of changes is genuinely
  back-incompatible against an installed base.

## 8. Open Risks

- **Stale state file across vault relocations.** If an operator
  moves the vault directory, relative symlinks survive but the
  state file's paths are vault-relative and survive too.
  Verified by construction (no absolute paths anywhere in
  `state.json`).
- **Race between `book pull` and a concurrent
  `artifacts create`.** Both write under `artifacts/…`; the
  current `core` write path is atomic (D19 / D9). No new race
  introduced here, but the state file is **not** locked — two
  concurrent `book pull` invocations could clobber each
  other's `state.json`. Acceptable for the MVP (the operator
  doesn't run two `book pull`s in parallel against the same
  vault), but worth a follow-up note in `docs/artbook.md`.
- **Symlink chain pointing at a deleted canonical.** If a
  consumer deletes a file under `artifacts/agents/` after a
  pull, the `.claude/agents/` symlink becomes broken. This is
  by design — the canonical is the source of truth; deletion
  there should be visible at the promotion target.
  `artifacts book promote --clean` recovers.
