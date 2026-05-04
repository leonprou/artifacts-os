---
created: 2026-05-03
id: n0008
kind: note
name: task-frontmatter-audit
type: planning
---

## Origin

Captured 2026-05-03 from a brainstorming session on
`artifacts/kinds/task/ARTIFACT.md`. After rewriting the body to
mirror the note/research/spec spine, we audited the task
**frontmatter** — which fields the schema declares vs which
fields tasks actually carry on disk — to decide what (if
anything) should change in `task.json`.

Prompting question: *do we need or use all the fields in the task
frontmatter?*

---

## What `task.json` declares today

`task.json` declares **5** properties (no `required:`, no
`additionalProperties: false`):

| Field | Type | Notes |
|---|---|---|
| `status` | enum (8) | `backlog … done`, `cancelled`, `rejected` |
| `priority` | enum (4) | `low / normal / high / urgent` |
| `assignee` | string | free-form |
| `owner` | string | free-form |
| `type` | enum (6) | `feature / implementation / spec / documentation / research / refactor` |

Every other field tasks carry (`id`, `kind`, `name`, `created`,
`started`, `completed`, `parent`, `subtasks`, `depends_on`,
`artifacts`, `summary`, `tags`, `aliases`) rides on the universal
`_BUILTIN_FIELDS` allowlist in `core/validate.py` — recognised but
not constrained.

## Empirical usage across 88 tasks

| Field | Coverage | Verdict |
|---|---:|---|
| `kind`, `name`, `type`, `status`, `assignee`, `owner`, `created`, `id` | **88 / 88 (100%)** | de-facto required |
| `started` | 62 / 88 (70%) | set on `→ in-progress` |
| `completed` | 45 / 88 (51%) | set on `→ done` |
| `parent` | 34 / 88 (39%) | sub-task linkage |
| `artifacts` | 20 / 88 (23%) | outputs produced during execution |
| `depends_on` | 11 / 88 (13%) | ordering hint |
| `subtasks` | 10 / 88 (11%) | umbrella manifest |
| `priority` | 6 / 88 (7%) | matches doc rule "omit when `normal`" |
| `summary` | 6 / 88 (7%) | **dead** — only on t0014–t0023 (legacy renaming era) |
| `aliases` | 2 / 88 (2%) | empty lists only — **cruft from agent kind** |
| `tags` | 2 / 88 (2%) | empty lists only — **no task convention** |

Sample query (re-run from the vault root to refresh):

```python
import os, re, yaml
from collections import Counter
c = Counter()
for f in sorted(os.listdir('artifacts/tasks')):
    if not f.endswith('.md'): continue
    with open(os.path.join('artifacts/tasks', f)) as fh:
        text = fh.read()
    m = re.match(r'^---\n(.*?)\n---', text, re.DOTALL)
    if not m: continue
    fm = yaml.safe_load(m.group(1)) or {}
    for k in fm:
        c[k] += 1
print(c.most_common())
```

## Findings

1. **Schema under-declares the de-facto required surface.** `type`,
   `status`, `assignee`, and `owner` are 100% present but the
   schema does not list them in `required:`. Validation passes only
   because `_REQUIRED_KEYS` in `core/validate.py` (`id`, `kind`,
   `name`, `created`) catches the universal four — the task-specific
   four are unenforced.
2. **Lifecycle and relationship fields are typed only by convention.**
   `started`, `completed`, `parent`, `subtasks`, `depends_on`,
   `artifacts` are recognised by `_BUILTIN_FIELDS` but the schema
   never says they must be dates / wikilinks / lists of wikilinks.
   A typo or wrong shape passes validation today.
3. **`summary` is dead.** Last set on t0023 (April 2026) during the
   `openstation → artifacts` rename push. The body's opening
   paragraph carries that role now (see the rewritten task
   `ARTIFACT.md`, summary paragraph after `# {{TITLE}}`).
4. **`aliases` and `tags` are agent/cross-kind cruft on tasks.**
   Each appears twice, both as empty `[]`. No author intent, no
   reader contract.
5. **`priority` usage is consistent with the doc.** 7% set rate
   matches "Optional; omit when `normal`." Keeping the closed enum
   prevents drift when it *is* set.

## Recommendations (D1–D5)

| ID | Decision | Rationale |
|---|---|---|
| **D1** | Add `required: [type, status, assignee, owner]` to `task.json`. | Closes the gap between de-facto-required (100% present) and schema-declared. |
| **D2** | Add typed schema entries for `started`, `completed` (`string`, `format: date` or `date-time`); `parent` (`string` wikilink); `subtasks`, `depends_on`, `artifacts` (`array` of `string`). | Makes wikilink/shape errors validation-visible instead of silently tolerated. |
| **D3** | Drop `summary` from the task surface — remove from any task-facing docs and stop suggesting it. | Dead field; replaced by body opening paragraph. Keep in `_BUILTIN_FIELDS` only if other kinds use it. |
| **D4** | Drop `aliases`, `tags` from the task surface. | Never used meaningfully on tasks; live on agents only. |
| **D5** | After D1–D4 land, set `additionalProperties: false` on `task.json`. | Makes the audit self-enforcing — unknown keys become validation errors going forward. |

D1–D4 are independent and can land in any order; D5 must be last
(it's the gate that depends on the surface being complete).

## Open questions

- Should `started` / `completed` be `date` (current convention,
  matches `created`) or `date-time` (some tasks store
  `2026-04-20 15:13:25`)? Pick one and migrate.
- Are `started` / `completed` set by an out-of-band tool
  (OpenStation lifecycle hooks?) or by hand? If by hand, the
  inconsistency (70% / 51% set rates) is just author drift; if by
  tool, the tool should always set them on transition.
- Does any other kind (`spec`, `research`) actually use `summary`?
  If not, drop it from `_BUILTIN_FIELDS` entirely.

## Next steps

A spec is **not** required for D1–D4 — each is a localised schema
edit with no design alternatives. D5 is also mechanical once the
surface is closed. File one or more `implementation` tasks
referencing this note as the source of truth.

D2 may surface a question about wikilink format (`[[t0042]]` vs
`[[t0042-fix-bug]]`) that already lives elsewhere — defer to the
existing wikilink-resolution behaviour rather than re-deciding
here.

## References

- [[artifacts/kinds/task/ARTIFACT.md]] — body authoring guide; the
  prompting context for this audit.
- `artifacts/kinds/task.json` — the schema this note recommends
  changing.
- `src/artifacts_os/core/validate.py` — `_REQUIRED_KEYS` and
  `_BUILTIN_FIELDS`; the universal allowlist that masks the
  task-schema gap today.
- [[t0076-implement-l1-kinds-catalogue-s0017]] — worked example
  of a complete task frontmatter (post-execution).
- [[t0014-rename-storage-root-from-openstation]] — last era when
  `summary:` was set; useful when verifying D3.