---
kind: task
id: t0176
name: teach-the-artifacts-os-skill
type: documentation
status: verified
assignee: author
owner: user
created: 2026-05-18
started: 2026-05-18
---

# Teach The Artifacts-Os Skill To Use Artifact.Md For Kind Selection And Body

## Why

Kinds ship with two authored surfaces — `kind.json` (validation contract)
and `ARTIFACT.md` (selection signal + body skeleton). Today the
`artifacts create` flow used by agents reads only `kind.json`. The
`ARTIFACT.md` body — including the `description:` selection signal and
the `## Skeleton` body template — is never consulted, so agents either
default to `task` and write empty bodies, or improvise drafting steps in
each per-kind slash command (which then drift from the authored
`ARTIFACT.md`). This task closes the gap at the agent-instruction layer
(skill + slash command), without touching the CLI.

## Context

This task implements Approaches **A** (skill prescribes the
read-then-create flow) and **E** (skill teaches selection via the
`description:` signal) from the PM↔user design conversation on
2026-05-18. Approach B (transparent CLI loading) and C (discrete
skeleton-emit verb) were considered and rejected because they reopen the
explicit s0018 D6/D7 layer boundary ("CLI stays body-agnostic; the
AI/agent layer is where `ARTIFACT.md` reading happens"). Approach D
(simplify per-kind `/openstation.create.<kind>` commands to defer to
`ARTIFACT.md`) is a follow-on for a separate technical-writer task.

The CLI surface needed by the agent already exists:
`artifacts kinds <name>` returns the full `ARTIFACT.md` body (text mode)
or `{meta, body}` (JSON via `-j`). `artifacts kinds` (no name) lists
descriptions for selection. No new CLI surface is required.

## Source of truth

- **s0017 — artifact kinds discovery mechanism** — locks the
  `description:` contract on `ARTIFACT.md` frontmatter (≤ 1024 chars,
  third-person, encodes *what* + *when*) and the L1 catalogue surface
  read by `artifacts kinds`.
- **s0018 — `ARTIFACT.md` body loader** — locks the body structure
  (`## Skeleton`, `## Variants/<name>`), the variant-selection
  precedence (§ 5.1), the `{{TITLE}}`-only substitution rule
  (D1, D3), the size cap (§ 8.2), and the layer boundary
  (D6, D7 — CLI body-agnostic; AI/agent layer reads `ARTIFACT.md`).
- **`src/artifacts_os/ai/body_loader.py`** — Python reference
  implementation of the read + extract + substitute algorithm
  described in s0018. The skill instructions should match its
  semantics so an agent following the skill produces the same body a
  programmatic caller would.
- **Shipped `ARTIFACT.md` worked examples** —
  `artifacts/kinds/note/ARTIFACT.md`,
  `artifacts/kinds/task/ARTIFACT.md`,
  `artifacts/kinds/spec/ARTIFACT.md`,
  `artifacts/kinds/research/ARTIFACT.md`. Use one of these in the
  skill's end-to-end example.
- **`docs/adding-a-kind.md`** — describes the author-side contract
  (how kinds are declared); useful background but not edited here.

## Files to touch

| Path | Surface | Edit |
|---|---|---|
| `.openstation/skills/artifacts-os/SKILL.md` | Canonical skill | Add selection + scaffolding sections, worked example, fallback note. |
| `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` | Shipped (harness-distributed) skill copy | Mirror the canonical skill verbatim. |
| `.claude/commands/artifacts.create.md` | Slash command (active project) | Reference the new flow (or delegate to the skill). |
| `.openstation/commands/artifacts.create.md` | Slash command (canonical) | Same. |

## Constraints

- **Variant-selection precedence (s0018 § 5.1).** When the chosen kind
  declares variants, precedence is: explicit user-requested variant >
  `--type` token when the kind's `ARTIFACT.md` frontmatter declares
  `variant_field: type` > default `## Skeleton`. Teach this exactly;
  do not paraphrase loosely.
- **Substitution scope (s0018 D1, D3).** `{{TITLE}}` is the only
  placeholder substituted. All other `{{TOKEN}}` placeholders are left
  literal for the agent to fill in during drafting.
- **No recursion (s0018 D6).** The skill reads exactly one
  `ARTIFACT.md` per create — the chosen kind's. It does not chase
  references to other kinds' `ARTIFACT.md`, does not read `kind.json`
  bodies, and does not follow playbook chains.
- **Layer boundary preserved (s0018 D6, D7).** No changes to
  `src/artifacts_os/cli/commands/create.py` or any other CLI module.
  The CLI stays body-agnostic; the skill (agent layer) is where
  `ARTIFACT.md` reading happens.
- **Skill voice.** Match the existing artifacts-os skill voice:
  directive ("Run X", "Pass Y"), example-led (fenced code blocks),
  with an explicit Rules section. Do not adopt the human-reference
  density of `docs/`.

## Out of scope

- Modifying or retiring `src/artifacts_os/ai/body_loader.py` —
  it stays for deterministic non-agent callers (CI, scripts).
  Whether to keep both surfaces long-term is a follow-up question,
  not this task.
- Updating `docs/creating-an-artifact.md` or `docs/adding-a-kind.md`
  to cross-reference the new flow — that is a downstream
  technical-writer task and should be filed when this lands.
- Simplifying per-kind `/openstation.create.<kind>` slash commands
  to defer to `ARTIFACT.md` (Approach D) — separate task.
- Any CLI change. Adding a CLI flag, a new verb, or a default-body
  policy change is explicitly out of scope.

## Requirements

1. **Selection signal (Approach E).** The `artifacts-os` skill instructs the agent that when the user does not specify a kind, the agent must first consult `artifacts kinds -j` (or the table form) and pick a kind by its `description:` field before falling back to the configured default. The skill explains briefly that `description:` encodes both the *what* and the *when* of a kind.

2. **Body scaffolding from ARTIFACT.md (Approach A).** The skill prescribes, for every create, a read-then-create flow:
   - Run `artifacts kinds <name>` to load the chosen kind's `ARTIFACT.md`.
   - Read the body's `## Skeleton` section (or the matching `## Variants/<variant>` section when a variant is implied by the user's request or by `--type`).
   - Substitute `{{TITLE}}` with the artifact's title; leave other `{{TOKEN}}` placeholders literal for the agent to fill in during drafting.
   - Pipe or pass the resolved body via `artifacts create "<title>" --kind <name> --body-file -` (or `--body`).

3. **Worked example.** The skill includes at least one end-to-end worked example combining selection + scaffolding for a real shipped kind (e.g., `note` or `spec`).

4. **Fallback policy stated.** When the chosen kind has no `ARTIFACT.md`, or `ARTIFACT.md` has no `## Skeleton` section, the agent falls back to creating with an empty body and surfaces a one-line info note to the user — matching the existing `body_loader.py` policy.

5. **Slash command mirrors the flow.** `.claude/commands/artifacts.create.md` and `.openstation/commands/artifacts.create.md` are updated to reference the same selection + scaffolding flow (or delegate to the skill).

6. **Shipped copy stays in sync.** `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` receives the same edits so consumers pulling via the artbook harness get the new flow.

7. **No CLI change.** `src/artifacts_os/cli/commands/create.py` is not modified — the s0018 D6/D7 layer boundary (CLI stays body-agnostic) is preserved.

## Verification

- [x] `artifacts-os` skill (canonical at `.openstation/skills/artifacts-os/SKILL.md`) includes a "Selecting a kind" subsection that prescribes consulting `artifacts kinds` descriptions before defaulting.
- [x] `artifacts-os` skill includes a "Drafting the body from ARTIFACT.md" subsection covering the `artifacts kinds <name>` → extract `## Skeleton` / `## Variants/<name>` → `{{TITLE}}` substitution → `--body-file -` flow.
- [x] Skill includes at least one worked example showing the full flow on a shipped kind (one of `note`, `task`, `spec`, `research`).
- [x] Skill states the variant-selection precedence per s0018 § 5.1 (explicit variant > `--type` token when `variant_field: type` > default `## Skeleton`).
- [x] Skill states that `{{TITLE}}` is the only placeholder substituted; other `{{TOKEN}}` placeholders remain literal for the agent to fill in (s0018 D1, D3).
- [x] Fallback for missing `ARTIFACT.md` or missing `## Skeleton` is documented (empty body + agent-visible info note).
- [x] `.claude/commands/artifacts.create.md` and `.openstation/commands/artifacts.create.md` mirror or reference the flow.
- [x] Shipped skill copy at `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` matches the canonical skill.
- [x] No changes to `src/artifacts_os/cli/commands/create.py`; CLI remains body-agnostic.
- [x] `pytest` still passes (skill-only edits should not affect tests; verifying no incidental breakage).
- [x] Reviewed and approved by user.

## Verification Report

*Verified: 2026-05-22*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | "Selecting a kind" subsection prescribes consulting `artifacts kinds` descriptions before defaulting | PASS | `SKILL.md` lines 122–140: H4 `#### Selecting a kind` instructs `artifacts kinds -j` consultation, explains the *what* + *when* contract, falls back only when no description matches. |
| 2 | "Drafting the body from ARTIFACT.md" subsection covers full flow | PASS | `SKILL.md` lines 142–164: H4 `#### Drafting the body from ARTIFACT.md` documents 4-step flow — `artifacts kinds <name>` → extract `## Skeleton` / `## Variants/<name>` → `{{TITLE}}` substitution → pipe via `--body-file -`. |
| 3 | At least one worked example on a shipped kind | PASS | `SKILL.md` lines 207–254: end-to-end `#### Worked example — creating a note` using the shipped `note` kind. |
| 4 | Variant-selection precedence per s0018 § 5.1 stated | PASS | `SKILL.md` lines 166–184: precedence stated verbatim — explicit user-requested variant > `--type` token when `variant_field: type` > default `## Skeleton`. |
| 5 | `{{TITLE}}`-only substitution rule stated | PASS | `SKILL.md` lines 186–191: "Substitution scope" section explicitly states `{{TITLE}}` is the only substituted placeholder; all others remain literal. |
| 6 | Fallback for missing ARTIFACT.md / Skeleton documented | PASS | `SKILL.md` lines 193–205: fallback with empty body + `info: kind '<kind>' has no ARTIFACT.md; created with empty body.` matching `body_loader.py` (s0018 § 6). |
| 7 | Slash commands mirror or reference the flow | PASS | `artifacts.create.md` lines 33–39 reference selection via `artifacts kinds -j`; lines 43–66 enumerate the 4-step body-scaffolding procedure with fallback note + skill delegation pointer. |
| 8 | Shipped skill copy matches canonical | PASS | `stat -L` confirms `.openstation/skills/artifacts-os/SKILL.md` and `src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md` resolve to inode 45206980 (symlinked — single source of truth). |
| 9 | No changes to `src/artifacts_os/cli/commands/create.py` | PASS | `git log --oneline src/artifacts_os/cli/commands/create.py` — last commit is `1f6c809` (t0161) predating this task; no commits during t0176 work. |
| 10 | `pytest` still passes | PASS | `pytest -q` — 1131 passed, 1 skipped in 27.43s. |
| 11 | Reviewed and approved by user | PASS | User invoked `/openstation.verify t0176-teach-the-artifacts-os-skill` — owner-gated review action. |

### Summary

11 passed, 0 failed. All verification criteria satisfied; the task is ready to transition to `verified`.

## Findings

Closed the kind-selection + body-scaffolding gap at the agent-instruction
layer per Approaches A + E from the 2026-05-18 design conversation. No
CLI surface was added or modified; s0018 D6/D7 layer boundary preserved.

### What was edited

- **`src/artifacts_os/ai/claude/skills/artifacts-os/SKILL.md`** (the
  canonical `.openstation/skills/artifacts-os/SKILL.md` is a symlink
  to this path, so a single edit satisfies both Requirement 1/2/3/4
  and Requirement 6). The Create section now contains three new
  H4 subsections plus an end-to-end worked example:
  - *Selecting a kind* — prescribes `artifacts kinds -j` consultation
    by `description:` before defaulting; explains the *what* + *when*
    contract from s0017.
  - *Drafting the body from ARTIFACT.md* — locks the four-step
    read-then-create flow (`artifacts kinds <name>` → extract
    skeleton → substitute `{{TITLE}}` → `--body-file -`), the
    variant-selection precedence verbatim from s0018 § 5.1, the
    `{{TITLE}}`-only substitution rule (s0018 D1/D3), and the empty-body
    fallback with the one-line info note (s0018 § 6).
  - *Worked example — creating a `note`* — end-to-end walkthrough on
    the shipped `note` kind: confirm by description, load
    `ARTIFACT.md`, substitute `{{TITLE}}`, pipe via `--body-file -`,
    surface the canonical stem.
  - A new Rule 6 in the Rules section pins the read-then-create flow
    into the rule list so it sits alongside the other CLI-only and
    body-immutability invariants.

- **`src/artifacts_os/ai/claude/commands/artifacts.create.md`** (both
  `.claude/commands/artifacts.create.md` and
  `.openstation/commands/artifacts.create.md` are symlinks to this
  path — Requirement 5). The kind-resolution paragraph now directs
  the agent to consult `artifacts kinds -j` by `description:` rather
  than guessing. A four-step body-scaffolding block was inserted at
  the top of the Procedure section, with the empty-body fallback note,
  s0018 D6/D7 boundary call-out, and a delegation pointer to the
  skill's "Drafting the body from ARTIFACT.md" subsection for the full
  contract.

### Design decisions

- **Symlink topology consolidates the work into two real file edits.**
  Both the canonical and shipped skill paths resolve to a single inode
  under `src/artifacts_os/ai/claude/`; same for the two slash-command
  copies. That means Requirements 5 and 6 (the "stays in sync" pair)
  are satisfied structurally, not by manual mirroring.
- **Skill voice over reference density.** The new subsections follow
  the existing skill voice ("Run X", fenced example blocks, explicit
  Rules) rather than the dense, prose-heavy register of `docs/`. The
  worked example uses a real shipped kind (`note`) end-to-end so the
  agent has a concrete template to imitate, not just a procedure.
- **Variant precedence and substitution scope are quoted, not
  paraphrased.** The Constraints section of the task flagged these as
  "teach exactly", so the wording mirrors s0018 § 5.1 (precedence) and
  D1/D3 (`{{TITLE}}` only) directly.
- **`body_loader.py` left in place.** Per the Out-of-scope section, the
  Python reference implementation continues to serve deterministic
  non-agent callers (CI, scripts). The skill's semantics now match
  `load_body` step-for-step so an agent following the skill produces
  the same body a programmatic caller would.

### Verification evidence

- `pytest` — 1131 passed, 1 skipped (no incidental breakage).
- `git diff --stat src/artifacts_os/cli/commands/create.py` — empty
  (no CLI changes; s0018 D6/D7 boundary preserved).
- Canonical / shipped skill paths confirmed as the same inode via
  symlink; slash-command paths confirmed as the same inode via
  symlinks under `src/artifacts_os/ai/claude/commands/`.

## Progress

- 2026-05-18T19:59Z — author — Edited skill (Create section + new
  H4 subsections + Rule 6) and slash command via the canonical paths
  under `src/artifacts_os/ai/claude/`. Both
  `.openstation/skills/artifacts-os/SKILL.md` and the slash-command
  copies under `.claude/commands/` and `.openstation/commands/`
  resolve to the same inodes as the shipped sources, so the in-sync
  invariant is structural. `pytest` — 1131 passed, 1 skipped;
  `src/artifacts_os/cli/commands/create.py` untouched. Findings +
  Downstream appended. Log:
  `openstation/logs/t0176-teach-the-artifacts-os-skill.jsonl`.

## Downstream

- File a technical-writer task to cross-reference the new flow from
  `docs/creating-an-artifact.md` and `docs/adding-a-kind.md`
  (explicitly deferred by the task's Out-of-scope section).
- File a follow-on task for Approach D — simplifying the per-kind
  `/openstation.create.<kind>` slash commands to delegate to
  `ARTIFACT.md` rather than carrying their own drafting steps. The
  skill now establishes the canonical drafting flow those commands
  should defer to.
- Decide whether `src/artifacts_os/ai/body_loader.py` and the skill
  instructions should remain as twin surfaces long-term. The task
  scoped this question out, but two surfaces means two places drift
  can happen; a follow-up should pick one as authoritative.
