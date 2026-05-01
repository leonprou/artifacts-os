---
kind: task
id: t0042
name: cli-create-kind-aware-help
type: feature
status: verified
assignee: developer
owner: user
parent: "[[t0036-improve-cli-create-command]]"
created: 2026-04-30
started: 2026-04-30
artifacts:
  - "[[artifacts/specs/s0011-cli-create-kind-aware-help]]"
---

# Cli Create: Kind-Aware --Help

## Goal

Make `artifacts create --kind <kind> --help` render help that is
specific to the requested kind, rather than the current static
flag list.

## Approach

Two-phase argparse build:

1. **Phase 1** — pre-parse with ``add_help=False`` and
   ``parse_known_args()`` to peek at ``--kind`` without firing
   ``--help``.
2. **Phase 2** — rebuild the parser using the resolved kind's
   schema (``artifacts/kinds/<kind>.json``) so ``--help``
   renders a kind-aware view.

Use the existing kind schemas as the single source of truth —
do not duplicate field definitions in the CLI layer.

## Variants in Scope

- **A. Filter** — hide convenience flags that don't apply to the
  kind (e.g. drop ``--assignee`` when ``note`` does not declare
  it). Keep ``--fields`` as the universal escape hatch.
- **B. Augment** — add kind-specific flags derived from the kind
  schema (e.g. ``--severity`` for ``bug``, ``--tags`` for
  ``note``). Convention: schema field ``foo`` → ``--foo`` flag,
  with type-based metavar/help.

Out of scope for this task: variants C (annotate-only) and
D (schema dump). Revisit if A+B feel insufficient.

## Open Questions to Resolve in Spec

- What happens when ``--kind`` is omitted? (Use the resolved
  default kind via the existing ``cli.defaults.create.kind``
  chain, or show a generic view + kinds index?)
- What happens when ``--kind`` is invalid? (Fail fast vs. fall
  back to generic help.)
- How are wikilink-typed schema fields surfaced (auto-wrap
  applies)?
- How are list-typed schema fields surfaced (repeatable flag
  vs. comma-list)?
- Does the same mechanism extend to ``validate`` / ``update``
  later, and should the design accommodate that now?

## Requirements

- Spec under ``artifacts/specs/`` (extend ``s0003`` or new sub-spec)
  documenting the resolution rules, flag-name conventions, and
  conflict handling (e.g. schema field named ``help``).
- Implementation in ``src/artifacts_os/cli/commands/create.py``
  using two-phase parsing.
- Tests in ``tests/cli/`` covering: kind-aware help text for at
  least two kinds with different schemas; unknown-kind handling;
  default-kind handling; that filtered flags still work via
  ``--fields`` (backwards compatibility).
- ``src/artifacts_os/cli/README.md`` updated with the new
  behavior and an example.
- ``.openstation/skills/artifacts-os/SKILL.md`` updated if user-
  facing behavior changes.

## Progress

### 2026-04-30 — developer
> time: 20:27

Implementation complete: two-phase parsing, Variant A filter + B augment, 14 new tests, docs updated

## Findings

Implemented kind-aware `--help` for `artifacts create` via two-phase argparse parsing.

**Spec**: `[[artifacts/specs/s0011-cli-create-kind-aware-help]]` documents resolution rules, Variant A filter (x-columns-based), Variant B augment (schema properties → flags), conflict avoidance, flag-name conventions, and backwards-compat guarantees.

**Implementation** (`src/artifacts_os/cli/`):
- `__init__.py`: added `_peek_create_kind_schema()` (Phase 1 pre-parse) and threaded `create_kind`/`create_schema` through `_build_parser()` → `create.register()`
- `commands/create.py`: `register()` now accepts `kind`/`schema` and builds kind-aware parser; filter uses `x-columns` presence as activation signal; augment adds `--<field>` for every schema property not already a convenience flag; `_build_fields()` uses `getattr` for filtered flags and collects kind-specific fields via `_kind_specific_fields` namespace attribute

**Filter criterion**: Variant A activates only when schema has `x-columns`. Schemas with only `properties` (including test fixtures) get all convenience flags, preserving backwards compat.

**Smoke test** (real vault):
- `artifacts create --kind task --help` → shows `--assignee`, `--status` (enum), `--priority`
- `artifacts create --kind note --help` → shows `--type` only (no `--assignee`)

**Tests**: 14 new tests in `tests/cli/test_create_kind_aware_help.py` + 98 existing tests continue to pass.

## Verification

- [x] Spec describing variants A + B, defaulting/error rules, and
      flag-name convention is in ``artifacts/specs/``
- [x] ``artifacts create --kind task --help`` and ``--kind note --help``
      render distinct, schema-driven flag lists
- [x] Unknown ``--kind`` value produces a clear error (not a stack
      trace)
- [x] Existing ``--fields`` escape hatch still accepts every
      schema field, including ones surfaced as dedicated flags
- [x] Tests in ``tests/cli/`` cover the cases listed under
      Requirements
- [x] ``src/artifacts_os/cli/README.md`` and the ``artifacts-os``
      skill reference reflect the new help behavior

## Verification Report

*Verified: 2026-04-30*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec for Variants A+B, defaulting/error rules, flag-name convention in `artifacts/specs/` | PASS | `artifacts/specs/s0011-cli-create-kind-aware-help.md` covers two-phase parsing (§2), Variant A filter (§3), Variant B augment (§4), conflict handling (§5), unknown-kind behavior (§6), flag-name conventions (§7), backwards compat (§8) |
| 2 | `--kind task --help` and `--kind note --help` render distinct, schema-driven flag lists | PASS | Smoke test: task help shows `--assignee --status --priority`; note help shows only `--type` (no `--assignee`, no augmented `--priority`/`--status`) |
| 3 | Unknown `--kind` produces clear error (not a stack trace) | PASS | `artifacts create --kind nonsense Test` → `error: Unknown kind: 'nonsense'` (exit 1, no traceback). Covered by `test_unknown_kind_exits_1` and `test_unknown_kind_help_shows_generic_parser` |
| 4 | `--fields` escape hatch still accepts every schema field, including ones surfaced as dedicated flags | PASS | Three tests pass: `test_fields_hatch_for_augmented_field`, `test_fields_hatch_for_filtered_convenience_flag`, `test_fields_hatch_overridable_by_dedicated_flag` |
| 5 | Tests in `tests/cli/` cover Requirements cases | PASS | `tests/cli/test_create_kind_aware_help.py`: 14 tests covering Variant A filter, Variant B augment, distinct kind help, default-kind handling, unknown-kind handling, augmented flags writing frontmatter, `--fields` escape hatch. Full CLI suite: 112/112 pass |
| 6 | `src/artifacts_os/cli/README.md` and `artifacts-os` skill reflect new help behavior | PASS | README.md L177–195 documents kind-aware help with Variant A/B explanation and examples. `.openstation/skills/artifacts-os/SKILL.md` L108–113 describes schema-driven `--help` with task/note examples |

### Summary

6 passed, 0 failed. All verification criteria are satisfied; task is ready for transition to `verified`.
