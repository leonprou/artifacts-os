---
name: release-changelog
description: Generate a task-aware changelog entry for a new release from conventional commits, the producing tasks, and the project's `## Release` section in CLAUDE.md.
user-invocable: false
---

# release-changelog

Generate a changelog entry for a new release. Reads project shape
(domain categories, path mapping, release checklist) from the
`## Release` section in `CLAUDE.md`, and enriches each entry with
the originating task's intent (`name`, `## Findings`, `## Goal`)
for every commit that carries a `(tNNNN)` trailer.

## When to Use

Use this skill when preparing a release — after all work is merged
to `main` and before pushing the release commit. The skill produces a
draft changelog entry for human review; it never auto-commits or auto-tags.

## Prerequisites

- All release work is merged to `main`.
- `CHANGELOG.md` exists at the repository root.
- `CLAUDE.md` at the repository root contains a `## Release` section
  with the required H3 subsections (`### Domain Categories`,
  `### File Path Mapping`, `### Checklist`).
- Git tags follow semver with a `v` prefix (`v0.1.0`, `v0.2.0`).
- Commits use conventional prefixes (`feat:`, `fix:`, `docs:`,
  `refactor:`, `chore:`, `test:`).

---

## Workflow

### Step 0 — Idempotency Check

Before generating anything, check whether the target version
already has an entry in `CHANGELOG.md`.

```bash
grep -q "^## v<VERSION>" CHANGELOG.md
```

- **If found** — Stop and ask: "CHANGELOG.md already has an entry
  for v\<VERSION\>. Regenerate and replace it, or skip?"
- **If not found** — Proceed.

If the user has not specified a target version, do NOT invent one.
Proceed through Steps 1–4 first, then recommend a version in
Step 5 based on change severity.

### Step 1 — Determine Release Range

Find the latest release tag and scope the commit range.

```bash
# Latest tag
git tag --sort=-v:refname | head -1

# Verify it exists and note its date
git log -1 --format="%ai" <last-tag>
```

The range is `<last-tag>..HEAD`. If no tags exist, use the full
history (`--root..HEAD`) — first release.

**After determining the range, parse `CLAUDE.md`:** locate the
`## Release` section and its four well-known H3 subsections:

- `### Domain Categories` — the ordered list of category names.
- `### File Path Mapping` — the two-column markdown table mapping
  path prefixes to category names.
- `### Checklist` — the numbered release checklist (used in Step 8).
- `### Exclusions` *(optional)* — glob paths and subject regexes to
  drop before categorisation.

If `CLAUDE.md` is missing, `## Release` is absent, or any of
`### Domain Categories`, `### File Path Mapping`, or `### Checklist`
is missing or malformed, **halt immediately** with:

```
release-changelog: cannot draft — CLAUDE.md is missing the `## Release` section
(or it is malformed). Required H3s: Domain Categories, File Path Mapping, Checklist.
See `docs/release.md` for the contract.
```

Do not proceed to Step 2.

### Step 2 — Collect Commits

Gather commit subjects, task trailers, and file-change stats for the range.

```bash
# Commit hashes and subjects
git log --format="%H %s" <last-tag>..HEAD

# Files changed per commit (for category hints)
git log --format="%H" <last-tag>..HEAD | while read h; do
  echo "=== $h ==="
  git diff-tree --no-commit-id --numstat -r "$h"
done
```

Exclude merge commits and `chore:` commits that are purely
internal (CI config, tooling tweaks with no user-facing impact),
and any commits matching `### Exclusions` patterns.

**Task-trailer extraction:** for each commit subject, apply the regex:

```
\(\s*t(\d{4,})(?:\s*,\s*t(\d{4,}))*\s*\)
```

Capture all task IDs in the parentheses. A commit with no matching
trailer is flagged for the Fallbacks summary (Step 6). A commit
with multiple IDs (e.g. `(t0099, t0100)`) retains all IDs.

**Task-file resolution:** for each captured task ID:

1. Walk up from CWD until a directory contains
   `artifacts/artifacts.yaml`. That is the vault root.
2. Glob `<vault-root>/artifacts/tasks/t<id>-*.md`.
3. Exactly one match → load and read frontmatter + body sections.
   Zero matches → flag missing-task fallback. Two or more →
   flag ambiguous-task fallback (use the first; warn).

### Step 3 — Parse and Categorize

#### 3a — Parse conventional commit prefix

Extract the prefix from each commit subject:

| Prefix | Meaning |
|--------|---------|
| `feat:` | New feature or enhancement |
| `fix:` | Bug fix |
| `docs:` | Documentation change |
| `refactor:` | Code restructuring |
| `test:` | Test-only change |
| `chore:` | Maintenance (usually omit from changelog) |

#### 3b — Assign domain category from `CLAUDE.md`

Use the `### File Path Mapping` table and `### Domain Categories`
list from the `## Release` section parsed in Step 1.

Routing precedence (first match wins):

1. **Exclusions** — drop commits matching any `### Exclusions`
   pattern before categorisation.
2. **`fix:` prefix override** — any commit with a `fix:` prefix
   routes to `Fix`, regardless of path.
3. **Longest-prefix match** — for the commit's most-changed file
   (by line count from `--numstat`), find the longest matching
   prefix in `### File Path Mapping`. Ties broken alphabetically.
4. **Architecture fallback** — if no prefix matches, route to
   `Architecture`. Flag the mismatch in Step 6 (not a hard error).

Rules:
- A `refactor:` commit: include if it changes user-facing
  behaviour or structure; omit if purely internal.
- A `chore:` commit: omit unless it affects the user experience
  (e.g., changing install steps or package metadata).
- A `test:` commit: omit unless it introduces a new testing
  capability worth noting.

### Step 4 — Draft the Entry

Write the changelog entry using the category order from
`### Domain Categories`. Omit empty categories.

**Bullet composition rules:**

For each commit (or task referenced by a commit), compose the
bullet as follows:

1. **Headline** — always the task `name` frontmatter field,
   rendered as Title Case With Spaces. If no task file was
   resolved, derive the headline from the commit subject after
   the conventional prefix (fallback; flagged in Step 6).

2. **Description** — field precedence:
   - `## Findings` section (first paragraph), if present and
     non-empty.
   - `## Goal` section (first paragraph), if `## Findings` absent.
   - Commit subject (after prefix), if both sections absent
     (flagged in Step 6).

3. **Multi-trailer commits** — `(t0099, t0100)` produces one
   bullet headlined by t0099's name; co-referenced IDs render
   inline as `(also t0100)`:
   ```
   - **<Title for t0099>** — <description from t0099>. (also t0100)
   ```

4. **Sub-task collapse** — build a parent → sub-tasks index from
   each resolved task's `parent` frontmatter field:
   - If a parent task `tP` has commits in range AND a sub-task
     `tC` (`tC.parent == tP`) also has commits in range: render
     one bullet for `tP`, with `tC`'s bullet as a sub-bullet
     (two-space indent).
   - If `tP` has no commits in range but `tC` does: render `tC`
     as a flat bullet; no synthetic parent line.
   - Sub-task transitivity is flattened to one level (maximum
     two-level nesting).

Format:

```markdown
## v<VERSION>

Summary paragraph describing the release theme in 1–3 sentences.
Focus on the biggest user-facing change.

### <Category>

- **Bold task name** — Description from task Findings or Goal.
- **Another item** — More detail. (also t0042)
  - **Sub-task name** — Sub-task description.

### <Category>

- **Item** — Description.
```

Format rules:
- H2 for the version heading (`## v<VERSION>`).
- Summary paragraph immediately after the heading.
- H3 for each category (`### Core`, `### CLI`, etc.).
- Each entry: `- **Bold name** — Description.` (em dash, not hyphen).
- Multi-sentence descriptions are fine.
- Order categories by the order in `### Domain Categories`.
- Omit empty categories.

### Step 5 — Version Recommendation

If the user hasn't specified a version, recommend one:

| Condition | Bump |
|-----------|------|
| Breaking changes (removed features, changed public API) | **major** |
| New features, significant enhancements | **minor** |
| Bug fixes, documentation, internal improvements only | **patch** |

Present the recommendation with reasoning; do not decide
unilaterally.

### Step 6 — Present for Review

Show the complete draft entry to the user. Flag:
- Any commits you were unsure how to categorize.
- Any commits you excluded and why.
- The recommended version bump (if applicable).

**Fallbacks summary block** — if any fallback was triggered during
Steps 2–4, append a `Fallbacks:` section after the draft:

```
Fallbacks:
- <commit-hash> "<subject>": no (tNNNN) trailer — used commit subject.
- <commit-hash> "<subject>": task t0123 referenced but file missing — used commit subject.
- <commit-hash> "<subject>": task t0124 has no `## Findings` or `## Goal` — used commit subject.
```

The reviewer decides whether each flagged commit deserves a manual
edit before approving Step 7.

**Wait for explicit approval before writing.**

### Step 7 — Write to CHANGELOG.md

On approval, insert the new entry into `CHANGELOG.md`:
- Place it immediately after the `# Changelog` heading.
- Keep a blank line before and after the new entry.
- Do not modify existing entries.

**Do not commit, tag, or push yet.** The changelog write is a
working-tree change only. Committing happens in Step 8.

### Step 8 — Release

After writing the changelog, render the release checklist from
`### Checklist` in `CLAUDE.md`. Substitute `<VERSION>` and `<TAG>`
with the actual values. Present the checklist and **wait for the
user to approve before executing**:

```
Release v<VERSION>:
<steps from ### Checklist, with <VERSION> and <TAG> substituted>
```

On approval, execute all steps in sequence. Stop immediately
if any step fails.

## What This Skill Does NOT Do

- **Never scan for migrations, API routes, or DB schemas.**
  Single-package Python project.
- **Never fetch PR metadata.** Commits are self-descriptive.
- **Never write per-version release files.** Single
  `CHANGELOG.md` only.
- **Never tag manually.** Tagging is handled by CI.
- **Never mutate `artifacts/tasks/`** — read-only consumer;
  never writes, never edits frontmatter.
- **Never appends to the JSONL operation log** — layer isolation
  is strict; the skill is a pure read-plus-draft consumer.
