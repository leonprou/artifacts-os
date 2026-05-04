---
agent: architect
created: 2026-05-02
id: s0017
kind: spec
name: artifact-kinds-discovery-mechanism
status: approved
task: '[[t0073-spec-artifact-kinds-discovery-mechanism]]'
---

# Artifact Kinds Discovery Mechanism — L1 Catalogue

Sub-spec of [[s0002-artifacts-os-architecture]]. Defines the **L1
catalogue** of the artifact-kind discovery mechanism — the always-on
surface that lists every registered kind with a one-line description so
an agent (or human) can pick the right kind when creating a new
artifact.

L2 (per-kind detail) and L3 (template / playbook content) are **out of
scope for this spec** and are sketched only as next steps (§ 11). The
work below is what consumers can rely on after the implementation lands;
the deeper layers will be locked in a follow-up spec once L1 is real
and L2 use-cases concretise.

**Scope: design only.** Implementation is filed as a follow-up task
once this spec is approved (see § 12). The locked decisions in
[[n0005-artifact-md-kind-folders-for]] (D1–D7) and the per-kind folder
layout established by [[artifacts/kinds/note/ARTIFACT.md]] are
**inputs**, not subjects of redesign.

## 1. Background and Cross-References

- **Task brief** — [[t0073-spec-artifact-kinds-discovery-mechanism]].
  This spec covers L1; L2/L3 are deferred per the user-driven scope
  reduction recorded in § 13.
- **Primary research** — [[r0002-claude-skills-design-reference]]
  documents the Claude Skills three-level disclosure model. R1, R2,
  R6, R7 (L1-relevant) are locked here; R3, R4, R5, R8 are noted but
  fully addressed only by the follow-up L2 spec (§ 10).
- **Brainstorm origins** — [[n0004-improve-create-command]] (10
  themes, 4 designs) and [[n0005-artifact-md-kind-folders-for]] (D1–D7
  locked decisions).
- **v1 exemplar** — [[artifacts/kinds/note/ARTIFACT.md]] shows the
  hybrid frontmatter + `## How to use` + `## Skeleton` shape. This
  spec consumes its frontmatter, not its body.
- **Existing loader** — `src/artifacts_os/core/registry.py`
  `_load_vault_kinds`. The mechanism extends this loader; no new
  walker is introduced.
- **Authoring guide** — [`docs/adding-a-kind.md`](../../docs/adding-a-kind.md)
  cross-referenced once L1 lands.

## 2. Goals and Non-Goals

### 2.1 Goals (this spec)

1. Lock the **L1 catalogue surface**: what consumers see when they
   ask "what kinds exist?".
2. Lock the **`description:` selection signal contract** — required,
   bounded, third-person, what + when.
3. Lock the **source-file split**: machine-readable schema in
   `kind.json`; human/agent-facing prose in `ARTIFACT.md` frontmatter.
4. Lock the **L1 fallback semantics** for missing `ARTIFACT.md` and
   missing/invalid `description`.
5. Define the **Python-API + CLI surface for L1**. CLI is a thin
   printer over a single core function.
6. Make L1's evolution **backwards-compatible** with the existing
   `artifacts kinds` command and its JSON output.

### 2.2 Non-Goals

- **L2 (per-kind detail).** Paths, variants, playbook lists, and
  schema-property summaries are **deferred** to a follow-up spec.
  Consumers cannot rely on `kinds show <name>` or any L2 surface
  until that spec ships.
- **L3 (template / playbook content).** No `read_template` or
  `read_playbook` API in v1.
- **`/artifacts.create` integration.** Defers to L2; the slash command
  keeps its current behaviour.
- **`ARTIFACT.md` body grammar.** Frontmatter contract is locked
  here; body shape is inherited from the v1 exemplar without
  amendment.
- **Implementation.** A follow-up task implements this spec.
- **Cross-kind composition, versioning, authoring lints.** Out of
  scope for L1 (and likely for L2 too — see § 11).

## 3. Locked Decisions Summary

| ID | Decision |
|----|----------|
| D1 | L1 carries `name + description` only; never reads `ARTIFACT.md` body or any playbook file |
| D2 | `description:` lives in `ARTIFACT.md` frontmatter (not `kind.json`) — sources stay split |
| D3 | `description:` is required, ≤ 1024 chars, third-person, encodes *what* + *when* |
| D4 | Missing `description:` (absent or empty) → registration warning; kind still listed with `description=None` |
| D5 | Missing `ARTIFACT.md` → soft warning; kind still listed; `has_template=False` |
| D6 | Description voice is contract-only (documented), not lint-enforced — false-positive risk outweighs author-blocking |
| D7 | L1 cost budget: ≤ 200 tokens per kind |
| D8 | CLI is a thin printer over `KindCatalog.list_kinds()`; CLI ↔ Python-API parity is testable |
| D9 | `artifacts kinds` evolves additively — new `description` column, new JSON keys, no breakage |
| D10 | The redundant `/artifacts.kinds` slash command is retired; agents invoke `artifacts kinds` CLI directly. See § 11.6. |

L2/L3-specific decisions (triggers, playbook one-deep rule, variants
placement) are **noted directionally in § 10** but not locked here.

## 4. Layered Disclosure Model — High Level

The full model has three layers; this spec only locks L1.

| Layer | Loaded when | Carries | Locked? |
|---|---|---|---|
| **L1** | Every catalogue request | `name`, `description`, `has_template` | **Yes — this spec** |
| **L2** | Consumer focuses on one kind | Paths, variants, declared playbooks, schema-property summary | No — see § 11 |
| **L3** | Consumer reads template / playbook content | `ARTIFACT.md` body, `playbooks/<name>.md` content | No — see § 11 |

**Layer-isolation invariant for L1.** L1 invocations MUST NOT read
`ARTIFACT.md` body content or any playbook file. Only `kind.json` and
the **frontmatter** of `ARTIFACT.md` are touched. Verified by tests
(§ 9.1). This invariant is the spec's load-bearing claim — when L2 and
L3 land, none of them may be triggered transitively from L1.

## 5. L1 — Catalogue

| Aspect | Spec |
|---|---|
| **Trigger** | Any "list registered kinds" call: `artifacts kinds` (CLI), `KindCatalog.list_kinds()` (Python API), future TUI's kind picker. Agents invoke the CLI directly — see § 11.6 for the retirement of the redundant `/artifacts.kinds` slash command. Loaded eagerly at every catalogue request. |
| **Content** | One `KindCatalogEntry` per kind (§ 5.1). |
| **Source files read** | `artifacts/kinds/<name>/kind.json` (full schema — existing loader); `artifacts/kinds/<name>/ARTIFACT.md` **frontmatter only** (for `description`). |
| **Source files NOT read** | `ARTIFACT.md` body (no `## How to use`, no `## Skeleton`, no `## Variants/<name>`); `playbooks/*.md`. Zero reads of either. |
| **Output shape (CLI text)** | Aligned table: `name`, `dir`, `prefix`, `numbered`, `statuses`, **`description`** (truncated to one line, 60 chars max). |
| **Output shape (CLI JSON)** | Each entry is `{"name", "dir", "prefix", "numbered", "statuses", "description", "has_template"}`. |
| **Output shape (Python API)** | `list[KindCatalogEntry]`. |
| **Token budget per kind** | ≤ 200 tokens (D7). Empirically: name (≤ 64 chars) + description (≤ 1024 chars) + boolean ≈ 100–150 tokens worst case. |

### 5.1 `KindCatalogEntry`

```python
@dataclass(frozen=True)
class KindCatalogEntry:
    name: str                # e.g. "task"
    description: str | None  # ARTIFACT.md frontmatter `description`; None if absent
    has_template: bool       # True iff artifacts/kinds/<name>/ARTIFACT.md exists
```

`name` is the kind name (the file stem of `kind.json`).
`description` is the frontmatter field defined in § 6.
`has_template` is a presence boolean — `True` iff `ARTIFACT.md` exists
on disk under the kind folder. Consumers that want template content
will use a future L2 surface.

### 5.2 Why this minimum

The L1 surface answers exactly one question: **which kinds exist, and
which one fits my intent?** Adding paths, variants, or schema fields
to L1 inflates the always-loaded budget; r0002 § 2 recommends ~100
tokens/kind, and we hold ≤ 200 to leave room for the description
itself. Anything richer is L2.

## 6. Selection Signal — `description` Field

Lock per r0002 R1 (D3). The `description:` field in `ARTIFACT.md`
frontmatter is the **sole** L1 selection signal.

### 6.1 Contract

| Property | Rule |
|---|---|
| Required | yes — missing/empty triggers a registration warning (D4) |
| Length | ≤ 1024 characters (matches Claude Skills cap) |
| Voice | third-person ("Captures planning notes…", not "I capture…") |
| Content | encodes both **what** the kind is and **when** to choose it |
| Forbidden tokens | XML tags (`<…>`); reserved words `anthropic`, `claude` |
| Format | single string; no markdown formatting required |

### 6.2 Worked Example

From `artifacts/kinds/note/ARTIFACT.md` (already on disk):

```yaml
description: Body template for note artifacts — planning notes, brainstorm captures, meeting notes, decisions, and scratch work.
```

Reads as: *what* = "body template for note artifacts"; *when* =
"planning notes, brainstorm captures, meeting notes, decisions, and
scratch work". Both halves present.

### 6.3 Validation

Validation runs at registry load time (alongside `kind.json` schema
checks). Outcomes:

| Condition | Outcome |
|---|---|
| `description` absent | warning logged; `KindCatalogEntry.description = None` |
| `description` empty string | warning logged; `KindCatalogEntry.description = None` |
| `description` > 1024 chars | hard error; kind registration fails |
| `description` contains XML tag | hard error; kind registration fails |
| `description` contains reserved word | hard error; kind registration fails |
| `description` not third-person | not enforced mechanically — guidance lives in `docs/adding-a-kind.md` |

Voice is unenforced (D6) because reliable third-person detection
requires heuristics with high false-positive rates. The contract is
documented; authoring review catches violations.

## 7. Source File Contract

### 7.1 `kind.json` — schema source

Owns machine-readable validation rules: field types, enums, required
properties, storage directory, prefix, numbered/non-numbered. **No
human-facing prose.** Loader unchanged from the existing
`_load_vault_kinds` (`src/artifacts_os/core/registry.py`). Path during
the per-kind-folder transition: either
`artifacts/kinds/<name>.json` (legacy flat) or
`artifacts/kinds/<name>/kind.json` (folder form). Loader tries both;
the folder form takes precedence when both exist.

### 7.2 `ARTIFACT.md` frontmatter — prose source

Owns human/agent-facing metadata. **L1 reads only the frontmatter.**
The full frontmatter schema is shared with the future L2 spec; L1
consumes only `description` and the file's mere existence
(`has_template`). Other frontmatter fields (`name`, `applies_to`,
`placeholder_syntax`, `schema_version`, `variant_field`, `variants`,
`playbooks`) are validated at registration but not surfaced at L1.

| Field | Type | Required | L1 reads? | Notes |
|---|---|---|---|---|
| `name` | string | yes | — | matches the kind name; mismatch → hard error |
| `applies_to` | string | yes | — | matches the kind name; mismatch → hard error |
| `description` | string | yes (warning if missing) | **yes** | § 6.1 contract |
| `placeholder_syntax` | string | no | — | reserved for L2 |
| `schema_version` | int | no | — | reserved for L2 |
| `variant_field` | string | no | — | reserved for L2 |
| `variants` | list[string] | no | — | reserved for L2 |
| `playbooks` | list[string] | no | — | reserved for L2 |

### 7.3 Body content (L3)

Out of scope for L1. The CLI never prints body content (n0005 D6).

## 8. Surfaces

### 8.1 Python API

A new module `src/artifacts_os/core/kinds_catalog.py` exposes:

```python
class KindCatalog:
    """L1 discovery surface over a Registry. Layers L2/L3 will extend
    this class in a follow-up spec."""

    def __init__(self, registry: Registry, root: Path) -> None: ...

    def list_kinds(self) -> list[KindCatalogEntry]: ...
```

The class is sized for v1 (one method) but named to anticipate L2/L3
methods (`get_detail`, `read_template`, `read_playbook`) that the
follow-up spec will add. Consumers depending on L1 today will not
need to switch surfaces when L2 lands.

#### 8.1.1 Why Python API + CLI (not CLI-only)

Three consumer classes need parity:

1. **Slash commands** invoke the CLI via shell.
2. **Future TUI** runs in-process; subprocessing the CLI just to
   parse JSON back would double-encode every list.
3. **Future agent harness** loads `artifacts_os` as a library; same
   constraint as TUI.

The CLI is a thin renderer of `KindCatalog` outputs. Tests pin parity
(§ 9.5). This mirrors how `core.list_artifacts` underlies `artifacts
list`, the views module, and any future programmatic caller
([[s0014-core-unified-filter-api]] § 1).

#### 8.1.2 Dependency DAG

`core` already owns `Registry`. `KindCatalog` lives in `core` as well
(uses `Registry`, no peer imports). CLI and TUI depend on `core`.
Matches the locked DAG `core → views → cli, tui`.

### 8.2 CLI — `artifacts kinds`

Backwards-compatible: behaves like today's `artifacts kinds`, plus a
new `description` column.

```
$ artifacts kinds
┏━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ name     ┃ dir      ┃ prefix ┃ numbered ┃ statuses      ┃ description                       ┃
┡━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ note     │ notes    │ n      │ yes      │ (none)        │ Body template for note artifa…   │
│ task     │ tasks    │ t      │ yes      │ backlog, …    │ (no description)                  │
└──────────┴──────────┴────────┴──────────┴───────────────┴───────────────────────────────────┘
```

Existing flags preserved: `-q` / `--quiet` (one name per line, no
description column), `-j` / `--json` (per-kind metadata, gains
`description` and `has_template` keys).

### 8.3 Backwards Compatibility

| Change | Compat impact |
|---|---|
| New `description` column in default table | Additive; existing scripts that parse by column **name** keep working. Scripts that count columns must update — flagged in release notes. |
| New `description` and `has_template` keys in `-j` JSON | Additive (new keys); JSON consumers ignore unknown keys safely. |
| `-q` mode unchanged | One name per line; no description column ever. |
| Description column truncation | Cosmetic only; full string available via `-j`. |
| Legacy `artifacts/kinds/<name>.json` (flat file) coexists with new folder form | Loader tries both; folder form wins when both exist. Migration is a separate task — this spec does not force a flag day. |

No flags, output keys, or exit codes are removed.

## 9. Test Plan

Layer-isolation tests are the spec's primary verification surface.
The L1 invariant **must** survive into the L2 follow-up.

### 9.1 L1 layer-isolation (critical)

- `test_l1_does_not_read_artifact_md_body`: build a vault where one
  kind has an `ARTIFACT.md` whose body would trigger a parse error
  if read. Assert `list_kinds()` succeeds (monkey-patch `Path.read_text`
  / `open` to assert reads are bounded to the frontmatter byte
  range).
- `test_l1_does_not_read_playbooks`: vault with a kind declaring
  playbooks. `list_kinds()` runs — assert no `read_text` call against
  any `playbooks/*.md` path.
- `test_l1_returns_name_and_description`: happy-path field check.
- `test_l1_missing_description_is_soft`: kind without `ARTIFACT.md`
  description → entry returned with `description=None`, warning
  emitted to a captured handler.
- `test_l1_missing_artifact_md_is_soft`: kind whose folder lacks
  `ARTIFACT.md` → `has_template=False`, no hard error.

### 9.2 Description contract

- `test_description_xml_tag_rejected`
- `test_description_reserved_word_rejected`
- `test_description_length_cap_enforced` (1024 ok; 1025 errors)
- `test_description_third_person_voice_unenforced` — explicit negative
  assertion: a first-person description loads with no error (only
  guidance lives in docs).

### 9.3 Source file contract

- `test_artifact_md_frontmatter_only_read_at_l1`: instrument the YAML
  parser to record byte offsets; assert no read past the frontmatter
  delimiter.
- `test_legacy_flat_kind_json_still_loads`: `artifacts/kinds/foo.json`
  (no folder) still registers `foo` and surfaces with
  `has_template=False`.
- `test_folder_form_wins_on_collision`: both
  `artifacts/kinds/foo.json` and `artifacts/kinds/foo/kind.json`
  present → folder form is chosen; warning logged.

### 9.4 CLI / output

- `test_cli_table_includes_description_column`
- `test_cli_quiet_mode_unchanged`: `-q` output byte-for-byte unchanged
  from baseline (no description column).
- `test_cli_json_keys_additive`: `-j` continues to emit `name, dir,
  prefix, numbered, statuses`; new keys `description, has_template`
  present.

### 9.5 CLI ↔ Python API parity

- `test_cli_json_matches_python_api`: for each kind, `artifacts kinds
  -j` payload equals `[asdict(e) for e in catalog.list_kinds()]`
  modulo serialisation.

### 9.6 Token budget (optional)

- `test_l1_token_budget`: estimate token count of `list_kinds()`
  output for the in-repo vault; assert ≤ 200 tokens per kind.

## 10. r0002 Engagement Table

For each of the eight recommendations in
[[r0002-claude-skills-design-reference]] § "Recommendations for
t0073", this spec records `LOCK`, `LOCK-WITH-EDIT`, or `REJECT`.

| # | r0002 recommendation (one-liner) | Verdict | Rationale |
|---|---|---|---|
| R1 | `description:` in `ARTIFACT.md` frontmatter — required, ≤ 1024 chars, third-person, what+when | **LOCK** | Adopted as written (§ 6). |
| R2 | L1 = name + description only, ~100–200 tokens/kind, never loads body | **LOCK** | Adopted as written (§ 5). Layer-isolation tests pin the invariant. |
| R3 | L2 trigger = "agent has selected this kind" | **LOCK-WITH-EDIT** | Locked as the directional rule for the future L2 spec; detailed surface (data shape, CLI verb, error semantics) deferred to that follow-up. |
| R4 | L3 = declared playbooks loaded on-reference, one-deep rule | **LOCK-WITH-EDIT** | Locked directionally; detailed contract deferred to the L2/L3 follow-up. The one-deep rule is the spec's anti-nesting guardrail and will not be relaxed. |
| R5 | `variants:` is first-class; surface at L2 not L1 | **LOCK** | L1 explicitly does **not** surface variants (§ 5, § 7.2 — `variants:` reserved for L2). The full L2 surface is deferred. |
| R6 | Description in `ARTIFACT.md`; schema in `kind.json`; do not merge | **LOCK** | Adopted as written (§ 7). |
| R7 | Missing `ARTIFACT.md` = soft, missing declared playbook = hard, missing `description` = warning | **LOCK-WITH-EDIT** | L1-side rules (missing `ARTIFACT.md` = soft; missing `description` = warning) are locked here (D4, D5). The "missing declared playbook = hard" rule is L2-side and locked directionally only — final placement in the validation pipeline lands in the L2 spec. |
| R8 | Adopt evaluation-first authoring model | **LOCK-WITH-EDIT** | Adopted as a prescription for the **authoring guide** (`docs/adding-a-kind.md`), not for the discovery mechanism. r0002 itself flags R8 as authoring-guide material. |

No `REJECT`s. No silent drops.

## 11. Next Steps — L2, L3, and Slash-Command Integration

These are deferred from this spec by user-driven scope reduction
(§ 13). They are listed at the level needed to file a follow-up spec
task; the actual locking happens in that follow-up.

### 11.1 L2 — Per-kind detail (deferred to follow-up spec)

A future `artifacts kinds show <name>` (or equivalent) should expose
paths and metadata needed to scaffold an artifact body without a
filesystem walk. Directional shape:

- Paths: `schema_path`, `artifact_md_path` (or `None`), `storage_dir`.
- Frontmatter echo: `placeholder_syntax`, `schema_version`,
  `variant_field`.
- Declared `variants` (names only).
- Declared `playbooks` (names + paths + presence booleans).
- Schema-property summary.
- Loud-vs-silent rules: missing-but-declared playbook = hard error;
  variant_field declared but absent from `kind.json` properties =
  hard error; missing `ARTIFACT.md` = soft (mirrors L1).

### 11.2 L3 — Template / playbook content (deferred)

`KindCatalog.read_template(name)` and
`KindCatalog.read_playbook(name, playbook)`. Triggered only when a
consumer references a file by name. **One-deep rule**: a playbook
file may not reference another playbook (anti-nesting guardrail
inherited from r0002 R4 / Skills best practices).

### 11.3 `/artifacts.create` integration (deferred)

Once L2 lands, the slash command resolves the body template via the
L2 surface (paths only; CLI never prints body content per n0005 D6),
reads `ARTIFACT.md` directly via the path returned, and never walks
the filesystem. This unblocks the original `/artifacts.create`
improvement that motivated t0073.

### 11.4 Authoring-guide update (deferred)

`docs/adding-a-kind.md` should adopt R8 (evaluation-first authoring)
and cross-link this spec once it lands. Filed as a documentation
sub-task against the implementation work.

### 11.5 Per-kind `ARTIFACT.md` rollout (deferred)

Only `note` has an `ARTIFACT.md` today. `task`, `spec`, `research`,
`agent` will each need their own once authoring conventions
stabilise. Out of scope for the discovery work but adjacent — each
new template makes L1's `description` field visible in the catalogue.

### 11.6 Retire the `/artifacts.kinds` slash command (folded into L1 implementation)

The existing `/artifacts.kinds` slash command
(`src/artifacts_os/ai/claude/commands/artifacts.kinds.md`) is a thin
wrapper that instructs the agent to run `artifacts kinds`. Once L1
ships, agents should invoke the CLI directly — the slash-command
prompt is pure context overhead with no behavioural gain.

**Decision (D10):** the L1 implementation task **retires** the
`/artifacts.kinds` slash command:

1. Delete `src/artifacts_os/ai/claude/commands/artifacts.kinds.md`.
2. Update `src/artifacts_os/ai/claude/commands/artifacts.create.md`
   so its "If the user has not specified a kind, run
   `/artifacts.kinds` first…" instruction reads "…run `artifacts
   kinds` first…" (or, post-L2, the L2 detail command).
3. Grep the repository for other references to `/artifacts.kinds`
   and replace each with `artifacts kinds` (or remove if obsolete).

**Rationale.** Skill / slash-command bodies are loaded into context
when the command is invoked; for a single-CLI passthrough that's
~100+ tokens of pure ceremony per invocation. Direct CLI invocation
costs nothing beyond the command line itself. The Skills design
reference ([[r0002-claude-skills-design-reference]] § 8) calls out
"over-explaining what the model already knows" as an anti-pattern;
a slash command that says "run this CLI command" is exactly that.

**Scope of the retirement.** Affects only `/artifacts.kinds`. Other
slash commands (`/artifacts.create`, `/artifacts.show`, `/artifacts.list`)
remain — they encode non-trivial workflow logic (token translation,
edge cases, wikilink wrapping) that direct CLI invocation cannot
replicate without re-instructing the agent each time.

## 12. Implementation Notes (for the L1 follow-up task)

The follow-up implementation task scoped to **L1 only** covers:

1. New module `src/artifacts_os/core/kinds_catalog.py` exposing
   `KindCatalog` and `KindCatalogEntry`.
2. Extension of `Registry._load_vault_kinds` to read `ARTIFACT.md`
   frontmatter alongside `kind.json` and surface the new validation
   warnings/errors per § 6.3 and § 7.
3. CLI changes: `artifacts kinds` gains the `description` column;
   `-j` JSON gains `description` and `has_template` keys.
4. Loader handles both `artifacts/kinds/<name>.json` (legacy) and
   `artifacts/kinds/<name>/kind.json` (folder form), folder wins on
   collision.
5. Tests per § 9.
6. Retire the `/artifacts.kinds` slash command per § 11.6 (D10):
   delete `src/artifacts_os/ai/claude/commands/artifacts.kinds.md`,
   update `artifacts.create.md` to invoke the CLI directly, grep for
   any stragglers.

Out of scope for the L1 implementation:

- Any `kinds show <name>` subcommand or L2 API method.
- Any `read_template` / `read_playbook` API method.
- Updates to `/artifacts.create` beyond the one-line CLI substitution
  in step 6 (the full template-loading integration is L2).
- Authoring-guide changes (separate documentation sub-task).

## 13. Scope History

- **First draft (review #1)** included full L1, L2, L3 specs plus
  `/artifacts.create` integration flow.
- **User feedback (2026-05-02):** "simplify to only the L1 in spec,
  L2 spec can be removed nearly all. just keep it in high level in
  next steps section."
- **Revision 2 (descope to L1)** narrows the locked surface to L1
  and pushes L2/L3/integration to § 11. Decisions D1–D9 are L1-only.
  The r0002 engagement table (§ 10) re-marks R3, R4, R7 (partial)
  as `LOCK-WITH-EDIT` to reflect that the L2/L3-relevant pieces are
  directional locks pending the follow-up spec.
- **Rationale** for the descope: shipping L1 unblocks the catalogue
  improvements (`description` column, kinds vs descriptions for
  agents) immediately while leaving L2's surface design open until a
  concrete consumer (`/artifacts.create`'s template loader) drives
  the requirements.
- **Revision 3 (retire `/artifacts.kinds` slash command).**
  User feedback (2026-05-02): "instead calling claude artifacts.kinds
  (line 73), we can just use the CLI command of artifact kinds. this
  will save tokens." Added decision **D10** (§ 3) and a new § 11.6
  spelling out the retirement. The CLI `artifacts kinds` is the only
  agent-facing surface; the slash command was a thin passthrough
  whose prompt body added ~100+ tokens per invocation with zero
  behavioural gain. Layered with r0002 R8's "over-explaining what
  the model already knows" anti-pattern.

## 14. Cross-References

- [[r0002-claude-skills-design-reference]] — primary research input.
- [[n0004-improve-create-command]] — original 10-theme problem framing.
- [[n0005-artifact-md-kind-folders-for]] — locked decisions D1–D7.
- [[t0073-spec-artifact-kinds-discovery-mechanism]] — task brief.
- [[s0002-artifacts-os-architecture]] — core module map (parent spec).
- [[s0011-cli-create-kind-aware-help]] — schema-driven `--help`
  generation; complementary to the discovery surface.
- [[s0014-core-unified-filter-api]] — precedent for "core API + CLI
  printer" pattern that this spec follows.
- [[artifacts/kinds/note/ARTIFACT.md]] — v1 `ARTIFACT.md` exemplar.
- `src/artifacts_os/core/registry.py` — extension point for loader.
- `src/artifacts_os/cli/commands/kinds.py` — CLI surface to extend.
- `src/artifacts_os/ai/claude/commands/artifacts.kinds.md` — slash
  command **deleted** by the L1 implementation per § 11.6 (D10).
- `src/artifacts_os/ai/claude/commands/artifacts.create.md` — touched
  only to swap the `/artifacts.kinds` reference for `artifacts kinds`;
  no other behaviour change in L1 (full template-loading integration
  is L2).
- [`docs/adding-a-kind.md`](../../docs/adding-a-kind.md) — authoring
  guide, cross-referenced once L1 lands.