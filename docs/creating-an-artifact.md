# Creating a New Artifact

The standard agent flow for creating an artifact instance. Run every
command from the vault root (the directory containing
`artifacts.yaml`).

For adding a *new kind* (registering a new artifact type), see
[`adding-a-kind.md`](adding-a-kind.md).

---

## 1. Discover kinds — `artifacts kinds`

```bash
artifacts kinds              # rich table with description column
artifacts kinds -j           # JSON output
artifacts kinds -q           # one name per line
```

The `description` column is the L1 selection signal — it encodes
both **what** the kind captures and **when** to choose it. Pick the
kind whose description matches the artifact you want to create.

If two kinds look plausible, lean on the *when* clause to
disambiguate. Examples (from the shipped kinds):

- `note` — captures thinking; use when context must outlive the
  conversation.
- `research` — captures cited findings; use when a question
  requires evidence before a design can act.
- `spec` — locks an implementation contract before code; use when
  a change crosses a module boundary, lands across multiple tasks,
  or pins a public surface.

---

## 2. Read per-kind detail — `artifacts kinds <name>`

```bash
artifacts kinds <name>          # full ARTIFACT.md body
artifacts kinds <name> -j       # {"meta": {...}, "body": "..."}
artifacts kinds <name> --meta   # prepend metadata block above body
artifacts kinds <name> -e       # open ARTIFACT.md in $EDITOR (TTY only)
```

Prints the kind's `## What is a <kind>?` definition, selection
table, and `## How to draft a <kind>` authoring guide. **Read this
before writing the body** — it names the required sections,
writing disciplines, and worked-example references for that kind.

Exit code `3` if the kind has no `ARTIFACT.md`. Artifacts of that
kind can still be created; you just won't get body scaffolding
guidance.

---

## 3. Create the file — `artifacts create <kind> "<title>"`

```bash
artifacts create note "morning standup"
# → artifacts/notes/n0042-morning-standup.md
```

- **Numbered kinds** (default): `artifacts/<dir>/<prefix><NNNN>-<slug>.md`
  with a sequential ID — tasks, specs, notes, research.
- **Non-numbered kinds**: `artifacts/<dir>/<slug>.md` — the slug
  *is* the identity (agents, registries).

The file ships with frontmatter only; the body is empty and is
yours to fill in.

---

## 4. Write the body — follow the guide from step 2

Open the new file and draft the body per the `## How to draft a
<kind>` section you read in step 2. Honour the kind's required
sections — for example:

| Kind | Required body sections |
|---|---|
| `note` | `## Origin`, `## References` |
| `research` | metadata block, `## TL;DR`, `## Recommendations`, `## Sources` |
| `spec` | one-paragraph summary, `## Out of Scope`, `## Architecture` (with a diagram), `## Test Plan`, `## Cross-References` — plus `## Components` / `## Data Models` / `## Surfaces` / `## File Structure` when the change touches them |

When in doubt, re-run `artifacts kinds <name>` and re-read the
authoring guide.

---

## 5. Verify

```bash
artifacts validate                # frontmatter validation across vault
artifacts list --kind <kind>      # confirm the new artifact appears
```

`artifacts validate` reports missing required fields and unknown
status values. `artifacts list --kind <kind>` filters the listing
to one kind; pair with `--<property>` flags (auto-generated from
the kind's JSON schema) to filter further.

---

## End-to-end example

```bash
artifacts kinds                                    # 1. discover
artifacts kinds note                               # 2. read the guide
artifacts create note "morning standup"            # 3. create file
$EDITOR artifacts/notes/n0042-morning-standup.md   # 4. write body
artifacts validate                                 # 5. verify
```

---

## Cross-References

- [`docs/adding-a-kind.md`](adding-a-kind.md) — registering a new
  artifact kind (operator task; complementary to this guide).
- [`src/artifacts_os/cli/README.md`](../src/artifacts_os/cli/README.md)
  — full CLI reference, including `--filter`, `--view`, and
  schema-derived filter flag rules.
- [`artifacts/kinds/<name>/ARTIFACT.md`](../artifacts/kinds/) —
  per-kind definition + authoring guide, fetched at runtime by
  `artifacts kinds <name>`.
