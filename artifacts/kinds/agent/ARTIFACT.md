---
name: agent
description: Defines a named AI agent — its role, capabilities, constraints, tools, and system prompt. Use when you want to give an LLM a stable identity and repeatable skill set for a recurring category of work.
---

# Agent

## What is an agent?

An **agent** is a named, role-scoped AI worker. It carries a system
prompt that establishes its identity, capabilities, and constraints;
a `tools` or `allowed-tools` list that bounds what it may do; and
an optional `skills` list that links to skill docs it should invoke
for specific tasks.

Agents live under `artifacts/agents/` and are referenced by `assignee`
and `owner` fields in task frontmatter. The CLI uses the `agent` kind
to validate assignee values and surface agent descriptions in `artifacts
list agents`.

## Key fields

| Field | Purpose |
|---|---|
| `name` | Slug identifier — matches the filename stem. Used in task `assignee`/`owner` fields. |
| `description` | One-line role summary shown in list views. |
| `model` | Preferred LLM (e.g. `claude-opus-4-7`). Optional; harness falls back to its default. |
| `tools` | Comma-separated list of allowed tools (legacy format). |
| `allowed-tools` | YAML list of allowed tools with optional glob patterns (e.g. `Bash(git *)`). Preferred over `tools`. |
| `skills` | YAML list of skill names this agent should invoke at startup or during work. |
| `aliases` | YAML list of alternate names the harness may use to match task assignees. |

## How to author an agent

### Step 1 — Define the role boundary

Start with one sentence: "You are a [role]." State the primary output
(specs, code, docs, research) and the lifecycle gate the agent owns
(e.g. "you approve or reject tasks assigned to architect"). Keep the
system prompt focused — agents that try to do everything do nothing
well.

### Step 2 — Pick the right tool surface

Least-privilege: only list the tools actually needed. Use
`allowed-tools` (YAML list) rather than `tools` (comma string) for
new agents — it supports glob patterns (`Bash(git *)`) and is
easier to audit.

### Step 3 — Link skills

If the agent operates within OpenStation or a similar harness, list
the skills it should invoke at startup. The harness loads skill docs
from `artifacts/` or the wheel bundle.

### Step 4 — Write the system prompt

The body below the frontmatter IS the system prompt. Structure it
with `##` sections for Capabilities, Constraints, and Workflow.
Constraints are as important as capabilities — state explicitly what
the agent must NOT do (e.g. "never make architectural decisions").

## Skeleton

```markdown
---
kind: agent
name: {{slug}}
description: >-
  One-line role summary shown in list views.
model: claude-opus-4-7
skills:
  - openstation-execute
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - "Bash(openstation *)"
---

**On startup**, invoke the `openstation-execute` skill.

# {{Title}}

You are a {{role}}. Your job is to {{primary output}}.

## Capabilities

- {{Capability 1}}
- {{Capability 2}}

## Constraints

- {{What this agent must NOT do}}
```
