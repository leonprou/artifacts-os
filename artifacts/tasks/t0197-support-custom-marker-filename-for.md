---
assignee: architect
created: 2026-06-01
id: t0197
kind: task
name: support-custom-marker-filename-for
owner: user
status: backlog
type: feature
---

# Support Custom Marker Filename for Vault Discovery and Settings Loading

## Goal

Add an entry point that lets a host application substitute the
default `artifacts.yaml` vault marker with a custom filename
(e.g. `openstation.yaml`). The schema, location semantics
(project root), and `from_base` extension model are unchanged —
only the *filename* and the *discovery target* become
configurable.

This unblocks openstation's single-file settings design (see
`~/workspace/os/open-station/openstation/specs/s2068-openstation-module-system.md`
§ 3 and the user-feedback section of t0464 in that vault),
where openstation wants exactly one config file at project root
named `openstation.yaml` containing both artifacts-os standard
settings and openstation extensions, leveraging the documented
`from_base` chain.

## Context

- Today `find_vault_root` walks up from CWD until it finds
  `artifacts.yaml` at project root (per v0.3.0 relocation,
  [[s0026-vault-marker-relocation]]).
- `core.load_settings(root)` reads `{root}/artifacts.yaml`
  directly.
- Both filenames are hard-coded.
- openstation needs to ship a host-branded config (one file,
  named after the host product) while still using artifacts-os
  schema, `Settings` base, `ViewsSettings.from_base`, etc.
- The collapse-into-`artifacts.yaml` approach was considered
  by openstation and rejected for ergonomics reasons (host
  ownership of the user-facing config name).

## Requirements

1. **Configurable marker filename** — `find_vault_root` accepts
   a `marker_filename` parameter (default `"artifacts.yaml"`)
   and walks up looking for that file. Also reads the env var
   `ARTIFACTS_MARKER_FILENAME` if set; explicit kwarg wins over
   env var.
2. **Settings loader honours the marker** — `core.load_settings`
   accepts the same `marker_filename` (or a fully-resolved
   `config_path`) and reads from that location. The schema
   parsed is unchanged; the file just lives under a different
   name.
3. **CLI passthrough** — `artifacts` CLI gains a `--config-file`
   flag (or `--marker <filename>`) that propagates to
   `find_vault_root` / `load_settings`. Also respects
   `ARTIFACTS_MARKER_FILENAME`.
4. **Backwards compatible** — if no kwarg, env var, or flag is
   set, behaviour is identical to today (look for
   `artifacts.yaml`). No existing vault breaks.
5. **One marker per process** — within a single CLI invocation
   or library session, the marker name is fixed at the entry
   call. Mixing markers within one process is out of scope.
6. **Doctor / init implications** — `artifacts init` accepts
   `--marker-filename` (or honours the env var) and writes the
   marker under the configured name. `artifacts doctor` reports
   the marker filename it discovered.
7. **No schema fork** — the file under any custom name must
   still parse as a `Settings`-shaped YAML with the same
   top-level keys (`layout_version`, `project`, `views`,
   `default_views`, `default_layouts`, plus host extensions
   via `from_base`). Custom marker name only changes the
   *file*, not the *schema*.
8. **Documented as the host extension point** — `docs/settings.md`
   gets a "Custom marker filename" section describing how a host
   like openstation registers its own marker name and what
   ownership it implies (host owns the file; artifacts-os reads
   it).

## Verification

- [ ] `find_vault_root(marker_filename="openstation.yaml")`
      finds an openstation.yaml at project root and ignores any
      artifacts.yaml at the same location.
- [ ] `ARTIFACTS_MARKER_FILENAME=openstation.yaml artifacts list`
      works on a vault with only `openstation.yaml`.
- [ ] `artifacts --config-file ./custom.yaml list` works.
- [ ] No-kwarg / no-env / no-flag invocation behaves identically
      to v0.5.0 (regression test added).
- [ ] `artifacts init --marker-filename openstation.yaml`
      bootstraps a vault whose marker file is `openstation.yaml`.
- [ ] `artifacts doctor` output includes the discovered marker
      filename.
- [ ] `docs/settings.md` "Custom marker filename" section lands.
- [ ] Smoke test from openstation side: openstation can boot
      against a single `openstation.yaml` at project root with
      both artifacts-os keys and openstation extensions present.
- [ ] No new dependency added.
- [ ] CHANGELOG entry under the next release describing the
      new primitive.

## Constraints

- **Schema unchanged.** Only the filename changes. If a host
  needs a different schema, that is a separate ask (and
  probably the wrong direction).
- **No artifacts-os runtime cost when feature unused.** The
  default path remains `artifacts.yaml`; the lookup logic is
  the same single `os.path.exists` per walk-up step.
- **No daemon / cache layer.** The marker is resolved per
  process entry; do not introduce process-wide caching unless
  it's already there.

## Open questions

1. API ergonomics: prefer `marker_filename` (just the basename)
   or `config_path` (absolute path)? The basename form composes
   cleanly with `find_vault_root`'s walk-up; the path form is
   more explicit but bypasses discovery. **Tentative answer:**
   support both — basename for the discovery flow, path for
   "I already know where it is" callers.
2. Should `artifacts.yaml` and `openstation.yaml` (or other
   custom names) be allowed to coexist at the same project
   root? Or is it an error? **Tentative answer:** allow
   coexistence, walk-up uses the configured marker only — no
   precedence rules between markers.
3. Should there be a registry of well-known host markers (the
   artifacts-os process knows about `openstation.yaml`,
   `artifacts.yaml`, etc.)? **Tentative answer:** no — the
   host tells artifacts-os its marker name at entry; no
   registry needed.

## Downstream consumer

- **openstation** — `s2068 § 3.3-rev3` (single-file
  `openstation.yaml`) and `s2068 § 5.5 W2b` (settings
  migration step) consume this primitive as a hard
  prerequisite. The openstation architect (working on t0464
  in the openstation vault) will revise the spec to describe
  the consumption side once this upstream API shape lands.
