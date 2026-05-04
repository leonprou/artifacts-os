---
assignee: author
created: 2026-05-02
id: t0070
kind: task
name: define-product-manager-agent
owner: user
status: done
type: feature
---

# Define `product-manager` Agent

## User Story

**As a** user driving artifacts-os direction,
**I want** a dedicated `product-manager` agent that owns product
strategy, roadmap, market/user discovery, and feature task
authoring,
**so that** product thinking has a clear home — distinct from
`project-manager`'s delivery-coordination role — and feature
tasks land in the backlog with strong user-facing intent before
the architect or developer touches them.

## Why

Today the `project-manager` agent carries two jobs that don't
naturally pair:

1. **Delivery coordination** — backlog flow, agent assignment,
   verification, status promotion. (Project work.)
2. **Requirements capture** — user stories, acceptance criteria,
   feature framing. (Product work.)

There is no agent at all for **strategy, roadmap, or
discovery** — the upstream activities that *decide which
features deserve a task in the first place*. Splitting these
concerns gives each agent a sharper mandate and lets the user
hand off product questions ("should we build X? what would users
need?") to a specialist.

This task is intentionally scoped to **defining the agent
spec**. Updating `project-manager` to remove the now-overlapping
responsibilities is a follow-up.

## Directions

> Intent, not contract. The author owns the final wording,
> structure, and frontmatter shape — match the conventions
> already used by the other agent specs in
> `artifacts/agents/`.

- Create `artifacts/agents/product-manager.md` following the
  same frontmatter pattern as `project-manager.md`,
  `researcher.md`, `devrel.md`, etc. (`kind: agent`, `name`,
  `aliases`, `description`, `model`, `skills`, `tools`,
  `allowed-tools`).
- Pick a non-conflicting alias. `pm` is taken by
  `project-manager`; `pdm` or `prod` are reasonable.
- The agent is **product- and user-oriented**. Its capabilities
  should cover, at minimum:
  - Product **strategy** — articulating the product's purpose,
    positioning, and direction.
  - **Roadmap** — sequencing themes/initiatives over time and
    explaining the rationale.
  - **Market and user discovery** — researching user needs,
    competitive landscape, and adoption signals (delegating
    deep technical research to `researcher` when appropriate).
  - **Feature task creation** — authoring user-story-shaped
    feature tasks with strong "what" and "why", deferring the
    "how" to the architect spec sub-task pattern already used
    by `project-manager`.
- Constraints worth surfacing in the spec:
  - Coordinate and define, **never implement**. No code, no
    technical specs, no architecture decisions.
  - User-facing framing only — the *what* and the *why*, never
    the *how*. Implementation contract belongs to the architect.
  - Do not own backlog flow, agent assignment, status
    transitions, or verification — those remain with
    `project-manager`. The two agents collaborate: product
    defines the feature, project routes and ships it.
  - Keep discovery output as artifacts (research notes,
    roadmap docs) rather than ad-hoc chat — store under
    `artifacts/` in an appropriate location.
- Tooling: the agent reads code/docs and writes artifacts; it
  likely needs `Read`, `Glob`, `Grep`, `Write`, `Edit`,
  `WebSearch`, `WebFetch`, plus the standard `openstation` /
  `ls` / `readlink` bash allowances. Mirror what `researcher`
  and `devrel` already use.
- Include the standard startup line invoking the
  `openstation-execute` skill.

## Open Questions for the Author

- Alias choice: `pdm` vs `prod` vs `product` — pick one and
  note the rationale in the spec.
- Should the spec explicitly enumerate the boundary with
  `researcher` (who does what kind of research)? Recommended
  yes, briefly.
- Should the spec reference a roadmap kind / location, or stay
  silent until a roadmap kind exists? Recommended: stay silent;
  a separate task can introduce a `roadmap` kind if needed.

## Sub-tasks

None — this is a single authoring task. A follow-up task to
**narrow the `project-manager` spec** (remove
requirements-capture language, lean fully into delivery
coordination) should be created by `project-manager` after this
ships.

## Verification

- [ ] `artifacts/agents/product-manager.md` exists and validates
      (`artifacts validate product-manager --kind agent`).
- [ ] Frontmatter matches the conventions of the other agent
      specs (`kind`, `name`, `aliases`, `description`, `model`,
      `skills`, `tools`, `allowed-tools`).
- [ ] Alias does not collide with `project-manager`'s `pm`.
- [ ] Capabilities section explicitly covers strategy,
      roadmap, market/user discovery, and feature task
      creation.
- [ ] Constraints section makes the boundary with
      `project-manager` (delivery coordination) and `architect`
      (technical contract) unambiguous.
- [ ] Agent appears in `artifacts list --kind agent` with a
      clear, accurate description.
- [ ] Follow-up task created to narrow the `project-manager`
      spec (linked from this task on completion).

## Findings

Created `artifacts/agents/product-manager.md` matching the
frontmatter shape used by the other agent specs (`kind`, `name`,
`aliases`, `description`, `model`, `skills`, `tools`,
`allowed-tools`).

Key decisions:

- **Alias `pdm`** — `pm` is `project-manager`. `pdm` is the most
  conventional industry shorthand for *Product Manager* when "PM"
  is taken (Project vs Product disambiguation). Compact and
  collision-free against existing aliases (`pm`, `arch`, `dev`,
  `res`, `dr`, `tw`, `au`).
- **Model `claude-opus-4-7`** — matches `project-manager` and
  `architect`. Strategy, roadmap, and discovery are reasoning-
  heavy coordination work, not throughput work.
- **Tools mirror `researcher` plus `mkdir`** — adds `WebSearch`
  and `WebFetch` for market/competitive discovery, keeps the
  standard `openstation` / `ls` / `readlink` Bash allowances, and
  permits `mkdir` for new artifact subdirectories under
  `artifacts/research/` and `artifacts/notes/` (mirrors `devrel`).
- **Boundaries section explicit** — distinguishes
  `product-manager` from `project-manager` (delivery
  coordination), `architect` (technical contract), `researcher`
  (deep technical evidence), and `devrel`/`technical-writer`
  (post-ship communication). The section directly addresses the
  open question about the `researcher` boundary; the architect-
  spec sub-task hand-off pattern is preserved.
- **Roadmap kind not introduced** — followed the recommendation
  in the task's open questions; roadmap drafts live as notes
  under `artifacts/notes/` until a dedicated kind is justified
  by a separate task.
- **Authoring guide section** — the spec includes an "Authoring
  a Feature Task" section that mirrors the structure already in
  use across `artifacts/tasks/` (User Story / Why / Directions /
  Open Questions / Sub-tasks / Verification) so feature tasks
  emitted by this agent stay consistent with the repo's
  conventions.

Validation:

- `artifacts validate product-manager --kind agent` → 1 valid,
  0 errors, 0 warnings.
- `artifacts list --kind agent` shows `product-manager` with the
  intended description.

Per user direction, `project-manager.md` is **intentionally
left untouched** in this task. The proposed follow-up
[[t0071-narrow-project-manager-spec-to]] was created and then
cancelled — the user opted to add the new agent only, without
narrowing the existing one. The current overlap (both agents
mention requirements/user-story framing) is acknowledged and
left in place for now.

**Revision (per user feedback): more hands-on framing.** The
spec was reworked to make the agent action-oriented rather than
merely "decide and hand off":

- Added an explicit "How you operate" section with a *bias to
  action* directive ("when in doubt, write the user story and
  file the task") and routine use of the `openstation` CLI.
- Promoted **feature-task creation** to a primary, routine
  capability — first in the list, framed as something done end-
  to-end via `openstation create`, not delegated.
- Promoted **user-story authoring and refinement** as a distinct
  capability (write, split, sharpen, sequence) rather than a
  framing concept inside task authoring.
- Added a **product-market fit (PMF)** capability and a
  dedicated "Driving Product-Market Fit" section — explicit PMF
  thesis (target user, job-to-be-done, killer-feature
  hypothesis, signals, running evidence log) maintained as
  `artifacts/notes/product-market-fit.md`. PMF is named the
  agent's north star.
- Loosened the constraints language: dropped "coordinate and
  define, never implement" / "out of delivery's lane" hard-line
  framing in favor of narrower, behavior-shaped constraints (no
  source code, no technical specs; user-facing framing inside
  tasks; don't run delivery for tasks others authored).
- The `architect` boundary (technical contract) and the
  `researcher` boundary (technical-shaped evidence) are
  preserved.

## Downstream

- `project-manager.md` still claims user-story / requirements-
  capture responsibilities that now overlap with
  `product-manager`'s mandate. Left as-is per user direction;
  if/when the user wants to disambiguate, file a fresh task.
- Future consideration (not filed): a dedicated `roadmap` kind
  could formalize roadmap artifacts. Deferred until the agent
  produces enough of them to justify the schema.