---
assignee: developer
created: 2026-05-29
id: t0192
kind: task
name: make-show-editor-default-agent
owner: user
status: done
type: implementation
---

# Make Show.Editor Default Agent-Safe (Tty/Agent Guard)

# Make the `show.editor` default agent-safe (TTY/agent guard)

## User story

> **As an** operator who turns on `cli.defaults.show.editor` in `artifacts.yaml`, **I want** `artifacts show` to open my `$EDITOR` only when I'm working interactively, **so that** agents (and any non-interactive caller) invoking `show` still receive the artifact's content on stdout instead of being left launching an editor they can't drive.

## Why

`artifacts show` already supports an editor-by-default opt-in: when `cli.defaults.show.editor: true`, `show` skips the Rich/stdout render and runs `$EDITOR` on the file (`src/artifacts_os/cli/commands/show.py:64-75`). The opt-in itself is desirable — humans want `art show t0042` to drop them straight into their editor.

The problem is the opt-in is applied **unconditionally**. Agents call `show` to pull artifact text *into their context via stdout* — this is the core "CLI access to artifacts as data" contract captured in [[n0003-programmatic-cli-access]]. If a vault enables the editor default, an agent's `show` launches an interactive editor in a non-interactive shell: it hangs or returns nothing, and the agent gets no content. So today the existing feature is effectively unusable in any vault that also runs agents.

openstation already solved exactly this and we have parity drift ([[r0001-openstation-integration-audit]]): it applies settings-driven CLI defaults **only in human context**, guarding the whole defaults pass behind an agent-environment check (`openstation/cli.py:508` — `if not os.environ.get("CLAUDECODE"): _apply_cli_defaults(...)`). It also keeps editor-default out of the shipped baseline (opt-in via the `standard`/`full` init templates, never the `minimal` default). Agents get plain stdout; humans get the editor.

This task closes the gap so the *existing* `show.editor` opt-in becomes safe to enable, rather than a footgun.

## Directions

Intent, not contract. The opt-in mechanism already exists; this is about *when* it's allowed to fire.

- A configured `show.editor` default (and, by the same logic, any future editor-style default) should take effect for **interactive humans** and be suppressed for **non-interactive / agent** callers — the suppressed path falls back to today's stdout render.
- An **explicit** `-e`/`--editor` on the command line should still always work, in any context — the guard governs the *default*, not the explicit flag. Likewise an explicit `-j`/`--meta` keeps precedence.
- Prefer mirroring openstation's signal so the two tools behave the same way in a shared vault, rather than inventing a new detection scheme. The exact signal (agent env var vs. `isatty()` vs. both) is the implementer's call — see open questions.
- Note a latent inconsistency to resolve while you're in `show.py`: `_render_meta`'s docstring already claims editor mode is "TTY-gated," but the code performs no such check. Whatever guard lands should make the docstring true (or correct it).

## Open questions

1. **What signal defines "non-interactive"?** Agent env var (openstation uses `CLAUDECODE`), `sys.stdout.isatty()`/`sys.stdin.isatty()`, or a combination? Recommendation: mirror openstation's env-var guard so a shared vault behaves identically under both tools; add a TTY fallback if cheap. Settle at implementation time — no spec.
2. **Scope of the guard.** Apply it narrowly to the `show.editor` default only, or generally to *all* settings-driven CLI defaults (a single guarded "apply defaults" step, as openstation does)? The general form is more future-proof but is a broader behavioral contract.
3. **Where does the guard live?** Inside `show`'s default resolution, or at a central point where `cli_settings.defaults` are merged into parsed args? Affects whether future editor-style defaults inherit the protection for free.
4. **Shipped baseline.** Should artifacts-os ever ship `show.editor: true` by default (it does not today)? Recommendation: keep it opt-in only; this task does not change the shipped default, only makes enabling it safe.

## Sub-tasks

None. This is a narrow guard on an already-shipped default-application path, not new contract surface — no architect spec. The open questions are recommendations the implementer settles inline; if the guard turns out to need a broader "apply all defaults" redesign (open question 2), split that out rather than expanding scope here.

## Verification

- With `cli.defaults.show.editor: true` set in `artifacts.yaml`, running `artifacts show <ref>` from an interactive terminal opens the file in `$EDITOR`.
- The same `artifacts show <ref>`, with the same setting, invoked in an agent / non-interactive context prints the artifact (Rich table + body) to stdout and does **not** launch an editor.
- An explicit `artifacts show <ref> -e` opens `$EDITOR` in any context, including the non-interactive one.
- An explicit `artifacts show <ref> -j` / `--meta` produces JSON / frontmatter output regardless of the `show.editor` default.
- An agent can run `artifacts show <ref>` against an editor-default-enabled vault and successfully read the artifact body from captured stdout.