---
assignee: developer
created: 2026-06-14
id: t0210
kind: task
name: artifacts-show-crashes-with-yaml
owner: user
status: done
type: implementation
---

# `artifacts show` crashes with a YAML traceback on malformed frontmatter

Filed as `type: implementation` because the `type` enum currently rejects
`bug` (see t0209).

## Repro

```bash
artifacts show product-manager --kind agent
# Traceback (most recent call last):
#   ...
# yaml.scanner.ScannerError: while scanning a block scalar
#   in "<unicode string>", line 7, column 14
# did not find expected comment or line break
```

The same vault state is handled gracefully by `list`:

```bash
artifacts list --kind agent
# (prints all other agents)
# warning: skipping artifacts/agents/product-manager.md (invalid frontmatter)
# exit 0
```

Trigger file: `artifacts/agents/product-manager.md` line 7 —
`description: >- Product manager — ...` is an invalid block scalar
(content on the same line as a `>-` header is rejected by PyYAML).
The malformed file itself is a separate issue (see n0025 candidate #2);
this task is about the **`show` failure mode**, not the fixture.

## Root cause

The call paths are asymmetric:

1. `cli/commands/list.py` calls `core.list_artifacts(...)`, which catches
   per-file parse errors and downgrades them to a one-line
   `warning: skipping <path>` so iteration continues.
2. `cli/commands/show.py:71` calls `core.get(registry, ref, kind=...)`,
   which loads and parses a single file. There is no wrapper that
   normalizes parse errors — `yaml.YAMLError` propagates raw.
3. The CLI exception cascade in `src/artifacts_os/cli/__init__.py`
   `_run()` (lines ~369–383) handles only `NotFoundError`,
   `AmbiguousError`, `ValidationError`, `BlockedByPreHook`, and
   `ValueError`. `yaml.YAMLError` is NOT a subclass of `ValueError`,
   so it escapes the cascade and Python's default unhandled-exception
   handler prints the full traceback.

The bug is not in PyYAML or in the fixture — it is the absence of a
single-file boundary that normalizes parse failures into the same
shape `list` already uses.

## Requirements

- Loading a single artifact whose frontmatter fails to parse must
  surface as a `ValidationError` (or a dedicated parse-error subclass)
  carrying the **file path** and the **parse message**, NOT a raw
  `yaml.YAMLError`.
- `artifacts show <ref>` against such a file must exit non-zero with a
  single-line stderr message in the same style as other CLI errors —
  no traceback under any invocation (interactive, `--json`, `-e`, or
  `CLAUDECODE=1`).
- The new behaviour must NOT regress `list`'s skip-with-warning policy.
- The error message must include the artifact's path; it should not
  leak Python frames or internal scanner offsets beyond the
  line/column reported by PyYAML.

## Suggested implementation shape

Decision is the implementer's — these are starting points, not
mandates:

- Wrap the YAML parse step in the single-file load path (likely in
  `core.store` / `core.frontmatter`, wherever `get()` reads
  frontmatter) so `yaml.YAMLError` re-raises as
  `ValidationError(f"{path}: {parse_msg}")`.
- Alternative: add `yaml.YAMLError` to the `_run()` cascade in
  `cli/__init__.py` mapping to exit 2. Acceptable as defence-in-depth,
  but not a substitute for normalizing at the core boundary (other
  callers — TUI, AI, future embedders — also need the normalized
  error type).
- Audit other single-file core entrypoints (`status`, `set`, `get_prop`,
  `parent`, `transitions_for`, anything that resolves one ref) for the
  same omission and apply the same wrapping.

## Verification

- [ ] Add a fixture with malformed frontmatter (block-scalar style;
      the existing `product-manager.md` line 7 pattern is fine).
- [ ] `artifacts show <ref>` on that fixture exits 2, prints exactly
      one stderr line of the form
      `error: <path>: <parse message>`, and emits no traceback.
- [ ] Same assertion under `CLAUDECODE=1` and with `--json` / `-e`.
- [ ] `artifacts list --kind <kind>` still emits the existing
      `warning: skipping ...` line and exits 0 against the same fixture.
- [ ] Repro on `artifacts/agents/product-manager.md` is clean (no
      traceback) — this confirms the end-to-end fix without depending
      on fixing the agent file itself.
- [ ] Unit test: calling `core.get(registry, <bad-ref>)` raises
      `ValidationError` (NOT `yaml.YAMLError`) with the path in the
      message.

## References

- Triage note: `n0025-potential-bugs-artifacts-os-triage.md` candidate #1.
- Related (separate task): malformed `product-manager.md` frontmatter
  (n0025 candidate #2).
- Related (separate task): t0209 — `type` enum omits `bug`.