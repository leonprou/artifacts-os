---
kind: task
id: t0155
name: publish-artifacts-os-as-its
type: implementation
status: ready
assignee: architect
owner: user
parent: "[[t0150-artbook-distribution-model]]"
created: 2026-05-15
---

# Publish Artifacts-Os As Its Own Artbook Distro (Artbook.Yaml At Repo Root)

## User story

> **As a** consumer of artifacts-os **I want** the artifacts-os repo
> itself to publish its agent defaults as an artbook distro **so that**
> I can point `artbook.distro_url` at it and pull working agents
> without anyone first having to spin up a separate distro repo.

## Why

[[s0029-artbook-mvp-distribution-model]] §3.1 Layout B describes the
"project repo doubling as its own distro" pattern: add one
`artbook.yaml` at the repo root, point its `path` at agents already
present in the tree, ship nothing else. This sub-task delivers that
file so the end-to-end MVP loop in [[t0150-artbook-distribution-model]]
has a real distro to pull from — independent of the consumer-side
work in t0152/t0153/t0154.

## Scope (intent — see spec for contract)

- Add **one** new file: `artbook.yaml` at the repo root.
- Conform to spec §3 schema: `version: 1`; required `distro.name`;
  one book entry with `type: agents` and a `path` pointing at this
  repo's canonical agent directory.
- Optionally include the `files:` allowlist (D18) to lock the
  exact set of agents shipped — architect's call.
- Validate the manifest parses with `yaml.safe_load` and survives
  the validation rules from spec §6.5 (no `..` segments, no
  absolute paths, no `/` in `files:` entries, etc.).

## Directional intent (architect's call)

- **Source path candidates** — pick one:
  - `artifacts/agents/` — canonical project vault per CLAUDE.md
    ("Store all project artifacts under `artifacts/`"); sits next
    to `artifacts.yaml`. 10 files (includes `qa.md`). My lean.
  - `openstation/agents/` — older OpenStation vault; what
    `.claude/agents/` ultimately resolves to via the symlink farm.
    10 files (includes `qa.md`).
- Per D8 / §7.2.1 the MVP explicitly does **not** solve
  replication — pick **one** canonical path, the others are out
  of the distro's view.
- If the parallel copies are not byte-identical, document which
  ones differ in the Findings — that informs the future sync
  spec.

## Out of scope

- **Dogfood migration** — removing the parallel agent copies in
  `.claude/agents/`, `.openstation/agents/`, and whichever of
  `openstation/agents/` or `artifacts/agents/` isn't picked.
  That's a separate spec (per [[s0029-artbook-mvp-distribution-model]]
  §1.3 and §9).
- Publishing the distro URL anywhere user-facing — the URL is just
  this repo's git remote; documenting it in `README.md` or
  `docs/` can land later when the consumer CLI exists (t0154).
- Adding more book types (`kinds`, `skills`, etc.) — MVP ships
  `agents` only.

## Verification

- [x] `artbook.yaml` exists at the repo root
- [x] `python -c "import yaml; print(yaml.safe_load(open('artbook.yaml')))"`
      parses without error
- [x] Manifest has `version: 1`, a `distro:` table with `name`, and
      a `books:` list with one entry of `type: agents`
- [x] The chosen `path` resolves to an existing directory in this
      repo and contains the agent files we intend to ship
- [x] If `files:` is set, every listed name exists under `path/`
      and contains no `/` — N/A; `files:` is intentionally omitted
      (directory-is-the-book mode per D18 / §3.2 minimal example).
- [x] Findings record the chosen path and any drift observed
      between parallel agent copies

## Findings

### Chosen source path

`artifacts/agents/` — the canonical project vault per CLAUDE.md
("Store all project artifacts under `artifacts/`"); sits next to
`artifacts.yaml`.

### Allowlist mode — omitted

`files:` is not set. The D20 walker (`*.md` minus `README.md` minus
dotfiles, non-recursive) picks up every agent in the directory. The
manifest stays minimal; agents added or renamed under
`artifacts/agents/` ship automatically without manifest churn.

The 10 agents shipped today (alphabetical):

1. `architect.md`
2. `author.md`
3. `developer.md`
4. `devrel.md`
5. `product-manager.md`
6. `project-manager.md`
7. `qa.md`
8. `researcher.md`
9. `security-engineer.md`
10. `technical-writer.md`

### Drift across parallel agent copies (informational, per task ask)

| Location | Files | Notes |
|---|---|---|
| `artifacts/agents/` (chosen) | 10 | Includes `qa.md`. |
| `openstation/agents/` | 10 | Byte-identical to `artifacts/agents/`. |
| `.openstation/agents/` | 9 | Missing `qa.md`. |
| `.claude/agents/` | 9 symlinks | Missing `qa.md`. 7 symlinks point at `openstation/agents/*`, 2 (`product-manager.md`, `security-engineer.md`) point at `artifacts/agents/*`. |

Diff verified with `diff -r artifacts/agents/ openstation/agents/`
(no output → byte-identical). The sole content drift is `qa.md`
existing in the two "full" copies but missing from `.openstation/`
and the symlink farm. This is replica lag, not editorial intent —
`openstation/agents/qa.md` exists and is byte-identical to
`artifacts/agents/qa.md`. Per D8 / §7.2.1 the MVP does **not**
solve replication; this drift is recorded here to inform the
future sync spec.

### `distro.name` choice

Picked `artifacts-os` (matches the repo / package name) over the
illustrative `artifacts-os-defaults` used in s0029 examples. The
`-defaults` suffix is appropriate when there are several distros
fanned out from one project (e.g. `artifacts-os-defaults`,
`artifacts-os-extras`); since this repo is *itself* the distro
under Layout B, the bare project name is clearer.

## References

- [[s0029-artbook-mvp-distribution-model]] §3 (manifest schema),
  §3.1 Layout B (dogfood pattern), §7.2.1 (replication scope cut)
- Parent: [[t0150-artbook-distribution-model]]
