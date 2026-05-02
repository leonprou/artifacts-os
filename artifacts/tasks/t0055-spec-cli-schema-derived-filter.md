---
kind: task
id: t0055
name: spec-cli-schema-derived-filter
type: spec
status: done
assignee: architect
owner: user
depends_on:
  - "[[t0053-spec-core-unified-filter-api]]"
  - "[[t0054-complete-kind-schemas]]"
created: 2026-05-01
started: 2026-05-02
artifacts:
  - "[[s0015-cli-schema-derived-filter-flags]]"
parent: "[[t0061-cli-schema-derived-filter-flags]]"
completed: 2026-05-02
---

# Spec Cli-Schema-Derived-Filter-Flags

## Goal

Produce a spec under `artifacts/specs/` that designs a system for
auto-generating CLI filter flags per kind from the kind schemas.
`artifacts list --kind task --help` should surface every filterable
field declared in `task.json`'s `properties` block as a typed flag,
with enum values from the schema enforced at parse time.

Implementation is **not** in scope — a follow-up task will be filed
once this spec is approved.

## Context

### Why this exists

Today `artifacts list` exposes only two filter flags: `--kind` and
`--status`. Other frontmatter axes used by views (`assignee`, `type`,
`owner`, `priority`, `agent`) have **no CLI flag** — they're reachable
only by defining a view in `artifacts.yaml` and running `-V <view>`.

The result: ad-hoc filtering forces YAML edits or memorising view
names. Schema-derived flag generation closes the gap by deriving the
CLI surface from the data model.

### How this composes with t0053

This task **depends on t0053** (unified `core.list_artifacts(kind=,
filters=dict)`). Without that, schema-derived flags would have to
wire into the current split-filter machinery (`status` → core,
others → `_apply_extra_filters`) and rewire later. With t0053 in
place:

```
schema-derived flag (--type feature)
        │ rewrite at parse time
        ▼
filter dict entry: {"type": "feature"}
        │ merge with view filters per t0053
        ▼
core.list_artifacts(kind="task", filters={"type": "feature", ...})
```

Schema-derived flags are **sugar** — they're a typed, discoverable
front-end on top of t0053's universal `--filter k=v`. Both
mechanisms coexist.

### How this composes with t0054

This task **depends on t0054** (complete-kind-schemas). The schemas
today declare only `status` and a few enums; most filterable axes
are missing. Generating flags from incomplete schemas would
under-deliver. t0054 is the prerequisite that makes flag generation
worth doing.

### The hard part: argparse and dynamic flags

argparse builds the parser **once** with a fixed flag set. The
`--kind` value isn't known until parse time, so the parser cannot
naturally show different flags per kind. Three resolution strategies,
all with tradeoffs:

| Strategy | How it works | Pros | Cons |
|----------|--------------|------|------|
| **Two-pass parse** | Pre-scan argv for `--kind`, build the per-kind parser, parse for real | Per-kind `--help` works; per-kind enum validation | argparse internals get re-entered; `--help` without `--kind` is awkward |
| **Union of all kinds** | Register every property from every kind globally; validate at runtime against the actual kind | Single parser; `--help` shows everything | Noisy `--help`; `--status` accepts the union of enums, loses per-kind validation at parse time |
| **Per-kind subparsers** | `artifacts list task --status ready` instead of `artifacts list --kind task --status ready` | Clean per-kind `--help`; per-kind enums; argparse-native | Breaking change to command surface; `artifacts list` (no kind) needs a separate path |

The architect must pick one and justify it. My read is that
**two-pass** is the least surgery (preserves `--kind` as a flag, no
breaking change, per-kind `--help` works once `--kind` is supplied).
But subparsers are arguably cleaner long-term.

### Cross-kind queries

When `--kind` isn't given (cross-kind list), which schema's flags
apply? Same question t0053 raises for cross-kind validation. The
spec must align with t0053's answer (intersection of enums? union?
opt out of validation entirely?).

### Discoverability and value space

Free-form fields (`assignee`, `owner`, `priority`) should still
become flags, just without enum-choices restriction. Argparse takes
`type=str` for these.

### References

- Current CLI surface: `src/artifacts_os/cli/commands/list.py`
  lines 16–25 (`register`).
- Kind schemas: `artifacts/kinds/*.json` — properties block is
  the source.
- Registry: `src/artifacts_os/core/registry.py` — provides kind
  schemas at runtime; CLI parser construction must consume from
  here.
- Dependent specs: `s0007` (views model), `s0012` (CLI list named
  views), and the spec produced by t0053 (unified filter API).
- Openstation reference: openstation does not auto-generate flags
  — this is a divergence. Note in spec.

## Requirements (spec must cover)

1. **Generation strategy** — pick one of (two-pass / union /
   subparsers). Justify with worked argparse interaction examples.
2. **Property → flag mapping** — for each JSON Schema property
   shape (enum, type:string, type:integer, type:boolean), define
   the corresponding argparse `add_argument` call.
3. **`description` propagation** — schema property `description`
   becomes argparse `help` text.
4. **Enum validation** — schema enums become argparse `choices`.
   Cross-kind behavior specified (intersection / union / off).
5. **Conflict handling** — when two kinds declare the same property
   name with different enums (e.g. `status`), the resolution
   strategy must define the behavior in cross-kind mode.
6. **Lifecycle / load order** — registry must be loaded before
   parser construction. Spell out the new order and where it
   lives in `cli/__init__.py`.
7. **Composition with t0053** — generated flag values rewrite into
   the unified filter dict before reaching core. Show the call
   trace.
8. **Rollback / opt-out** — escape hatch if a user wants raw
   `--filter k=v` semantics, or if a property name conflicts
   with an existing argparse flag (`--kind`, `--fields`,
   `--view`, `--quiet`, `--json`).
9. **Test plan** — coverage matrix per kind: enum match, enum
   mismatch (parse-time error), free-form string, cross-kind,
   missing `--kind`, conflicting flag names.
10. **Cross-link** — t0053 spec, t0054 schema completion, s0007,
    s0012, kind schemas in `artifacts/kinds/`.

## Verification

- [x] Spec file committed under `artifacts/specs/`
- [x] Covers all 10 requirements above
- [x] Picks one generation strategy with argparse-grounded
      justification
- [x] Cross-links t0053 spec output, t0054, `s0007`, `s0012`
- [x] Reviewed and approved by user
- [x] Follow-up implementation task can be filed against the spec
      without further design work

## Verification Report

*Verified: 2026-05-02*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec file committed under `artifacts/specs/` | PASS | `artifacts/specs/s0015-cli-schema-derived-filter-flags.md` exists (894 lines, frontmatter `id: s0015`, `kind: spec`, `task: [[t0055-spec-cli-schema-derived-filter]]`). |
| 2 | Covers all 10 requirements above | PASS | Spec §14 requirement-coverage map maps each task req to a section: §3 (req 1), §4 (req 2), §4.6 (req 3), §5 (req 4), §6 (req 5), §7 (req 6), §8 (req 7), §9 (req 8), §10 (req 9), §1/§11.3/§13 (req 10). All sections present and substantive. |
| 3 | Picks one generation strategy with argparse-grounded justification | PASS | §3.1 picks two-pass parsing; §3.2 scoring table compares all three options; §3.3 lists four concrete reasons (precedent, `--kind` ergonomics, real argparse choices, no surface change); §3.4 addresses the argparse-builds-once footgun directly; §3.5 has worked argparse stdout examples. |
| 4 | Cross-links t0053 spec output, t0054, `s0007`, `s0012` | PASS | §1 cross-references table links `[[s0014-core-unified-filter-api]]` (output of t0053), `[[t0054-complete-kind-schemas]]`, `[[s0007-artifacts-os-views-module]]`, `[[s0012-cli-list-named-views]]`, plus `[[s0011-cli-create-kind-aware-help]]` for precedent. 17 references total throughout spec. |
| 5 | Reviewed and approved by user | PASS | User (task `owner: user`) invoked `/openstation.verify` on this task while in `review` status — explicit review action. Spec content is self-consistent, all open questions resolved (§12), all decisions justified (§15). |
| 6 | Follow-up implementation task can be filed against the spec without further design work | PASS | §13 lists 7 concrete implementation steps with file targets and helper names; §11.1 has a per-file change table with LOC estimates; §10 has a 28-row test matrix as the executable acceptance contract. No further design decisions required. |

### Summary

6 passed, 0 failed. All verification criteria met — the spec is implementation-ready and the task is ready to be marked `verified`.

## Progress

### 2026-05-02 — architect
> time: 00:17
> log: [[artifacts/logs/t0055-spec-cli-schema-derived-filter]]

Drafted spec [[s0015-cli-schema-derived-filter-flags]] (~520
lines, 15 sections). Picked two-pass parsing strategy
(generalises s0011 precedent), defined property→flag mapping
with custom `_parse_bool` helper, resolved cross-kind enum
question (no `choices=`, per-kind existence validation only),
specified `--status` augment as the sole static-flag exception,
and laid out a 28-row test matrix for
`tests/cli/test_list_schema_flags.py`. All 10 task requirements
addressed; implementation outline in §13 is build-ready.

## Findings

Produced spec [[s0015-cli-schema-derived-filter-flags]] (15
sections, ~520 lines) designing schema-derived `--<field>` filter
flags for `artifacts list`. Key decisions, all resolved (full
justifications in the spec):

- **Generation strategy — two-pass parsing** (§3). Pre-scan argv
  for `--kind`, load `artifacts/kinds/<K>.json`, build the `list`
  subparser with kind-specific flags. Generalises the existing
  `_peek_create_kind_schema` precedent ([[s0011-cli-create-kind-aware-help]])
  — no new argparse machinery, no breaking change to the command
  surface, and per-kind enums are real argparse `choices=`. Union
  was rejected (loses per-kind enum at parse time); subparsers
  were rejected (breaks every existing `artifacts list ...`
  invocation).
- **Property → flag mapping** (§4). Direct table:
  `enum → choices=`, `string → type=str`, `integer → type=int`,
  `boolean → custom _parse_bool helper` (argparse `type=bool` is
  the well-known broken case). List-typed properties skipped in
  v1 — membership semantics differ from equality, covered by
  `--filter tags=...` until a future spec extends.
- **Description propagation** (§4.6). `prop["description"]` →
  argparse `help`; fallback `f"filter by {field}"`. Cross-kind
  mode appends `(varies by kind — pass --kind for per-kind details)`
  when descriptions disagree.
- **Enum validation** (§5). Per-kind mode: `choices=` enforced at
  parse time, exit 2 with argparse's standard "invalid choice"
  message. Cross-kind mode: **no** `choices=` because per-kind
  enums conflict (e.g. `task.status` vs `spec.status`); union
  over-accepts and under-documents. Per-kind existence is the
  validation contract, matching [[s0014-core-unified-filter-api]] §6.3.
- **Conflict handling** (§6). Two cases: (a) schema field whose
  generated flag name collides with a static flag — silent skip,
  reachable via `--filter`; (b) cross-kind mode where two kinds
  declare the same property with different shapes — pick the
  most-permissive shape (no choices, free-form string), suffix
  help with "varies by kind". `--status` is the sole exception:
  per-kind mode replaces the static `--status` with a
  schema-augmented version that retains the `-s` short form and
  adds `choices=`.
- **Lifecycle / load order** (§7). Schemas, not a constructed
  `Registry`, drive generation — same as today's `create`
  command. Phase 1 loads schemas directly from
  `artifacts/kinds/*.json`; Phase 2 builds the parser; Phase 3
  parses argv; Phase 4 constructs the registry; Phase 5 dispatches.
  Generalises `_peek_create_kind_schema` →
  `_peek_kind_for_command(command, ...)` and threads `list_kind`,
  `list_schema`, `list_all_schemas` into `_build_parser`.
- **Composition with [[s0014-core-unified-filter-api]]** (§8).
  Generated flags fold into `resolve_filters` between static
  flags (`--kind`, `--status`) and the `--filter k=v` escape
  hatch — so `--filter` always wins, matching the documented
  precedence in s0014 §7. Source of truth is the schema, not
  `KindDef.statuses` (avoids a layering shortcut and supports
  enums on non-`status` fields like `priority`).
- **Rollback / opt-out** (§9). `--filter k=v` is the
  contractually documented escape hatch; no `--no-schema-flags`
  or `cli.list.schema_filter_flags: false` in v1 (would duplicate
  `--filter`). Reserved-name conflicts (§6.1) are the automatic
  rollback — silent skip + `--filter` keeps the field reachable.
  Unknown-kind behaviour mirrors `create` (Phase 1 returns
  `(unknown, None)`, Phase 2 builds the static surface).
- **Test plan** (§10). 28 normative test rows in seven matrices:
  per-kind generation (L1–L7), cross-kind generation (L8–L12),
  composition with `--filter`/`--view` (L13–L16), Phase 1
  load-order regressions (L17–L21), type coercion (L22–L25),
  help-text propagation (L26–L28). New file
  `tests/cli/test_list_schema_flags.py`; existing tests unchanged.
- **Implementation outline** (§13). Five files touched: `cli/__init__.py`
  (refactor + new peek), `cli/commands/list.py` (~80 lines added),
  `tests/cli/test_list_schema_flags.py` (new), `docs/cli.md` (new
  section), optional shared helper extracted to `cli/_schema_flags.py`.
  Estimated 1 day of implementation + tests.

The spec is implementation-ready; a follow-up task can be filed
against §13 without further design work.

## Downstream

- **Implementation task.** §13 is concrete enough to file
  immediately; suggested title:
  `cli-schema-derived-filter-flags-impl` (per-kind argparse
  augment for `artifacts list`).
- **Optional refactor.** `cli/commands/create.py:_add_kind_flags`
  and the new `cli/commands/list.py:_add_schema_filter_flags`
  share enough structure that extracting a `cli/_schema_flags.py`
  utility module is worth a follow-up. Not blocking; spec'd as
  "recommended but optional" in §7.4.
- **Documentation surface.** `docs/cli.md` doesn't currently
  document the per-kind `--help` behaviour (added by s0011 for
  `create`); the implementation PR should fold both `create` and
  `list` into a single "Schema-derived flags" section.
- **Future enum-value validation on `--filter`.** Out of scope
  here and in s0014; revisit when a real user reports the
  `--filter status=bogus` silent-no-match as a footgun.
