---
kind: spec
name: views
---

# Views

Views are named presets for `openstation list` that bundle column
selection, filters, and sort order into a reusable configuration.
They are defined in `openstation.yaml` and activated with `--view`.

---

## Quick Start

```bash
# Use a named view
openstation list --view mine

# Override a view's filter inline
openstation list --view mine --status all

# Use --fields without a view
openstation list --fields id,name,status,created:date
```

---

## `--fields` Flag

`--fields` controls which columns appear in list output and how
values are formatted.

### Syntax

```
--fields FIELD_SPEC[,FIELD_SPEC...]
```

Each `FIELD_SPEC` has the form:

```
field[:format] [as Alias]
```

| Part | Required | Description |
|------|----------|-------------|
| `field` | yes | Frontmatter key to display (e.g. `id`, `status`, `created`) |
| `:format` | no | Format hint applied before display. Unknown hints pass raw. |
| `as Alias` | no | Column header override (case-preserved). |

### Format Hints

| Hint | Output |
|------|--------|
| `date` | `YYYY-MM-DD` (date portion only) |
| `datetime` | `YYYY-MM-DD HH:MM` (no seconds) |

Format hints only affect display — filtering and sort are unaffected.
Unknown hints pass the value through raw without warning.

### Examples

```bash
# Three columns, no formatting
--fields id,name,status

# Format a timestamp as date-only
--fields id,name,created:date

# Custom column header
--fields id,name,created:date as Created

# Mixed: raw, formatted, aliased, quoted alias
--fields id,status,created:date as Date,updated:datetime as "Last Updated"
```

Whitespace around commas and within `as Alias` is trimmed. The `as`
keyword is case-insensitive. Aliases with spaces must be quoted in
the shell.

---

## `--view` Flag

`--view <name>` loads a named view from `openstation.yaml`, applying
its `columns`, `filters`, and `sort` as defaults for the invocation.

```bash
openstation list --view mine
openstation list --view review-queue
```

If the named view does not exist in `openstation.yaml`, the CLI exits
with code 2 and an error message.

---

## View Schema

Views are defined under the `views` top-level key in `openstation.yaml`:

```yaml
views:
  <name>:
    columns: <field-spec-list>   # optional
    filters:                     # optional
      <field>: <value>
    sort: <field>                # optional
```

| Key | Type | Description |
|-----|------|-------------|
| `columns` | string | Comma-separated field spec list. Same syntax as `--fields`. |
| `filters` | object | Equality filters. Recognised keys: `status`, `assignee`, `type`. Unknown keys are silently ignored. |
| `sort` | string | Field to sort by (ascending). |

All keys are optional. A view with no keys is valid but has no effect.

The special value `me` in `filters.assignee` resolves to the current
user's username at query time.

### Example

```yaml
views:
  mine:
    columns: id,name,status,created:date as Since
    filters:
      assignee: me
      status: active
    sort: created

  review-queue:
    columns: id,name,assignee,status
    filters:
      status: review
    sort: created

  backlog:
    columns: id,name,type,created:date
    filters:
      status: backlog
```

---

## `default_views`

Maps artifact types to named views, applied automatically when
`openstation list` is run without an explicit `--view` flag.

```yaml
default_views:
  <artifact-type>: <view-name>
```

Each key is an artifact type string (matches the `type:` frontmatter
field). Each value must be a view name defined in `views:`.

### Example

```yaml
views:
  active-features:
    columns: id,name,assignee,status
    filters:
      type: feature
      status: active

  session-log:
    columns: id,name,started:datetime,status
    sort: started

default_views:
  feature: active-features   # openstation list --type feature → active-features
  session: session-log       # openstation sessions            → session-log
```

If a bound view name does not exist in `views:`, the CLI exits with
code 2:

```
error: default_views.feature refers to unknown view 'active-features'
```

---

## Precedence

When multiple sources specify the same setting:

```
explicit CLI flag  >  --fields  >  view columns  >  default columns
explicit --view    >  default_views binding       >  no view
```

Detail:

| Setting | Overrides |
|---------|-----------|
| `--fields` on CLI | `columns` from view |
| `--status` on CLI | `filters.status` from view |
| `--assignee` on CLI | `filters.assignee` from view |
| `--view` | `default_views` binding |

**Filter merging:** filters are merged per key, not replaced wholesale.
`--status active` overrides `filters.status` from the view but leaves
`filters.assignee` intact.

---

## JSON and Quiet Modes

`--json` (`-j`) and `--quiet` (`-q`) are unaffected by column settings:

- `--fields` is silently ignored (all fields are output)
- `--view` still applies `filters` and `sort`, but not `columns`

This preserves machine-readable output contracts.

---

## Full `openstation.yaml` Example

```yaml
views:
  mine:
    columns: id,name,status,created:date as Since
    filters:
      assignee: me
      status: active
    sort: created

  review-queue:
    columns: id,name,assignee,status
    filters:
      status: review
    sort: created

  session-log:
    columns: id,name,started:datetime,status
    sort: started

default_views:
  session: session-log
```

See [settings.md](settings.md) for the full `openstation.yaml` schema
and [cli.md](cli.md) for the complete `list` flag reference.
