---
kind: note
id: n0011
name: distributable-harness-layers-inventory
status: active
task: "[[t0144-distributable-opinionated-harness-for-artifacts]]"
created: 2026-05-14
---

# Distributable Harness — Layers Inventory

## Purpose

Reference inventory of the tools/artifacts that the distributable
opinionated harness ([[t0144-distributable-opinionated-harness-for-artifacts]])
will merge into a single managed surface. Each item is annotated with
its inclusion priority and current location.

Legend:

- ✅ **Core** — included in v1 of the distribution
- 🔧 **Optional** — included via opt-in manifest flag
- ⏭ **Deferred** — v2 or later

---

## Layer 1 — Vault primitives (what artifacts *are*)

| Item | Today's location | Call |
|---|---|---|
| Kind definitions (`kind.json`) | `src/artifacts_os/templates/kinds/<name>/` | ✅ |
| `ARTIFACT.md` per kind (AI-facing contract) | same | ✅ |
| Body templates for new artifacts (`body.md.tmpl`) | not yet shipped | ✅ |
| Frontmatter JSON schemas | embedded in `kind.json` | ✅ |
| Status lifecycles | inside `kind.json :: statuses` | ✅ |
| Example artifacts (exemplars) | not yet shipped | 🔧 |

## Layer 2 — Roles & process (who works with artifacts)

| Item | Today's location | Call |
|---|---|---|
| Agent definitions | `.claude/agents/`, `.openstation/agents/`, `artifacts/agents/`, `src/.../templates/agents/` (duplicated) | ✅ |
| Skills | `.claude/skills/`, `.openstation/skills/` (duplicated) | ✅ |
| Slash commands | `.claude/commands/`, `.openstation/commands/` (per-harness) | 🔧 |

## Layer 3 — Configuration (project-level conventions)

| Item | Today's location | Call |
|---|---|---|
| `artifacts.yaml` baseline | repo root | ✅ |
| Settings tiers (minimal / standard / full) | `src/.../templates/settings/` | ✅ |
| View definitions | inside `artifacts.yaml :: views` | ✅ |
| Default views per kind | `artifacts.yaml :: default_views` | ✅ |
| CLI aliases | `artifacts.yaml :: cli.aliases` | ✅ |
| Column / status styling per kind (`KindDef.meta`) | caller-owned today | 🔧 |
| AI context contract (`CLAUDE.md` / `AGENTS.md`) | repo root | ✅ |

## Layer 4 — Tooling & automation (what runs on artifacts)

| Item | Today's location | Call |
|---|---|---|
| Declarative hooks (`hooks.yaml`) | hooks module shipped; consumer config TBD | ✅ |
| Sync drift CI check (`artifacts sync --check`) | doesn't exist yet | ✅ |
| Hook recipes / bundles | not yet shipped | 🔧 |
| Pre-commit config fragment | not yet shipped | 🔧 |
| GitHub Actions workflow templates | not yet shipped | 🔧 |
| Release tooling (changelog skill + path mapping) | skill in `.claude/skills/`; mapping in `CLAUDE.md` | 🔧 |

## Layer 5 — Harness wiring (how AI tools find the above)

| Item | Today's location | Call |
|---|---|---|
| `.claude/` tree layout (agents, skills, commands, settings.json) | `.claude/` | ✅ |
| `.openstation/` tree layout | `.openstation/` | ✅ |
| Per-harness manifest (mapping catalogue → on-disk tree) | implicit today | ✅ |
| `.opencode/` tree layout | `.opencode/` | 🔧 |
| Harness-specific settings (`settings.json`, MCP defs) | `.claude/settings.json` | 🔧 |
| Runtime data (`state.db*`, `events/*.jsonl`, `logs/`) | `.openstation/state.db`, `.openstation/events/` | ⛔ excluded |

## Layer 6 — Docs (onboarding consumers)

| Item | Today's location | Call |
|---|---|---|
| Onboarding `USAGE.md` for consumers | not yet shipped | ✅ |
| Per-kind authoring guide (`AUTHORING.md`) | partial in `docs/adding-a-kind.md` | 🔧 |
| Example vault (`samples/`) | not yet shipped | 🔧 |

---

## Cross-cutting patterns (apply to every layer)

These four mechanisms recur across the inventory and form the actual
API surface of the distribution; everything else is content.

1. **Managed-file header marker** — every file sync writes carries a
   stamp (e.g. `<!-- managed-by: artifacts-os@<version> -->`). Sync
   refuses to overwrite anything missing it.
2. **Override directory** (`.artifacts-os/overrides/`) — mirrors the
   template tree; presence here replaces the bundled file.
3. **Manifest opt-in by name** — consumer picks subsets (`kinds: [...]`,
   `agents: [...]`, `hooks: [...]`, `harnesses: [...]`). No item is
   mandatory.
4. **Per-file-type merge semantics** — markdown is full-replace,
   YAML/JSON is deep-merge. Declared per file type, not per item.

---

## Items explicitly out of scope (never distributed)

- Project-specific artifacts (this repo's `artifacts/tasks/`,
  `artifacts/specs/`, `artifacts/notes/`) — consumer-owned work.
- Runtime data (`state.db*`, `events/*.jsonl`, `logs/`) — never
  touched by sync.
- IDE configs (`.vscode/`, `.idea/`), linter configs, LICENSE,
  `pyproject.toml`, devcontainer setup — out of artifacts-os's domain.

---

## References

- Parent feature: [[t0144-distributable-opinionated-harness-for-artifacts]]
- Architect spec sub-task: [[t0145-spec-the-distributable-harness-model]]
- Research sub-task: [[t0146-research-harness-footprints-and-current]]
