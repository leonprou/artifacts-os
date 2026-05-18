"""cli book commands — distro-backed artifact distribution.

Three verbs under the ``book`` namespace:

    artifacts book list                [--json]
    artifacts book show <name>         [--json]
    artifacts book pull <name>         [--json] [--dry-run]

``book`` is a deliberate exception to the flat-verb convention: it
introduces a resource namespace so the three operations read as natural
sentences.  ``--json`` applies to all three verbs; ``--dry-run`` is
exclusive to ``pull``.

Exit codes (command-specific — see §5.5):
    0  success
    1  runtime error (clone failed / manifest invalid / unknown book / write failed /
                      dest escapes vault / removed v1 `type:` field)
    2  usage error (bad flag, missing argument)
    3  vault not initialised (artifacts.yaml not found)
    4  artbook.distro_url missing or empty in artifacts.yaml

Spec: s0029-artbook-mvp-distribution-model §5, D24, D25
"""

from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.markup import escape as _markup_escape

import yaml

import artifacts_os.artbook as artbook
import artifacts_os.views as views
from artifacts_os.artbook import (
    ArtbookSettings,
    FetchError,
    ManifestError,
    PromotionReport,
    SettingsError,
    UnknownBookError,
)
from artifacts_os.artbook.errors import ArtbookError
from artifacts_os.artbook.fetch import get_short_sha
from artifacts_os.artbook.manifest import load_manifest
from artifacts_os.artbook.placement import (
    _select_files,
    destination_for,
    filter_entries_by_items,
    promote_book,
)
from artifacts_os.artbook.state import read_state
from artifacts_os.core import find_vault_root
from artifacts_os.core.models import ItemMeta
from artifacts_os.views._views import FieldSpec


# ---------------------------------------------------------------------------
# ItemMeta subclasses for table rendering (spec §5.1.3)
# ---------------------------------------------------------------------------


@dataclass
class BookRow(ItemMeta):
    """One book entry — rendered by ``book list``."""

    name: str
    src: str
    dest: str
    description: str = ""


@dataclass
class BookContentRow(ItemMeta):
    """One file under a book's src — rendered by ``book show``."""

    filename: str


@dataclass
class WriteActionRow(ItemMeta):
    """One planned or completed write — rendered by ``book pull``."""

    action: str       # "write" | "overwrite" | "[would] write" | "[would] overwrite"
    destination: str
    was_symlink: bool = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CONSOLE = Console()


def _err(cause: str, hint: str = "") -> None:
    """Print a two-line error message to stderr (spec §5.6)."""
    msg = f"error: {cause}"
    if hint:
        msg += f"\n       {hint}"
    print(msg, file=sys.stderr)


def _load_vault_and_raw() -> tuple[Path | None, dict]:
    """Return (vault_root, raw_yaml) or (None, {}) when vault is not found."""
    root = find_vault_root()
    if root is None:
        _err(
            "not in an artifacts-os vault (no artifacts.yaml found walking up from the current directory).",
            "Run `artifacts init` to create one, or cd into an existing vault.",
        )
        return None, {}

    settings_path = root / "artifacts.yaml"
    try:
        raw = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    except Exception:
        raw = {}
    return root, raw


def _artbook_settings_from_raw(raw: dict) -> ArtbookSettings:
    """Build ArtbookSettings directly from the raw artifacts.yaml dict.

    Uses ArtbookSettings.from_base via a duck-typed namespace; raises
    SettingsError for invalid promotion / promote_mode values (D39).
    """
    from types import SimpleNamespace
    return ArtbookSettings.from_base(SimpleNamespace(raw=raw))


def _book_header(manifest, distro_url: str, sha: str) -> str:
    """Single-line distro header for list/show output."""
    desc = f" — {manifest.description}" if manifest.description else ""
    sha_str = f" @ {sha}" if sha else ""
    return (
        f"[bold]Distro:[/bold] {manifest.name}{desc}\n"
        f"[bold]URL:[/bold]    {distro_url}{sha_str}"
    )


# ---------------------------------------------------------------------------
# Verb: list
# ---------------------------------------------------------------------------


def _render_book_list(manifest, distro_url: str, sha: str) -> None:
    """Render the book list table to the console (shared by local and remote paths)."""
    rows = []
    for b in manifest.books:
        desc = b.description or ""
        # D26 — annotate recurse-mode books in the Description column.
        if getattr(b, "recurse", False):
            desc = f"(recurse) {desc}".rstrip()
        rows.append(
            BookRow(
                name=b.name,
                src=b.src,
                dest=b.dest,
                description=desc,
            )
        )
    columns = [
        FieldSpec(key="name", fmt=None, label="Name"),
        FieldSpec(key="src", fmt=None, label="Source"),
        FieldSpec(key="dest", fmt=None, label="Destination"),
        FieldSpec(key="description", fmt=None, label="Description"),
    ]
    _CONSOLE.print(_book_header(manifest, distro_url, sha))
    _CONSOLE.print()
    _CONSOLE.print(views.render_table(rows, columns))
    n = len(rows)
    _CONSOLE.print(f"\n{n} book{'s' if n != 1 else ''}.")


def _run_list(args, root: Path, raw: dict) -> int:
    # D23 — local-manifest auto-detect: if artbook.yaml is in the vault root
    # and --remote is not set, read it in place without cloning.
    local_manifest_path = root / "artbook.yaml"
    if not getattr(args, "remote", False) and local_manifest_path.is_file():
        try:
            manifest = load_manifest(root)
        except ManifestError as exc:
            _err(str(exc))
            return 1

        if args.json_out:
            print(json.dumps({
                "distro": {
                    "name": manifest.name,
                    "description": manifest.description,
                    "url": None,
                    "sha": None,
                    "local": True,
                },
                "books": [dataclasses.asdict(b) for b in manifest.books],
            }, ensure_ascii=False))
            return 0

        _render_book_list(manifest, distro_url="(local)", sha="")
        return 0

    arts = _artbook_settings_from_raw(raw)
    if not arts.distro_url:
        _err(
            "artbook.distro_url not configured in artifacts.yaml",
            "Add `artbook.distro_url: <git-url>` to artifacts.yaml.",
        )
        return 4

    try:
        with tempfile.TemporaryDirectory(prefix="artbook-list-") as td:
            clone_root = Path(td) / "clone"
            manifest, _ = artbook.read_manifest(arts.distro_url, clone_into=clone_root)
            sha = get_short_sha(clone_root)

            if args.json_out:
                print(json.dumps({
                    "distro": {
                        "name": manifest.name,
                        "description": manifest.description,
                        "url": arts.distro_url,
                        "sha": sha,
                    },
                    "books": [dataclasses.asdict(b) for b in manifest.books],
                }, ensure_ascii=False))
                return 0

            _render_book_list(manifest, distro_url=arts.distro_url, sha=sha)

    except FetchError as exc:
        _err(
            f"git clone failed (exit {exc.returncode})",
            f"URL: {arts.distro_url}\nstderr: {exc.stderr.strip()}",
        )
        return 1
    except ManifestError as exc:
        _err(str(exc))
        return 1
    except ArtbookError as exc:
        _err(str(exc))
        return 1

    return 0


# ---------------------------------------------------------------------------
# Verb: show
# ---------------------------------------------------------------------------


def _render_book_show(
    book,
    manifest,
    src_dir: Path,
    root: Path,
    distro_url: str,
    sha: str,
    json_out: bool,
) -> int:
    """Render `book show` output (shared by local and remote paths).

    Returns 0 on success, 1 on error.
    """
    dest = destination_for(root, book)
    dest_rel = dest.relative_to(root)

    try:
        src_entries = _select_files(src_dir, book)
    except (ManifestError, ArtbookError) as exc:
        _err(str(exc))
        return 1
    # D26 — entries are now (abs_path, rel_path) tuples. Flat / allowlist
    # modes keep rel as a flat filename; recurse mode produces nested rels.
    rel_paths: list[Path] = [rel for _abs, rel in src_entries]

    if json_out:
        distro_info: dict = {"name": manifest.name}
        if distro_url:
            distro_info["url"] = distro_url
            distro_info["sha"] = sha
        else:
            distro_info["url"] = None
            distro_info["sha"] = None
            distro_info["local"] = True

        if book.recurse:
            # D26 — group contents by unit (first path component)
            units: dict[str, list[str]] = {}
            for rel in rel_paths:
                parts = rel.parts
                unit = parts[0] if parts else ""
                inner = str(Path(*parts[1:])) if len(parts) > 1 else ""
                if unit:
                    units.setdefault(unit, []).append(inner)
            contents_payload: list = [
                {"unit": u, "files": files} for u, files in units.items()
            ]
        else:
            contents_payload = [str(rel) for rel in rel_paths]

        print(json.dumps({
            "book": dataclasses.asdict(book),
            "distro": distro_info,
            "contents": contents_payload,
        }, ensure_ascii=False))
        return 0

    desc = book.description or ""
    _CONSOLE.print(f"[bold]Book:[/bold]        {book.name}")
    _CONSOLE.print(f"[bold]Source:[/bold]      {book.src}")
    _CONSOLE.print(f"[bold]Destination:[/bold] {dest_rel}/")
    if book.recurse:
        _CONSOLE.print("[bold]Mode:[/bold]        recurse (folder-of-folders)")
    _CONSOLE.print(f"[bold]Description:[/bold] {desc}")
    _CONSOLE.print()
    _CONSOLE.print(f"[bold]Distro:[/bold]      {manifest.name}")
    if distro_url:
        _CONSOLE.print(f"[bold]URL:[/bold]         {distro_url} @ {sha}")
    else:
        _CONSOLE.print("[bold]URL:[/bold]         (local)")
    _CONSOLE.print()

    if book.recurse:
        # D26 — grouped unit/file rendering
        units_grouped: dict[str, list[str]] = {}
        for rel in rel_paths:
            parts = rel.parts
            if not parts:
                continue
            unit = parts[0]
            inner = str(Path(*parts[1:])) if len(parts) > 1 else parts[0]
            # If rel is just the unit name (a file at unit root), inner == filename
            if len(parts) > 1:
                units_grouped.setdefault(unit, []).append(inner)
            else:
                # Loose file directly under src — shouldn't happen in recurse mode
                # because the walker ignores them, but defensively include.
                units_grouped.setdefault(unit, []).append("")
        n_units = len(units_grouped)
        n_files = sum(len(v) for v in units_grouped.values())
        _CONSOLE.print(
            f"Contents ({n_units} unit{'s' if n_units != 1 else ''}, "
            f"{n_files} file{'s' if n_files != 1 else ''}):"
        )
        for unit, files in units_grouped.items():
            _CONSOLE.print(f"\n  {unit}/")
            for f in files:
                _CONSOLE.print(f"    {f}")
    else:
        n = len(rel_paths)
        _CONSOLE.print(f"Contents ({n} file{'s' if n != 1 else ''}):")
        for rel in rel_paths:
            _CONSOLE.print(f"  {rel}")
    return 0


def _run_show(args, root: Path, raw: dict) -> int:
    book_name: str = args.name

    # D23 — local-manifest auto-detect: if artbook.yaml is in the vault root
    # and --remote is not set, read it in place without cloning.
    local_manifest_path = root / "artbook.yaml"
    if not getattr(args, "remote", False) and local_manifest_path.is_file():
        try:
            manifest = load_manifest(root)
        except ManifestError as exc:
            _err(str(exc))
            return 1

        try:
            book = artbook.find_book(manifest, book_name)
        except UnknownBookError:
            available = ", ".join(b.name for b in manifest.books)
            _err(
                f"book '{book_name}' not found in distro '{manifest.name}'",
                f"Available books: {available}.",
            )
            return 1

        src_dir = root / book.src
        return _render_book_show(
            book, manifest, src_dir, root,
            distro_url="", sha="", json_out=args.json_out,
        )

    arts = _artbook_settings_from_raw(raw)
    if not arts.distro_url:
        _err(
            "artbook.distro_url not configured in artifacts.yaml",
            "Add `artbook.distro_url: <git-url>` to artifacts.yaml.",
        )
        return 4

    try:
        with tempfile.TemporaryDirectory(prefix="artbook-show-") as td:
            clone_root = Path(td) / "clone"
            manifest, _ = artbook.read_manifest(arts.distro_url, clone_into=clone_root)
            sha = get_short_sha(clone_root)

            try:
                book = artbook.find_book(manifest, book_name)
            except UnknownBookError:
                available = ", ".join(b.name for b in manifest.books)
                _err(
                    f"book '{book_name}' not found in distro '{manifest.name}'",
                    f"Available books: {available}.",
                )
                return 1

            src_dir = clone_root / book.src
            return _render_book_show(
                book, manifest, src_dir, root,
                distro_url=arts.distro_url, sha=sha, json_out=args.json_out,
            )

    except FetchError as exc:
        _err(
            f"git clone failed (exit {exc.returncode})",
            f"URL: {arts.distro_url}\nstderr: {exc.stderr.strip()}",
        )
        return 1
    except ManifestError as exc:
        _err(str(exc))
        return 1
    except ArtbookError as exc:
        _err(str(exc))
        return 1

    return 0


# ---------------------------------------------------------------------------
# Verb: pull
# ---------------------------------------------------------------------------


def _plan_writes(
    book,
    clone_root: Path,
    vault_root: Path,
    *,
    preselected: list | None = None,
) -> list[WriteActionRow]:
    """Return planned writes without executing them (used for --dry-run).

    ``WriteActionRow.action`` stores the base action (``"write"`` or
    ``"overwrite"``); the ``[would]`` prefix is added at display time.

    *preselected* — when provided, use these ``(abs_src, rel)`` entries
    directly instead of calling ``_select_files`` (pass after item filtering).
    """
    dest_dir = destination_for(vault_root, book)

    src_dir = clone_root / book.src
    src_entries = preselected if preselected is not None else _select_files(src_dir, book)

    rows: list[WriteActionRow] = []
    for _src_file, rel in src_entries:
        dst = dest_dir / rel
        was_symlink = dst.is_symlink()
        overwritten = dst.exists() or was_symlink
        rows.append(WriteActionRow(
            action="overwrite" if overwritten else "write",
            destination=str(dst.relative_to(vault_root)),
            was_symlink=was_symlink,
        ))
    return rows


def _pull_write_rows(report, vault_root: Path) -> list[WriteActionRow]:
    """Convert a PullReport's written files into WriteActionRows (relative paths)."""
    rows: list[WriteActionRow] = []
    for wf in report.written:
        base_action = "overwrite" if wf.overwritten else "write"
        action = f"{base_action} (symlink replaced)" if wf.was_symlink else base_action
        rows.append(WriteActionRow(
            action=action,
            destination=str(wf.destination.relative_to(vault_root)),
            was_symlink=wf.was_symlink,
        ))
    return rows


def _render_promotion_report(
    promo: PromotionReport,
    vault_root: Path,
    *,
    json_out: bool,
    dry_run: bool = False,
) -> None:
    """Render a PromotionReport as a Rich table or JSON (D33, D34)."""
    from rich.table import Table as _Table
    from rich.text import Text as _Text

    if json_out:
        payload = {
            "book": promo.book.name,
            "target_root": str(promo.target_root.relative_to(vault_root)),
            "mode": promo.mode,
            "dry_run": dry_run,
            "promoted": [
                {
                    "canonical": str(pf.canonical.relative_to(vault_root)),
                    "target": str(pf.target.relative_to(vault_root)),
                    "mode": pf.mode,
                    "overwritten": pf.overwritten,
                    "fallback": pf.fallback,
                }
                for pf in promo.promoted
            ],
            "cleaned": [str(p.relative_to(vault_root)) for p in promo.cleaned],
            "skipped": [str(p.relative_to(vault_root)) for p in promo.skipped],
            "fallback_count": promo.fallback_count,
            "errors": list(promo.errors),
        }
        print(json.dumps(payload, ensure_ascii=False))
        return

    header_dry = _markup_escape("[dry-run] ") if dry_run else ""
    _CONSOLE.print(f"\n{header_dry}Promotion → {_markup_escape(str(promo.target_root.relative_to(vault_root)))}/")

    if promo.promoted:
        table = _Table()
        table.add_column("Action")
        table.add_column("Target")
        for pf in promo.promoted:
            label = "overwrite" if pf.overwritten else "write"
            if pf.fallback:
                label += " (copy fallback)"
            action_text = _Text(f"[would] {label}" if dry_run else label)
            target_rel = str(pf.target.relative_to(vault_root))
            table.add_row(action_text, _Text(target_rel))
        _CONSOLE.print(table)

    if promo.cleaned:
        _CONSOLE.print(f"  Cleaned {len(promo.cleaned)} stale target(s).")
    if promo.skipped:
        _CONSOLE.print(f"  Skipped {len(promo.skipped)} user-modified target(s).")
    if promo.errors:
        for err in promo.errors:
            _CONSOLE.print(f"  [red]error:[/red] {_markup_escape(err)}")
    n_promoted = len(promo.promoted)
    _CONSOLE.print(f"  {n_promoted} file{'s' if n_promoted != 1 else ''} promoted.")


def _run_pull(args, root: Path, raw: dict) -> int:
    try:
        arts = _artbook_settings_from_raw(raw)
    except SettingsError as exc:
        _err(str(exc))
        return 1

    if not arts.distro_url:
        _err(
            "artbook.distro_url not configured in artifacts.yaml",
            "Add `artbook.distro_url: <git-url>` to artifacts.yaml.",
        )
        return 4

    book_name: str = args.name
    dry_run: bool = args.dry_run
    items: list[str] = args.items or []
    no_promote: bool = getattr(args, "no_promote", False)

    try:
        with tempfile.TemporaryDirectory(prefix="artbook-pull-") as td:
            clone_root = Path(td) / "clone"
            manifest, _ = artbook.read_manifest(arts.distro_url, clone_into=clone_root)
            sha = get_short_sha(clone_root)

            try:
                book = artbook.find_book(manifest, book_name)
            except UnknownBookError:
                available = ", ".join(b.name for b in manifest.books)
                _err(
                    f"book '{book_name}' not found in distro '{manifest.name}'",
                    f"Available books: {available}.",
                )
                return 1

            # --- Item-level filtering (req 2–5) ---
            # Compute all entries first so we can validate item names before writing.
            preselected = None
            if items:
                src_dir = clone_root / book.src
                try:
                    all_entries = _select_files(src_dir, book)
                except (ManifestError, ArtbookError) as exc:
                    _err(str(exc))
                    return 1
                filtered, unmatched, available_items = filter_entries_by_items(
                    all_entries, items, recurse=book.recurse
                )
                if unmatched:
                    avail_str = ", ".join(available_items) if available_items else "(none)"
                    n = len(unmatched)
                    _err(
                        f"item{'s' if n > 1 else ''} not found in book '{book_name}': "
                        + ", ".join(unmatched),
                        f"Available items: {avail_str}\n"
                        f"       Run `artifacts book show {book_name}` to see all items.",
                    )
                    return 1
                preselected = filtered

            promo_report = None
            promo_skipped_reason = None
            if dry_run:
                try:
                    rows = _plan_writes(book, clone_root, root, preselected=preselected)
                except (ManifestError, ArtbookError) as exc:
                    _err(str(exc))
                    return 1
            else:
                try:
                    report = artbook.pull_book(
                        book, clone_root, root,
                        distro_url=arts.distro_url,
                        distro_sha=sha,
                        preselected=preselected,
                        no_promote=no_promote,
                        promote_disabled=(arts.promotion == "disabled"),
                        promote_mode_override=arts.promote_mode,
                    )
                except (ManifestError, ArtbookError) as exc:
                    _err(str(exc))
                    return 1
                rows = _pull_write_rows(report, root)
                promo_report = report.promotion
                promo_skipped_reason = report.promotion_skipped_reason

            # --- Compute summary stats ---
            n_written = len(rows)
            n_overwritten = sum(1 for r in rows if "overwrite" in r.action)
            n_new = n_written - n_overwritten

            if args.json_out:
                for r in rows:
                    # Use the base action for JSON (strip symlink note)
                    json_action = r.action.split(" (")[0]
                    print(json.dumps({
                        "action": json_action,
                        "destination": r.destination,
                        "overwritten": "overwrite" in r.action,
                        "was_symlink": r.was_symlink,
                    }, ensure_ascii=False))
                # Final summary line
                summary_line: dict = {
                    "summary": {
                        "written": n_written,
                        "overwritten": n_overwritten,
                        "new": n_new,
                    },
                    "distro": {"url": arts.distro_url, "sha": sha},
                    "book": book_name,
                }
                if dry_run:
                    summary_line["dry_run"] = True
                elif promo_report is not None:
                    summary_line["promotion"] = {
                        "promoted": len(promo_report.promoted),
                        "cleaned": len(promo_report.cleaned),
                        "errors": len(promo_report.errors),
                    }
                elif not dry_run:
                    summary_line["promotion_skipped"] = promo_skipped_reason
                print(json.dumps(summary_line, ensure_ascii=False))
                return 0

            # --- Rich table output ---
            # Escape action strings so Rich doesn't interpret "(" or other chars
            # as markup; for dry-run prefix each action with "[would] " — escaped.
            from rich.text import Text as _Text

            header_dry = _markup_escape("[dry-run] ") if dry_run else ""

            _CONSOLE.print(
                f"{header_dry}Pulling book '{_markup_escape(book_name)}' from "
                f"{_markup_escape(manifest.name)} @ {_markup_escape(sha)}…"
            )
            _CONSOLE.print()

            # Build table manually so action text is never interpreted as markup.
            from rich.table import Table as _Table

            table = _Table()
            table.add_column("Action")
            table.add_column("Destination")
            for r in rows:
                action_text = _Text(f"[would] {r.action}" if dry_run else r.action)
                table.add_row(action_text, _Text(r.destination))
            _CONSOLE.print(table)
            _CONSOLE.print()

            summary_text = (
                f"Summary: {n_written} written "
                f"({n_overwritten} overwritten, {n_new} new)."
            )
            if dry_run:
                # Use Text to avoid markup parsing on "[dry-run]"
                from rich.text import Text as _RText
                _CONSOLE.print(_RText(f"[dry-run] {summary_text}"))
            else:
                _CONSOLE.print(summary_text)

            # Render promotion report if present
            if not dry_run:
                if promo_report is not None:
                    _render_promotion_report(promo_report, root, json_out=False)
                    # Exit 1 if any promotion errors (D36)
                    if promo_report.errors:
                        return 1
                elif promo_skipped_reason:
                    _CONSOLE.print(f"\nPromotion skipped (reason: {promo_skipped_reason}).")

    except FetchError as exc:
        _err(
            f"git clone failed (exit {exc.returncode})",
            f"URL: {arts.distro_url}\nstderr: {exc.stderr.strip()}",
        )
        return 1
    except ManifestError as exc:
        _err(str(exc))
        return 1
    except ArtbookError as exc:
        _err(str(exc))
        return 1

    return 0


# ---------------------------------------------------------------------------
# Verb: promote
# ---------------------------------------------------------------------------


def _run_promote(args, root: Path, raw: dict) -> int:
    """Re-run promotion for one or all books that have a promote: field (D34)."""
    try:
        arts = _artbook_settings_from_raw(raw)
    except SettingsError as exc:
        _err(str(exc))
        return 1

    book_name: str | None = getattr(args, "book_name", None) or None
    clean: bool = getattr(args, "clean", False)
    dry_run: bool = getattr(args, "dry_run", False)
    json_out: bool = getattr(args, "json_out", False)

    # Load manifest (local preferred, then remote)
    local_manifest_path = root / "artbook.yaml"
    if local_manifest_path.is_file():
        try:
            manifest = load_manifest(root)
        except ManifestError as exc:
            _err(str(exc))
            return 1
    elif arts.distro_url:
        try:
            with tempfile.TemporaryDirectory(prefix="artbook-promote-") as td:
                clone_root = Path(td) / "clone"
                manifest, _ = artbook.read_manifest(arts.distro_url, clone_into=clone_root)
        except (FetchError, ManifestError, ArtbookError) as exc:
            _err(str(exc))
            return 1
    else:
        _err(
            "no local artbook.yaml found and artbook.distro_url not configured",
            "Cannot load manifest for promotion. Add artbook.distro_url to artifacts.yaml.",
        )
        return 4

    # Resolve which books to promote
    if book_name:
        try:
            books_to_promote = [artbook.find_book(manifest, book_name)]
        except UnknownBookError:
            available = ", ".join(b.name for b in manifest.books)
            _err(
                f"book '{book_name}' not found in distro '{manifest.name}'",
                f"Available books: {available}.",
            )
            return 1
    else:
        books_to_promote = [b for b in manifest.books if b.promote is not None]

    if not books_to_promote:
        _CONSOLE.print("No books with promote: field found.")
        return 0

    exit_code = 0
    state = read_state(root)

    for book in books_to_promote:
        if book.promote is None:
            if book_name:
                _err(f"book '{book.name}' has no promote: field; nothing to promote")
                return 1
            continue

        try:
            report = promote_book(
                book,
                root,
                mode_override=arts.promote_mode,
                state=state,
                dry_run=dry_run,
                clean=clean,
            )
        except (ArtbookError, ValueError) as exc:
            _err(str(exc))
            return 1

        if json_out:
            _render_promotion_report(report, root, json_out=True, dry_run=dry_run)
        else:
            _render_promotion_report(report, root, json_out=False, dry_run=dry_run)

        if report.errors:
            exit_code = 1

    return exit_code


# ---------------------------------------------------------------------------
# Top-level dispatcher and registration
# ---------------------------------------------------------------------------


def _run_book(args) -> int:
    """Dispatch to the selected book sub-verb after vault/settings setup."""
    root, raw = _load_vault_and_raw()
    if root is None:
        return 3
    return args.book_func(args, root, raw)


def register(subparsers) -> None:
    """Register the ``book`` command on *subparsers*."""
    book_parser = subparsers.add_parser(
        "book",
        help="browse and pull books from a configured distro",
    )
    book_subs = book_parser.add_subparsers(dest="book_verb", metavar="VERB")
    book_subs.required = True

    # --- list ---
    list_p = book_subs.add_parser(
        "list",
        help="list available books in the distro",
    )
    list_p.add_argument(
        "--json", "-j",
        action="store_true",
        dest="json_out",
        default=False,
        help="output raw JSON (default: Rich table)",
    )
    list_p.add_argument(
        "--remote",
        action="store_true",
        dest="remote",
        default=False,
        help="force the remote-clone path even when a local artbook.yaml is present",
    )
    list_p.set_defaults(book_func=_run_list)

    # --- show ---
    show_p = book_subs.add_parser(
        "show",
        help="show details and contents of a book",
    )
    show_p.add_argument("name", help="book name")
    show_p.add_argument(
        "--json", "-j",
        action="store_true",
        dest="json_out",
        default=False,
        help="output raw JSON (default: Rich text)",
    )
    show_p.add_argument(
        "--remote",
        action="store_true",
        dest="remote",
        default=False,
        help="force the remote-clone path even when a local artbook.yaml is present",
    )
    show_p.set_defaults(book_func=_run_show)

    # --- pull ---
    pull_p = book_subs.add_parser(
        "pull",
        help="pull a book into the vault",
    )
    pull_p.add_argument("name", help="book name")
    pull_p.add_argument(
        "items",
        nargs="*",
        metavar="ITEM",
        help=(
            "optional item filter — pull only matching items. "
            "For flat books: filename stem (architect) or full filename (architect.md). "
            "For recurse books: unit folder name (artifacts-os). "
            "If omitted, all items are pulled. "
            "Any unrecognised item aborts before writing."
        ),
    )
    pull_p.add_argument(
        "--json", "-j",
        action="store_true",
        dest="json_out",
        default=False,
        help="output JSONL writes + summary (default: Rich table)",
    )
    pull_p.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=False,
        help="plan the writes but do not execute them",
    )
    pull_p.add_argument(
        "--no-promote",
        action="store_true",
        dest="no_promote",
        default=False,
        help=(
            "skip the promotion step for this pull (canonical writes still happen). "
            "One-shot opt-out per D31; wins over artbook.promotion: disabled setting."
        ),
    )
    pull_p.set_defaults(book_func=_run_pull)

    # --- promote ---
    promote_p = book_subs.add_parser(
        "promote",
        help="re-run promotion for book(s) against current canonical content",
    )
    promote_p.add_argument(
        "book_name",
        nargs="?",
        metavar="BOOK",
        default=None,
        help=(
            "book name to promote. "
            "If omitted, re-runs promotion for every book with a promote: field."
        ),
    )
    promote_p.add_argument(
        "--clean",
        action="store_true",
        dest="clean",
        default=False,
        help="ignore existing state for this book and rebuild from current canonical content",
    )
    promote_p.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=False,
        help="print planned writes/cleanups, make no filesystem changes",
    )
    promote_p.add_argument(
        "--json", "-j",
        action="store_true",
        dest="json_out",
        default=False,
        help="emit PromotionReport as JSON (default: Rich table)",
    )
    promote_p.set_defaults(book_func=_run_promote)

    book_parser.set_defaults(func=_run_book, _pre_registry=True)
