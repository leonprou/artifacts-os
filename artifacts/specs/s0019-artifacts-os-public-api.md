---
agent: architect
created: 2026-05-03
id: s0019
kind: spec
name: artifacts-os-public-api
status: draft
---

# artifacts-os Public API Spec

Locks the public Python API surface of `artifacts-os` — the symbols
re-exported from the top-level package and the contracts they imply.
Consumers (OpenStation CLI, agent harness, third-party scripts) build
against this surface.

**Scope: design only.** This spec freezes the API contract; it does
not change implementation. Any change to a function signature, error
class, or return-type below is a breaking change and requires a new
spec revision.

## 1. Background and Cross-References

- **Parent spec** — [[s0002-artifacts-os-architecture]]. Defines the
  module DAG and overall architecture; this spec narrows to the API
  surface specifically.
- **Module system** — [[s0005-artifacts-os-module-system]]. Locks the
  one-way dependency rules this API respects.
- **Existing code** — `src/artifacts_os/__init__.py`. Authoritative
  re-export shim.
- **Existing code** — `src/artifacts_os/core/__init__.py`. Source of
  every re-exported symbol.
- **Docs** — `docs/architecture.md`. Human-facing summary that must
  stay in sync with this spec.

## 2. Goals and Non-Goals

### 2.1 Goals

1. Enumerate every symbol that callers may import from
   `artifacts_os` and `artifacts_os.core`, with type signature.
2. Lock the behavioural contracts — atomic writes, body immutability,
   error mapping — that consumers rely on.
3. Define stability tiers so additive vs. breaking changes are
   unambiguous in code review.

### 2.2 Non-Goals

- **CLI surface** — covered by [[s0003-artifacts-os-cli-module]].
  This spec stops at the Python API.
- **Settings extension API** — covered by `docs/settings.md` and the
  `from_base` pattern; only the public symbols are listed here.
- **Internal modules** (`frontmatter`, `ids`, `vault.find_vault_root`
  internals) — implementation detail; not part of the surface.
- **TUI / log / ai modules** — stubs; their public APIs are owned
  by `s0006`, `s0004`, `s0001` respectively.

## 3. Locked Decisions Summary

| ID | Decision |
|----|----------|
| D1 | Two import roots: top-level `artifacts_os` for everyday symbols; `artifacts_os.core` for settings/validation. |
| D2 | Body is immutable through `update`; callers needing body changes write the file directly. |
| D3 | All errors derive from `ArtifactError`; `NotFoundError`, `AmbiguousError`, `ValidationError` are the three concrete subclasses callers may catch. |
| D4 | Models are frozen-shape dataclasses — additive fields only; renames or removals are breaking. |
| D5 | `list_artifacts` accepts a unified `filters=` dict; legacy `status=` and `tag=` kwargs remain but emit `DeprecationWarning`. |
| D6 | Graph traversal is exposed via `parent` / `children`; both accept `str | ArtifactMeta | Path` for ergonomics. |

## 4. Surfaces

### 4.1 Top-level package — `artifacts_os`

```python
from artifacts_os import (
    # vault / registry
    find_vault_root, Registry, KindDef,

    # CRUD
    create, get, update,

    # discovery
    list_artifacts, resolve, search, parent, children,

    # models
    Artifact, ArtifactMeta,

    # errors
    ArtifactError, NotFoundError, AmbiguousError, ValidationError,
)
```

| Aspect | Spec |
|---|---|
| **Trigger** | Any consumer of `artifacts-os` |
| **Stability** | Public — covered by semver |
| **Source** | Re-export from `artifacts_os.core` (no logic in `__init__.py`) |
| **Output shape** | Functions, dataclasses, exception classes |

### 4.2 Core submodule — `artifacts_os.core`

Symbols not re-exported at top level but still public:

```python
from artifacts_os.core import (
    # settings
    load_settings, Settings, ProjectConfig, UnsupportedSchemaVersion,

    # validation
    validate_one, validate_many, ValidationIssue, ValidationResult,

    # graph traversal (also re-exported at top level)
    parent, children,

    # L1 catalogue
    KindCatalog, KindCatalogEntry,
)
```

| Aspect | Spec |
|---|---|
| **Trigger** | Consumers extending settings, running validation, iterating the kinds catalogue |
| **Stability** | Public — but importing from `artifacts_os.core` is required (intentionally not re-exported to keep top-level surface compact) |

### 4.3 Function contracts

```python
def find_vault_root(start: Path | None = None) -> Path | None: ...
```
Walks up from `start` (default CWD) until it finds
`artifacts/artifacts.yaml`. Returns the parent directory or `None`.
Pure FS walk; no git dependency.

```python
class Registry:
    def __init__(self, kinds: list[KindDef], root: Path | None = None) -> None: ...
    @property
    def root(self) -> Path | None: ...
    def get(self, kind: str) -> KindDef: ...           # raises ValueError on unknown
    def all(self) -> list[KindDef]: ...
    def for_dir(self, dir_name: str) -> KindDef | None: ...
```
Caller-supplied kinds are merged with vault-defined kinds loaded
from `artifacts/kinds/*.json` (and `artifacts/kinds/<name>/kind.json`,
folder form takes precedence on collision). Caller kinds win on
duplicate names against caller list (raises `ValueError` on caller
duplicates); vault kinds override caller kinds with the same name.

```python
def create(
    registry: Registry,
    kind: str,
    title: str,
    *,
    body: str = "",
    fields: dict | None = None,
) -> Artifact: ...
```
- Allocates ID with `O_CREAT | O_EXCL`; retries up to 5× on race.
- Always writes `kind`, `id`, `name` (slug) into frontmatter.
- Validates merged frontmatter against `KindDef.schema`; raises
  `ValidationError` on failure.
- Returns the parsed `Artifact` (with body) — never the dict that
  was passed in.

```python
def get(registry: Registry, ref: str, *, kind: str | None = None) -> Artifact: ...
```
Resolves `ref` (full stem, prefixed ID, all-digit ID, or partial
slug), reads the file, returns full `Artifact`. Raises
`NotFoundError` or `AmbiguousError`.

```python
def update(
    registry: Registry,
    ref: str,
    *,
    status: str | None = None,
    fields: dict | None = None,
) -> Artifact: ...
```
- **Frontmatter only.** Body bytes are preserved verbatim — no
  re-rendering, no normalisation.
- Merge semantics: existing frontmatter is shallow-merged with
  `fields`, then `status` overrides if supplied.
- Validates status against `KindDef.statuses` (when non-empty) and
  the full frontmatter against `KindDef.schema`. Either raises
  `ValidationError`.
- Atomic via `tmp + os.replace`.

```python
def list_artifacts(
    registry: Registry,
    kind: str | None = None,
    *,
    filters: dict[str, Any] | None = None,
    status: str | None = None,   # deprecated
    tag: str | None = None,      # deprecated
) -> list[ArtifactMeta]: ...
```
- `kind=None` queries every registered kind directory.
- `filters` keys must be known for the kind (built-ins +
  `KindDef.schema.properties` + `required`); unknown keys raise
  `ValidationError`. Cross-kind queries (`kind=None`) accept a key
  if any registered kind knows it.
- `tags` filter uses list-membership; all other filters use
  stringified equality.
- `status=` / `tag=` shim warns and folds into `filters`; removed
  in next minor.

```python
def resolve(registry: Registry, query: str, *, kind: str | None = None) -> Path: ...
def search(registry: Registry, query: str, *, kind: str | None = None) -> list[ArtifactMeta]: ...
```
`resolve` returns exactly one Path or raises; `search` returns the
full match set (possibly empty) without raising.

```python
def parent(
    registry: Registry,
    ref: str | ArtifactMeta | Path,
    *,
    kind: str | None = None,
) -> ArtifactMeta | None: ...

def children(
    registry: Registry,
    ref: str | ArtifactMeta | Path,
    *,
    kind: str | None = None,
    status: str | None = None,
) -> list[ArtifactMeta]: ...
```
Read the `parent` frontmatter wikilink/ref; resolve cross-kind
(no kind restriction — task → spec works). `parent` returns `None`
when no field; raises `NotFoundError` / `AmbiguousError` only when
the field exists but does not resolve cleanly. `children` is a
predicate query — empty list is a valid answer; never raises.

### 4.4 Models

```python
@dataclass
class KindDef:
    name: str
    dir: str
    prefix: str
    numbered: bool
    statuses: list[str] = []
    schema: dict = {}
    meta: dict = {}
    required_fields: list[str] | None = None
    description: str | None = None     # from ARTIFACT.md L1
    has_template: bool = False         # ARTIFACT.md present?

@dataclass
class ArtifactMeta:
    id: str
    kind: str
    name: str
    title: str
    status: str | None
    tags: list[str]
    created: str
    path: Path
    frontmatter: dict

@dataclass
class Artifact(ArtifactMeta):
    body: str = ""
```

- `name` is the **slug only** — never the full stem. The full stem
  is `path.stem`.
- `frontmatter` carries the raw merged dict — agents that need
  custom keys read from here.
- New fields may be appended (additive); rename/remove is breaking.

### 4.5 Error hierarchy and exit-code mapping

```
ArtifactError              ── exit 1
├── NotFoundError          ── exit 3
├── AmbiguousError         ── exit 4
└── ValidationError        ── exit 2
```

All public functions raise only these classes (or stdlib `OSError`
for raw FS faults). Catch `ArtifactError` to handle every library
failure.

## 5. Backwards Compatibility

| Change | Compat impact |
|---|---|
| Add a new top-level re-export | Additive — non-breaking |
| Add a field to a dataclass model | Additive — non-breaking (callers who use `dataclass.replace` keep working) |
| Add a new `KindDef.statuses` value | Owned by the vault; library is unaffected |
| Rename or remove any function in § 4.3 | **Breaking** — requires major bump |
| Tighten validation (e.g. reject input previously accepted) | **Breaking** — requires deprecation cycle |
| Remove `list_artifacts(status=, tag=)` shim | **Breaking** — already deprecation-warned; scheduled for next minor |
| Change error class for an existing failure | **Breaking** — requires a new spec revision |

## 6. Test Plan

### 6.1 Surface contract

- `test_top_level_exports`: import every name in `__all__` from
  `artifacts_os`; assert no `ImportError` and all are callables /
  classes.
- `test_core_exports`: same for `artifacts_os.core`.
- `test_no_unintended_top_level_symbols`: assert `dir(artifacts_os)`
  matches `__all__` plus stdlib dunders.

### 6.2 CRUD invariants

- `test_create_atomic`: concurrent creates do not collide on ID.
- `test_update_preserves_body`: feed unicode + trailing whitespace
  + code fences through `update`, assert byte-for-byte equality.
- `test_update_rejects_unknown_status`: raise `ValidationError`
  with allowed-status list in message.

### 6.3 Discovery

- `test_resolve_disambiguates_by_kind`: same slug across kinds
  resolves correctly when `kind=` supplied.
- `test_list_artifacts_filters_validate`: unknown filter key
  raises `ValidationError` with the known-keys list.
- `test_legacy_kwargs_warn`: `list_artifacts(status="x")` emits
  `DeprecationWarning` and still works.

### 6.4 Graph traversal

- `test_parent_resolves_wikilink`: `parent: "[[s0017-name]]"`
  resolves cross-kind.
- `test_children_no_field_returns_empty`: artifact with no
  `parent` field appears under no parent's `children`.

### 6.5 Errors

- `test_error_hierarchy`: every concrete error subclasses
  `ArtifactError`.
- `test_not_found_message_contains_query`: error messages include
  the offending ref / query string for debuggability.

## 7. Implementation Notes

This spec is **descriptive of what already ships** — no new code is
required. The follow-up task is verification only:

1. Run § 6 tests; confirm they exist or file a sub-task to add the
   missing ones.
2. Reconcile `docs/architecture.md` § "Public API Entry Points"
   with § 4 of this spec; update wherever they drift.
3. Mark this spec `approved` after reviewer sign-off; future
   surface changes amend this spec under `## Scope History`.

Out of scope:

- CLI surface — `s0003`.
- Settings extension API beyond the symbol list — `docs/settings.md`.
- TUI / ai / log module APIs — separate specs.

## 8. Cross-References

- [[s0002-artifacts-os-architecture]] — parent spec (architecture)
- [[s0005-artifacts-os-module-system]] — module DAG rules
- [[s0003-artifacts-os-cli-module]] — sibling spec (CLI surface)
- [[s0014-core-unified-filter-api]] — `filters=` decision rationale
- [[s0017-artifact-kinds-discovery-mechanism]] — L1 ARTIFACT.md fields on `KindDef`
- `src/artifacts_os/__init__.py` — re-export shim
- `src/artifacts_os/core/__init__.py` — symbol source
- `docs/architecture.md` — human-facing summary that mirrors this spec