---
created: 2026-06-14
id: n0025
kind: note
name: potential-bugs-artifacts-os-triage
---

# Potential bugs — artifacts-os triage backlog

Candidate defects surfaced on 2026-06-14 while validating t0208 and
filing t0209. "Potential" = observed but not yet filed as their own
task — confirm before promoting each to a bug/implementation task.

## Already filed / fixed (reference)

- **t0208** `create --body-file writes 0-byte files` — root-caused and
  fixed on `main` (commit d2eaae3: `_validate_schema` moved inside the
  cleanup try/except in `core/store.py`). Awaiting user verification;
  currently blocked by the type-enum issue below.
- **t0209** `type enum omits bug` — `artifacts/kinds/task/kind.json`
  `type.enum` lacks `bug`, so `type: bug` tasks can be neither created
  nor transitioned. Filed (status: backlog).

## Candidates (unfiled)

1. **`artifacts show` crashes on a malformed artifact** (high confidence)
   - `artifacts show product-manager --kind agent` raises an uncaught
     exception and dumps a Python traceback (YAML ScannerError on a
     block scalar in the frontmatter).
   - Inconsistent with `artifacts list`, which skips the same file
     gracefully with a `warning: skipping ...` line.
   - Expected: a clean single-line error naming the file and parse
     problem, non-zero exit, no traceback.

2. **`artifacts/agents/product-manager.md` has malformed frontmatter**
   (high confidence)
   - Block-scalar parse error (~line 7): "did not find expected comment
     or line break". The agent spec is invalid and invisible to tooling
     (skipped by `list`, crashes `show`). Frontmatter needs repair.

3. **Status transitions re-validate the whole record** (medium-high)
   - `artifacts status <ref> <new>` validates every frontmatter field,
     so a pre-existing invalid field unrelated to the transition (e.g.
     legacy `type: bug` on t0208) blocks an otherwise-valid status change
     with a confusing enum error.
   - This also let an agent (run r0214) silently rewrite `type` to escape
     validation instead of surfacing the real problem. Consider scoping
     validation to the field(s) being changed, or emitting an actionable
     error that names the offending field.

## Checked — NOT a bug

- `artifacts create` does return a non-zero exit (2) on schema validation
  failure; the earlier "exit 0" reading was a shell-pipe artifact.