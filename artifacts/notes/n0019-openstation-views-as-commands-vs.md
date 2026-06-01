---
created: 2026-05-29
id: n0019
kind: note
name: openstation-views-as-commands-vs
---

Feasibility comparison: can artifacts-os adopt openstation's
"named view promoted to a top-level command" mechanism? What it
would take, and what blocks it. Grounded in
[[r0001-openstation-integration-audit]].

## What openstation does

openstation has two layers stacked on the same `views:` config:

1. **Named views** (`openstation.yaml` → `views:`): columns +
   filters + sort, applied to `list` via `--view NAME`, plus a
   `default_views:` map binding a `type:` to a view. This is the
   classic preset layer (see `.openstation/docs/views.md`).
2. **Views as commands**: a named view is surfaced as a *flat
   top-level verb* — `openstation bugs`, `openstation research`,
   `openstation specs`, `openstation notes` — instead of forcing
   `openstation list --view bugs`. In openstation 0.20.1 these are
   still *hardcoded* subparsers in `cli.py` (e.g. `bugs` is
   literally "Browse bug tasks (type-scoped alias)"). The
   "mechanism" framing is the move to register these verbs
   **declaratively from settings** so an operator adds a view and
   gets a command for free, no code change.

The user-observable win: `os bugs` reads better than
`os list --view bugs`, is tab-discoverable in `--help`, and lets a
vault define its own vocabulary of browse verbs.

## What artifacts-os already has

artifacts-os is *further along on the view model itself* and only
one hop short on the command surface:

| Capability | openstation | artifacts-os today |
|---|---|---|
| Named views (columns/filters/sort) | ✅ `views:` | ✅ `ViewConfig` + **layout / tree / parent_field / prune** (richer) |
| Apply view to `list` | ✅ `list --view` | ✅ `list --view/-V` |
| `default_views` type→view | ✅ | ✅ (+`default_layouts`) |
| **Execute a view directly** | ❌ (only via `list --view`) | ✅ **`artifacts views <name>`** already runs it |
| Inspect a view | partial | ✅ `artifacts views show <name>` |
| View as **flat top-level verb** (`os bugs`) | ✅ (hardcoded) | 🟡 nearest is `artifacts views <name>` (nested, not flat) |
| Kind-scoped top-level verbs (`tasks`/`research`/…) | ✅ (proliferated) | ❌ **deliberately collapsed into `list --kind`** |

So the *only* delta is flat-verb surfacing:
`artifacts <viewname>` vs `artifacts views <viewname>`.

## How we'd implement it (intent, not contract)

The plumbing already exists. `_run()` resolves the vault root and
loads settings **before** `_build_parser()` runs, so view names are
available at parse-build time. A view-command layer would:

- After the static `register(subparsers)` roster, iterate the
  loaded `ViewsConfig.views` and register each name as a top-level
  subparser whose handler executes the view (the same code path
  `artifacts views <name>` already uses).
- Each generated verb needs the `list` flag set (override
  `--status`, `--fields`, `--kind`, projection/layout flags) so a
  view-command stays as capable as `list --view`. That replicates
  `list`'s dynamic per-kind flag registration.

The exact contract (collision rule, flag inheritance, help
grouping) is **architect's call**, not specified here.

## Blockers / open tensions

1. **CLI-convention collision (the real blocker).** CLAUDE.md "CLI
   Conventions" curates a *fixed* flat-verb roster (`list`, `show`,
   `create`, `status`, `verify`, `events`). Injecting arbitrary
   operator-named verbs at the top level invites namespace
   collisions — a view named `list`/`show`/`create` would shadow a
   built-in. Needs a documented resolution rule (built-ins win?
   reserved names? warn-and-skip?).

2. **Strategy fork, not just engineering.** artifacts-os
   *deliberately* did NOT copy openstation's `tasks`/`research`/
   `notes`/`bugs` top-level verbs — it collapsed them into
   `list --kind` / `list --view`. View-as-command reintroduces verb
   proliferation. Decision: is the minimal flat surface a
   deliberate product stance, or is operator-defined vocabulary
   worth the surface growth? This is the gating question.

3. **Overlap with the alias mechanism.** artifacts-os already has
   `DEFAULT_ALIASES` + vault-level `aliases` (`_apply_aliases` in
   `_run`). `bugs → views bugs` (or `list --view bugs`) is
   achievable as an alias *today*, zero new code. So "views as
   commands" may already be 80% solved by aliases — the genuine
   delta is only auto-registration + `--help` discoverability.
   Risk of building a second mechanism that overlaps the first.

4. **Flag-parity cost.** A view-command that can't take
   `--status`/`--fields` overrides is strictly weaker than
   `list --view`; reaching parity means re-running `list`'s dynamic
   flag registration per generated verb. Non-trivial, and argparse
   builds the parser once.

5. **Ownership.** New CLI surface + collision resolution + flag
   inheritance is a *technical contract* → architect spec, not PM
   prose (per role boundary; "no lifecycle logic in cli" is
   unaffected since views are read-only browse).

## Bottom line

Not blocked technically — the view model is richer than
openstation's and `artifacts views <name>` already executes views.
The flat-verb surfacing is a small, well-scoped addition. The real
gate is **product strategy** (does artifacts-os want operator-
defined top-level verbs, given it deliberately collapsed kind-verbs
into `list --kind`?) and the **alias overlap** (much of the value
exists today). Recommend: decide the strategy fork first; if yes,
file a feature task with an architect spec sub-task for the
collision/flag/help contract.

## Sources

- `.openstation/docs/views.md` (openstation views model)
- openstation `src/openstation/cli.py` (hardcoded `bugs`/`research`/
  `specs`/`notes` verbs; `--view` on `list`/`sessions`)
- `src/artifacts_os/views/models.py` (`ViewConfig`/`ViewsConfig`/
  `ViewsSettings`)
- `src/artifacts_os/cli/commands/views.py` (execute/show/list)
- `src/artifacts_os/cli/commands/list.py` (`--view`, dynamic flags)
- `src/artifacts_os/cli/__init__.py` (static subparser roster;
  early root+settings load; `_apply_aliases`)
- [[r0001-openstation-integration-audit]]