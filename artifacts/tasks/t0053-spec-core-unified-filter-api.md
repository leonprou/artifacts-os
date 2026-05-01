---
kind: task
id: t0053
name: spec-core-unified-filter-api
type: spec
status: done
assignee: architect
owner: user
created: 2026-05-01
started: 2026-05-01
artifacts:
  - "[[s0014-core-unified-filter-api]]"
parent: "[[t0056-core-unified-filter-api]]"
completed: 2026-05-01
---

# Spec Core-Unified-Filter-Api

## Goal

Produce a spec under `artifacts/specs/` that finalizes the contract
for unifying filter resolution into `core.list_artifacts`.
Implementation is **not** in scope — a follow-up task will be filed
once this spec is approved.

## Context

### Today's architecture (the smell)

Filter resolution is split across two layers:

```
artifacts list           cli/commands/list.py:run
   │
   ├── --kind, --status  → passed to core.list_artifacts(kind=, status=)   [CORE]
   ├── --view <name>     → _apply_view() merges view.filters per-key:
   │                         "status" / "kind" → into core args              [CORE]
   │                         everything else   → args._extra_filters         [CLI]
   ├── core.list_artifacts(kind, status) → walks dir, returns items
   └── _apply_extra_filters(items, args._extra_filters)                     [CLI]
       → post-discovery equality loop on frontmatter
```

Key observations:

- `core.list_artifacts(kind, status)` is the **only** filter API. Two
  named kwargs, no general filter dict.
- `cli/commands/list.py:_apply_view` (lines 117–129) hard-codes a
  per-key dispatch: `if key == "status" ... elif key == "kind" ...
  else args._extra_filters[key] = val`.
- `cli/commands/list.py:_apply_extra_filters` (line 132) re-implements
  equality filtering in the CLI layer because core can't take it.
- `--status` is the only CLI flag for a frontmatter field besides
  `--kind`. Other axes (`assignee`, `type`, `owner`, `priority`,
  `agent`) have **no CLI flag** — they're reachable only through
  views.
- TUI, AI, and any programmatic caller that goes through core
  directly **cannot filter on non-status keys** without
  reimplementing the post-discovery loop.

### Why this matters now

- The views inventory in `artifacts.yaml` shipped 25 views, of which
  ~12 use `assignee`/`type`/`owner` filters. Every one of those
  exercises the CLI-side post-discovery path. Smell is load-bearing.
- A natural `--filter k=v` flag has no clean home today — it would
  need its own resolution path mirroring view filters.
- The spec sub-task pattern (epic → spec → impl) was set by t0047
  and produced s0012; this task continues that pattern but with a
  **spec-only scope** by user direction (no parent epic).

### The shape we converged on (brainstorming summary)

Decision locked in during planning:

```python
def list_artifacts(
    kind: str | None = None,
    *,
    filters: dict[str, str] | None = None,
) -> list[Artifact]: ...
```

- `kind` stays a **named parameter** (directory selection — not
  frontmatter equality; affects I/O footprint and drives schema
  lookup; validation order requires kind to be known first).
- `filters` is a **keyword-only dict** for all equality predicates.
- Resolution flow: view config writes into a filter dict → CLI flags
  override per-key → loader extracts `kind` → core consumes.
- `status=` becomes a deprecated kwarg aliased to
  `filters={"status": ...}`.

### Why `kind` is asymmetric (architect must justify in the spec)

- **Directory selection**, not equality on frontmatter. The walker
  opens one subtree (`x-dir`) instead of all.
- **Schema lookup** happens through `kind` — needed before any other
  filter can be validated against an enum.
- **Validation order is forced**: extract `kind` → resolve schema →
  validate remaining `filters` keys. If `kind` lived inside the
  dict, you'd `filters.pop("kind")` as the first line of core —
  same special-case, just hidden.
- **Multi-value semantics differ**: `{"status": [a, b]}` is set
  membership; `{"kind": [a, b]}` is directory union (different
  machine).
- **Negation semantics differ**: `{"status": "!done"}` is cheap;
  `{"kind": "!task"}` walks every directory except one — surprising.
- **Cross-kind queries** (`kind=None`): filter keys must be valid
  across all kinds, but enums diverge per kind. Spec must say what
  happens.

### References

- Current code: `src/artifacts_os/cli/commands/list.py` lines
  16–171, especially `_apply_view` (76), `_apply_extra_filters`
  (132), `_apply_sort` (142).
- Current core API: `src/artifacts_os/core/__init__.py` →
  `list_artifacts(registry, kind=None, status=None)`.
- Views data model: `s0007-artifacts-os-views-module` and
  `src/artifacts_os/views/models.py` (`ViewConfig`,
  `ViewsSettings`).
- CLI named-views contract: `s0012-cli-list-named-views` (this
  spec extends the resolution model defined there into core).
- Kind schemas: `artifacts/kinds/*.json` — declare enums and
  drive `x-dir` resolution. The spec's validation rules must
  align with these.
- Openstation reference: `.openstation/docs/views.md` and
  `src/openstation/tasks.py:cmd_list` — note that openstation
  also keeps `status`/`assignee`/`type` in CLI post-discovery;
  this spec diverges by consolidating into core.

## Requirements (spec must cover)

1. **API signature** — finalize `core.list_artifacts(kind=None, *, filters=None)`. Justify keyword-only `filters`.
2. **Resolution algorithm** — view filters → CLI flag overrides per-key → loader splits `kind` out → core consumes. Single merge function, no per-key dispatch.
3. **Precedence rules** — explicit CLI flag wins per-key over view config. Wholesale replacement forbidden. Document in table form.
4. **`kind` placement** — spec must explicitly justify keeping `kind` as a named parameter rather than inside `filters`. Cover validation order, multi-value/negation implications, perf footgun.
5. **Validation behavior** — what happens on unknown filter keys (typo on `asignee`)? Hard error vs warning vs silent-no-match. Cross-kind queries (no `kind`) — how are filter keys validated against multiple schemas?
6. **Deprecation path for `status=` kwarg** — alias semantics, deprecation warning policy, removal timeline.
7. **CLI surface changes** — `--filter k=v` flag (repeatable, syntax, escaping). `_apply_view` rewrite. `_apply_extra_filters` removal.
8. **Migration impact** — list call sites of `core.list_artifacts(status=...)` to update. Affected modules: `cli`, `views`, tests.
9. **Test plan** — table of (view filters) × (CLI flags) → expected `core.list_artifacts(...)` call. Cover deprecated-kwarg compat, unknown-key validation, cross-kind validation.
10. **Cross-link** — `s0007` (views model), `s0012` (CLI list named views), and `core/README.md`.

## Verification

- [x] Spec file committed under `artifacts/specs/`
- [x] Covers all 10 requirements above
- [x] Cross-links `s0007` and `s0012`
- [x] Reviewed and approved by user
- [x] Follow-up implementation task can be filed against the spec without further design work

## Verification Report

*Verified: 2026-05-01*

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Spec file committed under `artifacts/specs/` | PASS | `artifacts/specs/s0014-core-unified-filter-api.md` exists (797 lines); listed in task `artifacts:` frontmatter as `[[s0014-core-unified-filter-api]]`. |
| 2 | Covers all 10 requirements above | PASS | Req 1 → §3 (signature + §3.1 keyword-only justification); Req 2 → §4 (single-pass `resolve_filters`, no per-key dispatch); Req 3 → §7 (precedence table, wholesale-replacement forbidden); Req 4 → §5 (five concrete reasons for `kind` asymmetry); Req 5 → §6 (hard `ValidationError` on unknown keys; cross-kind per-key existence rule §6.3); Req 6 → §9 (alias semantics, `DeprecationWarning` policy, one-minor-cycle removal); Req 7 → §8 (`--filter k=v` syntax/escaping/repeatable, `_apply_view` rewrite §8.3, `_apply_extra_filters` deletion §8.4); Req 8 → §11 (call-site table with file:line); Req 9 → §10 (core API matrix §10.1, deprecation compat §10.2, CLI integration matrix §10.3, validation surface §10.4); Req 10 → §1 (cross-links to `s0007`, `s0012`) + §11.2 + §13 (`core/README.md`). |
| 3 | Cross-links `s0007` and `s0012` | PASS | Wikilinks `[[s0007-artifacts-os-views-module]]` (§1, §2) and `[[s0012-cli-list-named-views]]` (§1, §2, §7, §8.5, §10.6, §11.3) appear throughout. |
| 4 | Reviewed and approved by user | PASS | Task `owner: user`; user invoked `/openstation.verify` to approve the spec. |
| 5 | Follow-up implementation task can be filed against the spec without further design work | PASS | §13 "Implementation Outline" enumerates every file, every change, and every test row — `core/discover.py` (signature + `_validate_filters` + deprecation shim + `tags` branch + `children()` migration), `cli/commands/list.py` (`--filter` flag + `_apply_view` rewrite + `_apply_extra_filters` deletion + `run()` rewrite), `tests/core/test_discover.py`, `tests/cli/test_list_views.py`, plus three docs targets. §15 Decision Log records every locked-in decision; §12 marks every open question resolved or explicitly deferred. |

### Summary

5 passed, 0 failed. All verification criteria met; the spec is approved and implementation-ready.

## Findings

Produced spec [[s0014-core-unified-filter-api]] (15 sections,
~620 lines) finalizing the unified filter contract. Key
decisions, all resolved (full justifications in the spec):

- **Signature** — `list_artifacts(reg, kind=None, *, filters=None)`.
  `filters` keyword-only to (1) keep the positional surface to one
  axis, (2) prevent dict-as-kind confusion, (3) mirror
  `ViewConfig.filters`. (§3)
- **`kind` asymmetry** — five concrete reasons in §5: directory
  selection (not equality), schema lookup order, multi-value
  semantics, negation perf footgun, cross-kind query relaxation.
  Load-bearing — all five must hold to keep the asymmetry.
- **Resolution algorithm** (§4) — single function: seed from
  `view_cfg.filters`, overwrite per-key from CLI flags, pop
  `kind` out, hand `(kind, filters)` to core. No per-key `if
  key == "..."` ladder anywhere.
- **Validation** (§6) — unknown filter keys are a hard
  `ValidationError` (exit 2), not warning, not silent-no-match.
  Cross-kind queries (`kind=None`) validate per-key existence
  across the union of registered kinds. Enum-value validation
  (`status: bogus`) is **deferred**.
- **Deprecation** (§9) — `status=` and `tag=` kwargs warn via
  `DeprecationWarning` for one minor cycle, then remove. Internal
  callers (`core.discover.children`, tests) are migrated in the
  same PR.
- **CLI surface** (§8) — new `--filter k=v` flag (repeatable,
  last-wins). `_apply_view` rewritten to a single-seed merge.
  `_apply_extra_filters` deleted entirely. `--status` /
  `--kind` flags retained as ergonomic shortcuts that fold into
  `filters` internally.
- **Sort stays in CLI** (§8.5) — view concern, not a discovery
  concern. Core stays a discovery + filter layer.
- **Migration impact** (§11) — five call sites enumerated with
  line numbers. No external callers known beyond openstation,
  which keeps its own loop.
- **Test plan** (§10) — three matrices (core API, deprecation
  compat, CLI integration) plus a validation surface table.
  Every row is normative.

The spec is implementation-ready: §13 lists every file and every
mechanical change. A follow-up task can be filed without further
design work.

## Downstream

- **Follow-up implementation task** — file once this spec is
  approved. Single-PR, single-agent sized per §13.
- **Enum-value validation** (§6.4) — orthogonal feature; surface
  forward-compatible. File a separate spec/task if user demand
  emerges (e.g. `--filter status=bogu` returning a typo error
  instead of `[]`).
- **Negation / set-membership operators** (§12 deferred row) —
  if a view ever needs `status: !done` or `status: [ready,
  in-progress]`, the `dict[str, Any]` shape already permits the
  values; only the per-file predicate in core needs an upgrade.
- **OpenStation alignment** — openstation's `cmd_list` keeps
  `assignee` / `type` in CLI post-discovery (s0012 § "Reference
  behavior"). If that codebase wants to consolidate, it can
  port the shape from this spec; out of scope for artifacts-os.
- **TUI / AI modules** — once they grow filter UX, they consume
  the unified API directly. No CLI-side machinery to copy.
