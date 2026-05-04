---
created: 2026-05-02
id: r0002
kind: research
name: claude-skills-design-reference
status: done
---

# Claude Skills Design Reference

**Date:** 2026-05-02
**For:** `[[t0073-spec-artifact-kinds-discovery-mechanism]]`
**Sources:** [Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview),
[Skills best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

---

## TL;DR

Claude Skills use a three-level progressive disclosure model: at startup
only `name` + `description` (~100 tokens/skill) load; the full `SKILL.md`
body loads on trigger; bundled files load only when referenced. Our
`ARTIFACT.md` + `kind.json` + `playbooks/` maps cleanly onto this
three-level model. The critical insight to adopt: **the `description`
field is the sole selection signal** — it must encode both *what* the
kind is and *when* to use it. The main divergence: Skills have no formal
variants concept; our `variants:` field is richer and should not be
collapsed to fit the Skills mould. Anti-patterns to mirror: avoid vague
descriptions, deeply nested file references, and skeleton bodies that
offer too many choices without guidance. See `[[n0004-improve-create-command]]`
and `[[n0005-artifact-md-kind-folders-for]]` for the artifact-side
context that makes this analogy actionable.

---

## 1. Skill Anatomy

A Skill is a **directory** containing:

| File | Role | Load level |
|---|---|---|
| `SKILL.md` (required) | YAML frontmatter (`name`, `description`) + markdown body | L1 = frontmatter; L2 = body |
| Supporting markdown files (`FORMS.md`, `REFERENCE.md`, `EXAMPLES.md`) | Specialised guidance, loaded only when referenced in `SKILL.md` | L3 instruction |
| `scripts/*.py` | Executable utilities; *executed*, not read into context | L3 code |

Frontmatter constraints
([overview § Skill structure](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#skill-structure)):
- `name`: ≤64 chars, `[a-z0-9-]` only, no XML tags, no reserved words
  ("anthropic", "claude")
- `description`: ≤1024 chars, non-empty, no XML tags; **must be written
  in third person**

**Side-by-side with our kind folder:**

| Skill component | artifacts-os equivalent |
|---|---|
| `SKILL.md` frontmatter (`name`, `description`) | `ARTIFACT.md` frontmatter + `kind.json` (`name`) |
| `SKILL.md` body | `ARTIFACT.md` body (`## How to use` + `## Skeleton`) |
| Supporting markdown files | `playbooks/<variant>.md` |
| `scripts/` | No current equivalent |

---

## 2. Discovery & Catalogue

At startup the agent pre-loads every Skill's `name` + `description` into
the system prompt
([overview § Level 1: Metadata](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#level-1-metadata-always-loaded)):

> "Claude loads this metadata at startup and includes it in the system
> prompt. This lightweight approach means you can install many Skills
> without context penalty."

**Catalogue surface characteristics:**
- Flat list — no manifest file, no registry object, no tag taxonomy
- ~100 tokens per Skill
- Populated by filesystem enumeration: any directory containing a valid
  `SKILL.md` is a registered Skill
- No separate index or lockfile

Implication: the catalogue is the set of `description` strings. There is
no secondary lookup layer between "list all kinds" (L1) and "read kind
detail" (L2).

---

## 3. Progressive Disclosure

Exact three-level mechanism
([overview § How Skills work](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#how-skills-work)):

| Level | When loaded | Token cost | Content |
|---|---|---|---|
| **L1: Metadata** | Always, at startup | ~100 tokens/skill | `name` + `description` from YAML frontmatter |
| **L2: Instructions** | When Skill is triggered (semantic match on description) | <5k tokens typical | `SKILL.md` body |
| **L3+: Resources** | When referenced from `SKILL.md` body | Effectively unlimited (no cost until read) | Bundled markdown files; scripts contribute output only, never source code |

**Trigger mechanism:** Purely semantic — Claude decides a Skill is
relevant when the user's intent matches the description. No
activation keyword, no explicit invocation syntax. The agent issues
a `bash: read <skill>/SKILL.md` when triggered.

**L3 lazy-load contract:**
[Best practices § Progressive disclosure](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#progressive-disclosure-patterns):
> "SKILL.md serves as an overview that points Claude to detailed
> materials as needed, like a table of contents in an onboarding guide."
> Keep SKILL.md body under 500 lines; split beyond that.

**Anti-nesting rule (hard):** All file references must be one level deep
from `SKILL.md`. Deeper chains cause partial reads ("Claude might use
`head -100` to preview content rather than reading entire files").

**Script execution model:** When `SKILL.md` says "run `scripts/validate.py`",
Claude executes it via bash; only the script *output* enters context.
The script source code never loads. This is why scripts are L3 "code"
rather than L3 "instructions".

---

## 4. Selection Signal

**The sole selection signal is the `description` field.**

From
[best practices § Writing effective descriptions](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#writing-effective-descriptions):
> "Each Skill has exactly one description field. The description is
> critical for skill selection: Claude uses it to choose the right Skill
> from potentially 100+ available Skills."

Contract enforced by best practices:
- Third-person voice ("Processes Excel files…", not "I can help you…")
- Include both *what* it does and *when* to use it

**Example (from best practices):**
```yaml
description: Extract text and tables from PDF files, fill forms, merge
  documents. Use when working with PDF files or when the user mentions
  PDFs, forms, or document extraction.
```

There are no tags, keywords, examples, or structured intent maps in the
L1 surface. Examples can appear in the `SKILL.md` body (L2) but do **not**
influence initial Skill selection — only the description does.

---

## 5. Variants / Sub-modes

**Skills have no formal variants concept.** There is no field analogous
to our `variants:` in `ARTIFACT.md` frontmatter.

Sub-mode handling is achieved by:
1. **Conditional workflows in `SKILL.md` body** — "Creating new content?
   → Creation workflow. Editing existing? → Editing workflow."
   ([best practices § Conditional workflow pattern](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#conditional-workflow-pattern))
2. **Domain-specific L3 files** — `reference/finance.md`,
   `reference/sales.md`; the agent picks based on request context.
3. **Description that names sub-capabilities** — "fill forms, merge
   documents" signals scope without locking a variant.

The absence of a formal variants field is where the analogy **breaks
down**. Our `variants:` field in `ARTIFACT.md` frontmatter is a
first-class structural concept that Skills lack. Do not collapse it to
fit the Skills mould.

---

## 6. Authoring & Validation

Validation rules are
[enforced at upload/registration](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#yaml-frontmatter-requirements),
not at read time:
- `name` and `description` field rules enforced (see §1)
- Missing or invalid frontmatter → hard registration error; Skill not loaded

There is no published `skill.schema.json` or equivalent schema file.
Rules are prose-documented on the best-practices page and enforced by
platform code.

**No version field.** Skills are unversioned from the agent's
perspective — the filesystem copy is canonical. Versioning is an
operator concern (pin the Skill directory).

**Iterative authoring model:** Best practices recommend an A/B Claude
loop — "Claude A" authors/refines the Skill; "Claude B" (fresh session
with the Skill loaded) tests it against real tasks; observations feed
back to Claude A. Evaluation-driven: build test scenarios *before*
writing extensive documentation.

---

## 7. Composition & Reuse

**Skills are atomic. No cross-Skill references, inheritance, or
composition.**
([overview § Using Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#using-skills))

- A `SKILL.md` body cannot reference another Skill's files
- No `extends:` or `inherits:` field
- The "one level deep" rule is an anti-nesting guardrail, not a
  composition mechanism

Multiple Skills can be loaded simultaneously (each contributes their L1
metadata), but they remain independent. The agent may *use* multiple
Skills in one task, but Skills themselves cannot invoke each other.

---

## 8. Anti-patterns

From
[best practices § Anti-patterns](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices#anti-patterns-to-avoid)
and surrounding sections, translated to artifacts-os equivalents:

| Skill anti-pattern | artifacts-os equivalent risk |
|---|---|
| Vague description ("Helps with documents") | Vague `description` in `ARTIFACT.md` frontmatter — breaks kind selection when agent is choosing a kind |
| Offering too many choices in body without a default | `ARTIFACT.md` skeleton that lists multiple body shapes without guidance — produces inconsistent artifacts run-to-run |
| Deeply nested file references (SKILL→A→B→C) | Playbook chains deeper than one level from `ARTIFACT.md` — risk partial reads |
| Time-sensitive information baked in ("use old API before Aug 2025") | Dated assumptions or version-pinned instructions in `ARTIFACT.md` skeleton |
| Magic constants without rationale | Undocumented constraint values in `kind.json` properties |
| Writing in first person in description ("I can help you…") | Same failure in `ARTIFACT.md` frontmatter `description` — causes discovery problems |
| Over-explaining what the model already knows | Verbose boilerplate in `ARTIFACT.md` that pads context with obvious instructions |

---

## 9. Mapping Table

| Concept | Claude Skills | artifacts-os kinds | Verdict | Rationale |
|---|---|---|---|---|
| Unit of capability | Skill (directory) | Kind (directory `kinds/<name>/`) | **adopt** | Directory-per-kind already decided in n0005 |
| Primary entry point | `SKILL.md` (uppercase) | `ARTIFACT.md` (uppercase) | **adopt** | Naming and uppercase convention already decided in n0005 (D4) |
| Catalogue metadata | `name` + `description` in `SKILL.md` frontmatter | `name` in `kind.json`; description not yet formalised | **adapt** | Consolidate description into `ARTIFACT.md` frontmatter as a required field; `kind.json` keeps machine-readable schema |
| L1 catalogue surface | name + description, ~100 tokens, always loaded | Not yet defined | **adopt** | L1 should carry name + one-line description only; never load `ARTIFACT.md` body at catalogue time |
| L2 instructions | `SKILL.md` body (≤500 lines), loaded on trigger | `ARTIFACT.md` `## How to use` + `## Skeleton`, loaded when creating | **adopt** | Same lazy-load trigger: only load when agent selects this kind |
| L3 supplemental files | Bundled markdown files (`FORMS.md`, etc.), referenced from body | `playbooks/<variant>.md`, already declared in `ARTIFACT.md` frontmatter | **adopt** | Playbooks already match L3 semantics; make the lazy-load contract explicit |
| Executable scripts | `scripts/*.py` executed not read | No current equivalent | **reject** (v1) | Out of scope; not needed for kind discovery |
| Selection signal | Single `description` field, what + when, ≤1024 chars, third-person | Not yet formalised | **adopt** | Lock a `description:` field in `ARTIFACT.md` frontmatter with same what+when contract and length cap |
| Variants / sub-modes | None (ad-hoc via conditional `SKILL.md` body) | `variants:` field in `ARTIFACT.md` frontmatter | **reject** as analogy | Our `variants:` is a first-class concept Skills lack; keep it, do not flatten it |
| Frontmatter validation | Platform-enforced at registration (hard error) | `kind.json` schema; `ARTIFACT.md` validation not yet defined | **adapt** | Missing `description` = registration warning; missing `ARTIFACT.md` = soft fallback (not hard error); missing declared playbook = hard error (already decided) |
| Versioning | None | None | **adopt** (non-decision) | No version field needed in v1; filesystem copy is canonical |
| Cross-kind composition | None — atomic | None currently | **adopt** (non-decision) | No cross-kind inheritance in v1 |
| Nesting depth | Max 1 level deep from `SKILL.md` | Max 1 level from `ARTIFACT.md` (playbooks declared directly) | **adopt** | Enforce one-deep rule in spec; nested playbook references are an error |
| Description voice | Third-person required | Not yet specified | **adopt** | Require third-person in `description` field guidance; first-person causes discovery failures |

---

## Recommendations for t0073

The following are directional inputs for the architect drafting
`[[t0073-spec-artifact-kinds-discovery-mechanism]]`. No CLI command
names, flag shapes, or file paths are prescribed here.

1. **Lock a `description:` field in `ARTIFACT.md` frontmatter.**
   Required, non-empty, ≤1024 chars, third-person, encodes both *what*
   the kind is and *when* to choose it. This is the sole L1 selection
   signal — mirrors the Skills `description` field exactly. The spec
   should treat a missing or empty description as a registration warning.

2. **Define L1 as name + description only, always loaded, no body.**
   The catalogue surface must never implicitly load `ARTIFACT.md` body
   content. L1 cost budget: ~100–200 tokens per kind. Mirrors Anthropic's
   ~100-token-per-Skill budget.

3. **Define L2 trigger as "agent has selected this kind".**
   Only when the agent is about to create an artifact of this kind (or
   inspect a specific kind) does `ARTIFACT.md` body load. Not on
   `kinds list`, not on generic browsing. Mirrors Skills' semantic trigger.

4. **Define L3 as declared playbooks, loaded on-reference.**
   Playbooks are already lazy-declared in `ARTIFACT.md` frontmatter.
   The spec should formalise that the `ARTIFACT.md` body may reference
   a playbook (by name) and the consumer reads it only at that point.
   The "one level deep" rule from Skills must be enforced: playbooks
   may not reference sibling playbooks.

5. **Keep `variants:` as a first-class field; do not flatten it.**
   Skills have no variants concept and handle sub-modes via ad-hoc
   conditional body text. Our variants field is richer. The spec should
   expose declared variants at L2 (per-kind detail), not L1.

6. **Separate the description source from the schema source.**
   `kind.json` owns machine-readable frontmatter schema (field types,
   enums, validations). `ARTIFACT.md` frontmatter owns human/agent-facing
   metadata (`description`, `variants`, `playbooks`). The spec should
   not try to merge them into one file — the split mirrors the
   Skills model (platform schema separate from `SKILL.md`).

7. **Spec the fallback semantics explicitly.**
   Skills fail hard on bad frontmatter. For us: missing `ARTIFACT.md` =
   kind is usable but body scaffolding unavailable (soft warning, not
   hard error). Missing *declared* playbook = hard error (already decided
   in n0005 locked context). The spec must state both rules, not leave
   them implicit.

8. **Adopt the evaluation-first authoring model for kind templates.**
   Anthropic recommends building test scenarios before writing extensive
   `SKILL.md` content. The same applies to `ARTIFACT.md`: identify
   representative creation tasks, confirm the skeleton produces consistent
   bodies, then freeze the template. Relevant for the authoring guide
   (`docs/adding-a-kind.md`), not the spec itself.