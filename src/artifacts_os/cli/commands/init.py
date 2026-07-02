"""cli init command — bootstrap a new artifacts-os project."""

import os
import sys
import tempfile
from dataclasses import dataclass
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
    """Prompt for a multi-select (per-book item selection)."""
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


# ─── Distro helpers ────────────────────────────────────────────────────────


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


# ─── Book flag parsing ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class BookSpec:
    name: str
    items: list[str] | None  # None = pull all


def _parse_book_flags(args, distro_url: str | None) -> list[BookSpec] | None:
    """Parse --book flags. Returns list[BookSpec] if flags given, None otherwise.

    Returns None (with no error) when no --book flags are given.
    Returns None when --book is given without a distro URL (caller checks args.book).
    """
    raw_flags: list[str] = getattr(args, "book", None) or []
    if not raw_flags:
        return None  # no --book flags → interactive or -y default
    if distro_url is None:
        # caller will detect this via args.book being non-empty
        return None
    specs: list[BookSpec] = []
    for token in raw_flags:
        name, sep, items_raw = token.partition(":")
        name = name.strip()
        if not name:
            print(f"error: invalid --book value: {token!r}", file=sys.stderr)
            return None
        items = (
            [i.strip() for i in items_raw.split(",") if i.strip()]
            if sep else None
        )
        specs.append(BookSpec(name=name, items=items))
    return specs


# ─── Bundled skill install ─────────────────────────────────────────────────


def _walk_resource(traversable) -> list:
    """Recursively walk a Traversable, yielding leaf files."""
    results = []
    for entry in traversable.iterdir():
        if entry.is_dir():
            results.extend(_walk_resource(entry))
        else:
            results.append(entry)
    return results


def _excluded_from_bundle(rel_path: Path) -> bool:
    """Returns True for __init__.py, __pycache__/, *.pyc, *.pyo, dotfiles."""
    parts = rel_path.parts
    if any(p == "__pycache__" for p in parts):
        return True
    if any(p.startswith(".") for p in parts):
        return True
    name = rel_path.name
    return (
        name == "__init__.py"
        or name.endswith(".pyc")
        or name.endswith(".pyo")
    )


def _install_bundled_skill(
    target: Path, *, force: bool, dry_run: bool, no_promote: bool, _do_write
) -> None:
    """Install the bundled artifacts-os skill via canonical-write + promote (D40).

    1. Write each skill file to ``artifacts/skills/artifacts-os/<rel>`` (canonical).
    2. Unless *no_promote* or *dry_run*, run ``promote_book`` on a synthetic
       in-memory Book to create relative symlinks at
       ``.claude/skills/artifacts-os/<rel>`` → canonical.

    The state file at ``artifacts/.artbook/state.json`` records the promotion
    under ``promotions["artifacts-os-skill"]``.  A subsequent distro pull that
    ships its own ``skills`` book replaces this entry cleanly (the synthetic
    name does not collide with any real book name).

    Uses the _do_write callable for canonical file writing so that ``--force``
    and ``--dry-run`` semantics are respected.
    """
    root = files("artifacts_os.ai.claude.skills").joinpath("artifacts-os")
    # 1. Canonical destination: artifacts/skills/artifacts-os/
    canonical_dest_root = target / "artifacts" / "skills" / "artifacts-os"

    leaf_files = _walk_resource(root)
    for entry in leaf_files:
        rel = _traversable_rel_path(entry, root)
        if rel is None or _excluded_from_bundle(rel):
            continue
        content = entry.read_text(encoding="utf-8")
        _do_write(canonical_dest_root / rel, content)

    # dry_run: canonical writes already reported via _do_write; skip promotion.
    if dry_run:
        return

    # 2. Promote: symlink .claude/skills/artifacts-os/<rel> → canonical.
    if not no_promote:
        from artifacts_os.artbook.manifest import Book, Promote
        from artifacts_os.artbook.placement import promote_book
        from artifacts_os.artbook.state import read_state

        book = Book(
            name="artifacts-os-skill",
            src="(bundled)",
            dest="artifacts/skills/",
            promote=Promote(target=".claude/skills/", mode="symlink"),
            recurse=True,
            files=None,
        )
        state = read_state(target)
        promote_book(book, target, state=state)


def _traversable_rel_path(entry, root) -> Path | None:
    """Compute the relative path of a Traversable entry from root.

    Both entry and root are Traversable objects. We derive the relative
    path by comparing their string representations (name segments).
    """
    # Convert to string paths — works for both zipimport and filesystem
    try:
        entry_path = Path(str(entry))
        root_path = Path(str(root))
        return entry_path.relative_to(root_path)
    except (ValueError, TypeError):
        # Fallback: just use the filename
        return Path(entry.name)


# ─── Book loop ─────────────────────────────────────────────────────────────


def _run_book_loop(
    distro_url: str,
    distro_source: str | None,
    book_specs: list[BookSpec] | None,
    target: Path,
    *,
    yes: bool,
    dry_run: bool,
    is_tty: bool,
    force: bool,
    _do_write,
) -> int:
    """Execute the book loop: clone the distro and pull selected books.

    Returns:
        0  — success
        1  — per-book errors (loop continues, non-zero exit at end)
        2  — fatal pre-pull error (manifest/clone/unknown book)
    """
    import artifacts_os.artbook as artbook
    from artifacts_os.artbook import FetchError, ManifestError
    from artifacts_os.artbook.errors import ArtbookError
    from artifacts_os.artbook.placement import (
        _select_files,
        filter_entries_by_items,
    )

    print()

    # Req 12: dry-run — report intended action without cloning or writing.
    if dry_run:
        if book_specs is not None:
            books_info = ", ".join(
                f"{bs.name} ({len(bs.items)} items)" if bs.items else f"{bs.name} (all)"
                for bs in book_specs
            )
            print(f"  [would] pull from distro: {distro_url} (books: {books_info})")
        else:
            print(f"  [would] pull from distro: {distro_url} (all books)")
        return 0

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
                # Env-supplied distro URL failure is non-fatal (fall through to D2 not
                # applicable here — we already wrote artifacts.yaml). Exit 2 for CLI,
                # exit 1 for env (vault is already written).
                if distro_source == "cli":
                    return 2
                return 1
            except ManifestError as exc:
                print(f"error: distro manifest invalid: {exc}", file=sys.stderr)
                if distro_source == "cli":
                    return 2
                return 1

            all_book_names = [b.name for b in manifest.books]

            # ── Validate --book names against manifest ────────────────
            if book_specs is not None:
                invalid_books = [
                    bs.name for bs in book_specs if bs.name not in all_book_names
                ]
                if invalid_books:
                    avail = ", ".join(all_book_names)
                    print(
                        f"error: unknown book(s) in --book: {', '.join(invalid_books)}; "
                        f"available: {avail}",
                        file=sys.stderr,
                    )
                    return 2

            # ── Determine which books to pull ─────────────────────────
            if book_specs is not None:
                # --book flags supplied — use exactly those books
                selected_book_names = [bs.name for bs in book_specs]
            elif yes:
                # -y + distro → all books, all items
                selected_book_names = list(all_book_names)
            else:
                # Interactive book selection: show all books, default = all
                print()
                selected_book_names = _prompt_multi_step(
                    "Books to pull",
                    all_book_names,
                    all_book_names,
                )

            if not selected_book_names:
                print("  No books selected — skipping distro pull.")
                return 0

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

                # Determine item filter for this book
                preselected = None
                if book_specs is not None:
                    # Find the BookSpec for this book
                    spec = next(bs for bs in book_specs if bs.name == book_name)
                    if spec.items is not None:
                        # Validate items before filtering
                        item_names = _distro_item_names(all_entries, book.recurse)
                        invalid_items = [i for i in spec.items if i not in item_names]
                        if invalid_items:
                            avail = ", ".join(item_names)
                            print(
                                f"error: unknown item(s) in --book {book_name}: "
                                f"{', '.join(invalid_items)}; available: {avail}",
                                file=sys.stderr,
                            )
                            return 2
                        filtered, _unmatched, _ = filter_entries_by_items(
                            all_entries,
                            spec.items,
                            recurse=book.recurse,
                        )
                        preselected = filtered
                elif not yes and is_tty:
                    # Interactive item selection (per-book item subset)
                    item_names = _distro_item_names(all_entries, book.recurse)
                    if item_names:
                        print()
                        selected_items = _prompt_multi_step(
                            f"Book '{book_name}' ({len(item_names)} items)",
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
                    # Continue with remaining books on per-book failure
                    print(
                        f"  error: book '{book_name}': {exc}", file=sys.stderr
                    )
                    had_error = True

            return 1 if had_error else 0

    except Exception as exc:  # noqa: BLE001
        print(f"error: distro step failed unexpectedly: {exc}", file=sys.stderr)
        return 1


# ─── CLI registration ──────────────────────────────────────────────────────

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
            "The init flow has two stages:\n"
            "  1. Settings tier — single choice: minimal / standard\n"
            "  2..N. One multi-select prompt per book in the distro\n"
            "        (only when --distro or $ARTIFACTS_DISTRO_URL is set)\n\n"
            "When no distro is configured, only Step 1 runs and the bundled\n"
            "artifacts-os skill is installed into .claude/skills/artifacts-os/.\n\n"
            "Pass --template to skip Step 1; use --book to specify which books\n"
            "and items to pull non-interactively; use -y to accept defaults."
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
        "--book",
        action="append",
        metavar="NAME[:ITEMS]",
        help=(
            "book to pull from distro (repeatable). "
            "NAME pulls the whole book; NAME:item,item pulls a subset. "
            "Requires --distro or $ARTIFACTS_DISTRO_URL."
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
        "--distro",
        default=None,
        metavar="URL",
        help=(
            "git-clonable distro URL; activates the book loop after "
            "artifacts.yaml is written. Use -y to pull all books/items "
            "non-interactively. Defaults to $ARTIFACTS_DISTRO_URL when set; "
            "the CLI flag always wins."
        ),
    )
    p.add_argument(
        "--no-promote",
        action="store_true",
        help=(
            "skip the promotion step — write canonical files only, do not "
            "create tool-specific symlinks or copies under .claude/"
        ),
    )
    p.set_defaults(func=run, _pre_registry=True)


# ─── Main run ──────────────────────────────────────────────────────────────


def run(args) -> int:  # no registry — called before vault setup
    import datetime

    # Spec s0034 §7.3: emit a courtesy note when --config is given alongside
    # init — the flag has no effect on init, which always writes artifacts.yaml.
    if getattr(args, "config", None) is not None:
        print(
            "note: --config is ignored by `artifacts init`\n"
            "      (init always writes artifacts.yaml at the target directory)",
            file=sys.stderr,
        )

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

    # ── Resolve distro URL (CLI flag > $ARTIFACTS_DISTRO_URL > none) ──
    cli_distro: str | None = getattr(args, "distro", None)
    env_distro_raw = os.environ.get("ARTIFACTS_DISTRO_URL", "")
    env_distro = env_distro_raw.strip() or None
    if cli_distro is not None:
        distro_url: str | None = cli_distro
        distro_source: str | None = "cli"
    elif env_distro is not None:
        distro_url = env_distro
        distro_source = "env"
    else:
        distro_url = None
        distro_source = None

    # ── Validate --book requires --distro (or env var) ──────────
    raw_book_flags: list[str] = getattr(args, "book", None) or []
    if raw_book_flags and distro_url is None:
        print(
            "error: --book requires --distro or $ARTIFACTS_DISTRO_URL",
            file=sys.stderr,
        )
        return 2

    # ── Parse --book flags ─────────────────────────────────────
    book_specs: list[BookSpec] | None = _parse_book_flags(args, distro_url)
    # If raw_book_flags is non-empty but book_specs is None, parsing failed
    if raw_book_flags and book_specs is None:
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

    # ── Non-TTY guard ──────────────────────────────────────────
    is_tty = sys.stdin.isatty()
    # Fully flagged = template is set AND (no distro OR book_specs given OR dry_run OR yes)
    distro_fully_flagged = (
        not distro_url
        or book_specs is not None
        or getattr(args, "dry_run", False)
        or args.yes
    )
    all_flags = args.template is not None and distro_fully_flagged
    if not is_tty and not args.yes and not all_flags:
        print(
            "error: stdin is not a TTY and no defaults were accepted.\n"
            "       Pass -y to accept defaults at every un-flagged step,\n"
            "       or supply --template (and --book for distro steps) explicitly.",
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
        step_label = "Settings tier (1 of 1)" if distro_url is None else "Settings tier (1 of N)"
        tier = _prompt_single_step(
            step_label,
            _TIER_OPTIONS,
            _TIER_DESCRIPTIONS,
            default_idx=_TIER_OPTIONS.index(_TIER_DEFAULT) + 1,
        )

    # ── Print summary ──────────────────────────────────────────
    print("\nSelected:")
    print(f"  template : {tier}")
    if distro_url:
        suffix = " (from ARTIFACTS_DISTRO_URL)" if distro_source == "env" else ""
        print(f"  distro   : {distro_url}{suffix}")
        if book_specs:
            books_summary = ", ".join(
                f"{bs.name} ({len(bs.items)} items)" if bs.items else f"{bs.name} (all)"
                for bs in book_specs
            )
            print(f"  books    : {books_summary}")
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

    # Inject artbook.distro_url before writing artifacts.yaml
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

    # ── D2 fallback: no distro → install bundled skill ─────────
    if distro_url is None:
        _install_bundled_skill(
            target,
            force=args.force,
            dry_run=args.dry_run,
            no_promote=getattr(args, "no_promote", False),
            _do_write=_do_write,
        )
        # Final output
        print()
        if args.dry_run:
            print(f"Dry-run complete. {written} files would be written.")
            return 0
        print(f"Initialised artifacts-os project: {target}")
        if failed > 0:
            print(f"  {written} files written, {failed} failed.")
            if failures:
                print()
                print("Failures:")
                for path, reason in failures:
                    print(f"  ✗ {path}: {reason}")
            return 1
        return 0

    # ── D1 + D3: book loop ─────────────────────────────────────
    book_loop_result = _run_book_loop(
        distro_url,
        distro_source,
        book_specs,
        target,
        yes=args.yes,
        dry_run=args.dry_run,
        is_tty=is_tty,
        force=args.force,
        _do_write=_do_write,
    )

    # For exit code 2 from book loop (pre-pull fatal errors), propagate directly
    if book_loop_result == 2:
        return 2

    distro_had_error = book_loop_result == 1

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
