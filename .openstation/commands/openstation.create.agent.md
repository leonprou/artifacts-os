---
name: openstation.create.agent
description: Create an agent spec. $ARGUMENTS is the agent name or role description. Use when user says "create an agent", "add agent X", or "new agent for Y".
---

# Create Agent Spec

Create an agent spec in `openstation/agents/`.

## Input

`$ARGUMENTS` — the agent name or role description (free text).

## Procedure

1. Take the name or description from `$ARGUMENTS`.

2. **Draft the agent spec.** Present a complete draft in one
   message. Do not create files yet.

   The draft must include:

   - **Name** — kebab-case agent identifier (e.g., `code-reviewer`)
   - **Role** — one-sentence description of the agent's purpose
   - **Capabilities** — what the agent can do (bullet list)
   - **Constraints** — what the agent must not do (bullet list)
   - **Tools** — suggested tools based on the role (e.g.,
     `Read, Glob, Grep, Write, Edit, Bash, WebSearch`)

   End with: **"Approve, or tell me what to change."**

3. **Iterate only if needed.** If the user approves, proceed.
   If they request changes, apply and re-present.

4. **Create the artifact file.** Use the CLI:

   ```bash
   openstation create "<name>" \
     --kind agent
   ```

   The CLI creates the agent spec file atomically in
   `openstation/agents/`.

5. **Fill in the body.** Edit the generated file to include the
   approved content:

   ```markdown
   **On startup**, invoke the `openstation-execute` skill to load the
   task management system context.

   # <Name>

   <Role — one sentence>

   ## Capabilities

   - <capability>
   - ...

   ## Constraints

   - <constraint>
   - ...
   ```

   Also update the frontmatter fields as needed:
   - `description` — the one-sentence role summary
   - `tools` — comma-separated tool list

6. Confirm the file was created and show the path.
