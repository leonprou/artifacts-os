---
assignee: researcher
created: 2026-05-02
id: t0074
kind: task
name: research-claude-skills-design-for
owner: user
parent: '[[t0079-artifact-md-artifacts-ai-extension]]'
status: done
type: research
---

# Research Claude Skills Design for Artifact-Kinds Discovery Alignment

## Goal

Before drafting the spec for the artifact-kinds discovery mechanism
(`[[t0073-spec-artifact-kinds-discovery-mechanism]]`), survey
**Claude Skills design** as a reference architecture and produce a
research artifact (`kind: research`) that captures:

1. How Claude Skills are organised, discovered, and progressively
   loaded.
2. Which patterns map cleanly onto our `kinds/<name>/` layout
   (`kind.json`, `ARTIFACT.md`, `playbooks/`).
3. Where the analogy breaks down or should NOT be copied.
4. Concrete recommendations the architect can lift into the t0073
   spec (catalogue surface, per-kind detail, L1/L2/L3 disclosure
   model, selection signal, fallback semantics).

The output is **a research artifact**, not a spec. No design
decisions are locked here — the architect will weigh the findings
against our locked context (see t0073) and produce the spec.

## Why this is research, not spec input the architect should redo

The user has flagged Claude Skills as a likely-good north star.
Surveying it once, in a research artifact, lets:

- the architect read a focused summary instead of crawling docs
  mid-spec;
- future kinds (not just discovery) inherit the same reference;
- the team disagree explicitly with Anthropic's choices where we
  have reason to.

## Primary source

- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
  (user-supplied; treat as primary).
- Adjacent pages on the same site (Skills overview, Skill structure,
  composition / progressive disclosure) — pull whatever the
  best-practices page links to.
- Use \`context7\` MCP for any current Anthropic docs the page
  references.

## Areas to cover

1. **Skill anatomy.** What files make up a Skill? What is the
   equivalent of our \`kind.json\` + \`ARTIFACT.md\` + \`playbooks/\`?
   Map the parts side by side.

2. **Discovery & catalogue.** How does an agent learn a Skill
   exists? Is there a manifest, a registry, a description blurb,
   tags? What does the L1 surface look like?

3. **Progressive disclosure.** This is the headline alignment.
   Document Anthropic's exact mechanism: what loads when, what
   triggers deeper loading, what stays out of context until used.
   Quote / paraphrase the best-practices guidance.

4. **Selection signal.** How does the agent pick the right Skill
   for an intent? Description text? Examples? Activation keywords?
   What's the contract that makes the choice cheap and reliable?

5. **Variants / sub-modes.** Do Skills have an analogue to our
   \`variants:\` field on \`ARTIFACT.md\`? If so, how are they
   declared and selected?

6. **Authoring & validation.** How are Skills authored, validated,
   versioned? Is there a schema? What's the failure mode when a
   Skill is malformed?

7. **Composition & reuse.** Can Skills reference other Skills?
   Inherit? Compose? Anything we should mirror or deliberately
   avoid?

8. **Anti-patterns.** What does the best-practices page warn
   against? Translate each warning into an artifacts-os equivalent.

9. **Mapping table.** Side-by-side: \`Claude Skill\` ↔
   \`artifacts kind\`. Cell per concept (manifest, description,
   skeleton, examples, etc.). Mark each row as \`adopt\`,
   \`adapt\`, or \`reject\` with one-line rationale.

10. **Recommendations for t0073.** A bulleted list of concrete
    inputs to the spec (e.g. \"L1 should carry one-line
    description from a top-level \`description:\` frontmatter
    key, mirroring Skills' \`description\` field\"). Stay
    directional — the architect locks the contract.

## Constraints

- **No spec language.** Do not invent CLI command names, flag
  shapes, or file paths in this artifact. Findings + analogies +
  recommendations only.
- **Cite.** Every claim about Claude Skills must point to a URL
  or page section.
- **Stay scoped.** This is about Skills as a *reference for
  artifact-kinds discovery*. Do not branch into general agent
  design, tool-use, or sub-agent coordination.
- **Length.** ~1–2 pages of dense markdown is the target. Long
  enough to lock the architect's mental model; short enough to
  read in one sitting.

## Deliverable

A new artifact: \`artifacts create \"<title>\" --kind research\`.
Suggested slug: \`claude-skills-design-reference\`.

The research artifact should:

- include a \`## TL;DR\` (5–10 lines);
- contain the mapping table from area 9;
- end with \`## Recommendations for t0073\` (area 10).

## Verification

- [ ] Research artifact created under \`artifacts/research/\`.
- [ ] All 10 areas covered.
- [ ] Mapping table includes \`adopt\` / \`adapt\` / \`reject\`
      verdict per row.
- [ ] Every Claude Skill claim cites a source URL / section.
- [ ] Cross-links \`[[t0073-spec-artifact-kinds-discovery-mechanism]]\`,
      \`[[n0004-improve-create-command]]\`,
      \`[[n0005-artifact-md-kind-folders-for]]\`.
- [ ] Reviewed by user; t0073 unblocked once approved.