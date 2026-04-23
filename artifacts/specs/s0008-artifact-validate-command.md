---
kind: spec
name: artifact-validate-command
status: draft
created: 2026-04-23
task: "[[t0011-spec-artifact-validate-command]]"
agent: architect
id: s0008
---

# artifacts validate — Frontmatter Validation Command

Spec for the `artifacts validate` subcommand and its backing
`core/validate.py` module. Covers data models, validation rules,
CLI interface, output formats, fix behaviour, and test strategy.

## Motivation

`artifacts verify` checks task body checklists for completeness.
`artifacts validate` is complementary: it checks *structural
correctness* of frontmatter — required fields, status legality,
ID format, and schema constraints — without ever reading or touching
the body. This separates two distinct concerns that must not bleed
into each other.

---

## Scope Boundary

| In scope | Out of scope |
|----------|-------------|
| Frontmatter field presence | Body content |
| Status value legality | Lifecycle transition rules |
| ID format conformance | File-system consistency (orphan links) |
| `KindDef.schema` field constraints | Business / workflow rules |

---

## Data Models

Both live in `src/artifacts_os/core/validate.py`.

```python
from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["error", "warning"]


@dataclass
class ValidationIssue:
    field: str               # frontmatter key involved, or "" for artifact-level
    message: str             # human-readable description
    fixable: bool            # True ↔ --fix can auto-correct this issue
    severity: Severity = "error"   # "error" fails validation; "warning" does not


@dataclass
class ValidationResult:
    name: str                           # artifact name (stem)
    kind: str                           # kind string
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def valid(self) -> bool:
        """True when no *errors* — warnings alone don't invalidate."""
        return not self.errors
```

**Severity semantics.** `error` means the artifact violates a hard
rule the system relies on (missing required key, bad status, ID that
won't resolve). `warning` means the artifact is suspicious but still
functional — currently only unknown-field drift. Exit code 2 triggers
only on errors; warnings appear in output and can be promoted to
errors by a future `--strict` flag.

---

## Core Module — `core/validate.py`

### Public API

```python
from artifacts_os.core.validate import validate_one, validate_many

def validate_one(
    meta: "ArtifactMeta",
    registry: "Registry",
) -> ValidationResult:
    """Validate frontmatter of a single artifact. Pure function; no I/O."""

def validate_many(
    metas: list["ArtifactMeta"],
    registry: "Registry",
) -> list[ValidationResult]:
    """Validate a list of artifacts. Returns one result per artifact."""
```

`validate_one` is a **pure function**: it reads `meta.frontmatter` and
the `KindDef` from the registry but performs no file I/O. This makes
it trivially unit-testable.

### Validation Rules (ordered; all applied, issues accumulated)

Each rule declares its severity in the table at the end of this section.

1. **Required keys** — `id`, `kind`, `title`, `created` must be present
   in `meta.frontmatter`. If `title` is absent but the `name` field is
   present, `title` is not generated from `name` — the missing field is
   still reported. Each missing key produces one `ValidationIssue`
   with `fixable=False`, `severity="error"`.

2. **`kind` resolves** — the `kind` value must be known to the registry
   (`registry.get(kind)` does not raise). If unknown, skip KindDef-
   dependent rules (3–6) and report a single issue; `fixable=False`,
   `severity="error"`.

3. **`status` legality** — if `KindDef.statuses` is non-empty, the
   artifact's `status` value must be in that list. If it is absent or
   unknown, report `field="status"`, `fixable=True`, `severity="error"`
   (fix: set to `KindDef.statuses[0]`, typically `"backlog"`).

4. **`id` format** — checked against the kind's numbering convention:
   - *Numbered kind* (`KindDef.numbered=True`): `id` must match
     `^{prefix}\d{4}$` (e.g. `t0042` for prefix `t`).
   - *Non-numbered kind* (`KindDef.numbered=False`): `id` must satisfy
     `validate_slug(id)` from `core.ids` — i.e. match
     `^[a-z0-9]+(-[a-z0-9]+)*$`.
   - Mismatch → `field="id"`, `fixable=False`, `severity="error"`
     (cannot safely reassign IDs).

5. **`KindDef.schema` constraints** — if `KindDef.schema` is non-empty,
   validate `meta.frontmatter` against the JSON Schema using
   `jsonschema.validate`. Each `jsonschema.ValidationError` becomes one
   `ValidationIssue` with `field` set to the dotted path of the failing
   property, `fixable=False`, `severity="error"`.

6. **Unknown fields** — warn on frontmatter keys that are not
   "recognised". A key is recognised if it is any of:
   - A built-in metadata field:
     `{id, kind, name, title, status, tags, created, started,
     updated, agent, task, parent, subtasks, artifacts, owner,
     assignee, type}`
   - Declared in `KindDef.schema.properties` (if the schema has a
     `properties` object)
   - Present in `KindDef.schema.required` (defensive — should already
     be in `properties`)

   Unrecognised keys produce one `ValidationIssue` per key with
   `field=<key>`, `fixable=False`, `severity="warning"`.

   **Skip this rule** when `KindDef.schema` sets
   `additionalProperties: false` — rule 5 already catches the same
   drift as a schema error, and we don't want to double-report.

### Rule Severity Summary

| # | Rule | Severity | Fixable |
|---|------|----------|---------|
| 1 | Missing required keys | error | no |
| 2 | Unknown `kind` | error | no |
| 3 | Bad `status` | error | yes (→ `statuses[0]`) |
| 4 | Bad `id` format | error | no |
| 5 | Schema constraint violation | error | no |
| 6 | Unknown fields | warning | no |

### Fix Behaviour

`validate_one` never writes. The CLI collects fixable issues and
calls `core.update` to apply corrections:

| Issue | Fix applied |
|-------|-------------|
| `status` absent or not in `KindDef.statuses` | Set `status` to `KindDef.statuses[0]` |

ID corrections and schema violations are not auto-fixable.

---

## CLI Command — `cli/commands/validate.py`

### Interface

```
artifacts validate [<ref>] [--kind KIND] [--all] [--fix] [--dry-run] [-j]
```

| Flag / arg | Effect |
|------------|--------|
| `<ref>` | Validate single artifact (resolved via `core.resolve`) |
| `--kind KIND` | Filter to one kind (only with `--all` or no ref) |
| `--all` | Explicit "validate everything"; same as no args |
| `--fix` | Auto-correct fixable issues via `core.update` |
| `--dry-run` | Show what `--fix` would do; no writes |
| `-j / --json` | JSON output |

`--fix` and `--dry-run` are mutually exclusive at parse time.

### Argument Parsing

```python
def register(subparsers) -> None:
    p = subparsers.add_parser("validate", help="validate artifact frontmatter")
    p.add_argument("ref", nargs="?", help="artifact reference")
    p.add_argument("--kind", "-k", help="filter by kind")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--fix", action="store_true",
                      help="auto-correct fixable issues")
    mode.add_argument("--dry-run", action="store_true",
                      help="show fixes without writing")
    p.add_argument("--all", action="store_true", dest="all_artifacts",
                   help="validate all artifacts (default when no ref)")
    p.add_argument("-j", "--json", action="store_true", dest="json_out",
                   help="JSON output")
    p.set_defaults(func=run)
```

### Dispatch Logic (`run` function)

```python
from artifacts_os.core import get, list_artifacts, update, Registry
from artifacts_os.core.validate import validate_one, validate_many
from artifacts_os.core.errors import ValidationError as CoreValidationError

def run(args, registry: Registry) -> int:
    if args.ref:
        # Single artifact
        meta = get(registry, args.ref, kind=args.kind or None)
        results = [validate_one(meta, registry)]
    else:
        metas = list_artifacts(registry, kind=args.kind or None)
        results = validate_many(metas, registry)

    if args.fix or args.dry_run:
        _apply_fixes(args, registry, results)

    if args.json_out:
        _print_json(results)
    else:
        _print_table(results)

    # Exit code keyed on errors only; warnings do not fail validation.
    has_errors = any(r.errors for r in results)
    return 2 if has_errors else 0
```

`_apply_fixes` iterates results, collects fixable issues, and for each
affected artifact calls `core.update(registry, name, fields={...})`.
With `--dry-run` it only prints what would change.

### Exit Codes

| Code | Condition |
|------|-----------|
| `0` | No errors (warnings alone do not fail) |
| `2` | One or more artifacts have `severity="error"` issues |
| `3` | `<ref>` not found (raised by `core.resolve`, caught in CLI dispatch) |

A vault that produces only warnings exits `0`. A future `--strict`
flag can flip the rule to treat warnings as errors.

Codes 3 and 4 (`NotFoundError`, `AmbiguousError`) are caught by the
existing top-level `_run` handler in `cli/__init__.py` — no special
handling needed in `validate.py`.

### Output — Default (Rich Table)

One section per artifact with issues. Artifacts that pass silently
are not printed unless `-v` (future flag; not in this spec). Each
issue line is prefixed with a severity marker: `E` (error) or `W`
(warning), and `[fixable]` when applicable.

```
validate — 2 errors, 1 warning across 2 artifact(s)

  task / t0042-broken-task
    E  status   Unknown status 'wip' — valid: backlog, ready, in-progress, done  [fixable]
    E  id       ID 't42' does not match expected format 't0042'
    W  assigne  Unknown field 'assigne' (did you mean 'assignee'?)

  agent / researcher
    E  title    Required field 'title' is missing
```

Summary line at the bottom:
`N artifact(s) checked — M valid, K with errors, J with warnings`

### Output — JSON (`-j`)

```json
[
  {
    "name": "t0042-broken-task",
    "kind": "task",
    "issues": [
      {"field": "status",  "message": "Unknown status 'wip'",                "fixable": true,  "severity": "error"},
      {"field": "id",      "message": "ID 't42' does not match expected format", "fixable": false, "severity": "error"},
      {"field": "assigne", "message": "Unknown field 'assigne'",             "fixable": false, "severity": "warning"}
    ]
  }
]
```

Only artifacts with at least one issue are included. Consumers can
filter by `severity` to separate errors from warnings.

---

## Registration in `cli/__init__.py`

Add `validate` alongside existing commands:

```python
from artifacts_os.cli.commands import validate as _validate_cmd

# in _build_parser():
_validate_cmd.register(subparsers)
```

Export `validate_one` and `validate_many` from `core/__init__.py`:

```python
from artifacts_os.core.validate import validate_one, validate_many

__all__ = [
    ...,
    "validate_one",
    "validate_many",
]
```

---

## File Map

| File | Action | Notes |
|------|--------|-------|
| `src/artifacts_os/core/validate.py` | **Create** | Pure validation logic |
| `src/artifacts_os/core/__init__.py` | **Edit** | Export `validate_one`, `validate_many` |
| `src/artifacts_os/cli/commands/validate.py` | **Create** | Thin CLI dispatch |
| `src/artifacts_os/cli/__init__.py` | **Edit** | Import + register command |
| `tests/core/test_validate.py` | **Create** | Unit tests for `validate_one` |
| `tests/cli/test_validate_cmd.py` | **Create** | Integration tests for `run()` |

---

## Test Strategy

### Unit Tests — `tests/core/test_validate.py`

Use the `make_vault` fixture. Construct `ArtifactMeta` objects
directly (no file I/O) for pure `validate_one` tests.

Required cases:

| Test | Asserts |
|------|---------|
| All valid artifact | `result.valid == True`, `issues == []` |
| Missing `id` | Error issue with `field="id"` |
| Missing `kind` | Error issue with `field="kind"` |
| Missing `title` | Error issue with `field="title"` |
| Missing `created` | Error issue with `field="created"` |
| Unknown `status` | Error issue with `field="status"`, `fixable=True` |
| Unknown `kind` | Error issue; KindDef-dependent rules (3–6) skipped |
| Numbered ID wrong format | Error issue with `field="id"`, `fixable=False` |
| Non-numbered ID bad slug | Error issue with `field="id"`, `fixable=False` |
| Schema violation | Error issue, `fixable=False` |
| Unknown field | **Warning** issue, `severity="warning"`, `fixable=False` |
| Unknown field + `additionalProperties: false` | Reported once as schema error (rule 6 skipped), not twice |
| Only warnings present | `result.valid == True`; errors/warnings properties separate them |
| Multiple violations | All accumulated, not short-circuited |

### Integration Tests — `tests/cli/test_validate_cmd.py`

Use the `make_vault` fixture and `Registry`. Call `run(args, registry)`
directly (not subprocess).

Required cases:

| Test | Asserts |
|------|---------|
| All-valid vault | Returns `0` |
| Vault with one bad artifact (error) | Returns `2`; output contains artifact name |
| Vault with only warnings | Returns `0`; warnings still shown in output |
| `--json` mode | Parses as valid JSON; each issue has `severity` key |
| `--fix` corrects status | `core.update` called; re-validate returns `0` |
| `--fix` does not touch warnings | Unknown fields remain after `--fix` |
| `--dry-run` doesn't write | File unchanged after call |
| `<ref>` not found | Raises `NotFoundError` (caught → exit 3) |
| `--kind` filter | Only named kind validated |

---

## Decisions and Trade-offs

| Decision | Rationale |
|----------|-----------|
| `validate_one` is pure (no I/O) | Maximises testability; CLI handles I/O |
| Accumulate all issues per artifact | Avoids repeated runs to find each problem |
| `title` not auto-derived from `name` on fix | Would silently fill wrong data; safer to require explicit fix |
| ID reformatting not fixable | Renaming files changes references; too risky to automate |
| Schema violations not fixable | Cannot safely infer correct values from constraints |
| `--fix` and `--dry-run` mutually exclusive | Semantic conflict; prevents ambiguity |
| JSON excludes valid artifacts | Reduces noise in scripted consumers |
| Unknown fields are warnings, not errors | Catches typos (`assigne`) without blocking CI on benign drift; composes with future `--strict` |
| Skip rule 6 when `additionalProperties: false` | Rule 5 already reports the same keys as schema errors; avoids double-reporting |
| Built-in metadata allowlist for rule 6 | Lifecycle-wide keys (`started`, `task`, `artifacts`, etc.) are recognised everywhere without each kind re-declaring them |

---

## Deferred / Out of Scope

- `-v / --verbose` to show passing artifacts in default output
- `--strict` mode that promotes warnings to errors
- Cross-artifact reference validation (broken wikilinks)
- Body-content validation (kept strictly in `verify`)
