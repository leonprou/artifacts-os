---
name: openstation.create.note
description: Create a planning note artifact. $ARGUMENTS is the note topic or title. Use when user says "create a note", "add a note about X", or "capture planning notes for Y".
---

# Create Note Artifact

Create a planning note artifact in `openstation/notes/`.

## Input

`$ARGUMENTS` — the note topic or title (free text).

## Procedure

1. Take the topic from `$ARGUMENTS`.

2. **Draft the note.** Present a complete draft in one message.
   Do not create files yet.

   The draft must include:

   - **Title** — concise name for the note
   - **Content summary** — what this note captures and its purpose
   - **Producing task** (if known) — which task prompted this
     note. Ask the user if unclear.

   End with: **"Approve, or tell me what to change."**

3. **Iterate only if needed.** If the user approves, proceed.
   If they request changes, apply and re-present.

4. **Create the artifact file.** Use the CLI:

   ```bash
   openstation create "<title>" \
     --kind note \
     [--task <producing-task-id>]
   ```

   The CLI assigns the next available ID for the notes
   directory and creates the file atomically.

5. **Fill in the body.** Edit the generated file to include the
   approved content:

   ```markdown
   # <Title>

   <Content summary and notes>
   ```

6. Confirm the file was created and show the path.
