---
kind: task
id: t0146
name: research-harness-footprints-and-current
type: research
status: ready
assignee: researcher
owner: user
parent: "[[t0144-distributable-opinionated-harness-for-artifacts]]"
created: 2026-05-14
---

# Research Harness Footprints And Current File Classification

## Goal

Close the M7 unknowns in the parent feature task so the architect
spec can finalize per-harness manifests and migration plan without
guessing.

## Questions to answer

1. **Per-harness footprint.** For each of Claude Code, OpenStation,
   and OpenCode: which subdirectories under their config root does
   the tool actually read? Which file formats? Does each accept
   symlinks? What is the minimal viable layout vs. the optional
   extras?
2. **Per-file classification of today's state.** For every file
   currently under `.claude/`, `.openstation/`, `.opencode/`, and
   `artifacts/{agents,kinds}/` in this repo, classify it as one of:
   - **Managed** — should be regenerated from the canonical source
     in `src/artifacts_os/templates/`.
   - **Project-specific** — content unique to this repo that must
     move to the override layer to survive migration (e.g. the
     `qa.md` agent that exists only in dogfood).
   - **Runtime data** — never touched by sync (`state.db*`,
     `events/*.jsonl`, etc.).
3. **Drift inventory.** Where do the parallel copies disagree today?
   - `.claude/` vs. `.openstation/` agents/skills/commands
   - `artifacts/agents/` vs. `src/.../templates/agents/`
   - `artifacts/kinds/` vs. `src/.../templates/kinds/`
   Enumerate the deltas so the migration plan can resolve each
   intentionally (which copy wins, or both kept via override).
4. **Slash-command portability.** Are the command formats consumed
   by Claude Code, OpenStation, and OpenCode close enough that one
   canonical recipe can be rendered to all three? Or are they
   incompatible enough that we need per-harness command files?
5. **Schema-extension precedents.** Survey how other tools handle
   schema extension without forking (JSON Schema `allOf`, OpenAPI
   `$ref` overlays, etc.). Recommend a direction for the spec to
   adopt; no decision required from research, but the trade-off
   table is.
6. **`.opencode/` actual usage.** Is OpenCode actively used against
   this repo, or is the directory residue? Recommendation: keep, or
   drop from v1 scope.

## Deliverable

A research artifact under `artifacts/research/` (numbered,
conventional format) containing:

- One section per question with the answer, supporting evidence
  (commands run, files inspected, docs cited), and any caveats.
- A consolidated **per-file classification table** spanning every
  file currently under `.claude/`, `.openstation/`, `.opencode/`,
  and `artifacts/{agents,kinds}/`.
- A short **recommendations** section flagging anything that should
  influence the architect spec's decisions.

## Verification

- [ ] All six questions answered with evidence, not opinion.
- [ ] Per-file classification table covers every file in scope; no
      unclassified rows.
- [ ] Recommendations section identifies any architectural
      questions the spec must explicitly resolve.
- [ ] Research artifact reviewed by architect; spec sub-task can
      proceed.

## Notes

This research is the blocking dependency for finishing the
architect spec. Draft spec work can run in parallel, but spec
verification (and parent feature promotion to `ready`) gates on
this research being complete.
