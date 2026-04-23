---
name: openstation.create.research
description: Create a research artifact. $ARGUMENTS is the research topic or question. Use when user says "research X", "investigate Y", or "look into Z".
---

# Create Research Artifact

Create a research artifact in `openstation/research/`.

## Input

`$ARGUMENTS` — the research topic or question (free text).

## Procedure

1. Take the topic from `$ARGUMENTS`.

2. **Draft the research spec.** Present a complete draft in one
   message. Do not create files yet.

   The draft must include:

   - **Title** — concise name for the research
   - **Questions to answer** — what the research should resolve
   - **Scope** — what's in and out of scope
   - **Producing task** (if known) — which task prompted this
     research. Ask the user if unclear.

   End with: **"Approve, or tell me what to change."**

3. **Iterate only if needed.** If the user approves, proceed.
   If they request changes, apply and re-present.

4. **Create the artifact file.** Use the CLI:

   ```bash
   openstation create "<title>" \
     --kind research \
     [--task <producing-task-id>]
   ```

   The CLI assigns the next available ID for the research
   directory and creates the file atomically.

5. **Fill in the body.** Edit the generated file to include the
   approved content:

   ```markdown
   # <Title>

   ## Questions

   1. <Question to answer>
   2. ...

   ## Scope

   <What's in and out of scope>
   ```

6. Confirm the file was created and show the path.
