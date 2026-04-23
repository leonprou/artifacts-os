---
name: openstation.create.spec
description: Create a spec artifact. $ARGUMENTS is the spec topic or design question. Use when user says "create a spec", "write a spec for X", or "design Y".
---

# Create Spec Artifact

Create a specification artifact in `openstation/specs/`.

## Input

`$ARGUMENTS` — the spec topic or design question (free text).

## Procedure

1. Take the topic from `$ARGUMENTS`.

2. **Draft the spec.** Present a complete draft in one message.
   Do not create files yet.

   The draft must include:

   - **Title** — concise name for the specification
   - **Design summary** — what this spec defines and why
   - **Scope** — what's in and out of scope
   - **Producing task** (if known) — which task prompted this
     spec. Ask the user if unclear.

   End with: **"Approve, or tell me what to change."**

3. **Iterate only if needed.** If the user approves, proceed.
   If they request changes, apply and re-present.

4. **Create the artifact file.** Use the CLI:

   ```bash
   openstation create "<title>" \
     --kind spec \
     [--task <producing-task-id>]
   ```

   The CLI assigns the next available ID for the specs
   directory and creates the file atomically.

5. **Fill in the body.** Edit the generated file to include the
   approved content:

   ```markdown
   # <Title>

   ## Summary

   <Design summary — what this spec defines and why>

   ## Scope

   <What's in and out of scope>
   ```

6. Confirm the file was created and show the path.
