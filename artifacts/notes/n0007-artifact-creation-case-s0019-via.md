---
created: 2026-05-03
id: n0007
kind: note
name: artifact-creation-case-s0019-via
type: brainstorm
---

Captures a third artifact-creation case observed in the same
2026-05-03 session: the `@architect` agent producing
`s0019-artifacts-os-public-api` via the OpenStation runner
(`os run arch`) with the prompt "write a simple spec for artifacts-os
API". Extends the two-case analysis in
`[[n0006-artifact-creation-cases-r0004-vs]]` so the framework now
covers a templated kind (spec) authored by a different agent through
the OpenStation runner surface, and surfaces several new findings the
earlier analysis did not have evidence for.

## Origin

Session 2026-05-03, immediately after `[[n0006-artifact-creation-cases-r0004-vs]]`
locked the Case A / Case B framework. The user invoked `os run arch`
(OpenStation runner) and prompted the architect with "write a simple
spec for artifacts-os API". A first trace summary was shared, then a
fuller transcript with explicit `Read` calls; this note integrates
both. Job here is transcription of the new case + reconciliation with
the prior findings; not re-litigation of D1–D3 from `n0006`.

## Case C — OpenStation runner + `@architect` (produced `s0019`)

### Mechanism

1. User invoked `os run arch` — OpenStation's runner, which launched
   Claude Code with the `@architect` agent profile (model: Opus 4.7,
   effort: xhigh — visibly different from `@researcher`'s Sonnet 4.6
   / high in Case A).
2. Project context loaded on startup (CLAUDE.md, agent spec, etc.).
3. `artifacts list --kind spec -j` — scanned existing specs for
   convention.
4. `artifacts show s0002 -j` + `python3 -c "..."` — pulled `s0002`'s
   frontmatter and body for shape reference.
5. `artifacts kinds` (worked) → `artifacts kinds spec` (**errored**:
   `unrecognized arguments: spec`). The agent attempted to drill
   into a single kind via subcommand-style invocation; the CLI does
   not support that shape today.
6. `ls artifacts/kinds/spec/` then **`Read artifacts/kinds/spec/ARTIFACT.md`**
   — the kind contract, read directly. Confirmed in the fuller trace.
7. Read six core source modules to ground the spec in shipped code:
   `src/artifacts_os/core/__init__.py`, `models.py`, `store.py`,
   `discover.py`, `registry.py`, `errors.py`. Confirmed in the
   fuller trace.
8. Wrote the body to `/tmp/spec_body.md` (Write tool).
9. Called:
   ```
   artifacts create "artifacts-os public API" \
     --kind spec \
     --body "$(cat /tmp/spec_body.md)" \
     --fields status=draft agent=architect
   ```
10. Verified via `artifacts show s0019 -j | python3 -c "..."`.

### What hit disk

A substantively complete spec (`s0019-artifacts-os-public-api`)
locking the public Python API surface across six decisions (D1–D6)
and eight numbered sections (Background → Goals → Locked decisions →
Surfaces → Backwards compatibility → Test plan → Implementation
notes → Cross-references). Frontmatter: `status: draft`,
`agent: architect`, parent reference to `s0002`.

### Defects observed

1. **Indirect-but-safe body delivery, not the obvious-and-safe one.**
   The agent wrote the body to a tempfile (good — same instinct that
   would have fixed Case A) but reached for `--body "$(cat file)"`
   instead of `--body-file file`. Both are safe in this case (see
   Finding 6 below) but the CLI provides `--body-file` precisely so
   agents don't have to reason about shell substitution semantics.
2. **`artifacts kinds spec` doesn't work.** The agent's instinct to
   drill into kind detail by subcommand is reasonable; the CLI's
   refusal is friction. Not catastrophic — the agent fell back to
   reading source — but each such failure costs a tool call and
   nudges agents toward direct file reads.
3. **Runner is just a launcher.** `os run arch` starts a Claude
   Code session with the architect profile but injects no
   kind-template-loading discipline. The architect succeeded at
   structural fidelity because its *agent spec* contains the prose
   "Respect existing conventions — read artifacts-os before
   proposing changes" — and the agent operationalised that as
   "read `kinds/spec/ARTIFACT.md` + the nearest sibling spec + the
   relevant source modules". The discipline is **emergent from
   agent-spec prose**, not encoded as an explicit instruction.

### Diagnosis

The agent read significantly more context up front than `@researcher`
did in Case A. Confirmed reads include the kind contract
(`artifacts/kinds/spec/ARTIFACT.md`), an existing spec
(`s0002-artifacts-os-architecture` for shape reference), and six
core source modules. Three plausible drivers:

- **Agent spec prose.** `@architect` carries the explicit
  "Respect existing conventions — read artifacts-os before
  proposing changes" line; `@researcher` does not.
- **Model + effort tier.** `@architect` runs Opus 4.7 with `xhigh`
  effort; `@researcher` runs Sonnet 4.6 with `high`. Higher-effort
  Opus tends to read more context before acting.
- **Task shape.** Spec authoring is procedurally heavier than ad-hoc
  research synthesis and naturally invites convention-mirroring.

The honest revision of the earlier "imitation, not contract" framing:
**the architect did read the contract** (`kinds/spec/ARTIFACT.md`) —
it just did so emergently, because the agent-spec prose nudged that
direction, not because any system rule said "read the kind template
before authoring". Different agents (e.g. `@researcher`) interpret
their own prose differently; the contract-reading discipline does
not transfer for free.

## Cross-cutting comparison (now three cases)

| Aspect | Case A — `r0004` | Case B — `r0005` | Case C — `s0019` |
|---|---|---|---|
| Trigger | `@researcher` agent | `artifacts create --kind research` (loader path) | `os run arch` (OpenStation runner) + `@architect` |
| Model + effort | Sonnet 4.6, high | n/a | Opus 4.7, xhigh |
| Authoring engine | LLM (skill-driven) | None | LLM (skill-driven) |
| Body delivery | `--body "literal..."` | (loader emits body) | `--body "$(cat tempfile)"` |
| Shell-expansion safety | **unsafe** — backticks evaluated | safe — Python I/O | safe — one-pass `$(…)` |
| Reconnaissance reads | 1 file, 2 dirs | n/a | kind `ARTIFACT.md` + `s0002` + 6 core source modules |
| Read kind's `ARTIFACT.md`? | no | n/a (loader uses it) | **yes (confirmed in trace)** |
| Structural fidelity | freelanced | template-perfect | matches kind contract (read directly) |
| Substantive content | yes (corrupted bytes) | none (placeholders) | yes |
| Self-assigned `agent` frontmatter | no | n/a | yes (`agent=architect`) |
| Side-effects on working tree | yes (`git reset --hard` ran) | none | none |

The matrix shows three different "shapes" of failure mode:

- **Case A**: rich content, broken bytes, drifted shape, no kind-contract awareness.
- **Case B**: clean bytes, perfect shape, no content.
- **Case C**: rich content, clean bytes, kind contract read directly — but the discipline is emergent from agent-spec prose, not enforced.

## New findings (extending `n0006`)

### Finding 6 — `--body "$(cat file)"` is safe but the wrong path of least resistance

When `$(cat file)` runs inside double quotes, command substitution is
**one-pass**: the file's bytes replace the substitution token and are
not re-scanned for further `$()`/backticks. So Case C avoided the
Case A bug — but only because of a shell-semantics subtlety the agent
had to get right. Two consequences:

1. **It's brittle as a pattern.** A small variation —
   `--body $(cat file)` (no outer quotes) → word-splits the body. Or
   `--body "$(eval cat file)"` → re-evaluates. Or trailing newline
   stripping by `$(...)` mutates the body. The pattern works only
   when the agent gets the quoting exactly right.
2. **It bypasses `--body-file`, which exists for this exact case.**
   `--body-file path` is the obvious-and-safe option. `$(cat path)`
   is the indirect-and-conditionally-safe option. If agents reach
   for the latter, the former is failing as a discoverability /
   training affordance.

This sharpens `[[t0088-fix-shell-expansion-footgun-in]]` R4
("update authoring guidance for skills / commands"): it is not enough
to say "don't use `--body \"literal\"`"; the guidance must also
**prefer `--body-file` over `--body \"$(cat …)\"`**. Otherwise agents
will route around the warning into the conditionally-safe pattern.

### Finding 7 — `artifacts kinds <name>` is a missing affordance

The agent tried `artifacts kinds spec` to inspect a single kind. The
CLI rejected it. This is a recurring shape — discovery commands on
collections often want a "drill into one" sibling — and its absence
nudges agents toward direct file reads of `artifacts/kinds/<name>/`.
Worth filing as a separate small task; not in scope here.

### Finding 8 — Reconnaissance discipline correlates with structural fidelity (with confounders)

Case A: 1 file read up front → freelanced shape.
Case C: kind `ARTIFACT.md` + sibling spec + six source modules read
up front → matches kind contract.

The pattern: **agents that read reference artifacts before authoring
hit the kind contract more reliably**. But the variables are tangled:

| Variable | Case A (`@researcher`) | Case C (`@architect`) |
|---|---|---|
| Agent-spec prose nudging context-reading | absent | present ("Respect existing conventions — read artifacts-os before proposing changes") |
| Model | Sonnet 4.6 | Opus 4.7 |
| Effort tier | high | xhigh |
| Task type | ad-hoc research | spec authoring |

Each of these plausibly contributes. We cannot, from N=2, attribute
the gap to any single cause. The body-loader command (Case B) sidesteps
the question entirely — it makes contract-loading structural rather
than agent-by-agent emergent — which is exactly the argument for why
D1 in `n0006` (keep the loader) holds even when, as in Case C, an
agent gets it right by reading.

### Finding 9 — Self-assignment of the `agent` frontmatter field

Case C set `--fields status=draft agent=architect`. The architect
stamped its own identity on the artifact. Case A did not (only
`status=draft`). The body-loader command (Case B) cannot do this
automatically — it has no knowledge of which agent invoked it — so
self-assignment is unambiguously the LLM's responsibility.

This is small but real. A vault where the `agent` field is reliably
populated lets future queries answer "what has architect been
producing?" without trace excavation. Whether to mandate it across
agents (and which agents the convention applies to) is an open
question for the agent-spec audit hinted at in `n0006` D2.

## Decisions reaffirmed / sharpened

- **D1 (n0006)** — keep the body-loader command. **Reaffirmed.** Case
  C demonstrates that even a competent agent's structural fidelity
  is downstream of reading reference material *that the agent
  decided to read on its own initiative*. The kind contract being
  read at all depends on agent-spec prose, model, effort tier, and
  task shape — none of which the system enforces. The loader makes
  contract-loading structural rather than agent-by-agent emergent.
- **D2 (n0006)** — update kind-authoring agent specs to be aware of
  `ARTIFACT.md`. **Sharpened.** The `@architect`'s success
  generalised "Respect existing conventions — read artifacts-os
  before proposing changes" into reading the kind contract + the
  nearest sibling + the relevant source modules. The right
  discipline to encode is "read the kind's `ARTIFACT.md` + the
  nearest sibling artifact + relevant source/docs", not just
  "read `ARTIFACT.md`". `@researcher` would benefit from an
  explicit version of this prose.
- **D3 (n0006)** — skills must use `--body-file` or stdin. **Extended
  by Finding 6:** guidance must also actively *prefer*
  `--body-file path` over `--body "$(cat path)"`, because agents
  will route around the bug warning into the conditionally-safe
  workaround if not redirected.

## New open questions

### Q4 — Should `--fields agent=…` be auto-populated from agent context?

If the CLI knew the invoking agent (env var, config, runtime
context), it could set `agent=…` automatically and the LLM would not
need to remember (Finding 9). Out of scope for this note; flagged for
a future spec or a body-loader extension.

### Q5 — Should `artifacts kinds <name>` show kind detail?

Friction observed in Case C (Finding 7). Small CLI affordance that
would reduce the "drill into source" fallback. Candidate task.

### Q6 — Why did the architect read so much more context than the researcher?

The variables (Finding 8 table) are tangled: agent-spec prose, model
(Sonnet vs Opus), effort tier (high vs xhigh), task type. Worth
running a controlled comparison — same model + effort, two agent
specs differing only in the "Respect existing conventions" line — to
isolate the prose's contribution. Until then, treat agent-spec prose
as the cheapest leverage and update `@researcher`'s spec
speculatively.

### Q7 — Should agent specs encode `read kinds/<kind>/ARTIFACT.md` as an explicit step, not implicit prose?

`@architect` got there by generalising "Respect existing
conventions". `@researcher` did not. The reliable fix is an
explicit instruction: "Before authoring an artifact of kind X, read
`artifacts/kinds/X/ARTIFACT.md`." This works without the body-loader
(Case A flow) and complements it (the loader provides the skeleton;
the agent reads the prose for guidance). Candidate addition to a
shared "kind-authoring agents" skill rather than per-agent prose
duplication.

## How to act on this note

1. Roll Finding 6 into `[[t0088-fix-shell-expansion-footgun-in]]` R4
   when that task is picked up: explicit "prefer `--body-file` over
   `--body \"$(cat file)\"`" guidance.
2. Treat Finding 7 (missing `artifacts kinds <name>`) as a candidate
   for a small follow-up task; don't bundle into t0088.
3. Treat Q6 (reconnaissance volume) as input to any future audit of
   kind-authoring agent specs (the `n0006` D2 follow-up).
4. Use Cases A / B / C together as worked examples in body-loader
   documentation: A shows what skill-only looks like (no
   contract-reading), B shows what loader-only looks like (contract
   without content), C shows skill + *emergent* contract-reading
   (good output, but the agent had to figure out to read
   `ARTIFACT.md` on its own). The full pipeline — loader + agent
   that *systematically* reads `ARTIFACT.md` + `--body-file` — is
   what we want and is not yet what any of the three cases
   demonstrates end-to-end.

## References

- [[n0006-artifact-creation-cases-r0004-vs]] — parent note (Cases A and B)
- [[r0004-computer-use-cli-vs-mcp]] — Case A artifact
- [[r0005-cli-vs-mcp-for-agents]] — Case B artifact
- [[s0019-artifacts-os-public-api]] — Case C artifact (this note's subject)
- [[s0002-artifacts-os-architecture]] — reference spec the architect read for shape
- [[t0088-fix-shell-expansion-footgun-in]] — bug task; Finding 6 sharpens R4
- [[s0018-artifact-md-body-loader-for]] — body-loader spec (Case B's mechanism)
- [[t0086-implement-artifacts-create-body-loader]] — body-loader implementation task
- `artifacts/kinds/spec/ARTIFACT.md` — spec kind template (**confirmed read** by the architect)
- `artifacts/agents/architect.md` — `@architect` spec; carries the "Respect existing conventions" line that drove reconnaissance
- `artifacts/agents/researcher.md` — `@researcher` spec; Case A baseline (no equivalent prose)
- `src/artifacts_os/core/__init__.py` — read by the architect to ground the spec
- `src/artifacts_os/core/models.py` — read by the architect
- `src/artifacts_os/core/store.py` — read by the architect
- `src/artifacts_os/core/discover.py` — read by the architect
- `src/artifacts_os/core/registry.py` — read by the architect
- `src/artifacts_os/core/errors.py` — read by the architect