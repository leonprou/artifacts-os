---
created: 2026-05-03
id: n0006
kind: note
name: artifact-creation-cases-r0004-vs
type: brainstorm
---

Captures the 2026-05-03 session comparing how two research artifacts
on the same topic — `r0004-computer-use-cli-vs-mcp` and
`r0005-cli-vs-mcp-for-agents` — were produced. Each case used a
different creation path (skill-only vs body-loader command). The note
preserves the per-case observations, the bug surfaced along the way,
and the architectural conclusion that emerged about how kind contracts
should be delivered to authoring agents.

## Origin

Session 2026-05-03. User asked "compare r4 (created with the skill
only) and r5 (with new command)". The comparison surfaced (a) the
shell-expansion bug filed as `[[t0088-fix-shell-expansion-footgun-in]]`,
(b) the observation that the `@researcher` agent never consulted
`artifacts/kinds/research/ARTIFACT.md`, and (c) a sharpened framing of
why the body-loader command exists — not as a safety primitive but as
a kind-contract enforcement seam.

Both research artifacts (`r0004`, `r0005`) and the bug task (`t0088`)
were created earlier in the same session. This note exists so a future
reader can reconstruct the analysis without re-running the comparison.

## Cases

### Case A — Skill-only path (produced `r0004`)

**Mechanism.** The user invoked the `@researcher` agent with a research
prompt ("research using computer use cli vs MCP for agents. pros, cons
and risks for each approach"). The agent, as recorded in the trace:

1. Read one file (the agent's own definition or `CLAUDE.md` — not
   `kinds/research/ARTIFACT.md`).
2. Listed existing research artifacts and ready tasks via
   `artifacts list -j`.
3. Ran two `WebSearch` calls and four `WebFetch` calls.
4. Wrote a long Markdown body and called
   `artifacts create "computer-use-cli-vs-mcp-for-agents" --kind research --fields status=draft --body "## Question … `rm -rf` … `git reset --hard` … `db drop` … `.env` … `tools/list` …"`.

**What hit disk.** A substantively complete research note (Question,
Conclusion, Approach A — CLI, Approach B — MCP, Head-to-Head eval,
Decision Guide, Sources). Genuine research synthesis, useful prose.

**Defects observed.**

1. **Shell-expansion corruption.** zsh ran command substitution on
   backtick code spans inside the `--body "..."` argument before the
   CLI ever saw them. Resulting bytes on disk:
   - `` `rm -rf`, `git reset --hard`, `db drop` `` → `, HEAD is now at 8332c17 docs(t0078): update adding-a-kind guide …,` (the `git reset --hard` actually executed against the working tree)
   - `` agent can read `.env` files, SSH keys `` → `agent can read , SSH keys`
   - `` Unix pipes: `ls \| grep X \| wc -l`. `` → `Unix pipes: .`
   - `` **Discoverability** \| `tools/list` endpoint `` → `**Discoverability** \| endpoint lets agents …`
2. **Structural drift from the kind contract.** The body's section
   shape (Question / Approach A / Approach B / Decision Guide) does
   not match `artifacts/kinds/research/ARTIFACT.md`'s required shape
   (`## TL;DR` → numbered `## N. {AREA}` → `## 6. Recommendations` →
   `## Sources`). No overlap on section names. The required
   `## Recommendations` heading is missing entirely.
3. **Frontmatter drift.** `status: draft` was set explicitly; `r0005`
   omitted it. Both technically valid, but two artifacts in the same
   kind already disagree on whether `status` is set on creation.

**Diagnosis.** The agent did not load
`kinds/research/ARTIFACT.md`. The `@researcher` agent spec
(`artifacts/agents/researcher.md`) does not mention kind templates,
`ARTIFACT.md`, or any obligation to consult kind-level authoring
guidance. The agent freelanced section structure from first principles
— a reasonable research shape, but not the project's canonical one.
The shell bug is orthogonal: even with a clean `--body-file`
invocation, the structural drift would have been identical.

### Case B — Body-loader command path (produced `r0005`)

**Mechanism.** Created by invoking `artifacts create --kind research`
through the new body-loader code path (per `[[s0018-artifact-md-body-loader-for]]`
/ `[[t0086-implement-artifacts-create-body-loader]]`). No agent
authoring involved; no LLM in the hot path. The command rendered
`artifacts/kinds/research/ARTIFACT.md`'s skeleton verbatim into a new
file under `artifacts/research/`.

**What hit disk.** The raw template — every `{{PLACEHOLDER}}` intact,
every `<!-- authoring guidance -->` HTML comment preserved. Section
shape exactly matches the kind template:

```
## TL;DR
## 1. {{AREA_OR_DIMENSION}}
## 2. {{AREA_OR_DIMENSION}}
## 3. {{GAPS_OR_SUB_AREAS}}
## 4. Mapping Table
## 5. Coverage matrix at a glance
## 6. Recommendations
## Sources
```

**Defects observed.** None at the disk-write seam — Python file I/O,
no shell, no interpolation. But the artifact is **substantively
empty**: zero research content, all placeholders. By itself it would
be useless to a downstream consumer.

**Diagnosis.** The command did exactly what it was designed to do —
emit a faithful, side-effect-free render of the kind contract.
Authoring is a separate step the command intentionally does not own.

## Analysis

### Finding 1 — The shell-expansion bug is orthogonal to command-vs-skill

`r0004`'s corruption was caused by `--body "..."` being shell-evaluated
in the user's shell. It would have happened to any caller — agent or
human — using that argument shape. Switching to `--body-file` or
`--body -` (stdin) eliminates it. Filed as
`[[t0088-fix-shell-expansion-footgun-in]]`. This bug is not a reason
to ship the body-loader command and not a reason to skip it. Fix it
independently.

### Finding 2 — The `@researcher` agent never read the kind's `ARTIFACT.md`

The trace shows no `Read` of `kinds/research/ARTIFACT.md`. The agent
spec contains no instruction to do so. The output's structural drift
is the predictable consequence of an authoring agent that does not
know the kind contract exists.

This is the load-bearing finding: **r0004's structural drift was not
a skill failing at its job — it was a skill that was never told the
job included reading the kind template**.

### Finding 3 — The choice is "command vs per-agent template-reading", not "command vs skill"

Both mechanisms can enforce the kind contract; they differ in where
the contract lives:

| Mechanism | Contract delivery | Cost | Failure mode |
|---|---|---|---|
| Body-loader command (Case B) | Materialised on disk before the LLM sees it; Python enforces shape | One implementation, one place to update when the template changes | Empty scaffold needs follow-up authoring |
| Skill / agent reads `ARTIFACT.md` (a hypothetical Case A') | Delivered as context the LLM is asked to follow; one extra `Read` call per author run | Every kind-authoring agent spec must be updated, individually, when conventions change | Probabilistic — agent can forget, drift, or misread |

The body-loader scales better: one code path, one source of truth for
each kind's shape. The per-agent approach is viable but distributed,
prose-encoded, and re-instantiated each run.

### Finding 4 — Neither artifact alone is the desired output

| Artifact | Has prose? | Has correct shape? | Safe to commit? |
|---|:-:|:-:|:-:|
| `r0004` (skill-only) | yes | no | no — corrupted bytes + freelanced structure |
| `r0005` (command-only) | no | yes | yes, but useless until filled |
| Desired (skill + command + safe-write) | yes | yes | yes |

The desired pipeline is **`artifacts create --kind research` (loader
materialises shape) → skill authors prose into the placeholders →
`--body-file` / stdin on any later regeneration**. None of the three
pieces is redundant.

### Finding 5 — Path-of-least-resistance shapes agent behaviour

Agents call the easiest path. Today, `artifacts create --kind research`
without a body-loader produces an empty body, so a skill that wants
content has to invent shape from scratch — exactly what `@researcher`
did. With a loader, the easy path emits the canonical scaffold; the
skill's job collapses to filling placeholders, which is harder to
freelance. The loader is a **default-shaping** tool, not a safety
primitive.

## Decisions captured

### D1 — Keep the body-loader command (per `[[s0018-artifact-md-body-loader-for]]`)

The loader is not redundant with the skill; they enforce different
properties (shape vs content). Drop neither.

### D2 — Update kind-authoring agent specs to be aware of `ARTIFACT.md`

Even with the loader, agents that author bodies need to know the
template exists so they fill placeholders within the canonical shape
rather than overwriting it. Specifically: `@researcher`,
`@architect`, `@author`, `@product-manager`, and any other agent that
runs `artifacts create` for a templated kind. Out of scope here —
candidate follow-up task.

### D3 — Skills that drive `artifacts create` must use `--body-file` or stdin, never `--body "..."`

Filed against `[[t0088-fix-shell-expansion-footgun-in]]`. Skill /
command authoring guidance should be updated alongside the bug fix.

## Open questions

### Q1 — Should every agent that creates artifacts read its kind's `ARTIFACT.md`, or should the loader's scaffold-then-edit pattern be the only required path?

Two viable patterns:

- **(a)** Loader materialises shape; agent edits the placeholders in
  place (no template read required). Simpler agent specs.
- **(b)** Agent reads `ARTIFACT.md` for the authoring-guidance
  prose (`## How to use` section), then drafts content informed by
  it. Higher quality but more context per run.

`r0004`'s prose was good despite ignoring the template; `r0005`'s
shape is correct despite having no prose. The right answer is
probably **both**: loader for shape + agent reads `ARTIFACT.md` for
guidance. But that doubles per-run context and needs validation that
the gain is worth it. Not yet decided.

### Q2 — Should `artifacts create --kind X --body-file Y` merge Y into the loader's scaffold, or replace it?

The body-loader spec (s0018) presumably already answers this; flagged
here for cross-check during t0086 implementation. If `--body-file`
replaces, an agent that authors before reading the template loses the
scaffold; if it merges (e.g. by section name), surprising outcomes
can result.

### Q3 — Should `--body "..."` be removed entirely?

t0088 leaves this open (R1). This note's evidence (real working-tree
mutation via `git reset --hard`) is a strong argument for removal in
favour of `--body-file` / stdin only.

## How to act on this note

1. Read `[[t0088-fix-shell-expansion-footgun-in]]` — addresses the
   shell bug (Finding 1, D3).
2. If Q1 is settled in favour of "agents should read `ARTIFACT.md`",
   create a follow-up task to update kind-authoring agent specs
   (`artifacts/agents/{researcher,architect,author,product-manager,…}.md`)
   with that obligation.
3. Use `r0004` and `r0005` as worked examples in any documentation
   that explains the body-loader's purpose — they are the cleanest
   side-by-side evidence of "skill alone" vs "command alone" vs
   "what the combination should produce".

## References

- [[r0004-computer-use-cli-vs-mcp]] — Case A artifact (skill-only path)
- [[r0005-cli-vs-mcp-for-agents]] — Case B artifact (body-loader command path)
- [[t0088-fix-shell-expansion-footgun-in]] — bug filed during this session
- [[s0018-artifact-md-body-loader-for]] — body-loader spec
- [[t0086-implement-artifacts-create-body-loader]] — body-loader implementation task
- [[n0004-improve-create-command]] — original problem framing (10 themes, 4 designs)
- [[n0005-artifact-md-kind-folders-for]] — sibling planning note (D1–D7 on kind folders + ARTIFACT.md)
- `artifacts/kinds/research/ARTIFACT.md` — research kind template (the contract `r0004` did not follow)
- `artifacts/agents/researcher.md` — `@researcher` spec (does not mention `ARTIFACT.md`)
- `src/artifacts_os/ai/body_loader.py` — body-loader implementation
- `tests/ai/test_body_loader.py` — body-loader tests