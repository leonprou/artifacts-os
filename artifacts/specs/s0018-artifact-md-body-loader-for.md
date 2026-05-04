---
agent: architect
kind: spec
id: s0018
name: artifact-md-body-loader-for
status: approved
task: "[[t0085-spec-artifacts-create-consumes-artifact]]"
created: 2026-05-03
---

# ARTIFACT.md Body Loader for `/artifacts.create`

Sub-spec of [[s0017-artifact-kinds-discovery-mechanism]]. Locks the
contract for **how the `/artifacts.create` slash command consumes a
chosen kind's `ARTIFACT.md` body** so newly-created artifacts open
with a populated skeleton instead of an empty body. Consumes the L1
selection signal locked in s0017 and the per-kind `ARTIFACT.md`
files shipped under [[t0079-artifact-md-artifacts-ai-extension]];
does **not** widen L1 or introduce L2 / L3 surfaces.

**Scope: design only.** Implementation is filed as a follow-up task
once this spec is approved (see § 9). The locked decisions in
[[n0005-artifact-md-kind-folders-for]] (D1–D7) and
[[s0017-artifact-kinds-discovery-mechanism]] (D1–D10) are **inputs**,
not subjects of redesign.

## 1. Background and Cross-References

- **Task brief** — [[t0085-spec-artifacts-create-consumes-artifact]];
  parent epic [[t0084-wire-artifacts-create-to-artifact]]. The epic
  carries the user story; this spec freezes the slash-command
  contract that the implementation sub-task will build against.
- **Locked design (must read)**
  - [[s0017-artifact-kinds-discovery-mechanism]] § 4 (layer
    isolation), § 6 (description contract), § 7 (source-file
    split), § 11.3 (slash-command integration sketch). This spec is
    the realisation of § 11.3.
  - [[n0005-artifact-md-kind-folders-for]] D6 ("CLI is body-agnostic;
    templating is agent-layer concern") — the load-bearing
    constraint.
  - [[t0079-artifact-md-artifacts-ai-extension]] — parent programme
    that shipped the `ARTIFACT.md` files this spec consumes.
- **Brainstorm origins** — [[n0004-improve-create-command]] themes
  A (template floor too thin), B (type-blind scaffolding), H
  (repo-pattern crawler). This spec closes A, B, H by wiring the
  shipped skeletons into the create flow. Themes C, D, E, F, G, I,
  J remain open and are **out of scope**.
- **Existing surface** — `src/artifacts_os/ai/claude/commands/artifacts.create.md`
  (slash command being updated); `src/artifacts_os/cli/commands/create.py`
  (CLI; body is passed via `--body` / `--body-file -`);
  `src/artifacts_os/core/kinds_catalog.py` (L1 surface; resolves
  `has_template` and the kind's storage `dir`).
- **Concrete inputs** — the four shipped skeletons under
  `artifacts/kinds/{note,task,spec,research}/ARTIFACT.md` (lines
  166, 314, 331, 300 respectively).

## 2. Goals and Non-Goals

### 2.1 Goals

1. Lock the **placeholder substitution contract** the slash command
   applies to a chosen kind's `## Skeleton` body — which tokens
   are recognised, where their values come from, and what happens
   when a token is unresolved.
2. Lock the **variant selection rule** the slash command uses when
   an `ARTIFACT.md` declares `## Variants/<name>` blocks.
3. Lock the **fallback semantics** when the chosen kind ships no
   `ARTIFACT.md`.
4. Restate the **CLI ↔ slash-command boundary** (n0005 D6) so
   future refactors do not re-litigate it: the CLI stays
   body-agnostic; the slash command owns skeleton loading and
   substitution.
5. Lock the **token budget** the slash command incurs per
   invocation (single ARTIFACT.md read; skeleton size cap).
6. Lock the **test plan** the implementation task implements
   verbatim.
7. Preserve **backwards compatibility**: the `artifacts create`
   CLI surface is unchanged; agents not using the slash command
   continue to receive empty-body files.

### 2.2 Non-Goals

- **L2 (per-kind detail surface).** No `kinds show <name>`
  subcommand, no L2 API method. Deferred to s0017 § 11.1.
- **L3 (template / playbook content surface).** No
  `read_template` / `read_playbook` API. Deferred to s0017 § 11.2.
- **CLI body-loading.** `artifacts create` does not gain an
  "auto-load skeleton" flag. The body remains whatever is passed
  via `--body` / `--body-file`. (n0005 D6.)
- **`ARTIFACT.md` body grammar amendments.** The body shape
  inherited from the shipped skeletons (frontmatter +
  `## How to use` + `## Skeleton` + optional `## Variants/<name>`)
  is consumed as-is. This spec does not redesign the file format.
- **Authoring lints, cross-kind composition, schema versioning.**
  Out of scope.
- **Implementation.** Filed as a follow-up task once approved
  (§ 9).
- **n0004 themes C, D, E, F, G, I, J.** Themes A, B, H close under
  this epic; the rest are separate workstreams (see
  [[t0084-wire-artifacts-create-to-artifact]] § "Open design
  questions" item 6).

## 3. Locked Decisions Summary

| ID | Decision |
|----|----------|
| D1 | The slash command substitutes a fixed, closed set of structural placeholders — **`{{TITLE}}`** only in v1 — sourced from the positional title; all other `{{TOKEN}}` placeholders are left **literal** for the agent to fill in. (§ 4) |
| D2 | The placeholder grammar is `{{NAME}}`-shaped (uppercase ASCII identifier; matches the `placeholder_syntax` declared in shipped `ARTIFACT.md` frontmatter). Substitution is a single literal-string replace per token; no nested or escaping rules. (§ 4) |
| D3 | Unresolved placeholders are **left literal** in the emitted body. They are never dropped, errored, or replaced with empty strings. The agent fills them in on the first edit. (§ 4) |
| D4 | Variant selection uses the precedence: explicit `variant:<name>` slash-command token → `--type` token (when frontmatter declares `variant_field: type`) → fallback to default `## Skeleton`. **Title inference is rejected.** None of the four shipped kinds use variants in v1. (§ 5) |
| D5 | When the chosen kind has `has_template=False` (no `ARTIFACT.md`), the slash command falls back to **empty body** (today's behaviour) and surfaces a one-line note in agent context. No error; no synthesised stub. (§ 6) |
| D6 | The slash command reads exactly **one** file per invocation: `<vault-root>/artifacts/kinds/<chosen-kind>/ARTIFACT.md`. It does not enumerate other kinds, read playbooks, or read `kind.json` bodies. The chosen-kind path is resolved from `KindCatalog.list_kinds()` (L1 surface). (§ 7) |
| D7 | The CLI ↔ slash-command boundary is **frozen as in n0005 D6**: `artifacts create` stays body-agnostic. The slash command performs all skeleton loading and substitution, then pipes the resolved body to the CLI via `--body-file -`. (§ 7) |
| D8 | Skeleton size is bounded by an authoring guideline — **`## Skeleton` block ≤ 400 lines / ≤ 8 KB** — checked at authoring time, not enforced at load time. The four shipped skeletons (166–331 lines) fit comfortably. (§ 8) |
| D9 | The `artifacts create` CLI surface (flags, exit codes, stdout shape) is unchanged. The slash command's existing `$ARGUMENTS` token grammar gains no new tokens in v1. Agents that skip the slash command and call `artifacts create` directly continue to receive empty-body files. (§ 10) |

## 4. Placeholder Substitution Contract

### 4.1 Grammar

The shipped `ARTIFACT.md` files declare:

```yaml
placeholder_syntax: "{{NAME}}"
```

This is the **shape** of a placeholder, not the literal token name.
A placeholder is any occurrence of:

```
{{IDENTIFIER}}
```

where `IDENTIFIER` is one or more uppercase ASCII letters, digits,
or underscores (regex: `\{\{[A-Z][A-Z0-9_]*\}\}`). Tokens that do
not match this shape (e.g. `{{title}}`, `{{ name }}`, `${TITLE}`)
are not recognised and are passed through verbatim.

The `placeholder_syntax` frontmatter field is informational in v1
— the slash command pins the grammar above. A future kind
declaring a different syntax would require a frontmatter-validation
extension and an explicit migration; out of scope for v1.

### 4.2 Substitution table

The slash command substitutes exactly one structural token in v1:

| Token | Source | Notes |
|---|---|---|
| `{{TITLE}}` | The positional title from `$ARGUMENTS` (the same string passed to `artifacts create "<title>"`). | The substitution happens **after** `artifacts create` writes the file's frontmatter `title:` field; the value is the same string. Substitution is a literal `str.replace`, applied once per occurrence in the skeleton. |

All other `{{TOKEN}}` placeholders that appear in shipped skeletons
— `{{ONE_PARAGRAPH_SUMMARY}}`, `{{ROLE}}`, `{{CAPABILITY}}`,
`{{TASK_REF}}`, `{{YYYY-MM-DD}}`, etc. — are **left literal**.
Rationale: each of these placeholders demands agent reasoning
(content authoring, ref selection, date typing in the right
context) that a mechanical substitution cannot reliably perform.
The shipped skeletons explicitly cue the agent to fill them in via
HTML-comment guidance below each placeholder.

### 4.3 Why the v1 substitution set is so small

Three constraints converge:

1. **Avoid context-dependent traps.** `{{NAME}}` in `note`'s
   skeleton means a person's name in the Attendees section, not
   the artifact slug. Auto-substituting `{{NAME}}` would corrupt
   the body.
2. **Honour author intent.** Skeletons authored under
   `evaluation-first` (r0002 R8 / `docs/adding-a-kind.md`) treat
   placeholders as agent prompts. Mechanical substitution beyond
   `{{TITLE}}` undermines that intent.
3. **Keep the CLI ↔ slash-command boundary clean.** The CLI
   already populates frontmatter (id, slug, kind, parent,
   assignee, owner, created). Re-doing that work in the slash
   command for body purposes duplicates state and risks drift.

A future revision may add `{{KIND}}`, `{{TODAY}}`, or `{{PARENT}}`
once the substitution semantics are observed in production. Adding
them is **additive** and backwards-compatible (literal tokens
become resolved tokens).

### 4.4 Substitution algorithm

Pseudocode (executed by the agent in the slash command):

```
1. Resolve kind_path = catalog.get(kind).artifact_md_path  # L1 lookup
2. If has_template is False → emit empty body; STOP. (§ 6)
3. body = read_skeleton_block(kind_path)                    # § 5
4. body = body.replace("{{TITLE}}", positional_title)       # § 4.2
5. Pipe `body` to `artifacts create … --body-file -`.       # § 7
```

`read_skeleton_block` returns the markdown between `## Skeleton`
and the next H2 heading, **stripped of the surrounding code-fence
delimiters** (` ```markdown` … ` ``` `) so the result is plain
markdown rather than a fenced block. (See § 5.2 for the variant
case.)

### 4.5 Negative cases

| Case | Behaviour |
|---|---|
| Skeleton contains no `{{TITLE}}` | No substitution; body emitted verbatim. |
| Title contains characters meaningful to markdown (`*`, `_`, `[`, `]`) | Inserted verbatim; no escaping. The H1 title in the skeleton mirrors what the user typed. |
| Title is empty (CLI rejects this earlier) | Unreachable — the CLI errors before the slash command runs the substitution. |
| `placeholder_syntax` frontmatter declares a value other than `"{{NAME}}"` | Logged as a warning by the implementation; v1 ignores the declaration and uses the locked grammar. |

## 5. Variant Selection

### 5.1 Selection rule (precedence)

When an `ARTIFACT.md` body declares one or more `## Variants/<name>`
sub-sections, the slash command picks **at most one** variant body
to substitute. Precedence (highest first):

1. **Explicit `variant:<name>` token** in `$ARGUMENTS`. The named
   variant must match a `## Variants/<name>` heading in the chosen
   kind's `ARTIFACT.md` (case-insensitive on `<name>`); a mismatch
   aborts with a one-line agent-visible error naming the
   declared variants.
2. **`--type` token** (i.e. `type:<value>` in `$ARGUMENTS`)
   **iff** the frontmatter declares `variant_field: type`. The
   value selects the variant whose name matches `<value>`. A
   declared `variant_field` whose declared value does not match
   any `## Variants/<name>` heading aborts with the same error
   shape as case 1.
3. **Default `## Skeleton`.** If no token in cases 1 or 2 applies
   (or the `ARTIFACT.md` declares no variants at all), the slash
   command renders the body under the literal heading
   `## Skeleton`.

**Title inference is rejected.** Inferring a variant from the
user's title — e.g. matching keywords — is unreliable, surprising,
and untestable; it is explicitly disallowed.

### 5.2 Rendering the chosen body

The slash command extracts the markdown between the chosen heading
(`## Skeleton` or `## Variants/<name>`) and the next H2 heading.
Inside the section, an opening ` ```markdown ` fence and its
matching closing ` ``` ` are stripped so the resulting body is
plain markdown rather than a fenced code block.

Each shipped skeleton today wraps its body in ` ```markdown … ``` `
under `## Skeleton`; the implementation must tolerate skeletons
authored without the fence (treat the section content verbatim).

### 5.3 v1 status of variants

None of the four shipped `ARTIFACT.md` files (`note`, `task`,
`spec`, `research`) declares `## Variants/<name>` blocks today.
The variant rule is locked nonetheless because:

- It is the locked answer to one of t0085's required design
  questions (§ Goal item 2).
- It pre-empts re-litigation when the first kind ships variants.
- The implementation is trivial once the rule is locked.

The implementation task ships variant support as **dead code**
(no shipped consumer) but with full test coverage on a synthetic
fixture kind (§ 11.3). The first real consumer drives a
documentation update under `docs/adding-a-kind.md`.

## 6. Fallback — No `ARTIFACT.md`

When `KindCatalog.list_kinds()` reports `has_template=False` for
the chosen kind, the slash command:

1. Skips the skeleton-loading procedure entirely (no file read).
2. Invokes `artifacts create` without a `--body` / `--body-file`
   flag, producing an empty body — the **current** behaviour.
3. Surfaces a one-line note in agent context:
   `info: kind '<K>' has no ARTIFACT.md; created with empty body.`

**Why empty, not error.** The chosen kind is registered (it
appears in `artifacts kinds`); rejecting creation would be a
surprise regression for `agent` and any future kind that ships
without a body template. The L1 selection signal already tells
the agent the template state via `has_template`.

**Why empty, not a synthesised stub.** A generic stub (e.g.
`# {{TITLE}}\n\n(write body here)\n`) would produce the very
"template floor too thin" drift n0004 § Theme A targets. Authoring
an `ARTIFACT.md` for the kind is the right fix; the empty-body
fallback keeps the missing-template state honest until that
authoring lands.

## 7. CLI ↔ Slash-Command Boundary

This section restates n0005 D6 and s0017 § 4 in the form the
implementation must honour. The boundary is **load-bearing**: any
future refactor that proposes moving template handling into the
CLI must revisit this spec.

### 7.1 What the CLI does and does not do

| Concern | CLI (`artifacts create`) | Slash command (`/artifacts.create`) |
|---|---|---|
| Resolves kind from `--kind` / settings default / built-in fallback | **yes** | passes through |
| Assigns ID and slug | **yes** | — |
| Validates frontmatter against `kind.json` schema | **yes** | — |
| Writes the artifact file atomically | **yes** | — |
| Prints the canonical file stem on success | **yes** | surfaces to user |
| Reads `ARTIFACT.md` (frontmatter or body) | **never** | **yes — frontmatter via L1 (already today); body of chosen kind only** |
| Performs `{{TITLE}}` substitution | **never** | **yes** |
| Selects a variant | **never** | **yes** |
| Pipes body content via `--body-file -` | accepts the pipe | **yes — produces it** |

### 7.2 Files the slash command reads

The slash command's read set per invocation is:

- **Always:** the L1 catalogue (already free under the existing
  `artifacts kinds` flow). L1 itself reads only `kind.json` files
  and the **frontmatter** of every `ARTIFACT.md` (s0017 § 4) — no
  bodies. The slash command does not read `kind.json` bodies
  directly; it consumes the catalogue.
- **Conditionally (skipped when `has_template=False`):**
  exactly one body file:
  `<vault-root>/artifacts/kinds/<chosen-kind>/ARTIFACT.md`. The
  read range is the entire file; only the `## Skeleton` (or
  variant) section's markdown is used downstream.

The slash command **must not**:

- Read other kinds' `ARTIFACT.md` files (one chosen kind only).
- Read `playbooks/*.md` or any companion file declared in
  frontmatter `playbooks:` (deferred to L3).
- Re-read `kind.json` content beyond what the catalogue exposes.

### 7.3 How the body reaches the CLI

The slash command writes the resolved skeleton body to a transient
location (subprocess stdin via `--body-file -` is preferred; a
temp file is acceptable). The CLI's existing `--body-file` /
stdin behaviour is unchanged.

This pipe is the only data path between the two layers. The CLI
never queries the slash command, the catalogue, or the skeleton
file. This is the n0005 D6 invariant in operational form.

## 8. Token Budget

### 8.1 Per-invocation read cost

The slash command reads:

- The L1 catalogue (already paid for under `artifacts kinds`;
  bounded by s0017 D7 at ≤ 200 tokens per kind).
- One `ARTIFACT.md` body — bounded by § 8.2.

Total worst-case marginal cost beyond the existing flow: one file
read of ≤ 8 KB.

### 8.2 Authoring guideline — skeleton size cap

The `## Skeleton` (or `## Variants/<name>`) block in any single
`ARTIFACT.md` SHOULD be:

- **≤ 400 lines** of body markdown, and
- **≤ 8 KB** on disk for the section.

The cap is an authoring guideline, **not** a load-time gate
(false-positive risk; same rationale as s0017 D6 for the
description voice contract). The four shipped skeletons fit
comfortably:

| Kind | Total `ARTIFACT.md` lines | `## Skeleton` lines (approx.) |
|---|---|---|
| `note` | 166 | ~95 |
| `task` | 314 | ~190 |
| `research` | 300 | ~135 |
| `spec` | 331 | ~180 |

`docs/adding-a-kind.md` should reference the cap once this spec
ships (filed as a doc sub-task by the PM after approval — see
§ 9.3).

### 8.3 Why the slash command does not read the catalogue eagerly

A naïve implementation could read every shipped `ARTIFACT.md`
upfront to "warm" the agent context. This violates s0017 § 4's
layer-isolation invariant — L1 is exactly the surface that exists
to prevent exactly that. The slash command consumes L1's already
loaded catalogue (cheap) and follows the chosen-kind path through
to a single body read (also cheap).

## 9. Implementation Notes (for the follow-up task)

The follow-up implementation task scoped to **the slash command
update only** covers:

1. **Body-loading procedure** — extend
   `src/artifacts_os/ai/claude/commands/artifacts.create.md` with
   the placeholder-substitution and variant-selection algorithm
   from § 4.4 and § 5.1, including the fallback in § 6 and the
   exact files-read list in § 7.2.
2. **Resolution helper** — the slash command must compute the
   chosen kind's `ARTIFACT.md` path. Either expose
   `KindCatalogEntry.artifact_md_path` (small additive change to
   `core/kinds_catalog.py` — read off the existing
   `KindDef.has_template` resolution path in
   `core/registry.py` lines 153–159) **or** document the
   convention `<vault-root>/artifacts/kinds/<name>/ARTIFACT.md` as
   the authoritative path when `has_template=True`. The
   implementation task picks one; either choice satisfies this
   spec. Recommended: the additive `artifact_md_path` field, so
   the slash command never spells the layout convention itself.
3. **Tests** — § 11 below, dropped verbatim into the
   implementation task's test plan.
4. **No CLI changes.** `cli/commands/create.py` is read-only for
   this task. (D9.)

### 9.1 Out of scope for the implementation

- Any L2 / L3 surface.
- Any change to `artifacts create` flags, exit codes, or stdout.
- Authoring-guide updates beyond the size-cap reference (§ 8.2);
  filed as the documentation sub-task per § 9.3.
- New placeholder tokens beyond `{{TITLE}}` (additive future work;
  not blocked by this spec).

### 9.2 Implementation task to file (after approval)

The PM files **two** sub-tasks under
[[t0084-wire-artifacts-create-to-artifact]]:

- **Sub-task #2 (implementation):** updates
  `src/artifacts_os/ai/claude/commands/artifacts.create.md` per
  this spec. Test plan is § 11.
- **Sub-task #3 (documentation):** updates
  `docs/adding-a-kind.md` to (a) reference the size cap (§ 8.2),
  (b) document the `## Variants/<name>` block convention with a
  small example, and (c) cross-link this spec. Optional — if the
  implementation task surfaces no new authoring conventions
  beyond what is already captured here, the PM closes #3 with a
  rationale per t0084's verification.

## 10. Backwards Compatibility

| Surface | Impact |
|---|---|
| `artifacts create` flags / exit codes / stdout | **Unchanged.** D9. |
| `$ARGUMENTS` token grammar | **Additive only.** No tokens are required by v1. The slash command continues to accept all existing tokens; behaviour without `kind:<K>` (default-kind resolution) is unchanged. |
| Empty-body invocation paths | **Unchanged.** Direct CLI invocation, third-party callers, and any agent that skips the slash command continue to receive empty-body files. |
| `placeholder_syntax` frontmatter field | Read by the implementation but not enforced beyond a warning when the declared value differs from `"{{NAME}}"`. (§ 4.5.) |
| `variants` frontmatter field | No v1 consumer; reserved per s0017 § 7.2. The variant rule (§ 5) operates on body headings, not on this field. (A future spec may align them.) |

No flags, output keys, or exit codes are removed. No file format
changes.

## 11. Test Plan

The implementation task's test surface is split into four groups.
Each item names a property the developer can turn into a pytest
case.

### 11.1 End-to-end skeleton substitution (per shipped kind)

For each of the four shipped kinds (`task`, `spec`, `research`,
`note`):

- `test_e2e_<kind>_skeleton_substitutes_title`: invoking
  `/artifacts.create kind:<K> "<title>"` produces a file whose
  body equals the kind's `## Skeleton` block (markdown only, no
  code-fence delimiters) with **`{{TITLE}}` replaced by the
  positional title** and all other `{{TOKEN}}`s preserved
  literally.
- `test_e2e_<kind>_unresolved_placeholders_preserved`: a sample
  non-`{{TITLE}}` placeholder from each kind's skeleton (e.g.
  `{{ONE_PARAGRAPH_SUMMARY}}` for `note`,
  `{{TESTABLE_CRITERION}}` for `task`) appears verbatim in the
  emitted body.
- `test_e2e_<kind>_frontmatter_unchanged_by_substitution`: the
  CLI-written frontmatter (id, name, kind, status, created) is
  untouched by the body-substitution path.

### 11.2 Negative path — no `ARTIFACT.md`

- `test_e2e_kind_without_artifact_md_falls_back_to_empty_body`:
  using a synthetic kind with `kind.json` only (no `ARTIFACT.md`),
  invoking `/artifacts.create kind:<K> "<title>"` produces a file
  with an empty body (whitespace tolerated). No exception, no
  partial substitution, no synthesised stub.
- `test_e2e_kind_without_artifact_md_emits_info_note`: the
  one-line agent-visible note from § 6 is present in the slash
  command's output (or the equivalent agent-context surface).
- `test_e2e_kind_with_invalid_frontmatter_treated_as_missing`:
  an `ARTIFACT.md` whose frontmatter fails the s0017 § 6.3
  validation pipeline (e.g. XML tag, reserved word, > 1024
  chars) is treated as if the file were absent — empty-body
  fallback, no body read.

### 11.3 Variant selection (synthetic fixture)

A fixture kind ships a hand-crafted `ARTIFACT.md` with two
`## Variants/<name>` blocks (`alpha`, `beta`) and a default
`## Skeleton`.

- `test_variant_explicit_token_picks_variant`:
  `/artifacts.create kind:<F> variant:alpha "<title>"` emits the
  `alpha` block.
- `test_variant_type_token_picks_variant_when_variant_field_declared`:
  fixture frontmatter declares `variant_field: type`;
  `/artifacts.create kind:<F> type:beta "<title>"` emits the
  `beta` block.
- `test_variant_type_token_ignored_when_variant_field_absent`:
  fixture frontmatter omits `variant_field`;
  `/artifacts.create kind:<F> type:beta "<title>"` emits the
  default `## Skeleton`.
- `test_variant_unknown_name_aborts_with_named_variants`:
  `/artifacts.create kind:<F> variant:gamma` errors with a
  message naming `alpha`, `beta`.
- `test_variant_falls_back_to_default_skeleton_when_no_token`:
  `/artifacts.create kind:<F> "<title>"` emits the default block.
- `test_variant_title_inference_rejected`: a title containing
  the literal word `alpha` does **not** select the `alpha`
  variant; the default skeleton wins.

### 11.4 Layer isolation

These tests pin the s0017 § 4 invariant in the new flow.

- `test_slash_command_reads_only_chosen_kind_artifact_md`:
  instrument file reads (e.g. monkey-patch `Path.read_text` /
  `open`); invoke the slash-command body-loading procedure for
  one chosen kind in a vault with multiple `ARTIFACT.md` files;
  assert exactly one body read against
  `artifacts/kinds/<chosen-kind>/ARTIFACT.md`.
- `test_slash_command_does_not_read_playbooks`: synthetic kind
  declares `playbooks: [foo]` with `playbooks/foo.md` on disk;
  the slash command runs and produces no read against the
  playbook file.
- `test_l1_catalogue_invocations_unchanged`: invoking
  `KindCatalog.list_kinds()` directly (i.e. the path the slash
  command uses for selection) still does not read any
  `ARTIFACT.md` body — the existing s0017 § 9.1 isolation tests
  continue to pass after the slash command lands. (This test
  may already exist in the repo; the implementation task verifies
  it does and adds a regression cite.)

### 11.5 CLI surface unchanged (D9)

- `test_cli_create_signature_unchanged`: parametric snapshot of
  `artifacts create --help` output before and after the
  implementation task lands; assert byte-identical.
- `test_cli_create_empty_body_path_still_works`: invoking
  `artifacts create "<title>" --kind task` directly (no slash
  command) writes an empty-body file, as today.

## 12. n0004 / n0005 Engagement Table

s0017 § 10 established the `LOCK` / `LOCK-WITH-EDIT` / `REJECT`
pattern. This spec consumes two upstream notes; each note's
themes / decisions get an explicit verdict.

### 12.1 [[n0004-improve-create-command]] — themes A–J

| # | Theme (one-liner) | Verdict | Rationale |
|---|---|---|---|
| A | Template floor too thin (skill produces `Goal/Reqs/Verification`; convention is denser) | **LOCK** | Closes here. Loading the kind's `## Skeleton` block makes the convention the floor. |
| B | Type-blind scaffolding (different shapes per task type / kind) | **LOCK** | Closes here for **kinds** (variant rule § 5 covers per-kind shape). Per-task-type scaffolding within a single kind is the variant mechanism, also locked. |
| C | Brainstorm-to-task transcription is lossy | **REJECT** for this spec | Out of scope. Theme C is a separate workstream — a "first transcribe convergence" instruction in the slash command is additive but does not depend on body-loading. Filed by the PM if pursued. |
| D | Verification depth varies (executable vs prose) | **REJECT** for this spec | Out of scope. The shipped `task` skeleton already addresses this in `## How to use` Step 4; reinforcement is an authoring-guide concern. |
| E | Round 1 output format is freeform | **REJECT** for this spec | Out of scope. Skeleton-loading already pins shape; round-1 prompting is a separate UX concern. |
| F | "Do not re-litigate" framing absent | **LOCK-WITH-EDIT** | Inherited from each kind's `## How to use` prose (the `task` skeleton already includes a "Cite, do not duplicate" step). The slash command does not add this framing itself; the skeletons carry it. |
| G | Touch points table is high-value | **REJECT** for this spec | Out of scope. The `task` skeleton's `## Context` section already accommodates it; mandating it across all task types is an authoring-guide concern. |
| H | Repo-pattern crawler (mimic recent same-type tasks) | **LOCK** | Closes here. The skeleton **is** the crawled pattern — baked once at authoring time, applied at every create. The crawler-at-create-time alternative is rejected (latency, drift). |
| I | Sub-task creation flow is verbose | **REJECT** for this spec | Out of scope. Multi-task draft + batch create is a separate UX concern. |
| J | Status defaults per type unspecified | **REJECT** for this spec | Out of scope. The CLI's `--status` flag and per-kind defaults already exist; refining them is unrelated to body-loading. |

### 12.2 [[n0005-artifact-md-kind-folders-for]] — D1–D7

| ID | Decision (one-liner) | Verdict | Rationale |
|---|---|---|---|
| D1 | Redesign target is `/artifacts.create`, not `/openstation.create` | **LOCK** | Inherited as input. This spec acts on `/artifacts.create` only. |
| D2 | Body-only scope (header is fine) | **LOCK** | Inherited. The slash command does not modify frontmatter handling beyond what the CLI already does. |
| D3 | Per-kind folder; n0005 used `types/`, superseded by s0017 retaining `kinds/` | **LOCK-WITH-EDIT** | Storage layout is `<vault-root>/artifacts/kinds/<name>/` per s0017 (path remained `kinds/`); n0005's `types/` rename is the part edited. |
| D4 | File names: `kind.json` and `ARTIFACT.md` | **LOCK** | Consumed verbatim. |
| D5 | Self-sufficient `ARTIFACT.md`, optional companions | **LOCK** | Variant rule (§ 5) and fallback (§ 6) preserve the "self-sufficient" property; companion files (playbooks) remain L3. |
| D6 | AI-only consumption; CLI body-agnostic | **LOCK** | The load-bearing constraint of this spec. Restated in § 7. |
| D7 | `ARTIFACT.md` format: hybrid (frontmatter + `## How to use` + `## Skeleton`) | **LOCK** | The slash command's parser targets exactly this shape, with the variant extension noted in § 5. |

No silent drops.

## 13. Cross-References

- [[s0017-artifact-kinds-discovery-mechanism]] — parent L1 spec;
  surfaces `has_template`, the per-kind path, and the
  layer-isolation invariant this spec inherits.
- [[t0084-wire-artifacts-create-to-artifact]] — parent epic (user
  story, scope, reading list).
- [[t0085-spec-artifacts-create-consumes-artifact]] — task brief.
- [[t0079-artifact-md-artifacts-ai-extension]] — programme that
  shipped the four `ARTIFACT.md` files this spec consumes.
- [[n0004-improve-create-command]] — original 10-theme problem
  framing; engagement table § 12.1.
- [[n0005-artifact-md-kind-folders-for]] — locked decisions D1–D7;
  engagement table § 12.2.
- `src/artifacts_os/ai/claude/commands/artifacts.create.md` —
  slash command updated by the implementation sub-task.
- `src/artifacts_os/cli/commands/create.py` — CLI entry point;
  **read-only** for the implementation sub-task.
- `src/artifacts_os/core/kinds_catalog.py` — L1 surface; the
  implementation may add `artifact_md_path` to
  `KindCatalogEntry` (§ 9 item 2).
- `src/artifacts_os/core/registry.py` — `_load_vault_kinds`
  resolves the per-kind `ARTIFACT.md` path (lines 153–159);
  reused by the catalogue extension if § 9 item 2 lands.
- `artifacts/kinds/{note,task,spec,research}/ARTIFACT.md` —
  concrete inputs.
- [`docs/adding-a-kind.md`](../../docs/adding-a-kind.md) —
  authoring guide; doc sub-task references this spec post-merge
  (§ 9.3).
