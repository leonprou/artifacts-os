---
kind: task
id: t0159
name: add-integrator-agent-for-forward
type: feature
status: backlog
assignee: architect
owner: user
created: 2026-05-15
---

# Add Integrator Agent For Forward-Deployed Integrations

## User story

**As a** project adopting artifacts-os (or openstation, or a future
artbook distro), **I want** a dedicated *integrator* agent that
acts as a forward-deployed engineer for my project **so that** I
have a hands-on partner who understands my conventions, can wire
the harness into my workflow, debug integration friction, and feed
adoption signals back to the artifacts-os roadmap.

## Why

- **Adoption is the killer test of the artbook distribution model.**
  Per [[n0014-books-integration-roadmap]], Phase 1 (agents +
  commands) is about to produce real consumer touchpoints. We have
  no agent whose explicit job is sitting with a consumer through
  the first install, the first migration, the first conflict.
- **The current lineup has a gap.** `devrel` ships broadcast
  content (articles, tutorials, demos). `technical-writer` writes
  generic reference docs. Neither does 1:1 integration work for a
  specific consumer project. `developer` writes artifacts-os code,
  not consumer-side adaptation. `project-manager` runs *our*
  delivery flow, not the consumer's adoption flow.
- **Integration friction is a feedback channel we're losing today.**
  Without a named role that owns "what hurt when this project
  tried to adopt us", we keep relearning the same onboarding
  papercuts. An integrator's discovery notes are direct input to
  `pdm` strategy and the backlog.
- **Forward-deployed engineering is a known-good pattern.** Palantir-
  style FDEs and modern devtool companies (Vercel, Linear, Retool)
  consistently use an embedded-with-customer role to compress the
  loop between product and adoption. It's the missing seat at our
  table.

## Directions (intent, not contract)

- New agent file `artifacts/agents/integrator.md`, matching the
  shape of existing agents (`devrel.md`, `technical-writer.md`).
- **Scope of work** the agent owns:
  - Onboarding a consumer project (e.g. helping them run
    `artifacts init`, configure `artbook.distro_url`, pull their
    first books).
  - Tailoring the harness to the consumer's conventions (their
    kinds, their slug rules, their existing `.claude/` setup).
  - Debugging integration friction — pull failures, command-name
    collisions, agent-name collisions, schema migrations.
  - Authoring migration helpers (e.g. v1 → v2 artbook schema
    bumps) targeted at a specific consumer's state.
  - **Capturing every integration session as a discovery note**
    under `artifacts/research/` or `artifacts/notes/`, surfacing
    friction back to `pdm` as feature signal.
- **Boundaries with adjacent agents** — describe explicitly in the
  agent file:
  - vs `devrel`: integrator is 1:1 hands-on; devrel is broadcast
    1:many content.
  - vs `technical-writer`: integrator writes consumer-specific
    runbooks and migration scripts; technical-writer writes
    generic, version-stable reference docs.
  - vs `developer`: integrator does *not* modify artifacts-os
    source. When an integration reveals a real bug or missing
    feature, they hand off (via `pdm` task or `project-manager`
    triage) to `developer`.
  - vs `project-manager`: integrator runs the *consumer's*
    adoption flow; PM runs the artifacts-os repo's delivery flow.
  - vs `pdm`: integrator is the *eyes-on-the-ground* feeding
    `pdm`; `pdm` decides which signals become roadmap.
- **Tools and permissions** should reflect the FDE role: read
  consumer state freely, but writes should be scoped to artifacts
  under `artifacts/` and to consumer files only via clearly
  intentional commands (no broad `Write` against the consumer's
  source).
- **Alias**: short and not colliding with `int`/`if` shells.
  `fde` is a candidate. Final choice belongs to the agent's
  author.

## Open questions

- **Where does this agent live?** In the artifacts-os repo (so
  every consumer who pulls the agents book gets it), or as part
  of a separate "deployment harness" / openstation-side distro?
  Default answer: in this repo, shipped via the existing `agents`
  book — but flag for architect review.
- **What's the agent's authority on consumer files?** Pure-read +
  generate-scripts-for-the-human-to-run, or allowed direct write
  to the consumer's working tree? FDE pattern usually trends
  toward direct action; security posture may push us toward
  scripts-only initially.
- **Hand-off contract to `developer`.** What does a "this is now
  a real bug" escalation look like — a `pdm` feature task, a
  direct `developer` task, or an alert?
- **Does the integrator have a skill of its own?** E.g. an
  `integrator-onboarding` skill that codifies the first-30-minutes
  walkthrough.

## Sub-tasks

- **Architect spec sub-task** (recommended): settle the integrator's
  place in the boundary diagram, the authority/permissions model,
  and the hand-off contracts to `developer` / `pdm`. Without this,
  the agent file risks restating existing roles instead of carving
  the genuine new seat.
- **Author sub-task** (after spec): write `artifacts/agents/integrator.md`
  matching the conventions of existing agent files.

## Verification

- `artifacts show agent integrator` returns the new agent
  definition with `kind: agent`, a stable alias, and the
  boundaries section explicitly naming `devrel`,
  `technical-writer`, `developer`, `project-manager`, `pdm`.
- `artifacts list agent` includes `integrator` in the agent
  inventory.
- A first real engagement — e.g. integrating artifacts-os into
  one external project (or a fresh repo as a stand-in) — produces
  at least one discovery note under `artifacts/research/` or
  `artifacts/notes/` authored by the integrator, capturing
  friction surfaced during the integration.
