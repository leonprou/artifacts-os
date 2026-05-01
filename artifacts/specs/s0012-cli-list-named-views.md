---
kind: spec
id: s0012
name: cli-list-named-views
status: draft
created: 2026-05-01
agent: architect
task: "[[t0048-spec-cli-list-named-views]]"
---

# CLI: Named Views for `artifacts list`

Sub-spec of [[s0003-artifacts-os-cli-module]]. Specifies the CLI
contract for consuming the `views` / `default_views` settings already
modelled in [[s0007-artifacts-os-views-module]].

The data model is shipped (`ViewsSettings`, `ViewConfig`,
`ViewsConfig`); the CLI currently ignores it. This spec defines how
`artifacts list` resolves a named view, applies its filters /
columns / sort, and merges them with explicit CLI flags.

## 1. Background and Cross-References

- **Data model** — [[s0007-artifacts-os-views-module]] (module owns
  `ViewsSettings.from_base` and the YAML parsing). This spec adds
  no new fields to `ViewConfig` / `ViewsConfig`.
- **CLI shape** — [[s0003-artifacts-os-cli-module]] § "Command Set"
  already advertises `--view V`; the flag is currently a TODO at
  the implementation level.
- **Reference implementation** — Open Station's
  [`.openstation/docs/views.md`](../../.openstation/docs/views.md)
  documents the precedence model end-users see; the canonical
  source is `src/openstation/tasks.py:cmd_list` (lines 1049–1102 in
  the reference checkout `~/workspace/open-station/`). This spec
  ports those semantics to `artifacts-os` with three deliberate
  divergences, called out in §10.
- **Settings infrastructure** —
  [[s0010-core-settings-module-spec]] (`Settings.from_base`
  pattern) and `CliSettings` ([[s0003-artifacts-os-cli-module]]
  § "Settings extension"). `cli` already loads `CliSettings`
  early; this spec adds a parallel `ViewsSettings` load on the
  `list` path.

## 2. Goals and Non-Goals

**Goals:**

- Add `--view <name>` to `artifacts list`.
- Auto-bind a view per kind via `default_views` when no
  `--view` is explicit.
- Define a precedence model that is *predictable* and matches the
  Open Station reference, with filter merging at the per-key level.
- Preserve machine-readable contracts for `-q` / `-j`.
- Provide a documented slash-command pattern so vault authors can
  expose curated views as ergonomic shortcuts.

**Non-goals:**

- New view fields beyond `columns`, `filters`, `sort` (those
  belong in s0007 if added later).
- New global flags or new commands.
- Generator tooling for slash-command shims (deferred — see §8).
- Filter expressions richer than equality (deferred — `filters`
  remain a flat key/value map).

## 3. CLI Surface

```text
artifacts list [--kind KIND] [--status STATUS] [--fields FIELDS]
               [--view NAME] [-q | -j]
```

| Flag | Type | New? | Description |
|------|------|------|-------------|
| `--kind`, `-k`     | string | existing | Filter by kind (`task`, `agent`, …). Already supported. |
| `--status`, `-s`   | string | existing | Filter by status. Already supported. |
| `--fields`, `-f`   | string | existing | Field-spec column list. Already supported. |
| `--view`, `-V`     | string | **new**  | Named view from `artifacts.yaml`. Capital `-V`; `-v` reserved for a future `--verbose`. |
| `-q`, `--quiet`    | bool   | existing | One name per line. Mutually exclusive with `-j`. |
| `-j`, `--json`     | bool   | existing | JSON output. Mutually exclusive with `-q`. |

**Decision — alias for `--view`:** `-V`. Rationale: leave the
lowercase `-v` slot free for `--verbose`, which the project does
not yet have but is conventional. The two-letter form `-V` is
already standard for "Version" in some tools, but `artifacts-os`
uses `--version` from argparse `version` action and never `-V`,
so the slot is free.

**No new long aliases** (e.g. `--with`, `--preset`). Match the
Open Station reference exactly to keep mental models aligned.

## 4. Resolution Algorithm

Triggered for **every** invocation of `cli.commands.list.run`,
*before* `list_artifacts` is called. Pseudocode:

```python
def resolve_list_args(args, registry, settings: ViewsSettings | None):
    # 1. Determine the active "binding kind".
    binding_kind = args.kind  # may be None when user omitted --kind

    # 2. Resolve view name.
    view_name = args.view
    if view_name is None and binding_kind is not None and settings is not None:
        view_name = (settings.views.default_views.get(binding_kind)
                     if settings.views else None)
        if view_name is not None:
            _assert_view_exists(settings, view_name, bound_from=binding_kind)

    # 3. Look up ViewConfig (if any).
    view_cfg: ViewConfig | None = None
    if view_name is not None:
        if settings is None or settings.views is None \
                or view_name not in settings.views.views:
            _err(f"unknown view '{view_name}'")
            return EXIT_VALIDATION  # 2
        view_cfg = settings.views.views[view_name]

    # 4. Merge filters per-key. Explicit flags win.
    if view_cfg is not None:
        for key, val in view_cfg.filters.items():
            if key == "status" and args.status is None:
                args.status = val
            elif key == "kind" and args.kind is None:
                args.kind = val
            # Any other key: stored on args._extra_filters for
            # post-discovery filtering (status/kind already
            # consumed natively by list_artifacts).
            else:
                args._extra_filters[key] = val

    # 5. Resolve column list (precedence — see §5).
    args._columns = _resolve_columns(args, view_cfg, registry)

    # 6. Stash sort key (post-discovery sorting — see §6).
    args._sort = view_cfg.sort if view_cfg is not None else None

    return EXIT_OK
```

Step-by-step, this matches `cmd_list` lines 1049–1102 with three
deliberate differences:

1. The binding key is **`--kind`** (not `--type`). Open Station
   uses `--type` because tasks carry a `type` frontmatter field;
   `artifacts-os` is kind-first, so the binding key is `kind`.
2. **Unknown explicit `--view` is a hard error** (exit 2). The
   reference issues a `core.warn(...)` and continues. We diverge
   because slash-command shims silently failing is harder to
   debug than a typo in `artifacts.yaml`.
3. **No silent fall-through when `views:` is absent.** If
   `--view foo` is passed and `artifacts.yaml` has no `views`
   section, exit 2 with `"error: unknown view 'foo' (no 'views:'
   section in artifacts.yaml)"`. `default_views` binding has no
   such effect — it is silently a no-op when `views:` is absent.

## 5. Precedence Rules

### Columns

```text
explicit --fields  >  view.columns  >  registry default columns
```

| Source | Activates when | Notes |
|--------|---------------|-------|
| `args.fields` | `--fields` non-empty | Wins outright. Passed through `views.parse_field_specs`. |
| `view_cfg.columns` | A view is active and `--fields` empty | Same `parse_field_specs` syntax as `--fields`. |
| `registry default` | Neither of the above | `views.default_columns(kind_def)`; falls back to `["name", "summary"]` per s0007. |
| Hardcoded fallback (`name,status,kind`) | Multi-kind / `kind` is None | Existing behaviour — see `list.run`. |

### Filters

```text
explicit CLI flag  >  view.filters[key]  (per-key merge)
```

- `--status active` wins over `view_cfg.filters["status"] = "ready"`;
  `view_cfg.filters["assignee"] = "alice"` still applies.
- `--kind` overrides `view_cfg.filters["kind"]`.
- Per-key merge, **never** wholesale replacement.
- Filter keys other than `status` / `kind` are stashed on
  `args._extra_filters` and applied as a final pass over the
  result of `list_artifacts` (post-discovery filter; see §11.3).

### View source

```text
explicit --view  >  default_views[binding_kind]  >  no view
```

Only one view is ever active. `--view foo` always beats the
`default_views[kind]` mapping.

## 6. Sort

`view_cfg.sort` is honoured via a post-discovery sort pass.
`list_artifacts` does not sort beyond `path.stem`; the CLI sorts
the returned `list[ArtifactMeta]` in `list.run`.

```python
def _apply_sort(items: list[ArtifactMeta], sort_key: str | None) -> list[ArtifactMeta]:
    if not sort_key:
        return items
    reverse = sort_key.startswith("-")
    key = sort_key.lstrip("-")
    return sorted(items,
                  key=lambda m: (str(m.frontmatter.get(key, "")) == "",
                                 str(m.frontmatter.get(key, ""))),
                  reverse=reverse)
```

The `(missing, value)` tuple key pushes rows lacking the sort
field to the **end** in both ascending and descending modes.
This is the predictable contract; without it descending sort
puts blanks at the top, which is rarely what a user wants.

**Decision — sort stability across kinds:** When the result set
spans multiple kinds (no `--kind` filter, multi-kind view), the
sort is best-effort lexicographic on the stringified frontmatter
value. This is consistent and dependency-free; richer ordering
(per-kind status order, etc.) is out of scope.

## 7. `default_views` Binding

### Activation

`default_views[binding_kind]` is consulted only when:

1. `args.view is None` — the user did not pass `--view`.
2. `binding_kind is not None` — the user passed `--kind <k>`,
   *or* a future "homogeneous result detection" supplies a kind.
   For this spec, **only the explicit `--kind` form fires the
   binding.** Inferring kind from a homogeneous result set is
   deferred (see §10).

### Lookup keys

- The dict is keyed by **kind name** (e.g. `task`, `note`,
  `agent`), not artifact `type`. This differs from the Open
  Station reference, which keys by `type`. The artifacts-os `type`
  field is itself a frontmatter convention used by some kinds
  (mostly `task`); kind is the universal axis.

### Error semantics

If `default_views[k] = "v"` and `v` is not in `views:`:

```
error: default_views.<k> refers to unknown view '<v>'
```

Exit code: `2` (`ValidationError`-equivalent, matches openstation
reference). Emit on stderr; the rest of the command must not
proceed.

If `default_views[k] = "v"` but the user passes `--view other`
explicitly, the binding is ignored entirely — no validation of
the bound view runs. Rationale: an explicit `--view` is a stronger
signal of intent, and validating an unused binding produces
confusing errors.

## 8. JSON / Quiet Contract

The contract from `.openstation/docs/views.md` § "JSON and Quiet
Modes" applies verbatim:

| Output mode | `args.fields` | `view.columns` | `view.filters` | `view.sort` |
|-------------|---------------|----------------|----------------|-------------|
| default (table) | applied | applied (if no `--fields`) | applied | applied |
| `-q` / `--quiet` | **ignored** | **ignored** | applied | applied |
| `-j` / `--json` | **ignored** | **ignored** | applied | applied |

`-q` and `-j` continue to print the existing shapes (one stem per
line; JSON list of frontmatter dicts). Filters and sort take effect
on the `list_artifacts` result *before* serialization, so machine
consumers see view-filtered, view-sorted data without paying for
column resolution.

**Implementation note** — `list.run` already short-circuits to
quiet/JSON before building `columns`. The patch must (a) move the
filter / sort resolution **above** that short-circuit and (b)
leave column resolution **below** it.

## 9. Error Handling

| Condition | Exit | Stderr message |
|-----------|------|----------------|
| `--view foo` and `views:` section missing | `2` | `error: unknown view 'foo' (no 'views:' section in artifacts.yaml)` |
| `--view foo` and `foo` not in `views:` | `2` | `error: unknown view 'foo'` |
| `default_views.k = "v"` and `v` not in `views:` | `2` | `error: default_views.<k> refers to unknown view '<v>'` |
| `views:` entry malformed (no `columns`) | `2` | Existing `ViewConfig` parser raises `ValueError`; surface as `error: <message>`. |
| `views:` section absent **and** no `--view` flag | `0` | Silent no-op — `list` runs as today. |
| `--view foo` and `artifacts.yaml` cannot be loaded | `2` | `error: <load_settings exception>`. |

All exits go through the existing `except` cascade in
`cli/__init__.py:_run` — surface the message as
`ValidationError` (exit 2) so the wrapper formats it consistently.

## 10. Open Questions — Resolved

| Question | Resolution | Rationale |
|----------|-----------|-----------|
| Alias for `--view`? | `-V` | `-v` left free for future `--verbose`; capital `V` is unambiguous, no conflict with `argparse` `version` action (we use `--version` only). |
| Sort stability across kinds? | Lexicographic on `str(value)`; missing → end. | Cheap, predictable, framework-free. Per-kind ordering is deferred. |
| Filter keys allowed | `status`, `kind` consumed natively by `list_artifacts`; any other key applied as a post-discovery equality filter against `frontmatter[key]`. | Matches the openstation reference's "unknown keys silently ignored at validation time" while still being useful for `assignee`, `type`, `priority`, etc. |
| Bind `default_views` by `--kind` or `--type`? | `--kind`. | `artifacts-os` is kind-first; `type` is a per-kind convention. Cross-link to s0007: the data model already uses `default_views: dict[kind_name, view_name]`. |
| Bind on homogeneous result detection? | **Deferred.** Only explicit `--kind` fires the binding. | Inference adds a second binding mechanism with two-step error reporting (which kind? which view?). Defer to a follow-up if there's user demand. |
| Generator for slash-command shims? | **Deferred.** Document by example. | Not enough variation to justify a generator; one example shim under `.openstation/commands/` is enough to copy. |

## 11. Implementation Outline

This spec is delivered by the parent task
[[t0047-cli-list-named-views]]. The following file-level changes
are normative — the implementing developer must touch each one.

### 11.1 `src/artifacts_os/cli/commands/list.py`

Add a helper that wraps the algorithm in §4 and call it before
the existing branches:

```python
from artifacts_os.views import (
    ViewsSettings, parse_field_specs, default_columns, render_table,
)
# ...
def register(subparsers) -> None:
    p = subparsers.add_parser("list", help="list artifacts")
    p.add_argument("--kind", "-k", help="filter by kind")
    p.add_argument("--status", "-s", help="filter by status")
    p.add_argument("--fields", "-f", help="field spec string …")
    p.add_argument("--view", "-V", help="named view from artifacts.yaml")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-q", "--quiet", action="store_true")
    mode.add_argument("-j", "--json", action="store_true", dest="json_out")
    p.set_defaults(func=run)


def run(args, registry: Registry) -> int:
    views_settings = _load_views_settings(registry.root)
    _apply_view(args, views_settings)        # mutates args; raises
                                             # ValidationError on failure

    items = list_artifacts(
        registry,
        kind=args.kind or None,
        status=args.status or None,
    )
    items = _apply_extra_filters(items, getattr(args, "_extra_filters", {}))
    items = _apply_sort(items, getattr(args, "_sort", None))

    if args.quiet:
        ...   # unchanged
    if args.json_out:
        ...   # unchanged
    columns = _resolve_columns(args, getattr(args, "_view_cfg", None), registry)
    table = render_table(items, columns, kind_def=...)
    Console().print(table)
    return 0
```

### 11.2 `src/artifacts_os/cli/__init__.py`

`_load_cli_settings` already reads `artifacts.yaml`. Either:

- **Option A (recommended):** add a parallel `_load_views_settings(root)`
  helper that returns `ViewsSettings | None`. Lazily called only
  by `list.run` so `init` and other pre-registry commands are
  unaffected. Keeps the `list` path self-contained.
- **Option B:** widen `CliSettings` to include parsed
  `ViewsSettings`. Rejected — couples `cli` settings parsing to
  `views` (violates module DAG `core → views → cli`).

Pick A.

### 11.3 Post-discovery filter helper

```python
def _apply_extra_filters(items, extra: dict[str, Any]) -> list:
    if not extra:
        return items
    return [
        m for m in items
        if all(str(m.frontmatter.get(k, "")) == str(v) for k, v in extra.items())
    ]
```

Equality only, stringified. Matches openstation behaviour for
`type`, `assignee`, `priority`, etc.

### 11.4 Tests — `tests/cli/test_list_views.py` (new)

Required cases:

1. `--view active` resolves filters + columns + sort.
2. `--view active --status all` overrides status; other filters
   stay.
3. `default_views: {task: active}` + `--kind task` fires the
   binding.
4. `default_views: {task: active}` + no `--kind` does **not**
   fire.
5. `--view does-not-exist` → exit 2, stderr matches.
6. `default_views: {task: missing}` + `--kind task` → exit 2,
   stderr matches.
7. `--view active -j` → JSON contains all frontmatter keys
   (columns ignored), but filters and sort applied.
8. `--view active -q` → quiet stems list, filtered + sorted.
9. `--fields x,y --view active` → `--fields` wins, `view.filters`
   still apply.
10. View with custom filter key (e.g. `assignee: alice`) →
    post-discovery filter behaves correctly.

Use the existing `vault` and `write_artifact` fixtures from
`tests/cli/conftest.py`. Add a tiny `make_artifacts_yaml` helper
that writes `views:` and `default_views:` sections, or extend the
fixture if the module already has one.

### 11.5 Documentation updates

- `src/artifacts_os/cli/README.md` — append a "Views" subsection
  under `list`. Mirror the structure of
  `.openstation/docs/views.md` but trimmed to the artifacts-os
  surface.
- `docs/settings.md` — add a "Views section" pointer with a
  worked YAML example, cross-linking to the views README.
- `s0003-artifacts-os-cli-module.md` — flesh out the existing
  one-line `--view` reference under "create flags" and the
  `list` synopsis to point at this spec.

### 11.6 Slash-command example

Ship one example shim under `.openstation/commands/`:

`artifacts.list.<view-name>.md` — convention
`artifacts.list.<view>` for any named view. The example must be
runnable against the artifacts-os vault's own `artifacts.yaml`.

## 12. Slash-Command Pattern

Convention for vault authors who want to expose a named view as a
slash command:

- **Filename:** `.openstation/commands/artifacts.list.<view>.md`
  where `<view>` matches the `views:` key in `artifacts.yaml`.
- **Frontmatter:** `name: artifacts.list.<view>`,
  `description: …` (one line, agent-facing).
- **Body:** A short rationale plus a single fenced bash block:

  ```bash
  artifacts list --view <view>
  ```

- The shim is intentionally thin — it never duplicates the
  view's columns / filters in the command body. Any change to
  the view's definition in `artifacts.yaml` is picked up on the
  next invocation.

**Generator status:** Deferred. Authors copy
`.openstation/commands/openstation.list.backlog.md` (the
existing pattern) and adapt it. If duplication becomes painful,
revisit with a `artifacts ai install --views` follow-up task.

## 13. Verification

The parent task [[t0047-cli-list-named-views]] inherits these
checks:

- [ ] `artifacts list --view <name>` end-to-end (filters,
      columns, sort all applied).
- [ ] `default_views: {<kind>: <view>}` fires automatically when
      `--kind <kind>` is supplied and no `--view` is.
- [ ] Per-key filter merging: explicit `--status` overrides
      view's `filters.status` while leaving other keys intact.
- [ ] Unknown `--view` exits `2` with a clear stderr message.
- [ ] Unknown bound view exits `2` with the
      `default_views.<k>` message.
- [ ] `-j` and `-q` ignore columns but apply filters + sort.
- [ ] `tests/cli/test_list_views.py` covers all 10 cases in
      §11.4.
- [ ] `src/artifacts_os/cli/README.md` and `docs/settings.md`
      reflect the final shape.
- [ ] At least one `.openstation/commands/artifacts.list.<v>.md`
      shim shipped, demonstrating the pattern in §12.
- [ ] `s0007` and `.openstation/docs/views.md` cross-linked
      from this spec (already done in §1).

## 14. Decision Log

| Marker | Items |
|--------|-------|
| **Decided** | Alias `-V`. Bind by `--kind`. Unknown `--view` is exit 2. Filter merge per-key. Sort: lexicographic with missing-last. View-on-quiet/json applies filters+sort, ignores columns. |
| **Recommended** | Helper-based loader (Option A in §11.2) over coupling `CliSettings` to views. Document slash-command pattern by example only. |
| **Deferred** | Homogeneous-result-set inference of `binding_kind`. Generator for slash-command shims. Richer filter expressions. Per-kind sort orderings. |
