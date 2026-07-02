---
assignee: architect
created: 2026-06-14
id: t0212
kind: task
name: spec-runtime-show-editor-default
owner: project-manager
parent: '[[t0211-make-show-editor-the-built]]'
status: cancelled
type: spec
---

# Spec: runtime-level default for `artifacts show` editor mode

## Goal

Design the runtime contract that makes `artifacts show <ref>` open
in an editor by default, without requiring any `artifacts.yaml`
configuration. Parent: [[t0211-make-show-editor-the-built]].

## Questions to answer

1. **Precedence ladder.** Concrete order between:
   - explicit `-e` / `-j` flags on the invocation,
   - `cli.defaults.show.editor` in `artifacts.yaml` (true / false / absent),
   - the new built-in runtime default (`true`),
   - the non-TTY guard from t0192.
   Spell out every combination that produces editor vs. text vs. JSON.
2. **Opt-out flag.** Is `--no-editor` introduced? `--text`? Reuse
   an existing flag? Pick one and justify against the CLI conventions
   in `CLAUDE.md` (flat verbs, top-level filter flags).
3. **Config interaction.** What happens when an existing vault has
   `cli.defaults.show.editor: false` explicitly set? Must still be
   honoured. What about `true`? (Now redundant but harmless.)
4. **Template implications.** Confirm no `cli:` block is added to
   `minimal.yaml` / `standard.yaml`. Also confirm whether
   `docs/settings.md` examples need updating to drop the
   editor-default snippet (or annotate it as redundant).
5. **Test surface.** Enumerate the test matrix needed:
   - TTY × no-config → editor
   - TTY × config-false → text
   - non-TTY × no-config → text (t0192 guard)
   - `-j` × anything → JSON
   - explicit `--no-editor` × anything → text
6. **Migration / backward compatibility.** Any user-visible breakage
   for existing vaults that don't set the config? Flag it explicitly.

## Reference material

- t0192 — non-TTY/agent guard for `show -e`.
- t0201 — cancelled; shipped the same default via init templates.
- `src/artifacts_os/cli/README.md` § Project Configuration.
- `docs/settings.md` — current documented precedence.
- Canonical `artifacts.yaml` in this repo (lines 146–151).

## Deliverable

A spec artifact (`s{NNNN}-…`) under `artifacts/specs/` containing:

- Precedence table (covers every combination above).
- Chosen opt-out flag, with rationale.
- Implementation outline: which module(s) own the default, where the
  resolution happens, how t0192's guard plugs in.
- Test matrix for the developer task.
- Docs delta list (READMEs, `docs/settings.md`).

Once approved, the parent task t0211 gets its verification checklist
rewritten from the spec and moves `backlog` → `ready`.

## Verification

- [ ] Spec artifact created and linked from t0211.
- [ ] Precedence table covers all flag × config × TTY combinations.
- [ ] Opt-out flag chosen and justified.
- [ ] Test matrix enumerated.
- [ ] Docs delta listed.
- [ ] Reviewed and approved by project-manager.