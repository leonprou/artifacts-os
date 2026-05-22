---
name: artifacts.create
description: Create a new artifact in the active vault. $ARGUMENTS supplies the artifact title plus optional kind, body, slug, and frontmatter overrides. Use when the user says "create a <kind>", "new artifact", "scaffold a <kind>", or asks to draft a new file under artifacts/.
---

# Create Artifact

Create a new artifact in the active vault using `artifacts create`. The CLI
resolves the kind, derives an ID + slug, writes the file under the kind's
storage directory, and prints the canonical file stem so callers can use it
as a ref.

## Input

`$ARGUMENTS` — a free-form artifact title plus optional `key:value` tokens
and flag-style suffixes. The title is **required**; everything else is
optional.

| Token | Effect |
|---|---|
| *(free text)* | Treated as the artifact title (positional). The slug is derived from this unless `name:<slug>` is supplied. |
| `kind:<value>` | Pick the kind explicitly. Otherwise the CLI resolves: explicit flag → `cli.defaults.create.kind` in `artifacts.yaml` → built-in fallback. |
| `name:<slug>` | Override the auto-derived slug; the title still appears in the body. |
| `body:<text>` | Inline body content. |
| `body-file:<path>` | Read body from a file; `body-file:-` reads from stdin. |
| `assignee:<value>` | Set frontmatter `assignee` (when the kind exposes it). |
| `owner:<value>` | Set frontmatter `owner` (when the kind exposes it). |
| `parent:<ref>` | Set frontmatter `parent`; bare refs auto-wrap as `[[ref]]`. |
| `depends-on:<ref>` | Append a dependency; bare refs auto-wrap as `[[ref]]`. Repeat the token to add more. |
| `fields:<KEY=VALUE>` | Generic frontmatter escape hatch; repeat for multiple. Comma-separated values become a list (`tags=a,b,c`). |
| `dry-run` | Preview the resolved frontmatter + body without writing. |

If the user has not specified a kind, **do not** fall straight through to
the configured default. Run `artifacts kinds -j` first and pick the kind
whose `description:` field matches the user's request — the description
encodes both the *what* (what the kind captures) and the *when* (which
signals indicate this kind over alternatives). The
`artifacts-os` skill's "Selecting a kind" subsection covers the full
contract; honour it here.

## Procedure

Before running `artifacts create`, draft the body from the chosen kind's
`ARTIFACT.md`:

1. Load the chosen kind's `ARTIFACT.md` body with
   `artifacts kinds <KIND>` (text) or `artifacts kinds <KIND> -j`
   (JSON `{meta, body}`).
2. Extract the `## Skeleton` section — or the matching
   `## Variants/<name>` section per the precedence locked in
   s0018 § 5.1: **explicit user-requested variant** > **`--type` token
   when the kind's `ARTIFACT.md` frontmatter declares
   `variant_field: type`** > **default `## Skeleton`**. Strip the
   surrounding ` ```markdown … ``` ` fence if present.
3. Substitute `{{TITLE}}` with the artifact's title. **Leave every other
   `{{TOKEN}}` placeholder literal** — they are intentional draft prompts
   for the agent to fill in after the file lands (s0018 D1, D3).
4. Pass the resolved body to the CLI via `--body-file -`.

When the chosen kind has no `ARTIFACT.md`, or its `ARTIFACT.md` has no
`## Skeleton` section (and no variant applies), skip the body step,
create with an empty body, and surface a one-line note:
`info: kind '<KIND>' has no ARTIFACT.md; created with empty body.`
This matches the `body_loader.py` policy (s0018 § 6); do not synthesise a
generic stub. The `artifacts-os` skill's "Drafting the body from
ARTIFACT.md" subsection has the worked example.

This selection + scaffolding flow lives at the agent layer; the CLI
itself never reads `ARTIFACT.md` bodies (s0018 D6/D7). Then run
`artifacts create` with the title positional and the flags translated
from `$ARGUMENTS`:

```bash
# Title only — kind comes from cli.defaults.create.kind in artifacts.yaml
# (or the CLI's built-in fallback when no default is configured)
artifacts create "<TITLE>"

# Explicit kind
artifacts create "<TITLE>" --kind <KIND>

# Override the slug; title is still rendered in the body
artifacts create "<TITLE>" --kind <KIND> --name <SLUG>

# Inline body
artifacts create "<TITLE>" --kind <KIND> --body "<MARKDOWN BODY>"

# Body from a file
artifacts create "<TITLE>" --kind <KIND> --body-file <PATH>

# Body from stdin
echo "<MARKDOWN>" | artifacts create "<TITLE>" --kind <KIND> --body-file -

# Generic frontmatter escape hatch (key=value pairs; commas → list)
artifacts create "<TITLE>" --kind <KIND> --fields priority=<VALUE> tags=<A,B,C>

# Convenience flags (available when the kind's schema declares them)
artifacts create "<TITLE>" --kind <KIND> --assignee <AGENT> --parent <REF>

# Preview without writing
artifacts create "<TITLE>" --kind <KIND> --dry-run
```

**IMPORTANT: Run the command exactly as shown above. Do not modify
the command in any way. Do not add `2>&1`, `2>/dev/null`,
`|| echo`, or any other shell operators.**

| Token / mode | CLI flag |
|---|---|
| `kind:<value>` | `--kind <value>` (alias `-k`) |
| `name:<slug>` | `--name <slug>` |
| `body:<text>` | `--body <text>` (alias `-b`) |
| `body-file:<path>` | `--body-file <path>` (use `-` for stdin) |
| `assignee:<value>` | `--assignee <value>` |
| `owner:<value>` | `--owner <value>` |
| `parent:<ref>` | `--parent <ref>` |
| `depends-on:<ref>` | `--depends-on <ref>` (repeatable) |
| `fields:<KEY=VALUE>` | `--fields <KEY=VALUE> [<KEY=VALUE> ...]` (alias `-f`) |
| `dry-run` | `--dry-run` (alias `-n`) |

### Kind-aware help

The convenience flags exposed on `artifacts create` depend on the chosen
kind. After translating `kind:<value>` to `--kind <value>`, re-run
`artifacts create --kind <KIND> --help` to discover any kind-specific flags
the schema declares (for example, a kind may surface `--priority`,
`--severity`, or other dedicated flags). When you do not yet know the
kind, run `artifacts kinds` first.

### Output

On success the CLI prints a single line — the artifact's canonical file
stem (e.g. `t0046-author-artifacts-create-command`). Surface that stem to
the user; it is the ref they will pass to `/artifacts.show`,
`/artifacts.list` filters, and wikilinks.

## Worked examples

User asks: "create a `<KIND>` titled `Improve onboarding flow`."

```bash
artifacts create "Improve onboarding flow" --kind <KIND>
```

The CLI assigns the next ID for that kind, derives the slug from the
title, writes the file under the kind's storage directory, and prints the
file stem. Follow up with `/artifacts.show <stem>` to inspect it.

User asks: "create a `<KIND>` assigned to `<AGENT>` with parent
`<PARENT-REF>` and a body from `notes.md`."

```bash
artifacts create "<TITLE>" \
  --kind <KIND> \
  --assignee <AGENT> \
  --parent <PARENT-REF> \
  --body-file notes.md
```

`--parent <PARENT-REF>` accepts a bare ref — the CLI auto-wraps it as
`[[<PARENT-REF>]]` in frontmatter. The same applies to `--depends-on`
entries.

User asks: "preview the frontmatter for a new `<KIND>` titled `<TITLE>`
before committing."

```bash
artifacts create "<TITLE>" --kind <KIND> --dry-run
```

The CLI prints the resolved YAML frontmatter and body to stdout under a
`--- dry run (no file written) ---` banner. Nothing is written until the
flag is removed.

For a custom slug or extra frontmatter fields not covered by convenience
flags:

```bash
artifacts create "<TITLE>" \
  --kind <KIND> \
  --name <SLUG> \
  --fields priority=<VALUE> tags=<A,B,C>
```

`--fields` accepts repeated `KEY=VALUE` pairs; comma-separated values are
parsed as a list (`tags=a,b,c` becomes `tags: [a, b, c]`).

## Edge cases

| Situation | Handling |
|---|---|
| Unknown kind | The CLI exits non-zero with a message naming the rejected kind. Run `artifacts kinds` to enumerate registered kinds and re-run with a valid one. |
| `--body` and `--body-file` both passed | The flags are mutually exclusive; the CLI rejects the combination. Pick one based on intent (`--body` for short inline text, `--body-file` for reusable content or stdin). |
| `--body-file -` with no piped input | Stdin is empty — the artifact is written with an empty body. If the user expected interactive input, re-run with `--body "<…>"` or pipe content explicitly (`cat draft.md \| artifacts create … --body-file -`). |
| Slug derivation fails | If `--name` produces an empty slug after slugification (e.g., the value contained no slug-safe characters), the CLI errors with `cannot derive slug from --name <value>`. Re-run with a value that contains letters or digits. |
| Validation failure | Frontmatter rejected by the kind's JSON-Schema → exit code 2 with a message naming the offending field. Either drop the offending `--fields` entry or, for required-but-missing fields, supply them via `--fields` or the appropriate convenience flag. |
| Wikilink fields | `parent`, `depends_on` are wikilink fields. Bare refs (`<REF>`) are auto-wrapped as `[[<REF>]]`. Pre-wrapped values (`[[<REF>]]`) are accepted as-is. |
| Comma-list semantics in `--fields` | Any `KEY=VALUE` whose value contains `,` is split into a list. To store a literal comma, supply the value via `--body-file` or set the field afterwards using a frontmatter editor. |
| Conflicting `kind:<x>` and a `cli.defaults.create.kind` | Explicit `--kind` always wins over the settings default. Pass `--kind` whenever the kind matters. |

## Cross-references

- `artifacts kinds` — discover registered kinds before passing `--kind`.
- `/artifacts.list` — list artifacts (filter by kind/status) to confirm the new file appears.
- `/artifacts.show <ref>` — inspect the created artifact using the file stem the CLI prints.
