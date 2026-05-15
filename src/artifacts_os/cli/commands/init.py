"""cli init command — bootstrap a new artifacts-os project."""

import json
import os
import sys
import tempfile
from importlib.resources import files
from pathlib import Path

# ─── Template loader ───────────────────────────────────────────────────────


def _template_root():
    return files("artifacts_os.templates")


def _load_settings_template(tier: str) -> str:
    try:
        return (
            _template_root()
            .joinpath("settings", f"{tier}.yaml")
            .read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise FileNotFoundError(
            f"template not found: artifacts_os/templates/settings/{tier}.yaml\n"
            "       (this is a bug — please file an issue)"
        ) from exc


def _load_kind_schema(name: str) -> str:
    return (
        _template_root()
        .joinpath("kinds", name, "kind.json")
        .read_text(encoding="utf-8")
    )


def _load_kind_artifact(name: str) -> str:
    return (
        _template_root()
        .joinpath("kinds", name, "ARTIFACT.md")
        .read_text(encoding="utf-8")
    )


def _load_agent_template(name: str) -> str:
    return (
        _template_root()
        .joinpath("agents", f"{name}.md")
        .read_text(encoding="utf-8")
    )


def _discover_kinds() -> list[str]:
    return sorted(
        p.name
        for p in _template_root().joinpath("kinds").iterdir()
        if p.is_dir() and p.joinpath("kind.json").is_file()
    )


def _discover_agents() -> list[str]:
    return sorted(
        p.name.removesuffix(".md")
        for p in _template_root().joinpath("agents").iterdir()
        if p.is_file() and p.name.endswith(".md")
    )


# ─── Variable interpolation ────────────────────────────────────────────────


def _get_project_name(directory: Path) -> str:
    """Extract project name from CLAUDE.md H1 or fall back to dir name."""
    claude_md = directory / "CLAUDE.md"
    if claude_md.is_file():
        try:
            for line in claude_md.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    name = line[2:].strip()
                    if name and name not in ("Open Station", "Artifacts OS"):
                        return name
        except OSError:
            pass
    return directory.name


def _derive_project_alias(project_name: str) -> str:
    """Derive a short alias: lowercase first whitespace-word, alphanumeric only, max 8 chars."""
    parts = project_name.split()
    first_word = parts[0] if parts else project_name
    alias = "".join(c for c in first_word.lower() if c.isalnum())
    return alias[:8]


def _interpolate(
    content: str,
    project_name: str,
    project_alias: str,
    today_iso: str,
) -> str:
    content = content.replace("{{project_name}}", project_name)
    content = content.replace("{{project_alias}}", project_alias)
    content = content.replace("{{created}}", today_iso)
    return content


# ─── Multi-select input ────────────────────────────────────────────────────


def _parse_selection(
    raw: str, options: list[str], defaults: list[str]
) -> list[str] | None:
    """Parse a multi-select input.  Returns selection or None on validation error."""
    raw = raw.strip()
    if raw == "":
        return list(defaults)
    if raw == "*":
        return list(options)
    if raw == "-":
        return []

    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    selected: list[str] = []
    seen: set[str] = set()
    errors: list[str] = []

    for token in tokens:
        if token.isdigit():
            idx = int(token)
            if 1 <= idx <= len(options):
                item = options[idx - 1]
                if item not in seen:
                    selected.append(item)
                    seen.add(item)
            else:
                errors.append(
                    f"  error: '{token}' is out of range; pick from 1..{len(options)}"
                )
        elif token in options:
            if token not in seen:
                selected.append(token)
                seen.add(token)
        else:
            errors.append(f"  error: '{token}' is not a valid choice")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return None

    return selected


def _prompt_single_step(
    label: str,
    options: list[str],
    descriptions: dict[str, str],
    default_idx: int,
) -> str:
    """Prompt for a single-choice selection (Step 1)."""
    print(f"{label}:")
    for i, name in enumerate(options, 1):
        desc = descriptions.get(name, "")
        print(f"  {i}) {name:<12} — {desc}")
    print()

    default_name = options[default_idx - 1]

    for _ in range(3):
        try:
            raw = input(f"Choice [{default_idx}]: ").strip()
        except EOFError:
            print()
            return default_name
        except KeyboardInterrupt:
            print()
            sys.exit(130)

        if raw == "":
            return default_name
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
            print(
                f"  error: '{raw}' is out of range; pick from 1..{len(options)}",
                file=sys.stderr,
            )
        elif raw in options:
            return raw
        else:
            print(
                f"  error: invalid choice '{raw}'; enter a number (1–{len(options)}) or name",
                file=sys.stderr,
            )

    print(f"  Defaulting to {default_name}.", file=sys.stderr)
    return default_name


def _prompt_multi_step(
    label: str, options: list[str], defaults: list[str]
) -> list[str]:
    """Prompt for a multi-select (Step 2 or 3)."""
    if defaults:
        defaults_display = ",".join(
            str(options.index(d) + 1) for d in defaults if d in options
        )
    else:
        defaults_display = "-"

    print(f"{label} — comma-separated numbers, '*' for all, '-' for none:")
    for i, name in enumerate(options, 1):
        marker = "  [default]" if name in defaults else ""
        print(f"  {i}) {name}{marker}")
    print()

    for _ in range(3):
        try:
            raw = input(f"Choice [{defaults_display}]: ").strip()
        except EOFError:
            print()
            return list(defaults)
        except KeyboardInterrupt:
            print()
            sys.exit(130)

        result = _parse_selection(raw, options, defaults)
        if result is not None:
            return result

    print(f"  Defaulting to [{defaults_display}].", file=sys.stderr)
    return list(defaults)


# ─── Output helpers ────────────────────────────────────────────────────────


def _print_write(rel: str, dry_run: bool, overwritten: bool) -> None:
    prefix = "[would] " if dry_run else ""
    suffix = " (overwritten)" if overwritten else ""
    print(f"  {prefix}✓ {rel}{suffix}")


def _print_skip(rel: str) -> None:
    print(f"  ⊘ {rel} (exists, skipped — use --force to overwrite)")


def _print_fail(rel: str, reason: str) -> None:
    print(f"  ✗ {rel}: {reason}", file=sys.stderr)


# ─── Distro step ───────────────────────────────────────────────────────────


def _distro_item_names(entries: list, recurse: bool) -> list[str]:
    """Return canonical item names from *entries* for display and selection.

    Flat / allowlist books → stems.  Recurse books → unit folder names.
    Preserves encounter order and deduplicates.
    """
    seen: dict[str, None] = {}
    for _abs, rel in entries:
        if recurse:
            key = rel.parts[0] if rel.parts else ""
        else:
            key = rel.stem
        if key:
            seen[key] = None
    return list(seen)


def _run_distro_step(
    distro_url: str,
    books_flag: str | None,
    target: Path,
    *,
    yes: bool,
    dry_run: bool,
    is_tty: bool,
) -> bool:
    """Execute Step 4: clone the distro and pull selected books.

    Returns True if any error occurred (clone failure or per-book failure).
    The vault files (artifacts.yaml, kinds, agents) have already been written
    by the time this function is called (req 7).
    """
    import artifacts_os.artbook as artbook
    from artifacts_os.artbook import FetchError, ManifestError
    from artifacts_os.artbook.errors import ArtbookError
    from artifacts_os.artbook.placement import (
        _select_files,
        destination_for,
        filter_entries_by_items,
    )

    print()

    # Req 12: dry-run — report intended action without cloning or writing.
    if dry_run:
        flag_info = f" (books: {books_flag})" if books_flag else " (all books)"
        print(f"  [would] pull from distro: {distro_url}{flag_info}")
        return False

    print("Fetching distro manifest…")
    try:
        with tempfile.TemporaryDirectory(prefix="artbook-init-") as td:
            clone_root = Path(td) / "clone"
            try:
                manifest, _ = artbook.read_manifest(distro_url, clone_into=clone_root)
            except FetchError as exc:
                print(
                    f"error: git clone failed (exit {exc.returncode}): "
                    f"{exc.stderr.strip()}",
                    file=sys.stderr,
                )
                return True
            except ManifestError as exc:
                print(f"error: distro manifest invalid: {exc}", file=sys.stderr)
                return True

            all_book_names = [b.name for b in manifest.books]

            # ── Determine which books to pull ─────────────────────────
            if books_flag is not None:
                # --books flag supplied — skip book-selection prompt (req 2)
                lower_flag = books_flag.strip().lower()
                if lower_flag == "all":
                    selected_book_names = list(all_book_names)
                else:
                    tokens = [t.strip() for t in books_flag.split(",") if t.strip()]
                    invalid = [t for t in tokens if t not in all_book_names]
                    if invalid:
                        avail = ", ".join(all_book_names)
                        print(
                            f"error: unknown book(s) in --books: {', '.join(invalid)}; "
                            f"available: {avail}",
                            file=sys.stderr,
                        )
                        return True
                    selected_book_names = tokens
            elif yes:
                # Req 4: -y + distro → all books, all items
                selected_book_names = list(all_book_names)
            else:
                # Interactive book selection (req 3)
                print()
                print("Available books:")
                for b in manifest.books:
                    desc = f" — {b.description}" if b.description else ""
                    print(f"  {b.name:<20} → {b.dest}{desc}")
                selected_book_names = _prompt_multi_step(
                    "Step 4 of 4: Distro books",
                    all_book_names,
                    all_book_names,
                )

            if not selected_book_names:
                print("  No books selected — skipping distro pull.")
                return False

            # ── Pull each selected book ───────────────────────────────
            had_error = False
            for book_name in selected_book_names:
                book = next(b for b in manifest.books if b.name == book_name)
                src_dir = clone_root / book.src

                try:
                    all_entries = _select_files(src_dir, book)
                except (ManifestError, ArtbookError) as exc:
                    print(
                        f"  error: book '{book_name}': {exc}", file=sys.stderr
                    )
                    had_error = True
                    continue

                preselected = None
                if not yes and is_tty:
                    # Interactive item selection (req 3 — per-book item subset)
                    item_names = _distro_item_names(all_entries, book.recurse)
                    if item_names:
                        print()
                        print(f"  Book '{book_name}' items:")
                        for item in item_names:
                            print(f"    • {item}")
                        selected_items = _prompt_multi_step(
                            f"  Items from '{book_name}'",
                            item_names,
                            item_names,
                        )
                        if set(selected_items) != set(item_names):
                            filtered, _unmatched, _ = filter_entries_by_items(
                                all_entries,
                                selected_items,
                                recurse=book.recurse,
                            )
                            preselected = filtered

                try:
                    report = artbook.pull_book(
                        book,
                        clone_root,
                        target,
                        distro_url=distro_url,
                        distro_sha="",
                        preselected=preselected,
                    )
                    n = len(report.written)
                    print(
                        f"  ✓ {book_name}: {n} file{'s' if n != 1 else ''} written"
                    )
                except (ManifestError, ArtbookError) as exc:
                    # Req 11: continue with remaining books on per-book failure
                    print(
                        f"  error: book '{book_name}': {exc}", file=sys.stderr
                    )
                    had_error = True

            return had_error

    except Exception as exc:  # noqa: BLE001
        print(f"error: distro step failed unexpectedly: {exc}", file=sys.stderr)
        return True


# ─── Flag validation ───────────────────────────────────────────────────────


def _parse_csv_flag(
    raw: str, valid_options: list[str], flag_name: str
) -> list[str] | None:
    """Parse --kinds / --agents flag.  Returns list or None on validation error.

    Prints an error message to stderr on failure (caller returns 2).
    """
    raw = raw.strip()
    lower = raw.lower()
    if lower in ("all",):
        return list(valid_options)
    if lower in ("none", "-"):
        return []

    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    result: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in valid_options:
            if token not in seen:
                result.append(token)
                seen.add(token)
        else:
            available = ", ".join(valid_options)
            print(
                f"error: unknown {flag_name} '{token}'; available: {available}",
                file=sys.stderr,
            )
            return None
    return result


# ─── CLI registration ──────────────────────────────────────────────────────

# Per spec D6 / D7
_DEFAULT_KINDS = ["task", "note", "spec"]
_DEFAULT_AGENTS: list[str] = []

_TIER_DESCRIPTIONS: dict[str, str] = {
    "minimal": "header + lifecycle views (active / ready / done)",
    "standard": "adds per-type slices, default_views, cross-kind 'recent'",
}

_TIER_OPTIONS: list[str] = ["minimal", "standard"]
_TIER_DEFAULT: str = "standard"


def register(subparsers) -> None:
    import argparse

    p = subparsers.add_parser(
        "init",
        help="initialise a new artifacts-os project",
        description=(
            "initialise a new artifacts-os project\n\n"
            "The init flow has three independent selection steps:\n"
            "  1. Settings tier — minimal / standard\n"
            "  2. Kinds         — multi-select from the bundled catalogue\n"
            "  3. Agents        — multi-select from the bundled catalogue\n\n"
            "Pass --template / --kinds / --agents to skip the corresponding\n"
            "step; use -y to accept defaults at every un-flagged step in\n"
            "non-interactive mode."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "directory",
        nargs="?",
        default=".",
        metavar="DIRECTORY",
        help="target directory (default: current directory)",
    )
    p.add_argument(
        "--template",
        choices=_TIER_OPTIONS,
        default=None,
        help="settings tier (skips Step 1 when given)",
    )
    p.add_argument(
        "--kinds",
        default=None,
        metavar="CSV",
        help=(
            "comma-separated kinds to install (skips Step 2)."
            " Use 'all' for every kind, 'none' for none."
        ),
    )
    p.add_argument(
        "--agents",
        default=None,
        metavar="CSV",
        help=(
            "comma-separated agents to install (skips Step 3)."
            " Use 'all' for every agent, 'none' for none."
        ),
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing files (per-file)",
    )
    p.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="accept defaults at every un-flagged step",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print actions without writing anything",
    )
    p.add_argument(
        "--openstation-compat",
        action="store_true",
        help="also create 'openstation -> artifacts' symlink",
    )
    p.add_argument(
        "--distro",
        default=None,
        metavar="URL",
        help=(
            "git-clonable distro URL; activates Step 4 (distro book pull) after "
            "vault files are written. Use -y to pull all books/items non-interactively."
        ),
    )
    p.add_argument(
        "--books",
        default=None,
        metavar="CSV",
        help=(
            "comma-separated book names to pull from distro (skips book-selection prompt). "
            "Use 'all' for every book. Requires --distro."
        ),
    )
    p.set_defaults(func=run, _pre_registry=True)


# ─── Main run ──────────────────────────────────────────────────────────────


def run(args) -> int:  # no registry — called before vault setup
    import datetime

    target = Path(args.directory).resolve()

    # ── Validate target directory ──────────────────────────────
    if not target.exists():
        parent = target.parent
        if not (parent.exists() and os.access(parent, os.W_OK)):
            print(
                f"error: '{target}' does not exist and parent is not writable",
                file=sys.stderr,
            )
            return 3
        target.mkdir(parents=True)

    # ── Discover available template options ────────────────────
    try:
        all_kinds = _discover_kinds()
        all_agents = _discover_agents()
    except Exception as exc:
        print(f"error: could not load bundled templates: {exc}", file=sys.stderr)
        return 2

    # ── Validate --books requires --distro ────────────────────────
    distro_url: str | None = getattr(args, "distro", None)
    books_flag: str | None = getattr(args, "books", None)
    if books_flag is not None and not distro_url:
        print("error: --books requires --distro", file=sys.stderr)
        return 2

    # ── Validate --kinds / --agents flag values (before any I/O) ──
    flag_kinds: list[str] | None = None
    flag_agents: list[str] | None = None

    if args.kinds is not None:
        flag_kinds = _parse_csv_flag(args.kinds, all_kinds, "--kinds")
        if flag_kinds is None:
            return 2

    if args.agents is not None:
        flag_agents = _parse_csv_flag(args.agents, all_agents, "--agents")
        if flag_agents is None:
            return 2

    # ── Already-initialised guard ──────────────────────────────
    settings_file = target / "artifacts.yaml"
    if settings_file.is_file() and not args.force:
        print(
            f"error: already initialised at {target};"
            " pass --force to re-init in place",
            file=sys.stderr,
        )
        return 2

    # ── Non-TTY guard (D3) ─────────────────────────────────────
    is_tty = sys.stdin.isatty()
    # Distro step is fully flagged when: no distro given, --books supplied, or dry-run
    distro_fully_flagged = (
        not distro_url
        or books_flag is not None
        or getattr(args, "dry_run", False)
    )
    all_flags = (
        args.template is not None
        and args.kinds is not None
        and args.agents is not None
        and distro_fully_flagged
    )
    if not is_tty and not args.yes and not all_flags:
        print(
            "error: stdin is not a TTY and no defaults were accepted.\n"
            "       Pass -y to accept defaults at every un-flagged step,\n"
            "       or supply --template, --kinds, and --agents explicitly.",
            file=sys.stderr,
        )
        return 2

    today_iso = datetime.date.today().isoformat()
    project_name = _get_project_name(target)
    project_alias = _derive_project_alias(project_name)

    # ── Step 1: Settings tier ──────────────────────────────────
    if args.template is not None:
        tier = args.template
    elif args.yes or not is_tty:
        tier = _TIER_DEFAULT
    else:
        tier = _prompt_single_step(
            "Settings tier (1 of 3)",
            _TIER_OPTIONS,
            _TIER_DESCRIPTIONS,
            default_idx=_TIER_OPTIONS.index(_TIER_DEFAULT) + 1,
        )

    # ── Step 2: Kinds ──────────────────────────────────────────
    if flag_kinds is not None:
        selected_kinds: list[str] = flag_kinds
    elif args.yes or not is_tty:
        selected_kinds = list(_DEFAULT_KINDS)
    else:
        selected_kinds = _prompt_multi_step("Kinds (2 of 3)", all_kinds, _DEFAULT_KINDS)

    # ── Step 3: Agents ─────────────────────────────────────────
    if flag_agents is not None:
        selected_agents: list[str] = flag_agents
    elif args.yes or not is_tty:
        selected_agents = list(_DEFAULT_AGENTS)
    else:
        selected_agents = _prompt_multi_step(
            "Agents (3 of 3)", all_agents, _DEFAULT_AGENTS
        )

    # ── D10: agent-kind auto-include ───────────────────────────
    agent_auto_included = False
    if selected_agents and "agent" not in selected_kinds:
        selected_kinds = list(selected_kinds) + ["agent"]
        agent_auto_included = True

    # ── Print summary ──────────────────────────────────────────
    kinds_display = ", ".join(selected_kinds) if selected_kinds else "(none)"
    if agent_auto_included:
        kinds_display += " (agent kind auto-included for selected agents)"
    agents_display = ", ".join(selected_agents) if selected_agents else "(none)"

    print("\nSelected:")
    print(f"  template : {tier}")
    print(f"  kinds    : {kinds_display}")
    print(f"  agents   : {agents_display}")
    print()

    # ── Build settings content ─────────────────────────────────
    try:
        settings_content = _load_settings_template(tier)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    settings_content = _interpolate(
        settings_content, project_name, project_alias, today_iso
    )

    # Req 6: inject artbook.distro_url before writing artifacts.yaml
    if distro_url:
        settings_content = settings_content.rstrip("\n") + (
            f"\n\nartbook:\n  distro_url: {distro_url}\n"
        )

    # ── Write loop ─────────────────────────────────────────────
    print("Writing files...")
    written = 0
    failed = 0
    failures: list[tuple[str, str]] = []

    def _do_write(path: Path, content: str) -> None:
        nonlocal written, failed
        rel = str(path.relative_to(target))
        exists = path.exists()

        if exists and not args.force:
            _print_skip(rel)
            return

        if args.dry_run:
            _print_write(rel, True, overwritten=exists)
            written += 1
            return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            _print_write(rel, False, overwritten=exists)
            written += 1
        except OSError as exc:
            _print_fail(rel, str(exc))
            failed += 1
            failures.append((rel, str(exc)))

    # artifacts.yaml
    _do_write(target / "artifacts.yaml", settings_content)

    # kinds
    for kind_name in selected_kinds:
        try:
            schema_text = _load_kind_schema(kind_name)
            artifact_text = _load_kind_artifact(kind_name)
        except Exception as exc:
            msg = str(exc)
            _print_fail(f"kinds/{kind_name}/*", msg)
            failed += 1
            failures.append((f"kinds/{kind_name}/*", msg))
            continue

        try:
            schema_obj = json.loads(schema_text)
        except Exception:
            schema_obj = {}
        x_dir: str = schema_obj.get("x-dir", f"{kind_name}s")

        _do_write(target / "artifacts" / "kinds" / kind_name / "kind.json", schema_text)
        _do_write(
            target / "artifacts" / "kinds" / kind_name / "ARTIFACT.md", artifact_text
        )
        _do_write(target / "artifacts" / x_dir / ".gitkeep", "")

    # agents
    for agent_name in selected_agents:
        try:
            agent_text = _load_agent_template(agent_name)
        except Exception as exc:
            msg = str(exc)
            _print_fail(f"agents/{agent_name}.md", msg)
            failed += 1
            failures.append((f"agents/{agent_name}.md", msg))
            continue
        _do_write(target / "artifacts" / "agents" / f"{agent_name}.md", agent_text)

    # openstation-compat symlink
    if getattr(args, "openstation_compat", False):
        symlink = target / "openstation"
        rel_sym = str(symlink.relative_to(target))
        if symlink.exists() or symlink.is_symlink():
            if not args.force:
                _print_skip(f"{rel_sym} -> artifacts")
        else:
            if args.dry_run:
                _print_write(f"{rel_sym} -> artifacts", True, overwritten=False)
            else:
                try:
                    os.symlink("artifacts", symlink)
                    _print_write(f"{rel_sym} -> artifacts", False, overwritten=False)
                    written += 1
                except OSError as exc:
                    _print_fail(rel_sym, str(exc))
                    failed += 1
                    failures.append((rel_sym, str(exc)))

    # ── Step 4: Distro (req 3–12) ──────────────────────────────
    # Vault files are written first (req 7); then clone + pull.
    # When -y and no --distro: skip silently (req 5).
    distro_had_error = False
    if distro_url:
        distro_had_error = _run_distro_step(
            distro_url,
            books_flag,
            target,
            yes=args.yes,
            dry_run=args.dry_run,
            is_tty=is_tty,
        )

    # ── Final output ───────────────────────────────────────────
    print()
    if args.dry_run:
        print(f"Dry-run complete. {written} files would be written.")
        return 0

    print(f"Initialised artifacts-os project: {target}")
    if failed > 0 or distro_had_error:
        print(f"  {written} files written, {failed} failed.")
        if distro_had_error:
            print("  Distro pull completed with errors (see above).")
        if failures:
            print()
            print("Failures:")
            for path, reason in failures:
                print(f"  ✗ {path}: {reason}")
        return 1

    return 0
