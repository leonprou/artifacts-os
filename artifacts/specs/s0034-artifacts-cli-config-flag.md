---
kind: spec
id: s0034
name: artifacts-cli-config-flag
status: draft
task: "[[t0198-support-config-flag-on-cli]]"
created: 2026-06-01
agent: architect
---

# `artifacts --config <ref>` — Global CLI Settings Override

A global `--config <ref>` flag on the top-level `artifacts`
parser that overrides marker-discovery for the current
invocation. The flag accepts either an explicit path or a
basename, lets operators run any verb against any vault without
`cd`-ing, exporting env vars, or renaming the marker file, and
does **not** affect `artifacts init`.

Producing task: [[t0198-support-config-flag-on-cli]].
Companion to: [[t0197-support-custom-marker-filename-for]]
(core-side primitive — `find_vault_root(marker_filename=…)`).

## 1. Background and Cross-References

- **Direct papercut** — [[n0020-openstation-command-coverage-buckets]]
  notes that operators today have no way to override the
  vault-marker walk-up from the command line; they must `cd` into
  the vault or fork the CLI.
- **Host-extension surface** — [[r0001-openstation-integration-audit]]
  §3 documents the `from_base` chain that lets a host project name
  its config something other than `artifacts.yaml`. A CLI flag is
  the operator-facing complement: the architect / host can plumb
  settings from a known path without depending on CWD geometry.
- **Core primitive** — [[t0197-support-custom-marker-filename-for]]
  delivers the `find_vault_root(marker_filename=…)` and
  `load_settings(path)` semantics that this spec composes on top
  of. **t0197's Req #3 (CLI passthrough) is descoped to this
  task** — t0197 stays focused on the library-level primitive,
  this spec owns the CLI flag.
- **Vault discovery** — [[s0026-vault-marker-at-root]] §6.2 is the
  current `find_vault_root` algorithm; this spec adds a second
  call mode (explicit path) and a marker-name substitution but
  leaves the walk-up shape unchanged.
- **Settings model** — [[s0010-core-settings-module-spec]].
  `load_settings(path)` is path-agnostic today; no signature
  change is needed at the loader.
- **CLI architecture** — [[s0003-artifacts-os-cli-module]]. The
  flat-verb convention is honoured — `--config` is a top-level
  flag on `artifacts`, not a sub-verb, and it inherits down the
  command surface without per-subcommand re-declaration.

## 2. Goals

1. One flag, one place — `artifacts --config <ref> <verb> …` is
   the single operator-facing override. No precedence machinery,
   no env-var dual control.
2. Predictable disambiguation — given a `<ref>` string, the
   user can reason about whether it means "this path" or "walk
   up looking for this basename" without consulting state on
   disk.
3. Identical default behaviour — when `--config` is absent, the
   CLI walks up from CWD for `artifacts.yaml`, exactly as today.
4. Clean error reporting — bad `<ref>` exits non-zero with a
   message that names the value the user typed.
5. `init` carved out — `artifacts init` always writes
   `artifacts.yaml` at the target directory. `--config` is read-
   side only.

## 3. Non-Goals

- **No env-var override.** `--config` is the only knob this spec
  adds. If t0197 ships an env var
  (`ARTIFACTS_MARKER_FILENAME` / similar) it owns the
  precedence rule between flag and env in its own spec.
- **No write-side override.** `--config` does not affect `init`,
  any future `set` command's write path, or any other surface
  that writes the marker file.
- **No relative-path normalisation surprises.** The flag value is
  resolved with `Path(value).resolve()` (or its basename walk-up
  equivalent) and used as-is. No `~` expansion beyond what
  argparse already does; no `${…}` substitution.
- **No multi-vault selection.** `--config` resolves to exactly
  one settings file. Querying multiple vaults in one invocation
  is out of scope.
- **No prompt / interactive picker.** A missing or bad value is a
  hard error, not a fall-back to discovery.
- **No mid-process re-binding.** The settings path is fixed at
  argv parse time and held for the rest of the invocation.

## 4. Locked Decisions Summary

| ID  | Decision | Rationale (brief) |
|-----|----------|-------------------|
| D1  | Flag name: `--config <ref>`. No short form. | Single global flag; abbreviating to `-c` collides with a likely future `--count` / `--columns` / `--config-key` on subcommands. Long-form keeps the namespace open. |
| D2  | Position: **global, on the top-level parser**, parsed by a pre-parser before the subcommand parsers see argv. Accepts `artifacts --config <ref> <verb> …` and `artifacts <verb> --config <ref> …` symmetrically. | Mirrors `--version` / `-v` which already sit on the top-level parser. Symmetric position avoids "flag-must-come-before-verb" footguns that argparse otherwise enforces when a flag is registered only on the root. |
| D3  | Disambiguation rule: `<ref>` is a **path** iff it contains any path separator (`os.sep` or, on Windows, `/` or `\\`) **or** is absolute. Otherwise it is a **basename**. | Pure-syntactic. Result depends only on the string, not on filesystem state. `os.path.exists`-based discrimination was rejected (D5). |
| D4  | Path mode (`./x.yaml`, `/etc/x.yaml`): use the file directly, **no walk-up**. Vault root = the resolved file's parent directory. | Operator who typed a path means "this exact file". Walk-up from a path argument would be surprising. |
| D5  | Basename mode (`openstation.yaml`): walk up from CWD looking for that basename, identical algorithm to today's `find_vault_root` with the filename substituted. | Existing algorithm, parameterised. Composes cleanly with t0197's `find_vault_root(marker_filename=…)`. |
| D6  | Missing or unreadable path exits **2** with `error: --config: <value>: <reason>` on stderr. | Exit 2 already means "operator-level failure / not in a vault" in this CLI; same family. |
| D7  | `init` ignores `--config`. The flag is accepted by the parser (so `artifacts --config x.yaml init` does not error) but the value is dropped: `init` always writes `artifacts.yaml` at the target directory. | Task spec is explicit. Host-side custom markers (e.g. `openstation.yaml`) are written by the host's own init flow, not by `artifacts init`. |
| D8  | Implementation depends on t0197's `find_vault_root(start, marker_filename)`. If t0198 lands first, it ships the **minimal** parameter addition to `find_vault_root` (just the `marker_filename` kwarg, defaulting to `"artifacts.yaml"`) — that is the smallest core change needed and is already part of t0197's surface. | Avoids blocking t0198 on the broader t0197 work (env var, init flag, doctor). t0197 keeps the kwarg as part of its surface and adds the rest. |
| D9  | Plumbing: a single helper `_resolve_settings_path(argv, cwd) -> SettingsRef \| None` in `cli/__init__.py` is the source of truth. `_run` calls it once, before alias resolution. All existing `Path(root) / "artifacts.yaml"` constructions in `cli/__init__.py` consume the same `SettingsRef`. | One resolver, one error site, one place to test. |
| D10 | When `--config` is absent **and** there is no vault marker discoverable from CWD, the existing "not in an artifacts-os vault" error path is unchanged. | Regression-free for the default case. |

## 5. CLI Surface

### 5.1 Synopsis

```text
artifacts [--config <ref>] [--version] <verb> [<flags>…]

  --config <ref>    Override settings-file discovery for this
                    invocation. <ref> is either an explicit path
                    (relative or absolute) or a basename to look
                    up by walking parents of CWD. Has no effect
                    on `artifacts init`.
```

### 5.2 Worked invocations

```bash
# Explicit path — read settings from /etc/artifacts/foo.yaml,
# vault root is /etc/artifacts/.
artifacts --config /etc/artifacts/foo.yaml list

# Relative path — same semantics, resolved from CWD.
artifacts --config ./custom.yaml list

# Basename — walk up from CWD looking for "openstation.yaml".
# Vault root is the directory containing the discovered file.
artifacts --config openstation.yaml list

# Verb-first ordering also accepted.
artifacts list --config ./custom.yaml

# Missing path — exits 2, names the value.
$ artifacts --config ./missing.yaml list
error: --config: ./missing.yaml: file not found
$ echo $?
2

# Basename not found anywhere up the tree — also exits 2.
$ artifacts --config openstation.yaml list
error: --config: openstation.yaml: no file with that name found
       walking up from /current/cwd
$ echo $?
2

# init ignores the flag — writes ./artifacts.yaml regardless.
artifacts --config openstation.yaml init  # creates ./artifacts.yaml,
                                          # not ./openstation.yaml
```

### 5.3 Verb coverage

The flag applies uniformly to every verb that resolves the
settings file. The implementing task verifies this by writing
tests against (at minimum):

- **read-side** — `list`, `show`, `events`, `get`, `views`
- **write-side** — `create`, `set`, `status`
- **carved-out** — `init` (regression: the flag has no effect)

The verb coverage is verified by **one** parameterised test that
takes a verb name and asserts that the resolved `root` /
settings path are honoured. There is no per-verb wiring change
inside `cli/commands/*.py` — every verb already goes through
`_run`'s root resolution.

## 6. Resolution Algorithm

### 6.1 Disambiguation

```python
# cli/_config.py (new helper module — keeps cli/__init__.py thin)
def _classify_ref(ref: str) -> str:
    """Return "path" if *ref* looks like a path, "basename" otherwise.

    A ref is a path iff it is absolute or contains any path
    separator. Falls back to "basename" for bare filenames.
    """
    if os.path.isabs(ref):
        return "path"
    # `os.sep` covers the host OS native sep; `/` is treated as a
    # path separator on every supported platform (Python normalises
    # it on Windows).
    if os.sep in ref or "/" in ref:
        return "path"
    return "basename"
```

### 6.2 Resolver

```python
@dataclass(frozen=True)
class SettingsRef:
    root: Path           # the directory that plays the "vault root" role
    settings_path: Path  # the file load_settings() will read

def _resolve_settings_path(
    *,
    config_ref: str | None,
    cwd: Path,
) -> SettingsRef | None:
    """Apply --config disambiguation and return (root, path).

    Returns None when no settings file was found (e.g. no --config
    given and no marker walking up from cwd). The caller emits the
    "not in a vault" error.

    Raises ConfigRefError when --config was given but cannot be
    resolved. The caller catches and emits an exit-2 error.
    """
    if config_ref is None:
        # Default behaviour — unchanged.
        root = find_vault_root(start=cwd)
        if root is None:
            return None
        return SettingsRef(root=root, settings_path=root / "artifacts.yaml")

    mode = _classify_ref(config_ref)
    if mode == "path":
        path = Path(config_ref).expanduser().resolve()
        if not path.is_file():
            raise ConfigRefError(config_ref, "file not found")
        return SettingsRef(root=path.parent, settings_path=path)

    # mode == "basename"
    root = find_vault_root(start=cwd, marker_filename=config_ref)
    if root is None:
        raise ConfigRefError(
            config_ref,
            f"no file with that name found walking up from {cwd}",
        )
    return SettingsRef(root=root, settings_path=root / config_ref)


class ConfigRefError(ValueError):
    """Raised when `--config <ref>` cannot be resolved."""

    def __init__(self, ref: str, reason: str) -> None:
        self.ref = ref
        self.reason = reason
        super().__init__(f"--config: {ref}: {reason}")
```

### 6.3 Edge cases

| `<ref>` | Mode | Behaviour |
|---------|------|-----------|
| `./openstation.yaml` | path | resolve absolute; require `is_file()`; root = parent. |
| `/abs/path/x.yaml` | path | resolve absolute; require `is_file()`; root = parent. |
| `openstation.yaml` | basename | walk up from CWD for that filename. |
| `~/foo.yaml` | path (contains no sep, but `expanduser()` makes it absolute *after* classification — so this is actually **basename** by our rule and would walk up looking for a literal `~/foo.yaml`). | **Pick:** require operators to pre-expand: `./~/foo.yaml` or `$HOME/foo.yaml`. Tilde-leading bare names are too rare to special-case and the rule must stay syntactic. |
| `..` | path | (contains no sep on the surface but resolves to a directory). `is_file()` is `False` → exits 2, "file not found". |
| `""` (empty) | path (contains no sep, no abs) → basename mode would call `find_vault_root(marker_filename="")`. **Reject at argparse** with a `type=` hook that raises if `ref` is empty. | Exits 2 via argparse error path. |
| `config/foo.yaml` (no leading `./`) | path | contains `/`; resolved relative to CWD. |
| `\\share\\foo.yaml` (Windows UNC) | path | absolute; same code path. |

### 6.4 Walk-up semantics in basename mode

Identical to today's `find_vault_root` with the literal
substituted. Concretely, for `ref = "openstation.yaml"`:

```python
def find_vault_root(start, marker_filename="artifacts.yaml"):
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / marker_filename).is_file():
            return candidate
    return None
```

This is the **minimum** core-side change t0198 ships. t0197
specifies the broader surface (env var, init flag, doctor
output). The `marker_filename` kwarg signature is shared between
the two specs — they must agree on it. (See §10 Dependencies.)

### 6.5 Why not `os.path.exists` for disambiguation?

| Pick | Pro | Con |
|------|-----|-----|
| **Syntactic (this spec)** | Pure function of the string. Operator can predict the mode without knowing the filesystem state. | One pathological case (`~/foo.yaml`) — addressed in §6.3. |
| `os.path.exists` | Handles bare-filename-also-is-a-file case (rare). | Mode depends on filesystem state. Same flag value can mean different things in different working directories. Hard to test. Hard to document. |

**Pick:** syntactic. Documented behaviour is more valuable than
covering the rare ambiguous case.

## 7. argparse Plumbing

### 7.1 Pre-parser pass

`_run` currently does:

```python
def _run(argv: Sequence[str]) -> int:
    argv = list(argv)
    root = find_vault_root()                            # ← today
    cli_settings = _load_cli_settings(root) if root else None
    argv = _apply_aliases(argv, …)
    …
    parser = _build_parser(…)
    args = parser.parse_args(argv)
```

After this spec the prologue grows one step — a pre-parser that
extracts `--config <ref>` from argv before alias resolution and
before the subcommand peek-parsers (`_peek_create_kind_schema`,
`_peek_list_kind_schema`) need to know the root:

```python
def _run(argv: Sequence[str]) -> int:
    argv = list(argv)

    # Phase 0 — extract --config <ref> from argv.
    pre = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    pre.add_argument("--config", default=None)
    known, argv = pre.parse_known_args(argv)
    config_ref: str | None = known.config

    try:
        ref = _resolve_settings_path(
            config_ref=config_ref,
            cwd=Path.cwd(),
        )
    except ConfigRefError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    root: Path | None = ref.root if ref is not None else None
    settings_path: Path | None = ref.settings_path if ref is not None else None

    cli_settings = _load_cli_settings(settings_path) if ref else None
    …
    # Re-register --config on the *real* parser so `--help` shows it
    # and validation catches typos (`--confg`).  Same dest; value is
    # already consumed by the pre-parser, so we re-add it just for
    # help / error reporting.
    parser = _build_parser(...)
    parser.add_argument(
        "--config", default=None,
        metavar="<ref>",
        help="settings file path or basename (default: walk up for artifacts.yaml)",
    )
    args = parser.parse_args(argv)            # argv has --config stripped
    …
```

**Subtlety — pre-parser strips, real parser re-declares:** the
pre-parser consumes `--config <ref>` and removes both tokens
from argv. The real parser re-declares `--config` purely so that
`artifacts --help` documents it and so that `artifacts
--confgi` (a typo) gets a clear argparse error rather than being
silently passed through. Because the real parser receives argv
*without* `--config`, the re-declared flag never fires.

`allow_abbrev=False` on the pre-parser is required so that
`--config-key=x` (a hypothetical future flag) is not greedily
matched as `--config`.

### 7.2 Why not a single top-level parser declaration?

| Pick | Pro | Con |
|------|-----|-----|
| **Pre-parser (this spec)** | Symmetric — `--config` works both before and after the verb. `find_vault_root` and the kind-peek helpers can see the resolved root, which they need. | Two argparse passes. |
| Single declaration on top-level parser | Less code. | argparse enforces strict "global flags before subcommand" ordering. `artifacts list --config foo.yaml` would fail. Also: `find_vault_root` happens before `parser.parse_args` today, so the global flag would be read *after* the root is already resolved. Refactoring the order is more invasive than adding a pre-parser pass. |

**Pick:** pre-parser. Already an established pattern in `_run`
(see `_peek_create_kind_schema`, `_peek_list_kind_schema`).

### 7.3 `init` integration

`init` runs before vault setup (it has `_pre_registry=True`).
The pre-parser still strips `--config` from argv, but `init`'s
`run(args)` does not read `args.cli_settings` and does not call
`find_vault_root`. The settings path resolved in Phase 0 is
simply not consulted by `init`.

To make the carve-out explicit and prevent operator confusion,
the implementation **emits a one-line stderr note** when both
`--config` and `init` are present:

```
note: --config is ignored by `artifacts init`
      (init always writes artifacts.yaml at the target directory)
```

The note goes to stderr, exit code is unchanged from current
`init` behaviour. This is a courtesy, not an error.

## 8. Settings Path Plumbing in `cli/__init__.py`

The existing call sites that hardcode `Path(root) / "artifacts.yaml"`
must consume `settings_path` from the `SettingsRef` resolved in
Phase 0.

| File | Today | After |
|------|-------|-------|
| `cli/__init__.py:62` (`_load_views_settings`) | `settings_path = Path(root) / "artifacts.yaml"` | `settings_path = ref.settings_path` (passed in by `_run`). |
| `cli/__init__.py:78` (`_load_cli_settings`) | same | same. |
| `cli/__init__.py:268` (`_run`) | `root = find_vault_root()` | `ref = _resolve_settings_path(...)`; derive `root = ref.root`. |

Both `_load_*_settings` helpers gain a `settings_path: Path`
parameter and drop their `root` parameter. Their callers in
`_run` pass `ref.settings_path` directly.

`Registry(_registered_kinds, root=root)` is unchanged — it
consumes the directory, not the marker. `root = ref.root` keeps
the existing call site working.

## 9. Error Handling Contract

| Condition | Exit | stderr |
|-----------|------|--------|
| No `--config`, no `artifacts.yaml` walking up | 2 | `error: not in an artifacts-os vault (no artifacts.yaml found walking up from <cwd>).` *(unchanged from today)* |
| `--config /abs/x.yaml`, file does not exist | 2 | `error: --config: /abs/x.yaml: file not found` |
| `--config ./x.yaml`, file does not exist | 2 | `error: --config: ./x.yaml: file not found` |
| `--config ./x.yaml`, exists but is a directory | 2 | `error: --config: ./x.yaml: file not found` *(directory is not a file — same message; operator can `ls` to debug)* |
| `--config ./x.yaml`, exists but unreadable | 2 | `error: --config: ./x.yaml: <OSError message>` *(propagate the OS-level reason — permission denied, etc.)* |
| `--config openstation.yaml`, basename not found walking up | 2 | `error: --config: openstation.yaml: no file with that name found walking up from <cwd>` |
| `--config ""` (empty value) | 2 | `error: argument --config: expected non-empty value` *(argparse `type=` hook)* |
| Valid `--config`, loaded settings has bad YAML | 1 | `error: <YAML parser message>` *(existing path — unchanged)* |
| Valid `--config`, loaded settings has unsupported `layout_version` | 1 | `error: <UnsupportedSchemaVersion message>` *(existing path — unchanged)* |

The `--config:` prefix in every error string is the marker that
this came from the flag (vs. the default discovery path). The
flag value follows verbatim — the user can paste-match it
against the argv they typed.

## 10. Dependencies

### 10.1 t0197 — core primitive

This spec depends on `find_vault_root(start, marker_filename)`.
The contract (only the `marker_filename` kwarg, default
`"artifacts.yaml"`) is shared with t0197. Build sequence options:

| Order | Approach |
|-------|----------|
| **t0197 first** (preferred) | t0197 lands the kwarg in `find_vault_root` and the matching test cases. t0198 then consumes it without any core change. |
| **t0198 first** | t0198's implementing task ships **just** the kwarg addition to `find_vault_root` (the smallest sufficient core change). t0197 later adds env-var support, `init --marker-filename`, doctor reporting, etc. — none of which collide with the kwarg signature. |

Either order works because the kwarg signature is the same in
both specs. The implementing task picks based on which lands
first; the parent task t0198 explicitly notes this option in its
Direction section.

### 10.2 No other module-level dependencies

`load_settings` is path-agnostic today (s0010 §load_settings).
`ViewsSettings.from_base`, `CliSettings.from_base`,
`EventsSettings.from_base`, etc. all consume `Settings.raw`,
not a path — none of them change.

## 11. Tests

### 11.1 New test file

`tests/cli/test_config_flag.py` — covers the flag's behaviour
end-to-end through `_run`. The existing `make_vault` fixture
constructs a writable vault under `tmp_path`; the new tests
build on it.

| # | Test | Asserts |
|---|------|---------|
| 1 | `--config <abs-path>` resolves explicit path | `list` against a vault outside CWD succeeds. `root` is the file's parent. |
| 2 | `--config ./<rel-path>` resolves relative path | Same as 1, with `Path(value).resolve()` applied. |
| 3 | `--config <basename>` walks up | Walking from a deep CWD finds the file two parents up. |
| 4 | `--config <missing-path>` exits 2 | stderr contains `--config: <value>: file not found`. |
| 5 | `--config <missing-basename>` exits 2 | stderr contains `--config: <value>: no file with that name found walking up from`. |
| 6 | `--config ""` exits 2 | argparse error mentions `--config`. |
| 7 | Symmetric position | `artifacts --config x.yaml list` and `artifacts list --config x.yaml` produce identical output. |
| 8 | Verb coverage | Parameterised over `list`, `show`, `create`, `set`, `status`, `events`. Each verb honours the override. |
| 9 | `init` carve-out | `artifacts --config foo.yaml init <tmpdir>` writes `<tmpdir>/artifacts.yaml`, not `<tmpdir>/foo.yaml`. Note is printed to stderr. |
| 10 | Default behaviour unchanged | `artifacts list` (no flag) inside a vault still works. |
| 11 | Default + no vault | `artifacts list` (no flag, no marker) emits the existing "not in an artifacts-os vault" error and exits 2. |
| 12 | Custom-basename vault | A vault whose only marker is `openstation.yaml` at root works under `artifacts --config openstation.yaml list` and fails under bare `artifacts list` (regression for the carve-out). |

### 11.2 Existing test surface

No existing test is removed. Tests that already exercise
`find_vault_root` or `load_settings` continue to pass: their
default code path (no `--config`) is unchanged.

If t0198 lands the `marker_filename` kwarg addition to
`find_vault_root` (per §10.1 option 2), it also adds these
core-side tests:

- `tests/core/test_vault.py::test_find_vault_root_custom_marker` —
  walks up looking for `openstation.yaml`, finds it, returns the
  parent directory.
- `tests/core/test_vault.py::test_find_vault_root_default_unchanged` —
  with no kwarg, behaviour is identical to today (regression).

If t0197 has already landed those, this spec defers to them.

### 11.3 Fixture pattern

The implementing task adds a helper that materialises a vault
under a custom basename without forking the existing
`make_vault`:

```python
# tests/cli/conftest.py — new helper
def make_vault_with_marker(tmp_path, marker: str = "artifacts.yaml"):
    root = tmp_path / "vault"
    root.mkdir()
    (root / marker).write_text("layout_version: 1\nproject:\n  name: test\n")
    (root / "artifacts").mkdir()
    return root
```

Used by tests 3, 5, 9, 12. The existing `make_vault` factory is
unchanged.

## 12. Documentation Updates

### 12.1 `docs/settings.md`

Add a new section **"CLI override — `--config`"** before
"Extension Pattern":

```markdown
### CLI override — `--config`

`artifacts --config <ref>` overrides settings discovery for a
single invocation. `<ref>` is either a path
(`./custom.yaml`, `/etc/foo.yaml`) — used directly, no walk-up
— or a basename (`openstation.yaml`) — walked up from CWD like
the default `artifacts.yaml` marker.

The flag has no effect on `artifacts init`, which always writes
`artifacts.yaml` at the target directory. Custom-named markers
are owned by the host application (e.g. openstation's own init
flow writes `openstation.yaml`); `artifacts` only *reads* them.

See [s0034-artifacts-cli-config-flag](../openstation/specs/s0034-artifacts-cli-config-flag.md)
for the full contract.
```

### 12.2 `src/artifacts_os/cli/README.md`

Add `--config <ref>` to the top-level flag table; cross-link to
`docs/settings.md` for the full semantics.

### 12.3 No `CLAUDE.md` change

The release-changelog mapping does not need updating — `--config`
is a CLI feature and lands under the existing `CLI` category.

### 12.4 CHANGELOG entry

```
- CLI: `artifacts --config <ref>` overrides settings-file
  discovery for the current invocation. Accepts a path or a
  basename; does not affect `artifacts init`. See
  docs/settings.md § "CLI override".
```

## 13. Implementation Plan

One implementing task, one PR. Files touched:

1. **`src/artifacts_os/cli/_config.py`** *(new)* —
   `_classify_ref`, `SettingsRef`, `_resolve_settings_path`,
   `ConfigRefError`.
2. **`src/artifacts_os/cli/__init__.py`** — Phase 0 pre-parser,
   `_load_*_settings` signature change (`settings_path: Path`),
   re-declared `--config` on the real parser (for `--help`).
3. **`src/artifacts_os/core/vault.py`** — `find_vault_root` gains
   `marker_filename="artifacts.yaml"` kwarg.
   *Skip this step if t0197 has already landed it.*
4. **`src/artifacts_os/cli/commands/init.py`** — emit the
   `note: --config is ignored by artifacts init` stderr line
   when `args.config is not None`. No other change.
5. **`tests/cli/test_config_flag.py`** *(new)* — twelve cases
   per §11.1.
6. **`tests/cli/conftest.py`** — add `make_vault_with_marker`
   helper.
7. **`tests/core/test_vault.py`** — two new cases per §11.2.
   *Skip if t0197 has already landed them.*
8. **`docs/settings.md`** — new "CLI override" section
   (§12.1).
9. **`src/artifacts_os/cli/README.md`** — flag table entry
   (§12.2).
10. **`CHANGELOG.md`** — one-line entry (§12.4).

The implementing task is small enough to ship in a single PR —
no atomic-step ordering is required. The pre-parser pattern is
already established in `_run` (see `_peek_*` helpers), so the
implementing agent has a worked example to mirror.

## 14. Trade-offs

### 14.1 Flag name — `--config` vs `--config-file` vs `--marker`

| Pick | Pro | Con |
|------|-----|-----|
| **`--config` (this spec)** | Short, conventional (`git config`, `pip config`, `gh --config`, etc.). | Slightly overloaded — could later collide with a hypothetical `set config <key>=<value>` (but that would be a subcommand, not a top-level flag). |
| `--config-file` | Maximally explicit. | Verbose; nobody types it. |
| `--marker` / `--marker-filename` | Aligns with t0197's vocabulary ("custom marker filename"). | Internal jargon — `marker` is not how operators think about "the settings file". `--config` matches the operator mental model. |

**Pick:** `--config`. Aligns with the operator's mental model
("point me at a different config"); t0197's internal "marker"
vocabulary stays at the library / docs layer.

### 14.2 Re-declaring `--config` on the real parser

| Pick | Pro | Con |
|------|-----|-----|
| **Re-declare (this spec)** | `--help` shows the flag. Typos (`--confg`) get a clear argparse error. | Two declarations to keep in sync. |
| Pre-parser only | One declaration. | `--help` does not show the flag; typos are silently passed through to the verb's parser and rejected there with a less-clear error. |

**Pick:** re-declare. The cost is one duplicated line; the help
output and typo-safety win is large.

### 14.3 `init` — silent vs. noisy carve-out

| Pick | Pro | Con |
|------|-----|-----|
| **Stderr note (this spec)** | Operator who mixed `--config` with `init` is told it had no effect. Easy to grep for. | Adds output to a previously-quiet command. |
| Silent | `init` output stays unchanged. | Operator who typed `artifacts --config openstation.yaml init` may believe they have just initialised an openstation vault — silent failure of intent. |
| Hard error | Loud failure prevents intent mismatch. | Too strict — the flag is ignored, not invalid. Operators who scripted `artifacts --config x.yaml <any-verb>` would suddenly fail on `init`. |

**Pick:** stderr note. Intent mismatch is the dangerous case;
loud-by-default is the right ergonomics.

### 14.4 Exit code 2 vs new code

| Pick | Pro | Con |
|------|-----|-----|
| **Exit 2 (this spec)** | Already documented as "operator-level failure / not in a vault". `--config` failure is semantically the same family. | Less specific than a dedicated code. |
| New code (e.g. 5) | Programs can disambiguate `--config` failure from other operator errors. | Adds an exit-code allocation that callers must learn; no current consumer needs the disambiguation. |

**Pick:** 2. Same exit-code family as the existing
"not in a vault" path keeps the contract simple.

## 15. Out of Scope (Made Explicit)

1. **Env-var override.** `ARTIFACTS_CONFIG` /
   `ARTIFACTS_MARKER_FILENAME` are not introduced here. t0197
   owns the env-var question if/when it ships one.
2. **Per-key overrides.** No `--config-key foo.bar=value` flag.
   The settings file is the only source of truth for keyed
   config.
3. **`set --config` write-side.** Writes always target the
   discovered marker file. A future `artifacts set` could grow
   `--config` semantics, but that is its own spec.
4. **`doctor --config` reporting.** Doctor (if/when it lands) is
   a separate surface; cross-cutting reporting is t0197's
   concern.
5. **TUI passthrough.** This spec covers `artifacts` CLI only.
   The TUI is a downstream consumer (s0006) and can adopt the
   same flag in its own spec.
6. **Per-invocation log-path override.** The `--config` flag
   points at the settings file, not at the events log directory.
   Log-path overrides are out of scope.

## 16. Verification Mapping

The producing task ([[t0198-support-config-flag-on-cli]])'s
verification items map to this spec as follows:

| Task verification item | Spec section |
|-----------------------|--------------|
| Explicit path resolves a vault outside CWD | §5.2, §6.2, §11.1 #1 |
| Basename walks up | §5.2, §6.4, §11.1 #3 |
| Missing path exits non-zero with the value in the message | §9, §11.1 #4 |
| No-flag invocation behaves identically (regression) | §9, §11.1 #10 |
| Flag works the same across 3+ verbs (read + write) | §5.3, §11.1 #8 |
| `init` is unaffected (regression) | §5.3, §7.3, §11.1 #9 |
| `docs/settings.md` gains a "CLI override" section | §12.1 |
