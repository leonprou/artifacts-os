---
kind: spec
name: research-spec
---

# Research Specification

Defines the format for research outputs in Open Station. A research
artifact is a markdown document that captures investigation results —
what was found, how confident the finding is, and what sources were
consulted.

For task format see `docs/task.spec.md`.

## File Location

Research artifacts live permanently in `openstation/research/`:

```
openstation/research/<name>.md
```

Research files are created here once and never move.

## Naming

Two naming patterns are used:

- **Numbered** — `NNNN-kebab-slug` for research tied to a specific
  task. Auto-assigned by `openstation create --kind research`. The
  ID counter is per-kind (`openstation/research/` only).
- **Evergreen** — plain `kebab-slug` for reusable reference
  documents not tied to a single task (e.g., `obsidian-plugin-api.md`).

The filename (without `.md`) and the `name` frontmatter field must
match exactly. Never pick NNNN IDs manually — use
`openstation create --kind research`.

> **CLI note:** `openstation create --kind research` **always** assigns a
> `NNNN-` prefix. There is no flag to create an evergreen (plain-slug)
> research file via the CLI. To create an evergreen reference document
> (e.g. `obsidian-plugin-api.md`), create the file directly in
> `openstation/research/` with the correct frontmatter — the CLI is not
> involved.

## Frontmatter Schema

```yaml
---
kind: research                         # Required. Always "research".
name: 0042-oauth-provider-comparison   # Required. Matches filename (without .md).
agent: researcher                      # Optional. Agent that created this.
task: "[[NNNN-task-slug]]"             # Optional. Producing task (wikilink).
created: YYYY-MM-DD                    # Required. Date research was produced.
tags:                                  # Optional. Topic tags for discovery.
  - authentication
  - oauth
---
```

### Field Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `kind` | string | yes | — | Always `research` |
| `name` | string | yes | — | Kebab-case slug, matches filename (without `.md`) |
| `agent` | string | no | empty | Agent that produced this artifact. Use `manual` for human-authored research. |
| `task` | string | no | empty | Wikilink to the task that produced this artifact (`"[[NNNN-slug]]"`) |
| `created` | date | yes | — | ISO 8601 date (`YYYY-MM-DD`) when the research was written |
| `tags` | list | no | `[]` | Topic tags for discovery and filtering |

## Body Structure

The markdown body follows the frontmatter. It starts with an H1
title and a Summary section, followed by detailed findings.

### Required Sections

#### `# Title`

Human-readable description of what was researched as an H1 heading.

#### `## Summary`

The most important findings, stated up front. A reviewer should be
able to act on the Summary alone without reading the rest of the
document.

Include:
- Key conclusions (what did you find?)
- Which option/approach/pattern is recommended, if applicable
- Any critical caveats or unknowns

Lead with conclusions, not process narrative.

### Recommended Sections

#### `## <Topic>` or `## <Item>`

One section per major topic, source, or item investigated. For
comparative research, one section per option. For framework/tool
research, one section per framework/tool.

Each section should state:
- **What it is** — brief description of the subject
- **What was found** — concrete findings
- **Confidence level** — how certain the finding is (see below)

#### Confidence Labels

Tag each major finding with a confidence level:

| Label | Meaning |
|-------|---------|
| **Confirmed** | Verified against primary source (docs, code, spec) |
| **Likely** | Based on indirect evidence or multiple secondary sources |
| **Unknown** | Could not verify — explicitly flag as uncertain |

Use inline labels rather than a separate section:
```markdown
**Confidence**: Confirmed (verified against GitHub source)
```

### Optional Sections

| Section | Purpose |
|---------|---------|
| `## Recommendations` | Actionable suggestions derived from findings |
| `## Rejected Approaches` | Options evaluated and ruled out, with reasons |
| `## Open Questions` | Unknowns that warrant further investigation |
| `## Sources` | Links and references consulted |

## Provenance

Research artifacts must declare provenance in frontmatter:

```yaml
agent: researcher
task: "[[0044-research-obsidian-plugin-api]]"
```

Use `agent: manual` and omit `task` for manually authored research.
The producing task should also list the artifact in its `artifacts`
field:

```yaml
# In the task frontmatter
artifacts:
  - "[[openstation/research/0044-obsidian-plugin-api]]"
```

## Progressive Disclosure

Research artifacts are typically written in one pass. Add sections
as investigation progresses; do not pre-structure empty sections.

### Rules

1. **Summary first, always** — write the Summary before diving into
   detail sections. If you run out of time, the Summary alone has
   value.
2. **State confidence explicitly** — do not let findings blur into
   speculation. Label every major claim.
3. **Lead with conclusions** — reviewers and downstream agents
   read the top; put the actionable content there.
4. **Flag unknowns, don't omit them** — an explicit "Unknown"
   finding is more useful than silence.

## Example

### Comparative research

```markdown
---
kind: research
name: 0042-oauth-provider-comparison
agent: researcher
task: "[[0042-research-oauth-providers]]"
created: 2026-03-15
tags:
  - authentication
  - oauth
---

# OAuth Provider Comparison

## Summary

Three providers evaluated: Auth0, Clerk, and Supabase Auth.
Clerk is the strongest fit for Open Station's use case — minimal
setup, built-in agent-friendly API keys, and no self-hosting
requirement. Auth0 is viable but overkill for current scale.
Supabase Auth requires more configuration for non-standard flows.

---

## Auth0

**Confidence**: Confirmed (primary docs reviewed)

Mature, full-featured IdP. Supports all standard OAuth flows.
Pricing scales with MAU; free tier covers 7,500 MAU.

Downside: significant configuration surface for simple use cases.
Management API requires a separate token flow.

## Clerk

**Confidence**: Confirmed (primary docs + sandbox tested)

Developer-focused IdP with first-class API key support — ideal
for agent authentication. SDK available for Next.js and plain
fetch. Free tier: 10,000 MAU.

No self-hosting option; vendor lock-in trade-off.

## Supabase Auth

**Confidence**: Likely (docs reviewed, not tested)

Built into Supabase platform. Fine for projects already on
Supabase. Adding it standalone adds infrastructure overhead.

## Recommendations

Use Clerk for new projects. Re-evaluate Auth0 if enterprise SSO
(SAML) is needed in the future.

## Sources

- https://clerk.com/docs
- https://auth0.com/docs
- https://supabase.com/docs/guides/auth
```
