---
kind: spec
id: s0011
name: cli-create-kind-aware-help
status: draft
created: 2026-04-30
agent: developer
task: "[[t0042-cli-create-kind-aware-help]]"
---

# CLI create: Kind-Aware --help

Sub-spec of `s0003`. Documents the two-phase parsing strategy that makes
`artifacts create --kind <kind> --help` render a schema-driven flag list.

---

## 1. Problem

The static `create` parser shows the same flag list regardless of `--kind`.
Fields irrelevant to a kind clutter the output; schema-specific fields
(e.g. `--priority` for `task`, `--status` for `spec`) are not surfaced.

---

## 2. Two-Phase Parsing

### Phase 1 — peek

Build a minimal parser with `add_help=False` and call
`parse_known_args(argv[1:])` to extract `--kind` without consuming
`--help`. Resolution order:

1. Explicit `--kind` flag in argv
2. `cli.defaults.create.kind` from `artifacts.yaml`
3. Hardcoded fallback: `"task"`

Load the JSON schema from `artifacts/kinds/<kind>.json`. If the file does
not exist the kind is unknown; proceed to Phase 2 with `schema = None`.

### Phase 2 — build

Reconstruct the `create` subparser using the resolved kind and schema.
With `schema = None` (unknown kind) the parser is equivalent to the
pre-existing static parser; the error surfaces in `run()` when the
registry rejects the unknown kind.

---

## 3. Variant A — Filter

Convenience flags (`--assignee`, `--owner`, `--parent`, `--depends-on`,
`--type`) are shown only when the resolved schema declares the
corresponding field.

**Declaration check** — a field is considered declared if it appears in:
- `properties` keys, OR
- any entry in `x-columns` (strip the `:format` suffix before matching)

**Filter activation** — Variant A filtering only applies when the schema
has an `x-columns` list. When `x-columns` is absent (schema defines
`properties` only, or is entirely minimal), all convenience flags are
shown as a generic fallback. This avoids hiding flags for kinds whose
schemas haven't yet opted into explicit column declarations.

`--fields` is always shown regardless of kind (universal escape hatch).

---

## 4. Variant B — Augment

For every key in `schema["properties"]` that does **not** already have a
dedicated convenience flag, a `--<field>` flag is derived:

| Schema type | argparse behaviour | Metavar |
|-------------|-------------------|---------|
| `string` (with `enum`) | `choices=enum` | `VALUE` |
| `string` | plain string arg | `TEXT` |
| `integer` | plain string arg | `INT` |
| `array` / has `items` | `action="append"` | `VAL` |
| other | plain string arg | `VALUE` |

Flag name: `field.replace("_", "-")` prefixed with `--`.
Help text: `prop["description"]` if present, otherwise `"set frontmatter <field>"`.

**Fields with existing convenience flags** (never re-added via augment):
`assignee`, `owner`, `parent`, `depends_on`, `type`.

---

## 5. Conflict Handling

If a schema property is named `help`, `version`, `kind`, `body`, `name`,
`fields`, `dry-run`, `body-file`, or any other flag already registered in
the static parser, it is **silently skipped** during augmentation to avoid
argparse conflicts. The field remains reachable via `--fields`.

---

## 6. Behaviour for Unknown Kinds

When `--kind <unknown>` is passed without `--help`: the parser is built
with `schema = None` (static flags only); `run()` calls `registry.get()`
which raises `ValueError` → exit 1 with `error: Unknown kind: '<unknown>'`.

When `--kind <unknown>` is passed **with `--help`**: generic (static) help
is shown; no error is emitted. The unknown-kind error surfaces only on
actual execution.

---

## 7. Flag-Name Conventions

- Schema field `foo_bar` → CLI flag `--foo-bar` (underscore → hyphen)
- Schema field `foo_bar` → `args` dest `foo_bar` (unchanged)
- Enum choices rendered as `|`-joined string in metavar for readability

---

## 8. Backwards Compatibility

All convenience flags that would be hidden by filtering remain accessible
via `--fields KEY=VALUE`. Kind-specific flags (Variant B) that are added
to the parser can also be set via `--fields` — `--fields` always takes
every schema field. Existing tests must continue to pass unchanged.
